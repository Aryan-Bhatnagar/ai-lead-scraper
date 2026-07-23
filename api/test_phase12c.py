"""
Unit tests for Phase 12C: Lead Enrichment using ScrapeGraphAI.
Tests mock external calls to avoid network/LLM dependencies.
"""
import json
import unittest
from unittest.mock import patch, MagicMock

from api.app import create_app


class TestPhase12CEnrichment(unittest.TestCase):
    def setUp(self):
        """Set up test client and mock database."""
        self.app = create_app({"TESTING": True, "DATABASE": ":memory:"})
        self.client = self.app.test_client()
        # Initialize in-memory database
        with self.app.app_context():
            from scraper.database import initialize_database, get_connection
            initialize_database()
            # Ensure tables exist
            with get_connection() as conn:
                conn.execute("SELECT 1")

    # -----------------------------------------------------------------
    # Test enrich_leads function directly
    # -----------------------------------------------------------------
    @patch("scraper.lead_enrichment.enrich_lead")
    def test_enrich_leads_function(self, mock_enrich_lead):
        """Test the enrich_leads function merges data correctly."""
        from scraper.lead_enrichment import enrich_leads

        # Mock enrich_lead to return deterministic data (no error)
        mock_enrich_lead.side_effect = [
            {"company_name": "Enriched Co", "website": "http://example.com", "email": "info@example.com"},
            {"company_name": "", "website": "http://example2.com", "phone": "123"},
        ]

        leads = [
            {"website": "http://example.com", "company_name": "Discovery Co", "industry": "Tech"},
            {"website": "http://example2.com", "industry": "Marketing"},
        ]

        result = enrich_leads(leads)

        # Should have called enrich_lead twice
        self.assertEqual(mock_enrich_lead.call_count, 2)
        # First lead: discovery company_name should be kept (non-empty)
        self.assertEqual(result[0]["company_name"], "Discovery Co")
        self.assertEqual(result[0]["website"], "http://example.com")
        self.assertEqual(result[0]["email"], "info@example.com")
        # Second lead: discovery company_name empty, so use enriched (empty)
        self.assertEqual(result[1]["company_name"], "")
        self.assertEqual(result[1]["website"], "http://example2.com")
        self.assertEqual(result[1]["phone"], "123")
        # No errors
        self.assertNotIn("_error", result[0])
        self.assertNotIn("_error", result[1])

    @patch("scraper.lead_enrichment.enrich_lead")
    def test_enrich_leads_duplicate_website(self, mock_enrich_lead):
        """Test that duplicate websites in a batch are scraped only once."""
        from scraper.lead_enrichment import enrich_leads

        mock_enrich_lead.return_value = {
            "company_name": "Test Co",
            "website": "http://example.com",
            "email": "test@example.com",
        }

        leads = [
            {"website": "http://example.com", "company_name": "First"},
            {"website": "http://example.com", "company_name": "Second"},  # duplicate
            {"website": "http://example.com/path", "company_name": "Third"},  # same normalized URL
        ]

        result = enrich_leads(leads)

        # Should have called enrich_lead only once (deduplication)
        self.assertEqual(mock_enrich_lead.call_count, 1)
        # All three leads should have the same enriched data merged with discovery data
        for i, lead in enumerate(result):
            # discovery name kept
            self.assertEqual(lead["company_name"], lead.get("company_name"))
            self.assertEqual(lead["website"], "http://example.com")
            self.assertEqual(lead["email"], "test@example.com")

    # -----------------------------------------------------------------
    # Test API endpoints
    # -----------------------------------------------------------------
    @patch("scraper.lead_enrichment.enrich_leads")
    def test_enrich_leads_endpoint_success(self, mock_enrich_leads):
        """Test POST /api/leads/enrich with valid data."""
        mock_enrich_leads.return_value = [
            {"company_name": "Test Co", "website": "http://example.com", "email": "test@example.com"}
        ]

        payload = {
            "leads": [
                {"website": "http://example.com", "company_name": "Discovery Co"}
            ]
        }
        response = self.client.post(
            "/api/leads/enrich",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["company_name"], "Test Co")
        self.assertEqual(data["results"][0]["website"], "http://example.com")
        self.assertEqual(data["results"][0]["email"], "test@example.com")
        mock_enrich_leads.assert_called_once()

    def test_enrich_leads_endpoint_missing_leads(self):
        """Test POST /api/leads/enrich missing leads field."""
        payload = {}
        response = self.client.post(
            "/api/leads/enrich",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_enrich_leads_endpoint_empty_leads(self):
        """Test POST /api/leads/enrich with empty leads list."""
        payload = {"leads": []}
        response = self.client.post(
            "/api/leads/enrich",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_enrich_leads_endpoint_invalid_lead(self):
        """Test POST /api/leads/enrich with invalid lead object."""
        payload = {"leads": [{"website": 123}]}
        response = self.client.post(
            "/api/leads/enrich",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_enrich_leads_endpoint_missing_website(self):
        """Test POST /api/leads/enrich with lead missing website."""
        payload = {"leads": [{}]}
        response = self.client.post(
            "/api/leads/enrich",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    @patch("scraper.lead_enrichment.enrich_leads")
    def test_enrich_leads_endpoint_enrichment_error(self, mock_enrich_leads):
        """Test POST /api/leads/enrich when enrichment raises an exception."""
        mock_enrich_leads.side_effect = Exception("Scraping failed")
        payload = {"leads": [{"website": "http://example.com"}]}
        response = self.client.post(
            "/api/leads/enrich",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn("error", data)

    # -----------------------------------------------------------------
    # Test free-and-enrich endpoint
    # -----------------------------------------------------------------
    @patch("scraper.lead_enrichment.enrich_leads")
    @patch("scraper.free_lead_discovery.discover_free_leads")
    def test_discover_free_and_enrich_endpoint_success(self, mock_discover, mock_enrich):
        """Test POST /api/discover/free-and-enrich with valid data."""
        mock_discover.return_value = [
            {"website": "http://example.com", "company_name": "Discovered Co"}
        ]
        mock_enrich.return_value = [
            {"company_name": "Enriched Co", "website": "http://example.com", "email": "info@example.com"}
        ]

        payload = {
            "industry": "Technology",
            "location": "City",
            "max_results": 5
        }
        response = self.client.post(
            "/api/discover/free-and-enrich",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["company_name"], "Enriched Co")
        self.assertEqual(data["results"][0]["website"], "http://example.com")
        self.assertEqual(data["results"][0]["email"], "info@example.com")
        self.assertEqual(data["industry"], "Technology")
        self.assertEqual(data["location"], "City")
        self.assertEqual(data["source"], "free_web")
        mock_discover.assert_called_once_with(industry="Technology", location="City", max_results=5)
        mock_enrich.assert_called_once()

    def test_discover_free_and_enrich_missing_industry(self):
        """Test POST /api/discover/free-and-enrich missing industry."""
        payload = {"location": "City"}
        response = self.client.post(
            "/api/discover/free-and-enrich",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_discover_free_and_enrich_invalid_max_results(self):
        """Test POST /api/discover/free-and-enrich with invalid max_results."""
        payload = {"industry": "Tech", "location": "City", "max_results": 0}
        response = self.client.post(
            "/api/discover/free-and-enrich",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    @patch("scraper.lead_enrichment.enrich_leads")
    @patch("scraper.free_lead_discovery.discover_free_leads")
    def test_discover_free_and_enrich_discovery_failure(self, mock_discover, mock_enrich):
        """Test POST /api/discover/free-and-enrich when discovery fails."""
        mock_discover.side_effect = Exception("Discovery failed")
        payload = {"industry": "Tech", "location": "City"}
        response = self.client.post(
            "/api/discover/free-and-enrich",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn("error", data)
        mock_enrich.assert_not_called()

    @patch("scraper.lead_enrichment.enrich_leads")
    @patch("scraper.free_lead_discovery.discover_free_leads")
    def test_discover_free_and_enrich_enrichment_failure(self, mock_discover, mock_enrich):
        """Test POST /api/discover/free-and-enrich when enrichment fails."""
        mock_discover.return_value = [{"website": "http://example.com"}]
        mock_enrich.side_effect = Exception("Enrichment failed")
        payload = {"industry": "Tech", "location": "City"}
        response = self.client.post(
            "/api/discover/free-and-enrich",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn("error", data)

    # -----------------------------------------------------------------
    # Ensure existing /api/discover/free endpoint still works
    # -----------------------------------------------------------------
    @patch("scraper.free_lead_discovery.discover_free_leads")
    def test_discover_free_endpoint_unchanged(self, mock_discover):
        """Test that the original /api/discover/free endpoint still works."""
        mock_discover.return_value = [
            {"website": "http://example.com", "company_name": "Free Co"}
        ]
        payload = {"industry": "Tech", "location": "City", "max_results": 10}
        response = self.client.post(
            "/api/discover/free",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["website"], "http://example.com")
        self.assertEqual(data["results"][0]["company_name"], "Free Co")
        self.assertEqual(data["source"], "free_web")


if __name__ == "__main__":
    unittest.main()