"""
Upwork Normalizer.

Maps raw candidates from UpworkDiscoveryProvider into canonical UnifiedLead format.
"""

from __future__ import annotations
from datetime import datetime, UTC
from typing import Any

from .base import BaseNormalizer
from ..model import UnifiedLead, LocationData, Provenance
from .registry import default_registry

class UpworkNormalizer(BaseNormalizer):
    """
    Concrete normalizer for leads discovered via Upwork scraper.
    """

    def normalize(self, candidate: RawCandidate, query: DiscoveryQuery) -> UnifiedLead:
        payload = candidate.payload

        title = payload.get("job_title") or payload.get("company_name") or payload.get("company") or payload.get("title") or "Upwork Buyer Client"
        url = payload.get("job_url") or payload.get("url") or payload.get("website") or payload.get("source_url") or "https://www.upwork.com"
        snippet = payload.get("job_description") or payload.get("summary") or payload.get("description") or ""

        location = LocationData()
        if query.location:
            location.country = query.location

        provenance = Provenance(
            source=candidate.source or "upwork",
            source_url=url,
            discovered_at=datetime.now(UTC),
            discovery_query={"industry": query.industry, "location": query.location},
            raw_ref="upwork_scraper"
        )

        return UnifiedLead(
            company_name=title,
            website=url,
            description=snippet,
            location=location,
            provenance=provenance
        )

default_registry.register("upwork", UpworkNormalizer())
