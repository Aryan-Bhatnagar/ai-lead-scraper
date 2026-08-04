from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

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