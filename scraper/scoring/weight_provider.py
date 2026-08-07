"""Loads and provides feature weights from YAML configuration.

Reads ``config/lead_scoring.yaml`` once and exposes weights as a typed dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class FeatureWeight:
    """Configured weight for a single scoring feature."""

    feature: str
    weight: float
    description: str
    enabled: bool
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, feature_name: str, raw: Dict[str, Any]) -> "FeatureWeight":
        extra = dict(raw)
        weight = extra.pop("weight", 0)
        description = extra.pop("description", feature_name)
        enabled = extra.pop("enabled", True)
        return cls(
            feature=feature_name,
            weight=float(weight),
            description=str(description),
            enabled=bool(enabled),
            extra=extra,
        )


@dataclass
class WeightProvider:
    """Reads ``config/lead_scoring.yaml`` and provides validated weights."""

    config_path: Path | None = None
    weights: Dict[str, FeatureWeight] = field(default_factory=dict)
    thresholds: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.config_path is None:
            # Walk up from this file to find config/
            candidates = [
                Path.cwd() / "config" / "lead_scoring.yaml",
                Path(__file__).resolve().parent.parent.parent / "config" / "lead_scoring.yaml",
            ]
            for p in candidates:
                if p.exists():
                    self.config_path = p
                    break
        if self.config_path is not None and Path(self.config_path).exists():
            self._load()
        if not self.weights:
            self._use_defaults()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        with open(self.config_path, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}

        raw_features: Dict[str, Any] = cfg.get("features", {})
        for feat_name, raw in raw_features.items():
            self.weights[feat_name] = FeatureWeight.from_dict(feat_name, raw)

        raw_thresholds: Dict[str, Any] = cfg.get("thresholds", {})
        self.thresholds = {
            "excellent": int(raw_thresholds.get("excellent", 90)),
            "good": int(raw_thresholds.get("good", 75)),
            "average": int(raw_thresholds.get("average", 50)),
            "poor": int(raw_thresholds.get("poor", 0)),
        }

    def _use_defaults(self) -> None:
        """Hard‑coded defaults matching the Phase 18C spec when no YAML exists."""
        defaults: Dict[str, FeatureWeight] = {
            "website_exists": FeatureWeight(
                feature="website_exists", weight=25.0, description="Website", enabled=True,
            ),
            "business_email": FeatureWeight(
                feature="business_email", weight=20.0, description="Business Email", enabled=True,
            ),
            "phone_number": FeatureWeight(
                feature="phone_number", weight=15.0, description="Phone", enabled=True,
            ),
            "description_quality": FeatureWeight(
                feature="description_quality", weight=9.0, description="Description", enabled=True,
            ),
            "location_quality": FeatureWeight(
                feature="location_quality", weight=8.0, description="Location", enabled=True,
            ),
            "multiple_sources": FeatureWeight(
                feature="multiple_sources", weight=10.0, description="Multiple Sources", enabled=True,
                extra={"bonus_per_extra_source": 5},
            ),
            "social_profiles": FeatureWeight(
                feature="social_profiles", weight=3.0, description="Social Profiles", enabled=True,
                extra={"score_per_profile": 1},
            ),
            "company_size_hints": FeatureWeight(
                feature="company_size_hints", weight=3.0, description="Company Size", enabled=True,
            ),
            "recent_activity": FeatureWeight(
                feature="recent_activity", weight=2.0, description="Recent Activity", enabled=True,
            ),
            "provider_confidence": FeatureWeight(
                feature="provider_confidence", weight=2.0, description="Provider Confidence", enabled=True,
            ),
            "ai_enrichment_confidence": FeatureWeight(
                feature="ai_enrichment_confidence", weight=3.0, description="AI Enrichment", enabled=True,
            ),
        }
        self.weights = defaults
        self.thresholds = {"excellent": 90, "good": 75, "average": 50, "poor": 0}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get(self, feature_name: str) -> FeatureWeight | None:
        return self.weights.get(feature_name)

    def enabled_features(self) -> Dict[str, FeatureWeight]:
        """Return only features that are enabled."""
        return {k: v for k, v in self.weights.items() if v.enabled}

    def total_max_weight(self) -> float:
        """Sum of all enabled feature weights."""
        return sum(fw.weight for fw in self.enabled_features().values())

    def quality_tier(self, score: float) -> str:
        """Classify a 0‑100 score into 'excellent', 'good', 'average', or 'poor'."""
        if score >= self.thresholds.get("excellent", 90):
            return "excellent"
        if score >= self.thresholds.get("good", 75):
            return "good"
        if score >= self.thresholds.get("average", 50):
            return "average"
        return "poor"


def default_weight_provider() -> WeightProvider:
    return WeightProvider()