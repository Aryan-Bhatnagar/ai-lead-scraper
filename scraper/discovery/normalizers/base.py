"""
Base normalizer interface.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from ..model import UnifiedLead
from ..query import RawCandidate, DiscoveryQuery

class BaseNormalizer(ABC):
    """
    Abstract base class for mapping raw provider payloads to UnifiedLead.
    """

    @abstractmethod
    def normalize(self, candidate: RawCandidate, query: DiscoveryQuery) -> UnifiedLead:
        """
        Transforms a RawCandidate into a UnifiedLead.

        Args:
            candidate: The raw data and metadata from the provider.
            query: The original query used for discovery (to populate provenance).

        Returns:
            A fully populated UnifiedLead object.
        """
        ...
