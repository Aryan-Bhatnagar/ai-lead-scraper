"""
Guru Scraper Service.

Handles the raw data acquisition from Guru via the Apify API.
"""

import os
from . import apify_scraper_service as apify_base
from typing import List, Dict, Any, Optional
import logging

# Setup logger
logger = logging.getLogger(__name__)

class GuruScraperService(apify_base.ApifyScraperService):
    """
    Service layer for fetching Guru job listings.

    Uses the Apify Guru Scraper actor to bypass bot protection
    and receive structured JSON data.
    """

    def __init__(self):
        """Initialize the Guru scraper service with the Guru actor ID."""
        super().__init__(actor_id="apify/guru-scraper")

    def scrape_jobs(self, keywords: List[str], max_results: int = 20, location: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for jobs on Guru based on keywords.

        Args:
            keywords: List[str]: Search terms to use.
            max_results int: Limit the number of jobs returned.
            location Optional[str]: Optional location filter.

        Returns:
            List[Dict[str, Any]]: A list of raw job dictionaries.
        """
        # Prepare the actor input
        query_string = " ".join(keywords)

        # Input for the Apify Guru Scraper actor
        run_input = {
            "queries": [query_string],
            "maxResults": max_results,
            "location": location,
        }

        # Call the actor using the base class method
        return self._call_actor(run_input)