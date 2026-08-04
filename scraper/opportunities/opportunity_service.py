"""
Opportunity service layer.
"""
from typing import List, Optional, Dict, Any
from .opportunity_models import Opportunity
from .opportunity_repository import OpportunityRepository
from .opportunity_engine import OpportunityEngine
from .provider_registry import provider_registry
from .query_generator import QueryGenerator, Query

class OpportunityService:
    """Service for opportunity discovery and management."""

    def __init__(self, repository: Optional[OpportunityRepository] = None,
                 engine: Optional[OpportunityEngine] = None):
        self.repository = repository or OpportunityRepository()
        self.engine = engine or OpportunityEngine(self.repository)
        self.query_generator = QueryGenerator()

    def discover_opportunities(self,
                             categories: Optional[List[str]] = None,
                             custom_keywords: Optional[List[str]] = None,
                             max_queries_per_category: int = 3,
                             max_opportunities_per_query: int = 50,
                             providers: Optional[List[str]] = None) -> List[Opportunity]:
        """
        Discover opportunities from enabled providers.

        Args:
            categories: List of categories to search for. If None, use all categories.
            custom_keywords: Additional keywords to include in queries.
            max_queries_per_category: Maximum number of queries to generate per category.
            max_opportunities_per_query: Maximum opportunities to fetch per query per provider.
            providers: Specific providers to use (if None, use all enabled providers).

        Returns:
            List of discovered opportunities.
        """
        # Generate queries
        queries = self.query_generator.generate_queries(
            categories=categories,
            custom_keywords=custom_keywords,
            max_queries_per_category=max_queries_per_category
        )

        # Temporarily enable/disable providers if specified
        original_enabled = set()
        if providers is not None:
            # Disable all providers first
            for provider_name in provider_registry.get_provider_names():
                if provider_name in self.engine._enabled_providers:
                    original_enabled.add(provider_name)
                    self.engine.disable_provider(provider_name)

            # Enable only the specified providers
            for provider_name in providers:
                self.engine.enable_provider(provider_name)

        try:
            # Discover opportunities
            opportunities = self.engine.discover_opportunities(
                queries=queries,
                max_opportunities_per_query=max_opportunities_per_query
            )
            return opportunities
        finally:
            # Restore original provider state
            if providers is not None:
                # Disable all providers
                for provider_name in provider_registry.get_provider_names():
                    self.engine.disable_provider(provider_name)
                # Re-enable originally enabled providers
                for provider_name in original_enabled:
                    self.engine.enable_provider(provider_name)

    def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get an opportunity by ID."""
        return self.repository.get_opportunity(opportunity_id)

    def get_opportunities(self, **kwargs) -> List[Opportunity]:
        """Get opportunities with optional filtering."""
        return self.repository.get_opportunities(**kwargs)

    def search_opportunities(self, query: str, limit: int = 50) -> List[Opportunity]:
        """Search opportunities by text query."""
        return self.repository.search_opportunities(query, limit)

    def get_opportunity_statistics(self) -> Dict[str, Any]:
        """Get statistics about opportunities."""
        return self.repository.get_statistics()

    def get_opportunity_recommendations(self, opportunities: List[Opportunity]) -> List[Dict[str, Any]]:
        """Generate recommendations for opportunities."""
        return self.engine.generate_recommendations(opportunities)

    def enable_provider(self, provider_name: str):
        """Enable a provider for opportunity discovery."""
        self.engine.enable_provider(provider_name)

    def disable_provider(self, provider_name: str):
        """Disable a provider for opportunity discovery."""
        self.engine.disable_provider(provider_name)

    def get_enabled_providers(self) -> List[str]:
        """Get list of enabled provider names."""
        return [p.name for p in self.engine.get_enabled_providers()]

    def get_available_providers(self) -> List[str]:
        """Get list of all available provider names."""
        return provider_registry.get_provider_names()

    def get_available_categories(self) -> List[str]:
        """Get list of all available categories."""
        return self.query_generator.get_all_categories()