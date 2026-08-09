"""InMemoryStore — Phase 19B.

Dict-backed LeadStore.  Used for unit tests and as a reference implementation
of the abstract contract; intentionally free of any SQL or I/O.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ..exceptions import DuplicateLeadError
from ..models import LeadRecord
from .base import LeadQuery, LeadStore


_SORTABLE = {"created_at", "updated_at", "score", "company_name"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class InMemoryStore(LeadStore):
    """Simple dict-backed store guarded by a lock for thread safety."""

    def __init__(self) -> None:
        self._records: Dict[str, LeadRecord] = {}
        self._history: Dict[str, List[Dict]] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def insert(self, record: LeadRecord) -> str:
        with self._lock:
            lid = record["id"]
            if lid in self._records:
                raise DuplicateLeadError(lid)
            self._records[lid] = dict(record)
            return lid

    def get(self, lead_id: str) -> Optional[LeadRecord]:
        with self._lock:
            rec = self._records.get(lead_id)
            return dict(rec) if rec is not None else None

    def update(self, lead_id: str, record: LeadRecord) -> bool:
        with self._lock:
            if lead_id not in self._records:
                return False
            new_rec = dict(record)
            new_rec["id"] = lead_id
            if "created_at" not in new_rec or not new_rec["created_at"]:
                new_rec["created_at"] = self._records[lead_id].get(
                    "created_at", _utc_now_iso()
                )
            new_rec["updated_at"] = _utc_now_iso()
            self._records[lead_id] = new_rec
            return True

    def delete(self, lead_id: str) -> bool:
        with self._lock:
            removed = self._records.pop(lead_id, None) is not None
            self._history.pop(lead_id, None)
            return removed

    # ------------------------------------------------------------------
    # Bulk
    # ------------------------------------------------------------------
    def bulk_insert(self, records: List[LeadRecord]) -> List[str]:
        with self._lock:
            ids: List[str] = []
            for record in records:
                lid = record["id"]
                if lid in self._records:
                    raise DuplicateLeadError(lid)
                self._records[lid] = dict(record)
                ids.append(lid)
            return ids

    def bulk_update(self, records: List[Tuple[str, LeadRecord]]) -> int:
        changed = 0
        with self._lock:
            for lead_id, record in records:
                if self.update(lead_id, record):
                    changed += 1
        return changed

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------
    def _matches(self, rec: LeadRecord, q: LeadQuery) -> bool:
        if q.lifecycle and rec.get("lifecycle") != q.lifecycle:
            return False
        if q.quality_tier and rec.get("quality_tier") != q.quality_tier:
            return False
        if q.company_name and (
            (rec.get("company_name") or "").lower() != q.company_name.lower()
        ):
            return False

        if q.min_score is not None and (rec.get("score") or 0) < q.min_score:
            return False
        if q.max_score is not None and (rec.get("score") or 0) > q.max_score:
            return False

        if q.has_email is not None:
            has = bool(json.loads(rec.get("emails_json") or "[]"))
            if has != q.has_email:
                return False
        if q.has_website is not None:
            has = bool(rec.get("website"))
            if has != q.has_website:
                return False

        if q.sources:
            prov_raw = rec.get("provenance_json") or "{}"
            sources_str = (json.loads(prov_raw).get("source") or "").lower()
            prov_parts = {p.strip() for p in sources_str.split(",") if p.strip()}
            needed = {s.strip().lower() for s in q.sources}
            if not prov_parts.intersection(needed):
                return False

        if q.search_text:
            needle = q.search_text.lower()
            hay = " ".join(
                filter(None, [
                    rec.get("company_name") or "",
                    rec.get("website") or "",
                    rec.get("description") or "",
                ])
            ).lower()
            if needle not in hay:
                return False

        return True

    def find(self, query: LeadQuery) -> Tuple[List[LeadRecord], int]:
        with self._lock:
            rows = [r for r in self._records.values() if self._matches(r, query)]
            total = len(rows)

            key = query.order_by if query.order_by in _SORTABLE else "created_at"
            rows.sort(
                key=lambda r: (r.get(key) is None, r.get(key)),
                reverse=query.descending,
            )

            page = max(query.page, 1)
            per = max(query.per_page, 1)
            start = (page - 1) * per
            return [dict(r) for r in rows[start:start + per]], total

    def count(self, query: Optional[LeadQuery] = None) -> int:
        if query is None:
            return len(self._records)
        _, total = self.find(
            LeadQuery(
                lifecycle=query.lifecycle,
                min_score=query.min_score,
                max_score=query.max_score,
                quality_tier=query.quality_tier,
                sources=query.sources,
                has_email=query.has_email,
                has_website=query.has_website,
                company_name=query.company_name,
                search_text=query.search_text,
                page=1, per_page=10**9,
            )
        )
        return total

    def exists_domain(self, canonical_domain: str) -> bool:
        target = (canonical_domain or "").lower()
        if not target:
            return False
        with self._lock:
            return any(
                (r.get("canonical_domain") or "").lower() == target
                for r in self._records.values()
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def set_lifecycle(
        self, lead_id: str, new_state: str, reason: Optional[str] = None
    ) -> Tuple[Optional[str], bool]:
        with self._lock:
            rec = self._records.get(lead_id)
            if rec is None:
                return None, False

            old = rec.get("lifecycle")
            rec["lifecycle"] = new_state
            rec["lifecycle_updated_at"] = _utc_now_iso()
            rec["updated_at"] = _utc_now_iso()

            self._history.setdefault(lead_id, []).append({
                "lead_id": lead_id,
                "from_state": old,
                "to_state": new_state,
                "reason": reason,
                "created_at": _utc_now_iso(),
            })
            return old, old != new_state

    def get_lifecycle_history(self, lead_id: str) -> List[Dict]:
        with self._lock:
            return list(self._history.get(lead_id, []))
