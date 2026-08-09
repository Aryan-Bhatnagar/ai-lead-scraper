"""
Google Maps Discovery Provider using the gosom Google Maps Scraper REST API.

This provider submits a scraping job to a local Docker instance of the gosom scraper,
polls until completion, and returns the results as RawCandidates.
"""

from __future__ import annotations

import time
import csv
import io
from datetime import datetime, UTC
from typing import List, Optional
import requests

from ..provider import DiscoveryProvider, CapabilitySet
from ..query import DiscoveryQuery, DiscoveryBatch, RawCandidate, SourceMeta
from ...scrape_leads import scrape_site

class GoogleMapsDiscoveryProvider(DiscoveryProvider):
    """Discover businesses via the gosom Google Maps Scraper API with website enrichment."""

    name = "google_maps"
    source_type = "api"
    requires_api_key = False

    capabilities = CapabilitySet(
        can_provide_website=True,
        can_provide_email=True,
        can_provide_phone=True,
        can_provide_rating=True,
        can_provide_review_count=True,
        can_provide_coordinates=True,
        can_provide_business_hours=True,
        can_provide_social_links=True,
        can_provide_categories=True,
        custom={},
    )

    # Local API endpoint for the gosom scraper
    API_BASE_URL = "http://localhost:8080/api/v1"
    POLL_INTERVAL = 5.0
    MAX_POLL_TIME = 600  # 10 minutes

    # B2B Quality Filters
    BLACKLISTED_DOMAINS = {
        # Social Media
        "facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com",
        "youtube.com", "reddit.com", "vk.com", "pinterest.com", "tiktok.com",
        "snapchat.com", "threads.net",
        # Directories & Aggregators
        "zomato.com", "tripadvisor.com", "justdial.com", "sulekha.com",
        "restaurantguru.com", "yellowpages.com", "foursquare.com",
        "yelp.com", "angie.com", "homeadvisor.com", "thumbtack.com",
        "wikipedia.org", "crunchbase.com", "glassdoor.com", "indeed.com",
        "trustpilot.com", "sitejabber.com", "clutch.co", "goodfirms.co",
        # Delivery & Food Apps
        "swiggy.com", "zomato.com", "ubereats.com", "doordash.com",
        "grubhub.com", "postmates.com", "foodpanda.com",
        # Maps & Navigation (not business sites)
        "goo.gl", "maps.google.com", "google.com/maps",
        # Generic/Blog/Content platforms
        "medium.com", "blogspot.com", "wordpress.com", "tumblr.com",
        "substack.com", "ghost.io", "wix.com", "squarespace.com",
        "weebly.com", "github.io", "gitlab.io", "netlify.app",
    }

    JUNK_KEYWORDS = [
        # Menus & Food
        "menu", "delivery", "takeout", "catering", "order online",
        "food delivery", "online ordering", "zomato", "swiggy",
        # Lists & Directories
        "top 10", "top 5", "best ", "top rated", "best of",
        "directory", "listing", "listings", "classified",
        "near me", "nearby", "in ", "area", "local ",
        # Blogs & Articles
        "blog", "article", "review", "news", "guide", "tips",
        "updated 2024", "updated 2025", "updated 2026",
        "published", "author", "read more", "continue reading",
        # Social & Non-business
        "playlist", "video", "photos", "images", "gallery",
        "follow us", "like us", "share", "subscribe",
        # Job/Recruitment
        "jobs", "careers", "hiring", "vacancy", "recruitment",
        # Generic/Placeholder
        "home", "about", "contact", "privacy", "terms",
        "under construction", "coming soon", "placeholder",
        # Marketplace/Aggregator pages
        "marketplace", "aggregator", "comparison", "vs ",
        "alternatives", "competitors", "pricing", "quotes",
    ]

    def discover(self, query: DiscoveryQuery) -> DiscoveryBatch:
        """Submit a job to the local gosom scraper and poll for results.

        Process:
        1. Submit job via /api/v1/jobs
        2. Poll /api/v1/jobs/{id} until status is 'completed' or 'failed'
        3. Download results via /api/v1/jobs/{id}/download
        4. Convert CSV rows to RawCandidate payloads
        5. Enrich candidates using existing scrape_site() logic
        """
        # Step 1: Submit Job
        search_query = f"{query.industry} {query.location}".strip()
        print(f"[{self.name}] Submitting gosom job for: {search_query}...", flush=True)
        try:
            submit_resp = requests.post(
                f"{self.API_BASE_URL}/jobs",
                json={
                    "name": f"Discovery: {search_query}",
                    "keywords": [search_query],
                    "lang": "en",
                    "depth": 1,
                    "email": True, # Use scraper's built-in email extraction as a first pass
                    "max_time": 3600
                },
                timeout=20
            )
            submit_resp.raise_for_status()
            job_id = submit_resp.json().get("id")
        except Exception as e:
            print(f"[{self.name}] Failed to submit job to gosom API: {e}", flush=True)
            return DiscoveryBatch(
                source=self.name,
                candidates=[],
                meta=SourceMeta(source=self.name, request_count=1),
            )

        # Step 2: Poll for Completion
        start_time = time.time()
        job_completed = False
        print(f"[{self.name}] Polling for job {job_id} completion...", flush=True)
        while time.time() - start_time < self.MAX_POLL_TIME:
            try:
                status_resp = requests.get(f"{self.API_BASE_URL}/jobs/{job_id}", timeout=20)
                status_resp.raise_for_status()
                status = status_resp.json().get("Status", "").lower()

                if status == "completed" or status == "ok":
                    print(f"[{self.name}] Job {job_id} completed!", flush=True)
                    job_completed = True
                    break
                if status == "failed":
                    print(f"[{self.name}] Job {job_id} failed according to API.", flush=True)
                    break
            except Exception as e:
                print(f"[{self.name}] Error polling job {job_id}: {e}", flush=True)

            time.sleep(self.POLL_INTERVAL)

        if not job_completed:
            print(f"[{self.name}] Job {job_id} timed out or failed.", flush=True)
            return DiscoveryBatch(
                source=self.name,
                candidates=[],
                meta=SourceMeta(source=self.name, request_count=2),
            )

        # Step 3: Download Results
        print(f"[{self.name}] Downloading CSV results for job {job_id}...", flush=True)
        try:
            download_resp = requests.get(f"{self.API_BASE_URL}/jobs/{job_id}/download", timeout=30)
            download_resp.raise_for_status()
            csv_content = download_resp.text
        except Exception as e:
            print(f"[{self.name}] Failed to download results for job {job_id}: {e}", flush=True)
            return DiscoveryBatch(
                source=self.name,
                candidates=[],
                meta=SourceMeta(source=self.name, request_count=3),
            )

        # Step 4: Parse CSV to RawCandidates
        candidates = []
        request_count = 3

        # Use csv module to handle quoting correctly
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)

        processed = 0
        for row in reader:
            if processed >= query.max_results:
                break

            # 1. Junk Keyword Filter
            company_name = row.get("title") or ""
            category_str = row.get("category") or ""
            if any(kw.lower() in company_name.lower() or kw.lower() in category_str.lower() for kw in self.JUNK_KEYWORDS):
                continue

            # 2. Geo-Fencing (Simple check: target location must be in address)
            address = row.get("address") or ""
            if query.location and query.location.lower() not in address.lower():
                continue

            # Map CSV columns to the payload structure expected by the existing normalizer
            payload = {
                "company_name": company_name,
                "website": row.get("website"),
                "phone": row.get("phone"),
                "address": address,
                "rating": self._parse_float(row.get("review_rating")),
                "reviews": self._parse_int(row.get("review_count")),
                "category": [row.get("category")] if row.get("category") else [],
                "place_id": row.get("place_id"),
                "google_maps_url": row.get("link"),
                "source": "google_maps",
                "emails": self._parse_list(row.get("emails")),
                "phones": [row.get("phone")] if row.get("phone") else [],
                "socials": {},
                "about_page": None,
                "contact_page": None,
            }


            if not payload["company_name"]:
                continue

            # Step 5: Enrich with existing website scraping logic
            website = payload.get("website")
            if website:
                # Clean blacklisted websites from payload immediately
                if not self._is_valid_business_website(website):
                    payload["website"] = None
                    website = None # Prevent scraping

            if website:
                try:
                    website_lead_data = scrape_site(website)
                    if website_lead_data:
                        payload = self._merge_website_data(payload, website_lead_data)
                    request_count += 1
                except Exception as e:
                    print(f"[{self.name}] Failed to scrape website {website}: {e}", flush=True)

            # Final B2B Validation: must have name, valid website, address, and category
            if not (payload.get("company_name") and payload.get("website") and payload.get("address") and payload.get("category")):
                continue

            candidates.append(
                RawCandidate(
                    payload=payload,
                    source=self.name,
                    fetched_at=datetime.now(UTC),
                )
            )
            processed += 1

        print(f"[{self.name}] CSV parsed. {len(candidates)} businesses discovered.", flush=True)

        return DiscoveryBatch(
            source=self.name,
            candidates=candidates,
            meta=SourceMeta(source=self.name, request_count=request_count),
        )

    def _parse_float(self, val: Optional[str]) -> Optional[float]:
        if not val: return None
        try: return float(val)
        except ValueError: return None

    def _parse_int(self, val: Optional[str]) -> Optional[int]:
        if not val: return None
        try: return int(float(val))
        except ValueError: return None

    def _parse_list(self, val: Optional[str]) -> List[str]:
        if not val: return []
        if val.startswith("[") and val.endswith("]"):
            try:
                import json
                return json.loads(val.replace("'", "\""))
            except:
                pass
        return [e.strip() for e in val.split(",") if e.strip()]

    def _is_valid_business_website(self, website: str) -> bool:
        """Check if website is a valid business site (not a directory or social profile)."""
        if not website or not isinstance(website, str):
            return False
        website_lower = website.lower().strip()
        if not website_lower.startswith(("http://", "https://")):
            return False

        try:
            from urllib.parse import urlparse
            domain = urlparse(website_lower).netloc.lower().removeprefix("www.")

            # Check against strict blacklist
            for black_domain in self.BLACKLISTED_DOMAINS:
                if black_domain in domain:
                    return False
            return True
        except Exception:
            return False

    def _merge_website_data(self, google_data: dict, website_data: dict) -> dict:
        """Merge website scraped data with Google Maps data."""
        merged = google_data.copy()
        contact_fields = ["emails", "phones", "socials"]
        for field in contact_fields:
            if website_data.get(field):
                merged[field] = website_data[field]

        additional_fields = ["about_page", "contact_page"]
        for field in additional_fields:
            if website_data.get(field):
                merged[field] = website_data[field]

        if website_data.get("emails") and not merged.get("emails"):
            merged["emails"] = website_data["emails"]
        if website_data.get("phones") and not merged.get("phones"):
            merged["phones"] = website_data["phones"]

        return merged
