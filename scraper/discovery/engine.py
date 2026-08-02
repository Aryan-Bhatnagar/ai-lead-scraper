"""Orchestration engine for lead discovery.

Phase 16A — framework definitions only.  Contains no concrete providers and
no database imports.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .model import UnifiedLead
from .provider import DiscoveryProvider, ProviderResponse
from .query import DiscoveryQuery, DiscoveryBatch
from .registry import ProviderRegistry, default_registry
from .normalizers.registry import default_registry as normalizer_registry

# ---------------------------------------------------------------------------
# Summary value objects
# ---------------------------------------------------------------------------

@dataclass
class SourceRunSummary:
    """Per-provider outcome for a single discovery run."""

    source: str = ""
    found: int = 0
    new: int = 0
    duplicates: int = 0
    failed: int = 0
    no_data: int = 0
    next_cursor: Optional[str] = None
    error: Optional[str] = None


@dataclass
class DiscoveryRunSummary:
    """Checksum-level summary for an entire multi-provider run."""

    total_found: int = 0
    total_new: int = 0
    per_source: Dict[str, SourceRunSummary] = field(default_factory=dict)
    leads: List[UnifiedLead] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class LeadDiscoveryEngine:
    """Concurrent orchestrator for all registered DiscoveryProviders.

    The engine fans out discovery across all providers registered in the
    ``registry`` parameter (or the module-level ``default_registry`` when none
    is supplied).  It collects batches, merges deduplicated UnifiedLead items,
    and returns a DiscoveryRunSummary.
    """

    def __init__(
        self,
        registry: ProviderRegistry = default_registry,
        max_workers: int = 8,
    ) -> None:
        self.registry = registry
        self.max_workers = max_workers

    def run(
        self,
        query: DiscoveryQuery,
        *,
        sources: Optional[List[str]] = None,
    ) -> DiscoveryRunSummary:
        """Execute discovery across selected providers in parallel.

        Parameters
        ----------
        query:
            The single DiscoveryQuery all providers receive.
        sources:
            Optional list of provider names to restrict execution to.
            When ``None``, every registered provider runs.

        Returns
        -------
        DiscoveryRunSummary
            Aggregated counts, per-source breakdown, and the merged list of
            normalized UnifiedLead items ready for persistence.
        """
        # ------------------------------------------------------------------
        # 1. Select providers
        # ------------------------------------------------------------------
        names = sources if sources is not None else self.registry.list()
        providers: List[DiscoveryProvider] = []
        for name in names:
            provider = self.registry.get(name)
            if provider is not None:
                providers.append(provider)

        summary = DiscoveryRunSummary()

        if not providers:
            return summary

        # ------------------------------------------------------------------
        # 2. Fan out concurrently
        # ------------------------------------------------------------------
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            future_map = {
                pool.submit(provider.discover, query): provider
                for provider in providers
            }

            for future in as_completed(future_map):
                provider = future_map[future]
                source_name = provider.name
                src_summary = SourceRunSummary(source=source_name)

                try:
                    batch: DiscoveryBatch = future.result()
                except Exception as exc:
                    # The provider itself should return ProviderResponse on
                    # failure; but we catch all exceptions defensively here.
                    src_summary.error = str(exc)
                    src_summary.failed += 1
                    summary.per_source[source_name] = src_summary
                    continue

                # --------------------------------------------------------------
                # 3. Normalize candidates to UnifiedLeads
                # --------------------------------------------------------------
                for raw in batch.candidates:
                    # Use the NormalizerRegistry to find the appropriate normalizer
                    normalizer = normalizer_registry.get(raw.source)
                    if normalizer:
                        try:
                            lead = normalizer.normalize(raw, query)
                            summary.leads.append(lead)
                            src_summary.found += 1
                        except Exception as norm_exc:
                            print(f"Normalization error for {raw.source}: {norm_exc}")
                            src_summary.failed += 1
                    else:
                        # Fallback if no normalizer is registered for this source
                        print(f"No normalizer registered for source: {raw.source}")
                        src_summary.failed += 1

                # --------------------------------------------------------------
                # 4. Secondary Enrichment (Website Discovery)
                # --------------------------------------------------------------
                # If we discovered leads that have websites, we can now trigger
                # the WebsiteDiscoveryProvider to perform deep scraping.
                # Note: WebsiteDiscoveryProvider.discover() takes a DiscoveryQuery
                # with target_websites in filters.

                websites_to_enrich = [l.website for l in summary.leads if l.website]
                if websites_to_enrich:
                    enrichment_query = DiscoveryQuery(
                        industry=query.industry,
                        location=query.location,
                        keywords=query.keywords,
                        filters={"target_websites": websites_to_enrich}
                    )

                    web_provider = self.registry.get("website_discovery")
                    if web_provider:
                        try:
                            web_batch = web_provider.discover(enrichment_query)

                            # Now normalize these enriched candidates and merge them
                            # back into the original UnifiedLeads.
                            for web_raw in web_batch.candidates:
                                web_norm = normalizer_registry.get(web_raw.source)
                                if web_norm:
                                    enriched_lead = web_norm.normalize(web_raw, enrichment_query)
                                    # Merge enriched data into existing lead with matching website
                                    for lead in summary.leads:
                                        if lead.website == enriched_lead.website:
                                            # Merge simple fields
                                            lead.description = enriched_lead.description or lead.description
                                            # Merge complex fields (sets/lists)
                                            if hasattr(enriched_lead, 'socials') and enriched_lead.socials:
                                                if not hasattr(lead, 'socials') or lead.socials is None:
                                                    lead.socials = {}
                                                lead.socials.update(enriched_lead.socials)
                                            # Add other enrichments as needed...
                                            break
                        except Exception as web_exc:
                            print(f"Website enrichment phase failed: {web_exc}")

                if batch.meta:
                    src_summary.next_cursor = batch.next_cursor

                summary.per_source[source_name] = src_summary
                # Accumulate totals on the run-level summary (raw counts)
                summary.total_found += src_summary.found
                summary.total_new += 0  # placeholder for future dedupe
                summary.leads.extend([])  # placeholder for future dedupe

        # ------------------------------------------------------------------
        # 5. Deduplication (new stage – Phase 18B)
        # ------------------------------------------------------------------
        from scraper.deduplication.deduper import LeadDeduper
        deduper = LeadDeduper()
        deduped_leads = deduper.deduplicate(summary.leads)
        # Replace the leads list with the deduplicated version and update counts
        summary.leads = deduped_leads
        summary.total_new = len(deduped_leads)
        # ``total_found`` already reflects the raw number of candidates; we keep
        # it unchanged because it represents discovery volume before dedup.

        return summary
