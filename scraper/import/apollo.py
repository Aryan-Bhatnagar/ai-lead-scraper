"""
Apollo.io JSON Import Adapter.

Maps Apollo API JSON records to UnifiedLead model.
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseImportAdapter, ImportResult
from ..discovery.model import UnifiedLead, LocationData, Provenance


class ApolloImportAdapter(BaseImportAdapter):
    """Import adapter for Apollo.io JSON export files."""

    @property
    def source_name(self) -> str:
        return "Apollo"

    @property
    def supported_extensions(self) -> List[str]:
        return [".json"]

    def parse_file(self, file_path: str) -> ImportResult:
        """Parse Apollo JSON file."""
        result = ImportResult()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            result.add_error(f"Failed to parse JSON: {e}")
            return result

        # Apollo exports can be an array or an object with a data array
        records = []
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            # Try common keys for the data array
            for key in ["data", "records", "leads", "contacts", "results"]:
                if key in data and isinstance(data[key], list):
                    records = data[key]
                    break

        if not records:
            result.add_error("No records found in Apollo JSON")
            return result

        seen_emails = set()
        seen_domains = set()

        for record in records:
            try:
                lead = self.map_record(record)

                # Deduplication: skip if email or domain already seen
                email_key = lead.emails[0].lower() if lead.emails else None
                domain_key = lead.website.lower() if lead.website else None

                if email_key and email_key in seen_emails:
                    result.add_duplicate()
                    continue
                if domain_key and domain_key in seen_domains:
                    result.add_duplicate()
                    continue

                if email_key:
                    seen_emails.add(email_key)
                if domain_key:
                    seen_domains.add(domain_key)

                result.add_lead(lead)

            except Exception as e:
                result.add_error(f"Failed to map record: {e}")

        return result

    def map_record(self, record: Dict[str, Any]) -> UnifiedLead:
        """Map a single Apollo record to UnifiedLead."""
        # Extract contact info
        first_name = record.get("firstName", "").strip()
        last_name = record.get("lastName", "").strip()
        contact_name = f"{first_name} {last_name}".strip()
        contact_role = record.get("title", "").strip()
        email = record.get("email", "").strip()
        phone = record.get("phone", "").strip()
        linkedin_url = record.get("linkedinUrl", "").strip()

        # Extract company info
        company_name = record.get("companyName", "").strip()
        website = record.get("companyDomain", "").strip()
        industry = record.get("companyIndustry", "")
        if isinstance(industry, list):
            industry = ", ".join([str(i) for i in industry])
        industry = industry.strip()
        company_description = record.get("companyDescription", "").strip()
        company_size = str(record.get("companySize", "")).strip()

        # Location
        city = record.get("city", "").strip()
        country = record.get("country", "").strip()
        state = record.get("state", "").strip()

        # Build location
        location = self._create_location(
            city=city,
            country=country,
            region=state,
        )

        # Build source URL - prefer LinkedIn, then company website
        source_url = linkedin_url or f"https://{website}" if website else f"apollo://{company_name}/{email}"

        # Build provenance
        provenance = self._create_provenance(
            source_url=source_url,
            raw_ref=f"apollo_export:{record.get('id', 'unknown')}",
        )

        # Social links
        socials = {}
        if linkedin_url:
            socials["linkedin"] = linkedin_url

        # Build UnifiedLead
        lead = UnifiedLead(
            company_name=company_name,
            website=website,
            description=company_description,
            industry=industry,
            location=location,
            provenance=provenance,
            emails=[email] if email else [],
            phones=[phone] if phone else [],
            socials=socials,
        )

        # Set contact info
        lead.contact_name = contact_name
        lead.contact_role = contact_role

        # Store company size estimate
        lead.metadata["company_size_estimate"] = company_size
        lead.metadata["apollo_raw"] = record

        return lead