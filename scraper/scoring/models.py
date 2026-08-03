"""Lead scoring data models.

Defines the lightweight data structures used by the LeadScoringService.
No I/O or business logic — pure data containers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from scraper.discovery.model import UnifiedLead


@dataclass
class ScoreBreakdown:
    """Documents each feature's contribution to the overall score."""

    feature: str = ""
    label: str = ""
    weight: float = 0.0
    quality_ratio: float = 0.0  # 0.0 - 1.0
    contribution: float = 0.0   # weight × quality_ratio
    detail: str = ""            # human-readable explanation of the sub-score

    def format_line(self) -> str:
        """Return ``+15 Phone`` style line."""
        return f"+{int(round(self.contribution))} {self.label}"


@dataclass
class ScoreExplanation:
    """Full explanation for a scored lead's overall score.

    Includes the total and a line-item breakdown showing each feature's
    contribution, suitable for display or debugging.

    Example
    -------

        Overall Score: 87

        +25 Website
        +20 Business Email
        +15 Phone
        +10 Multiple Sources
        +8 Location
        +9 Description
    """

    overall_score: int = 0  # 0-100
    breakdowns: List[ScoreBreakdown] = field(default_factory=list)
    quality_tier: str = "low"

    def render_lines(self) -> List[str]:
        """Return a human-readable list of lines explaining the score."""
        lines = [f"Overall Score: {self.overall_score}", ""]
        # Sort breakdowns by contribution descending so the biggest factors
        # appear first.
        sorted_items = sorted(
            self.breakdowns, key=lambda b: b.contribution, reverse=True
        )
        for b in sorted_items:
            if b.contribution > 0:
                lines.append(b.format_line())
        return lines

    def __str__(self) -> str:
        return "\n".join(self.render_lines())

    def quality_tier_label(self) -> str:
        tier_labels = {"low": "Low Quality", "medium": "Medium Quality", "high": "High Quality"}
        return tier_labels.get(self.quality_tier, self.quality_tier)


@dataclass
class ScoredLead:
    """Wraps a UnifiedLead with its computed overall score and explanation.

    The original lead is kept intact — no mutation.
    """

    lead: UnifiedLead
    overall_score: int = 0  # 0-100
    explanation: ScoreExplanation = field(default_factory=ScoreExplanation)
    quality_tier: str = "low"

    @property
    def company_name(self) -> str:
        return self.lead.company_name or "Unknown"

    @property
    def website(self) -> str:
        return self.lead.website or ""