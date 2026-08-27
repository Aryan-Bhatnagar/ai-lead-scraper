"""
PeoplePerHour Normalizer.

Maps candidates from PeoplePerHourDiscoveryProvider into canonical UnifiedLead format.
"""

from __future__ import annotations
from datetime import datetime, UTC
from typing import Any

from .base import BaseNormalizer
from ..model import UnifiedLead, LocationData, Provenance
from ..query import RawCandidate, DiscoveryQuery
from .registry import default_registry

class PeoplePerHourNormalizer(BaseNormalizer):
    """Concrete normalizer for leads discovered via PeoplePerHour.com."""

    def normalize(self, candidate: RawCandidate, query: DiscoveryQuery) -> UnifiedLead:
        payload = candidate.payload

        title = payload.get("title") or payload.get("company_name") or "PeoplePerHour Active Job"
        url = payload.get("website") or payload.get("source_url") or "https://www.peopleperhour.com"
        snippet = payload.get("summary") or payload.get("description") or ""

        location = LocationData()
        if query.location:
            location.country = query.location

        provenance = Provenance(
            source=candidate.source or "peopleperhour",
            source_url=url,
            discovered_at=datetime.now(UTC),
            discovery_query={"industry": query.industry, "location": query.location},
            raw_ref="peopleperhour_search"
        )

        comp_name = title if title.startswith("PeoplePerHour") else f"PeoplePerHour Client: {title}"

        return UnifiedLead(
            company_name=comp_name,
            website=url,
            description=snippet,
            industry=query.industry or payload.get("service") or "Software & IT",
            location=location,
            provenance=provenance,
            ai_summary=payload.get("ai_summary") or payload.get("summary"),
            outreach_strategy=payload.get("outreach_strategy"),
            buying_signals=payload.get("buying_signals"),
            recommended_service=payload.get("recommended_service") or query.industry
        )

default_registry.register("peopleperhour", PeoplePerHourNormalizer())
