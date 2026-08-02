"""
Normalizer registry for mapping providers to their respective normalizers.
"""

from typing import Dict, Optional
from .base import BaseNormalizer

class NormalizerRegistry:
    """
    In-memory registry mapping provider source names to normalizer instances.
    """

    def __init__(self) -> None:
        self._normalizers: Dict[str, BaseNormalizer] = {}

    def register(self, source_name: str, normalizer: BaseNormalizer) -> None:
        """Register a normalizer for a specific provider source."""
        self._normalizers[source_name] = normalizer

    def get(self, source_name: str) -> Optional[BaseNormalizer]:
        """Retrieve the normalizer for a given provider source."""
        return self._normalizers.get(source_name)

    def list_available(self) -> list[str]:
        """List all registered provider sources."""
        return list(self._normalizers.keys())

# Module-level singleton
default_registry = NormalizerRegistry()
