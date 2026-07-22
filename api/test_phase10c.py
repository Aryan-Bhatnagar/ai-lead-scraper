# -*- coding: utf-8 -*-
"""Tests for Phase 10C – Outreach dispatch workflow.

These tests verify:
* Successful dispatch transitions PENDING → PROCESSING → SENT.
* Webhook failure transitions to FAILED and records the error.
* A FAILED entry can be retried, incrementing ``attempt_count`` again.
* SENT entries cannot be dispatched again.
* non‑existent queue IDs return 404.
* Missing ``OUTREACH_WEBHOOK_URL`` results in a 500 error.
* ``requests.post`` receives the correct webhook URL and payload.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

# Ensure the project root is on ``sys.path`` so imports resolve.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scraper.database as db_module
from api.app import create_app
import requests


class Phase10CTest(unittest.TestCase):
    def setUp(self):
        # Temporary SQLite DB for isolation.
        self.temp_db_file = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = Path(self.temp_db_file.name)
        self.temp_db_file.close()
        # Initialise the DB – ensures the outreach_queue table exists.
        db_module.initialize_database(self.db_path)
        # Flask app configured to use the temporary DB.
        self.app = create_app({"TESTING": True, "DATABASE": str(self.db_path)})
        self.client = self.app.test_client()
        # Create a qualified lead (eligible for outreach).
        self.lead_id = self._create_qualified_lead()

    def tearDown(self):
        os.unlink(self.db_path)

    # ---------------------------------------------------------------------
    # Helper utilities
    # ---------------------------------------------------------------------
    def _create_qualified_lead(self, lead_status="QUALIFIED", email="test@example.com", phone="+1234567890"):
        """Insert a lead and set its CRM status.

        The ``upsert_lead`` helper deliberately does not touch ``lead_status``; we set it
        manually so the lead is eligible for outreach.
        """
        lead = {
            "company_name": "TestCo",
            "source_url": f"https://{lead_status.lower()}.example.com",
            "lead_status": lead_status,
            "email": email,
            "phone": phone,
        }
        lead_id = db_module.upsert_lead(lead, self.db_path)
        db_module.update_lead_status(lead_id, lead_status, self.db_path)
        return lead_id

    def _create_outreach_entry(self, channel="EMAIL"):
        """Create a single outreach queue entry for ``self.lead_id``.

        Returns the ``id`` of the new ``outreach_queue`` row.
        """
        return db_module.create_outreach_entry(self.lead_id, channel, self.db_path)

    # ---------------------------------------------------------------------
    # Test cases
    # ---------------------------------------------------------------------
    @patch("api.app.requests.post")
    def test_successful_dispatch(self, mock_post):
        """A PENDING entry should become SENT and have its attempt counted."""
        os.environ["OUTREACH_WEBHOOK_URL"] = "http://example.com/webhook"
        # Mock a successful HTTP response.
        mock_resp = Mock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        entry_id = self._create_outreach_entry()
        resp = self.client.post(f"/api/outreach/{entry_id}/dispatch")
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertEqual(payload["outreach_status"], "SENT")

        # Verify DB reflects the successful transition.
        entry = db_module.get_outreach_entry_by_id(entry_id, self.db_path)
        self.assertEqual(entry["outreach_status"], "SENT")
        self.assertEqual(entry["attempt_count"], 1)
        self.assertIsNotNone(entry["last_contacted_at"])
        self.assertIsNone(entry["error_message"])

        # Verify the webhook was called with the correct URL and payload.
        mock_post.assert_called_once()
        called_url = mock_post.call_args[0][0]
        self.assertEqual(called_url, os.environ["OUTREACH_WEBHOOK_URL"])
        json_payload = mock_post.call_args[1]["json"]
        self.assertEqual(json_payload["queue_id"], entry_id)
        self.assertEqual(json_payload["lead_id"], self.lead_id)
        # The payload should reflect the *pre‑dispatch* status (PENDING).
        self.assertEqual(json_payload["outreach_status"], "PENDING")

    @patch("api.app.requests.post")
    def test_webhook_failure(self, mock_post):
        """A RequestException should transition the entry to FAILED and store the error."""
        os.environ["OUTREACH_WEBHOOK_URL"] = "http://example.com/webhook"
        mock_post.side_effect = requests.RequestException("boom")

        entry_id = self._create_outreach_entry()
        resp = self.client.post(f"/api/outreach/{entry_id}/dispatch")
        self.assertEqual(resp.status_code, 502)
        data = resp.get_json()
        self.assertIn("Webhook dispatch failed", data["error"])

        entry = db_module.get_outreach_entry_by_id(entry_id, self.db_path)
        self.assertEqual(entry["outreach_status"], "FAILED")
        self.assertEqual(entry["attempt_count"], 1)
        self.assertIsNotNone(entry["last_contacted_at"])
        self.assertIn("boom", entry["error_message"])

    @patch("api.app.requests.post")
    def test_retry_failed_outreach(self, mock_post):
        """A FAILED entry should be retryable and increment ``attempt_count`` again."""
        os.environ["OUTREACH_WEBHOOK_URL"] = "http://example.com/webhook"

        entry_id = self._create_outreach_entry()
        # First attempt – force a webhook failure.
        mock_post.side_effect = requests.RequestException("first failure")
        resp1 = self.client.post(f"/api/outreach/{entry_id}/dispatch")
        self.assertEqual(resp1.status_code, 502)
        entry1 = db_module.get_outreach_entry_by_id(entry_id, self.db_path)
        self.assertEqual(entry1["outreach_status"], "FAILED")
        self.assertEqual(entry1["attempt_count"], 1)

        # Reset the mock to simulate a successful second attempt.
        mock_post.side_effect = None
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        resp2 = self.client.post(f"/api/outreach/{entry_id}/dispatch")
        self.assertEqual(resp2.status_code, 200)
        payload2 = resp2.get_json()
        self.assertEqual(payload2["outreach_status"], "SENT")

        entry2 = db_module.get_outreach_entry_by_id(entry_id, self.db_path)
        self.assertEqual(entry2["outreach_status"], "SENT")
        # ``attempt_count`` should now be 2 because the retry incremented it.
        self.assertEqual(entry2["attempt_count"], 2)
        self.assertIsNone(entry2["error_message"])

    @patch("api.app.requests.post")
    def test_sent_entry_cannot_be_dispatched_again(self, mock_post):
        """Attempting to dispatch an entry that is already SENT should be rejected."""
        os.environ["OUTREACH_WEBHOOK_URL"] = "http://example.com/webhook"
        mock_resp = Mock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        entry_id = self._create_outreach_entry()
        # First successful dispatch.
        first = self.client.post(f"/api/outreach/{entry_id}/dispatch")
        self.assertEqual(first.status_code, 200)
        # Second attempt – should be a 400 error.
        second = self.client.post(f"/api/outreach/{entry_id}/dispatch")
        self.assertEqual(second.status_code, 400)
        data = second.get_json()
        self.assertIn("cannot be dispatched", data["error"].lower())

    @patch("api.app.requests.post")
    def test_nonexistent_outreach_id_returns_404(self, mock_post):
        """A request for an ID that does not exist should return 404."""
        os.environ["OUTREACH_WEBHOOK_URL"] = "http://example.com/webhook"
        # Mock a successful response – it will never be hit because the entry is missing.
        mock_resp = Mock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        resp = self.client.post("/api/outreach/999999/dispatch")
        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertIn("Outreach entry not found", data["error"])

    @patch("api.app.requests.post")
    def test_missing_webhook_url_error(self, mock_post):
        """If ``OUTREACH_WEBHOOK_URL`` is not set the endpoint should error with 500."""
        os.environ.pop("OUTREACH_WEBHOOK_URL", None)
        entry_id = self._create_outreach_entry()
        resp = self.client.post(f"/api/outreach/{entry_id}/dispatch")
        self.assertEqual(resp.status_code, 500)
        data = resp.get_json()
        self.assertIn("OUTREACH_WEBHOOK_URL is not configured", data["error"])


if __name__ == "__main__":
    unittest.main()
