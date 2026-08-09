"""Repository configuration — Phase 19B.

Single place that decides *where* the repository database lives and what the
default backend URI is, so no caller needs to hard-code paths.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _repo_root() -> Path:
    """Project root regardless of where Python was launched from."""
    return Path(__file__).resolve().parent.parent.parent


def default_db_path() -> Path:
    """Location of the dedicated Lead Repository SQLite file.

    Deliberately separate from the legacy ``data/leads.db`` used by the
    scraper API so this layer can migrate independently.
    """
    return _repo_root() / "data" / "leads_repo.db"


def default_sqlite_uri() -> str:
    return f"sqlite:///{default_db_path().as_posix()}"


@dataclass
class PersistenceConfig:
    """Runtime knobs for :class:`LeadRepository`."""

    backend_uri: str = field(default_factory=lambda: os.getenv(
        "LEAD_REPOSITORY_URI", default_sqlite_uri()
    ))
    """Backend connection string (``memory://`` or ``sqlite:///...``)."""

    page_size_default: int = 50
    """Default ``per_page`` when callers omit it."""

    page_size_max: int = 500
    """Hard ceiling on ``per_page`` to stop runaway scans."""


DEFAULT_CONFIG = PersistenceConfig()
