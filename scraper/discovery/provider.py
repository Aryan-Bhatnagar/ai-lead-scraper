"""Abstract base class for all discovery providers.

Phase 16A — framework definitions only.

This file defines the contract every discovery provider must fulfil.
No concrete provider classes exist here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Set

from .query import DiscoveryQuery, DiscoveryBatch


@dataclass
class CapabilitySet:
    """Declares which UnifiedLead fields this provider can reliably populate."""

    can_provide_website: bool = False
    can_provide_email: bool = False
    can_provide_phone: bool = False
    can_provide_rating: bool = False
    can_provide_review_count: bool = False
    can_provide_coordinates: bool = False
    can_provide_business_hours: bool = False
    can_provide_social_links: bool = False
    can_provide_categories: bool = False
    custom: Set[str] = field(default_factory=set)  # e.g. {"upwork_jobs_completed"}


@dataclass
class ProviderResponse:
    """Lightweight wrapper returned by providers on partial failure."""

    batch: Optional[DiscoveryBatch] = None
    error: Optional[str] = None
    status: str = "success"  # "success" | "failed" | "no_data"


class DiscoveryProvider(ABC):
    """Abstract contract for every lead-source adapter.

    Subclasses must:
      1. Declare a unique ``name``.
      2. Declare their ``capabilities``.
      3. Implement ``discover()`` to accept a DiscoveryQuery and return a
         DiscoveryBatch containing RawCandidate items.

    They must NOT write to the database.  Persistence is the engine's job.
    """

    name: str
    source_type: str = "api"          # "api" | "scrape" | "actor"
    requires_api_key: bool = False
    capabilities: CapabilitySet = field(default_factory=CapabilitySet)

    @abstractmethod
    def discover(self, query: DiscoveryQuery) -> DiscoveryBatch:
        """Run discovery and return a batch of raw, un-normalized candidates.

        The returned batch must contain RawCandidate items whose
        ``payload`` holds the provider-native dict.  Normalization to
        UnifiedLead happens in the normalizer layer, not here.

        Parameters
        ----------
        query:
            The single input object every provider understands.

        Returns
        -------
        DiscoveryBatch
            Even on total failure the batch may be empty rather than raising.
            Provider-level failures should produce ``ProviderDiscoveryResponse``
            semantics instead of exceptions (mirroring the enrichment pattern).
        """
        ...
