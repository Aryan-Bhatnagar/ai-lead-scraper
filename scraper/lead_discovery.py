"""
Automated lead discovery for the AI Lead Scraper.

This module discovers candidate business websites using DDGS search.
It does not scrape leads itself. Its responsibility is to find and
clean candidate URLs that can later be passed to the scraping pipeline.
"""

from typing import Dict, List
from urllib.parse import urlparse, urlunparse

from ddgs import DDGS


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
}


def build_search_query(industry: str, location: str) -> str:
    """
    Build a search query from an industry and location.
    """
    industry = industry.strip()
    location = location.strip()

    if not industry:
        raise ValueError("industry must not be empty")

    if not location:
        raise ValueError("location must not be empty")

    return f"{industry} {location}"


def normalize_url(url: str) -> str:
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


def is_blocked_domain(url: str) -> bool:
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


def discover_leads(
    industry: str,
    location: str,
    max_results: int = 20,
) -> List[Dict[str, str]]:
    """
    Discover candidate business websites.

    Returns a list containing:
        title
        url
        description
    """
    query = build_search_query(industry, location)

    if not isinstance(max_results, int) or isinstance(max_results, bool):
        raise ValueError("max_results must be an integer")

    if max_results < 1:
        raise ValueError("max_results must be greater than 0")

    results = DDGS().text(
        query,
        max_results=max_results,
    )

    discovered = []
    seen_urls = set()

    for result in results:
        if not isinstance(result, dict):
            continue

        raw_url = result.get("href", "")
        normalized_url = normalize_url(raw_url)

        if not normalized_url:
            continue

        if is_blocked_domain(normalized_url):
            continue

        if normalized_url in seen_urls:
            continue

        seen_urls.add(normalized_url)

        discovered.append(
            {
                "title": result.get("title", ""),
                "url": normalized_url,
                "description": result.get("body", ""),
            }
        )

    return discovered


if __name__ == "__main__":
    leads = discover_leads(
        industry="software companies",
        location="Chandigarh",
        max_results=10,
    )

    print(f"Discovered {len(leads)} candidate websites:\n")

    for index, lead in enumerate(leads, start=1):
        print(f"{index}. {lead['title']}")
        print(f"   URL: {lead['url']}")
        print(f"   Description: {lead['description']}")
        print()