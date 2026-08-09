"""
Opportunity normalizer for converting raw provider data to Opportunity model.
"""
from typing import Dict, Any, Optional
from scraper.opportunities.provider_registry import provider_registry
from scraper.opportunities.base_provider import BaseOpportunityProvider


class OpportunityNormalizer:
    """Normalizes raw opportunity data from providers into Opportunity models."""

    def __init__(self, provider_registry=None):
        self.provider_registry = provider_registry or provider_registry

    def normalize(self, raw_data: Dict[str, Any], provider_name: str) -> Optional[dict]:
        """
        Normalize raw data from a provider into a dictionary suitable for Opportunity creation.

        Args:
            raw_data: Raw data from the provider
            provider_name: Name of the provider (e.g., 'upwork', 'freelancer')

        Returns:
            Normalized opportunity data as a dictionary, or None if normalization fails
        """
        provider = self.provider_registry.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found in registry")

        # Use the provider's normalize_opportunity method
        opportunity = provider.normalize_opportunity(raw_data)
        if opportunity:
            return opportunity.to_dict()
        return None

    def normalize_batch(self, raw_data_list: list, provider_name: str) -> list:
        """
        Normalize a batch of raw data items.

        Args:
            raw_data_list: List of raw data items from a provider
            provider_name: Name of the provider

        Returns:
            List of normalized opportunity dictionaries
        """
        normalized = []
        for raw_data in raw_data_list:
            try:
                normalized_opp = self.normalize(raw_data, provider_name)
                if normalized_opp:
                    normalized.append(normalized_opp)
            except Exception as e:
                # Log error but continue processing other items
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to normalize opportunity from {provider_name}: {e}")
                continue
        return normalized