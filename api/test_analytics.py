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


class AnalyticsAPITest(unittest.TestCase):
    def setUp(self):
        # Create a temporary SQLite file and populate it.
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db_path = Path(self.temp_db.name)
        self.temp_db.close()

        # Initialise the database with the real schema.
        db_module.initialize_database(self.temp_db_path)

        # Insert a variety of leads for testing analytics.
        self.lead_ids = []
        leads_data = [
            # Lead 1: HIGH score, USA, Technology, NEW
            _make_lead(1, "TechCorp", "success", "HIGH", "https://techcorp.com", 95, "USA", "San Francisco", "Technology"),
            # Lead 2: MEDIUM score, USA, Healthcare, CONTACTED
            _make_lead(2, "HealthInc", "success", "MEDIUM", "https://healthinc.com", 75, "USA", "New York", "Healthcare", lead_status="CONTACTED"),
            # Lead 3: LOW score, Canada, Finance, IGNORED (but we use REJECTED)
            _make_lead(3, "FinanceCo", "failed", "LOW", "https://financeco.com", 40, "Canada", "Toronto", "Finance", lead_status="REJECTED"),
            # Lead 4: HIGH score, UK, Technology, DUPLICATE (same source as lead1? we'll make different)
            _make_lead(4, "UKTech", "success", "HIGH", "https://uktech.co.uk", 88, "UK", "London", "Technology"),
            # Lead 5: MEDIUM score, Germany, Automotive, INTERESTED
            _make_lead(5, "AutoAG", "success", "MEDIUM", "https://autoag.de", 65, "Germany", "Berlin", "Automotive", lead_status="INTERESTED"),
            # Lead 6: LOW score, France, Retail, NEW
            _make_lead(6, "RetailFR", "success", "LOW", "https://retailfr.fr", 30, "France", "Paris", "Retail"),
            # Lead 7: No score (None), USA, Education, NEW
            _make_lead(7, "EduOnline", "success", "MEDIUM", "https://eduonline.com", None, "USA", "Boston", "Education"),
            # Lead 8: HIGH score, USA, Technology, CONVERTED (to test conversion)
            _make_lead(8, "ConvertInc", "success", "HIGH", "https://convertinc.com", 92, "USA", "Los Angeles", "Technology", lead_status="CUSTOMER"),
            # Lead 9: MEDIUM score, USA, Technology, CONVERTED
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

    # ---------- Analytics endpoints ----------
    def test_analytics_overview(self):
        resp = self.client.get("/api/analytics/overview")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("total_leads", data)
        self.assertEqual(data["total_leads"], 10)
        self.assertIn("average_score", data)
        # Average of scores (None treated as 0): (95+75+40+88+65+30+0+92+78+85) / 10 = 64.8
        self.assertAlmostEqual(data["average_score"], 64.8, places=1)
        self.assertIn("total_companies", data)
        self.assertEqual(data["total_companies"], 10)  # all company names unique
        self.assertIn("lead_sources", data)
        self.assertIn("countries", data)
        self.assertIn("cities", data)
        self.assertIn("industries", data)
        self.assertIn("lifecycle_distribution", data)
        self.assertIn("quality_distribution", data)
        # Quality distribution based on score thresholds (excellent>=85, good 65-84, average 50-64, poor<50, unknown None)
        # With our data:
        # excellent (>=85): 95, 92, 88, 85 => 4
        # good (65-84): 78, 75 => 2
        # average (50-64): 65 => 1
        # poor (<50): 40, 30, 0 => 3
        # unknown: 0
        self.assertEqual(data["quality_distribution"]["excellent"], 4)
        self.assertEqual(data["quality_distribution"]["good"], 2)
        self.assertEqual(data["quality_distribution"]["average"], 1)
        self.assertEqual(data["quality_distribution"]["poor"], 3)
        self.assertEqual(data["quality_distribution"]["unknown"], 0)
        # Lifecycle distribution based on lead_status
        # NEW: leads 1,4,6,7 =>4
        # CONTACTED: lead2 =>1
        # REJECTED: lead3 =>1
        # INTERESTED: lead5 =>1
        # CUSTOMER: leads 8,9 =>2
        # RESPONDED: lead10 =>1
        self.assertEqual(data["lifecycle_distribution"]["NEW"], 4)
        self.assertEqual(data["lifecycle_distribution"]["CONTACTED"], 1)
        self.assertEqual(data["lifecycle_distribution"]["REJECTED"], 1)
        self.assertEqual(data["lifecycle_distribution"]["INTERESTED"], 1)
        self.assertEqual(data["lifecycle_distribution"]["CUSTOMER"], 2)
        self.assertEqual(data["lifecycle_distribution"]["RESPONDED"], 1)

    def test_analytics_quality(self):
        resp = self.client.get("/api/analytics/quality")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("excellent", data)  # score >=85
        self.assertIn("good", data)       # 65-84
        self.assertIn("average", data)    # 50-64
        self.assertIn("poor", data)       # <50
        self.assertIn("unknown", data)    # None score
        # With our data:
        # excellent (>=85): 95, 92, 88, 85 => 4
        # good (65-84): 78, 75 => 2
        # average (50-64): 65 => 1
        # poor (<50): 40, 30, 0 => 3
        # unknown: 0 (none are None because we set quality_score to int)
        self.assertEqual(data["excellent"], 4)
        self.assertEqual(data["good"], 2)
        self.assertEqual(data["average"], 1)
        self.assertEqual(data["poor"], 3)
        self.assertEqual(data["unknown"], 0)

    def test_analytics_trends(self):
        resp = self.client.get("/api/analytics/trends")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("daily", data)
        self.assertIn("weekly", data)
        self.assertIn("monthly", data)
        self.assertIn("growth_rate", data)
        self.assertIn("rolling_average", data)
        self.assertIn("moving_average", data)
        # We have 10 leads, but they might have same created_at (now). We'll just check structure.
        self.assertIsInstance(data["daily"], list)
        self.assertIsInstance(data["weekly"], list)
        self.assertIsInstance(data["monthly"], list)

    def test_analytics_providers(self):
        resp = self.client.get("/api/analytics/providers")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        # We have 10 leads with various domains: techcorp.com, healthinc.com, financeco.com, uktech.co.uk, autoag.de, retailfr.fr, edonline.com, convertinc.com, convertinc2.com, respitech.com
        # So we expect 10 providers (each domain unique)
        self.assertEqual(len(data), 10)
        # Check that each entry has the expected keys.
        for provider in data:
            self.assertIn("provider_name", provider)
            self.assertIn("total_leads", provider)
            self.assertIn("average_leads_per_provider", provider)
            self.assertIn("success_rate", provider)
            self.assertIn("failure_rate", provider)
            self.assertIn("duplicate_percentage", provider)
            self.assertIn("unique_percentage", provider)

    def test_analytics_lifecycle(self):
        resp = self.client.get("/api/analytics/lifecycle")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, dict)
        # We have leads with lead_status: NEW (1,4,6,7), CONTACTED (2), REJECTED (3), INTERESTED (5), CUSTOMER (8,9), RESPONDED (10)
        # So we expect keys for each of these.
        self.assertIn("NEW", data)
        self.assertEqual(data["NEW"], 4)  # leads 1,4,6,7
        self.assertIn("CONTACTED", data)
        self.assertEqual(data["CONTACTED"], 1)
        self.assertIn("REJECTED", data)
        self.assertEqual(data["REJECTED"], 1)
        self.assertIn("INTERESTED", data)
        self.assertEqual(data["INTERESTED"], 1)
        self.assertIn("CUSTOMER", data)
        self.assertEqual(data["CUSTOMER"], 2)
        self.assertIn("RESPONDED", data)
        self.assertEqual(data["RESPONDED"], 1)

    def test_analytics_insights(self):
        resp = self.client.get("/api/analytics/insights")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("top_performing_industries", data)
        self.assertIn("best_countries", data)
        self.assertIn("most_valuable_sources", data)
        self.assertIn("highest_quality_segments", data)
        self.assertIn("most_contacted_leads", data)
        self.assertIn("highest_conversion_states", data)
        # Check that we have some data in each (maybe empty lists for some)
        self.assertIsInstance(data["top_performing_industries"], list)
        self.assertIsInstance(data["best_countries"], list)
        self.assertIsInstance(data["most_valuable_sources"], list)
        self.assertIsInstance(data["highest_quality_segments"], list)
        self.assertIsInstance(data["most_contacted_leads"], list)
        self.assertIsInstance(data["highest_conversion_states"], list)


if __name__ == "__main__":
    unittest.main()