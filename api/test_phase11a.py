"""Tests for Phase 11A – Automated outreach processing.

These tests verify the new batch processor endpoint ``POST /api/outreach/process``.
The processor should:
* select eligible ``PENDING`` or ``FAILED`` entries (respecting a retry limit),
* dispatch each entry using the shared dispatch logic,
* correctly transition statuses and attempt counts,
* return a JSON summary of the operation.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import requests

# Ensure project root is importable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scraper.database as db_module
from api.app import create_app

class Phase11ATest(unittest.TestCase):
    def setUp(self):
        # Temporary DB.
        self.temp_db_file = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = Path(self.temp_db_file.name)
        self.temp_db_file.close()
        db_module.initialize_database(self.db_path)
        self.app = create_app({"TESTING": True, "DATABASE": str(self.db_path)})
        self.client = self.app.test_client()
        # Create a qualified lead for outreach entries.
        self.lead_id = self._create_qualified_lead()

    def tearDown(self):
        os.unlink(self.db_path)

    def _create_qualified_lead(self, lead_status="QUALIFIED", email="test@example.com", phone="+1234567890"):
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

    @patch("api.app.requests.post")
    def test_process_batch_success_and_failure(self, mock_post):
        """A batch with one successful and one failing dispatch returns the correct summary."""
        os.environ["OUTREACH_WEBHOOK_URL"] = "http://example.com/webhook"
        # Create two outreach entries (both start as PENDING).
        entry1 = db_module.create_outreach_entry(self.lead_id, "EMAIL", self.db_path)
        entry2 = db_module.create_outreach_entry(self.lead_id, "CALL", self.db_path)

        # Configure mock: first call succeeds, second raises.
        mock_success = Mock()
        mock_success.raise_for_status.return_value = None
        mock_post.side_effect = [mock_success, requests.RequestException("boom")]

        resp = self.client.post("/api/outreach/process")
        self.assertEqual(resp.status_code, 200)
        summary = resp.get_json()
        self.assertEqual(summary.get("processed"), 2)
        self.assertEqual(summary.get("sent"), 1)
        self.assertEqual(summary.get("failed"), 1)
        self.assertEqual(summary.get("skipped"), 0)

        # Verify DB state.
        e1 = db_module.get_outreach_entry_by_id(entry1, self.db_path)
        e2 = db_module.get_outreach_entry_by_id(entry2, self.db_path)
        self.assertEqual(e1["outreach_status"], "SENT")
        self.assertEqual(e1["attempt_count"], 1)
        self.assertEqual(e2["outreach_status"], "FAILED")
        self.assertEqual(e2["attempt_count"], 1)
        self.assertIn("boom", e2["error_message"])

    @patch("api.app.requests.post")
    def test_process_batch_empty_queue(self, mock_post):
        """When there are no eligible entries the summary reports zeros."""
        os.environ["OUTREACH_WEBHOOK_URL"] = "http://example.com/webhook"
        # No outreach entries created.
        resp = self.client.post("/api/outreach/process")
        self.assertEqual(resp.status_code, 200)
        summary = resp.get_json()
        self.assertEqual(summary, {"processed": 0, "sent": 0, "failed": 0, "skipped": 0})
        # Ensure no webhook was attempted.
        mock_post.assert_not_called()

    @patch("api.app.requests.post")
    def test_missing_webhook_configuration(self, mock_post):
        """If the webhook URL env var is unset, the processor returns a 500 error."""
        os.environ.pop("OUTREACH_WEBHOOK_URL", None)
        # Create a pending entry.
        db_module.create_outreach_entry(self.lead_id, "EMAIL", self.db_path)
        resp = self.client.post("/api/outreach/process")
        self.assertEqual(resp.status_code, 500)
        data = resp.get_json()
        self.assertIn("OUTREACH_WEBHOOK_URL is not configured", data.get("error", ""))
        mock_post.assert_not_called()

if __name__ == "__main__":
    unittest.main()
