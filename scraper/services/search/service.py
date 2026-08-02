"""
Search service orchestrator.
"""

from typing import List, Dict, Any, Optional
from .factory import default_factory # Using the singleton
from .factory import default_factory as factory
from .schema import SearchResult

class SearchService:
    """
    High-level service for executing searches across multiple backends.
    """

    def __init__(self, factory=None):
        # Allow injecting a custom factory for testing
        self.factory = factory or default_factory

    def search(self, query: str, limit: int = 10, preferred_backend: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Execute a search using the specified or default backend.
        """
        # 1. Determine which backend to use
        backend_name = preferred_backend
        if not backend_name:
            # Default to the first available backend if none specified
            available = self.factory.list_available()
            if not available:
                return []
            backend_name = available[0]

        # 2. Retrieve backend from factory
        backend = self.factory.get(backend_name)
        if not backend:
            return []

        try:
            # 3. Execute the search
            raw_results = backend.search(query, limit)

            # 4. Ensure results are canonicalized
            # Each backend is responsible for returning dicts compatible with SearchResult,
            # but we can explicitly wrap them here if needed.
            return raw_results

        except Exception as e:
            # Log error (omitted for brevity) and return empty list to ensure stability
            print(f"SearchService error using backend {backend_name}: {e}")
            return []
