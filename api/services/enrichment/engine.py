import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

from .base import BaseEnrichmentProvider
from .website import WebsiteEnrichmentProvider
from scraper.database import get_connection, utc_now

class UnifiedEnrichmentEngine:
    """
    Orchestrates multiple enrichment providers to build a single Business Profile.
    """

    def __init__(self):
        # Register providers. In a production system, this could be dynamic via config.
        self.providers: Dict[str, BaseEnrichmentProvider] = {
            "scrapegraph": WebsiteEnrichmentProvider(),
            # Future providers:
            # "google_maps": GoogleMapsProvider(),
            # "scout": ScoutProvider(),
        }

        # Priority for merging: Higher index = higher priority
        # Manual > Website > Google Maps > Scout
        self.priority_map = {
            "manual": 100,
            "scrapegraph": 80,
            "google_maps": 60,
            "scout": 40
        }

    def enrich_lead(self, lead_id: int, website: str, company_name: str) -> Dict[str, Any]:
        """
        Triggers parallel enrichment and merges results into a Business Profile.
        """
        # 1. Parallel Fetching
        results = {}
        with ThreadPoolExecutor() as executor:
            future_to_provider = {
                executor.submit(provider.fetch_data, lead_id, website, company_name): name
                for name, provider in self.providers.items()
            }
            for future in future_to_provider:
                name = future_to_provider[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    results[name] = None # Handle as failed

        # 2. Persist Raw Data
        self._persist_raw_data(lead_id, results)

        # 3. Merge into Business Profile
        profile = self._merge_to_profile(lead_id, company_name, website, results)

        # 4. Persist Final Profile
        self._persist_profile(lead_id, profile)

        return profile

    def _merge_to_profile(self, lead_id: int, company_name: str, website: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merges data from multiple providers into a standardized Business Profile.
        """
        profile = {
            "lead_id": lead_id,
            "company_name": company_name,
            "website": website,
            "industry": None,
            "location": {"city": None, "state": None, "country": None, "address": None},
            "contact_info": {
                "emails": set(),
                "phones": set(),
                "social_links": set(),
                "contact_page": None
            },
            "business_details": {
                "description": None,
                "size": None,
                "founding_year": None,
                "category": None,
                "tagline": None,
                "services": set(),
                "products": set(),
                "technologies_used": set(),
                "business_hours": None
            },
            "website_metadata": {
                "title": None,
                "meta_description": None,
                "favicon": None,
                "language": None
            },
            "technical_signals": {
                "cms": None,
                "analytics": set(),
                "framework": None
            },
            "raw_sources": {},
            "updated_at": utc_now()
        }

        # Sort providers by priority to ensure higher priority overrides
        sorted_providers = sorted(
            self.providers.keys(),
            key=lambda x: self.priority_map.get(x, 0)
        )

        for provider_name in sorted_providers:
            res = results.get(provider_name)
            if not res or res.status != "success":
                continue

            data = res.data
            profile["raw_sources"][provider_name] = data

            # --- Scalar Overrides ---
            # Description/Summary
            desc = data.get("company_summary") or data.get("description") or data.get("summary")
            if desc:
                profile["business_details"]["description"] = desc

            # Industry/Category
            ind = data.get("industry") or data.get("industry_category") or data.get("category")
            if ind:
                profile["industry"] = ind
                profile["business_details"]["category"] = ind

            # Tagline
            tagline = data.get("tagline")
            if tagline:
                profile["business_details"]["tagline"] = tagline

            # --- Contact Info (Union Merge) ---
            emails = data.get("emails", [])
            if isinstance(emails, list):
                profile["contact_info"]["emails"].update(emails)
            elif emails:
                profile["contact_info"]["emails"].add(emails)

            phones = data.get("phones", [])
            if isinstance(phones, list):
                profile["contact_info"]["phones"].update(phones)
            elif phones:
                profile["contact_info"]["phones"].add(phones)

            # Social Links (from structural parser)
            socials = data.get("social_links", {})
            if isinstance(socials, dict):
                profile["contact_info"]["social_links"].update(socials.values())

            # Contact Page
            pages = data.get("pages", {})
            if isinstance(pages, dict) and pages.get("contact_page"):
                profile["contact_info"]["contact_page"] = pages["contact_page"]

            # --- Business Details (Union Merge) ---
            services = data.get("services", [])
            if isinstance(services, list):
                profile["business_details"]["services"].update(services)
            elif services:
                profile["business_details"]["services"].add(services)

            products = data.get("products", [])
            if isinstance(products, list):
                profile["business_details"]["products"].update(products)
            elif products:
                profile["business_details"]["products"].add(products)

            tech = data.get("technologies_used", [])
            if isinstance(tech, list):
                profile["business_details"]["technologies_used"].update(tech)
            elif tech:
                profile["business_details"]["technologies_used"].add(tech)

            # --- Website Metadata ---
            meta = data.get("metadata", {})
            if isinstance(meta, dict):
                for key in ["title", "meta_description", "favicon", "language"]:
                    val = meta.get(key)
                    if val:
                        profile["website_metadata"][key] = val

            # --- Technical Signals ---
            signals = data.get("technical_signals", {})
            if isinstance(signals, dict):
                cms = signals.get("cms")
                if cms and cms != "unknown":
                    profile["technical_signals"]["cms"] = cms

                framework = signals.get("framework")
                if framework and framework != "unknown":
                    profile["technical_signals"]["framework"] = framework

                analytics = signals.get("analytics", [])
                if isinstance(analytics, list):
                    profile["technical_signals"]["analytics"].update(analytics)

        # Convert sets back to lists for JSON serialization
        profile["contact_info"]["emails"] = list(profile["contact_info"]["emails"])
        profile["contact_info"]["phones"] = list(profile["contact_info"]["phones"])
        profile["contact_info"]["social_links"] = list(profile["contact_info"]["social_links"])

        profile["business_details"]["services"] = list(profile["business_details"]["services"])
        profile["business_details"]["products"] = list(profile["business_details"]["products"])
        profile["business_details"]["technologies_used"] = list(profile["business_details"]["technologies_used"])

        profile["technical_signals"]["analytics"] = list(profile["technical_signals"]["analytics"])

        return profile

    def _persist_raw_data(self, lead_id: int, results: Dict[str, Any]):
        with get_connection() as conn:
            for name, res in results.items():
                if res:
                    conn.execute(
                        "INSERT INTO enrichment_raw_data (lead_id, provider_name, raw_payload, created_at) VALUES (?, ?, ?, ?)",
                        (lead_id, name, json.dumps(res.data), utc_now())
                    )

    def _persist_profile(self, lead_id: int, profile: Dict[str, Any]):
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO business_profiles (lead_id, profile_json, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(lead_id) DO UPDATE SET profile_json=excluded.profile_json, updated_at=excluded.updated_at",
                (lead_id, json.dumps(profile), profile["updated_at"])
            )

    def get_profile(self, lead_id: int) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute("SELECT profile_json FROM business_profiles WHERE lead_id = ?", (lead_id,)).fetchone()
            return json.loads(row["profile_json"]) if row else None

# Singleton instance
uee_engine = UnifiedEnrichmentEngine()
