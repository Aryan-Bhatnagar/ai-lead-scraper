"""Lead Scoring — Phase 18C.

Scores every UnifiedLead from 0–100 using configurable weighted features.
"""

from .models import ScoredLead, ScoreExplanation, ScoreBreakdown
from .weight_provider import WeightProvider
from .feature_extractor import FeatureExtractor
from .score_calculator import ScoreCalculator
from .scoring_engine import ScoringEngine
from .scoring_service import LeadScoringService

__all__ = [
    "ScoredLead",
    "ScoreExplanation",
    "ScoreBreakdown",
    "WeightProvider",
    "FeatureExtractor",
    "ScoreCalculator",
    "ScoringEngine",
    "LeadScoringService",
]