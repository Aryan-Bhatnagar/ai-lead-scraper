"""
Base Import Adapter Framework.

Provides the abstract base class and result dataclass for all import adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from ..discovery.model import UnifiedLead, LocationData, Provenance


@dataclass
class ImportResult:
    """Result of an import operation."""

    leads: List[UnifiedLead] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duplicates_skipped: int = 0
    total_processed: int = 0

    def add_lead(self, lead: UnifiedLead) -> None:
        self.leads.append(lead)
        self.total_processed += 1

    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.total_processed += 1

    def add_duplicate(self) -> None:
        self.duplicates_skipped += 1
        self.total_processed += 1


class BaseImportAdapter(ABC):
    """Abstract base class for import adapters.

    Each adapter implements the logic to parse a specific file format
    and map records to the UnifiedLead model.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Normalized source name (e.g., 'Apollo', 'Upwork', 'Google Maps')."""
        ...

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """List of file extensions this adapter supports (e.g., ['.json', '.csv'])."""
        ...

    @abstractmethod
    def parse_file(self, file_path: str) -> ImportResult:
        """Parse a file and return UnifiedLead objects.

        Args:
            file_path: Path to the file to parse.

        Returns:
            ImportResult with leads, errors, and duplicate count.
        """
        ...

    @abstractmethod
    def map_record(self, record: Dict[str, Any]) -> UnifiedLead:
        """Map a single raw record to a UnifiedLead.

        Args:
            record: Raw record from the source data.

        Returns:
            UnifiedLead with all available fields populated.
        """
        ...

    def _create_provenance(
        self,
        source_url: str,
        raw_ref: str,
        discovered_at: Optional[datetime] = None,
    ) -> Provenance:
        """Create a Provenance object for the lead."""
        return Provenance(
            source=self.source_name,
            source_url=source_url,
            discovered_at=discovered_at or datetime.now(UTC),
            discovery_query={"import_source": self.source_name},
            raw_ref=raw_ref,
        )

    def _create_location(
        self,
        city: str = "",
        country: str = "",
        region: str = "",
        address: str = "",
    ) -> LocationData:
        """Create a LocationData object."""
        location = LocationData()
        location.city = city
        location.country = country
        location.region = region
        location.address = address
        return location