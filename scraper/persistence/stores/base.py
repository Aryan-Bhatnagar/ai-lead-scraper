"""LeadStore abstract base + LeadQuery value object — Phase 19B.

A LeadStore is a *dumb persistence engine*: it saves, fetches, updates and
deletes ``LeadRecord`` dicts.  It knows nothing about ``UnifiedLead``,
scoring, transitions, or HTTP — those belong to the repository layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..models import LeadRecord


@dataclass
class LeadQuery:
    """Backend-neutral filter/sort/paginate description.

    All fields optional; the meaning matches :meth:`LeadRepository.filter`.
    ``search_text`` is a case-insensitive substring match over
    company_name / website / description.
    """

    lifecycle: Optional[str] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    quality_tier: Optional[str] = None
    sources: Optional[List[str]] = None
    has_email: Optional[bool] = None
    has_website: Optional[bool] = None
    company_name: Optional[str] = None
    search_text: Optional[str] = None
    order_by: str = "created_at"   # created_at | updated_at | score | company_name
    descending: bool = True
    page: int = 1
    per_page: int = 50


class LeadStore(ABC):
    """Storage abstraction behind :class:`LeadRepository`."""

    # ------------------------------------------------------------------
    # Single-row operations
    # ------------------------------------------------------------------
    @abstractmethod
    def insert(self, record: LeadRecord) -> str:
        """Insert a new record; return its id.  Raise DuplicateLeadError."""

    @abstractmethod
    def get(self, lead_id: str) -> Optional[LeadRecord]:
        """Fetch one record by id, or ``None``."""

    @abstractmethod
    def update(self, lead_id: str, record: LeadRecord) -> bool:
        """Full overwrite of an existing record.  False when id missing."""

    @abstractmethod
    def delete(self, lead_id: str) -> bool:
        """Delete one record.  False when id missing."""

    # ------------------------------------------------------------------
    # Bulk
    # ------------------------------------------------------------------
    @abstractmethod
    def bulk_insert(self, records: List[LeadRecord]) -> List[str]:
        """Insert many; return ids (order matches input)."""

    @abstractmethod
    def bulk_update(self, records: List[Tuple[str, LeadRecord]]) -> int:
        """Update many; return number of rows actually changed."""

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @abstractmethod
    def find(self, query: LeadQuery) -> Tuple[List[LeadRecord], int]:
        """Return (records, total_count) respecting filters + pagination."""

    @abstractmethod
    def count(self, query: Optional[LeadQuery] = None) -> int:
        """Number of records matching ``query`` (or all when ``None``)."""

    @abstractmethod
    def exists_domain(self, canonical_domain: str) -> bool:
        """Cheap uniqueness probe: any record with this domain already."""

    # ------------------------------------------------------------------
    # Lifecycle audit trail
    # ------------------------------------------------------------------
    @abstractmethod
    def set_lifecycle(
        self, lead_id: str, new_state: str, reason: Optional[str] = None
    ) -> Tuple[Optional[str], bool]:
        """Set ``lifecycle`` on a record and append an audit event.

        Returns ``(previous_state, changed)`` — ``previous_state`` is the
        state before the update, or ``None`` when the lead does not exist
        (``changed`` then ``False``).
        """

    @abstractmethod
    def get_lifecycle_history(self, lead_id: str) -> List[Dict]:
        """All LifecycleEvent dicts for a lead, oldest first."""

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------
    def close(self) -> None:  # default no-op — backends may override
        """Release any resources the store holds."""

    # ------------------------------------------------------------------
    # Convenience — iterate everything (diagnostics / migrations)
    # ------------------------------------------------------------------
    def iter_all(self, batch: int = 200):
        """Yield every record, ``batch`` at a time, regardless of filters."""
        from itertools import count

        for page in count(1):
            records, _ = self.find(LeadQuery(page=page, per_page=batch))
            if not records:
                return
            yield from records
