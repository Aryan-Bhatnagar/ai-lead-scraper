"""Persistence layer — Phase 19B.

Public interface:
- LeadRepository: domain-facing repository for leads
- LeadStore: storage abstraction (ABC)
- InMemoryStore: dict-backed store (for tests)
- SQLiteStore: default persistent store
- LifecycleState: enum of lead lifecycle states
- Page: paginated result wrapper
- LifecycleEvent: audit trail entry
- LeadRecord: storage DTO (alias for dict)
- StoreRegistry: maps URI strings to LeadStore factories
- default_store_registry: pre-configured registry with memory:// and sqlite:///
- PersistenceConfig: runtime knobs (page sizes, etc.)
- DEFAULT_CONFIG: default configuration instance
"""

from .config import DEFAULT_CONFIG, PersistenceConfig
from .exceptions import DuplicateLeadError, InvalidLifecycleTransition, StoreConfigurationError
from .lifecycle import LifecycleState
from .models import LifecycleEvent, LeadRecord, Page
from .mappers import lead_to_record, record_to_lead
from .repository import LeadRepository
from .stores import LeadStore, StoreRegistry, default_store_registry
from .stores.memory import InMemoryStore
from .stores.sqlite import SQLiteStore

__all__ = [
    "LeadRepository",
    "LeadStore",
    "InMemoryStore",
    "SQLiteStore",
    "LifecycleState",
    "Page",
    "LifecycleEvent",
    "LeadRecord",
    "StoreRegistry",
    "default_store_registry",
    "PersistenceConfig",
    "DEFAULT_CONFIG",
    "DuplicateLeadError",
    "InvalidLifecycleTransition",
    "StoreConfigurationError",
]