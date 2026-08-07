"""
Legacy lead persistence adapter for integrating with the original lead storage (scraper.database).

This adapter allows the discovery orchestrator to persist leads directly to the
legacy `leads` table used by the API and the original lead scraper.
"""

from __future__ import annotations

from typing import Iterable, List
from scraper.discovery.model import UnifiedLead
from scraper.scoring.models import ScoredLead
import scraper.database as db
from pathlib import Path


class LegacyLeadPersistenceAdapter:
    """
    Persists leads to the legacy leads table via scraper.database.upsert_lead.

    The adapter expects UnifiedLead or ScoredLead objects and converts them
    to a dictionary matching the legacy leads table schema.
    """

    def __init__(self, db_path: str | Path = "data/leads.db"):
        self.db_path = Path(db_path)
        # Ensure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def bulk_insert(self, leads: Iterable[UnifiedLead | ScoredLead]) -> List[str]:
        """
        Insert or update leads in the legacy leads table.

        Args:
            leads: An iterable of UnifiedLead or ScoredLead objects.

        Returns:
            A list of lead IDs (empty list for now; the legacy upsert_lead returns the
            database row ID, but we don't capture it here for simplicity).
        """
        inserted_ids: List[str] = []
        for lead in leads:
            # Convert to a dictionary for the legacy leads table
            # Pass the ScoredLead directly so _to_legacy_dict can extract scoring info
            legacy_dict = self._to_legacy_dict(lead)
            # Use upsert_lead to insert or update
            lead_id = db.upsert_lead(legacy_dict, str(self.db_path))
            inserted_ids.append(str(lead_id))
            print(f"[LegacyAdapter] Inserted/updated lead: {legacy_dict.get('company_name')} with ID {lead_id}")

        return inserted_ids

    def _to_legacy_dict(self, lead: UnifiedLead | ScoredLead) -> dict:
        """
        Map a UnifiedLead or ScoredLead to the legacy leads table columns.

        The legacy table columns are defined in scraper.database.LEAD_COLUMNS.
        We map as many fields as possible; missing fields are set to empty strings.
        """
        # Extract UnifiedLead from ScoredLead if necessary
        if isinstance(lead, ScoredLead):
            scored_lead = lead
            unified_lead = lead.lead
        else:
            scored_lead = None
            unified_lead = lead

        # Start with empty values for all legacy columns
        legacy_data = {col: "" for col in db.LEAD_COLUMNS}

        # Map fields that exist in UnifiedLead
        if unified_lead.company_name:
            legacy_data["company_name"] = unified_lead.company_name
        if unified_lead.website:
            legacy_data["website"] = unified_lead.website
        if unified_lead.description:
            legacy_data["company_description"] = unified_lead.description
        if unified_lead.industry:
            legacy_data["industry"] = unified_lead.industry
        # Location data
        if unified_lead.location:
            if unified_lead.location.city:
                legacy_data["city"] = unified_lead.location.city
            if unified_lead.location.country:
                legacy_data["country"] = unified_lead.location.country
            # Note: legacy table has city and country, but not region/address
        # Contact info
        if unified_lead.emails:
            legacy_data["email"] = unified_lead.emails[0] if unified_lead.emails else ""
        if unified_lead.phones:
            legacy_data["phone"] = unified_lead.phones[0] if unified_lead.phones else ""
        # Socials - store as JSON
        if unified_lead.socials:
            import json
            legacy_data["socials_json"] = json.dumps(unified_lead.socials)
        # Provenance: we can store the source URL in source_url
        if unified_lead.provenance and unified_lead.provenance.source_url:
            legacy_data["source_url"] = unified_lead.provenance.source_url
        # Set scraped_at to now if not provided
        from datetime import datetime, timezone
        if unified_lead.provenance and unified_lead.provenance.discovered_at:
            legacy_data["scraped_at"] = unified_lead.provenance.discovered_at.isoformat()
        else:
            legacy_data["scraped_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        # Status: we can set a default scraper status, e.g., "pending" or "new"
        legacy_data["status"] = "pending"
        # Enriched fields from UnifiedLead (Google Maps data)
        if unified_lead.maps_rating is not None:
            legacy_data["google_rating"] = unified_lead.maps_rating
        if unified_lead.maps_review_count is not None:
            legacy_data["maps_review_count"] = unified_lead.maps_review_count
        if unified_lead.categories:
            import json
            legacy_data["categories"] = json.dumps(unified_lead.categories)
        # Data quality and quality score: extract from ScoredLead if available
        if scored_lead is not None:
            legacy_data["quality_score"] = scored_lead.overall_score
            # Map quality tier to data_quality
            tier_map = {
                "excellent": "HIGH",
                "high": "HIGH",
                "good": "MEDIUM",
                "medium": "MEDIUM",
                "average": "LOW",
                "low": "LOW",
                "poor": "LOW",
            }
            legacy_data["data_quality"] = tier_map.get(scored_lead.quality_tier.lower(), "unknown")
            # Add new enriched fields from ScoredLead
            legacy_data["quality_tier"] = scored_lead.quality_tier
            if scored_lead.explanation:
                import json
                legacy_data["score_breakdown_json"] = json.dumps(scored_lead.explanation.model_dump() if hasattr(scored_lead.explanation, 'model_dump') else str(scored_lead.explanation))
        else:
            legacy_data["quality_score"] = 0
            legacy_data["data_quality"] = "unknown"
            legacy_data["quality_tier"] = ""
            legacy_data["score_breakdown_json"] = ""
        # Error: leave empty
        legacy_data["error"] = ""
        # Source pages: not available, leave empty
        legacy_data["source_pages"] = ""
        # Email/source page/type: leave empty
        legacy_data["email_source_page"] = ""
        legacy_data["email_source_type"] = ""
        legacy_data["phone_source_page"] = ""
        legacy_data["phone_source_type"] = ""

        return legacy_data