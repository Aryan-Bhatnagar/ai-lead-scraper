import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from api.app import create_app
import scraper.database as db_module


class Phase8BDiscoveryAPITest(unittest.TestCase):

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db_path = Path(self.temp_db.name)
        self.temp_db.close()

        db_module.initialize_database(self.temp_db_path)

        self.app = create_app({
            "TESTING": True,
            "DATABASE": str(self.temp_db_path),
        })

        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.temp_db_path)

    @patch("api.app.discover_leads")
    def test_valid_discovery_request(self, mock_discover):
        mock_discover.return_value = [
            {
                "title": "Test Company",
                "url": "https://example.com",
                "description": "Test company description",
            }
        ]

        response = self.client.post(
            "/api/discover",
            json={
                "industry": "software companies",
                "location": "Chandigarh",
                "max_results": 10,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["industry"], "software companies")
        self.assertEqual(data["location"], "Chandigarh")
        self.assertEqual(
            data["results"][0]["url"],
            "https://example.com",
        )

        mock_discover.assert_called_once_with(
            industry="software companies",
            location="Chandigarh",
            max_results=10,
        )

    def test_missing_industry(self):
        response = self.client.post(
            "/api/discover",
            json={
                "location": "Chandigarh"
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_empty_industry(self):
        response = self.client.post(
            "/api/discover",
            json={
                "industry": "   ",
                "location": "Chandigarh",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_location(self):
        response = self.client.post(
            "/api/discover",
            json={
                "industry": "software companies"
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_empty_location(self):
        response = self.client.post(
            "/api/discover",
            json={
                "industry": "software companies",
                "location": "   ",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_max_results_not_integer(self):
        response = self.client.post(
            "/api/discover",
            json={
                "industry": "software companies",
                "location": "Chandigarh",
                "max_results": "10",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_max_results_below_minimum(self):
        response = self.client.post(
            "/api/discover",
            json={
                "industry": "software companies",
                "location": "Chandigarh",
                "max_results": 0,
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_max_results_above_maximum(self):
        response = self.client.post(
            "/api/discover",
            json={
                "industry": "software companies",
                "location": "Chandigarh",
                "max_results": 51,
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_non_json_request(self):
        response = self.client.post(
            "/api/discover",
            data="not json",
            headers={
                "Content-Type": "text/plain"
            },
        )

        self.assertEqual(response.status_code, 400)

    @patch("api.app.discover_leads")
    def test_discovery_exception_handled(self, mock_discover):
        mock_discover.side_effect = Exception(
            "Search provider unavailable"
        )

        response = self.client.post(
            "/api/discover",
            json={
                "industry": "software companies",
                "location": "Chandigarh",
                "max_results": 10,
            },
        )

        self.assertEqual(response.status_code, 500)

        data = response.get_json()

        self.assertEqual(
            data["error"],
            "Lead discovery failed",
        )


if __name__ == "__main__":
    unittest.main()