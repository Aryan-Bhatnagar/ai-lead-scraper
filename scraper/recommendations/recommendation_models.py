"""
Recommendation models for the AI Lead Scraper.
Defines data structures for recommendation results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class Recommendation:
    """A recommendation for a lead."""
    lead_id: int
    priority: str  # Critical, High, Medium, Low
    next_action: str  # Research Website, Find Email, Contact Immediately, Follow Up, LinkedIn Outreach, Phone Call, Ignore
    confidence: float  # 0.0 to 1.0
    reasons: List[str] = field(default_factory=list)
    suggested_outreach: str = ""  # e.g., "Email", "Phone", "LinkedIn"
    risk_level: str = ""  # Low, Medium, High
    estimated_conversion: float = 0.0  # 0.0 to 1.0
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class RecommendationSummary:
    """Summary of recommendations across all leads."""
    total_leads: int = 0
    priority_distribution: Dict[str, int] = field(default_factory=dict)
    next_action_distribution: Dict[str, int] = field(default_factory=dict)
    average_confidence: float = 0.0
    average_estimated_conversion: float = 0.0
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())