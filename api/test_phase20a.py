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

from api.app import create_app
import scraper.database as db_module


def _make_lead(lead_id: int, name: str, status: str, data_quality: str, source_url: str):
    """Return a dict suitable for db_module.upsert_lead."""
    return {
        "company_name": name,
        "status": status,
        "data_quality": data_quality,
        "quality_score": 100,
        "source_url": source_url,
        "website": f"https://{name.lower().replace(' ', '')}.com",
        "email": f"contact@{name.lower().replace(' ', '')}.com",
        "phone": "+1-555-1234",
        "city": "Anytown",
        "country": "USA",
        "company_description": f"A great company named {name}",
        "contact_name": "John Doe",
        "contact_role": "CEO",
    }


class FlaskAPITestPhase20A(unittest.TestCase):
    def setUp(self):
        # Create a temporary SQLite file and populate it.
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db_path = Path(self.temp_db.name)
        self.temp_db.close()

        # Initialise the database with the real schema.
        db_module.initialize_database(self.temp_db_path)

        # Insert a few leads for testing.
        self.lead_ids = []
        for i in range(3):
            lead = _make_lead(
                i+1,
                f"Company {i+1}",
                "success",
                "HIGH",
                f"https://example.com/lead{i+1}"
            )
            lead_id = db_module.upsert_lead(lead, self.temp_db_path)
            self.lead_ids.append(lead_id)

        # Create the app using the temp db.
        self.app = create_app({"TESTING": True, "DATABASE": str(self.temp_db_path)})
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.temp_db_path)

    # ---------- Lead CRUD endpoints ----------
    def test_create_lead(self):
        payload = {
            "company_name": "NewCo",
            "website": "https://newco.com",
            "email": "info@newco.com",
            "phone": "+1-555-5678",
            "city": "New City",
            "country": "USA",
            "company_description": "A new company",
            "contact_name": "Jane Smith",
            "contact_role": "CEO",
            "source_url": "https://newco.com"
        }
        resp = self.client.post("/api/leads", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["company_name"], "NewCo")
        self.assertEqual(data["source_url"], "https://newco.com")
        self.assertIn("id", data)

    def test_create_lead_missing_source_url(self):
        payload = {
            "company_name": "NewCo",
            "website": "https://newco.com",
        }
        resp = self.client.post("/api/leads", json=payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("source_url", resp.get_json()["error"])

    def test_get_lead_by_id(self):
        # First, get a lead we know exists
        resp = self.client.get(f"/api/leads/{self.lead_ids[0]}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["id"], self.lead_ids[0])
        self.assertEqual(data["company_name"], "Company 1")

        # Non-existent lead
        resp = self.client.get("/api/leads/9999")
        self.assertEqual(resp.status_code, 404)

    def test_update_lead(self):
        lead_id = self.lead_ids[0]
        payload = {
            "company_name": "Updated Company",
            "email": "updated@example.com"
        }
        resp = self.client.put(f"/api/leads/{lead_id}", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["company_name"], "Updated Company")
        self.assertEqual(data["email"], "updated@example.com")

        # Try to update source_url (should fail)
        payload = {"source_url": "https://new-example.com"}
        resp = self.client.put(f"/api/leads/{lead_id}", json=payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Cannot update source_url", resp.get_json()["error"])

        # Non-existent lead
        resp = self.client.put("/api/leads/9999", json={"company_name": "Test"})
        self.assertEqual(resp.status_code, 404)

    def test_bulk_create_leads(self):
        payload = {
            "leads": [
                {
                    "company_name": "BulkCo1",
                    "website": "https://bulkco1.com",
                    "source_url": "https://bulkco1.com"
                },
                {
                    "company_name": "BulkCo2",
                    "website": "https://bulkco2.com",
                    "source_url": "https://bulkco2.com"
                }
            ]
        }
        resp = self.client.post("/api/leads/bulk", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(len(data["lead_ids"]), 2)
        self.assertEqual(data["count"], 2)

        # Verify the leads were created
        for lead_id in data["lead_ids"]:
            resp = self.client.get(f"/api/leads/{lead_id}")
            self.assertEqual(resp.status_code, 200)

    def test_bulk_create_leads_invalid(self):
        # Missing leads
        payload = {}
        resp = self.client.post("/api/leads/bulk", json=payload)
        self.assertEqual(resp.status_code, 400)

        # Empty leads list
        payload = {"leads": []}
        resp = self.client.post("/api/leads/bulk", json=payload)
        self.assertEqual(resp.status_code, 400)

        # Leads not a list
        payload = {"leads": {}}
        resp = self.client.post("/api/leads/bulk", json=payload)
        self.assertEqual(resp.status_code, 400)

    def test_search_leads(self):
        # Search by company name
        resp = self.client.get("/api/leads/search?company=Company 1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["leads"][0]["company_name"], "Company 1")

        # Search by country
        resp = self.client.get("/api/leads/search?country=USA")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 3)

        # Search by min_score
        resp = self.client.get("/api/leads/search?min_score=90")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 3)

        # Search with no matches
        resp = self.client.get("/api/leads/search?company=Nonexistent")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 0)

        # Pagination
        resp = self.client.get("/api/leads/search?limit=2&offset=0")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["limit"], 2)
        self.assertEqual(data["offset"], 0)
        self.assertEqual(data["total"], 3)

        # Sorting
        resp = self.client.get("/api/leads/search?sort_by=company_name&sort_desc=true")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # Should be descending: Company 3, Company 2, Company 1
        company_names = [lead["company_name"] for lead in data["leads"]]
        self.assertEqual(company_names, ["Company 3", "Company 2", "Company 1"])

    def test_filter_leads_alias(self):
        # /api/leads/filter should behave the same as /api/leads/search
        resp1 = self.client.get("/api/leads/search?company=Company 1")
        resp2 = self.client.get("/api/leads/filter?company=Company 1")
        self.assertEqual(resp1.status_code, resp2.status_code)
        self.assertEqual(resp1.get_json(), resp2.get_json())

    def test_update_lead_lifecycle(self):
        # Start with a lead in NEW status (our test leads are inserted with status 'success' but lead_status defaults to NEW)
        # Let's check the initial lead_status of one of our leads.
        resp = self.client.get(f"/api/leads/{self.lead_ids[0]}")
        lead = resp.get_json()
        # The lead_status should be NEW (default) because we didn't set it in _make_lead
        self.assertEqual(lead.get("lead_status"), "NEW")

        # Valid transition: NEW -> DISCOVERED
        payload = {"lead_status": "DISCOVERED"}
        resp = self.client.patch(f"/api/leads/{self.lead_ids[0]}/lifecycle", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["lead_status"], "DISCOVERED")

        # Valid transition: DISCOVERED -> ENRICHED
        payload = {"lead_status": "ENRICHED"}
        resp = self.client.patch(f"/api/leads/{self.lead_ids[0]}/lifecycle", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["lead_status"], "ENRICHED")

        # Invalid transition: ENRICHED -> NEW (going backwards)
        payload = {"lead_status": "NEW"}
        resp = self.client.patch(f"/api/leads/{self.lead_ids[0]}/lifecycle", json=payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid lifecycle transition", resp.get_json()["error"])

        # Non-existent lead
        resp = self.client.patch("/api/leads/9999/lifecycle", json={"lead_status": "DISCOVERED"})
        self.assertEqual(resp.status_code, 404)

        # Invalid status
        payload = {"lead_status": "INVALID_STATUS"}
        resp = self.client.patch(f"/api/leads/{self.lead_ids[0]}/lifecycle", json=payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid lifecycle transition", resp.get_json()["error"])

    def test_get_lead_statistics(self):
        resp = self.client.get("/api/leads/statistics")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["total_leads"], 3)
        # We have 3 leads, all with data_quality HIGH
        self.assertEqual(len(data["quality_distribution"]), 1)
        self.assertEqual(data["quality_distribution"][0]["quality"], "HIGH")
        self.assertEqual(data["quality_distribution"][0]["count"], 3)
        # All leads have lead_status NEW (default)
        self.assertEqual(len(data["lifecycle_distribution"]), 1)
        self.assertEqual(data["lifecycle_distribution"][0]["status"], "NEW")
        self.assertEqual(data["lifecycle_distribution"][0]["count"], 3)
        # Average score should be 100.0
        self.assertEqual(data["average_score"], 100.0)
        # Top companies: we have Company 1, Company 2, Company 3 each once
        self.assertEqual(len(data["top_companies"]), 3)
        company_names = [item["company"] for item in data["top_companies"]]
        self.assertIn("Company 1", company_names)
        self.assertIn("Company 2", company_names)
        self.assertIn("Company 3", company_names)


if __name__ == "__main__":
    unittest.main()