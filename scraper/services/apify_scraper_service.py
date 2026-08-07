"""
Apify Scraper Service Base Class.

Provides a base class for scraping data from Apify actors.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import requests
import time

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
        """

        if not self.apify_token:
            logger.error("APIFY_TOKEN environment variable is not set.")
            print("[APIFY_TOKEN] Loaded: False")
            return []

        print("\n" + "=" * 80)
        print("[APIFY] STARTING ACTOR")
        print("=" * 80)
        print(f"[APIFY] Token Loaded : True")
        print(f"[APIFY] Actor ID     : {self.actor_id}")
        print(f"[APIFY] Input        : {run_input}")
        print("=" * 80)

        try:
            # ------------------------------------------------------------------
            # STEP 1 - START ACTOR
            # ------------------------------------------------------------------

            run_endpoint = f"{self.apify_api_url}/acts/{self.actor_id}/runs"

            start_resp = requests.post(
                run_endpoint,
                params={"token": self.apify_token},
                json=run_input,
                timeout=120,
            )

            print("\n[APIFY] START RESPONSE")
            print("Status Code :", start_resp.status_code)
            print(start_resp.text)

            start_resp.raise_for_status()

            start_json = start_resp.json()
            start_data = start_json.get("data", start_json)

            run_id = (
                start_data.get("id")
                or start_data.get("runId")
                or start_data.get("actRunId")
            )

            if not run_id:
                raise RuntimeError("Run ID missing from Apify response.")

            print(f"\n[APIFY] Run ID : {run_id}")

            # ------------------------------------------------------------------
            # STEP 2 - POLL
            # ------------------------------------------------------------------

            poll_url = f"{self.apify_api_url}/actor-runs/{run_id}"

            elapsed = 0
            timeout = 180
            interval = 5

            run_data = None

            while elapsed < timeout:

                poll_resp = requests.get(
                    poll_url,
                    params={"token": self.apify_token},
                    timeout=30,
                )

                print(f"\n[APIFY] POLL ({elapsed}s)")
                print("Status Code :", poll_resp.status_code)
                print(poll_resp.text)

                poll_resp.raise_for_status()

                poll_json = poll_resp.json()
                poll_data = poll_json.get("data", poll_json)

                status = poll_data.get("status")

                print("[APIFY] Current Status :", status)

                if status == "SUCCEEDED":
                    run_data = poll_data
                    break

                if status in ("FAILED", "TIMED-OUT", "ABORTED"):
                    raise RuntimeError(f"Run ended with status: {status}")

                time.sleep(interval)
                elapsed += interval

            if run_data is None:
                raise TimeoutError("Actor never reached SUCCEEDED.")

            # ------------------------------------------------------------------
            # STEP 3 - DATASET
            # ------------------------------------------------------------------

            dataset_id = run_data.get("defaultDatasetId")

            print("\n[APIFY] Dataset ID :", dataset_id)

            if not dataset_id:
                raise RuntimeError("defaultDatasetId missing.")

            dataset_url = f"{self.apify_api_url}/datasets/{dataset_id}/items"

            dataset_resp = requests.get(
                dataset_url,
                params={"token": self.apify_token},
                timeout=60,
            )

            print("\n[APIFY] DATASET RESPONSE")
            print("Status Code :", dataset_resp.status_code)
            print(dataset_resp.text)

            dataset_resp.raise_for_status()

            items = dataset_resp.json()

            if not isinstance(items, list):
                items = [items]

            print("\n" + "=" * 80)
            print(f"[APIFY] ITEMS RECEIVED : {len(items)}")

            if items:
                print("[APIFY] FIRST ITEM")
                print(items[0])
            else:
                print("[APIFY] DATASET IS EMPTY")

            print("=" * 80 + "\n")

            return items

        except Exception as e:
            logger.exception("Apify scraper failed")
            print("\n" + "=" * 80)
            print("[APIFY] EXCEPTION")
            print(type(e).__name__)
            print(e)
            print("=" * 80 + "\n")
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