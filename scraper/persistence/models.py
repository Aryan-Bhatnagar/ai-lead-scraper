"""Domain value objects for the Lead Repository — Phase 19B.

Everything here is a pure data container: no I/O, no SQL, no provider imports.
The ``LeadRecord`` alias (``dict``) is the DTO exchanged with LeadStores; it
deliberately has no behavioural requirements so *any* backend can produce it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from math import ceil
from typing import Any, Dict, Generic, List, Optional, TypeVar


# ---------------------------------------------------------------------------
# Record DTO
# ---------------------------------------------------------------------------

# A LeadRecord is the plain-dict representation a LeadStore understands.
# Keys are defined by ``scraper.persistence.mappers.lead_to_record``.
LeadRecord = Dict[str, Any]


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

_T = TypeVar("_T")


@dataclass
class Page(Generic[_T]):
    """One slice of a filtered/ordered result set plus navigation metadata."""

    items: List[_T] = field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 50

    @property
    def pages(self) -> int:
        """Total page count; 0 when there are no items at all."""
        if self.per_page <= 0:
            return 0
        return ceil(self.total / self.per_page) if self.total else 0

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


# ---------------------------------------------------------------------------
# Lifecycle audit event
# ---------------------------------------------------------------------------

@dataclass
class LifecycleEvent:
    """One entry in a lead's lifecycle audit trail."""

    lead_id: str
    to_state: "LifecycleState"
    from_state: Optional["LifecycleState"] = None
    reason: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        # Late import to avoid a cycle with lifecycle.py.
        from .lifecycle import LifecycleState

        if isinstance(self.to_state, str):
            self.to_state = LifecycleState(self.to_state)
        if isinstance(self.from_state, str):
            self.from_state = LifecycleState(self.from_state)


# Re-export for convenient `from .models import LifecycleState`
from .lifecycle import LifecycleState  # noqa: E402
