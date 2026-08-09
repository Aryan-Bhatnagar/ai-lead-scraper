"""
Website Discovery Provider.

Adapts the existing multi-page scraping logic from `scraper/scrape_leads.py`
into the Discovery Framework.
"""

from __future__ import annotations
from datetime import datetime, UTC

from dateutil.tz import UTC
fetched_at=datetime.now(UTC)
from typing import List

from ..provider import DiscoveryProvider, CapabilitySet
from ..query import DiscoveryQuery, DiscoveryBatch, RawCandidate, SourceMeta
from ...scrape_leads import scrape_site

class WebsiteDiscoveryProvider(DiscoveryProvider):
    """
    Adapter that enables the discovery engine to use the deep website scraping
    pipeline.
    """

    name = "website_discovery"
    source_type = "scrape"
    requires_api_key = False

    # This provider can populate almost all core fields via semantic and deterministic extraction
    capabilities = CapabilitySet(
        can_provide_website=True,
        can_provide_email=True,
        can_provide_phone=True,
        can_provide_social_links=True,
        can_provide_categories=True, # Mapped from 'industry'
    )

    def discover(self, query: DiscoveryQuery) -> DiscoveryBatch:
        """
        Adapts the DiscoveryQuery into one or more website scraping tasks.

        Currently, the DiscoveryQuery doesn't have a dedicated 'websites' list,
        so we look for target URLs in the filters or treat keywords as potential domain seeds.
        In a typical usage, the engine would pass specific target websites via filters.
        """
        candidates: List[RawCandidate] = []

        # Extract target websites from query filters.
        # Expected format: query.filters.get("target_websites", [])
        target_urls = query.filters.get("target_websites", [])

        if not target_urls:
            # If no specific URLs are provided, we cannot "discover" via a website provider
            # unless we have a way to find websites from keywords (which is a different provider).
            return DiscoveryBatch(
                source=self.name,
                candidates=[],
                meta=SourceMeta(source=self.name, request_count=0)
            )

        for url in target_urls:
            try:
                # Reuse the existing deep-scrape logic
                # scrape_site(url) handles:
                # 1. Homepage fetch
                # 2. Internal page discovery (About/Contact)
                # 3. Deterministic contact harvesting
                # 4. Semantic LLM extraction
                # 5. Lead cleaning and canonicalization
                lead_data = scrape_site(url)

                if lead_data:
                    candidates.append(
                        RawCandidate(
                            payload=lead_data,
                            source=self.name,
                            fetched_at=datetime.now(UTC)
                        )
                    )
            except Exception as e:
                # We log the error but don't let one failed site crash the whole batch
                print(f"[{self.name}] Failed to scrape {url}: {e}")

        return DiscoveryBatch(
            source=self.name,
            candidates=candidates,
            meta=SourceMeta(
                source=self.name,
                request_count=len(target_urls)
            )
        )
