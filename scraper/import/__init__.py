"""
Import Adapter Package for AI Lead Scraper.

This package provides adapters for importing leads from various data sources
into the unified lead model.
"""

from .base import BaseImportAdapter, ImportResult
from .registry import ImportAdapterRegistry, default_registry
from .orchestrator import ImportOrchestrator
from .apollo import ApolloImportAdapter
from .upwork import UpworkImportAdapter
from .google_maps import GoogleMapsImportAdapter
from .csv_adapter import CSVImportAdapter

# Auto-register default adapters
default_registry.register(ApolloImportAdapter())
default_registry.register(UpworkImportAdapter())
default_registry.register(GoogleMapsImportAdapter())
default_registry.register(CSVImportAdapter())

__all__ = [
    "BaseImportAdapter",
    "ImportResult",
    "ImportAdapterRegistry",
    "default_registry",
    "ImportOrchestrator",
    "ApolloImportAdapter",
    "UpworkImportAdapter",
    "GoogleMapsImportAdapter",
    "CSVImportAdapter",
]