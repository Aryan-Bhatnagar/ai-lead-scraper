"""Extracts feature quality ratios (0.0–1.0) from a UnifiedLead.

No I/O — each method is a pure function that inspects the lead's fields.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from scraper.discovery.model import UnifiedLead

# Generic email domains that don't count as "business" emails
_GENERIC_DOMAINS = frozenset({
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "aol.com", "icloud.com", "protonmail.com", "mail.com",
})


def _is_business_email(email: str) -> bool:
    """Return True when the email is *not* from a generic free provider."""
    parts = email.strip().split("@")
    if len(parts) != 2:
        return False
    return parts[1].lower() not in _GENERIC_DOMAINS


class FeatureExtractor:
    """Extract 0.0‑1.0 quality ratios for each configured feature.

    Each method corresponds to one feature key and returns a ratio between
    0.0 (feature absent) and 1.0 (feature fully present / high quality).
    """

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def extract_all(self, lead: UnifiedLead) -> dict[str, float]:
        """Return a dict mapping feature_name → quality_ratio for all features."""
        return {
            "website_exists": self.website_exists(lead),
            "business_email": self.business_email(lead),
            "phone_number": self.phone_number(lead),
            "description_quality": self.description_quality(lead),
            "location_quality": self.location_quality(lead),
            "multiple_sources": self.multiple_sources(lead),
            "social_profiles": self.social_profiles(lead),
            "company_size_hints": self.company_size_hints(lead),
            "recent_activity": self.recent_activity(lead),
            "provider_confidence": self.provider_confidence(lead),
            "ai_enrichment_confidence": self.ai_enrichment_confidence(lead),
        }

    # ------------------------------------------------------------------
    # Individual feature extractors
    # ------------------------------------------------------------------
    @staticmethod
    def website_exists(lead: UnifiedLead) -> float:
        """1.0 if the lead has a website URL, else 0.0."""
        return 1.0 if lead.website else 0.0

    @staticmethod
    def business_email(lead: UnifiedLead) -> float:
        """1.0 if at least one email is a business address (non‑generic domain)."""
        for email in lead.emails:
            if _is_business_email(email):
                return 1.0
        return 0.0

    @staticmethod
    def phone_number(lead: UnifiedLead) -> float:
        """1.0 if the lead has at least one phone number."""
        return 1.0 if lead.phones else 0.0

    @staticmethod
    def description_quality(lead: UnifiedLead) -> float:
        """Quality based on description length (capped at ~200 characters)."""
        desc = lead.description or ""
        length = len(desc.strip())
        if length == 0:
            return 0.0
        if length < 30:
            return 0.3
        if length < 100:
            return 0.7
        return 1.0

    @staticmethod
    def location_quality(lead: UnifiedLead) -> float:
        """Completeness of location fields.

        * 0.0 — no location at all
        * 0.4 — country only
        * 0.6 — city or region only
        * 0.8 — city + country
        * 1.0 — city + region + country
        """
        if lead.location is None:
            return 0.0
        loc = lead.location
        has_city = bool(loc.city)
        has_region = bool(loc.region)
        has_country = bool(loc.country)

        if has_city and has_region and has_country:
            return 1.0
        if has_city and has_country:
            return 0.8
        if has_city or has_region:
            return 0.5
        if has_country:
            return 0.4
        return 0.0

    @staticmethod
    def multiple_sources(lead: UnifiedLead) -> float:
        """Ratio based on number of distinct discovery sources.

        The provenance.source field may be a comma‑separated list after
        deduplication.  2+ sources → 1.0, 1 source → 0.5.
        """
        source_str = lead.provenance.source if lead.provenance else ""
        if not source_str:
            return 0.0
        sources = [s.strip() for s in source_str.split(",") if s.strip()]
        count = len(sources)
        if count >= 3:
            return 1.0
        if count == 2:
            return 0.7
        return 0.5  # single source

    @staticmethod
    def social_profiles(lead: UnifiedLead) -> float:
        """Count of populated social profile keys.  Capped at 5."""
        if not lead.socials:
            return 0.0
        filled = sum(1 for v in lead.socials.values() if v)
        ratio = min(filled, 5) / 5.0
        return ratio

    @staticmethod
    def company_size_hints(lead: UnifiedLead) -> float:
        """Presence of size‑related fields.

        * jobs_completed (Upwork), review_count (Maps), categories.
        """
        signals = 0
        if lead.jobs_completed is not None and lead.jobs_completed > 0:
            signals += 1
        if lead.maps_review_count is not None and lead.maps_review_count > 0:
            signals += 1
        if lead.rating is not None and lead.rating > 0:
            signals += 1
        if lead.categories:
            signals += 0.5
        if lead.skills:
            signals += 0.5
        return min(signals / 3.0, 1.0)

    @staticmethod
    def recent_activity(lead: UnifiedLead) -> float:
        """Discoverer is within the past 30 days → 1.0, older → partial.

        If no discovered_at timestamp, returns 0.0.
        """
        if lead.provenance is None or lead.provenance.discovered_at is None:
            return 0.0
        dt = lead.provenance.discovered_at
        # Make sure dt is timezone-aware before subtracting
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff_days = (now - dt).days
        if diff_days < 30:
            return 1.0
        if diff_days < 90:
            return 0.5
        return 0.2

    @staticmethod
    def provider_confidence(lead: UnifiedLead) -> float:
        """Raw provider confidence score (0.0‑1.0)."""
        if lead.provenance is None:
            return 0.0
        conf = lead.provenance.confidence
        return min(max(conf, 0.0), 1.0)

    @staticmethod
    def ai_enrichment_confidence(lead: UnifiedLead) -> float:
        """1.0 when the lead appears to have been enriched by AI.

        Heuristic: a description composed by AI is typically ≥ 50 chars,
        and enriched leads often have normalized company names.
        """
        score = 0.0
        if lead.description and len(lead.description.strip()) >= 50:
            score += 0.5
        if lead.company_name_norm:
            score += 0.25
        if lead.industry:
            score += 0.25
        return min(score, 1.0)