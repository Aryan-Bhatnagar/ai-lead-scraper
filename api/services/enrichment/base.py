import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

@dataclass
class ProviderResponse:
    """Standardized response from any enrichment provider."""
    data: Dict[str, Any]
    confidence: float = 1.0
    status: str = "success"  # "success" | "failed" | "no_data"
    error: Optional[str] = None

class BaseEnrichmentProvider(ABC):
    """Abstract Base Class for all data enrichment sources."""

    @abstractmethod
    def fetch_data(self, lead_id: int, website: str, company_name: str) -> ProviderResponse:
        """Fetch raw data from the source and return it in a standardized response."""
        pass

    def _normalize_response(self, raw_data: Any) -> Dict[str, Any]:
        """Optional helper to cast raw provider data into a partial Business Profile format."""
        return raw_data if isinstance(raw_data, dict) else {}
