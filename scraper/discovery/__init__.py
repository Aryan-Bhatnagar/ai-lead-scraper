"""unified discovery framework.

Phase 16A — framework scaffolding only. No concrete providers are registered
and no existing discovery modules are modified by this package.
"""

from .model import UnifiedLead, LocationData, Provenance
from .query import DiscoveryQuery, DiscoveryBatch, RawCandidate, SourceMeta
from .provider import DiscoveryProvider, CapabilitySet, ProviderResponse as ProviderDiscoveryResponse
from .registry import ProviderRegistry, default_registry
from .engine import LeadDiscoveryEngine, DiscoveryRunSummary, SourceRunSummary
from .orchestrator import DiscoveryOrchestrator, DEFAULT_PROVIDER_ORDER

__all__ = [
    # model.py
    "UnifiedLead",
    "LocationData",
    "Provenance",
    # query.py
    "DiscoveryQuery",
    "DiscoveryBatch",
    "RawCandidate",
    "SourceMeta",
    # provider.py
    "DiscoveryProvider",
    "CapabilitySet",
    "ProviderDiscoveryResponse",
    # registry.py
    "ProviderRegistry",
    "default_registry",
    # engine.py
    "LeadDiscoveryEngine",
    "DiscoveryRunSummary",
    "SourceRunSummary",
    # orchestrator.py
    "DiscoveryOrchestrator",
    "DEFAULT_PROVIDER_ORDER",
]
