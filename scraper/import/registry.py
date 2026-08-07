"""
Import Adapter Registry.

Manages registration and lookup of import adapters by source name or file extension.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from .base import BaseImportAdapter


class ImportAdapterRegistry:
    """Registry for import adapters, similar to the normalizer registry."""

    def __init__(self):
        self._adapters: Dict[str, BaseImportAdapter] = {}
        self._by_extension: Dict[str, List[BaseImportAdapter]] = {}

    def register(self, adapter: BaseImportAdapter) -> None:
        """Register an adapter instance.

        Args:
            adapter: An instance of a BaseImportAdapter subclass.
        """
        self._adapters[adapter.source_name] = adapter
        for ext in adapter.supported_extensions:
            ext_lower = ext.lower()
            if ext_lower not in self._by_extension:
                self._by_extension[ext_lower] = []
            self._by_extension[ext_lower].append(adapter)

    def get_by_source(self, source_name: str) -> Optional[BaseImportAdapter]:
        """Get adapter by source name (case-insensitive)."""
        return self._adapters.get(source_name)

    def get_by_extension(self, extension: str) -> List[BaseImportAdapter]:
        """Get all adapters for a file extension."""
        return self._by_extension.get(extension.lower(), [])

    def get_by_file_path(self, file_path: str) -> Optional[BaseImportAdapter]:
        """Get adapter by file path (uses extension)."""
        import os
        _, ext = os.path.splitext(file_path)
        adapters = self.get_by_extension(ext)
        return adapters[0] if adapters else None

    def list_sources(self) -> List[str]:
        """List all registered source names."""
        return list(self._adapters.keys())

    def list_extensions(self) -> List[str]:
        """List all supported file extensions."""
        return list(self._by_extension.keys())

    def auto_detect(self, file_path: str) -> Optional[BaseImportAdapter]:
        """Auto-detect adapter based on file content and extension."""
        import json
        import os

        _, ext = os.path.splitext(file_path)
        adapters = self.get_by_extension(ext)

        if not adapters:
            return None

        if len(adapters) == 1:
            return adapters[0]

        # Multiple adapters for this extension - try content-based detection
        try:
            # Read the full file with error handling to ensure valid JSON
            content = None
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    with open(file_path, "r", encoding=encoding, errors='replace') as f:
                        content = f.read()
                    data = json.loads(content)
                    break
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue

            if content is None:
                return adapters[0]

            # Check for Apollo format (array of objects with firstName, companyName, etc.)
            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                if isinstance(first, dict):
                    if "firstName" in first and "companyName" in first:
                        for adapter in adapters:
                            if adapter.source_name == "Apollo":
                                return adapter
                    if "uid" in first and "externalLink" in first:
                        for adapter in adapters:
                            if adapter.source_name == "Upwork":
                                return adapter
                    if "place_id" in first or "formatted_address" in first:
                        for adapter in adapters:
                            if adapter.source_name == "Google Maps":
                                return adapter

            # Check for object with data array
            if isinstance(data, dict):
                for key in ["data", "records", "leads", "contacts", "results", "jobs", "opportunities", "places"]:
                    if key in data and isinstance(data[key], list) and len(data[key]) > 0:
                        first = data[key][0]
                        if isinstance(first, dict):
                            if "firstName" in first and "companyName" in first:
                                for adapter in adapters:
                                    if adapter.source_name == "Apollo":
                                        return adapter
                            if "uid" in first and "externalLink" in first:
                                for adapter in adapters:
                                    if adapter.source_name == "Upwork":
                                        return adapter
                            if "place_id" in first or "formatted_address" in first:
                                for adapter in adapters:
                                    if adapter.source_name == "Google Maps":
                                        return adapter

        except Exception as e:
            # Log error but fall back to first adapter
            pass

        # Default to first adapter
        return adapters[0]


# Global default registry instance
default_registry = ImportAdapterRegistry()