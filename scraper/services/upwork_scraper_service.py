"""
Upwork Scraper Service.

Handles the raw data acquisition from Upwork via the Apify API.
This service is entirely independent of the Discovery Framework.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import requests

# Setup logger
logger = logging.getLogger(__name__)

class UpworkScraperService:
    """
    Service layer for fetching Upwork job listings.

    Uses the Apify Upwork Scraper actor to bypass bot protection
    and receive structured JSON data.
    """

    def __init__(self):
        # Configuration from environment variables
        self.apify_token = os.environ.get("APIFY_TOKEN")
        self.actor_id = "apify/upwork-scraper" # Example actor ID
        self.apify_api_url = "https://api.apify.com/v2"

    def scrape_jobs(self, keywords: List[str], max_results: int = 20, location: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for jobs on Upwork based on keywords.

        Args:
            keywords: List[str]: Search terms to use.
            max_results int: Limit the number of jobs returned.
            location Optional[str]: Optional location filter.

        Returns:
            List[Dict[str, Any]]: A list of raw job dictionaries.
        """
        if not self.apify_token:
            logger.error("APIFY_TOKEN environment variable is not set.")
            return []

        try:
            # 1. Prepare the actor input
            # Note: Actual actor input schema varies by actor version; this is a representative structure.
            # We typically join keywords into a single query string or iterate.
            query_string = " ".join(keywords)

            # Input for the Apify Upwork Scraper actor
            run_input = {
                "queries": [query_string],
                "maxItems": max_results,
                "location": location,
            }

            # 2. Start the actor run (synchronously for this service)
            # Using the 'run-sync-get-dataset-items' endpoint for simplicity
            endpoint = f"{self.apify_api_url}/acts/{self.actor_id}/run-sync-get-dataset-items"
            params = {
                "token": self.apify_token,
            }

            response = requests.post(endpoint, params=params, json=run_input, timeout=60)
            response.raise_for_status()

            # 3. Parse and return raw results
            data = response.json()
            if isinstance(data, list):
                return data[:max_results]

            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"Apify API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in UpworkScraperService: {e}")
            return []
