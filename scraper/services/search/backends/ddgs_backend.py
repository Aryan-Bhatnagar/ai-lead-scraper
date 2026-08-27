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
            print(f"DDGSBackend primary error: {e}, attempting native HTTP fallback...")
            return self._native_fallback(query, limit)

    def _native_fallback(self, query: str, limit: int) -> List[Dict[str, Any]]:
        import urllib.parse
        import urllib.request
        import re

        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
        )

        canonical_results = []
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                blocks = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<a class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
                if not blocks:
                    # Alternative regex for DDG HTML results
                    links = re.findall(r'uddg=([^&"]+)', html)
                    titles = re.findall(r'<a class="result__title"[^>]*>(.*?)</a>', html, re.DOTALL)
                    for idx, l in enumerate(links[:limit]):
                        clean_url = urllib.parse.unquote(l)
                        t_str = re.sub(r'<[^>]+>', '', titles[idx]).strip() if idx < len(titles) else clean_url
                        result = SearchResult(
                            title=t_str,
                            url=clean_url,
                            snippet=t_str,
                            source_engine=self.name,
                            timestamp=datetime.now(UTC).isoformat()
                        )
                        canonical_results.append(result.to_dict())
                    return canonical_results

                for href, raw_t, raw_s in blocks[:limit]:
                    clean_t = re.sub(r'<[^>]+>', '', raw_t).strip()
                    clean_s = re.sub(r'<[^>]+>', '', raw_s).strip()
                    actual_url = href
                    if 'uddg=' in href:
                        m = re.search(r'uddg=([^&]+)', href)
                        if m:
                            actual_url = urllib.parse.unquote(m.group(1))

                    result = SearchResult(
                        title=clean_t,
                        url=actual_url,
                        snippet=clean_s,
                        source_engine=self.name,
                        timestamp=datetime.now(UTC).isoformat()
                    )
                    canonical_results.append(result.to_dict())
        except Exception as ex:
            print(f"DDGSBackend native fallback error: {ex}")

        return canonical_results
