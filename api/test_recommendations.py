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


def _make_lead(lead_id: int, name: str, status: str, data_quality: str, source_url: str, quality_score: int,
               country: str = "USA", city: str = "AnyTown", industry: str = "Technology",
               lead_status: str = "NEW") -> dict:
    """Return a dict suitable for db_module.upsert_lead."""
    return {
        "company_name": name,
        "status": status,
        "data_quality": data_quality,
        "quality_score": quality_score,
        "source_url": source_url,
        "website": f"https://{name.lower().replace(' ', '')}.com",
        "email": f"contact@{name.lower().replace(' ', '')}.com",
        "phone": "+1-555-1234",
        "city": city,
        "country": country,
        "company_description": f"A great company named {name}",
        "contact_name": "John Doe",
        "contact_role": "CEO",
        "industry": industry,
        "lead_status": lead_status,
        # Note: scraped_at and created_at will be set by upsert_lead
    }


class RecommendationAPITest(unittest.TestCase):
    def setUp(self):
        # Create a temporary SQLite file and populate it.
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db_path = Path(self.temp_db.name)
        self.temp_db.close()

        # Initialise the database with the real schema.
        db_module.initialize_database(self.temp_db_path)

        # Insert a variety of leads for testing recommendations.
        self.lead_ids = []
        leads_data = [
            # Lead 1: HIGH score, USA, Technology, NEW
            _make_lead(1, "TechCorp", "success", "HIGH", "https://techcorp.com", 95, "USA", "San Francisco", "Technology"),
            # Lead 2: MEDIUM score, USA, Healthcare, CONTACTED
            _make_lead(2, "HealthInc", "success", "MEDIUM", "https://healthinc.com", 75, "USA", "New York", "Healthcare", lead_status="CONTACTED"),
            # Lead 3: LOW score, Canada, Finance, REJECTED
            _make_lead(3, "FinanceCo", "failed", "LOW", "https://financeco.com", 40, "Canada", "Toronto", "Finance", lead_status="REJECTED"),
            # Lead 4: HIGH score, UK, Technology, NEW (different source)
            _make_lead(4, "UKTech", "success", "HIGH", "https://uktech.co.uk", 88, "UK", "London", "Technology"),
            # Lead 5: MEDIUM score, Germany, Automotive, INTERESTED
            _make_lead(5, "AutoAG", "success", "MEDIUM", "https://autoag.de", 65, "Germany", "Berlin", "Automotive", lead_status="INTERESTED"),
            # Lead 6: LOW score, France, Retail, NEW
            _make_lead(6, "RetailFR", "success", "LOW", "https://retailfr.fr", 30, "France", "Paris", "Retail"),
            # Lead 7: No score (None), USA, Education, NEW
            _make_lead(7, "EduOnline", "success", "MEDIUM", "https://eduonline.com", None, "USA", "Boston", "Education"),
            # Lead 8: HIGH score, USA, Technology, CUSTOMER (converted)
            _make_lead(8, "ConvertInc", "success", "HIGH", "https://convertinc.com", 92, "USA", "Los Angeles", "Technology", lead_status="CUSTOMER"),
            # Lead 9: MEDIUM score, USA, Technology, CUSTOMER
            _make_lead(9, "ConvertInc2", "success", "MEDIUM", "https://convertinc2.com", 78, "USA", "San Diego", "Technology", lead_status="CUSTOMER"),
            # Lead 10: HIGH score, USA, Technology, RESPONDED
            _make_lead(10, "RespTech", "success", "HIGH", "https://respitech.com", 85, "USA", "Seattle", "Technology", lead_status="RESPONDED"),
        ]

        for lead in leads_data:
            lead_id = db_module.upsert_lead(lead, self.temp_db_path)
            self.lead_ids.append(lead_id)

        # Create the app using the temp db.
        self.app = create_app({"TESTING": True, "DATABASE": str(self.temp_db_path)})
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.temp_db_path)

    # ---------- Recommendation endpoints ----------
    def test_recommendations_list(self):
        resp = self.client.get("/api/recommendations")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 10)  # We have 10 leads
        # Check that each recommendation has the expected fields
        for rec in data:
            self.assertIn("lead_id", rec)
            self.assertIn("priority", rec)
            self.assertIn("next_action", rec)
            self.assertIn("confidence", rec)
            self.assertIn("reasons", rec)
            self.assertIn("suggested_outreach", rec)
            self.assertIn("risk_level", rec)
            self.assertIn("estimated_conversion", rec)
            # Validate values
            self.assertIn(rec["priority"], ["Critical", "High", "Medium", "Low"])
            self.assertIn(rec["next_action"], [
                "Research Website", "Find Email", "Contact Immediately",
                "Follow Up", "LinkedIn Outreach", "Phone Call", "Ignore"
            ])
            self.assertGreaterEqual(rec["confidence"], 0.0)
            self.assertLessEqual(rec["confidence"], 1.0)
            self.assertGreaterEqual(rec["estimated_conversion"], 0.0)
            self.assertLessEqual(rec["estimated_conversion"], 1.0)

    def test_recommendation_detail(self):
        # Test for an existing lead
        lead_id = self.lead_ids[0]
        resp = self.client.get(f"/api/recommendations/{lead_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["lead_id"], lead_id)
        self.assertIn("priority", data)
        self.assertIn("next_action", data)
        self.assertIn("confidence", data)
        self.assertIn("reasons", data)
        self.assertIn("suggested_outreach", data)
        self.assertIn("risk_level", data)
        self.assertIn("estimated_conversion", data)

        # Test for a non-existing lead
        resp = self.client.get("/api/recommendations/9999")
        self.assertEqual(resp.status_code, 404)

    def test_recommendations_summary(self):
        resp = self.client.get("/api/recommendations/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("total_leads", data)
        self.assertEqual(data["total_leads"], 10)
        self.assertIn("priority_distribution", data)
        self.assertIn("next_action_distribution", data)
        self.assertIn("average_confidence", data)
        self.assertIn("average_estimated_conversion", data)
        # Check that the distribution sums to total_leads
        total_priority = sum(data["priority_distribution"].values())
        total_action = sum(data["next_action_distribution"].values())
        self.assertEqual(total_priority, 10)
        self.assertEqual(total_action, 10)
        self.assertGreaterEqual(data["average_confidence"], 0.0)
        self.assertLessEqual(data["average_confidence"], 1.0)
        self.assertGreaterEqual(data["average_estimated_conversion"], 0.0)
        self.assertLessEqual(data["average_estimated_conversion"], 1.0)


if __name__ == "__main__":
    unittest.main()