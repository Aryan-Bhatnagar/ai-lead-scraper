"""
DuckDuckGo Search Backend.

Implements the SearchBackend interface using the DDGS search library.
"""

from __future__ import annotations
from datetime import UTC, datetime
from typing import List, Dict, Any

from ..interface import SearchBackend
from ..schema import SearchResult

class DDGSBackend(SearchBackend):
    """
    Search backend for DuckDuckGo.
    """

    def __init__(self):
        try:
            from ddgs import DDGS
            self.ddgs = DDGS()
        except ImportError:
            print("Error: ddgs package not installed. Please run 'pip install ddgs'.")
            self.ddgs = None

    @property
    def name(self) -> str:
        return "ddgs"

    def search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Perform a search using DuckDuckGo.
        """
        if self.ddgs is None:
            return []

        try:
            # Use the text search method from DDGS
            # results is a generator of dicts: {"title": ..., "href": ..., "body": ...}
            raw_results = self.ddgs.text(query, max_results=limit)

            canonical_results = []
            for res in raw_results:
                # Map DDGS schema to our Canonical SearchResult schema
                result = SearchResult(
                    title=res.get("title", ""),
                    url=res.get("href", ""),
                    snippet=res.get("body", ""),
                    source_engine=self.name,
                    query=query,
                    timestamp=datetime.now(UTC).isoformat()
                )
                canonical_results.append(result.to_dict())

            return canonical_results

        except Exception as e:
            print(f"DDGSBackend error during search for '{query}': {e}")
            return []
