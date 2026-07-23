"""Tests for Phase 12D – Reliable Free Web Search Lead Discovery.

The tests cover:
* successful discovery via HTML search (primary provider)
* fallback to Instant Answer when HTML returns zero results
* blocked domains are excluded
* duplicate domains are removed
* malformed URLs are ignored
* max_results is respected
* network failure is handled
* existing /api/discover/free endpoint remains compatible
* /api/discover/free-and-enrich remains compatible

All external HTTP calls are mocked.
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


class Phase12DTest(unittest.TestCase):
    def setUp(self):
        # Ensure a fresh Flask app for each test.
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self):
        # Clean up any env var if needed.
        pass

    @patch("scraper.free_lead_discovery.requests.get")
    def test_html_search_returns_results(self, mock_get):
        """Test that HTML search returns usable business websites."""
        # Mock response for HTML search (duckduckgo.com/html/)
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = '''
        <div class="result">
            <a class="result__url" href="/uddg?uddg=https%3A%2F%2Fexample.com">Example Company</a>
        </div>
        <div class="result">
            <a class="result__url" href="/uddg?uddg=https%3A%2F%2Ftestsite.org">Test Site Agency</a>
        </div>
        '''
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
        # Should have 2 results
        self.assertEqual(len(data["results"]), 2)
        # Verify normalized fields
        first = data["results"][0]
        self.assertEqual(first["company_name"], "Example Company")
        self.assertEqual(first["website"], "https://example.com")
        self.assertIsNone(first["description"])  # HTML search doesn't extract description
        self.assertEqual(first["source"], "duckduckgo")
        self.assertEqual(first["industry"], "Digital Marketing Agency")
        self.assertEqual(first["location"], "Chandigarh")
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["source"], "free_web")  # endpoint still labels as free_web

    @patch("scraper.free_lead_discovery.requests.get")
    def test_fallback_to_instant_answer(self, mock_get):
        """Test fallback to Instant Answer when HTML search returns zero results."""
        # First call (HTML search) returns empty/no usable results
        mock_resp_html = MagicMock()
        mock_resp_html.raise_for_status.return_value = None
        mock_resp_html.text = '<div class="result"></div>'  # No result__url links
        # Second call (Instant Answer API) returns data
        mock_resp_api = MagicMock()
        mock_resp_api.raise_for_status.return_value = None
        mock_resp_api.json.return_value = {
            "RelatedTopics": [
                {
                    "FirstURL": "https://example.com",
                    "Text": "Example Company - Best digital marketing services in Chandigarh",
                },
                {
                    "FirstURL": "https://testsite.org",
                    "Text": "Test Site Agency",
                },
            ]
        }
        # Side effect: first call returns HTML response, second returns API response
        mock_get.side_effect = [mock_resp_html, mock_resp_api]

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
        # Should have 2 results from the API fallback
        self.assertEqual(len(data["results"]), 2)
        # Verify normalized fields
        first = data["results"][0]
        self.assertEqual(first["company_name"], "Example")
        self.assertEqual(first["website"], "https://example.com")
        self.assertEqual(first["description"], "Example Company - Best digital marketing services in Chandigarh")
        self.assertEqual(first["source"], "duckduckgo")
        self.assertEqual(first["industry"], "Digital Marketing Agency")
        self.assertEqual(first["location"], "Chandigarh")
        self.assertEqual(data["count"], 2)

    @patch("scraper.free_lead_discovery.requests.get")
    def test_blocked_domains_excluded(self, mock_get):
        """Test that blocked domains (social media, etc.) are excluded."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = '''
        <div class="result">
            <a class="result__url" href="/uddg?uddg=https%3A%2F%2Fexample.com">Example Company</a>
        </div>
        <div class="result">
            <a class="result__url" href="/uddg?uddg=https%3A%2F%2Ffacebook.com%2Fcompany">Facebook Page</a>
        </div>
        <div class="result">
            <a class="result__url" href="/uddg?uddg=https%3A%2F%2Flndedin.com%2Fcompany">LinkedIn Company</a>
        </div>
        '''
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
        # Should have only 1 result (example.com)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["website"], "https://example.com")

    @patch("scraper.free_lead_discovery.requests.get")
    def test_duplicate_domains_removed(self, mock_get):
        """Test that duplicate domains are removed (normalized to root domain)."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = '''
        <div class="result">
            <a class="result__url" href="/uddg?uddg=https%3A%2F%2Fexample.com%2Fabout">Example About</a>
        </div>
        <div class="result">
            <a class="result__url" href="/uddg?uddg=https%3A%2F%2Fwww.example.com%2Fcontact">Example WWW</a>
        </div>
        <div class="result">
            <a class="result__url" href="/uddg?uddg=https%3A%2F%2Ftestsite.org">Test Site</a>
        </div>
        '''
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
        # Should have only 2 unique domains: example.com and testsite.org
        self.assertEqual(len(data["results"]), 2)
        websites = [r["website"] for r in data["results"]]
        self.assertIn("https://example.com", websites)
        self.assertIn("https://testsite.org", websites)

    @patch("scraper.free_lead_discovery.requests.get")
    def test_malformed_urls_ignored(self, mock_get):
        """Test that malformed URLs (e.g., missing scheme, blocked domains) are ignored."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = '''
        <div class="result">
            <a class="result__url" href="/uddg?uddg=example.com">No Scheme</a>
        </div>
        <div class="result">
            <a class="result__url" href="/uddg?uddg=https%3A%2F%2Fexample.com">Valid Site</a>
        </div>
        <div class="result">
            <a class="result__url" href="/uddg?uddg=https%3A%2F%2Fgoogle.com%2Fsearch">Search Engine</a>
        </div>
        '''
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
    def test_max_results_respected(self, mock_get):
        """Test that max_results limits the number of returned results."""
        # Create HTML with 5 result links
        links = '\n'.join([
            f'<div class="result"><a class="result__url" href="/uddg?uddg=https%3A%2F%2Fsite{i}.com">Site {i}</a></div>'
            for i in range(5)
        ])
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = f'<div class="result">{links}</div>'
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

    @patch("scraper.free_lead_discovery.requests.get")
    def test_network_failure_handled(self, mock_get):
        """Test that network failure raises a 500 error."""
        mock_get.side_effect = Exception("Network error")

        payload = {
            "industry": "Digital Marketing Agency",
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
        self.assertIn("Network error", error_msg)

    @patch("scraper.free_lead_discovery.requests.get")
    def test_free_and_enrich_endpoint_compatible(self, mock_get):
        """Test that /api/discover/free-and-enrich remains compatible."""
        # Mock HTML search to return one result
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = '''
        <div class="result">
            <a class="result__url" href="/uddg?uddg=https%3A%2F%2Fexample.com">Example Company</a>
        </div>
        '''
        mock_get.return_value = mock_resp

        payload = {
            "industry": "Digital Marketing Agency",
            "location": "Chandigarh",
            "max_results": 1,
        }
        resp = self.client.post(
            "/api/discover/free-and-enrich",
            data=json.dumps(payload),
            content_type="application/json",
        )
        # The endpoint should return 200 and call the enrichment step.
        # We don't need to mock the enrichment step because we're only testing compatibility.
        # If the endpoint returns 200, it means the discovery step succeeded and enrichment was attempted.
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()