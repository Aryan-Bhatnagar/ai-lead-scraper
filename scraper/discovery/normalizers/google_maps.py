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
        website = payload.get("website", "").strip()
        description = payload.get("description", "").strip()

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
            website=website,
            description=description,
            location=location,
            provenance=provenance,
        )

        # Maps-specific enrichment fields
        maps_rating = payload.get("rating")
        if maps_rating is not None:
            lead.maps_rating = maps_rating
        reviews = payload.get("reviews")
        if reviews is not None:
            lead.maps_review_count = reviews

        # Handle phones - could be from Google Maps or website enrichment
        phone = payload.get("phone")
        if phone:
            lead.phones.append(phone)

        # Handle emails from website enrichment
        emails = payload.get("emails", [])
        if emails:
            lead.emails.extend(emails)

        # Handle social links from website enrichment
        socials = payload.get("socials", {})
        if socials:
            lead.socials.update(socials)

        # Handle about and contact pages
        about_page = payload.get("about_page")
        if about_page:
            lead.about_page = about_page
        contact_page = payload.get("contact_page")
        if contact_page:
            lead.contact_page = contact_page

        # Handle categories/types
        categories = payload.get("category", [])
        if categories:
            lead.categories.extend(categories)

        place_id = payload.get("place_id")
        if place_id:
            lead.external_ids["google_places_id"] = place_id

        return lead


# Register the normalizer
default_registry.register("google_maps", GoogleMapsNormalizer())
