"""SQLiteStore — Phase 19B.

Own, separate SQLite database (``data/leads_repo.db`` by default) so the
legacy ``data/leads.db`` and the Flask endpoints backed by it are untouched.
"""

from __future__ import annotations

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..exceptions import DuplicateLeadError, StoreConfigurationError
from ..models import LeadRecord
from .base import LeadQuery, LeadStore


SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id                    TEXT PRIMARY KEY,
    canonical_domain      TEXT,
    company_name_norm     TEXT,
    external_ids_json     TEXT,
    company_name          TEXT,
    website               TEXT,
    description           TEXT,
    industry              TEXT,
    city                  TEXT,
    region                TEXT,
    country               TEXT,
    address               TEXT,
    emails_json           TEXT,
    phones_json           TEXT,
    socials_json          TEXT,
    hourly_rate           REAL,
    skills_json           TEXT,
    rating                REAL,
    jobs_completed        INTEGER,
    maps_rating           REAL,
    maps_review_count     INTEGER,
    coordinates_json      TEXT,
    business_status       TEXT,
    categories_json       TEXT,
    provenance_json       TEXT,
    score                 INTEGER,
    quality_tier          TEXT,
    explanation_json      TEXT,
    lifecycle             TEXT NOT NULL DEFAULT 'NEW',
    lifecycle_updated_at  TEXT,
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lead_lifecycle_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id     TEXT NOT NULL,
    from_state  TEXT,
    to_state    TEXT NOT NULL,
    reason      TEXT,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_leads_domain     ON leads(canonical_domain);
CREATE INDEX IF NOT EXISTS idx_leads_lifecycle  ON leads(lifecycle);
CREATE INDEX IF NOT EXISTS idx_leads_score      ON leads(score);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_events_lead_id   ON lead_lifecycle_events(lead_id);
"""

_COLUMNS = [
    "id", "canonical_domain", "company_name_norm", "external_ids_json",
    "company_name", "website", "description", "industry",
    "city", "region", "country", "address",
    "emails_json", "phones_json", "socials_json",
    "hourly_rate", "skills_json", "rating", "jobs_completed",
    "maps_rating", "maps_review_count", "coordinates_json",
    "business_status", "categories_json", "provenance_json",
    "score", "quality_tier", "explanation_json",
    "lifecycle", "lifecycle_updated_at", "created_at", "updated_at",
]

_SORTABLE = {"created_at", "updated_at", "score", "company_name"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SQLiteStore(LeadStore):
    """SQLite-backed LeadStore with parameterized queries and transaction safety."""

    def __init__(self, uri_or_path: str | Path) -> None:
        s = str(uri_or_path)
        if s.startswith("sqlite:///"):
            s = s[len("sqlite:///"):]
        self.db_path = Path(s)
        # ":memory:" is a legal sqlite path for ephemeral stores in tests.
        if s != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def insert(self, record: LeadRecord) -> str:
        columns = ", ".join(_COLUMNS)
        placeholders = ", ".join(f":{c}" for c in _COLUMNS)
        values = {c: record.get(c) for c in _COLUMNS}
        with self._connect() as conn:
            try:
                conn.execute(
                    f"INSERT INTO leads ({columns}) VALUES ({placeholders})",
                    values,
                )
            except sqlite3.IntegrityError as exc:
                if "UNIQUE constraint failed" in str(exc):
                    raise DuplicateLeadError(record["id"]) from exc
                raise
        return record["id"]

    def get(self, lead_id: str) -> Optional[LeadRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM leads WHERE id = ?", (lead_id,)
            ).fetchone()
        return self._row_to_record(row) if row else None

    def update(self, lead_id: str, record: LeadRecord) -> bool:
        assignments = ", ".join(f"{c} = :{c}" for c in _COLUMNS if c not in ("id", "created_at"))
        values = {c: record.get(c) for c in _COLUMNS if c not in ("id", "created_at")}
        values["id"] = lead_id
        values["updated_at"] = _utc_now_iso()
        with self._connect() as conn:
            cur = conn.execute(
                f"UPDATE leads SET {assignments} WHERE id = :id", values
            )
            return cur.rowcount > 0

    def delete(self, lead_id: str) -> bool:
        with self._connect() as conn:
            cur1 = conn.execute(
                "DELETE FROM lead_lifecycle_events WHERE lead_id = ?", (lead_id,)
            )
            cur2 = conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            return cur2.rowcount > 0

    # ------------------------------------------------------------------
    # Bulk
    # ------------------------------------------------------------------
    def bulk_insert(self, records: List[LeadRecord]) -> List[str]:
        columns = ", ".join(_COLUMNS)
        placeholders = ", ".join(f":{c}" for c in _COLUMNS)
        sql = f"INSERT INTO leads ({columns}) VALUES ({placeholders})"
        ids: List[str] = []
        with self._connect() as conn:
            for record in records:
                try:
                    conn.execute(sql, {c: record.get(c) for c in _COLUMNS})
                    ids.append(record["id"])
                except sqlite3.IntegrityError as exc:
                    if "UNIQUE constraint failed" in str(exc):
                        raise DuplicateLeadError(record["id"]) from exc
                    raise
        return ids

    def bulk_update(self, records: List[Tuple[str, LeadRecord]]) -> int:
        changed = 0
        assignments = ", ".join(f"{c} = :{c}" for c in _COLUMNS if c not in ("id", "created_at"))
        with self._connect() as conn:
            for lead_id, record in records:
                values = {c: record.get(c) for c in _COLUMNS}
                values["id"] = lead_id
                values["updated_at"] = _utc_now_iso()
                cur = conn.execute(
                    f"UPDATE leads SET {assignments} WHERE id = :id", values
                )
                changed += cur.rowcount
        return changed

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------
    def _build_where(self, q: LeadQuery) -> Tuple[str, List]:
        clauses, params = [], []
        if q.lifecycle:
            clauses.append("lifecycle = ?"); params.append(q.lifecycle)
        if q.quality_tier:
            clauses.append("quality_tier = ?"); params.append(q.quality_tier)
        if q.company_name:
            clauses.append("LOWER(company_name) = LOWER(?)") ; params.append(q.company_name)
        if q.min_score is not None:
            clauses.append("COALESCE(score, 0) >= ?"); params.append(q.min_score)
        if q.max_score is not None:
            clauses.append("COALESCE(score, 0) <= ?"); params.append(q.max_score)
        if q.has_email is True:
            clauses.append("emails_json NOT IN ('[]', '') AND emails_json IS NOT NULL")
        elif q.has_email is False:
            clauses.append("(emails_json IN ('[]', '') OR emails_json IS NULL)")
        if q.has_website is True:
            clauses.append("website IS NOT NULL AND website != ''")
        elif q.has_website is False:
            clauses.append("(website IS NULL OR website = '')")
        if q.sources:
            # sources are comma-separated inside provenance_json.source
            src_cols = ["LOWER(provenance_json) LIKE ?" for _ in q.sources]
            clauses.append("(" + " OR ".join(src_cols) + ")")
            params.extend(f"%{s.lower()}%" for s in q.sources)
        if q.search_text:
            needle = f"%{q.search_text.lower()}%"
            clauses.append(
                "(LOWER(COALESCE(company_name,'')) LIKE ? OR "
                "LOWER(COALESCE(website,'')) LIKE ? OR "
                "LOWER(COALESCE(description,'')) LIKE ?)"
            )
            params.extend([needle, needle, needle])
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return where, params

    def find(self, query: LeadQuery) -> Tuple[List[LeadRecord], int]:
        where, params = self._build_where(query)

        col = query.order_by if query.order_by in _SORTABLE else "created_at"
        direction = "DESC" if query.descending else "ASC"
        order_sql = f"ORDER BY {col} {direction}, id {direction}"

        page = max(query.page, 1)
        per = max(query.per_page, 1)
        offset = (page - 1) * per

        with self._connect() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) AS n FROM leads{where}", params
            ).fetchone()
            total = total_row["n"] if total_row else 0

            rows = conn.execute(
                f"SELECT * FROM leads{where} {order_sql} LIMIT ? OFFSET ?",
                [*params, per, offset],
            ).fetchall()

        return [self._row_to_record(r) for r in rows], total

    def count(self, query: Optional[LeadQuery] = None) -> int:
        if query is None:
            where, params = "", []
        else:
            where, params = self._build_where(query)
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) AS n FROM leads{where}", params
            ).fetchone()
            return int(row["n"]) if row else 0

    def exists_domain(self, canonical_domain: str) -> bool:
        if not canonical_domain:
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM leads WHERE LOWER(COALESCE(canonical_domain,'')) = LOWER(?) LIMIT 1",
                (canonical_domain,),
            ).fetchone()
            return row is not None

    # ------------------------------------------------------------------
    # Lifecycle audit trail
    # ------------------------------------------------------------------
    def set_lifecycle(
        self, lead_id: str, new_state: str, reason: Optional[str] = None
    ) -> Tuple[Optional[str], bool]:
        now = _utc_now_iso()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT lifecycle FROM leads WHERE id = ?", (lead_id,)
            ).fetchone()
            if row is None:
                return None, False
            old_state = row["lifecycle"]

            conn.execute(
                "UPDATE leads SET lifecycle = ?, lifecycle_updated_at = ?, updated_at = ? WHERE id = ?",
                (new_state, now, now, lead_id),
            )
            conn.execute(
                """
                INSERT INTO lead_lifecycle_events
                    (lead_id, from_state, to_state, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (lead_id, old_state, new_state, reason, now),
            )
            return old_state, old_state != new_state

    def get_lifecycle_history(self, lead_id: str) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT lead_id, from_state, to_state, reason, created_at
                FROM lead_lifecycle_events
                WHERE lead_id = ?
                ORDER BY id
                """,
                (lead_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> LeadRecord:
        rec = {k: row[k] for k in _COLUMNS}
        return rec

    def close(self) -> None:
        # SQLite connections are opened/closed per operation; nothing held.
        return None