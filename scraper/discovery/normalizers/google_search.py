"""
Google Search Normalizer.

Maps raw search results from the GoogleSearchDiscoveryProvider
into the canonical UnifiedLead format.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any

from .base import BaseNormalizer
from ..model import UnifiedLead, LocationData, Provenance
from ..query import RawCandidate, DiscoveryQuery
from .registry import default_registry

class GoogleSearchNormalizer(BaseNormalizer):
    """
    Concrete normalizer for leads discovered via Google Search.
    """

    def normalize(self, candidate: RawCandidate, query: DiscoveryQuery) -> UnifiedLead:
        """
        Transforms a RawCandidate from google_search into a UnifiedLead.
        """
        payload = candidate.payload

        # Extract fields from the payload (Canonical Search Result schema)
        title = payload.get("title", "").strip()
        url = payload.get("url", "").strip()
        snippet = payload.get("snippet", "").strip()
        source_engine = payload.get("source_engine", "unknown")
        search_query = payload.get("query", "")
        timestamp = payload.get("timestamp") or datetime.utcnow().isoformat()

        # Basic Location Extraction from snippet/title (Optional heuristic)
        # In a real scenario, we might use an LLM or NER here.
        location = LocationData()
        if query.location:
            location.country = query.location # Assume location query matches lead location

        # Build Provenance
        provenance = Provenance(
            source=candidate.source,
            source_url=url,
            discovered_at=datetime.fromisoformat(timestamp) if timestamp else None,
            discovery_query={"industry": query.industry, "location": query.location},
            raw_ref=f"search_{source_engine}"
        )

        # Create UnifiedLead
        return UnifiedLead(
            company_name=title,
            website=url,
            description=snippet,
            location=location,
            provenance=provenance
        )

# Register the normalizer
default_registry.register("google_search", GoogleSearchNormalizer())
