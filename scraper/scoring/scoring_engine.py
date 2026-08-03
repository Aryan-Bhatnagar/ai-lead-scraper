"""ScoringEngine — orchestrates feature extraction and score computation.

Given a list of UnifiedLead objects, produces ScoredLead wrappers.
"""

from __future__ import annotations

from typing import List

from scraper.discovery.model import UnifiedLead

from .feature_extractor import FeatureExtractor
from .models import ScoredLead, ScoreExplanation
from .score_calculator import ScoreCalculator
from .weight_provider import WeightProvider, default_weight_provider


class ScoringEngine:
    """High-level service that scores a batch of UnifiedLead objects.

    This is the main integration point for the discovery pipeline —
    after deduplication, before returning DiscoveryRunSummary.
    """

    def __init__(self, weight_provider: WeightProvider | None = None) -> None:
        self.wp = weight_provider or default_weight_provider()
        self.extractor = FeatureExtractor()
        self.calculator = ScoreCalculator(self.wp)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def score_leads(self, leads: List[UnifiedLead]) -> List[ScoredLead]:
        """Score every lead and return ScoredLead wrappers.

        Parameters
        ----------
        leads:
            Deduplicated UnifiedLead objects ready for scoring.

        Returns
        -------
        list[ScoredLead]
            Each with ``overall_score`` (0-100) and ``explanation``.
        """
        scored: List[ScoredLead] = []

        for lead in leads:
            # Extract quality ratios for every feature
            ratios = self.extractor.extract_all(lead)

            # Compute overall score + per-feature breakdown
            overall, breakdowns = self.calculator.calculate(ratios)

            # Determine quality tier
            tier = self.wp.quality_tier(overall)

            # Build the explanation object
            explanation = ScoreExplanation(
                overall_score=overall,
                breakdowns=breakdowns,
                quality_tier=tier,
            )

            scored.append(
                ScoredLead(
                    lead=lead,
                    overall_score=overall,
                    explanation=explanation,
                    quality_tier=tier,
                )
            )

        return scored

    def score_lead(self, lead: UnifiedLead) -> ScoredLead:
        """Score a single lead — convenience wrapper."""
        return self.score_leads([lead])[0]
