"""
Guru Normalizer.

Maps raw candidates from GuruDiscoveryProvider into canonical UnifiedLead format.
"""

from __future__ import annotations
from datetime import datetime, UTC
from typing import Any

from .base import BaseNormalizer
from ..model import UnifiedLead, LocationData, Provenance
from ..query import RawCandidate, DiscoveryQuery
from .registry import default_registry

class GuruNormalizer(BaseNormalizer):
    def normalize(self, candidate: RawCandidate, query: DiscoveryQuery) -> UnifiedLead:
        payload = candidate.payload

        title = payload.get("company_name") or payload.get("title") or "Guru Buyer Client"
        url = payload.get("website") or payload.get("source_url") or "https://www.guru.com"
        snippet = payload.get("summary") or payload.get("description") or ""

        location = LocationData()
        if query.location:
            location.country = query.location

        provenance = Provenance(
            source="guru",
            source_url=url,
            discovered_at=datetime.now(UTC),
            discovery_query={"industry": query.industry, "location": query.location},
            raw_ref="guru_scraper"
        )

        return UnifiedLead(
            company_name=title,
            website=url,
            description=snippet,
            location=location,
            provenance=provenance
        )

default_registry.register("guru", GuruNormalizer())
