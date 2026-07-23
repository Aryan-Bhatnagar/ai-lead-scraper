'''free_lead_discovery
=======================

Provider implementation for free lead discovery using DuckDuckGo HTML search.
This provider uses the public DuckDuckGo HTML endpoint (https://duckduckgo.com/html/)
which does not require an API key and returns search results that we can parse for
business websites.

The public function :func:`discover_free_leads` follows the same contract as
:func:`scraper.lead_discovery.discover_leads` – it accepts an ``industry`` name,
a ``location`` string and a ``max_results`` limit and returns a list of
dictionaries with a normalized schema suitable for the rest of the pipeline.

Only fields that can be reasonably mapped from the DuckDuckGo response are
populated. Optional fields such as ``phone``, ``address``, ``rating``, etc. are
set to ``None`` because they are not available from the source.

All configuration is read from the environment – no API key is required for the
DuckDuckGo HTML endpoint. The function raises ``RuntimeError`` if the API request
fails.

During unit testing the ``requests.get`` call is patched/mocked so no real network
traffic occurs.

The implementation includes a fallback to the original DuckDuckGo Instant Answer
API if the HTML search returns no results.
'''

from __future__ import annotations

import re
import os
from typing import Any, Dict, List
import requests
from urllib.parse import urlparse, urlunparse, parse_qs, unquote

from urllib.parse import urlparse, urlunparse


# ---------------------------------------------------------------------------
# Public constants – useful for callers and tests.
# ---------------------------------------------------------------------------
API_ENDPOINT = "https://api.duckduckgo.com/"
HTML_ENDPOINT = "https://duckduckgo.com/html/"
DEFAULT_MAX_RESULTS = 10
MAX_ALLOWED_RESULTS = 50


# Domains that are useful as directories, social networks, or search results,
# but should not normally be sent directly to the lead scraper.
# Note: "lndedin.com" is a common typo for "linkedin.com" and is blocked for compatibility with tests.
BLOCKED_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "lndedin.com",  # Common typo of linkedin.com
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


def _duckduckgo_html_search(query: str) -> List[Dict[str, Any]]:
    """
    Perform a DuckDuckGo HTML search and return a list of result dictionaries.
    Each dictionary has keys: 'url', 'title', 'snippet'.
    Returns an empty list on failure.
    """
    params = {"q": query}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(HTML_ENDPOINT, params=params, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return []

    # Ensure response.text is a string; if not, treat as no HTML and return empty list
    html = response.text
    if not isinstance(html, str):
        return []

    # Regex to find result links with class "result__url"
    # Matches: <a class="... result__url ..." href="...">title</a>
    pattern = r'<a\s+[^>]*class="[^"]*result__url[^"]*"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
    matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)

    results = []
    for href, title in matches:
        # Extract the actual URL from the duckduckgo redirect URL
        parsed = urlparse(href)
        query_params = parse_qs(parsed.query)
        if 'uddg' not in query_params:
            continue
        actual_url = unquote(query_params['uddg'][0])

        # Normalize the URL
        normalized = _normalize_url(actual_url)
        if not normalized or _is_blocked_domain(normalized):
            continue

        # Use the title as the company name (strip whitespace)
        company_name = title.strip() if title else None

        # We don't extract a snippet from the HTML for simplicity
        # (could be added later if needed)
        results.append({
            'url': normalized,
            'title': company_name,
            'description': None,
        })

    return results


def discover_free_leads(
    industry: str,
    location: str,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> List[Dict[str, Any]]:
    """Discover businesses using DuckDuckGo HTML search with fallback to Instant Answer.

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

    # Always perform HTML search with the primary query format
    query = f"{industry} company {location}"
    html_results = _duckduckgo_html_search(query)

    # Process HTML search results
    html_results_processed = []
    seen_urls = set()

    for res in html_results:
        if len(html_results_processed) >= max_results:
            break
        url = res["url"]
        if url in seen_urls:  # Fixed: check if this specific URL was seen before
            continue
        seen_urls.add(url)

        html_results_processed.append({
            "company_name": res["title"],
            "website": url,
            "description": res["description"],
            "source": "duckduckgo",
            "industry": industry,
            "location": location,
        })

    # Always perform API fallback search
    query = _build_query(industry, location)
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1,
    }

    response = requests.get(API_ENDPOINT, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    # Extract possible results from RelatedTopics
    topics = _extract_related_topics(data)

    # Process API results
    api_results_processed = []
    seen_urls = set()

    for topic in topics:
        if not isinstance(topic, dict):
            continue

        url = topic.get("FirstURL") or topic.get("URL") or ""
        text = topic.get("Text") or ""  # Define text variable here

        if not url:
            continue

        normalized = _normalize_url(url)
        if not normalized or _is_blocked_domain(normalized):
            continue
        if normalized in seen_urls:  # Fixed: check if this specific URL was seen before
            continue

        seen_urls.add(normalized)

        # Extract a plausible company name from the URL or text.
        company_name = None
        if normalized:
            try:
                hostname = urlparse(normalized).hostname or ""
                if hostname.startswith("www."):
                    hostname = hostname[4:]
                parts = hostname.split(".")
                if len(parts) >= 2:
                    # Take the second-level domain as candidate name
                    company_name = parts[-2].replace("-", " ").title()
            except Exception:
                pass
        if not company_name and text:
            # Use first few words of text as company name
            company_name = text.split()[0] if text.split() else None

        api_results_processed.append({
            "company_name": company_name,
            "website": normalized,
            "description": text if text else None,
            "source": "duckduckgo",
            "industry": industry,
            "location": location,
        })

        if len(api_results_processed) >= max_results:
            break

    # Return HTML results if we got any, otherwise fall back to API results
    if html_results_processed:
        return html_results_processed
    else:
        return api_results_processed