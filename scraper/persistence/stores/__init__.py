"""Concrete LeadStore implementations — Phase 19B."""

from .base import LeadQuery, LeadStore
from .memory import InMemoryStore
from .sqlite import SQLiteStore
from .registry import StoreRegistry, default_store_registry

__all__ = [
    "LeadQuery",
    "LeadStore",
    "InMemoryStore",
    "SQLiteStore",
    "StoreRegistry",
    "default_store_registry",
]