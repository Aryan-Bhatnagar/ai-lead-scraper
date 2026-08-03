"""
Google Maps Discovery Provider.

Adapter that exposes ``scraper.google_maps_discovery.discover_google_maps``
through the unified :class:`DiscoveryProvider` interface (Phase 19A).

The provider intentionally performs no normalization of its own — raw
payloads are wrapped into RawCandidate items and handed to the
``google_maps`` normalizer.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import List

from ..provider import DiscoveryProvider, CapabilitySet
from ..query import DiscoveryQuery, DiscoveryBatch, RawCandidate, SourceMeta


class GoogleMapsDiscoveryProvider(DiscoveryProvider):
    """Discover businesses via the Google Places Text Search API."""

    name = "google_maps"
    source_type = "api"
    requires_api_key = True  # GOOGLE_MAPS_API_KEY environment variable

    capabilities = CapabilitySet(
        can_provide_website=False,
        can_provide_email=False,
        can_provide_phone=False,
        can_provide_rating=True,
        can_provide_review_count=True,
        can_provide_coordinates=False,
        can_provide_business_hours=False,
        can_provide_social_links=False,
        can_provide_categories=False,
        custom={"place_id", "google_maps_url"},
    )

    def discover(self, query: DiscoveryQuery) -> DiscoveryBatch:
        """Run Text Search discovery and wrap results into RawCandidate items.

        Delegates the HTTP work to ``scraper.google_maps_discovery`` so this
        adapter stays free of provider internals.
        """
        # Imported lazily so the module (and the default registry) stay
        # importable even when requests / the API key are unavailable.
        from ...google_maps_discovery import discover_google_maps

        results = discover_google_maps(
            industry=query.industry,
            location=query.location,
            max_results=query.max_results,
        )

        candidates: List[RawCandidate] = [
            RawCandidate(
                payload=r,
                source=self.name,
                fetched_at=datetime.now(UTC),
            )
            for r in results
        ]

        return DiscoveryBatch(
            source=self.name,
            candidates=candidates,
            meta=SourceMeta(source=self.name, request_count=1),
        )
