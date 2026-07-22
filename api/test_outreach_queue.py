import os
import sys
import tempfile
import unittest
from pathlib import Path
import json

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scraper.database as db_module
from api.app import create_app

class OutreachQueueTest(unittest.TestCase):
    def setUp(self):
        # temporary DB
        self.temp_db_file = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = Path(self.temp_db_file.name)
        self.temp_db_file.close()
        # init DB schema (including outreach_queue)
        db_module.initialize_database(self.db_path)
        # create a Flask app with this DB
        self.app = create_app({"TESTING": True, "DATABASE": str(self.db_path)})
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.db_path)

    def _create_lead(self, lead_status="QUALIFIED", email="test@example.com", phone="+1234567890"):
        lead = {
            "company_name": "TestCo",
            "source_url": f"https://{lead_status.lower()}.example.com",
            "lead_status": lead_status,
            "email": email,
            "phone": phone,
        }
        lead_id = db_module.upsert_lead(lead, self.db_path)
        # After upserting, explicitly set the CRM lead_status using the helper.
        # The `upsert_lead` function deliberately excludes `lead_status` to preserve
        # manual status management (Phase 10A).  For the outreach queue tests we need
        # the status to be set, so we update it here.
        db_module.update_lead_status(lead_id, lead_status, self.db_path)
        return lead_id

    def test_fresh_db_has_outreach_table(self):
        # Verify table exists via pragma
        info = db_module.get_outreach_entries(self.db_path)
        self.assertIsInstance(info, list)

    def test_get_outreach_includes_company_name(self):
        # Create a qualified lead with a known company name
        lead_id = self._create_lead()
        # Queue an outreach entry for the lead
        resp = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        self.assertEqual(resp.status_code, 201)
        entry = resp.get_json()
        # Verify the response includes the company_name from the lead
        self.assertEqual(entry.get("company_name"), "TestCo")
        # Verify a GET request also returns the company_name
        list_resp = self.client.get('/api/outreach', query_string={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        self.assertEqual(list_resp.status_code, 200)
        entries = list_resp.get_json()["outreach"]
        self.assertTrue(any(e.get("company_name") == "TestCo" for e in entries))
    def test_migration_adds_outreach_table(self):
        # Build old schema DB without outreach_queue
        old_schema = """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            source_url TEXT UNIQUE,
            lead_status TEXT NOT NULL DEFAULT 'NEW',
            created_at TEXT,
            updated_at TEXT
        );
        """
        with db_module.get_connection(self.db_path) as conn:
            conn.executescript(old_schema)
        # run migration
        db_module.initialize_database(self.db_path)
        # check outreach table exists
        entries = db_module.get_outreach_entries(self.db_path)
        self.assertIsInstance(entries, list)

    def test_eligible_lead_can_be_queued(self):
        lead_id = self._create_lead()
        resp = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["lead_id"], lead_id)
        self.assertEqual(data["outreach_channel"], "EMAIL")
        self.assertEqual(data["outreach_status"], "PENDING")

    def test_new_lead_cannot_be_queued(self):
        lead_id = self._create_lead(lead_status="NEW")
        resp = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("not eligible", resp.get_json().get("error", ""))

    def test_email_requires_email(self):
        lead_id = self._create_lead(email="")
        resp = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("missing email", resp.get_json().get("error", "").lower())

    def test_whatsapp_requires_phone(self):
        lead_id = self._create_lead(phone="")
        resp = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "WHATSAPP"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("missing phone", resp.get_json().get("error", "").lower())

    def test_duplicate_active_entry_rejected(self):
        lead_id = self._create_lead()
        # first creation
        r1 = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        self.assertEqual(r1.status_code, 201)
        # second attempt same channel should fail
        r2 = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        self.assertEqual(r2.status_code, 400)
        self.assertIn("active outreach entry", r2.get_json().get("error", ""))

    def test_different_channels_allowed(self):
        lead_id = self._create_lead()
        r1 = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        self.assertEqual(r1.status_code, 201)
        r2 = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "CALL"})
        self.assertEqual(r2.status_code, 201)

    def test_attempt_count_increment_on_processing(self):
        lead_id = self._create_lead()
        # create entry
        r = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        entry = r.get_json()
        entry_id = entry["id"]
        # transition to PROCESSING
        r2 = self.client.patch(f'/api/outreach/{entry_id}', json={"outreach_status": "PROCESSING"})
        self.assertEqual(r2.status_code, 200)
        data = r2.get_json()
        self.assertEqual(data["outreach_status"], "PROCESSING")
        self.assertEqual(data["attempt_count"], 1)
        # transition to SENT, attempt_count should stay 1
        r3 = self.client.patch(f'/api/outreach/{entry_id}', json={"outreach_status": "SENT"})
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.get_json()["attempt_count"], 1)

    def test_processing_to_failed_no_extra_increment(self):
        lead_id = self._create_lead()
        r = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        entry_id = r.get_json()["id"]
        self.client.patch(f'/api/outreach/{entry_id}', json={"outreach_status": "PROCESSING"})
        r2 = self.client.patch(f'/api/outreach/{entry_id}', json={"outreach_status": "FAILED", "error_message": "oops"})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json()["attempt_count"], 1)
        self.assertEqual(r2.get_json()["outreach_status"], "FAILED")

    def test_failed_allows_new_entry(self):
        lead_id = self._create_lead()
        r = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        entry_id = r.get_json()["id"]
        self.client.patch(f'/api/outreach/{entry_id}', json={"outreach_status": "FAILED"})
        # now create a new entry same channel – should succeed
        r2 = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        self.assertEqual(r2.status_code, 201)
        # verify two entries exist (including failed one)
        list_resp = self.client.get('/api/outreach', query_string={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_resp.get_json()["count"], 2)

    def test_get_filters(self):
        lead_id = self._create_lead()
        # create two entries different channels
        self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "CALL"})
        # filter by channel EMAIL
        resp = self.client.get('/api/outreach', query_string={"outreach_channel": "EMAIL"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["count"], 1)

    def test_delete_restrictions(self):
        lead_id = self._create_lead()
        r = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        entry_id = r.get_json()["id"]
        # delete while PENDING should succeed
        del_resp = self.client.delete(f'/api/outreach/{entry_id}')
        self.assertEqual(del_resp.status_code, 200)
        # recreate and move to SENT
        r2 = self.client.post('/api/outreach', json={"lead_id": lead_id, "outreach_channel": "EMAIL"})
        entry_id2 = r2.get_json()["id"]
        self.client.patch(f'/api/outreach/{entry_id2}', json={"outreach_status": "PROCESSING"})
        self.client.patch(f'/api/outreach/{entry_id2}', json={"outreach_status": "SENT"})
        # attempt delete – should be forbidden
        del2 = self.client.delete(f'/api/outreach/{entry_id2}')
        self.assertEqual(del2.status_code, 400)
        self.assertIn("cannot be deleted", del2.get_json().get("error", ""))

if __name__ == '__main__':
    unittest.main()
