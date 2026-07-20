import os
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

# Ensure project root on sys.path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.app import create_app
import scraper.database as db_module

# Helper to init temp db

def init_temp_db():
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_path = Path(temp_file.name)
    temp_file.close()
    db_module.initialize_database(temp_path)
    return temp_path

class Phase6CTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_db_path = init_temp_db()
        self.app = create_app({"TESTING": True, "DATABASE": str(self.temp_db_path)})
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.temp_db_path)

    def test_missing_body(self):
        with patch("scraper.scrape_api_helper.run_job_in_background"):
            resp = self.client.post('/api/jobs')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_malformed_json(self):
        with patch("scraper.scrape_api_helper.run_job_in_background"):
            resp = self.client.post('/api/jobs', data='notjson', headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_non_object_root(self):
        with patch("scraper.scrape_api_helper.run_job_in_background"):
            resp = self.client.post('/api/jobs', data=json.dumps([]), headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_missing_urls(self):
        with patch("scraper.scrape_api_helper.run_job_in_background"):
            resp = self.client.post('/api/jobs', data=json.dumps({}), headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_urls_not_list(self):
        with patch("scraper.scrape_api_helper.run_job_in_background"):
            resp = self.client.post('/api/jobs', data=json.dumps({'urls': 'http://example.com'}), headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_empty_urls_list(self):
        with patch("scraper.scrape_api_helper.run_job_in_background"):
            resp = self.client.post('/api/jobs', data=json.dumps({'urls': []}), headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_non_string_url_entry(self):
        with patch("scraper.scrape_api_helper.run_job_in_background"):
            resp = self.client.post('/api/jobs', data=json.dumps({'urls': [123]}), headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_empty_string_url(self):
        with patch("scraper.scrape_api_helper.run_job_in_background"):
            resp = self.client.post('/api/jobs', data=json.dumps({'urls': ['']} ), headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_whitespace_only_url(self):
        with patch("scraper.scrape_api_helper.run_job_in_background"):
            resp = self.client.post('/api/jobs', data=json.dumps({'urls': ['   '] }), headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_unsupported_scheme(self):
        with patch("scraper.scrape_api_helper.run_job_in_background"):
            resp = self.client.post('/api/jobs', data=json.dumps({'urls': ['ftp://example.com']}), headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_missing_host(self):
        with patch("scraper.scrape_api_helper.run_job_in_background"):
            resp = self.client.post('/api/jobs', data=json.dumps({'urls': ['http:///nohost']}), headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_valid_request_and_normalization(self):
        urls_input = ['  http://example.com  ', 'https://test.com', 'http://example.com', '   https://test.com  ']
        with patch("scraper.scrape_api_helper.run_job_in_background") as mock_bg:
            resp = self.client.post('/api/jobs', data=json.dumps({'urls': urls_input}), headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 202)
        data = resp.get_json()
        self.assertIn('job_id', data)
        job_id = data['job_id']
        self.assertEqual(data['status'], 'queued')
        # Verify db items
        resp_items = self.client.get(f'/api/jobs/{job_id}/items')
        items_data = resp_items.get_json()
        self.assertEqual(items_data['count'], 2)
        expected_urls = ['http://example.com', 'https://test.com']
        actual_urls = [item['source_url'] for item in items_data['items']]
        self.assertEqual(actual_urls, expected_urls)
        # Verify background called once with correct params
        mock_bg.assert_called_once_with(job_id, expected_urls, str(self.temp_db_path))

    def test_get_job(self):
        urls_input = ['http://example.com']
        with patch("scraper.scrape_api_helper.run_job_in_background"):
            resp = self.client.post('/api/jobs', data=json.dumps({'urls': urls_input}), headers={'Content-Type': 'application/json'})
        job_id = resp.get_json()['job_id']
        resp_job = self.client.get(f'/api/jobs/{job_id}')
        self.assertEqual(resp_job.status_code, 200)
        job_data = resp_job.get_json()
        self.assertEqual(job_data['id'], job_id)
        self.assertEqual(job_data['status'], 'queued')

    def test_unknown_route(self):
        resp = self.client.get('/api/nonexistent')
        self.assertEqual(resp.status_code, 404)
        self.assertIn('error', resp.get_json())

    def test_unsupported_method(self):
        resp = self.client.post('/api/health')
        self.assertEqual(resp.status_code, 405)
        self.assertIn('error', resp.get_json())

    def test_cors_header(self):
        with patch("scraper.scrape_api_helper.run_job_in_background"):
            resp = self.client.post('/api/jobs', data=json.dumps({'urls': ['http://example.com']}), headers={'Content-Type': 'application/json', 'Origin': 'https://tester.com'})
        self.assertIn('Access-Control-Allow-Origin', resp.headers)

if __name__ == '__main__':
    unittest.main()
