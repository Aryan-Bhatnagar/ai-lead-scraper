"""
Google Search Discovery Provider.

Discovers potential leads by performing search queries via the SearchService.
"""

from __future__ import annotations
from datetime import datetime
from typing import List

from ..provider import DiscoveryProvider, CapabilitySet
from ..query import DiscoveryQuery, DiscoveryBatch, RawCandidate, SourceMeta
from ...services.search.service import SearchService

class GoogleSearchDiscoveryProvider(DiscoveryProvider):
    """
    Provider that discovers leads using search engine results.

    Note: Despite the name, it uses the SearchService which may employ
    different backends (e.g., ddgs) to retrieve results.
    """

    name = "google_search"
    source_type = "scrape"
    requires_api_key = False

    capabilities = CapabilitySet(
        can_provide_website=True,
        can_provide_email=False,
        can_provide_phone=False,
        can_provide_rating=False,
        can_provide_review_count=False,
        can_provide_coordinates=False,
        can_provide_business_hours=False,
        can_provide_social_links=False,
        can_provide_categories=False,
    )

    def discover(self, query: DiscoveryQuery) -> DiscoveryBatch:
        """
        Discovers leads by generating search queries based on industry and location.
        """
        candidates: List[RawCandidate] = []

        # 1. Construct search queries
        # Pattern: "{industry} company {location}"
        search_query = f"{query.industry} company {query.location}"

        # We also incorporate specific keywords if provided
        queries_to_run = [search_query]
        for kw in query.keywords:
            queries_to_run.append(f"{kw} company {query.location}")

        # 2. Use SearchService to fetch results
        search_service = SearchService()

        total_results_collected = 0
        for q in queries_to_run:
            if total_results_collected >= query.max_results:
                break

            # Fetch remaining results needed
            remaining = query.max_results - total_results_collected

            try:
                # Use preferred_backend="ddgs" as requested
                results = search_service.search(
                    query=q,
                    limit=remaining,
                    preferred_backend="ddgs"
                )

                for res in results:
                    candidates.append(
                        RawCandidate(
                            payload=res, # Contains title, snippet, url, source_engine, query, timestamp
                            source=self.name,
                            fetched_at=datetime.utcnow()
                        )
                    )
                    total_results_collected += 1
            except Exception as e:
                print(f"[{self.name}] Error searching for {q}: {e}")

        return DiscoveryBatch(
            source=self.name,
            candidates=candidates,
            meta=SourceMeta(
                source=self.name,
                request_count=len(queries_to_run)
            )
        )
