"""
Upwork JSON Import Adapter for Opportunities.

Maps Upwork job/opportunity JSON records to Opportunity model.
This adapter imports directly into the Opportunities repository.
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

from scraper.opportunities.opportunity_models import Opportunity
from scraper.opportunities.opportunity_repository import OpportunityRepository


class UpworkOpportunityImportAdapter:
    """Import adapter for Upwork JSON export files into Opportunities."""

    @property
    def source_name(self) -> str:
        return "Upwork"

    @property
    def supported_extensions(self) -> List[str]:
        return [".json"]

    def __init__(self, repository: Optional[OpportunityRepository] = None):
        """Initialize the adapter with an optional repository."""
        self.repository = repository or OpportunityRepository(storage_path="data/opportunities.json")

    def parse_file(self, file_path: str) -> ImportResult:
        """Parse Upwork JSON file and import into Opportunities repository."""
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
                opportunity = self.map_record(record)

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

                # Save to repository
                if self.repository.add(opportunity):
                    result.add_lead(opportunity)  # Using add_lead for tracking
                else:
                    result.add_duplicate()

            except Exception as e:
                result.add_error(f"Failed to map record: {e}")

        return result

    def map_record(self, record: Dict[str, Any]) -> Opportunity:
        """Map a single Upwork record to Opportunity."""
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

        # Parse published_at
        posted_time = None
        if published_at:
            try:
                # Handle ISO format with Z
                if published_at.endswith('Z'):
                    published_at = published_at[:-1] + '+00:00'
                posted_time = datetime.fromisoformat(published_at)
            except Exception:
                posted_time = None

        # Extract client info
        client = record.get("client", {})
        client_country = client.get("countryCode", "").strip() if isinstance(client, dict) else ""
        client_stats = client.get("stats", {}) if isinstance(client, dict) else {}
        client_rating = client_stats.get("feedbackRate", 0) if isinstance(client_stats, dict) else 0
        client_reviews = client_stats.get("feedbackCount", 0) if isinstance(client_stats, dict) else 0
        client_jobs_posted = client_stats.get("totalHires", 0) if isinstance(client_stats, dict) else 0
        client_hire_rate = client_stats.get("hireRate", 0) if isinstance(client_stats, dict) else 0

        # Parse budget
        budget_min = None
        budget_max = None
        currency = "USD"
        if isinstance(budget, dict):
            if budget.get("hourlyRate"):
                hourly = budget["hourlyRate"]
                budget_min = hourly.get("min")
                budget_max = hourly.get("max")
            elif budget.get("fixedBudget"):
                budget_max = budget.get("fixedBudget")

        # Build provider_metadata with extra fields
        provider_metadata = {
            "budget": budget,
            "externalLink": external_link,
            "client": client,
            "vendor": record.get("vendor", {}),
            "applicationCost": record.get("applicationCost"),
            "customJobScore": record.get("customJobScore"),
            "isFeatured": record.get("isFeatured", False),
        }

        # Ensure required fields are present with defaults
        opportunity = Opportunity(
            id=str(uid),
            provider="upwork",
            project_title=title,
            description=description,
            budget_min=budget_min,
            budget_max=budget_max,
            currency=currency,
            client_country=client_country,
            category=category or subcategory,
            skills=skills,
            experience_level=record.get("vendor", {}).get("experienceLevel", "") if isinstance(record.get("vendor"), dict) else "",
            posted_time=posted_time,
            deadline=None,
            proposal_count=0,  # Not provided in dataset
            estimated_value=budget_max,
            url=external_link,
            provider_metadata=provider_metadata
        )
        return opportunity


# For backward compatibility, also provide a class that works with the import orchestrator
class UpworkImportAdapter:
    """Import adapter for Upwork JSON export files (legacy - maps to UnifiedLead)."""

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

    def map_record(self, record: Dict[str, Any]):
        """Map a single Upwork record to UnifiedLead (legacy)."""
        # Import here to avoid circular imports
        from scraper.discovery.model import UnifiedLead, LocationData, Provenance
        from .base import BaseImportAdapter

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
        client_country = client.get("countryCode", "").strip() if isinstance(client, dict) else ""
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
        location = LocationData(
            city=client_city,
            country=client_country,
        )

        # Source URL
        source_url = external_link or f"upwork://job/{uid}"

        # Provenance
        provenance = Provenance(
            source="Upwork",
            source_url=source_url,
            discovered_at=datetime.now(UTC),
            discovery_query={"import_source": "Upwork"},
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
            emails=[],
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


def register_upwork_adapters():
    """Register the Upwork import adapters."""
    from .registry import default_registry
    default_registry.register(UpworkImportAdapter())
    # Note: UpworkOpportunityImportAdapter is not registered in the default registry
    # as it works with OpportunityRepository directly, not UnifiedLead


# Auto-register on module import
register_upwork_adapters()