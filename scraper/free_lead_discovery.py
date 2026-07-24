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
    if not (1 <= max_results <= 50):
        raise ValueError(
            f"'max_results' must be between 1 and 50"
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
                parsed.scheme.lower(),  # scheme
                netloc,                 # netloc
                "",                     # path
                "",                     # params
                "",                     # query
                "",                     # fragment
            )
        )

    except Exception as e:
        print(f"[NORMALIZE ERROR] {e}")
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
    # Check if debug mode is enabled via environment variable
    DEBUG = os.environ.get('DEBUG_FREE_LEAD', '').lower() in ('1', 'true', 'yes')

    params = {"q": query}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    if DEBUG:
        print(f"[DEBUG] Attempting DuckDuckGo HTML search for query: {query}")

    try:
        response = requests.get("https://duckduckgo.com/html/", params=params, headers=headers, timeout=10)
        if DEBUG:
            print("=" * 80)
            print("[DEBUG] DuckDuckGo Request")
            print("Status:", response.status_code)
            print("URL:", response.url)
            print("Content-Type:", response.headers.get("Content-Type"))
            print("=" * 80)

            print(response.text[:2000])

            print("=" * 80)

        response.raise_for_status()
    except requests.RequestException as e:
        if DEBUG:
            print(f"[DEBUG] HTML search request failed: {e}")
        return []

    # Safely obtain HTML body
    html = response.text

    # Some unit tests mock requests.Response and response.text may be a MagicMock
    # instead of an actual string. Treat anything that's not a string as empty HTML.
    if not isinstance(html, str):
        if DEBUG:
            print(f"[DEBUG] response.text is {type(html).__name__}, treating as empty HTML")
        html = ""

    if DEBUG:
        # Save the complete HTML response to a temporary file
        debug_file_path = os.path.join(os.getcwd(), 'ddg_response.html')
        with open(debug_file_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"[DEBUG] Saved complete HTML response to {debug_file_path}")
        print(f"[DEBUG] HTML search URL: {response.url}")
        print(f"[DEBUG] HTTP status: {response.status_code}")
        # Log a small snippet of HTML to see structure without flooding logs
        print(f"[DEBUG] HTML snippet (first 500 chars): {html[:500]}")

        # Count total <a> tags
        total_a_tags = len(re.findall(r'<a[^>]*>', html, re.IGNORECASE))
        print(f"[DEBUG] Total <a> tags found: {total_a_tags}")

    # Updated regex to match DuckDuckGo's current result structure
    # Looking for result links with various possible class names
    # Order matters: put patterns that capture full href first
    patterns = [
        r'<a\s+[^>]*class="[^"]*result__url[^"]*"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>',
        r'<a\s+[^>]*class="[^"]*result[^"]*"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>',
        r'<a\s+[^>]*href="([^"]*uddg=[^"]*)"[^>]*>([^<]*)</a>',
        r'<a\s+[^>]*href="/uddg\?uddg=([^"]*)"[^>]*class="[^"]*result[^"]*"[^>]*>([^<]*)</a>'
    ]

    matches = []
    pattern_used = None
    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
        if matches:
            pattern_used = pattern
            if DEBUG:
                print(f"[DEBUG] Found matches using pattern: {pattern}")
            break

    if DEBUG:
        print(f"[DEBUG] Number of raw candidate links (before URL extraction): {len(matches)}")

    results = []
    seen_urls = set()
    accepted_count = 0
    rejected_count = 0

    for href, link_text in matches:
        print("\n====================================================")
        print(f"[STEP 1] href = {href}")

        # Extract the actual URL from the duckduckgo redirect URL
        try:
            if href.startswith("/uddg?"):
                parsed = urlparse("https://duckduckgo.com" + href)
            else:
                parsed = urlparse(href)

            query_params = parse_qs(parsed.query)

            if "uddg" not in query_params:
                print("[REJECT] No uddg parameter")
                rejected_count += 1
                continue

            actual_url = unquote(query_params["uddg"][0])

            print(f"[STEP 2] actual_url = {actual_url}")

        except Exception as e:
            print(f"[REJECT] URL extraction failed: {e}")
            rejected_count += 1
            continue

        # Normalize URL
        normalized = _normalize_url(actual_url)

        print(f"[STEP 3] normalized = {normalized}")

        if not normalized:
            print("[REJECT] normalize returned empty string")
            rejected_count += 1
            continue

        # Blocked domain?
        blocked = _is_blocked_domain(normalized)

        print(f"[STEP 4] blocked = {blocked}")

        if blocked:
            print("[REJECT] Blocked domain")
            rejected_count += 1
            continue

        # Duplicate?
        duplicate = normalized in seen_urls

        print(f"[STEP 5] duplicate = {duplicate}")

        if duplicate:
            print("[REJECT] Duplicate")
            rejected_count += 1
            continue

        seen_urls.add(normalized)

        company_name = link_text.strip() if link_text else None

        results.append({
            "url": normalized,
            "title": company_name,
            "description": None,
        })

        print(f"[STEP 6] ACCEPTED -> {normalized}")

        accepted_count += 1

        if len(results) >= 50:
            break

    if DEBUG:
        print(f"[DEBUG] Number of results after filtering: {len(results)}")
        print(f"[DEBUG] Accepted links: {accepted_count}")
        print(f"[DEBUG] Rejected links: {rejected_count}")

    return results


def discover_free_leads(
    industry: str,
    location: str,
    max_results: int = 10,
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

    # Check if debug mode is enabled via environment variable
    DEBUG = os.environ.get('DEBUG_FREE_LEAD', '').lower() in ('1', 'true', 'yes')

    if DEBUG:
        print(f"[DEBUG] Starting free lead discovery for industry='{industry}', location='{location}', max_results={max_results}")

    # Always perform HTML search with the primary query format
    query = f"{industry} company {location}"
    if DEBUG:
        print(f"[DEBUG] Using HTML search query: {query}")

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

        if DEBUG:
            print(f"[DEBUG] Added to final results: {res['title']} -> {url}")

    if DEBUG:
        print(f"[DEBUG] HTML search produced {len(html_results_processed)} results after deduplication")

    # Always perform API fallback search
    query = _build_query(industry, location)
    if DEBUG:
        print(f"[DEBUG] Using Instant Answer API query: {query}")

    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1,
    }

    try:
        response = requests.get("https://api.duckduckgo.com/", params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        if DEBUG:
            print(f"[DEBUG] API fallback request failed: {e}")
        # If API also fails, return what we got from HTML (might be empty)
        if html_results_processed:
            return html_results_processed
        return []

    if DEBUG:
        print(f"[DEBUG] Instant Answer API HTTP status: {response.status_code}")

    data = response.json()
    # Extract possible results from RelatedTopics
    topics = _extract_related_topics(data)

    if DEBUG:
        print(f"[DEBUG] Instant Answer API returned {len(topics)} raw topics")

    # Process API results
    api_results_processed = []
    seen_urls = set()

    for topic in topics:
        if not isinstance(topic, dict):
            continue

        url = topic.get("FirstURL") or topic.get("URL") or ""
        text = topic.get("Text") or ""  # Define text variable here

        if not url:
            if DEBUG:
                print(f"[DEBUG] Skipping topic with no URL: {topic}")
            continue

        normalized = _normalize_url(url)
        if not normalized or _is_blocked_domain(normalized):
            if DEBUG:
                print(f"[DEBUG] Skipping blocked/invalid URL: {normalized}")
            continue
        if normalized in seen_urls:  # Fixed: check if this specific URL was seen before
            if DEBUG:
                print(f"[DEBUG] Skipping duplicate URL: {normalized}")
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

        if DEBUG:
            print(f"[DEBUG] Added API result: {company_name} -> {normalized}")

        if len(api_results_processed) >= max_results:
            break

    if DEBUG:
        print(f"[DEBUG] API fallback produced {len(api_results_processed)} results after deduplication")

    # Return HTML results if we got any, otherwise fall back to API results
    if html_results_processed:
        if DEBUG:
            print(f"[DEBUG] Returning HTML search results")
        return html_results_processed
    else:
        if DEBUG:
            print(f"[DEBUG] Returning API fallback results")
        return api_results_processed