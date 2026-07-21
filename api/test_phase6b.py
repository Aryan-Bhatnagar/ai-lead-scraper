import os
import tempfile
import sqlite3
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.app import create_app
import scraper.database as db_module
import scraper.scrape_api_helper as scrape_api_helper

# ----- Helper to build a mock lead -----

def mock_lead(company_name):
    return {
        "company_name": company_name,
        "industry": "Test",
        "company_description": "Desc",
        "contact_name": "Alice",
        "contact_role": "CEO",
        "email": "alice@example.com",
        "phone": "1234567",
        "website": "https://example.com",
        "city": "City",
        "country": "Country",
        "source_url": "https://example.com",
        "source_pages": "page",
        "email_source_page": "page",
        "email_source_type": "mailto",
        "phone_source_page": "page",
        "phone_source_type": "tel",
        "scraped_at": "2026-01-01T00:00:00Z",
        "status": "success",
        "quality_score": 100,
        "data_quality": "HIGH",
        "error": "",
    }

class Phase6BTest(unittest.TestCase):
    def setUp(self):
        # temporary DB
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db_path = Path(self.temp_db.name)
        self.temp_db.close()
        db_module.initialize_database(self.temp_db_path)
        self.app = create_app({"TESTING": True, "DATABASE": str(self.temp_db_path)})
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.temp_db_path)

    def _poll_job(self, job_id, max_iter=20):
        for _ in range(max_iter):
            resp = self.client.get(f"/api/jobs/{job_id}")
            job = resp.get_json()
            if job.get("status") in ("completed", "failed"):
                return job
            time.sleep(0.01)
        return None

    def test_post_valid_job_202(self):
        with patch("scraper.scrape_api_helper.scrape_site", return_value=mock_lead("TestCo")), \
             patch("scraper.scrape_leads.has_meaningful_data", return_value=True):
            resp = self.client.post("/api/jobs", json={"urls": ["https://example.com"]})
            self.assertEqual(resp.status_code, 202)
            data = resp.get_json()
            self.assertIn("job_id", data)
            self.assertEqual(data["status"], "queued")
            job_id = data["job_id"]
            job = db_module.get_scrape_job(job_id, self.temp_db_path)
            self.assertIsNotNone(job)
            items = db_module.get_job_items(job_id, self.temp_db_path)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["source_url"], "https://example.com")
            completed = self._poll_job(job_id)
            self.assertIsNotNone(completed)
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["successful_urls"], 1)
            self.assertEqual(completed["no_data_urls"], 0)
            self.assertEqual(completed["failed_urls"], 0)
            lead = db_module.get_lead_by_source_url("https://example.com", self.temp_db_path)
            self.assertIsNotNone(lead)
            self.assertEqual(lead["company_name"], "TestCo")

    def test_post_missing_urls_400(self):
        resp = self.client.post("/api/jobs", json={})
        self.assertEqual(resp.status_code, 400)

    def test_post_empty_urls_400(self):
        resp = self.client.post("/api/jobs", json={"urls": []})
        self.assertEqual(resp.status_code, 400)

    def test_post_urls_not_list_400(self):
        resp = self.client.post("/api/jobs", json={"urls": "string"})
        self.assertEqual(resp.status_code, 400)

    def test_post_invalid_url_entries_400(self):
        resp = self.client.post("/api/jobs", json={"urls": ["", 123]})
        self.assertEqual(resp.status_code, 400)

    def test_post_non_json_400(self):
        resp = self.client.post("/api/jobs", data="not json", headers={"Content-Type": "text/plain"})
        self.assertEqual(resp.status_code, 400)

    def test_scraped_lead_missing_source_url_uses_job_url(self):
        lead_without_source_url = mock_lead("SourceUrlTestCo")
        lead_without_source_url.pop("source_url")

        job_url = "https://source-url-test.com"

        with patch(
            "scraper.scrape_api_helper.scrape_site",
            return_value=lead_without_source_url,
        ), patch(
            "scraper.scrape_leads.has_meaningful_data",
            return_value=True,
        ):
            resp = self.client.post(
                "/api/jobs",
                json={"urls": [job_url]},
            )

            self.assertEqual(resp.status_code, 202)
            job_id = resp.get_json()["job_id"]

            completed = self._poll_job(job_id)

            self.assertIsNotNone(completed)
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["successful_urls"], 1)
            self.assertEqual(completed["failed_urls"], 0)

            lead = db_module.get_lead_by_source_url(
                job_url,
                self.temp_db_path,
            )

            self.assertIsNotNone(lead)
            self.assertEqual(lead["company_name"], "SourceUrlTestCo")
            self.assertEqual(lead["source_url"], job_url)

            items = db_module.get_job_items(
                job_id,
                self.temp_db_path,
            )

            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["source_url"], job_url)
            self.assertEqual(items[0]["status"], "success")

    def test_scrape_site_exception_handled(self):
        with patch(
            "scraper.scrape_api_helper.scrape_site",
            side_effect=Exception("Test error"),
        ), patch(
            "scraper.scrape_api_helper.has_meaningful_data",
            return_value=True,
        ):
            resp = self.client.post(
                "/api/jobs",
                json={"urls": ["https://error.com"]},
            )

            self.assertEqual(resp.status_code, 202)
            job_id = resp.get_json()["job_id"]

            completed = self._poll_job(job_id)

            self.assertIsNotNone(completed)
            self.assertEqual(completed["failed_urls"], 1)

            items = db_module.get_job_items(
                job_id,
                self.temp_db_path,
            )

            self.assertEqual(items[0]["status"], "failed")

if __name__ == "__main__":
    unittest.main()
