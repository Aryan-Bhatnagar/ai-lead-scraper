"""Provider registry for the Unified Lead Discovery framework.

Phase 16A — framework definitions only.  Contains no concrete providers.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .provider import DiscoveryProvider
from .providers.website_provider import WebsiteDiscoveryProvider
from .providers.upwork_provider import UpworkDiscoveryProvider
from .providers.google_search_provider import GoogleSearchDiscoveryProvider

class ProviderRegistry:
    """In-memory registry mapping provider name → provider instance.

    The registry is intentionally simple — a dict — because Phase 16A ships
    no concrete providers.  Future phases add entries via ``register()``.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, DiscoveryProvider] = {}

    def register(self, provider: DiscoveryProvider) -> None:
        """Add a provider instance to the registry."""
        self._providers[provider.name] = provider

    def unregister(self, name: str) -> None:
        """Remove a provider by name.  Raises KeyError if absent."""
        del self._providers[name]

    def get(self, name: str) -> Optional[DiscoveryProvider]:
        """Return a provider by name, or None."""
        return self._providers.get(name)

    def list(self) -> List[str]:
        """Return all registered provider names."""
        return list(self._providers.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._providers

    def __len__(self) -> int:
        return len(self._providers)


# Module-level singleton for convenience — the engine uses this by default.
default_registry = ProviderRegistry()
default_registry.register(WebsiteDiscoveryProvider())
default_registry.register(UpworkDiscoveryProvider())
default_registry.register(GoogleSearchDiscoveryProvider())
