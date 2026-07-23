'''google_maps_discovery
========================

Provider implementation for Google Maps / Google Places based lead discovery.

The public function :func:`discover_google_maps` follows the same contract as
:func:`scraper.lead_discovery.discover_leads` – it accepts an ``industry`` name,
a ``location`` string and a ``max_results`` limit and returns a list of
 dictionaries with a normalized schema suitable for the rest of the pipeline.

Only fields that are reliably available from the **Places Text Search** API are
populated.  Optional fields such as ``phone`` or ``website`` are set to ``None``
because they require an additional *Place Details* request which is outside the
scope of Phase 12A (the focus is discovery only).

All configuration is read from the environment – the API key must be supplied
via ``GOOGLE_MAPS_API_KEY``.  The function raises ``RuntimeError`` if the key is
missing; the Flask endpoint translates this into a 500 error with a helpful
message.

The implementation avoids hard‑coding any URL parts besides the official API
endpoint and makes the HTTP call through ``requests``.  During unit testing the
``requests.get`` call is patched/mocked so no real network traffic occurs.
'''

from __future__ import annotations

import os
from typing import Any, Dict, List
import requests
from sqlalchemy import exc

# ---------------------------------------------------------------------------
# Public constants – useful for callers and tests.
# ---------------------------------------------------------------------------
API_ENDPOINT = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DEFAULT_MAX_RESULTS = 20
MAX_ALLOWED_RESULTS = 50


def _validate_inputs(industry: str, location: str, max_results: int) -> None:
    """Validate user supplied parameters.

    The validation mirrors the checks performed in the Flask endpoint so the
    discovery function can be called directly from other code (e.g. tests) without
    the surrounding request handling.
    """
    if not isinstance(industry, str):
        raise ValueError("'industry' must be a string")
    industry = industry.strip()
    if not industry:
        raise ValueError("'industry' cannot be empty")

    if not isinstance(location, str):
        raise ValueError("'location' must be a string")
    location = location.strip()
    if not location:
        raise ValueError("'location' cannot be empty")

    if not isinstance(max_results, int) or isinstance(max_results, bool):
        raise ValueError("'max_results' must be an integer")
    if not (1 <= max_results <= MAX_ALLOWED_RESULTS):
        raise ValueError(
            f"'max_results' must be between 1 and {MAX_ALLOWED_RESULTS}"
        )

    # ``industry`` and ``location`` are deliberately not returned – they are only
    # used to build the query string for the API.


def _build_query(industry: str, location: str) -> str:
    """Construct the query string understood by the Places Text Search API.

    The API treats the ``query`` parameter as free‑text, so we concatenate the
    industry and location with a space.  Adding ``" in "`` improves relevance on
    some queries but is optional – the simple concatenation works reliably.
    """
    return f"{industry} {location}".strip()


def _extract_normalized(result: Dict[str, Any]) -> Dict[str, Any]:
    """Map a raw Google Places result to the project's normalized schema.

    Fields that the Text Search endpoint does not provide (phone, website) are set
    to ``None``.  ``google_maps_url`` is built from the ``place_id`` using the
    public Google Maps link format.
    """
    place_id = result.get("place_id")
    return {
        "company_name": result.get("name"),
        "address": result.get("formatted_address"),
        "phone": None,  # requires a Place Details request
        "website": None,  # requires a Place Details request
        "rating": result.get("rating"),
        "reviews_count": result.get("user_ratings_total"),
        "place_id": place_id,
        "google_maps_url": (
            f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else None
        ),
        "source": "google_maps",
    }


def discover_google_maps(
    industry: str,
    location: str,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> List[Dict[str, Any]]:
    """Discover businesses using the Google Places *Text Search* API.

    Parameters
    ----------
    industry: str
        Business sector or type, e.g. ``"Digital Marketing Agency"``.
    location: str
        Human readable location, e.g. ``"Chandigarh"``.
    max_results: int, optional
        Upper bound on the number of entries to return.  The API itself returns a
        maximum of 20 results per request; the function caps the result list to
        ``max_results`` for consistency with the existing discovery API.

    Returns
    -------
    List[Dict[str, Any]]
        Normalized lead dictionaries ready for downstream processing.
    """
    # Input validation – raises ``ValueError`` on bad user data.
    _validate_inputs(industry, location, max_results)

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY environment variable is not set")

    query = _build_query(industry, location)
    params = {
        "query": query,
        "key": api_key,
        "language": "en",
    }

    try:
        response = requests.get(API_ENDPOINT, params=params)
        response.raise_for_status()
    except requests.RequestException as exc:
     raise RuntimeError(f"Google Maps API request failed: {exc}") from exc

    data = response.json()
    raw_results: List[Dict[str, Any]] = data.get("results", [])

    normalized: List[Dict[str, Any]] = []
    for raw in raw_results:
        if not isinstance(raw, dict):
            continue
        normalized.append(_extract_normalized(raw))
        if len(normalized) >= max_results:
            break

    return normalized
