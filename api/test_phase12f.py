"""
Unit tests for Phase 12F: Standalone Email Extractor.
Tests mock external calls to avoid network/LLM dependencies.
"""
import json
import unittest
from unittest.mock import patch, MagicMock

from api.app import create_app


class TestPhase12FEmailExtractor(unittest.TestCase):
    def setUp(self):
        """Set up test client and mock database."""
        self.app = create_app({"TESTING": True, "DATABASE": ":memory:"})
        self.client = self.app.test_client()
        # Initialize in-memory database
        with self.app.app_context():
            from scraper.database import initialize_database, get_connection
            initialize_database()
            with get_connection() as conn:
                conn.execute("SELECT 1")

    # -----------------------------------------------------------------
    # Test extract_emails_batch function directly
    # -----------------------------------------------------------------
    @patch("scraper.email_extractor.enrich_email_for_lead")
    def test_extract_emails_batch_function(self, mock_enrich):
        """Test the extract_emails_batch function returns correct results."""
        from scraper.email_extractor import extract_emails_batch

        mock_enrich.return_value = {
            "website": "https://acme.com",
            "company_name": "Acme Corp",
            "email": "sales@acme.com",
            "email_source_page": "https://acme.com",
            "email_source_type": "mailto",
            "pages_checked": ["https://acme.com"],
        }

        leads = [{"website": "https://acme.com", "company_name": "Acme Corp"}]
        result = extract_emails_batch(leads)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["email"], "sales@acme.com")
        self.assertEqual(result[0]["company_name"], "Acme Corp")
        mock_enrich.assert_called_once()

    # -----------------------------------------------------------------
    # Test API endpoint: POST /api/leads/extract-emails
    # -----------------------------------------------------------------
    @patch("scraper.email_extractor.extract_emails_batch")
    def test_extract_emails_endpoint_success(self, mock_batch):
        """Test POST /api/leads/extract-emails with valid data."""
        mock_batch.return_value = [
            {
                "website": "https://acme.com",
                "email": "sales@acme.com",
                "email_source_page": "https://acme.com",
                "email_source_type": "mailto",
            }
        ]

        payload = {"leads": [{"website": "https://acme.com"}]}
        response = self.client.post(
            "/api/leads/extract-emails",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["email"], "sales@acme.com")
        self.assertEqual(data["results"][0]["website"], "https://acme.com")
        mock_batch.assert_called_once()

    def test_extract_emails_endpoint_missing_body(self):
        """Test POST /api/leads/extract-emails with no body."""
        response = self.client.post(
            "/api/leads/extract-emails",
            data=b"",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_extract_emails_endpoint_missing_leads_key(self):
        """Test POST /api/leads/extract-emails missing leads field."""
        payload = {"not_leads": []}
        response = self.client.post(
            "/api/leads/extract-emails",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_extract_emails_endpoint_empty_leads_list(self):
        """Test POST /api/leads/extract-emails with empty leads list."""
        payload = {"leads": []}
        response = self.client.post(
            "/api/leads/extract-emails",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_extract_emails_endpoint_lead_no_website(self):
        """Test POST /api/leads/extract-emails with lead missing website."""
        payload = {"leads": [{"company_name": "Acme"}]}
        response = self.client.post(
            "/api/leads/extract-emails",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_extract_emails_endpoint_invalid_json(self):
        """Test POST /api/leads/extract-emails with malformed JSON."""
        response = self.client.post(
            "/api/leads/extract-emails",
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("scraper.email_extractor.extract_emails_batch")
    def test_extract_emails_endpoint_extraction_error(self, mock_batch):
        """Test POST /api/leads/extract-emails when extraction raises an exception."""
        mock_batch.side_effect = Exception("Extraction failed")
        payload = {"leads": [{"website": "https://acme.com"}]}
        response = self.client.post(
            "/api/leads/extract-emails",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_extract_emails_endpoint_leads_not_list(self):
        """Test POST /api/leads/extract-emails with leads not a list."""
        payload = {"leads": "not a list"}
        response = self.client.post(
            "/api/leads/extract-emails",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_extract_emails_endpoint_lead_not_dict(self):
        """Test POST /api/leads/extract-emails with lead not a dict."""
        payload = {"leads": ["not a dict"]}
        response = self.client.post(
            "/api/leads/extract-emails",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    # -----------------------------------------------------------------
    # Ensure existing endpoints still work (backward compatibility)
    # -----------------------------------------------------------------
    @patch("scraper.lead_enrichment.enrich_leads")
    def test_enrich_endpoint_still_works(self, mock_enrich):
        """Test that /api/leads/enrich is not broken by Phase 12F."""
        mock_enrich.return_value = [
            {"website": "https://example.com", "email": "info@example.com"}
        ]
        payload = {"leads": [{"website": "https://example.com"}]}
        response = self.client.post(
            "/api/leads/enrich",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
