import unittest
from unittest.mock import patch

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scraper.lead_discovery import (
    build_search_query,
    discover_leads,
    is_blocked_domain,
    normalize_url,
)


class LeadDiscoveryTest(unittest.TestCase):

    def test_build_search_query(self):
        query = build_search_query(
            "software companies",
            "Chandigarh",
        )

        self.assertEqual(
            query,
            "software companies Chandigarh",
        )

    def test_empty_industry_rejected(self):
        with self.assertRaises(ValueError):
            build_search_query("", "Chandigarh")

    def test_empty_location_rejected(self):
        with self.assertRaises(ValueError):
            build_search_query("software companies", "")

    def test_normalize_url(self):
        url = normalize_url(
            "https://www.example.com/about?source=test"
        )

        self.assertEqual(
            url,
            "https://example.com",
        )

    def test_invalid_url_rejected(self):
        self.assertEqual(
            normalize_url("not-a-url"),
            "",
        )

    def test_blocked_domain(self):
        self.assertTrue(
            is_blocked_domain("https://linkedin.com")
        )

        self.assertTrue(
            is_blocked_domain("https://www.goodfirms.co")
        )

        self.assertFalse(
            is_blocked_domain("https://example.com")
        )

    @patch("scraper.lead_discovery.DDGS")
    def test_discover_leads(self, mock_ddgs):
        mock_ddgs.return_value.text.return_value = [
            {
                "title": "Example Company",
                "href": "https://www.example.com/about",
                "body": "Example software company.",
            },
            {
                "title": "Example Company Duplicate",
                "href": "https://example.com/contact",
                "body": "Duplicate result.",
            },
            {
                "title": "LinkedIn",
                "href": "https://linkedin.com/company/example",
                "body": "Social profile.",
            },
            {
                "title": "Second Company",
                "href": "https://second-example.com",
                "body": "Another company.",
            },
        ]

        results = discover_leads(
            industry="software companies",
            location="Chandigarh",
            max_results=10,
        )

        self.assertEqual(len(results), 2)

        self.assertEqual(
            results[0]["url"],
            "https://example.com",
        )

        self.assertEqual(
            results[1]["url"],
            "https://second-example.com",
        )

    def test_invalid_max_results(self):
        with self.assertRaises(ValueError):
            discover_leads(
                "software companies",
                "Chandigarh",
                0,
            )


if __name__ == "__main__":
    unittest.main()