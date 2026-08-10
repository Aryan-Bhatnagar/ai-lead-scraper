"""
CSV Import Adapter.

Maps CSV records to UnifiedLead model. Flexible column mapping.
"""

from __future__ import annotations

import csv
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseImportAdapter, ImportResult
from ..discovery.model import UnifiedLead, LocationData, Provenance


class CSVImportAdapter(BaseImportAdapter):
    """Import adapter for CSV files with configurable column mapping."""

    # Default column mapping from common CSV formats
    DEFAULT_COLUMN_MAP = {
        "company_name": ["company_name", "company", "name", "business_name", "organization"],
        "website": ["website", "domain", "url", "site", "homepage"],
        "description": ["description", "company_description", "about", "summary", "details"],
        "industry": ["industry", "sector", "category", "vertical"],
        "contact_name": ["contact_name", "name", "contact", "person_name", "full_name"],
        "contact_role": ["contact_role", "role", "title", "position", "job_title"],
        "email": ["email", "email_address", "contact_email", "e_mail"],
        "phone": ["phone", "phone_number", "telephone", "mobile", "contact_phone"],
        "city": ["city", "town", "location_city"],
        "country": ["country", "nation", "location_country"],
        "region": ["region", "state", "province", "location_state"],
        "address": ["address", "street_address", "location_address"],
        "source_url": ["source_url", "url", "link", "profile_url", "linkedin_url"],
        "source": ["source", "source_name", "provider", "origin"],
    }

    def __init__(self, column_map: Optional[Dict[str, List[str]]] = None):
        """Initialize with optional custom column mapping.

        Args:
            column_map: Dict mapping UnifiedLead fields to lists of possible CSV column names.
        """
        self.column_map = column_map or self.DEFAULT_COLUMN_MAP

    @property
    def source_name(self) -> str:
        return "CSV Import"

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    def parse_file(self, file_path: str) -> ImportResult:
        """Parse CSV file."""
        result = ImportResult()

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                # Detect dialect
                sample = f.read(1024)
                f.seek(0)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample)
                f.seek(0)
                reader = csv.DictReader(f, dialect=dialect)
                records = list(reader)
        except Exception as e:
            result.add_error(f"Failed to parse CSV: {e}")
            return result

        if not records:
            result.add_error("No records found in CSV")
            return result

        # Build column index map
        fieldnames = reader.fieldnames or []
        column_index = self._build_column_index(fieldnames)

        seen_emails = set()
        seen_domains = set()
        seen_source_urls = set()

        for idx, record in enumerate(records):
            try:
                # Map CSV columns to standard fields
                mapped_record = self._map_columns(record, column_index)
                mapped_record["_row_number"] = idx + 1

                lead = self.map_record(mapped_record)

                # Deduplication
                email_key = lead.emails[0].lower() if lead.emails else None
                domain_key = lead.website.lower() if lead.website else None
                source_url_key = lead.provenance.source_url.lower() if lead.provenance.source_url else None

                is_duplicate = False
                if email_key and email_key in seen_emails:
                    is_duplicate = True
                if domain_key and domain_key in seen_domains:
                    is_duplicate = True
                if source_url_key and source_url_key in seen_source_urls:
                    is_duplicate = True

                if is_duplicate:
                    result.add_duplicate()
                    continue

                if email_key:
                    seen_emails.add(email_key)
                if domain_key:
                    seen_domains.add(domain_key)
                if source_url_key:
                    seen_source_urls.add(source_url_key)

                result.add_lead(lead)

            except Exception as e:
                result.add_error(f"Row {idx + 1}: Failed to map record: {e}")

        return result

    def _build_column_index(self, fieldnames: List[str]) -> Dict[str, str]:
        """Build mapping from standard field to actual CSV column name."""
        index = {}
        fieldnames_lower = {f.lower(): f for f in fieldnames}

        for standard_field, possible_names in self.column_map.items():
            for name in possible_names:
                if name.lower() in fieldnames_lower:
                    index[standard_field] = fieldnames_lower[name.lower()]
                    break

        return index

    def _map_columns(self, record: Dict[str, str], column_index: Dict[str, str]) -> Dict[str, str]:
        """Map CSV record columns to standard field names."""
        mapped = {}
        for standard_field, csv_column in column_index.items():
            mapped[standard_field] = record.get(csv_column, "").strip()
        # Also include any unmapped columns
        for key, value in record.items():
            if key not in column_index.values():
                mapped[key] = value.strip() if isinstance(value, str) else value
        return mapped

    def map_record(self, record: Dict[str, Any]) -> UnifiedLead:
        """Map a single CSV record to UnifiedLead."""
        # Extract fields with defaults
        company_name = record.get("company_name", "").strip()
        website = record.get("website", "").strip()
        description = record.get("description", "").strip()
        industry = record.get("industry", "").strip()
        contact_name = record.get("contact_name", "").strip()
        contact_role = record.get("contact_role", "").strip()
        email = record.get("email", "").strip()
        phone = record.get("phone", "").strip()
        city = record.get("city", "").strip()
        country = record.get("country", "").strip()
        region = record.get("region", "").strip()
        address = record.get("address", "").strip()
        source_url = record.get("source_url", "").strip()
        source = record.get("source", "CSV Import").strip()

        # Build location
        location = self._create_location(
            city=city,
            country=country,
            region=region,
            address=address,
        )

        # Source URL fallback
        if not source_url:
            if website:
                source_url = f"https://{website}" if not website.startswith("http") else website
            elif email:
                source_url = f"mailto:{email}"
            else:
                source_url = f"csv://{company_name}/{contact_name or 'contact'}"

        # Provenance
        provenance = self._create_provenance(
            source_url=source_url,
            raw_ref=f"csv_import:{record.get('_row_number', 'unknown')}",
        )
        provenance.source = source  # Override with CSV source column

        # Social links - check for common social columns
        socials = {}
        for platform in ["linkedin", "twitter", "facebook", "instagram", "github", "youtube"]:
            if platform in record and record[platform]:
                socials[platform] = record[platform].strip()

        # Build UnifiedLead
        lead = UnifiedLead(
            company_name=company_name,
            website=website,
            description=description,
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

        # Store metadata
        lead.metadata["csv_raw"] = record

        return lead