"""Tests for Phase 12A – Google Maps discovery endpoint.

The tests cover:
* successful discovery (mocking the Google Places API)
* missing/empty industry
* missing/empty location
* invalid ``max_results`` values
* missing ``GOOGLE_MAPS_API_KEY``
* upstream provider failure (HTTP error)
* normalization of returned business data
* empty results handling
"""

from typing import Self
import unittest
from unittest.mock import patch, MagicMock
import os
import json
from aiohttp import payload
import requests
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.app import create_app

class GoogleMapsDiscoveryTest(unittest.TestCase):
    def setUp(self):
        # Ensure a fresh Flask app for each test.
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()
        # Use a dummy API key for normal tests – overridden where needed.
        os.environ["GOOGLE_MAPS_API_KEY"] = "dummy-key"

    def tearDown(self):
        # Clean up env var to avoid cross‑test leakage.
        if "GOOGLE_MAPS_API_KEY" in os.environ:
            del os.environ["GOOGLE_MAPS_API_KEY"]

    @patch("scraper.google_maps_discovery.requests.get")
    def test_successful_discovery(self, mock_get):
        # Mock a successful Google Places response with two results.
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "results": [
                {
                    "name": "Acme Marketing",
                    "formatted_address": "123 Main St, Chandigarh",
                    "place_id": "abc123",
                    "rating": 4.2,
                    "user_ratings_total": 87,
                },
                {
                    "name": "Beta Agency",
                    "formatted_address": "45 Oak Rd, Chandigarh",
                    "place_id": "def456",
                    "rating": 3.9,
                    "user_ratings_total": 45,
                },
            ]
        }
        mock_get.return_value = mock_resp

        payload = {
            "industry": "Digital Marketing Agency",
            "location": "Chandigarh",
            "max_results": 2,
        }
        resp = self.client.post(
            "/api/discover/google-maps",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 2)
        # Verify normalized fields.
        first = data["results"][0]
        self.assertEqual(first["company_name"], "Acme Marketing")
        self.assertEqual(first["address"], "123 Main St, Chandigarh")
        self.assertIsNone(first["phone"])  # phone not fetched in Phase 12A
        self.assertIsNone(first["website"])
        self.assertEqual(first["rating"], 4.2)
        self.assertEqual(first["reviews_count"], 87)
        self.assertEqual(first["place_id"], "abc123")
        self.assertTrue(first["google_maps_url"].endswith("place_id:abc123"))
        self.assertEqual(first["source"], "google_maps")

    def test_missing_industry(self):
        payload = {"location": "Chandigarh", "max_results": 5}
        resp = self.client.post(
            "/api/discover/google-maps",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Missing 'industry'", resp.get_json()["error"])

    def test_empty_industry(self):
        payload = {"industry": "   ", "location": "Chandigarh", "max_results": 5}
        resp = self.client.post(
            "/api/discover/google-maps",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("'industry' cannot be empty", resp.get_json()["error"])

    def test_missing_location(self):
        payload = {"industry": "Digital Marketing", "max_results": 5}
        resp = self.client.post(
            "/api/discover/google-maps",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Missing 'location'", resp.get_json()["error"])

    def test_empty_location(self):
        payload = {"industry": "Digital Marketing", "location": "   ", "max_results": 5}
        resp = self.client.post(
            "/api/discover/google-maps",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("'location' cannot be empty", resp.get_json()["error"])

    def test_invalid_max_results(self):
        payload = {"industry": "Digital Marketing", "location": "Chandigarh", "max_results": 0}
        resp = self.client.post(
            "/api/discover/google-maps",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("'max_results' must be between 1 and", resp.get_json()["error"])

    def test_missing_api_key(self):
        del os.environ["GOOGLE_MAPS_API_KEY"]
        payload = {"industry": "Digital Marketing", "location": "Chandigarh", "max_results": 5}
        resp = self.client.post(
            "/api/discover/google-maps",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 500)
        self.assertIn("GOOGLE_MAPS_API_KEY environment variable is not set", resp.get_json()["error"])

    @patch("scraper.google_maps_discovery.requests.get")
    def test_upstream_failure(self, mock_get):
        # Simulate a non-200 response.
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("502 Bad Gateway")
        mock_get.return_value = mock_resp

        payload = {
        "industry": "Digital Marketing",
        "location": "Chandigarh",
        "max_results": 5,
        }

        resp = self.client.post(
            "/api/discover/google-maps",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 500)
        self.assertIn("Google Maps API request failed", resp.get_json()["error"])

    @patch("scraper.google_maps_discovery.requests.get")
    def test_empty_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"results": []}
        mock_get.return_value = mock_resp
        payload = {"industry": "Digital Marketing", "location": "Nowhere", "max_results": 5}
        resp = self.client.post(
            "/api/discover/google-maps",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["results"], [])
        self.assertEqual(data["count"], 0)

if __name__ == "__main__":
    unittest.main()
