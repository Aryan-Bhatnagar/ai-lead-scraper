import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from scraper import database as db_module
from scraper.scrape_api_helper import _process_url


class Phase9ALeadQualityScoringTest(unittest.TestCase):

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db_path = Path(self.temp_db.name)
        self.temp_db.close()

        db_module.initialize_database(self.temp_db_path)

    def tearDown(self):
        os.unlink(self.temp_db_path)

    def create_job(self, url):
        return db_module.create_scrape_job(
            [url],
            self.temp_db_path,
        )

    @patch("scraper.scrape_api_helper.scrape_site")
    def test_high_quality_lead_score_is_persisted(self, mock_scrape):
        url = "https://high-quality-test.com"

        mock_scrape.return_value = {
            "company_name": "Test Company",
            "industry": "Software Development",
            "company_description": "Software development company",
            "contact_name": "Test Person",
            "contact_role": "Founder",
            "email": "hello@testcompany.com",
            "phone": "+911234567890",
            "website": url,
            "city": "Chandigarh",
            "country": "India",
        }

        job_id = self.create_job(url)

        result = _process_url(
            job_id,
            url,
            self.temp_db_path,
        )

        self.assertEqual(result[1], "success")

        lead = db_module.get_lead_by_source_url(
            url,
            self.temp_db_path,
        )

        self.assertIsNotNone(lead)
        self.assertEqual(lead["quality_score"], 100)
        self.assertEqual(lead["data_quality"], "HIGH")
        self.assertEqual(lead["status"], "success")

    @patch("scraper.scrape_api_helper.scrape_site")
    def test_medium_quality_lead_score_is_persisted(self, mock_scrape):
        url = "https://medium-quality-test.com"

        mock_scrape.return_value = {
            "company_name": "Medium Company",
            "industry": "Software Development",
            "email": "hello@mediumcompany.com",
            "phone": "+911234567890",
        }

        job_id = self.create_job(url)

        result = _process_url(
            job_id,
            url,
            self.temp_db_path,
        )

        self.assertEqual(result[1], "success")

        lead = db_module.get_lead_by_source_url(
            url,
            self.temp_db_path,
        )

        self.assertIsNotNone(lead)
        self.assertEqual(lead["quality_score"], 65)
        self.assertEqual(lead["data_quality"], "MEDIUM")
        self.assertEqual(lead["status"], "success")

    @patch("scraper.scrape_api_helper.scrape_site")
    def test_source_url_is_added_before_scoring_and_persistence(
        self,
        mock_scrape,
    ):
        url = "https://source-url-test.com"

        mock_scrape.return_value = {
            "company_name": "Source URL Company",
            "email": "hello@sourceurl.com",
        }

        job_id = self.create_job(url)

        result = _process_url(
            job_id,
            url,
            self.temp_db_path,
        )

        self.assertEqual(result[1], "success")

        lead = db_module.get_lead_by_source_url(
            url,
            self.temp_db_path,
        )

        self.assertIsNotNone(lead)
        self.assertEqual(lead["source_url"], url)
        self.assertEqual(lead["quality_score"], 40)
        self.assertEqual(lead["data_quality"], "LOW")

    @patch("scraper.scrape_api_helper.scrape_site")
    def test_no_meaningful_data_does_not_create_lead(
        self,
        mock_scrape,
    ):
        url = "https://no-data-test.com"

        mock_scrape.return_value = {}

        job_id = self.create_job(url)

        result = _process_url(
            job_id,
            url,
            self.temp_db_path,
        )

        self.assertEqual(result[1], "no_data")

        lead = db_module.get_lead_by_source_url(
            url,
            self.temp_db_path,
        )

        self.assertIsNone(lead)


if __name__ == "__main__":
    unittest.main()