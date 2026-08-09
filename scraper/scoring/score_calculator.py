"""ScoreCalculator — computes overall score for a single UnifiedLead.

Given extracted quality ratios and configured weights, produces a
ScoreExplanation with a full breakdown.
"""

from __future__ import annotations

from .models import ScoreBreakdown, ScoreExplanation
from .weight_provider import WeightProvider


class ScoreCalculator:
    """Computes the 0‑100 score for one lead.

    Parameters
    ----------
    weight_provider:
        Source of feature weights and thresholds.
    """

    def __init__(self, weight_provider: WeightProvider) -> None:
        self.wp = weight_provider

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def calculate(
        self,
        quality_ratios: dict[str, float],
        *,
        clamp_min: float = 0.0,
        clamp_max: float = 100.0,
    ) -> tuple[int, list[ScoreBreakdown]]:
        """Compute overall_score and per‑feature breakdown.

        Parameters
        ----------
        quality_ratios:
            Mapping ``feature_name → quality_ratio`` (0.0‑1.0) as produced by
            FeatureExtractor.
        clamp_min / clamp_max:
            Hard bounds for the final score.

        Returns
        -------
        (overall_score: int, breakdowns: list[ScoreBreakdown])
        """
        breakdowns: list[ScoreBreakdown] = []
        raw_score = 0.0

        for feat_name, fw in self.wp.enabled_features().items():
            ratio = quality_ratios.get(feat_name, 0.0)
            contrib = fw.weight * ratio
            raw_score += contrib

            breakdowns.append(ScoreBreakdown(
                feature=feat_name,
                label=fw.description,
                weight=fw.weight,
                quality_ratio=ratio,
                contribution=contrib,
                detail=self._detail_for(feat_name, ratio, fw.weight, contrib),
            ))

        overall = max(clamp_min, min(clamp_max, raw_score))
        return int(round(overall)), breakdowns

    def calculate_explanation(
        self,
        quality_ratios: dict[str, float],
    ) -> ScoreExplanation:
        """Convenience: compute score AND return a ScoreExplanation."""
        overall, breakdowns = self.calculate(quality_ratios)
        tier = self.wp.quality_tier(overall)
        return ScoreExplanation(
            overall_score=overall,
            breakdowns=breakdowns,
            quality_tier=tier,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _detail_for(
        feat_name: str,
        ratio: float,
        weight: float,
        contrib: float,
    ) -> str:
        """Return a short human‑readable justification."""
        label = feat_name.replace("_", " ").title()
        pct = int(round(ratio * 100))
        return f"{label}: {pct}% quality × {weight} weight = {contrib:.1f}"