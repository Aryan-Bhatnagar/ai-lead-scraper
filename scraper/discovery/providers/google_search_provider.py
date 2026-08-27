"""
Google Search Discovery Provider using the existing SearchService.
"""

from __future__ import annotations
import os
from datetime import datetime, UTC
from typing import List

from ..provider import DiscoveryProvider, CapabilitySet
from ..query import DiscoveryQuery, DiscoveryBatch, RawCandidate, SourceMeta
from ...services.search.service import SearchService

COMPETITOR_BLOCKLIST = [
    'fiverr.com', 'behance.net', 'dribbble.com', 'truelancer.com', 
    'peopleperhour.com', 'guru.com', 'toptal.com', 'freelancer.com/u/',
    'upwork.com/freelancers'
]

DIRECTORY_BLOCKLIST = [
    'justdial.com', 'indiamart.com', 'yellowpages.com', 'yelp.com',
    'wikipedia.org', 'quora.com', 'medium.com', 'slideshare.net',
    'facebook.com/groups', 'reddit.com', 'youtube.com', 'sulekha.com'
]

def is_valid_client_url(url: str) -> bool:
    if not url:
        return False
    url_lower = url.lower()
    for comp in COMPETITOR_BLOCKLIST:
        if comp in url_lower:
            return False
    for portal in DIRECTORY_BLOCKLIST:
        if portal in url_lower:
            return False
    return True

def transform_query_for_buyer_clients(service_keyword: str, location: str = "") -> List[str]:
    kw = (service_keyword or "").lower()
    loc_str = f" {location.strip()}" if location and location.strip() else ""
    if 'logo' in kw or 'design' in kw or 'brand' in kw:
        return [
            f"New Startups contact phone email{loc_str}",
            f"Restaurants Cafes contact phone email{loc_str}",
            f"Real Estate Agencies contact phone email{loc_str}",
            f"Clinics Healthcare contact phone email{loc_str}",
            f"Retail Stores contact phone email{loc_str}"
        ]
    elif 'web' in kw or 'software' in kw or 'app' in kw or 'ui' in kw or 'ux' in kw:
        return [
            f"Law Firms contact phone email{loc_str}",
            f"Dental Clinics contact phone email{loc_str}",
            f"Manufacturing Exporters contact phone email{loc_str}",
            f"Architects Interior Design contact phone email{loc_str}"
        ]
    else:
        return [f"New Businesses {service_keyword} contact phone email{loc_str}"]

class GoogleSearchDiscoveryProvider(DiscoveryProvider):
    """
    Provider that discovers leads using Google Search via the SearchService.
    """

    name = "google_search"
    source_type = "scrape"
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
        can_provide_categories=False,
    )

    def discover(self, query: DiscoveryQuery) -> DiscoveryBatch:
        """
        Discovers leads by performing search queries via the SearchService.
        """
        candidates: List[RawCandidate] = []

        # Service keywords that indicate Bilvaleaf's offerings
        SERVICE_KEYWORDS = {
            "logo", "logo design", "logo designing", "branding", "identity",
            "web design", "website design", "web development", "mobile app", "app development", "ui/ux", "ui ux",
            "digital marketing", "seo", "bpo", "kpo", "ai automation", "software development",
            "ai agent", "ai agents", "chatbot", "ai chatbot", "agentic ai", "ai solutions", "automation"
        }

        queries_to_run = []
        loc = (query.location or "").strip()
        ind = (query.industry or "").strip().lower()

        # Check if the query target is a service Bilvaleaf provides
        is_service_query = any(sk in ind for sk in SERVICE_KEYWORDS) or any(
            any(sk in kw.lower() for sk in SERVICE_KEYWORDS) for kw in query.keywords
        )

        enable_intent_discovery = os.getenv("ENABLE_INTENT_DISCOVERY", "false").lower() in ("true", "1", "t", "yes")

        if is_service_query:
            # Client Query Transformation Logic: Convert service into Target Buyer Business Categories
            queries_to_run.extend(transform_query_for_buyer_clients(ind or query.industry, location=loc))
            if loc:
                queries_to_run.append(f"new business startup {loc} contact us")
                queries_to_run.append(f"company vacancy hiring {loc} contact")
            else:
                queries_to_run.append(f"new business startup contact us")
                queries_to_run.append(f"company vacancy hiring contact us")

            if enable_intent_discovery:
                loc_suffix = f" {loc}" if loc else ""
                hiring_signal_queries = [
                    f'"{query.industry}" hiring OR vacancy OR "looking for"{loc_suffix}',
                    f'{query.industry} "need a logo" OR "need a website" OR "website redesign"{loc_suffix}',
                    f'{query.industry} "request for proposal" OR "RFP" logo OR website{loc_suffix}',
                    f'{query.industry} careers "graphic designer" OR "web developer"{loc_suffix}',
                ]
                queries_to_run.extend(hiring_signal_queries)
        else:
            # Non-service query (e.g. user specified direct buyer vertical like "Dental")
            loc_suffix = f" {loc}" if loc else ""
            base_query = f"{query.industry}{loc_suffix} contact us" if query.industry else f"business{loc_suffix} contact"
            queries_to_run.append(base_query)
            for kw in query.keywords:
                queries_to_run.append(f"{kw}{loc_suffix} email phone")

        # Directory, listing portal, document host, job board, and freelance marketplace blacklist
        DIRECTORY_BLACKLIST = {
            # Directories & Aggregators
            "sulekha.com", "mouthshut.com", "yellowpages", "makaan.com", "housing.com",
            "homes247", "emis.com", "submitmybusiness.com", "rightmoverealtors.in",
            "justdial.com", "indiamart.com", "tradeindia.com", "magicbricks.com",
            "99acres.com", "clutch.co", "goodfirms.co", "glassdoor.com", "indeed.com",
            "quikr.com", "olx.in", "facebook.com", "instagram.com", "linkedin.com",
            "twitter.com", "youtube.com", "wikipedia.org", "tripadvisor", "zomato",
            "scribd.com", "aeroleads.com", "indiaonline.in", "slideshare.net", "pdf",
            # Freelance & Job Board Portals
            "upwork.com", "dribbble.com", "truelancer.com", "twine.net", "contra.com",
            "apna.co", "jobhai.com", "naukri.com", "foundit.in", "monster.com",
            "fiverr.com", "freelancer.com", "behance.net", "freelancewebdesignerindia.in",
            "creativejunkyard.in", "toptal.com", "peopleperhour.com", "guru.com"
        }

        # General directory title markers
        AGGREGATOR_TITLE_MARKERS = [
            "list of", "top 10", "best 10", "directory", "yellow pages", "sulekha",
            "mouthshut", "housing.com", "makaan", "find builders", "reviews"
        ]

        # Job aggregator title markers (only rejected if domain is in blacklisted aggregators)
        JOB_AGGREGATOR_TITLE_MARKERS = [
            "jobs in", "vacancies in", "freelancers for hire", "logo designers for hire",
            "freelance logo designers"
        ]

        NEGATIVE_OPERATORS_SUFFIX = " -site:sulekha.com -site:upwork.com -site:dribbble.com -site:apna.co -site:naukri.com"

        total_results_collected = 0
        for q in queries_to_run:
            if total_results_collected >= query.max_results:
                break

            remaining = query.max_results - total_results_collected

            try:
                # Add negative site operators to query to reduce directory & job board noise
                query_with_negatives = f"{q}{NEGATIVE_OPERATORS_SUFFIX}"

                # Use SearchService with preferred_backend="ddgs"
                results = SearchService().search(
                    query=query_with_negatives,
                    limit=remaining * 2,  # Request extra to account for directory filtering
                    preferred_backend="ddgs"
                )

                for res in results:
                    url = (res.get("url") or "").lower()
                    title = (res.get("title") or "").lower()

                    # Check competitor blocklist filter
                    if not is_valid_client_url(url):
                        continue

                    is_blacklisted_domain = any(domain in url for domain in DIRECTORY_BLACKLIST)

                    # 1. Skip if URL matches any directory/aggregator domain
                    if is_blacklisted_domain:
                        continue

                    # 2. Skip if title contains aggregate listing markers
                    if any(marker in title for marker in AGGREGATOR_TITLE_MARKERS):
                        continue

                    # 3. Job aggregator markers are ONLY rejected for blacklisted domain candidates
                    # (Direct company domains with titles like "Acme Corp — Vacancies in Design" survive)
                    if is_blacklisted_domain and any(marker in title for marker in JOB_AGGREGATOR_TITLE_MARKERS):
                        continue

                    # Ensure the result has the expected fields
                    payload = {
                        "title": res.get("title", ""),
                        "url": res.get("url", ""),
                        "snippet": res.get("snippet", ""),
                        "source_engine": res.get("source_engine", "ddgs"),
                        "query": q,
                        "timestamp": res.get("timestamp") or datetime.now(UTC).isoformat()
                    }

                    candidates.append(
                        RawCandidate(
                            payload=payload,
                            source=self.name,
                            fetched_at=datetime.now(UTC)
                        )
                    )
                    total_results_collected += 1
                    if total_results_collected >= query.max_results:
                        break
            except Exception as e:
                print(f"[{self.name}] Error searching for {q}: {e}")

        return DiscoveryBatch(
            source=self.name,
            candidates=candidates,
            meta=SourceMeta(
                source=self.name,
                request_count=len(queries_to_run)
            )
        )