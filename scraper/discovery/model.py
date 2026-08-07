"""Model classes for the Unified Lead Discovery framework.

Phase 16A — framework definitions only.  Contains the canonical data model
every discovery provider maps into before persistence.

No business logic, no I/O, no database imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class LocationData:
    """Structured geo/address information for a lead."""

    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None


@dataclass
class Provenance:
    """Where and how this particular candidate was found."""

    source: str = ""                       # provider name, e.g. "google_maps"
    source_url: Optional[str] = None       # platform-native URL (listing, profile)
    discovered_at: Optional[datetime] = None
    discovery_query: Optional[Dict[str, Any]] = None
    confidence: float = 1.0
    raw_ref: Optional[str] = None          # pointer into a raw-payload store


@dataclass
class UnifiedLead:
    """The single normalized schema every discovery provider returns.

    Fields are grouped into logical clusters.  Any field may be omitted
    (None or empty) by the source — the schema does not force providers to
    fabricate data they cannot supply.
    """

    # --- Identity ---
    id: Optional[str] = None
    canonical_domain: Optional[str] = None
    company_name_norm: Optional[str] = None
    external_ids: Dict[str, str] = field(default_factory=dict)

    @property
    def lead_id(self) -> Optional[str]:
        """Alias for ``id`` to match legacy test expectations."""
        return self.id

    # --- Core ---
    company_name: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    location: LocationData = field(default_factory=LocationData)
    lifecycle: Optional[LifecycleState] = None

    # --- Contact ---
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    socials: Dict[str, Optional[str]] = field(default_factory=dict)
    contact_name: Optional[str] = None
    contact_role: Optional[str] = None

    # --- Marketplace (freelance platforms) ---
    hourly_rate: Optional[float] = None
    skills: List[str] = field(default_factory=list)
    rating: Optional[float] = None
    jobs_completed: Optional[int] = None

    # --- Maps (Google Maps) ---
    maps_rating: Optional[float] = None
    maps_review_count: Optional[int] = None
    coordinates: Optional[Dict[str, float]] = None  # {"lat": ..., "lng": ...}
    business_status: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    address: Optional[str] = None
    google_rating: Optional[float] = None

    # --- Provenance ---
    provenance: Provenance = field(default_factory=Provenance)

    # --- Metadata (for import adapters and enrichment) ---
    metadata: Dict[str, Any] = field(default_factory=dict)
