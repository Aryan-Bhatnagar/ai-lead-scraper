"""LeadScoringService — entry point for the scoring layer.

This is the class the discovery engine calls.  It wraps ScoringEngine
and adds service-level concerns (caching, batching, configuration).
"""

from __future__ import annotations

from typing import List, Optional

from scraper.discovery.model import UnifiedLead

from .models import ScoredLead, ScoreExplanation
from .scoring_engine import ScoringEngine
from .weight_provider import WeightProvider, default_weight_provider


class LeadScoringService:
    """Public service facade used by the discovery engine.

    Usage in pipeline::

        scoring_service = LeadScoringService()
        scored_leads = scoring_service.score(deduped_leads)

    Parameters
    ----------
    weight_provider : optional
        A pre-configured WeightProvider; if None, a fresh one is created
        from ``config/lead_scoring.yaml``.
    """

    def __init__(self, weight_provider: Optional[WeightProvider] = None) -> None:
        self._wp = weight_provider or default_weight_provider()
        self._engine = ScoringEngine(weight_provider=self._wp)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def score(self, leads: List[UnifiedLead]) -> List[ScoredLead]:
        """Score a list of deduplicated leads.

        Parameters
        ----------
        leads:
            The deduplicated output from the dedup stage.

        Returns
        -------
        list[ScoredLead]
            Scored leads with ``overall_score``, ``breakdowns``, and
            ``quality_tier``.
        """
        return self._engine.score_leads(leads)

    def score_one(self, lead: UnifiedLead) -> ScoredLead:
        """Score a single lead."""
        return self._engine.score_lead(lead)

    def explain(self, lead: UnifiedLead) -> ScoreExplanation:
        """Return only the ScoreExplanation for a lead (no wrapper)."""
        scored = self.score_one(lead)
        return scored.explanation

    def get_weights(self) -> WeightProvider:
        """Expose the underlying weight provider for inspection/testing."""
        return self._wp
