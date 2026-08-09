"""Unit tests for Phase 19A — Discovery Orchestrator."""

from __future__ import annotations

from unittest.mock import patch
from datetime import datetime, UTC

import pytest

from scraper.discovery.model import UnifiedLead
from scraper.discovery.provider import CapabilitySet, DiscoveryProvider
from scraper.discovery.query import DiscoveryBatch, DiscoveryQuery, RawCandidate
from scraper.discovery.registry import ProviderRegistry
from scraper.discovery.orchestrator import (
    DEFAULT_PROVIDER_ORDER,
    DiscoveryOrchestrator,
)
from scraper.discovery.engine import DiscoveryRunSummary
from scraper.discovery.normalizers.base import BaseNormalizer
from scraper.discovery.normalizers.registry import default_registry as norm_registry


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _query() -> DiscoveryQuery:
    return DiscoveryQuery(industry="DevOps", location="USA", keywords=[], max_results=10)


class _SuccessProvider(DiscoveryProvider):
    """Provider returning N candidates."""

    name = "ok_provider"
    source_type = "api"
    capabilities = CapabilitySet()

    def __init__(self, n_candidates: int = 2):
        self.calls = 0
        self._n = n_candidates

    def discover(self, query: DiscoveryQuery) -> DiscoveryBatch:
        self.calls += 1
        # Distinct, non-similar names/domains so the Phase 18B deduper does
        # not merge the synthetic candidates back together.
        distinct = [
            ("Alpha Widgets LLC", "https://alpha-widgets.example.com"),
            ("Zephyr Logistics", "https://zephyr-logistics.example.org"),
            ("Quorn Bakery Co", "https://quorn-bakery.example.net"),
        ]
        return DiscoveryBatch(
            source=self.name,
            candidates=[
                RawCandidate(
                    payload={"title": name, "url": url,
                             "snippet": "S", "source_engine": "t", "query": "q",
                             "timestamp": datetime.now(UTC).isoformat()},
                    source=self.name,
                )
                for (name, url) in distinct[: self._n]
            ],
        )


class _FlakyThenOkProvider(DiscoveryProvider):
    """Fails ``fail_times`` then succeeds."""

    name = "flaky_provider"

    def __init__(self, fail_times: int):
        self.calls = 0
        self._fail_times = fail_times

    def discover(self, query: DiscoveryQuery) -> DiscoveryBatch:
        self.calls += 1
        if self.calls <= self._fail_times:
            raise RuntimeError(f"boom #{self.calls}")
        return DiscoveryBatch(source=self.name, candidates=[])


class _AlwaysFailsProvider(DiscoveryProvider):
    name = "fail_provider"

    def __init__(self):
        self.calls = 0

    def discover(self, query: DiscoveryQuery) -> DiscoveryBatch:
        self.calls += 1
        raise RuntimeError("always fails")


class _GenericNormalizer(BaseNormalizer):
    """Very small normalizer that accepts any payload."""

    def normalize(self, candidate, query):
        return UnifiedLead(
            company_name=candidate.payload.get("title", "?"),
            website=candidate.payload.get("url"),
        )


def _registry_with(*providers) -> ProviderRegistry:
    reg = ProviderRegistry()
    for p in providers:
        reg.register(p)
    return reg


@pytest.fixture(autouse=True)
def _register_generic_normalizers():
    """Register permissive normalizers for the stub provider names used below.

    Normalizer registry is module-level, so we clean up after each test.
    """
    names = ["ok_provider", "flaky_provider", "fail_provider"]
    originals = {n: norm_registry.get(n) for n in names}
    for n in names:
        norm_registry.register(n, _GenericNormalizer())
    yield
    for n in names:
        if originals[n] is None:
            # best-effort cleanup
            try:
                norm_registry._normalizers.pop(n, None)
            except AttributeError:
                pass
        else:
            norm_registry.register(n, originals[n])


# ---------------------------------------------------------------------------
# Orchestrator basics
# ---------------------------------------------------------------------------

class TestOrchestratorBasics:
    def test_exports(self):
        from scraper.discovery import DiscoveryOrchestrator as O  # noqa: F401
        assert "google_search" in DEFAULT_PROVIDER_ORDER
        assert "upwork" in DEFAULT_PROVIDER_ORDER
        assert "google_maps" in DEFAULT_PROVIDER_ORDER
        assert "website_discovery" in DEFAULT_PROVIDER_ORDER

    def test_default_providers_registered(self):
        from scraper.discovery.registry import default_registry
        for name in ("google_search", "website_discovery", "google_maps", "upwork"):
            assert name in default_registry.list()

    def test_enabled_providers_respect_config(self):
        reg = _registry_with(_SuccessProvider(), _FlakyThenOkProvider(0))
        orch = DiscoveryOrchestrator(
            registry=reg,
            provider_order=["flaky_provider", "ok_provider"],
            provider_enabled={"flaky_provider": False},
        )
        assert orch.enabled_providers() == ["ok_provider"]

    def test_missing_registry_names_skipped(self):
        reg = _registry_with(_SuccessProvider())
        orch = DiscoveryOrchestrator(
            registry=reg, provider_order=["nope", "ok_provider"],
        )
        assert orch.enabled_providers() == ["ok_provider"]


# ---------------------------------------------------------------------------
# Execution order / enable-disable
# ---------------------------------------------------------------------------

class TestOrderAndToggle:
    def test_execution_order(self):
        order: list[str] = []

        class _Tap(DiscoveryProvider):
            def __init__(self, name):
                self.name = name
            def discover(self, query):
                order.append(self.name)
                return DiscoveryBatch(source=self.name, candidates=[])

        reg = _registry_with(_Tap("c"), _Tap("a"), _Tap("b"))
        orch = DiscoveryOrchestrator(
            registry=reg,
            provider_order=["b", "c", "a"],
            max_retries=1,  # force sequential path so order is observable
            retry_backoff=0.0,
        )
        orch.run(_query())
        assert order == ["b", "c", "a"]

    def test_enable_disable_flag(self):
        seen: list[str] = []

        class _Tap(DiscoveryProvider):
            def __init__(self, name):
                self.name = name
            def discover(self, query):
                seen.append(self.name)
                return DiscoveryBatch(source=self.name, candidates=[])

        reg = _registry_with(_Tap("keep"), _Tap("skip"))
        orch = DiscoveryOrchestrator(
            registry=reg,
            provider_order=["keep", "skip"],
            provider_enabled={"skip": False},
            max_retries=1,
            retry_backoff=0.0,
        )
        summary = orch.run(_query())
        assert seen == ["keep"]
        assert "keep" in summary.per_source
        assert "skip" not in summary.per_source

    def test_runtime_toggle(self):
        orch = DiscoveryOrchestrator(registry=_registry_with(_SuccessProvider()),
                                     provider_order=["ok_provider"])
        orch.set_provider_enabled("ok_provider", False)
        assert orch.enabled_providers() == []
        orch.set_provider_enabled("ok_provider", True)
        assert orch.enabled_providers() == ["ok_provider"]

    def test_sources_override_order(self):
        order: list[str] = []

        class _Tap(DiscoveryProvider):
            def __init__(self, name):
                self.name = name
            def discover(self, query):
                order.append(self.name)
                return DiscoveryBatch(source=self.name, candidates=[])

        reg = _registry_with(_Tap("x"), _Tap("y"), _Tap("z"))
        orch = DiscoveryOrchestrator(
            registry=reg, provider_order=["z", "y", "x"],
            max_retries=1, retry_backoff=0.0,
        )
        orch.run(_query(), sources=["x", "z"])
        assert order == ["x", "z"]


# ---------------------------------------------------------------------------
# Retries
# ---------------------------------------------------------------------------

class TestRetries:
    def test_retry_until_success(self):
        flaky = _FlakyThenOkProvider(fail_times=2)
        reg = _registry_with(flaky)
        orch = DiscoveryOrchestrator(
            registry=reg,
            provider_order=["flaky_provider"],
            max_retries=3,
            retry_backoff=0.0,
        )
        summary = orch.run(_query())
        assert flaky.calls == 3
        assert "flaky_provider" in summary.per_source
        assert summary.per_source["flaky_provider"].error is None

    def test_retry_exhaustion_yields_failed_source(self):
        always = _AlwaysFailsProvider()
        reg = _registry_with(always)
        orch = DiscoveryOrchestrator(
            registry=reg,
            provider_order=["fail_provider"],
            max_retries=2,
            retry_backoff=0.0,
        )
        summary = orch.run(_query())
        assert always.calls == 3  # 1 initial + 2 retries
        src = summary.per_source["fail_provider"]
        assert src.error is not None
        assert "always fails" in src.error

    def test_no_retry_when_disabled(self):
        always = _AlwaysFailsProvider()
        reg = _registry_with(always)
        orch = DiscoveryOrchestrator(
            registry=reg,
            provider_order=["fail_provider"],
            max_retries=0,  # fast path — engine handles exceptions itself
        )
        summary = orch.run(_query())
        assert always.calls == 1
        assert summary.per_source["fail_provider"].error is not None


# ---------------------------------------------------------------------------
# Aggregation / pipeline output
# ---------------------------------------------------------------------------

class TestAggregation:
    def test_full_pipeline_produces_scored_leads(self):
        reg = _registry_with(_SuccessProvider(n_candidates=2))
        orch = DiscoveryOrchestrator(
            registry=reg,
            provider_order=["ok_provider"],
            max_retries=0,  # engine fast path
        )
        summary = orch.run(_query())
        assert isinstance(summary, DiscoveryRunSummary)
        assert summary.total_found == 2
        assert len(summary.leads) == 2
        assert len(summary.scored_leads) == 2
        assert all(0 <= s.overall_score <= 100 for s in summary.scored_leads)

    def test_aggregation_with_retry_path(self):
        reg = _registry_with(_SuccessProvider(n_candidates=3))
        orch = DiscoveryOrchestrator(
            registry=reg,
            provider_order=["ok_provider"],
            max_retries=2,
            retry_backoff=0.0,
        )
        summary = orch.run(_query())
        assert summary.total_found == 3
        assert len(summary.scored_leads) == 3
        assert summary.per_source["ok_provider"].found == 3

    def test_empty_registry_returns_empty_summary(self):
        orch = DiscoveryOrchestrator(registry=_registry_with(), provider_order=[])
        summary = orch.run(_query())
        assert summary.total_found == 0
        assert summary.per_source == {}
        assert summary.scored_leads == []

    def test_mixed_success_and_failure_aggregates(self):
        reg = _registry_with(_SuccessProvider(n_candidates=1), _AlwaysFailsProvider())
        orch = DiscoveryOrchestrator(
            registry=reg,
            provider_order=["ok_provider", "fail_provider"],
            max_retries=1,
            retry_backoff=0.0,
        )
        summary = orch.run(_query())
        assert summary.per_source["ok_provider"].found == 1
        assert summary.per_source["fail_provider"].error is not None
        assert summary.total_found == 1


# ---------------------------------------------------------------------------
# Google Maps provider adapter
# ---------------------------------------------------------------------------

class TestGoogleMapsProvider:
    def test_adapter_wraps_legacy_function(self):
        from scraper.discovery.providers.google_maps_provider import (
            GoogleMapsDiscoveryProvider,
        )
        provider = GoogleMapsDiscoveryProvider()
        assert provider.name == "google_maps"
        assert provider.requires_api_key is True

        fake_rows = [
            {"company_name": "Acme", "address": "1 Main St", "phone": None,
             "website": None, "rating": 4.2, "reviews_count": 15,
             "place_id": "pid", "google_maps_url": "https://maps/x",
             "source": "google_maps"},
        ]
        with patch(
            "scraper.google_maps_discovery.discover_google_maps",
            return_value=fake_rows,
        ) as mock_fn:
            batch = provider.discover(_query())
        mock_fn.assert_called_once_with(industry="DevOps", location="USA", max_results=10)
        assert len(batch.candidates) == 1
        assert batch.candidates[0].source == "google_maps"
        assert batch.candidates[0].payload["company_name"] == "Acme"

    def test_normalizer_maps_payload_to_unified_lead(self):
        from scraper.discovery.normalizers.google_maps import GoogleMapsNormalizer
        from scraper.discovery.query import RawCandidate

        payload = {
            "company_name": "Acme Corp",
            "address": "123 Main St",
            "phone": "+1-555",
            "website": "https://acme.com",
            "rating": 4.5,
            "reviews_count": 99,
            "place_id": "PID123",
            "google_maps_url": "https://maps/pid",
        }
        lead = GoogleMapsNormalizer().normalize(
            RawCandidate(payload=payload, source="google_maps"), _query()
        )
        assert lead.company_name == "Acme Corp"
        assert lead.website == "https://acme.com"
        assert lead.location.address == "123 Main St"
        assert lead.phones == ["+1-555"]
        assert lead.maps_rating == 4.5
        assert lead.maps_review_count == 99
        assert lead.external_ids["google_places_id"] == "PID123"
        assert lead.provenance.source == "google_maps"

    def test_google_maps_end_to_end_through_orchestrator(self):
        from scraper.discovery.providers.google_maps_provider import (
            GoogleMapsDiscoveryProvider,
        )

        reg = _registry_with(GoogleMapsDiscoveryProvider())
        fake_rows = [
            {"company_name": "Acme", "address": "1 Main St", "phone": None,
             "website": None, "rating": 4.2, "reviews_count": 15,
             "place_id": "pid", "google_maps_url": "https://maps/x",
             "source": "google_maps"},
        ]
        with patch(
            "scraper.google_maps_discovery.discover_google_maps",
            return_value=fake_rows,
        ):
            orch = DiscoveryOrchestrator(
                registry=reg, provider_order=["google_maps"], max_retries=0,
            )
            summary = orch.run(_query())
        assert summary.per_source["google_maps"].found == 1
        assert summary.total_new == 1
        assert len(summary.scored_leads) == 1
        assert summary.scored_leads[0].lead.company_name == "Acme"
        assert 0 <= summary.scored_leads[0].overall_score <= 100
