"""
Backend factory for managing search engine implementations.
"""

from typing import Dict, Optional, Type
from .interface import SearchBackend
from .backends.ddgs_backend import DDGSBackend

class BackendFactory:
    """
    Registry for search engine backends.
    """

    def __init__(self) -> None:
        self._backends: Dict[str, SearchBackend] = {}

    def register(self, backend: SearchBackend) -> None:
        """Register a concrete search backend."""
        self._backends[backend.name] = backend

    def get(self, name: str) -> Optional[SearchBackend]:
        """Retrieve a registered backend by name."""
        return self._backends.get(name)

    def list_available(self) -> list[str]:
        """List all registered backend names."""
        return list(self._backends.keys())

# Module-level singleton
default_factory = BackendFactory()
default_factory.register(DDGSBackend())

