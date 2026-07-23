'''free_lead_discovery
=======================

Provider implementation for free lead discovery using the DuckDuckGo Instant Answer API.
This provider uses the public DuckDuckGo instant answer endpoint (https://api.duckduckgo.com/)
which does not require an API key and returns structured data including related topics and
abstracts that we can map to lead-like structures.

The public function :func:`discover_free_leads` follows the same contract as
:func:`scraper.lead_discovery.discover_leads` – it accepts an ``industry`` name,
a ``location`` string and a ``max_results`` limit and returns a list of
dictionaries with a normalized schema suitable for the rest of the pipeline.

Only fields that can be reasonably mapped from the DuckDuckGo response are populated.
Optional fields such as ``phone``, ``address``, ``rating``, etc. are set to ``None``
because they are not available from the source.

All configuration is read from the environment – no API key is required for the
DuckDuckGo Instant Answer API. The function raises ``RuntimeError`` if the API request
fails.

During unit testing the ``requests.get`` call is patched/mocked so no real network
traffic occurs.
'''

from __future__ import annotations

import os
from typing import Any, Dict, List
import requests

from urllib.parse import urlparse, urlunparse


# ---------------------------------------------------------------------------
# Public constants – useful for callers and tests.
# ---------------------------------------------------------------------------
API_ENDPOINT = "https://api.duckduckgo.com/"
DEFAULT_MAX_RESULTS = 10
MAX_ALLOWED_RESULTS = 50


# Domains that are useful as directories, social networks, or search results,
# but should not normally be sent directly to the lead scraper.
BLOCKED_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "x.com",
    "twitter.com",
    "reddit.com",
    "wikipedia.org",
    "google.com",
    "bing.com",
    "duckduckgo.com",
    "f6s.com",
    "goodfirms.co",
    "clutch.co",
    "techbehemoths.com",
    "github.com",
    "gitlab.com",
}


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


def _build_query(industry: str, location: str) -> str:
    """Build a search query from an industry and location."""
    industry = industry.strip()
    location = location.strip()
    if not industry:
        raise ValueError("industry must not be empty")
    if not location:
        raise ValueError("location must not be empty")
    return f"{industry} {location}"


def _normalize_url(url: str) -> str:
    """
    Normalize a URL to its website root.

    Example:
        https://example.com/about -> https://example.com
    """
    if not isinstance(url, str):
        return ""

    url = url.strip()

    if not url:
        return ""

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return ""

        if not parsed.netloc:
            return ""

        hostname = parsed.hostname

        if not hostname:
            return ""

        hostname = hostname.lower()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        port = f":{parsed.port}" if parsed.port else ""

        netloc = f"{hostname}{port}"

        return urlunparse(
            (
                parsed.scheme.lower(),
                netloc,
                "",
                "",
                "",
                "",
            )
        )

    except (ValueError, TypeError):
        return ""


def _is_blocked_domain(url: str) -> bool:
    """
    Return True if the URL belongs to a blocked domain.
    """
    try:
        hostname = urlparse(url).hostname

        if not hostname:
            return True

        hostname = hostname.lower()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        return any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in BLOCKED_DOMAINS
        )

    except (ValueError, TypeError):
        return True


def _extract_related_topics(data: dict) -> List[Dict[str, Any]]:
    """
    Extract RelatedTopics from DuckDuckGo response.
    Returns list of dicts with keys: 'Text', 'FirstURL', 'Text'.
    """
    topics = data.get("RelatedTopics", [])
    # Some items may be nested under 'Topics' key
    results = []
    for item in topics:
        if isinstance(item, dict):
            if "Topics" in item and isinstance(item["Topics"], list):
                results.extend(item["Topics"])
            else:
                results.append(item)
    return results


def discover_free_leads(
    industry: str,
    location: str,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> List[Dict[str, Any]]:
    """Discover businesses using the DuckDuckGo Instant Answer API.

    Parameters
    ----------
    industry: str
        Business sector or type, e.g. ``"Digital Marketing Agency"``.
    location: str
        Human readable location, e.g. ``"Chandigarh"``.
    max_results: int, optional
        Upper bound on the number of entries to return.  The API itself returns
        a limited number of results; we cap the result list to ``max_results``
        for consistency with the existing discovery API.

    Returns
    -------
    List[Dict[str, Any]]
        Normalized lead dictionaries ready for downstream processing.
        Each dict contains:
            - company_name: str or None
            - website: str or None
            - description: str or None
            - source: str (always "duckduckgo")
            - industry: str (input industry)
            - location: str (input location)
    """
    # Input validation – raises ``ValueError`` on bad user data.
    _validate_inputs(industry, location, max_results)

    query = _build_query(industry, location)
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1,
    }

    try:
        response = requests.get(API_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"DuckDuckGo API request failed: {exc}") from exc

    data = response.json()

    # Extract possible results from RelatedTopics
    topics = _extract_related_topics(data)

    results: List[Dict[str, Any]] = []
    seen_urls = set()

    for topic in topics:
        if not isinstance(topic, dict):
            continue

        # Some topics may have 'FirstURL' (the URL) and 'Text' (description)
        url = topic.get("FirstURL") or topic.get("URL") or ""
        text = topic.get("Text") or ""

        if not url:
            continue

        normalized = _normalize_url(url)
        if not normalized:
            continue
        if _is_blocked_domain(normalized):
            continue
        if normalized in seen_urls:
            continue

        seen_urls.add(normalized)

        # Extract a plausible company name from the URL or text.
        # Try to get domain name without www and tld as a fallback.
        company_name = None
        if normalized:
            try:
                hostname = urlparse(normalized).hostname or ""
                if hostname.startswith("www."):
                    hostname = hostname[4:]
                # Remove common TLDs and split
                parts = hostname.split(".")
                if len(parts) >= 2:
                    # Take the second-level domain as candidate name
                    company_name = parts[-2].replace("-", " ").title()
            except Exception:
                pass
        if not company_name and text:
            # Use first few words of text as company name
            company_name = text.split()[0] if text.split() else None

        results.append(
            {
                "company_name": company_name,
                "website": normalized,
                "description": text if text else None,
                "source": "duckduckgo",
                "industry": industry,
                "location": location,
            }
        )

        if len(results) >= max_results:
            break

    return results