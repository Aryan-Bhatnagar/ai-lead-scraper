"""
SQLite persistence for the AI Lead Scraper (Phase 5).

Uses Python's built-in sqlite3. Three tables:
  - leads            one row per company, unique on source_url (upsert)
  - scrape_jobs      one row per scraping run (for the future Flask API)
  - scrape_job_items one row per URL within a job (FK -> scrape_jobs)

All queries are parameterized; foreign keys are enforced; writes run inside
transactions via context managers.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# Default database location – tests override this via ``set_database_path``.
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "leads.db"

def set_database_path(path: str | Path) -> None:
    """Override the default database path.

    The test suite creates a temporary SQLite file and passes its path via the
    ``DATABASE`` Flask config key.  This helper makes it easy for the code to
    honour that override without touching production data.
    """
    global DB_PATH
    DB_PATH = Path(path)

JOB_STATUSES = {"queued", "running", "completed", "failed"}
JOB_ITEM_STATUSES = {"queued", "running", "success", "no_data", "failed", "skipped"}

# Columns of the leads table that come from the scraped lead dict
# (same field names as the scraper's CSV row, minus scraper-only bookkeeping)
LEAD_COLUMNS = [
    "company_name",
    "industry",
    "company_description",
    "contact_name",
    "contact_role",
    "email",
    "phone",
    "website",
    "city",
    "country",
    "source_url",
    "source_pages",
    "email_source_page",
    "email_source_type",
    "phone_source_page",
    "phone_source_type",
    "scraped_at",
    "status",
    "quality_score",
    "data_quality",
    "error",
]

# CRM lead lifecyle statuses – independent of the scraper ``status`` field.
LEAD_STATUSES = {
    "NEW",
    "QUALIFIED",
    "CONTACTED",
    "INTERESTED",
    "CONVERTED",
    "REJECTED",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    industry TEXT,
    company_description TEXT,
    contact_name TEXT,
    contact_role TEXT,
    email TEXT,
    phone TEXT,
    website TEXT,
    city TEXT,
    country TEXT,
    source_url TEXT UNIQUE,
    source_pages TEXT,
    email_source_page TEXT,
    email_source_type TEXT,
    phone_source_page TEXT,
    phone_source_type TEXT,
    scraped_at TEXT,
    status TEXT,
    quality_score INTEGER,
    data_quality TEXT,
    error TEXT,
    lead_status TEXT NOT NULL DEFAULT 'NEW',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS scrape_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT,
    total_urls INTEGER,
    completed_urls INTEGER DEFAULT 0,
    successful_urls INTEGER DEFAULT 0,
    no_data_urls INTEGER DEFAULT 0,
    failed_urls INTEGER DEFAULT 0,
    skipped_urls INTEGER DEFAULT 0,
    current_url TEXT,
    created_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS scrape_job_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    source_url TEXT,
    status TEXT,
    error TEXT,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (job_id) REFERENCES scrape_jobs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_leads_source_url ON leads(source_url);
CREATE INDEX IF NOT EXISTS idx_leads_data_quality ON leads(data_quality);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_lead_status ON leads(lead_status);
CREATE INDEX IF NOT EXISTS idx_job_items_job_id ON scrape_job_items(job_id);
"""


def utc_now() -> str:
    """Return the current UTC timestamp as an ISO‑8601 string (seconds precision)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_connection(db_path: Path | str = DB_PATH):
    """Connection context manager.

    * Enables foreign‑key constraints.
    * Returns ``sqlite3.Row`` objects for dict‑like access.
    * Commits on success, rolls back on exception.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database(db_path: Path | str = DB_PATH) -> None:
    """Create tables and indexes if they don't exist.

    This function is idempotent – it can be called on every app start.  It also
    performs a lightweight migration for older databases that lack the
    ``lead_status`` column.

    The migration runs **before** any ``CREATE INDEX`` statements that refer to
    ``lead_status``.  Older databases contain the ``leads`` table without the
    ``lead_status`` column, but the ``SCHEMA`` script creates the index on that
    column *after* the ``CREATE TABLE`` block, causing ``sqlite3.OperationalError``
    ``no such column: lead_status`` during initialization.  We now catch that
    error, add the column, and retry the script so that the indexes can be
    created safely.
    """
    with get_connection(db_path) as conn:
        try:
            # Try the full schema first – on a brand‑new DB this succeeds.
            conn.executescript(SCHEMA)
        except sqlite3.OperationalError as e:
            # If the error is caused by the missing ``lead_status`` column,
            # add the column and retry the script.
            if "no such column: lead_status" in str(e):
                conn.execute(
                    "ALTER TABLE leads ADD COLUMN lead_status TEXT NOT NULL DEFAULT 'NEW'"
                )
                conn.executescript(SCHEMA)
            else:
                # Unexpected error – re‑raise.
                raise

        # Ensure ``lead_status`` exists for the case where the schema ran
        # successfully but the column is still missing (e.g., a DB that was
        # created with a schema that omitted the column but did not have the
        # failing index). This makes the migration truly idempotent.
        cur = conn.execute("PRAGMA table_info(leads)")
        cols = {row["name"] for row in cur.fetchall()}
        if "lead_status" not in cols:
            conn.execute(
                "ALTER TABLE leads ADD COLUMN lead_status TEXT NOT NULL DEFAULT 'NEW'"
            )

# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------
def upsert_lead(lead: dict, db_path: Path | str = DB_PATH) -> int:
    """Insert or update a lead keyed by ``source_url``.

    * If the ``source_url`` already exists the row is updated – **only** the
      columns listed in :data:`LEAD_COLUMNS` are touched.  ``lead_status`` is
      deliberately omitted so manual CRM updates survive rescrapes.
    * ``created_at`` is set on insert, ``updated_at`` on both insert and
      update.
    """
    if not lead.get("source_url"):
        raise ValueError("upsert_lead requires a non-empty source_url")

    now = utc_now()
    values = {col: lead.get(col, "") for col in LEAD_COLUMNS}
    values["quality_score"] = int(lead.get("quality_score") or 0)

    columns = ", ".join(LEAD_COLUMNS)
    placeholders = ", ".join(f":{c}" for c in LEAD_COLUMNS)
    update_cols = [c for c in LEAD_COLUMNS if c != "source_url"]
    update_clause = ", ".join(f"{c} = excluded.{c}" for c in update_cols)

    with get_connection(db_path) as conn:
        conn.execute(
            f"""
            INSERT INTO leads ({columns}, created_at, updated_at)
            VALUES ({placeholders}, :now, :now)
            ON CONFLICT(source_url) DO UPDATE SET
                {update_clause},
                updated_at = excluded.updated_at
            """,
            {**values, "now": now},
        )
        row = conn.execute(
            "SELECT id FROM leads WHERE source_url = ?", (values["source_url"],)
        ).fetchone()
        return row["id"]


def get_lead_by_source_url(source_url: str, db_path: Path | str = DB_PATH) -> dict | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM leads WHERE source_url = ?", (source_url,)
        ).fetchone()
        return dict(row) if row else None

def get_lead_by_id(lead_id: int, db_path: Path | str = DB_PATH) -> dict | None:
    """Return a lead row by primary key ``id`` or ``None`` if not found."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM leads WHERE id = ?", (lead_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_leads(db_path: Path | str = DB_PATH) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM leads ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def delete_lead(lead_id: int, db_path: Path | str = DB_PATH) -> bool:
    """Delete a lead; returns ``True`` if a row was removed."""
    with get_connection(db_path) as conn:
        cur = conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
        return cur.rowcount > 0


def update_lead_status(lead_id: int, lead_status: str, db_path: Path | str = DB_PATH) -> bool:
    """Update the CRM ``lead_status`` for a lead.

    * ``lead_status`` must be one of :data:`LEAD_STATUSES` – otherwise a
      ``ValueError`` is raised.
    * ``updated_at`` is refreshed to the current timestamp.
    * Returns ``True`` when a row was updated, ``False`` when the ``lead_id``
      does not exist.
    """
    if lead_status not in LEAD_STATUSES:
        raise ValueError(f"Invalid lead_status: {lead_status}")
    now = utc_now()
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "UPDATE leads SET lead_status = ?, updated_at = ? WHERE id = ?",
            (lead_status, now, lead_id),
        )
        return cur.rowcount > 0

# ---------------------------------------------------------------------------
# Scrape jobs
# ---------------------------------------------------------------------------
def create_scrape_job(urls: list[str], db_path: Path | str = DB_PATH) -> int:
    """Create a queued job plus one queued item per URL. Returns the job id."""
    now = utc_now()
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO scrape_jobs (status, total_urls, created_at)
            VALUES ('queued', ?, ?)
            """,
            (len(urls), now),
        )
        job_id = cur.lastrowid
        conn.executemany(
            """
            INSERT INTO scrape_job_items (job_id, source_url, status)
            VALUES (?, ?, 'queued')
            """,
            [(job_id, url) for url in urls],
        )
        return job_id


def get_scrape_job(job_id: int, db_path: Path | str = DB_PATH) -> dict | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM scrape_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return dict(row) if row else None


def update_scrape_job(job_id: int, db_path: Path | str = DB_PATH, **fields) -> None:
    """Update named columns on a job (status, counters, current_url, ...)."""
    allowed = {
        "status", "total_urls", "completed_urls", "successful_urls",
        "no_data_urls", "failed_urls", "skipped_urls", "current_url",
        "started_at", "completed_at", "error",
    }
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unknown scrape_jobs columns: {sorted(unknown)}")
    if "status" in fields and fields["status"] not in JOB_STATUSES:
        raise ValueError(f"Invalid job status: {fields['status']}")
    if not fields:
        return
    clause = ", ".join(f"{c} = :{c}" for c in fields)
    with get_connection(db_path) as conn:
        conn.execute(
            f"UPDATE scrape_jobs SET {clause} WHERE id = :job_id",
            {**fields, "job_id": job_id},
        )


def update_job_item(
    job_id: int,
    source_url: str,
    status: str,
    error: str = "",
    db_path: Path | str = DB_PATH,
) -> None:
    """Update one job item's status; stamps ``started_at``/``completed_at`` as appropriate."""
    if status not in JOB_ITEM_STATUSES:
        raise ValueError(f"Invalid job item status: {status}")
    now = utc_now()
    sets = ["status = :status", "error = :error"]
    if status == "running":
        sets.append("started_at = :now")
    elif status in {"success", "no_data", "failed", "skipped"}:
        sets.append("completed_at = :now")
    with get_connection(db_path) as conn:
        conn.execute(
            f"""
            UPDATE scrape_job_items SET {", ".join(sets)}
            WHERE job_id = :job_id AND source_url = :source_url
            """,
            {"status": status, "error": error, "now": now,
             "job_id": job_id, "source_url": source_url},
        )


def get_job_items(job_id: int, db_path: Path | str = DB_PATH) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM scrape_job_items WHERE job_id = ? ORDER BY id",
            (job_id,),
        ).fetchall()
        return [dict(r) for r in rows]
