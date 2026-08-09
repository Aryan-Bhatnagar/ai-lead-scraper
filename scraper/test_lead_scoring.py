"""Unit tests for Phase 18C — Lead Scoring.

Covers WeightProvider, FeatureExtractor, ScoreCalculator, ScoringEngine,
LeadScoringService, and the engine integration hook.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from scraper.discovery.model import LocationData, Provenance, UnifiedLead
from scraper.scoring import (
    FeatureExtractor,
    LeadScoringService,
    ScoredLead,
    ScoreCalculator,
    ScoringEngine,
    WeightProvider,
)
from scraper.scoring.weight_provider import FeatureWeight


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_lead() -> UnifiedLead:
    return UnifiedLead(
        company_name="Empty",
        location=LocationData(),
        provenance=Provenance(source="", confidence=0.0),
    )


def _rich_lead() -> UnifiedLead:
    return UnifiedLead(
        company_name="Acme Corp",
        company_name_norm="acme corp",
        website="https://acme.com",
        description="A" * 150,
        industry="widgets",
        emails=["info@acme.com"],
        phones=["+1-555-1212"],
        location=LocationData(city="NYC", region="NY", country="USA"),
        provenance=Provenance(
            source="google,yellowpages,bing",
            discovered_at=datetime.now(timezone.utc),
            confidence=0.9,
        ),
        socials={"linkedin": "x", "twitter": "y", "facebook": "z", "instagram": "w", "github": "v"},
        jobs_completed=5,
        maps_review_count=10,
        rating=4.5,
        categories=["a"],
        skills=["b"],
    )


# ---------------------------------------------------------------------------
# WeightProvider
# ---------------------------------------------------------------------------

class TestWeightProvider:
    def test_loads_yaml_and_weights_sum_to_100(self):
        wp = WeightProvider()
        assert wp.weights, "no weights loaded"
        assert wp.total_max_weight() == pytest.approx(100.0)

    def test_thresholds_present(self):
        wp = WeightProvider()
        t = wp.thresholds
        assert t["low_quality"] < t["medium_quality"] < t["high_quality"]

    def test_quality_tier_boundaries(self):
        wp = WeightProvider()
        high = wp.thresholds["high_quality"]
        medium = wp.thresholds["medium_quality"]
        assert wp.quality_tier(high) == "high"
        assert wp.quality_tier(medium) == "medium"
        assert wp.quality_tier(medium - 1) == "low"

    def test_disabled_feature_excluded(self):
        wp = WeightProvider()
        wp.weights["phone_number"].enabled = False
        enabled = wp.enabled_features()
        assert "phone_number" not in enabled
        assert "website_exists" in enabled

    def test_defaults_when_no_yaml(self):
        wp = WeightProvider(config_path="nonexistent/path.yaml")
        assert wp.weights
        assert wp.total_max_weight() == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# FeatureExtractor
# ---------------------------------------------------------------------------

class TestFeatureExtractor:
    ex = FeatureExtractor()

    def test_empty_lead_all_zeros(self):
        ratios = self.ex.extract_all(_empty_lead())
        # recent_activity may be 0.0 when no discovered_at
        assert ratios["website_exists"] == 0.0
        assert ratios["business_email"] == 0.0
        assert ratios["phone_number"] == 0.0
        assert ratios["description_quality"] == 0.0
        assert all(0.0 <= r <= 1.0 for r in ratios.values())

    def test_rich_lead_high_ratios(self):
        ratios = self.ex.extract_all(_rich_lead())
        assert ratios["website_exists"] == 1.0
        assert ratios["business_email"] == 1.0
        assert ratios["phone_number"] == 1.0
        assert ratios["description_quality"] == 1.0
        assert ratios["location_quality"] == 1.0
        assert ratios["multiple_sources"] == 1.0
        assert ratios["social_profiles"] == 1.0
        assert ratios["recent_activity"] == 1.0

    def test_generic_email_not_business(self):
        lead = _empty_lead()
        lead.emails = ["bob@gmail.com"]
        assert self.ex.business_email(lead) == 0.0
        lead.emails = ["bob@acme.io"]
        assert self.ex.business_email(lead) == 1.0

    def test_description_quality_buckets(self):
        lead = _empty_lead()
        lead.description = ""
        assert self.ex.description_quality(lead) == 0.0
        lead.description = "short"
        assert self.ex.description_quality(lead) == 0.3
        lead.description = "x" * 50
        assert self.ex.description_quality(lead) == 0.7
        lead.description = "x" * 150
        assert self.ex.description_quality(lead) == 1.0

    def test_location_quality_buckets(self):
        lead = _empty_lead()
        assert self.ex.location_quality(lead) == 0.0
        lead.location = LocationData(country="US")
        assert self.ex.location_quality(lead) == 0.4
        lead.location = LocationData(city="NYC")
        assert self.ex.location_quality(lead) == 0.5
        lead.location = LocationData(city="NYC", country="US")
        assert self.ex.location_quality(lead) == 0.8
        lead.location = LocationData(city="NYC", region="NY", country="US")
        assert self.ex.location_quality(lead) == 1.0

    def test_multiple_sources_counting(self):
        lead = _empty_lead()
        lead.provenance = Provenance(source="a")
        assert self.ex.multiple_sources(lead) == 0.5
        lead.provenance = Provenance(source="a,b")
        assert self.ex.multiple_sources(lead) == 0.7
        lead.provenance = Provenance(source="a,b,c")
        assert self.ex.multiple_sources(lead) == 1.0

    def test_recent_activity_recency(self):
        lead = _empty_lead()
        lead.provenance = Provenance(source="x", discovered_at=None)
        assert self.ex.recent_activity(lead) == 0.0
        lead.provenance = Provenance(source="x", discovered_at=datetime.now(timezone.utc))
        assert self.ex.recent_activity(lead) == 1.0
        lead.provenance = Provenance(source="x", discovered_at=datetime.now(timezone.utc) - timedelta(days=60))
        assert self.ex.recent_activity(lead) == 0.5
        lead.provenance = Provenance(source="x", discovered_at=datetime.now(timezone.utc) - timedelta(days=200))
        assert self.ex.recent_activity(lead) == 0.2

    def test_naive_datetime_tolerated(self):
        lead = _empty_lead()
        lead.provenance = Provenance(source="x", discovered_at=datetime.now())  # naive
        assert self.ex.recent_activity(lead) == 1.0


# ---------------------------------------------------------------------------
# ScoreCalculator
# ---------------------------------------------------------------------------

class TestScoreCalculator:
    def test_perfect_ratios_score_100(self):
        wp = WeightProvider()
        calc = ScoreCalculator(wp)
        ratios = {name: 1.0 for name in wp.enabled_features()}
        score, breakdowns = calc.calculate(ratios)
        assert score == 100
        assert len(breakdowns) == len(wp.enabled_features())
        assert sum(b.contribution for b in breakdowns) == pytest.approx(100.0)

    def test_zero_ratios_score_0(self):
        wp = WeightProvider()
        calc = ScoreCalculator(wp)
        score, _ = calc.calculate({})
        assert score == 0

    def test_breakdown_fields(self):
        wp = WeightProvider()
        calc = ScoreCalculator(wp)
        score, breakdowns = calc.calculate({"website_exists": 1.0})
        for b in breakdowns:
            assert 0.0 <= b.quality_ratio <= 1.0
            assert 0.0 <= b.contribution <= b.weight
            assert b.feature
            assert b.label
            assert b.detail

    def test_clamps_and_rounds(self):
        wp = WeightProvider()
        calc = ScoreCalculator(wp)
        score, _ = calc.calculate({"website_exists": 1.0})
        assert score == 25  # yaml weight for website_exists


# ---------------------------------------------------------------------------
# ScoringEngine / LeadScoringService
# ---------------------------------------------------------------------------

class TestScoringEngine:
    def test_score_leads_returns_wrapped(self):
        engine = ScoringEngine()
        scored = engine.score_leads([_empty_lead(), _rich_lead()])
        assert len(scored) == 2
        assert all(isinstance(s, ScoredLead) for s in scored)
        assert all(0 <= s.overall_score <= 100 for s in scored)
        assert scored[1].overall_score > scored[0].overall_score

    def test_scores_deterministic(self):
        engine = ScoringEngine()
        a = engine.score_lead(_rich_lead()).overall_score
        b = engine.score_lead(_rich_lead()).overall_score
        assert a == b

    def test_explanation_structure(self):
        engine = ScoringEngine()
        sc = engine.score_lead(_rich_lead())
        exp = sc.explanation
        assert exp.overall_score == sc.overall_score
        assert exp.quality_tier == sc.quality_tier
        assert exp.breakdowns
        rendered = exp.render_lines()
        assert rendered[0].startswith("Overall Score:")
        assert any(line.startswith("+") for line in rendered[2:])

    def test_service_facade(self):
        svc = LeadScoringService()
        sc = svc.score_one(_rich_lead())
        assert sc.quality_tier == "high"
        exp = svc.explain(_rich_lead())
        assert exp.overall_score == sc.overall_score
        weights = svc.get_weights()
        assert isinstance(weights, WeightProvider)

    def test_empty_lead_scores_zero(self):
        svc = LeadScoringService()
        sc = svc.score_one(_empty_lead())
        assert sc.overall_score == 0
        assert sc.quality_tier == "low"


# ---------------------------------------------------------------------------
# Engine integration
# ---------------------------------------------------------------------------

class TestEngineIntegration:
    def test_engine_has_scoring_step(self):
        import inspect
        from scraper.discovery.engine import LeadDiscoveryEngine

        src = inspect.getsource(LeadDiscoveryEngine.run)
        assert "LeadScoringService" in src
        assert "score" in src and "scored_leads" in src

    def test_run_exposes_scored_leads(self):
        from scraper.discovery.engine import LeadDiscoveryEngine
        from scraper.discovery.provider import DiscoveryProvider
        from scraper.discovery.query import DiscoveryBatch, DiscoveryQuery
        from scraper.discovery.registry import ProviderRegistry

        class _Stub(DiscoveryProvider):
            name = "google_search"  # registered normalizer
            def discover(self, query):
                return DiscoveryBatch(candidates=[])

        # Use an isolated registry so we don't clobber the module-level
        # default_registry shared by other tests.
        registry = ProviderRegistry()
        registry.register(_Stub())
        engine = LeadDiscoveryEngine(registry=registry, max_workers=2)
        summary = engine.run(DiscoveryQuery(industry="x", location="y"), sources=["google_search"])
        assert hasattr(summary, "scored_leads")
        assert isinstance(summary.scored_leads, list)
