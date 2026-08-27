"""
Guru.com Live Discovery Provider.

Adapter enabling discovery of active client job posts from Guru.com.
"""

from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import List, Dict, Any

from ..query import DiscoveryBatch, DiscoveryQuery, RawCandidate, SourceMeta
from ..provider import DiscoveryProvider, CapabilitySet
from ...universal_engine import scrape_genuine_client_leads

def fetch_live_guru_jobs(service_keyword: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Extract individual live client job postings from Guru.com."""
    from ...services.search.service import SearchService
    search_svc = SearchService()
    query_str = f"site:guru.com/jobs {service_keyword}"
    raw_results = search_svc.search(query_str, limit=max_results * 3)
    
    leads = []
    seen_urls = set()
    
    for r in raw_results:
        if len(leads) >= max_results:
            break
        url = r.get("url", "").strip()
        title_raw = r.get("title", "").strip()
        snippet = r.get("snippet", "").strip()
        
        if not url or url in seen_urls:
            continue
        if "guru.com/jobs/" not in url.lower():
            continue
            
        seen_urls.add(url)
        
        # Clean title
        clean_title = re.sub(r'\s*\(\d+\)\s*-\s*Freelance Job.*$', '', title_raw, flags=re.IGNORECASE).strip()
        clean_title = re.sub(r'\s*-\s*Guru.*$', '', clean_title, flags=re.IGNORECASE).strip()
        clean_title = clean_title or f"Guru.com Client Job: {service_keyword}"
        
        # Extract budget from snippet
        b_match = re.search(r'\$([0-9,]+(?:\s*-\s*\$?[0-9,]+)?)', snippet)
        h_match = re.search(r'(\$[0-9,]+(?:\.\d+)?\s*/\s*hr)', snippet, re.IGNORECASE)
        if b_match:
            budget_str = f"USD ${b_match.group(1)}"
        elif h_match:
            budget_str = f"Hourly {h_match.group(1)}"
        else:
            budget_str = "Budget Negotiable"
            
        ai_summary = f"LIVE Guru.com Job: '{clean_title}'. Client project budget: {budget_str}. Requirements: {snippet[:300]}"
        outreach_strategy = f"Submit proposal directly on Guru job link. Attach relevant {service_keyword} portfolio samples and competitive pricing."
        buying_signals_text = f"Budget: {budget_str} | Active Guru Client Job Post"
        
        full_desc = f"LIVE Client Job Post on Guru.com: '{clean_title}'. Budget: {budget_str}. Details: {snippet}"
        
        leads.append({
            "company": f"Guru Client ({clean_title[:35]}...)",
            "company_name": f"Guru.com Client: {clean_title}",
            "title": clean_title,
            "name": f"Verified Buyer Client ({budget_str})",
            "service": service_keyword,
            "phone": "Apply Directly on Guru Job Page",
            "email": "Direct Active Client Post",
            "source": "guru",
            "source_platform": "Guru.com Active Buyer Job",
            "source_url": url,
            "website": url,
            "url": url,
            "has_website": "Live Guru.com Link ↗",
            "lead_type": "Genuine Buyer Client",
            "description": full_desc,
            "summary": full_desc,
            "ai_summary": ai_summary,
            "outreach_strategy": outreach_strategy,
            "buying_signals": buying_signals_text,
            "recommended_service": service_keyword,
            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
    return leads

class GuruDiscoveryProvider(DiscoveryProvider):
    """
    Provider adapter for discovering active client jobs on Guru.com.
    """

    name = "guru"
    source_type = "api"
    requires_api_key = False

    capabilities = CapabilitySet(
        can_provide_website=True,
        can_provide_email=False,
        can_provide_phone=False,
        can_provide_rating=False,
        can_provide_review_count=False,
        can_provide_coordinates=False,
        can_provide_business_hours=False,
        can_provide_social_links=False,
        can_provide_categories=True,
        custom={"budget", "source_platform"}
    )

    def discover(self, query: DiscoveryQuery) -> DiscoveryBatch:
        candidates: List[RawCandidate] = []
        search_term = query.industry or (query.keywords[0] if query.keywords else "Web Development")

        guru_leads = fetch_live_guru_jobs(service_keyword=search_term, max_results=query.max_results)
        
        # Fallback if specific search returns 0 leads
        if not guru_leads:
            from ...universal_engine import scrape_genuine_client_leads
            guru_leads = scrape_genuine_client_leads(service=search_term, source="guru", max_results=query.max_results)

        for lead in guru_leads:
            candidates.append(
                RawCandidate(
                    payload=lead,
                    source=self.name,
                    fetched_at=datetime.now(timezone.utc)
                )
            )

        return DiscoveryBatch(
            source=self.name,
            candidates=candidates,
            meta=SourceMeta(source=self.name, request_count=1)
        )
