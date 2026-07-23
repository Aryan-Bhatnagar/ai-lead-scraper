"""Tests for Phase 12B – Free lead discovery endpoint.

The tests cover:
* successful discovery (mocking the DuckDuckGo API)
* missing/empty industry
* missing/empty location
* invalid ``max_results`` values
* duplicate URL removal
* irrelevant/social URL filtering
* upstream/provider failure (HTTP error)
* max_results enforcement
"""

from typing import Self
import unittest
from unittest.mock import patch, MagicMock
import os
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.app import create_app


class FreeLeadDiscoveryTest(unittest.TestCase):
    def setUp(self):
        # Ensure a fresh Flask app for each test.
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self):
        # Clean up any env var if needed.
        pass

    @patch("scraper.free_lead_discovery.requests.get")
    def test_successful_discovery(self, mock_get):
        # Mock a successful DuckDuckGo response with RelatedTopics.
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "RelatedTopics": [
                {
                    "FirstURL": "https://example.com",
                    "Text": "Example Company - Best digital marketing services in Chandigarh",
                },
                {
                    "FirstURL": "https://testsite.org",
                    "Text": "Test Site Agency",
                    "Topics": [
                        {
                            "FirstURL": "https://sub.testsite.org",
                            "Text": "Sub Topic",
                        }
                    ],
                },
                {
                    "FirstURL": "https://facebook.com/somepage",  # Should be filtered out
                    "Text": "Facebook Page",
                },
            ]
        }
        mock_get.return_value = mock_resp

        payload = {
            "industry": "Digital Marketing Agency",
            "location": "Chandigarh",
            "max_results": 10,
        }
        resp = self.client.post(
            "/api/discover/free",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("results", data)
        # Should have 2 results (facebook filtered out)
        self.assertEqual(len(data["results"]), 2)
        # Verify normalized fields.
        first = data["results"][0]
        self.assertEqual(first["company_name"], "Example")
        self.assertEqual(first["website"], "https://example.com")
        self.assertEqual(first["description"], "Example Company - Best digital marketing services in Chandigarh")
        self.assertEqual(first["source"], "duckduckgo")
        self.assertEqual(first["industry"], "Digital Marketing Agency")
        self.assertEqual(first["location"], "Chandigarh")
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["source"], "free_web")

    def test_missing_industry(self):
        payload = {"location": "Chandigarh", "max_results": 5}
        resp = self.client.post(
            "/api/discover/free",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Missing 'industry'", resp.get_json()["error"])

    def test_empty_industry(self):
        payload = {"industry": "   ", "location": "Chandigarh", "max_results": 5}
        resp = self.client.post(
            "/api/discover/free",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("'industry' cannot be empty", resp.get_json()["error"])

    def test_missing_location(self):
        payload = {"industry": "Digital Marketing", "max_results": 5}
        resp = self.client.post(
            "/api/discover/free",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Missing 'location'", resp.get_json()["error"])

    def test_empty_location(self):
        payload = {"industry": "Digital Marketing", "location": "   ", "max_results": 5}
        resp = self.client.post(
            "/api/discover/free",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("'location' cannot be empty", resp.get_json()["error"])

    def test_invalid_max_results(self):
        payload = {"industry": "Digital Marketing", "location": "Chandigarh", "max_results": 0}
        resp = self.client.post(
            "/api/discover/free",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("'max_results' must be between 1 and", resp.get_json()["error"])

    def test_max_results_enforcement(self):
        # Test that max_results > 50 is rejected
        payload = {"industry": "Digital Marketing", "location": "Chandigarh", "max_results": 51}
        resp = self.client.post(
            "/api/discover/free",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("'max_results' must be between 1 and", resp.get_json()["error"])

    @patch("scraper.free_lead_discovery.requests.get")
    def test_duplicate_url_removal(self, mock_get):
        # Mock response with duplicate URLs
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "RelatedTopics": [
                {
                    "FirstURL": "https://example.com",
                    "Text": "First Example",
                },
                {
                    "FirstURL": "https://example.com/",  # Same domain, different path
                    "Text": "Second Example",
                },
                {
                    "FirstURL": "https://www.example.com",  # WWW version
                    "Text": "Third Example",
                },
                {
                    "FirstURL": "https://test.com",
                    "Text": "Test Site",
                },
            ]
        }
        mock_get.return_value = mock_resp

        payload = {
            "industry": "Digital Marketing Agency",
            "location": "Chandigarh",
            "max_results": 10,
        }
        resp = self.client.post(
            "/api/discover/free",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # Should have only 2 unique domains after normalization
        self.assertEqual(len(data["results"]), 2)
        websites = [r["website"] for r in data["results"]]
        self.assertIn("https://example.com", websites)
        self.assertIn("https://test.com", websites)

    @patch("scraper.free_lead_discovery.requests.get")
    def test_social_url_filtering(self, mock_get):
        # Mock response with social media URLs that should be filtered out
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "RelatedTopics": [
                {
                    "FirstURL": "https://facebook.com/company",
                    "Text": "Facebook Page",
                },
                {
                    "FirstURL": "https://twitter.com/company",
                    "Text": "Twitter Profile",
                },
                {
                    "FirstURL": "https://linkedin.com/company",
                    "Text": "LinkedIn Company",
                },
                {
                    "FirstURL": "https://instagram.com/company",
                    "Text": "Instagram Profile",
                },
                {
                    "FirstURL": "https://youtube.com/company",
                    "Text": "YouTube Channel",
                },
                {
                    "FirstURL": "https://wikipedia.org/wiki/Something",
                    "Text": "Wikipedia Article",
                },
                {
                    "FirstURL": "https://google.com/search",
                    "Text": "Google Search",
                },
                {
                    "FirstURL": "https://github.com/user/repo",
                    "Text": "GitHub Repo",
                },
                {
                    "FirstURL": "https://reddit.com/r/something",
                    "Text": "Reddit Post",
                },
                {
                    "FirstURL": "https://example.com",
                    "Text": "Valid Company",
                },
            ]
        }
        mock_get.return_value = mock_resp

        payload = {
            "industry": "Digital Marketing Agency",
            "location": "Chandigarh",
            "max_results": 10,
        }
        resp = self.client.post(
            "/api/discover/free",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # Should have only 1 result (the valid example.com)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["website"], "https://example.com")

    @patch("scraper.free_lead_discovery.requests.get")
    def test_upstream_failure(self, mock_get):
        # Simulate a non-200 response.
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("502 Bad Gateway")
        mock_get.return_value = mock_resp

        payload = {
            "industry": "Digital Marketing",
            "location": "Chandigarh",
            "max_results": 5,
        }

        resp = self.client.post(
            "/api/discover/free",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 500)
        error_msg = resp.get_json()["error"]
        self.assertIn("502 Bad Gateway", error_msg)

    @patch("scraper.free_lead_discovery.requests.get")
    def test_empty_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"RelatedTopics": []}
        mock_get.return_value = mock_resp
        payload = {"industry": "Digital Marketing", "location": "Nowhere", "max_results": 5}
        resp = self.client.post(
            "/api/discover/free",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["results"], [])
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["source"], "free_web")

    @patch("scraper.free_lead_discovery.requests.get")
    def test_max_results_limiting(self, mock_get):
        # Mock response with more results than requested
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "RelatedTopics": [
                {"FirstURL": f"https://site{i}.com", "Text": f"Site {i}"}
                for i in range(10)  # 10 potential results
            ]
        }
        mock_get.return_value = mock_resp

        payload = {
            "industry": "Digital Marketing Agency",
            "location": "Chandigarh",
            "max_results": 3,  # Request only 3
        }
        resp = self.client.post(
            "/api/discover/free",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # Should have exactly 3 results
        self.assertEqual(len(data["results"]), 3)
        self.assertEqual(data["count"], 3)


if __name__ == "__main__":
    unittest.main()