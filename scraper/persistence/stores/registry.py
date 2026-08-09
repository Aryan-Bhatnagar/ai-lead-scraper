"""StoreRegistry — Phase 19B.

Maps backend URI schemes (``memory://``, ``sqlite:///...``) to LeadStore
factories so ``LeadRepository`` can swap backends without changing caller
code.  Callers may register additional schemes at runtime.
"""

from __future__ import annotations

from typing import Callable, Dict

from .base import LeadStore
from .memory import InMemoryStore
from .sqlite import SQLiteStore
from ..exceptions import StoreConfigurationError


Factory = Callable[[str], LeadStore]


class StoreRegistry:
    """Resolver from backend URI → concrete LeadStore instance."""

    def __init__(self) -> None:
        self._factories: Dict[str, Factory] = {}
        self.register("memory", lambda uri: InMemoryStore())
        self.register("sqlite", lambda uri: SQLiteStore(uri))

    def register(self, scheme: str, factory: Factory) -> None:
        """Register ``factory(uri)`` under ``scheme://``.

        ``factory`` receives the full URI; e.g. ``sqlite:///data/x.db``.
        """
        if not scheme or "://" in scheme:
            raise StoreConfigurationError(
                f"scheme must be a bare name without ://, got {scheme!r}"
            )
        self._factories[scheme.lower()] = factory

    def resolve(self, uri: str) -> LeadStore:
        if "://" not in (uri or ""):
            raise StoreConfigurationError(
                f"backend URI must be of form scheme://..., got {uri!r}"
            )
        scheme = uri.split("://", 1)[0].lower()
        factory = self._factories.get(scheme)
        if factory is None:
            raise StoreConfigurationError(
                f"no LeadStore registered for scheme {scheme!r}"
            )
        return factory(uri)


# Module-level default registry used when callers don't supply one.
default_store_registry = StoreRegistry()
