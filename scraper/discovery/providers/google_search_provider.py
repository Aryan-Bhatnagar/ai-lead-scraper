"""
Google Search Discovery Provider using the existing SearchService.
"""

from __future__ import annotations
from datetime import datetime, UTC
from typing import List

from ..provider import DiscoveryProvider, CapabilitySet
from ..query import DiscoveryQuery, DiscoveryBatch, RawCandidate, SourceMeta
from ...services.search.service import SearchService

class GoogleSearchDiscoveryProvider(DiscoveryProvider):
    """
    Provider that discovers leads using Google Search via the SearchService.
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
        Discovers leads by performing search queries via the SearchService.
        """
        candidates: List[RawCandidate] = []

        # Construct search queries
        queries_to_run = []
        base_query = f"{query.industry} company {query.location}"
        queries_to_run.append(base_query)
        for kw in query.keywords:
            queries_to_run.append(f"{kw} company {query.location}")

        total_results_collected = 0
        for q in queries_to_run:
            if total_results_collected >= query.max_results:
                break

            remaining = query.max_results - total_results_collected

            try:
                # Use SearchService with preferred_backend="ddgs" as in the original
                results = SearchService().search(
                    query=q,
                    limit=remaining,
                    preferred_backend="ddgs"
                )

                for res in results:
                    # Ensure the result has the expected fields
                    payload = {
                        "title": res.get("title", ""),
                        "url": res.get("url", ""),
                        "snippet": res.get("snippet", ""),
                        "source_engine": res.get("source_engine", "ddgs"),
                        "query": q,
                        "timestamp": res.get("timestamp") or datetime.now(UTC).isoformat()
                    }

                    candidates.append(
                        RawCandidate(
                            payload=payload,
                            source=self.name,
                            fetched_at=datetime.now(UTC)
                        )
                    )
                    total_results_collected += 1
                    if total_results_collected >= query.max_results:
                        break
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