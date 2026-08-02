"""
Upwork Discovery Provider.

Implements the DiscoveryProvider interface to find leads from Upwork job postings.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from ..provider import DiscoveryProvider, CapabilitySet
from ..query import DiscoveryQuery, DiscoveryBatch, RawCandidate, SourceMeta
from ...services.upwork_scraper_service import UpworkScraperService

class UpworkDiscoveryProvider(DiscoveryProvider):
    """
    Adapter that enables the discovery engine to find leads from Upwork.

    This provider searches for job postings based on keywords provided in the
    DiscoveryQuery and wraps the results into RawCandidate objects.
    """

    name = "upwork"
    source_type = "scrape"
    requires_api_key = False

    # Declare capabilities based on the fields an Upwork job can provide
    capabilities = CapabilitySet(
        can_provide_website=False,
        can_provide_email=False,
        can_provide_phone=False,
        can_provide_rating=False,
        can_provide_review_count=False,
        can_provide_coordinates=False,
        can_provide_business_hours=False,
        can_provide_social_links=False,
        can_provide_categories=True, # Mapped from skills/category
        custom={"payment_type", "experience_level", "proposal_count", "budget"}
    )

    def discover(self, query: DiscoveryQuery) -> DiscoveryBatch:
        """
        Discover leads from Upwork based on the query keywords.

        Execution Flow:
        1. Extract keywords from query.
        2. Search Upwork for matching jobs.
        3. Extract job metadata (title, budget, experience, etc.).
        4. Wrap each job into a RawCandidate.
        5. Return as a DiscoveryBatch.
        """
        candidates: List[RawCandidate] = []

        # 1. Extract keywords for search
        # We use the keywords list from the query; if empty, we fallback to industry
        search_terms = query.keywords if query.keywords else [query.industry]

        # In a full implementation, this would call a separate UpworkScraper utility.
        # For the framework implementation, we define the adapter logic.
        try:
            # Use the dedicated service layer for Upwork data acquisition
            scraper_service = UpworkScraperService()
            results = scraper_service.scrape_jobs(
                keywords=search_terms,
                max_results=query.max_results,
                location=query.location
            )

            for job in results:
                candidates.append(
                    RawCandidate(
                        payload=job, # Dictionary containing project_title, budget, etc.
                        source=self.name,
                        fetched_at=datetime.utcnow()
                    )
                )
        except Exception as e:
            # Log error but return empty batch to avoid crashing the engine
            print(f"[{self.name}] Error during Upwork discovery: {e}")

        return DiscoveryBatch(
            source=self.name,
            candidates=candidates,
            meta=SourceMeta(
                source=self.name,
                request_count=len(search_terms)
            )
        )

    def _perform_upwork_search(self, terms: List[str], max_results: int, location: Optional[str]) -> List[dict]:
        """
        DEPRECATED: This logic has been moved to UpworkScraperService.
        Maintained for backward compatibility if needed, but no longer used by discover().
        """
        return []
