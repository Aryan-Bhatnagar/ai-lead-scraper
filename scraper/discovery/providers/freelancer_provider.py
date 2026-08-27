"""
Freelancer.com Live Active Buyer Projects Discovery Provider.

Integrates Freelancer.com Active Client Projects API for instant warm buyer leads.
"""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import requests

from ..provider import DiscoveryProvider, CapabilitySet
from ..query import DiscoveryQuery, DiscoveryBatch, RawCandidate, SourceMeta

logger = logging.getLogger(__name__)

import re
import urllib.parse
import urllib.request
import json
from datetime import datetime

def extract_relevance_tokens(service_keyword: str) -> list[str]:
    kw_lower = service_keyword.lower().strip()
    words = [w for w in re.split(r'[\s\-_]+', kw_lower) if w and len(w) > 2 and w not in {'services', 'needed', 'expert', 'support', 'help', 'global', 'project', 'platform', 'company', 'agency'}]
    if not words:
        words = [w for w in re.split(r'[\s\-_]+', kw_lower) if len(w) > 2]
    
    tokens = set(words)
    
    # Smart Synonym & Related Tech Domain Expansion
    SYNONYMS = {
        'frontend': ['frontend', 'front-end', 'front end', 'web', 'website', 'react', 'vue', 'angular', 'html', 'css', 'javascript', 'js', 'ui', 'interface', 'landing page', 'app', 'developer', 'development'],
        'backend': ['backend', 'back-end', 'back end', 'node', 'python', 'django', 'fastapi', 'php', 'laravel', 'api', 'database', 'sql', 'server', 'developer', 'development'],
        'fullstack': ['fullstack', 'full-stack', 'full stack', 'web', 'app', 'software', 'developer', 'development'],
        'logo': ['logo', 'brand', 'branding', 'graphic', 'vector', 'illustrator', 'design', 'designer'],
        'design': ['design', 'designer', 'graphic', 'logo', 'ui', 'ux', 'figma', 'photoshop', 'illustrator'],
        'devops': ['devops', 'ci/cd', 'docker', 'kubernetes', 'aws', 'cloud', 'azure', 'server', 'linux'],
        'web': ['web', 'website', 'html', 'css', 'javascript', 'php', 'wordpress', 'react', 'frontend'],
        'app': ['app', 'application', 'flutter', 'react native', 'ios', 'android', 'mobile', 'swift', 'kotlin']
    }
    
    for key, syns in SYNONYMS.items():
        if any(k in kw_lower for k in [key, key.replace('end', '-end'), key.replace('end', ' end')]):
            tokens.update(syns)
            
    return list(tokens)

def is_strictly_relevant(text: str, service_keyword: str) -> bool:
    tokens = extract_relevance_tokens(service_keyword)
    if not tokens:
        return True
    text_lower = text.lower()
    return any(t in text_lower for t in tokens)

def is_buyer_lead(text: str) -> bool:
    text_lower = text.lower()
    COMPETITOR_EXCLUSION_KEYWORDS = ['we offer', 'our services', 'portfolio', 'hire us', 'agency']
    if any(k in text_lower for k in COMPETITOR_EXCLUSION_KEYWORDS):
        return False
    return True

def generate_freelancer_ai_intelligence(title: str, budget_str: str, clean_preview: str, service_keyword: str) -> dict:
    import os
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if groq_api_key:
        try:
            prompt = (
                f"Analyze Freelancer.com project '{title}'. Budget: {budget_str}. Target Service: {service_keyword}. "
                f"Requirements: {clean_preview[:300]}. "
                f"Return JSON with two keys:\n"
                f'  "team_overview": "A 1-sentence AI summary of the client requirements & budget.",\n'
                f'  "sales_pitch": "A 1-sentence high-converting proposal pitch angle."\n'
                f"JSON output only."
            )
            payload = json.dumps({
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150
            }).encode('utf-8')
            
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                res_data = json.loads(resp.read().decode('utf-8'))
                ai_text = res_data['choices'][0]['message']['content'].strip()
                if "```" in ai_text:
                    ai_text = re.sub(r'```json\s*|\s*```', '', ai_text).strip()
                parsed = json.loads(ai_text)
                return {
                    "ai_summary": parsed.get("team_overview", f"AI Team Overview: Freelancer project '{title}' ({budget_str})."),
                    "outreach_strategy": parsed.get("sales_pitch", f"Recommended Proposal Angle: Highlight proven expertise in {service_keyword} & commit to fast delivery within {budget_str}.")
                }
        except Exception:
            pass

    # Fallback: Native High-Converting Proposal Pitch Engine
    short_req = clean_preview[:200] + "..." if len(clean_preview) > 200 else clean_preview
    return {
        "ai_summary": f"AI Team Overview: Active Client Project. Budget: {budget_str}. Client Requirements: {short_req}",
        "outreach_strategy": f"Recommended Proposal Angle: Highlight past work in {service_keyword} & commit to fast delivery within {budget_str}."
    }

def format_time_submitted(ts: Any) -> str:
    if not ts:
        return "Recently Posted"
    try:
        now_ts = datetime.now(timezone.utc).timestamp()
        diff_sec = int(now_ts - float(ts))
        if diff_sec < 60:
            return "Posted just now"
        elif diff_sec < 3600:
            mins = diff_sec // 60
            return f"Posted {mins}m ago"
        elif diff_sec < 86400:
            hrs = diff_sec // 3600
            return f"Posted {hrs}h ago"
        else:
            days = diff_sec // 86400
            return f"Posted {days}d ago"
    except Exception:
        return "Recently Posted"

def format_time_remaining(sub_ts: Any, bidperiod_days: Any) -> str:
    if not sub_ts or not bidperiod_days:
        return "Open for Bids"
    try:
        deadline_ts = float(sub_ts) + (float(bidperiod_days) * 86400)
        now_ts = datetime.now(timezone.utc).timestamp()
        remaining_sec = int(deadline_ts - now_ts)
        if remaining_sec <= 0:
            return "Bidding Closed"
        elif remaining_sec < 3600:
            mins = remaining_sec // 60
            return f"Ends in {mins}m"
        elif remaining_sec < 86400:
            hrs = remaining_sec // 3600
            return f"Ends in {hrs}h"
        else:
            days = remaining_sec // 86400
            return f"Ends in {days}d"
    except Exception:
        return "Open for Bids"

def fetch_live_freelancer_client_jobs(service_keyword: str, max_results: int = 10, limit: int = 10) -> list:
    fetch_limit = 100
    # Clean service keyword for query (e.g. "logo designing" -> "logo design")
    query_str = service_keyword.lower().replace("designing", "design").replace("developing", "development").strip()
    encoded = urllib.parse.quote(query_str)
    url = f"https://www.freelancer.com/api/projects/0.1/projects/active/?query={encoded}&limit={fetch_limit}&job_details=true"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    req = urllib.request.Request(url, headers=headers)
    leads = []
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            projects = data.get('result', {}).get('projects', [])
            
            for p in projects:
                if len(leads) >= max_results:
                    break
                title = p.get('title', 'Client Job Post')
                seo_url = p.get('seo_url', '')
                live_link = f"https://www.freelancer.com/projects/{seo_url}" if seo_url else f"https://www.freelancer.com/projects/{p.get('id')}"
                
                raw_preview = p.get('preview', '')
                clean_preview = re.sub(r'<[^>]+>', '', raw_preview).strip()
                clean_preview = re.sub(r'\s+', ' ', clean_preview)
                
                # Extract must-have required skills from jobs field
                raw_jobs = p.get('jobs', []) or []
                skills = [j.get('name') for j in raw_jobs if isinstance(j, dict) and j.get('name')]
                skills_str = ", ".join(skills) if skills else ""
                
                combined_text = title + " " + clean_preview + " " + skills_str

                if not is_buyer_lead(combined_text):
                    continue

                if not is_strictly_relevant(combined_text, service_keyword):
                    continue

                currency = p.get('currency', {}).get('code', 'USD')
                min_b = p.get('budget', {}).get('minimum', 0)
                max_b = p.get('budget', {}).get('maximum', 0)
                budget_str = f"{currency} {min_b} - {max_b}" if min_b else "Budget Negotiable"
                
                sub_ts = p.get('time_submitted') or p.get('submitdate')
                bidperiod = p.get('bidperiod', 7)
                bid_stats = p.get('bid_stats', {}) or {}
                bid_count = bid_stats.get('bid_count', 0) if isinstance(bid_stats, dict) else 0

                posted_time_str = format_time_submitted(sub_ts)
                time_left_str = format_time_remaining(sub_ts, bidperiod)
                proposals_str = f"{bid_count} Proposals" if bid_count else "Be First to Bid"
                
                skills_tag = f"Must-Haves: {skills_str} | " if skills_str else ""
                buying_signals_text = f"Budget: {budget_str} | {skills_tag}{proposals_str} | {posted_time_str} | {time_left_str}"

                ai_intel = generate_freelancer_ai_intelligence(title, budget_str, clean_preview, service_keyword)
                
                # Full un-truncated description with rich project details & must-haves
                req_prefix = f" [Required Skills: {skills_str}]" if skills_str else ""
                full_description = f"LIVE Client Project: '{title}'.{req_prefix} Budget: {budget_str}. Requirements: {clean_preview[:1200]}"
                
                leads.append({
                    "company": f"Freelancer Client ({title[:35]}...)",
                    "company_name": f"Freelancer.com Client: {title}",
                    "title": title,
                    "name": f"Verified Buyer Client ({budget_str})",
                    "service": service_keyword,
                    "phone": "Apply & Chat Directly on Freelancer Job Page",
                    "email": "Direct Active Client Post",
                    "source": "freelancer",
                    "source_platform": "Freelancer.com Active Buyer Job",
                    "source_url": live_link,
                    "website": live_link,
                    "has_website": "Live Freelancer.com Link ↗",
                    "lead_type": "Genuine Buyer Client",
                    "description": full_description,
                    "summary": full_description,
                    "ai_summary": ai_intel["ai_summary"],
                    "outreach_strategy": ai_intel["outreach_strategy"],
                    "buying_signals": buying_signals_text,
                    "recommended_service": service_keyword,
                    "skills": skills,
                    "categories": skills,
                    "skills_str": skills_str,
                    "bid_count": bid_count,
                    "proposals_str": proposals_str,
                    "posted_time_str": posted_time_str,
                    "time_left_str": time_left_str,
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
    except Exception as e:
        print(f"Error fetching Freelancer API: {e}")
        
    return leads[:max_results]

fetch_live_client_jobs = fetch_live_freelancer_client_jobs

class FreelancerLiveDiscoveryProvider(DiscoveryProvider):
    """
    Adapter that enables the discovery engine to find active buyer project leads from Freelancer.com API.
    """

    name = "freelancer"
    source_type = "api"
    requires_api_key = False

    capabilities = CapabilitySet(
        can_provide_website=False,
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
        search_terms = query.keywords if query.keywords else [query.industry]

        for term in search_terms:
            if not term:
                continue
            leads = fetch_live_client_jobs(term, limit=query.max_results)
            for lead in leads:
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
            meta=SourceMeta(
                source=self.name,
                request_count=len(search_terms)
            )
        )
