"""
Google Maps Normalizer.

Maps raw payloads from the GoogleMapsDiscoveryProvider (Google Places Text
Search results) into the canonical UnifiedLead format.
"""

from __future__ import annotations
from datetime import datetime, UTC

from .base import BaseNormalizer
from ..model import UnifiedLead, LocationData, Provenance
from ..query import RawCandidate, DiscoveryQuery
from .registry import default_registry


class GoogleMapsNormalizer(BaseNormalizer):
    """Concrete normalizer for leads discovered via Google Maps / Places."""

    def normalize(self, candidate: RawCandidate, query: DiscoveryQuery) -> UnifiedLead:
        payload = candidate.payload

        company_name = (payload.get("company_name") or "").strip()
        address = (payload.get("address") or "").strip()

        location = LocationData(address=address or None)
        if query.location:
            location.country = query.location

        provenance = Provenance(
            source=candidate.source,
            source_url=payload.get("google_maps_url"),
            discovered_at=datetime.now(UTC),
            discovery_query={"industry": query.industry, "location": query.location},
            raw_ref=payload.get("place_id"),
        )

        lead = UnifiedLead(
            company_name=company_name,
            website=payload.get("website"),
            location=location,
            provenance=provenance,
        )

        # Maps-specific enrichment fields
        maps_rating = payload.get("rating")
        if maps_rating is not None:
            lead.maps_rating = maps_rating
        reviews = payload.get("reviews_count")
        if reviews is not None:
            lead.maps_review_count = reviews
        phone = payload.get("phone")
        if phone:
            lead.phones.append(phone)
        place_id = payload.get("place_id")
        if place_id:
            lead.external_ids["google_places_id"] = place_id

        return lead


# Register the normalizer
default_registry.register("google_maps", GoogleMapsNormalizer())
