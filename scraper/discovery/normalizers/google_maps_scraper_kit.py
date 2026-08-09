"""
Normalizer for the Google Maps Scraper Kit results.
"""

from __future__ import annotations
from typing import Any, Dict
from ..normalizers.base import BaseNormalizer
from ..model import UnifiedLead
from ..query import RawCandidate, DiscoveryQuery

class GoogleMapsScraperKitNormalizer(BaseNormalizer):
    """
    Maps raw payloads from the Google Maps Scraper Kit to the UnifiedLead model.
    """

    def normalize(self, candidate: RawCandidate, query: DiscoveryQuery) -> UnifiedLead:
        payload: Dict[str, Any] = candidate.payload

        # Mapping logic based on the Scraper Kit result schema
        # Result fields: name, phone, email, website, category, address, rating, review_count, lat, lng

        lead = UnifiedLead(
            company_name=payload.get("name") or "Unknown",
            website=payload.get("website"),
            industry=payload.get("category"),
            location=LocationData(
                address=payload.get("address"),
            ),
        )

        if payload.get("email"):
            lead.emails = [payload.get("email")]

        if payload.get("phone"):
            lead.phones = [payload.get("phone")]

        if payload.get("category"):
            lead.categories = [payload.get("category")]

        lead.maps_rating = payload.get("rating")
        lead.maps_review_count = payload.get("review_count")

        if "lat" in payload and "lng" in payload:
            lead.coordinates = {"lat": payload["lat"], "lng": payload["lng"]}

        # Provenance
        lead.provenance = Provenance(
            source=candidate.source,
            discovered_at=candidate.fetched_at,
            discovery_query=query.__dict__ if hasattr(query, '__dict__') else {},
            raw_ref=candidate.payload.get("job_id")
        )

        return lead
