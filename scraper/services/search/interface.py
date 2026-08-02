"""
Search backend interface.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from .schema import SearchResult

class SearchBackend(ABC):
    """
    Abstract base class for all search engine implementations.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique identifier for the search engine (e.g., 'google')."""
        ...

    @abstractmethod
    def search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Execute a search and return a list of results.

        Each dictionary in the list must be compatible with the SearchResult schema.
        """
        ...
