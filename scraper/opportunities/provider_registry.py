from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import aiohttp
import asyncio
from .opportunity_models import Opportunity

class BaseOpportunityProvider(ABC):
    """Abstract base class for opportunity providers."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    async def search_opportunities(self, query: str, limit: int = 100) -> List[Opportunity]:
        """Search for opportunities based on a query."""
        pass

    @abstractmethod
    async def get_opportunity_details(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get detailed information about a specific opportunity."""
        pass

    @abstractmethod
    def get_supported_categories(self) -> List[str]:
        """Return list of categories this provider supports."""
        pass

    def normalize_opportunity(self, raw_data: Dict[str, Any]) -> Opportunity:
        """Normalize raw provider data into Opportunity model.
        This is a base implementation that should be overridden by subclasses.
        """
        # This is a base implementation that should be overridden by each provider
        # to map their specific fields to the Opportunity model.
        raise NotImplementedError("Subclasses must implement normalize_opportunity")

class ProviderRegistry:
    """Registry for opportunity providers."""

    def __init__(self):
        self._providers: dict[str, BaseOpportunityProvider] = {}

    def register(self, provider: BaseOpportunityProvider):
        """Register a provider."""
        self._providers[provider.name] = provider

    def get_provider(self, name: str) -> Optional[BaseOpportunityProvider]:
        """Get a provider by name."""
        return self._providers.get(name)

    def get_all_providers(self) -> List[BaseOpportunityProvider]:
        """Get all registered providers."""
        return list(self._providers.values())

    def get_provider_names(self) -> List[str]:
        """Get names of all registered providers."""
        return list(self._providers.keys())

# Global registry instance
provider_registry = ProviderRegistry()