"""Concrete normalizer implementations.

Importing this package causes all bundled normalizers to register themselves
with ``scraper.discovery.normalizers.registry.default_registry``.
"""

from . import google_search as google_search  # noqa: F401
from . import google_maps as google_maps  # noqa: F401
from . import website as website  # noqa: F401

__all__ = ["google_search", "google_maps", "website"]
