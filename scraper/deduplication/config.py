"""Deduplication configuration.

Only the fuzzy‑company‑name similarity threshold is configurable for now.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DedupConfig:
    """Configuration for the LeadDeduper.

    Attributes
    ----------
    company_name_min_similarity: float
        The minimum similarity (0‑1) required for two company names to be
        considered a match when the higher‑priority keys (domain, email domain,
        phone) are not equal.
    """

    company_name_min_similarity: float = 0.85

    @classmethod
    def default(cls) -> "DedupConfig":
        """Return the default configuration.

        Having a factory makes it easy to extend the config later without
        changing call‑sites.
        """
        return cls()
