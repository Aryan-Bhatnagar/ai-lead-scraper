import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys

# Ensure project root is on sys.path so that "api" package can be found
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# The app factory lives in api.app – import it after setting the
# PYTHONPATH so the tests can locate the module.
from api.app import create_app

# ---------------------------------------------------------------------------
# Use the production database module for schema, inserts and helpers.
# ---------------------------------------------------------------------------
import scraper.database as db_module

# ---------------------------------------------------------------------------
# Helper function to build a sample lead dictionary.
# ---------------------------------------------------------------------------

def _make_lead(lead_id: int, name: str, status: str, data_quality: str):
    """Return a dict suitable for db_module.upsert_lead."""
    return {
        "company_name": name,
        "status": status,
        "data_quality": data_quality,
        "quality_score": 100,
        "source_url": f"https://example.com/lead{lead_id}"
    }

# ---------------------------------------------------------------------------
# Sample data. Values are simple; only the fields used in the tests are set.
# ---------------------------------------------------------------------------
SAMPLE_LEADS = [
    _make_lead(1, "Alice", "success", "HIGH"),
    _make_lead(2, "Bob", "failed", "LOW"),
    _make_lead(3, "Eve", "success", "LOW"),
]

# ---------------------------------------------------------------------------
# For jobs we store a list of URLs per job. create_scrape_job will generate
# the job and the corresponding job items.
# ---------------------------------------------------------------------------
SAMPLE_JOB_URLS = [
    ["https://example.com/a1", "https://example.com/a2"],
    ["https://example.com/b1"],
]

class FlaskAPITest(unittest.TestCase):
    def setUp(self):
        # Create a temporary SQLite file and populate it.
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db_path = Path(self.temp_db.name)
        self.temp_db.close()

        # Initialise the database with the real schema.
        db_module.initialize_database(self.temp_db_path)

        # Insert leads.
        for lead in SAMPLE_LEADS:
            db_module.upsert_lead(lead, self.temp_db_path)

        # Create jobs and their associated items.
        self.job_ids = []
        for urls in SAMPLE_JOB_URLS:
            job_id = db_module.create_scrape_job(urls, self.temp_db_path)
            self.job_ids.append(job_id)

        # Create the app using the temp db.
        self.app = create_app({"TESTING": True, "DATABASE": str(self.temp_db_path)})
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.temp_db_path)

    # ---------- Health -------------------------------------------------
    def test_health(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"status": "ok"})

    # ---------- Leads list (empty) -------------------------------------
    def test_empty_leads_list(self):
        # Remove all leads
        conn = sqlite3.connect(self.temp_db_path)
        conn.execute("DELETE FROM leads")
        conn.commit()
        conn.close()

        resp = self.client.get("/api/leads")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["leads"], [])

    # ---------- Lead listing --------------------------------------------
    def test_leads_list(self):
        resp = self.client.get("/api/leads")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["leads"]), 3)

    # ---------- Filtering ----------------------------------------------
    def test_status_filter(self):
        resp = self.client.get("/api/leads?status=success")
        data = resp.get_json()
        self.assertEqual(data["count"], 2)
        self.assertTrue(all(l["status"] == "success" for l in data["leads"]))

    def test_data_quality_filter(self):
        resp = self.client.get("/api/leads?data_quality=HIGH")
        data = resp.get_json()
        self.assertEqual(data["count"], 1)
        self.assertTrue(all(l["data_quality"] == "HIGH" for l in data["leads"]))

    # ---------- Get single lead -----------------------------------------
    def test_get_lead_by_id(self):
        resp = self.client.get("/api/leads/1")
        self.assertEqual(resp.status_code, 200)
        lead = resp.get_json()
        self.assertEqual(lead["id"], 1)
        self.assertEqual(lead["company_name"], "Alice")

    def test_get_nonexistent_lead(self):
        resp = self.client.get("/api/leads/999")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("error", resp.get_json())

    # ---------- Delete lead --------------------------------------------
    def test_delete_lead(self):
        resp = self.client.delete("/api/leads/1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"deleted": True})
        # Verify removal
        resp2 = self.client.get("/api/leads/1")
        self.assertEqual(resp2.status_code, 404)

    def test_delete_missing_lead(self):
        resp = self.client.delete("/api/leads/999")
        self.assertEqual(resp.status_code, 404)

    # ---------- Jobs --------------------------------------------
    def test_get_jobs(self):
        resp = self.client.get("/api/jobs")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["jobs"]), 2)

    def test_get_job_by_id(self):
        resp = self.client.get("/api/jobs/1")
        self.assertEqual(resp.status_code, 200)
        job = resp.get_json()
        self.assertEqual(job["id"], 1)

    def test_get_missing_job(self):
        resp = self.client.get("/api/jobs/999")
        self.assertEqual(resp.status_code, 404)

    # ---------- Job items --------------------------------------------
    def test_job_items(self):
        resp = self.client.get("/api/jobs/1/items")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["items"]), 2)

    def test_job_items_nonexistent_job(self):
        resp = self.client.get("/api/jobs/999/items")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["items"], [])

if __name__ == "__main__":
    unittest.main()
