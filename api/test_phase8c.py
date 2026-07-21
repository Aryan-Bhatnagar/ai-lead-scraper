"""Test suite for the POST /api/discover-and-scrape endpoint.\n\nThe tests mirror the behaviour of the discovery endpoint in :mod:`api.app` but replace external dependencies with mocks so that they run quickly and deterministically.\n\n* Mock :func:`scraper.lead_discovery.discover_leads` – the heavy network call that scrapes the web.\n* Mock :func:`scraper.scrape_api_helper.run_job_in_background` – the queueing helper that starts the asynchronous scraper.\n* Use a temporary SQLite database created with :func:`scraper.database.initialize_database`.\n\nThe test cases focus on:\n1. Successful discovery and job creation.\n2. URL deduplication logic.\n3. URL validation (only http/https).\n4. Empty candidate handling.\n5-10. Input validation and error handling.\n\nAll this is done using unittest's ``patch`` to intercept calls to the real external functions.\n"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure the project root is on sys.path – tests live in the same directory as api/test_phase8b.py, so the root is one level up.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.app import create_app
import scraper.database as db_module

# Helper to fetch all scrape jobs in the test database

def _count_jobs(db_path: Path):
    with db_module.get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM scrape_jobs")
        return cursor.fetchone()[0]


class Phase8CDiscoverAndScrapeAPITest(unittest.TestCase):
    def setUp(self):
        # Create a temporary SQLite db file – never touched by real app logic
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db_path = Path(self.temp_db.name)
        self.temp_db.close()
        db_module.initialize_database(self.temp_db_path)

        # Create the Flask test client
        self.app = create_app({
            "TESTING": True,
            "DATABASE": str(self.temp_db_path),
        })
        self.client = self.app.test_client()

    def tearDown(self):
        # Delete temp db file
        os.unlink(self.temp_db_path)

    @patch("api.app.discover_leads")
    @patch("scraper.scrape_api_helper.run_job_in_background")
    def test_valid_discovery_request(self, mock_run, mock_discover):
        # Two unique URLs from discovery
        mock_discover.return_value = [
            {"url": "https://example.com"},
            {"url": "https://second.com"},
        ]

        resp = self.client.post(
            "/api/discover-and-scrape",
            json={
                "industry": "software", "location": "Chandigarh", "max_results": 10
            },
        )
        self.assertEqual(resp.status_code, 202)
        data = resp.get_json()
        self.assertEqual(data["status"], "queued")
        self.assertEqual(data["discovered_count"], 2)
        self.assertIn("job_id", data)

        # Job actually stored in DB
        job_id = data["job_id"]
        self.assertEqual(_count_jobs(self.temp_db_path), 1)

        # Background call
        mock_run.assert_called_once_with(
            job_id, ["https://example.com", "https://second.com"], str(self.temp_db_path)
        )

    @patch("api.app.discover_leads")
    @patch("scraper.scrape_api_helper.run_job_in_background")
    def test_duplicate_urls_deduped(self, mock_run, mock_discover):
        mock_discover.return_value = [
            {"url": "https://dup.com"},
            {"url": "https://dup.com"},  # duplicate
            {"url": "https://unique.com"},
        ]

        resp = self.client.post(
            "/api/discover-and-scrape",
            json={
                "industry": "software", "location": "CF", "max_results": 10
            },
        )
        self.assertEqual(resp.status_code, 202)
        data = resp.get_json()
        self.assertEqual(data["discovered_count"], 2)
        self.assertEqual(data["urls"], ["https://dup.com", "https://unique.com"])
        mock_run.assert_called_once_with(
            data["job_id"], ["https://dup.com", "https://unique.com"], str(self.temp_db_path)
        )

    @patch("api.app.discover_leads")
    @patch("scraper.scrape_api_helper.run_job_in_background")
    def test_invalid_urls_filtered(self, mock_run, mock_discover):
        mock_discover.return_value = [
            {"url": "https://valid.com"},
            {"url": ""},
            {"url": "    "},
            {"url": None},
            {"url": 123},
            {"url": "ftp://bad.com"},
        ]

        resp = self.client.post(
            "/api/discover-and-scrape",
            json={"industry": "software", "location": "LT", "max_results": 10},
        )
        self.assertEqual(resp.status_code, 202)
        data = resp.get_json()
        self.assertEqual(data["discovered_count"], 1)
        self.assertEqual(data["urls"], ["https://valid.com"])
        mock_run.assert_called_once_with(
            data["job_id"], ["https://valid.com"], str(self.temp_db_path)
        )

    @patch("api.app.discover_leads")
    @patch("scraper.scrape_api_helper.run_job_in_background")
    def test_no_usable_candidates(self, mock_run, mock_discover):
        mock_discover.return_value = [
            {"url": ""},
            {"url": None},
            {"url": "ftp://bad.com"},
        ]

        resp = self.client.post(
            "/api/discover-and-scrape",
            json={"industry": "software", "location": "UT", "max_results": 5},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "no_candidates")
        self.assertEqual(data["discovered_count"], 0)
        self.assertEqual(data["urls"], [])
        mock_run.assert_not_called()
        self.assertEqual(_count_jobs(self.temp_db_path), 0)

    def test_missing_industry(self):
        resp = self.client.post(
            "/api/discover-and-scrape",
            json={"location": "L", "max_results": 10},
        )
        self.assertEqual(resp.status_code, 400)

    def test_missing_location(self):
        resp = self.client.post(
            "/api/discover-and-scrape",
            json={"industry": "Soft", "max_results": 10},
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_max_results_type(self):
        resp = self.client.post(
            "/api/discover-and-scrape",
            json={"industry": "Soft", "location": "L", "max_results": "10"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_boolean_max_results(self):
        resp = self.client.post(
            "/api/discover-and-scrape",
            json={"industry": "Soft", "location": "L", "max_results": True},
        )
        self.assertEqual(resp.status_code, 400)

    def test_max_results_outside_bounds(self):
        for val in (0, 51):
            resp = self.client.post(
                "/api/discover-and-scrape",
                json={"industry": "Soft", "location": "L", "max_results": val},
            )
            self.assertEqual(resp.status_code, 400)

    @patch("api.app.discover_leads")
    def test_discovery_exception(self, mock_discover):
        mock_discover.side_effect = Exception("Network error")
        resp = self.client.post(
            "/api/discover-and-scrape",
            json={"industry": "Soft", "location": "L", "max_results": 10},
        )
        self.assertEqual(resp.status_code, 500)
        data = resp.get_json()
        self.assertEqual(data["error"], "Lead discovery failed")
        self.assertEqual(_count_jobs(self.temp_db_path), 0)


if __name__ == "__main__":
    unittest.main()
