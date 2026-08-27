"""
LinkedIn Normalizer.

Maps raw candidates from LinkedInDiscoveryProvider into canonical UnifiedLead format.
"""

from __future__ import annotations
from datetime import datetime, UTC
from typing import Any

from .base import BaseNormalizer
from ..model import UnifiedLead, LocationData, Provenance
from ..query import RawCandidate, DiscoveryQuery
from .registry import default_registry

class LinkedInNormalizer(BaseNormalizer):
    def normalize(self, candidate: RawCandidate, query: DiscoveryQuery) -> UnifiedLead:
        payload = candidate.payload

        title = payload.get("company_name") or payload.get("title") or "LinkedIn Hiring Feed"
        url = payload.get("website") or payload.get("source_url") or "https://www.linkedin.com"
        snippet = payload.get("summary") or payload.get("description") or ""

        location = LocationData()
        if query.location:
            location.country = query.location

        provenance = Provenance(
            source="linkedin",
            source_url=url,
            discovered_at=datetime.now(UTC),
            discovery_query={"industry": query.industry, "location": query.location},
            raw_ref="linkedin_scraper"
        )

        return UnifiedLead(
            company_name=title,
            website=url,
            description=snippet,
            location=location,
            provenance=provenance
        )

default_registry.register("linkedin", LinkedInNormalizer())
