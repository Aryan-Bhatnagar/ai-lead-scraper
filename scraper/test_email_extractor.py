"""Offline unit tests for scraper.email_extractor (Phase 12F).

No network requests, no LLM — all fetch_html and discover_pages calls
are mocked.  Run with:
    python -m pytest scraper/test_email_extractor.py -v
"""

import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper import email_extractor as ee


# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------
HTML_MAILTO = """
<html><body>
<h1>Contact Us</h1>
<p>We'd love to hear from you.</p>
<a href="mailto:sales@acme.com?subject=Inquiry">Email Sales</a>
<a href="tel:+15551234567">Call Us</a>
</body></html>
"""

HTML_VISIBLE_TEXT = """
<html><body>
<h1>About Acme Corp</h1>
<p>For general inquiries, write to info@acme.com</p>
<p>Phone: +1 555-987-6543</p>
</body></html>
"""

HTML_NO_EMAIL = """
<html><body>
<h1>Welcome</h1>
<p>We build great products.</p>
<p>Phone: +1 555-111-2222</p>
</body></html>
"""

HTML_BLOCKLISTED = """
<html><body>
<a href="mailto:noreply@acme.com">Do not reply</a>
</body></html>
"""

HTML_MULTIPLE = """
<html><body>
<a href="mailto:noreply@acme.com">No reply</a>
<a href="mailto:sales@acme.com">Sales</a>
<a href="mailto:info@acme.com">Info</a>
<p>General: hello@acme.com</p>
</body></html>
"""

HTML_CONTACT_PAGE = """
<html><body>
<h1>Contact Page</h1>
<a href="mailto:contact@deepcorp.com">Email us</a>
</body></html>
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestExtractEmailsFromHtml(TestCase):
    """Tests for extract_emails_from_html()."""

    def test_mailto_extraction(self):
        result = ee.extract_emails_from_html(HTML_MAILTO, source_page="https://acme.com")
        self.assertEqual(result["email"], "sales@acme.com")
        self.assertEqual(result["email_source_type"], "mailto")
        self.assertEqual(result["email_source_page"], "https://acme.com")

    def test_visible_text_extraction(self):
        result = ee.extract_emails_from_html(HTML_VISIBLE_TEXT, source_page="https://acme.com")
        self.assertEqual(result["email"], "info@acme.com")
        self.assertEqual(result["email_source_type"], "visible_text")

    def test_no_email(self):
        result = ee.extract_emails_from_html(HTML_NO_EMAIL, source_page="https://acme.com")
        self.assertEqual(result["email"], "")
        self.assertEqual(result["email_source_page"], "")
        self.assertEqual(result["email_source_type"], "")
        self.assertEqual(result["all_emails"], [])

    def test_blocklisted_email_rejected(self):
        result = ee.extract_emails_from_html(HTML_BLOCKLISTED, source_page="https://acme.com")
        self.assertEqual(result["email"], "")

    def test_multiple_sources_selects_best(self):
        result = ee.extract_emails_from_html(HTML_MULTIPLE, source_page="https://acme.com")
        # sales@ is highest priority mailbox prefix and mailto beats visible_text
        self.assertEqual(result["email"], "sales@acme.com")
        self.assertEqual(result["email_source_type"], "mailto")

    def test_all_emails_list_populated(self):
        result = ee.extract_emails_from_html(HTML_MULTIPLE, source_page="https://acme.com")
        # Should have at least hello@ (visible_text) and sales@ (mailto)
        values = [e["value"] for e in result["all_emails"]]
        self.assertIn("sales@acme.com", values)
        self.assertIn("hello@acme.com", values)


class TestExtractEmailsFromUrl(TestCase):
    """Tests for extract_emails_from_url() with mocked fetch_html."""

    @patch("scraper.email_extractor.fetch_html")
    def test_successful_extraction(self, mock_fetch):
        mock_fetch.return_value = HTML_MAILTO
        result = ee.extract_emails_from_url("https://acme.com")

        self.assertEqual(result["email"], "sales@acme.com")
        self.assertEqual(result["url"], "https://acme.com")
        self.assertIn("https://acme.com", result["pages_checked"])
        self.assertNotIn("_error", result)

    @patch("scraper.email_extractor.fetch_html")
    def test_fetch_failure(self, mock_fetch):
        mock_fetch.side_effect = ConnectionError("network down")
        result = ee.extract_emails_from_url("https://acme.com")

        self.assertEqual(result["email"], "")
        self.assertIn("_error", result)
        self.assertEqual(result["pages_checked"], [])


class TestEnrichEmailForLead(TestCase):
    """Tests for enrich_email_for_lead() with mocked fetch_html and discover_pages."""

    @patch("scraper.email_extractor.fetch_html")
    def test_email_on_homepage(self, mock_fetch):
        mock_fetch.return_value = HTML_MAILTO
        lead = {"website": "https://acme.com", "company_name": "Acme"}
        result = ee.enrich_email_for_lead(lead)

        self.assertEqual(result["email"], "sales@acme.com")
        self.assertEqual(result["email_source_type"], "mailto")
        self.assertEqual(result["company_name"], "Acme")
        self.assertIn("https://acme.com", result["pages_checked"])

    @patch("scraper.email_extractor.discover_pages")
    @patch("scraper.email_extractor.fetch_html")
    def test_email_on_discovered_page(self, mock_fetch, mock_discover):
        # Homepage has no email, but /contact does
        mock_fetch.side_effect = [HTML_NO_EMAIL, HTML_CONTACT_PAGE]
        mock_discover.return_value = ["https://deepcorp.com/contact"]

        lead = {"website": "https://deepcorp.com", "company_name": "DeepCorp"}
        result = ee.enrich_email_for_lead(lead)

        self.assertEqual(result["email"], "contact@deepcorp.com")
        self.assertEqual(result["email_source_page"], "https://deepcorp.com/contact")
        self.assertIn("https://deepcorp.com", result["pages_checked"])
        self.assertIn("https://deepcorp.com/contact", result["pages_checked"])

    @patch("scraper.email_extractor.discover_pages")
    @patch("scraper.email_extractor.fetch_html")
    def test_no_email_found(self, mock_fetch, mock_discover):
        mock_fetch.return_value = HTML_NO_EMAIL
        mock_discover.return_value = ["https://acme.com/about"]

        lead = {"website": "https://acme.com", "company_name": "Acme"}
        result = ee.enrich_email_for_lead(lead)

        self.assertEqual(result["email"], "")
        self.assertEqual(result["email_source_page"], "")
        self.assertEqual(result["email_source_type"], "")

    def test_no_website(self):
        lead = {"company_name": "NoSite"}
        result = ee.enrich_email_for_lead(lead)
        self.assertEqual(result["email"], "")
        self.assertEqual(result["pages_checked"], [])

    @patch("scraper.email_extractor.fetch_html")
    def test_fetch_exception(self, mock_fetch):
        mock_fetch.side_effect = ConnectionError("down")
        lead = {"website": "https://acme.com"}
        result = ee.enrich_email_for_lead(lead)
        self.assertEqual(result["email"], "")

    @patch("scraper.email_extractor.discover_pages")
    @patch("scraper.email_extractor.fetch_html")
    def test_discovered_page_fetch_failure(self, mock_fetch, mock_discover):
        # Homepage has no email, discovered page throws exception
        mock_fetch.side_effect = [HTML_NO_EMAIL, ConnectionError("timeout")]
        mock_discover.return_value = ["https://acme.com/contact"]

        lead = {"website": "https://acme.com"}
        result = ee.enrich_email_for_lead(lead)
        self.assertEqual(result["email"], "")


class TestExtractEmailsBatch(TestCase):
    """Tests for extract_emails_batch() with mocked internals."""

    @patch.object(ee, "enrich_email_for_lead")
    def test_batch_deduplication(self, mock_enrich):
        mock_enrich.return_value = {
            "email": "sales@acme.com",
            "email_source_page": "https://acme.com",
            "email_source_type": "mailto",
            "pages_checked": ["https://acme.com"],
        }
        leads = [
            {"website": "https://acme.com", "company_name": "Acme A"},
            {"website": "https://acme.com", "company_name": "Acme B"},
        ]
        results = ee.extract_emails_batch(leads)

        # Only one enrichment call (deduplicated)
        self.assertEqual(mock_enrich.call_count, 1)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["email"], "sales@acme.com")
        self.assertEqual(results[1]["email"], "sales@acme.com")

    @patch.object(ee, "enrich_email_for_lead")
    def test_batch_preserves_lead_fields(self, mock_enrich):
        mock_enrich.return_value = {
            "email": "info@test.com",
            "email_source_page": "https://test.com",
            "email_source_type": "visible_text",
            "pages_checked": ["https://test.com"],
        }
        lead = {
            "website": "https://test.com",
            "company_name": "TestCo",
            "industry": "SaaS",
            "city": "London",
        }
        results = ee.extract_emails_batch([lead])

        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertEqual(r["company_name"], "TestCo")
        self.assertEqual(r["industry"], "SaaS")
        self.assertEqual(r["city"], "London")
        self.assertEqual(r["email"], "info@test.com")

    def test_batch_no_website(self):
        leads = [{"company_name": "NoSite"}]
        results = ee.extract_emails_batch(leads)
        self.assertEqual(len(results), 1)
        # Lead without website is passed through as-is (no email field added)
        self.assertNotIn("email", results[0])
        self.assertEqual(results[0]["company_name"], "NoSite")

    def test_batch_empty_list(self):
        results = ee.extract_emails_batch([])
        self.assertEqual(results, [])

    @patch.object(ee, "enrich_email_for_lead")
    def test_batch_different_websites(self, mock_enrich):
        mock_enrich.side_effect = [
            {"email": "a@a.com", "email_source_page": "https://a.com",
             "email_source_type": "mailto", "pages_checked": []},
            {"email": "b@b.com", "email_source_page": "https://b.com",
             "email_source_type": "mailto", "pages_checked": []},
        ]
        leads = [
            {"website": "https://a.com"},
            {"website": "https://b.com"},
        ]
        results = ee.extract_emails_batch(leads)

        self.assertEqual(mock_enrich.call_count, 2)
        self.assertEqual(results[0]["email"], "a@a.com")
        self.assertEqual(results[1]["email"], "b@b.com")
