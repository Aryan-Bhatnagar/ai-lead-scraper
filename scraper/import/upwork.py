"""
Upwork JSON Import Adapter.

Maps Upwork job/opportunity JSON records to UnifiedLead model.
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseImportAdapter, ImportResult
from ..discovery.model import UnifiedLead, LocationData, Provenance


class UpworkImportAdapter(BaseImportAdapter):
    """Import adapter for Upwork JSON export files."""

    @property
    def source_name(self) -> str:
        return "Upwork"

    @property
    def supported_extensions(self) -> List[str]:
        return [".json"]

    def parse_file(self, file_path: str) -> ImportResult:
        """Parse Upwork JSON file."""
        result = ImportResult()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            result.add_error(f"Failed to parse JSON: {e}")
            return result

        # Upwork exports can be an array or an object with a data array
        records = []
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            # Try common keys for the data array
            for key in ["data", "records", "jobs", "opportunities", "results"]:
                if key in data and isinstance(data[key], list):
                    records = data[key]
                    break

        if not records:
            result.add_error("No records found in Upwork JSON")
            return result

        seen_uids = set()
        seen_external_links = set()

        for record in records:
            try:
                lead = self.map_record(record)

                # Deduplication: skip if uid or external link already seen
                uid = record.get("uid", "").strip()
                external_link = record.get("externalLink", "").strip()

                if uid and uid in seen_uids:
                    result.add_duplicate()
                    continue
                if external_link and external_link in seen_external_links:
                    result.add_duplicate()
                    continue

                if uid:
                    seen_uids.add(uid)
                if external_link:
                    seen_external_links.add(external_link)

                result.add_lead(lead)

            except Exception as e:
                result.add_error(f"Failed to map record: {e}")

        return result

    def map_record(self, record: Dict[str, Any]) -> UnifiedLead:
        """Map a single Upwork record to UnifiedLead."""
        # Extract job info
        uid = record.get("uid", "").strip()
        title = record.get("title", "").strip()
        description = record.get("description", "").strip()
        budget = record.get("budget", {})
        budget_amount = budget.get("amount", "") if isinstance(budget, dict) else str(budget)
        budget_type = budget.get("type", "") if isinstance(budget, dict) else ""
        skills = record.get("skills", [])
        published_at = record.get("publishedAt", "").strip()
        category = record.get("category", "").strip()
        subcategory = record.get("subcategory", "").strip()
        external_link = record.get("externalLink", "").strip()

        # Extract client info
        client = record.get("client", {})
        client_name = client.get("name", "").strip() if isinstance(client, dict) else ""
        client_country = client.get("country", "").strip() if isinstance(client, dict) else ""
        client_city = client.get("city", "").strip() if isinstance(client, dict) else ""
        client_rating = client.get("rating", "") if isinstance(client, dict) else ""
        client_reviews = client.get("reviews", "") if isinstance(client, dict) else ""
        client_jobs_posted = client.get("jobsPosted", "") if isinstance(client, dict) else ""
        client_hire_rate = client.get("hireRate", "") if isinstance(client, dict) else ""

        # Build company name from client or use "Upwork Client"
        company_name = client_name or f"Upwork Client ({uid[:8]})"

        # Use external link as website if available
        website = ""
        if external_link:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(external_link)
                website = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                website = external_link

        # Industry from category
        industry = category or subcategory

        # Location from client
        location = self._create_location(
            city=client_city,
            country=client_country,
        )

        # Source URL
        source_url = external_link or f"upwork://job/{uid}"

        # Provenance
        provenance = self._create_provenance(
            source_url=source_url,
            raw_ref=f"upwork_export:{uid}",
        )

        # Build description with job details
        full_description = description
        if budget_amount:
            full_description += f"\n\nBudget: {budget_amount} ({budget_type})"
        if skills:
            full_description += f"\n\nSkills: {', '.join(skills)}"

        # Build UnifiedLead
        lead = UnifiedLead(
            company_name=company_name,
            website=website,
            description=full_description,
            industry=industry,
            location=location,
            provenance=provenance,
            emails=[],  # Upwork doesn't provide emails
            phones=[],
            socials={},
        )

        # Set contact info - use client info if available
        lead.contact_name = client_name
        lead.contact_role = "Hiring Manager"

        # Store Upwork-specific metadata
        lead.metadata["upwork_uid"] = uid
        lead.metadata["upwork_budget"] = budget_amount
        lead.metadata["upwork_budget_type"] = budget_type
        lead.metadata["upwork_skills"] = skills
        lead.metadata["upwork_published_at"] = published_at
        lead.metadata["upwork_category"] = category
        lead.metadata["upwork_client_rating"] = client_rating
        lead.metadata["upwork_client_reviews"] = client_reviews
        lead.metadata["upwork_client_jobs_posted"] = client_jobs_posted
        lead.metadata["upwork_client_hire_rate"] = client_hire_rate
        lead.metadata["upwork_external_link"] = external_link
        lead.metadata["upwork_raw"] = record

        return lead