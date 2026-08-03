"""Phase 19A — Discovery Orchestrator.

Orchestrates execution of multiple DiscoveryProviders with:

* provider execution (retries with exponential backoff)
* per-provider enable/disable
* execution-order control
* aggregation into ``DiscoveryRunSummary``
* optional persistence of results via a :class:`LeadRepository`

The orchestrator has no knowledge of provider internals — it interacts
with providers only through the :class:`DiscoveryProvider` interface
(``provider.name`` + ``provider.discover(query)``).

Pipeline:  Discovery → Normalization → Deduplication → Lead Scoring
(implemented by delegating aggregation to ``LeadDiscoveryEngine``).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from .engine import DiscoveryRunSummary, LeadDiscoveryEngine
from .provider import DiscoveryProvider
from .query import DiscoveryBatch, DiscoveryQuery, SourceMeta
from .registry import ProviderRegistry, default_registry

logger = logging.getLogger(__name__)

# Ordered list of built-in providers (highest priority first).
# This is the default execution order when the user does not supply one.
DEFAULT_PROVIDER_ORDER: List[str] = [
    "google_search",
    "website_discovery",
    "google_maps",
    "upwork",
]


class DiscoveryOrchestrator:
    """Coordinate multiple DiscoveryProviders through the standard interface.

    Parameters
    ----------
    registry:
        Provider registry to draw providers from (defaults to the module-level
        ``default_registry``).
    provider_order:
        Names in the order they must execute.  Registered providers missing
        from this list are appended at the end (in registration order).
    provider_enabled:
        Mapping ``provider_name → bool``.  When ``False``, the provider is
        skipped without error.
    max_retries:
        Maximum number of retry attempts per provider (0 → no retries).
    retry_backoff:
        Multiplier for the exponential backoff between retries (seconds).
    max_workers:
        Thread-pool size forwarded to the underlying aggregation engine.
    engine:
        Optional pre-configured :class:`LeadDiscoveryEngine`; a new one is
        created from ``registry``/``max_workers`` when omitted.
    repository:
        Optional :class:`LeadRepository` for persisting discovered leads.
        If provided, the orchestrator will call ``persist_results`` after
        a successful run to store the scored leads.
    """

    def __init__(
        self,
        registry: ProviderRegistry = default_registry,
        provider_order: Optional[List[str]] = None,
        provider_enabled: Optional[Dict[str, bool]] = None,
        max_retries: int = 1,
        retry_backoff: float = 0.5,
        max_workers: int = 8,
        engine: Optional[LeadDiscoveryEngine] = None,
        repository: Optional[object] = None,  # We'll accept any object that has persist_orchestrator_summary or bulk_insert
    ) -> None:
        self.registry = registry
        self.provider_order: List[str] = (
            list(provider_order) if provider_order is not None else list(DEFAULT_PROVIDER_ORDER)
        )
        self.provider_enabled: Dict[str, bool] = dict(provider_enabled or {})
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.max_workers = max_workers
        self.engine = engine or LeadDiscoveryEngine(
            registry=registry, max_workers=max_workers
        )
        self.repository = repository

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(
        self,
        query: DiscoveryQuery,
        sources: Optional[List[str]] = None,
    ) -> DiscoveryRunSummary:
        """Execute the full discovery pipeline and return the aggregated summary.

        Flow:

        1. Resolve the active provider list (order, enable/disable, sources).
        2. Optionally pre-execute providers with retries, collecting batches.
        3. Delegate aggregation to the engine (normalization → dedup → scoring).
        4. Optionally persist results via the configured repository.

        Parameters
        ----------
        query:
            The single DiscoveryQuery every provider receives.
        sources:
            Optional explicit provider-name list restricting this run.
            Overrides ``provider_order``/``provider_enabled`` ordering.

        Returns
        -------
        DiscoveryRunSummary
            Aggregated counts, per-source breakdown, merged leads and scored
            leads.
        """
        active = self._resolve_active_providers(sources)
        if not active:
            return DiscoveryRunSummary()

        # Fast path — no retries configured: let the engine handle everything
        # (it already fans out providers concurrently and aggregates).
        if self.max_retries <= 0:
            summary = self.engine.run(query, sources=active)
        else:
            # Retry path — execute providers here so transient failures can be
            # retried, then feed the collected batches to the engine for the
            # normalization → dedupe → scoring aggregation.
            batches = self._execute_with_retries(active, query)
            summary = self._aggregate(query, batches, active)

        # Persist results if a repository is configured
        if self.repository is not None:
            self.persist_results(summary)

        return summary

    def persist_results(self, summary: DiscoveryRunSummary) -> None:
        """Persist the scored leads from a discovery run.

        This method is called by the orchestrator after a successful run when a
        repository is provided. It expects the summary to have a ``scored_leads``
        attribute (list of ScoredLead).

        Parameters
        ----------
        summary:
            The result of a discovery run.
        """
        if hasattr(summary, 'scored_leads'):
            leads = getattr(summary, 'scored_leads', [])
            if leads:
                # The repository's bulk_insert expects an iterable of UnifiedLead or ScoredLead.
                # We have ScoredLead objects, so we can pass them directly.
                self.repository.bulk_insert(leads)

    def set_provider_enabled(self, name: str, enabled: bool) -> None:
        """Enable or disable a provider by name."""
        self.provider_enabled[name] = enabled

    def enabled_providers(self) -> List[str]:
        """Return the names of providers that will run, in execution order."""
        return self._resolve_active_providers(None)

    # ------------------------------------------------------------------
    # Provider resolution
    # ------------------------------------------------------------------
    def _resolve_active_providers(
        self, sources: Optional[List[str]]
    ) -> List[str]:
        """Return ordered, enabled provider names for this run.

        Resolution rules:
        * ``sources`` (explicit request) always wins as the candidate set.
        * Otherwise the candidate set is every provider in ``provider_order``
          followed by any registered providers not already listed.
        * Providers absent from the registry are silently skipped.
        * Providers disabled via ``provider_enabled`` are skipped.
        """
        if sources is not None:
            candidates = list(sources)
        else:
            candidates = list(self.provider_order)
            for name in self.registry.list():
                if name not in candidates:
                    candidates.append(name)

        active: List[str] = []
        for name in candidates:
            if self.registry.get(name) is None:
                continue
            if not self.provider_enabled.get(name, True):
                logger.debug("Provider '%s' disabled — skipping", name)
                continue
            active.append(name)
        return active

    # ------------------------------------------------------------------
    # Execution with retries
    # ------------------------------------------------------------------
    def _execute_with_retries(
        self, names: List[str], query: DiscoveryQuery
    ) -> Dict[str, DiscoveryBatch]:
        """Run each provider sequentially in the configured order.

        For every provider, up to ``max_retries`` attempts are made.  A failed
        attempt is retried with exponential backoff; a permanently failing
        provider yields an empty DiscoveryBatch so aggregation can continue.
        """
        batches: Dict[str, DiscoveryBatch] = {}
        attempt_details: Dict[str, Dict[str, Any]] = {}
        for name in names:
            provider = self.registry.get(name)
            batch, attempts, last_err = self._run_provider_with_retry(provider, query)
            batches[name] = batch
            attempt_details[name] = {
                "attempts": attempts,
                "error": str(last_err) if last_err is not None else None,
            }
        self._last_attempts = attempt_details
        return batches

    def _run_provider_with_retry(
        self, provider: DiscoveryProvider, query: DiscoveryQuery
    ):
        """Call ``provider.discover`` with retry + exponential backoff.

        Returns
        -------
        (DiscoveryBatch, attempts, last_error)
        """
        attempts = 0
        last_err: Optional[BaseException] = None
        for attempt in range(self.max_retries + 1):
            attempts = attempt + 1
            try:
                batch = provider.discover(query)
                return batch, attempts, None
            except Exception as exc:  # noqa: BLE001 — isolate provider failures
                last_err = exc
                logger.warning(
                    "Provider '%s' attempt %d/%d failed: %s",
                    provider.name,
                    attempts,
                    self.max_retries + 1,
                    exc,
                )
                if attempt < self.max_retries:
                    sleep_s = self.retry_backoff * (2 ** attempt)
                    time.sleep(sleep_s)

        logger.error(
            "Provider '%s' permanently failed after %d attempts: %s",
            provider.name,
            attempts,
            last_err,
        )
        empty = DiscoveryBatch(
            source=provider.name,
            candidates=[],
            meta=SourceMeta(source=provider.name, request_count=0),
        )
        return empty, attempts, last_err

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------
    def _aggregate(
        self,
        query: DiscoveryQuery,
        batches: Dict[str, DiscoveryBatch],
        active: List[str],
    ) -> DiscoveryRunSummary:
        """Hand the pre-fetched batches to the engine's aggregation path.

        The engine owns normalization, website enrichment, dedupe and scoring;
        we simply replay the batches through a transient stub registry so the
        engine sees them as already-executed providers.
        """
        from .registry import ProviderRegistry

        stub_registry = ProviderRegistry()
        only_active = set(active)
        attempt_info = getattr(self, "_last_attempts", {}) or {}

        for name, batch in batches.items():
            if name not in only_active:
                continue
            info = attempt_info.get(name, {})

            class _BatchedProvider(DiscoveryProvider):
                """Replay a pre-fetched batch (or permanent failure) through the
                engine's aggregation pipeline."""

                def __init__(self, name, batch, error):
                    self.name = name
                    self._batch = batch
                    self._error = error

                def discover(self, _query):
                    if self._error is not None:
                        raise self._error
                    return self._batch

            error = (
                _ProviderReplayError(info["error"]) if info.get("error") else None
            )
            stub_registry.register(_BatchedProvider(name, batch, error))

        engine = LeadDiscoveryEngine(registry=stub_registry, max_workers=self.max_workers)
        return engine.run(query, sources=list(batches.keys()))


class _ProviderReplayError(Exception):
    """Internal marker re-raised by batched replay providers for permanently
    failed providers so the engine records the error in the source summary."""
