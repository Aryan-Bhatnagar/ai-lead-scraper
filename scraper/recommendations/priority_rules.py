"""
Priority rules for determining lead priority.
"""

from __future__ import annotations

from typing import Any
from scraper.database import LEAD_STATUSES


def determine_priority(lead: dict, score: int, lifecycle: str, source: str,
                       has_website: bool, has_email: bool, company_size: str,
                       location: str, days_since_created: int,
                       provider_confidence: float) -> str:
    """
    Determine the priority of a lead based on various factors.

    Returns one of: "Critical", "High", "Medium", "Low"
    """
    # Start with a base score
    priority_score = 0

    # Score contribution (0-40 points)
    if score >= 90:
        priority_score += 40
    elif score >= 80:
        priority_score += 30
    elif score >= 70:
        priority_score += 20
    elif score >= 60:
        priority_score += 10

    # Lifecycle contribution (0-20 points)
    lifecycle_scores = {
        "NEW": 10,
        "DISCOVERED": 15,
        "ENRICHED": 15,
        "SCORED": 20,
        "CONTACTED": 10,
        "RESPONDED": 15,
        "QUALIFIED": 20,
        "CUSTOMER": 5,  # Already converted, lower priority for new work
        "LOST": 0
    }
    priority_score += lifecycle_scores.get(lifecycle, 0)

    # Source credibility (0-10 points)
    trusted_sources = ["google_maps", "industry_directory", "partner_referral"]
    if source in trusted_sources:
        priority_score += 10
    elif source in ["social_media", "forum"]:
        priority_score += 5

    # Contact information availability (0-15 points)
    if has_website and has_email:
        priority_score += 15
    elif has_website or has_email:
        priority_score += 8

    # Company size (if available, 0-10 points)
    size_scores = {
        "Enterprise": 10,
        "Medium": 7,
        "Small": 4,
        "Startup": 6,
        "Unknown": 0
    }
    priority_score += size_scores.get(company_size, 0)

    # Location bonus (0-5 points)
    # Example: prioritize certain regions
    high_value_locations = ["USA", "Canada", "UK", "Germany", "Australia"]
    if location in high_value_locations:
        priority_score += 5

    # Recency (0-10 points) - newer leads get higher priority
    if days_since_created <= 7:
        priority_score += 10
    elif days_since_created <= 30:
        priority_score += 5

    # Provider confidence (0-10 points)
    priority_score += int(provider_confidence * 10)

    # Convert score to priority level
    if priority_score >= 85:
        return "Critical"
    elif priority_score >= 70:
        return "High"
    elif priority_score >= 50:
        return "Medium"
    else:
        return "Low"