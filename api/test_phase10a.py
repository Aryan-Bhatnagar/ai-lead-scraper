"""Tests for Phase 10A – CRM Lead Status Management.

These tests verify:
* Database migration adds a ``lead_status`` column with default ``NEW``.
* New leads default to ``NEW``.
* The ``PATCH /api/leads/<id>/status`` endpoint validates input and updates the
  CRM status.
* ``GET /api/leads`` returns the ``lead_status`` field and supports filtering by
  ``lead_status``.
* Re‑scraping (upserting) a lead does **not** reset a manually changed
  ``lead_status``.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure the project root is on ``sys.path`` so imports resolve.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.app import create_app
import scraper.database as db_module


class Phase10ATest(unittest.TestCase):
    def setUp(self):
        # Temporary SQLite DB for isolation.
        self.temp_db_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db_path = Path(self.temp_db_file.name)
        self.temp_db_file.close()
        # Initialise the DB – this will also run the migration for old DBs.
        db_module.initialize_database(self.temp_db_path)
        # Flask test client.
        self.app = create_app({"TESTING": True, "DATABASE": str(self.temp_db_path)})
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.temp_db_path)

    def test_database_migration_adds_lead_status_column(self):
        # Simulate an older DB that lacks the ``lead_status`` column.
        # Create a fresh DB using the original schema (without the column).
        old_schema = """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            industry TEXT,
            company_description TEXT,
            contact_name TEXT,
            contact_role TEXT,
            email TEXT,
            phone TEXT,
            website TEXT,
            city TEXT,
            country TEXT,
            source_url TEXT UNIQUE,
            source_pages TEXT,
            email_source_page TEXT,
            email_source_type TEXT,
            phone_source_page TEXT,
            phone_source_type TEXT,
            scraped_at TEXT,
            status TEXT,
            quality_score INTEGER,
            data_quality TEXT,
            error TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """
        # Build a DB with the old schema.
        with db_module.get_connection(self.temp_db_path) as conn:
            conn.executescript(old_schema)
        # Run the migration logic (initialize_database) – it should add the column.
        db_module.initialize_database(self.temp_db_path)
        # Verify ``lead_status`` exists and defaults to 'NEW' for a new row.
        lead = {
            "company_name": "MigrateCo",
            "source_url": "https://migrate.example.com",
        }
        lead_id = db_module.upsert_lead(lead, self.temp_db_path)
        row = db_module.get_lead_by_id(lead_id, self.temp_db_path)
        self.assertIn("lead_status", row)
        self.assertEqual(row["lead_status"], "NEW")

    def test_new_lead_defaults_to_new_status(self):
        lead = {"company_name": "NewCo", "source_url": "https://new.example.com"}
        lead_id = db_module.upsert_lead(lead, self.temp_db_path)
        stored = db_module.get_lead_by_id(lead_id, self.temp_db_path)
        self.assertEqual(stored["lead_status"], "NEW")

    def test_patch_lead_status_success(self):
        # Insert a lead.
        lead = {"company_name": "PatchCo", "source_url": "https://patch.example.com"}
        lead_id = db_module.upsert_lead(lead, self.temp_db_path)
        # Perform PATCH request.
        resp = self.client.patch(f"/api/leads/{lead_id}/status", json={"lead_status": "QUALIFIED"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["lead_status"], "QUALIFIED")
        # Verify in DB.
        stored = db_module.get_lead_by_id(lead_id, self.temp_db_path)
        self.assertEqual(stored["lead_status"], "QUALIFIED")

    def test_patch_lead_status_invalid_status(self):
        lead = {"company_name": "BadCo", "source_url": "https://bad.example.com"}
        lead_id = db_module.upsert_lead(lead, self.temp_db_path)
        resp = self.client.patch(f"/api/leads/{lead_id}/status", json={"lead_status": "INVALID"})
        self.assertEqual(resp.status_code, 400)

    def test_patch_lead_status_missing_field(self):
        lead = {"company_name": "MissingCo", "source_url": "https://missing.example.com"}
        lead_id = db_module.upsert_lead(lead, self.temp_db_path)
        resp = self.client.patch(f"/api/leads/{lead_id}/status", json={})
        self.assertEqual(resp.status_code, 400)

    def test_patch_lead_status_unknown_id(self):
        # Use an ID that does not exist.
        resp = self.client.patch("/api/leads/99999/status", json={"lead_status": "NEW"})
        self.assertEqual(resp.status_code, 404)

    def test_get_leads_returns_lead_status_and_filtering(self):
        # Insert two leads with different statuses.
        lead1 = {"company_name": "LeadOne", "source_url": "https://lead1.com"}
        lead2 = {"company_name": "LeadTwo", "source_url": "https://lead2.com"}
        id1 = db_module.upsert_lead(lead1, self.temp_db_path)
        id2 = db_module.upsert_lead(lead2, self.temp_db_path)
        # Update lead2 to QUALIFIED.
        db_module.update_lead_status(id2, "QUALIFIED", self.temp_db_path)
        # GET all leads – both should be present with proper lead_status.
        resp = self.client.get("/api/leads")
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertEqual(payload["count"], 2)
        ids = {l["id"] for l in payload["leads"]}
        self.assertIn(id1, ids)
        self.assertIn(id2, ids)
        # Filter by lead_status=QUALIFIED – only lead2 should appear.
        resp2 = self.client.get("/api/leads?lead_status=QUALIFIED")
        self.assertEqual(resp2.status_code, 200)
        payload2 = resp2.get_json()
        self.assertEqual(payload2["count"], 1)
        self.assertEqual(payload2["leads"][0]["id"], id2)
        self.assertEqual(payload2["leads"][0]["lead_status"], "QUALIFIED")

    def test_upsert_does_not_reset_manual_lead_status(self):
        lead = {"company_name": "RescrapeCo", "source_url": "https://rescrape.example.com"}
        lead_id = db_module.upsert_lead(lead, self.temp_db_path)
        # Manually set status to CONTACTED.
        db_module.update_lead_status(lead_id, "CONTACTED", self.temp_db_path)
        # Upsert the same lead with a different company_name (simulating a rescrape).
        lead_update = {"company_name": "RescrapeCoUpdated", "source_url": "https://rescrape.example.com"}
        db_module.upsert_lead(lead_update, self.temp_db_path)
        # Verify that lead_status stayed CONTACTED.
        stored = db_module.get_lead_by_id(lead_id, self.temp_db_path)
        self.assertEqual(stored["lead_status"], "CONTACTED")
        # Also verify that other fields were updated (company_name).
        self.assertEqual(stored["company_name"], "RescrapeCoUpdated")

if __name__ == "__main__":
    unittest.main()
