"""Offline tests for scraper/database.py using a temporary SQLite database.

Never touches data/leads.db. Run: python scraper/test_database.py
"""

import sqlite3
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import database as db

failures = []


def check(label, got, expected):
    if got != expected:
        failures.append(f"FAIL: {label} -> {got!r}, expected {expected!r}")


def sample_lead(**overrides) -> dict:
    lead = {
        "company_name": "Acme",
        "industry": "SaaS",
        "company_description": "Does things.",
        "contact_name": "John Smith",
        "contact_role": "CEO",
        "email": "sales@acme.com",
        "phone": "+15551234567",
        "website": "https://acme.com",
        "city": "Berlin",
        "country": "Germany",
        "source_url": "https://acme.com/",
        "source_pages": "https://acme.com/|https://acme.com/contact",
        "email_source_page": "https://acme.com/contact",
        "email_source_type": "mailto",
        "phone_source_page": "https://acme.com/contact",
        "phone_source_type": "tel",
        "scraped_at": "2026-07-18T12:00:00+00:00",
        "status": "success",
        "quality_score": 100,
        "data_quality": "HIGH",
        "error": "",
    }
    lead.update(overrides)
    return lead


# Use a temporary file for the SQLite database (does not create a dir)
DB = Path(tempfile.mktemp(suffix=".db"))
# ensure file does not exist before we start
if DB.exists():
    DB.unlink()

    # --- initialization -----------------------------------------------------
    db.initialize_database(DB)
    with sqlite3.connect(DB) as conn:
        tables = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    for table in ("leads", "scrape_jobs", "scrape_job_items"):
        check(f"table exists: {table}", table in tables, True)

    # idempotent re-init
    db.initialize_database(DB)
    check("re-init safe", True, True)

    with sqlite3.connect(DB) as conn:
        indexes = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
        }
    for idx in ("idx_leads_source_url", "idx_leads_data_quality",
                "idx_leads_status", "idx_job_items_job_id"):
        check(f"index exists: {idx}", idx in indexes, True)

    # --- lead insert --------------------------------------------------------
    lead_id = db.upsert_lead(sample_lead(), DB)
    check("insert returns id", lead_id, 1)
    stored = db.get_lead_by_source_url("https://acme.com/", DB)
    check("get by source_url", stored["company_name"], "Acme")
    check("created_at set", bool(stored["created_at"]), True)
    check("updated_at set", bool(stored["updated_at"]), True)
    check("quality_score is int", stored["quality_score"], 100)
    check("quality_score type", type(stored["quality_score"]), int)

    # provenance fields persist
    check("email prov page", stored["email_source_page"], "https://acme.com/contact")
    check("email prov type", stored["email_source_type"], "mailto")
    check("phone prov page", stored["phone_source_page"], "https://acme.com/contact")
    check("phone prov type", stored["phone_source_type"], "tel")
    check("source_pages persisted", stored["source_pages"],
          "https://acme.com/|https://acme.com/contact")

    # --- upsert by source_url ----------------------------------------------
    original_created = stored["created_at"]
    time.sleep(1.1)  # ensure a different updated_at second
    lead_id2 = db.upsert_lead(
        sample_lead(company_name="Acme GmbH", quality_score=85, data_quality="HIGH"),
        DB,
    )
    check("upsert same id", lead_id2, lead_id)
    check("no duplicate after upsert", len(db.get_all_leads(DB)), 1)
    updated = db.get_lead_by_source_url("https://acme.com/", DB)
    check("upsert updated field", updated["company_name"], "Acme GmbH")
    check("upsert updated score", updated["quality_score"], 85)
    check("created_at preserved", updated["created_at"], original_created)
    check("updated_at changed", updated["updated_at"] != original_created, True)

    # --- multiple leads / get_all / delete ---------------------------------
    db.upsert_lead(sample_lead(source_url="https://other.com/", company_name="Other"), DB)
    all_leads = db.get_all_leads(DB)
    check("get_all count", len(all_leads), 2)
    check("get_all order by id", [l["company_name"] for l in all_leads],
          ["Acme GmbH", "Other"])

    check("delete existing", db.delete_lead(lead_id, DB), True)
    check("delete missing", db.delete_lead(999, DB), False)
    check("count after delete", len(db.get_all_leads(DB)), 1)
    check("deleted gone", db.get_lead_by_source_url("https://acme.com/", DB), None)

    # source_url is required
    try:
        db.upsert_lead({"company_name": "NoUrl"}, DB)
        check("upsert without source_url raises", "no exception", "ValueError")
    except ValueError:
        check("upsert without source_url raises", "ValueError", "ValueError")

    # --- SQL parameter safety ----------------------------------------------
    tricky = sample_lead(
        source_url="https://tricky.com/?q='; DROP TABLE leads;--",
        company_name='O\'Reilly "Media" & Co, LLC',
        company_description="Line1\nLine2, with 'quotes' and; semicolons",
    )
    db.upsert_lead(tricky, DB)
    fetched = db.get_lead_by_source_url("https://tricky.com/?q='; DROP TABLE leads;--", DB)
    check("special chars roundtrip", fetched["company_name"], 'O\'Reilly "Media" & Co, LLC')
    check("newlines roundtrip", fetched["company_description"],
          "Line1\nLine2, with 'quotes' and; semicolons")
    check("leads table survived injection text", len(db.get_all_leads(DB)), 2)

    # --- scrape jobs --------------------------------------------------------
    urls = ["https://a.com/", "https://b.com/", "https://c.com/"]
    job_id = db.create_scrape_job(urls, DB)
    job = db.get_scrape_job(job_id, DB)
    check("job created queued", job["status"], "queued")
    check("job total_urls", job["total_urls"], 3)
    check("job counters default 0", job["completed_urls"], 0)
    check("job created_at set", bool(job["created_at"]), True)
    check("get missing job", db.get_scrape_job(999, DB), None)

    items = db.get_job_items(job_id, DB)
    check("items created per url", len(items), 3)
    check("items queued", {i["status"] for i in items}, {"queued"})
    check("item urls", [i["source_url"] for i in items], urls)

    # --- job status/progress updates ---------------------------------------
    db.update_scrape_job(job_id, DB, status="running", started_at=db.utc_now(),
                         current_url="https://a.com/")
    job = db.get_scrape_job(job_id, DB)
    check("job running", job["status"], "running")
    check("job current_url", job["current_url"], "https://a.com/")

    db.update_job_item(job_id, "https://a.com/", "running", db_path=DB)
    item = db.get_job_items(job_id, DB)[0]
    check("item running", item["status"], "running")
    check("item started_at", bool(item["started_at"]), True)

    db.update_job_item(job_id, "https://a.com/", "success", db_path=DB)
    db.update_job_item(job_id, "https://b.com/", "failed", error="Timeout", db_path=DB)
    db.update_job_item(job_id, "https://c.com/", "skipped", db_path=DB)
    items = db.get_job_items(job_id, DB)
    check("item success", items[0]["status"], "success")
    check("item completed_at", bool(items[0]["completed_at"]), True)
    check("item failed error", items[1]["error"], "Timeout")
    check("item skipped", items[2]["status"], "skipped")

    db.update_scrape_job(job_id, DB, status="completed", completed_urls=3,
                         successful_urls=1, failed_urls=1, skipped_urls=1,
                         completed_at=db.utc_now())
    job = db.get_scrape_job(job_id, DB)
    check("job completed", job["status"], "completed")
    check("job progress counts", (job["completed_urls"], job["successful_urls"],
                                  job["failed_urls"], job["skipped_urls"]), (3, 1, 1, 1))

    # invalid statuses rejected
    try:
        db.update_scrape_job(job_id, DB, status="banana")
        check("invalid job status raises", "no exception", "ValueError")
    except ValueError:
        check("invalid job status raises", "ValueError", "ValueError")
    try:
        db.update_job_item(job_id, "https://a.com/", "banana", db_path=DB)
        check("invalid item status raises", "no exception", "ValueError")
    except ValueError:
        check("invalid item status raises", "ValueError", "ValueError")
    try:
        db.update_scrape_job(job_id, DB, nonsense_column="x")
        check("unknown job column raises", "no exception", "ValueError")
    except ValueError:
        check("unknown job column raises", "ValueError", "ValueError")

    # --- foreign key behavior ----------------------------------------------
    # inserting an item for a nonexistent job must fail
    try:
        with db.get_connection(DB) as conn:
            conn.execute(
                "INSERT INTO scrape_job_items (job_id, source_url, status) "
                "VALUES (999, 'https://x.com/', 'queued')"
            )
        check("FK violation raises", "no exception", "IntegrityError")
    except sqlite3.IntegrityError:
        check("FK violation raises", "IntegrityError", "IntegrityError")

    # deleting a job cascades to its items
    with db.get_connection(DB) as conn:
        conn.execute("DELETE FROM scrape_jobs WHERE id = ?", (job_id,))
    check("cascade deletes items", db.get_job_items(job_id, DB), [])


if failures:
    print("\n".join(failures))
    print(f"\n{len(failures)} test(s) FAILED")
    sys.exit(1)
print("All database tests passed.")
# clean up temp DB file
if DB.exists():
    DB.unlink()
