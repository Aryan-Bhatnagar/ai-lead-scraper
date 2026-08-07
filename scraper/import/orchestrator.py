"""
Import Orchestrator.

Coordinates the import process: adapter selection, deduplication,
database persistence, and optional AI enrichment triggering.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseImportAdapter, ImportResult
from .registry import ImportAdapterRegistry, default_registry
from ..database import upsert_lead, get_connection, DB_PATH, utc_now
from ..discovery.model import UnifiedLead


@dataclass
class OrchestratorResult:
    """Result of an orchestrated import operation."""

    total_files: int = 0
    total_leads_imported: int = 0
    total_duplicates_skipped: int = 0
    total_errors: int = 0
    file_results: Dict[str, ImportResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def add_file_result(self, file_path: str, result: ImportResult) -> None:
        self.file_results[file_path] = result
        self.total_files += 1
        self.total_leads_imported += len(result.leads)
        self.total_duplicates_skipped += result.duplicates_skipped
        self.total_errors += len(result.errors)

    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.total_errors += 1


class ImportOrchestrator:
    """Orchestrates the import of lead data from various sources."""

    def __init__(
        self,
        registry: Optional[ImportAdapterRegistry] = None,
        db_path: Path | str = DB_PATH,
        auto_enrich: bool = False,
    ):
        """Initialize the orchestrator.

        Args:
            registry: Adapter registry (uses default if not provided).
            db_path: Database path.
            auto_enrich: Whether to trigger AI enrichment after import.
        """
        self.registry = registry or default_registry
        self.db_path = Path(db_path)
        self.auto_enrich = auto_enrich

        # Track seen identifiers across all imports for cross-file deduplication
        self._seen_emails: set = set()
        self._seen_domains: set = set()
        self._seen_source_urls: set = set()

    def import_file(self, file_path: str) -> ImportResult:
        """Import a single file using the appropriate adapter.

        Args:
            file_path: Path to the file to import.

        Returns:
            ImportResult with leads, errors, and stats.
        """
        # Auto-detect adapter
        adapter = self.registry.auto_detect(file_path)
        if not adapter:
            result = ImportResult()
            result.add_error(f"No adapter found for file: {file_path}")
            return result

        # Parse file
        result = adapter.parse_file(file_path)

        # Apply cross-file deduplication
        self._apply_cross_file_dedup(result)

        # Persist leads to database
        self._persist_leads(result.leads, adapter.source_name)

        return result

    def import_directory(self, directory: str, recursive: bool = True) -> OrchestratorResult:
        """Import all supported files from a directory.

        Args:
            directory: Path to directory containing import files.
            recursive: Whether to search subdirectories.

        Returns:
            OrchestratorResult with combined stats.
        """
        result = OrchestratorResult()
        dir_path = Path(directory)

        if not dir_path.exists():
            result.add_error(f"Directory not found: {directory}")
            return result

        # Find all files with supported extensions
        supported_exts = self.registry.list_extensions()
        files = []
        if recursive:
            for ext in supported_exts:
                files.extend(dir_path.rglob(f"*{ext}"))
        else:
            for ext in supported_exts:
                files.extend(dir_path.glob(f"*{ext}"))

        for file_path in files:
            file_result = self.import_file(str(file_path))
            result.add_file_result(str(file_path), file_result)

        return result

    def import_files(self, file_paths: List[str]) -> OrchestratorResult:
        """Import multiple specific files.

        Args:
            file_paths: List of file paths to import.

        Returns:
            OrchestratorResult with combined stats.
        """
        result = OrchestratorResult()

        for file_path in file_paths:
            file_result = self.import_file(file_path)
            result.add_file_result(file_path, file_result)

        return result

    def _apply_cross_file_dedup(self, result: ImportResult) -> None:
        """Apply cross-file deduplication to the import result."""
        deduplicated_leads = []

        for lead in result.leads:
            email_key = lead.emails[0].lower() if lead.emails else None
            domain_key = lead.website.lower() if lead.website else None
            source_url_key = lead.provenance.source_url.lower() if lead.provenance.source_url else None

            is_duplicate = False
            if email_key and email_key in self._seen_emails:
                is_duplicate = True
            if domain_key and domain_key in self._seen_domains:
                is_duplicate = True
            if source_url_key and source_url_key in self._seen_source_urls:
                is_duplicate = True

            if is_duplicate:
                result.duplicates_skipped += 1
                result.total_processed += 1
                continue

            if email_key:
                self._seen_emails.add(email_key)
            if domain_key:
                self._seen_domains.add(domain_key)
            if source_url_key:
                self._seen_source_urls.add(source_url_key)

            deduplicated_leads.append(lead)

        result.leads = deduplicated_leads

    def _persist_leads(self, leads: List[UnifiedLead], source_name: str) -> None:
        """Persist UnifiedLead objects to the database.

        Args:
            leads: List of UnifiedLead objects to persist.
            source_name: Normalized source name for the 'source' column.
        """
        for lead in leads:
            try:
                lead_dict = self._lead_to_dict(lead, source_name)
                upsert_lead(lead_dict, self.db_path)
            except Exception as e:
                # Log error but continue with other leads
                print(f"Error persisting lead {lead.company_name}: {e}")

    def _lead_to_dict(self, lead: UnifiedLead, source_name: str) -> Dict[str, Any]:
        """Convert UnifiedLead to database dictionary."""
        now = utc_now()
        location = lead.location or type('obj', (object,), {})()

        import json

        # Build the dictionary matching LEAD_COLUMNS
        lead_dict = {
            "company_name": lead.company_name or "",
            "industry": lead.industry or "",
            "company_description": lead.description or "",
            "contact_name": getattr(lead, "contact_name", "") or "",
            "contact_role": getattr(lead, "contact_role", "") or "",
            "email": lead.emails[0] if lead.emails else "",
            "phone": lead.phones[0] if lead.phones else "",
            "website": lead.website or "",
            "city": getattr(location, "city", "") or "",
            "country": getattr(location, "country", "") or "",
            "source_url": lead.provenance.source_url or "",
            "source_pages": str(lead.provenance.discovery_query) if lead.provenance.discovery_query else "",
            "email_source_page": "",
            "email_source_type": "",
            "phone_source_page": "",
            "phone_source_type": "",
            "scraped_at": lead.provenance.discovered_at.isoformat() if lead.provenance.discovered_at else now,
            "status": "imported",
            "quality_score": getattr(lead, "quality_score", 0) or 0,
            "data_quality": "UNKNOWN",
            "error": "",
            "lead_status": "NEW",
            # Enriched fields
            "quality_tier": "",
            "score_breakdown_json": "",
            "google_rating": lead.metadata.get("google_rating"),
            "maps_review_count": lead.metadata.get("maps_review_count"),
            "categories": json.dumps(lead.metadata.get("google_types", [])) if lead.metadata.get("google_types") else "",
            "socials_json": json.dumps(lead.socials) if lead.socials else "",
            # Phase 1 Unified Lead Model fields
            "address": getattr(location, "address", "") or "",
            "source": source_name,
            "discovery_date": lead.provenance.discovered_at.isoformat() if lead.provenance.discovered_at else now,
            "ai_score": None,
            "ai_summary": "",
            "recommended_service": "",
            "pain_points": "",
            "company_size_estimate": lead.metadata.get("company_size_estimate", ""),
            "decision_maker_guess": "",
            "buying_signals": "",
            "outreach_strategy": "",
            "ai_confidence": None,
            "opportunity_score": None,
            "score_explanation_json": "",
            "company_logo": "",
        }

        return lead_dict

    def reset_dedup_state(self) -> None:
        """Reset the cross-file deduplication state."""
        self._seen_emails.clear()
        self._seen_domains.clear()
        self._seen_source_urls.clear()