import urllib.parse
import urllib.request
import re
import json
from datetime import datetime

# Blocklist of competitor/freelancer directory domains
COMPETITOR_DOMAINS = [
    'fiverr.com/freelancers', 'behance.net', 'dribbble.com', 
    'truelancer.com/freelancers', 'peopleperhour.com/freelancers', 'toptal.com/designers'
]

def fetch_url(url, is_json=False):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'application/json' if is_json else 'text/html,application/xhtml+xml'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            return json.loads(content) if is_json else content
    except Exception:
        return {} if is_json else ""

def clean_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_phone(text):
    patterns = [
        r'\+91[\s-]?\d{5}[\s-]?\d{5}',
        r'\+91[\s-]?\d{10}',
        r'0?\d{10}',
        r'\d{3,5}[\s-]\d{6,8}'
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            cleaned = re.sub(r'\D', '', m)
            if len(cleaned) == 10 and cleaned.startswith(('6','7','8','9','0','1','2')):
                return "+91" + cleaned
            elif len(cleaned) == 12 and cleaned.startswith('91'):
                return "+" + cleaned
    return ""

def extract_email(text):
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if match:
        email = match.group(0).lower()
        if not any(email.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', 'duckduckgo.com', 'w3.org']):
            return email
    return ""

# =========================================================================
# MAIN HIGH-QUALITY LEAD EXTRACTION FUNCTION
# =========================================================================
import xml.etree.ElementTree as ET

# =========================================================================
# MAIN HIGH-QUALITY LEAD EXTRACTION FUNCTION (100% REAL LIVE DATA - ZERO MOCK DATA)
# =========================================================================
def scrape_genuine_client_leads(service: str, source: str = "all", max_results: int = 15) -> list:
    """
    Extracts high quality buyer client leads.
    source options: 'all', 'freelancer', 'upwork', 'guru', 'google_maps', 'instagram', 'linkedin'
    """
    encoded_service = urllib.parse.quote(service)
    leads = []
    
    # 1. FREELANCER.COM LIVE REST API (Real Client Budgets & Project Titles & AI Intelligence)
    if source in ["all", "freelancer"]:
        from .discovery.providers.freelancer_provider import fetch_live_freelancer_client_jobs
        fl_leads = fetch_live_freelancer_client_jobs(service_keyword=service, max_results=max_results)
        leads.extend(fl_leads)

    # 2. UPWORK REAL-TIME INDIVIDUAL JOB EXTRACTION
    if source in ["all", "upwork"]:
        from .discovery.providers.upwork_provider import fetch_live_upwork_jobs
        up_leads = fetch_live_upwork_jobs(service_keyword=service, max_results=max_results)
        leads.extend(up_leads)

    # 3. GURU.COM REAL-TIME INDIVIDUAL JOB EXTRACTION
    if source in ["all", "guru"]:
        from .discovery.providers.guru_provider import fetch_live_guru_jobs
        guru_leads = fetch_live_guru_jobs(service_keyword=service, max_results=max_results)
        leads.extend(guru_leads)
    # 4. LINKEDIN EXECUTIVE SEARCH ENGINE
    if source in ["all", "linkedin"]:
        from .discovery.providers.linkedin_provider import fetch_linkedin_executive_leads
        lkd_leads = fetch_linkedin_executive_leads(service=service, location="Global", max_results=max_results)
        leads.extend(lkd_leads)

    # 5. GOOGLE MAPS LOCAL BUSINESS SCRAPER ENGINE
    if source in ["all", "google_maps", "google_maps_scraper_kit"]:
        from .discovery.providers.google_maps_provider import fetch_google_maps_leads
        gmaps_leads = fetch_google_maps_leads(service=service, location="Global", max_results=max_results)
        leads.extend(gmaps_leads)

    # 6. PEOPLEPERHOUR REAL-TIME INDIVIDUAL JOB EXTRACTION
    if source in ["all", "peopleperhour"]:
        from .discovery.providers.peopleperhour_provider import fetch_live_peopleperhour_jobs
        pph_leads = fetch_live_peopleperhour_jobs(service_keyword=service, max_results=max_results)
        leads.extend(pph_leads)

    return leads[:max_results]
