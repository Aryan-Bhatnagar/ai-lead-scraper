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
import json
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

-- Outreach queue table (Phase 10B)
CREATE TABLE IF NOT EXISTS outreach_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    outreach_channel TEXT NOT NULL,
    outreach_status TEXT NOT NULL DEFAULT 'PENDING',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_contacted_at TEXT,
    next_follow_up_at TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
    CHECK (outreach_channel IN ('EMAIL','WHATSAPP','CALL')),
    CHECK (outreach_status IN ('PENDING','PROCESSING','SENT','FAILED','COMPLETED'))
);

CREATE TABLE IF NOT EXISTS ai_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    company_summary TEXT,
    services_offered TEXT,
    target_customers TEXT,
    business_model TEXT,
    industry_category TEXT,
    technologies_used TEXT,
    pain_points TEXT,
    sales_opportunities TEXT,
    generated_at TEXT,
    llm_provider TEXT,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS business_profiles (
    lead_id INTEGER PRIMARY KEY,
    profile_json TEXT,
    updated_at TEXT,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS enrichment_raw_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    provider_name TEXT NOT NULL,
    raw_payload TEXT,
    created_at TEXT,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_enrichment_lead_id ON enrichment_raw_data(lead_id);


CREATE UNIQUE INDEX IF NOT EXISTS uq_outreach_active
ON outreach_queue (lead_id, outreach_channel)
WHERE outreach_status IN ('PENDING','PROCESSING','SENT');
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

# ---------------------------------------------------------------------------
# Outreach Queue (Phase 10B)
# ---------------------------------------------------------------------------

# Allowed channel and status values – used for validation in the API.
OUTREACH_CHANNELS = {"EMAIL", "WHATSAPP", "CALL"}
OUTREACH_STATUSES = {"PENDING", "PROCESSING", "SENT", "FAILED", "COMPLETED"}
ACTIVE_OUTREACH_STATUSES = {"PENDING", "PROCESSING", "SENT"}

def create_outreach_entry(
    lead_id: int,
    outreach_channel: str,
    db_path: Path | str = DB_PATH,
    next_follow_up_at: str | None = None,
) -> int:
    """Insert a new outreach queue entry.

    The function validates:
    * ``outreach_channel`` is in :data:`OUTREACH_CHANNELS`.
    * No *active* queue entry exists for the same ``lead_id``/``outreach_channel``.
    It sets ``created_at``/``updated_at`` using :func:`utc_now` and returns the
    new row ``id``.
    """
    if outreach_channel not in OUTREACH_CHANNELS:
        raise ValueError(f"Invalid outreach_channel: {outreach_channel}")

    now = utc_now()
    with get_connection(db_path) as conn:
        # Application‑level duplicate‑active guard – raise if one already exists.
        dup = conn.execute(
            "SELECT 1 FROM outreach_queue WHERE lead_id = ? AND outreach_channel = ? AND outreach_status IN (" + ",".join([f"'{s}'" for s in ACTIVE_OUTREACH_STATUSES]) + ")",
            (lead_id, outreach_channel),
        ).fetchone()
        if dup:
            raise ValueError(
                "active outreach entry already exists for this lead and channel"
            )
        cur = conn.execute(
            """
            INSERT INTO outreach_queue (
                lead_id,
                outreach_channel,
                outreach_status,
                attempt_count,
                created_at,
                updated_at,
                next_follow_up_at
            ) VALUES (?, ?, 'PENDING', 0, ?, ?, ?)
            """,
            (lead_id, outreach_channel, now, now, next_follow_up_at),
        )
        return cur.lastrowid

def get_outreach_entries(
    db_path: Path | str = DB_PATH,
    lead_id: int | None = None,
    outreach_channel: str | None = None,
    outreach_status: str | None = None,
) -> list[dict]:
    """Return outreach queue rows optionally filtered by the given parameters.

    Includes related lead information (company_name, email, phone) via a LEFT JOIN.
    """
    # Base query selects all outreach_queue columns plus lead fields.
    query = """
        SELECT oq.*, l.company_name, l.email, l.phone
        FROM outreach_queue oq
        LEFT JOIN leads l ON oq.lead_id = l.id
    """
    clauses: list[str] = []
    params: list = []
    if lead_id is not None:
        clauses.append("oq.lead_id = ?")
        params.append(lead_id)
    if outreach_channel is not None:
        clauses.append("oq.outreach_channel = ?")
        params.append(outreach_channel)
    if outreach_status is not None:
        clauses.append("oq.outreach_status = ?")
        params.append(outreach_status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
    return [dict(r) for r in rows]

def get_outreach_entry_by_id(entry_id: int, db_path: Path | str = DB_PATH) -> dict | None:
    """Return a single outreach entry (including related lead fields).

    The result includes the outreach_queue columns plus ``company_name``, ``email`` and ``phone``
    from the associated lead, via a LEFT JOIN.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT oq.*, l.company_name, l.email, l.phone
            FROM outreach_queue oq
            LEFT JOIN leads l ON oq.lead_id = l.id
            WHERE oq.id = ?
            """,
            (entry_id,)
        ).fetchone()
        return dict(row) if row else None

def update_outreach_entry(
    entry_id: int,
    db_path: Path | str = DB_PATH,
    **fields,
) -> bool:
    """Update mutable fields of an outreach entry.

    Allowed mutable fields are ``outreach_status``, ``next_follow_up_at``,
    ``error_message``. Attempt count and timestamps are handled automatically.
    """
    if not fields:
        return False
    allowed = {"outreach_status", "next_follow_up_at", "error_message"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Invalid outreach fields: {sorted(unknown)}")

    # Load current row for business‑logic checks (attempt_count, timestamps).
    cur_row = get_outreach_entry_by_id(entry_id, db_path)
    if not cur_row:
        return False

    # Prepare updates.
    set_clauses: list[str] = []
    params: list = []
    now = utc_now()

    # Handle status transition logic.
    if "outreach_status" in fields:
        new_status = fields["outreach_status"]
        if new_status not in OUTREACH_STATUSES:
            raise ValueError(f"Invalid outreach_status: {new_status}")
        old_status = cur_row["outreach_status"]
        # Increment attempt_count only when entering PROCESSING from a non‑PROCESSING state.
        if new_status == "PROCESSING" and old_status != "PROCESSING":
            set_clauses.append("attempt_count = attempt_count + 1")
            # Record when the attempt actually starts.
            set_clauses.append("last_contacted_at = ?")
            params.append(now)
        # If moving to SENT or FAILED, we keep the existing last_contacted_at (already set when PROCESSING started).
        # Clear error_message when moving out of FAILED (optional – preserve if you like).
        if old_status == "FAILED" and new_status != "FAILED":
            set_clauses.append("error_message = NULL")
        set_clauses.append("outreach_status = ?")
        params.append(new_status)
    # next_follow_up_at and error_message are direct assignments if present.
    if "next_follow_up_at" in fields:
        set_clauses.append("next_follow_up_at = ?")
        params.append(fields["next_follow_up_at"])
    if "error_message" in fields:
        set_clauses.append("error_message = ?")
        params.append(fields["error_message"])

    # Always bump updated_at.
    set_clauses.append("updated_at = ?")
    params.append(now)

    set_clause = ", ".join(set_clauses)
    sql = f"UPDATE outreach_queue SET {set_clause} WHERE id = ?"
    params.append(entry_id)

    with get_connection(db_path) as conn:
        cur = conn.execute(sql, params)
        return cur.rowcount > 0

def delete_outreach_entry(entry_id: int, db_path: Path | str = DB_PATH) -> bool:
    """Delete an outreach entry if it is in a cancellable state.

    Cancellable states are ``PENDING`` and ``FAILED``. Returns ``True`` when a row
    was removed.
    """
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "DELETE FROM outreach_queue WHERE id = ? AND outreach_status IN ('PENDING','FAILED')",
            (entry_id,),
        )
        return cur.rowcount > 0
def start_dispatch(entry_id: int, db_path: Path | str = DB_PATH) -> bool:
    """Transition a PENDING or FAILED outreach entry to PROCESSING."""
    now = utc_now()

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE outreach_queue
            SET outreach_status = 'PROCESSING',
                attempt_count = attempt_count + 1,
                last_contacted_at = ?,
                error_message = NULL,
                updated_at = ?
            WHERE id = ?
              AND outreach_status IN ('PENDING', 'FAILED')
            """,
            (now, now, entry_id),
        )
        return cursor.rowcount > 0


def mark_dispatch_success(
    entry_id: int,
    db_path: Path | str = DB_PATH,
) -> bool:
    """Transition a PROCESSING outreach entry to SENT."""
    now = utc_now()

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE outreach_queue
            SET outreach_status = 'SENT',
                error_message = NULL,
                updated_at = ?
            WHERE id = ?
              AND outreach_status = 'PROCESSING'
            """,
            (now, entry_id),
        )
        return cursor.rowcount > 0


def mark_dispatch_failure(
    entry_id: int,
    db_path: Path | str = DB_PATH,
    error_msg: str | None = None,
) -> bool:
    """Transition a PROCESSING outreach entry to FAILED."""
    now = utc_now()

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE outreach_queue
            SET outreach_status = 'FAILED',
                error_message = ?,
                updated_at = ?
            WHERE id = ?
              AND outreach_status = 'PROCESSING'
            """,
            (error_msg, now, entry_id),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Scrape jobs
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
        return [dict(dict(r)) for r in rows]

def get_ai_insights_by_lead_id(lead_id: int, db_path: Path | str = DB_PATH) -> dict | None:
    """Return AI insights for a specific lead, or None if not found."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM ai_insights WHERE lead_id = ?", (lead_id,)
        ).fetchone()
        if not row:
            return None

        result = dict(row)
        # JSON columns that should be deserialized
        json_cols = [
            "services_offered", "target_customers", "technologies_used",
            "pain_points", "sales_opportunities"
        ]
        for col in json_cols:
            val = result.get(col)
            if isinstance(val, str) and (val.startswith('[') or val.startswith('{')):
                try:
                    result[col] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass
        return result

def upsert_ai_insights(lead_id: int, insights: dict, provider: str, db_path: Path | str = DB_PATH) -> int:
    """Insert or update AI insights for a lead. Returns the insight row id."""
    now = utc_now()
    # We expect insights to be a dict matching the table columns
    columns = [
        "company_summary", "services_offered", "target_customers",
        "business_model", "industry_category", "technologies_used",
        "pain_points", "sales_opportunities"
    ]

    # Ensure all columns are present and convert lists/dicts to JSON
    values = {}
    for col in columns:
        val = insights.get(col, "")
        if isinstance(val, (list, dict)):
            values[col] = json.dumps(val)
        else:
            values[col] = val

    with get_connection(db_path) as conn:
        # Check if exists
        existing = conn.execute(
            "SELECT id FROM ai_insights WHERE lead_id = ?", (lead_id,)
        ).fetchone()

        if existing:
            # Update existing
            set_clause = ", ".join([f"{c} = :{c}" for c in columns])
            set_clause += ", generated_at = :generated_at, llm_provider = :llm_provider"
            conn.execute(
                f"UPDATE ai_insights SET {set_clause} WHERE lead_id = :lead_id",
                {**values, "generated_at": now, "llm_provider": provider, "lead_id": lead_id}
            )
            return existing["id"]
        else:
            # Insert new
            cols = ["lead_id"] + columns + ["generated_at", "llm_provider"]
            placeholders = ", ".join([":" + c for c in cols])
            cur = conn.execute(
                f"INSERT INTO ai_insights ({', '.join(cols)}) VALUES ({placeholders})",
                {**values, "lead_id": lead_id, "generated_at": now, "llm_provider": provider}
            )
            return cur.lastrowid

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