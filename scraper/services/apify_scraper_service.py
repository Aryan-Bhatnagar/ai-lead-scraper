"""
Apify Scraper Service Base Class.

Provides a base class for scraping data from Apify actors.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import requests

# Setup logger
logger = logging.getLogger(__name__)

class ApifyScraperService:
    """
    Base service layer for fetching data from Apify actors.

    Uses the Apify API to run actors and retrieve dataset items.
    """

    def __init__(self, actor_id: str):
        """
        Initialize the Apify scraper service.

        Args:
            actor_id: The Apify actor ID to use (e.g., "apify/upwork-scraper").
        """
        # Configuration from environment variables
        self.apify_token = os.environ.get("APIFY_TOKEN")
        self.actor_id = actor_id
        self.apify_api_url = "https://api.apify.com/v2"

        if not self.apify_token:
            logger.warning("APIFY_TOKEN environment variable is not set. Scraping will fail.")

    def _call_actor(self, run_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Call an Apify actor with the given input and return the dataset items.

        Args:
            run_input: The input payload for the Apify actor.

        Returns:
            List[Dict[str, Any]]: A list of raw data dictionaries from the actor's dataset.
        """
        if not self.apify_token:
            logger.error("APIFY_TOKEN environment variable is not set.")
            return []

        try:
            # Start the actor run and wait for it to finish (synchronous)
            endpoint = f"{self.apify_api_url}/acts/{self.actor_id}/run-sync-get-dataset-items"
            params = {
                "token": self.apify_token,
            }

            response = requests.post(endpoint, params=params, json=run_input, timeout=60)
            response.raise_for_status()

            # Parse and return raw results
            data = response.json()
            if isinstance(data, list):
                return data
            else:
                # If the actor returns a single object, wrap it in a list
                return [data]

        except requests.exceptions.RequestException as e:
            logger.error(f"Apify API request failed for actor {self.actor_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in ApifyScraperService for actor {self.actor_id}: {e}")
            return []

    # This method is to be implemented by subclasses
    def scrape_jobs(self, keywords: List[str], max_results: int = 20, location: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for jobs based on keywords. To be implemented by subclasses.

        Args:
            keywords: List[str]: Search terms to use.
            max_results int: Limit the number of jobs returned.
            location Optional[str]: Optional location filter.

        Returns:
            List[Dict[str, Any]]: A list of raw job dictionaries.
        """
        raise NotImplementedError("Subclasses must implement scrape_jobs method")