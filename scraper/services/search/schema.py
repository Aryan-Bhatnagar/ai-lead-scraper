"""
Canonical search result schema.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class SearchResult:
    """
    Canonical representation of a search result across all engines.
    """
    title: str
    url: str
    snippet: str
    source_engine: str
    query: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    location: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for DiscoveryProvider compatibility."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source_engine": self.source_engine,
            "query": self.query,
            "timestamp": self.timestamp,
            "location": self.location,
        }
