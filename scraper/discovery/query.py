"""Discovery query and batch value objects.

Phase 16A — framework definitions only.

These are the *input* and *output* containers for every DiscoveryProvider.
They contain no I/O and no business logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional


@dataclass
class DiscoveryQuery:
    """The single input every discovery provider receives."""

    industry: str
    location: str
    keywords: List[str] = field(default_factory=list)
    max_results: int = 20
    filters: Dict[str, Any] = field(default_factory=dict)
    cursor: Optional[str] = None  # opaque pagination token; None = first page


@dataclass
class RawCandidate:
    """One un-normalized item as returned directly by a provider.

    The provider's Normalizer converts each RawCandidate into a UnifiedLead.
    `payload` holds the provider-native dict (or raw text) untouched.
    """

    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class SourceMeta:
    """Per-provider execution metadata returned alongside a batch."""

    source: str = ""
    request_count: int = 0
    rate_limit_remaining: Optional[int] = None
    cost_credits: Optional[float] = None
    page: Optional[int] = None


@dataclass
class DiscoveryBatch:
    """The result of one provider's discover() call."""

    source: str
    candidates: List[RawCandidate] = field(default_factory=list)
    next_cursor: Optional[str] = None
    meta: SourceMeta = field(default_factory=SourceMeta)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
