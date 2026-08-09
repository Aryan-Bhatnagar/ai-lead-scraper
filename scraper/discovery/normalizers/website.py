"""
Website Discovery Normalizer.

Maps raw deep-scrape data from the WebsiteDiscoveryProvider
into the canonical UnifiedLead format.
"""

from __future__ import annotations
from datetime import datetime, UTC
from typing import Any

from .base import BaseNormalizer
from ..model import UnifiedLead, LocationData, Provenance
from ..query import RawCandidate, DiscoveryQuery
from .registry import default_registry

class WebsiteNormalizer(BaseNormalizer):
    """
    Concrete normalizer for leads enriched via deep website scraping.
    """

    def normalize(self, candidate: RawCandidate, query: DiscoveryQuery) -> UnifiedLead:
        """
        Transforms a RawCandidate from website_discovery into a UnifiedLead.
        """
        payload = candidate.payload

        # 1. Extract core fields
        company_name = payload.get("company_name", "").strip()
        website = payload.get("website", "").strip()
        description = payload.get("company_description", payload.get("description", "")).strip()
        industry = payload.get("industry", "").strip()
        
        # 2. Location handling
        location = LocationData()
        location.city = payload.get("city", "").strip()
        location.country = payload.get("country", "").strip()
        if not location.city and not location.country and query.location:
            location.country = query.location

        # 3. Provenance
        # website_discovery provider usually includes _provenance and _source_pages
        prov_data = payload.get("_provenance", {})
        
        provenance = Provenance(
            source=candidate.source,
            source_url=website,
            discovered_at=datetime.now(UTC), # Or from a timestamp if available in payload
            discovery_query={"industry": query.industry, "location": query.location},
            raw_ref="website_deep_scrape"
        )

        # 4. Create UnifiedLead
        lead = UnifiedLead(
            company_name=company_name,
            website=website,
            description=description,
            industry=industry,
            location=location,
            provenance=provenance
        )

        # Map contact fields from the deep scrape payload
        # Email and phone are already validated by the scraping logic
        if payload.get("email"):
            lead.emails = [payload["email"]]
        if payload.get("phone"):
            lead.phones = [payload["phone"]]

        # Map social profiles - the field from scrape_site is "socials" not "social_links"
        socials = payload.get("socials", {})
        if socials:
            lead.socials = socials

        return lead

# Register the normalizer
default_registry.register("website_discovery", WebsiteNormalizer())
