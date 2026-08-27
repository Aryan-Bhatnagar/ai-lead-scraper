"""
Phase 12F: Standalone Email Extractor.

Provides deterministic email extraction from business websites without
LLM overhead.  Reuses existing helpers from scraper.scrape_leads for
HTML fetching, page discovery, contact harvesting, and email validation.

No ScrapeGraphAI, no Ollama — pure HTML parsing with full provenance.
"""

from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urlparse

from .scrape_leads import (
    harvest_contacts,
    select_email,
    fetch_html,
    discover_pages,
)


# ---------------------------------------------------------------------------
# URL normalization (same logic as lead_enrichment._normalize_url_for_dedup)
# ---------------------------------------------------------------------------
def _normalize_url_for_dedup(url: str) -> str:
    """Normalize a URL for deduplication: lowercase, remove trailing slash,
    strip www prefix, remove path/params/fragment."""
    if not url:
        return ""
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if host.startswith("www."):
            host = host[4:]
        normalized = f"{parsed.scheme}://{host}"
        if parsed.port:
            normalized += f":{parsed.port}"
        return normalized.rstrip("/")
    except Exception:
        return url.lower().rstrip("/")


# ---------------------------------------------------------------------------
# Core extraction functions
# ---------------------------------------------------------------------------
def extract_emails_from_html(
    html: str, source_page: str = ""
) -> Dict[str, Any]:
    """Extract the best email from raw HTML using deterministic harvesting.

    Reuses harvest_contacts() and select_email() from scrape_leads — no
    LLM involved.

    Parameters
    ----------
    html:
        Raw HTML content to search.
    source_page:
        URL of the page the HTML was fetched from (for provenance).

    Returns
    -------
    dict
        {
            "email": str,              # best email or ""
            "email_source_page": str,  # URL where it was found
            "email_source_type": str,  # "mailto" or "visible_text"
            "all_emails": list,        # full list of candidate dicts
        }
    """
    harvested = harvest_contacts(html, source_page=source_page)
    candidates = harvested.get("emails", [])

    best = select_email(candidates)

    if best:
        return {
            "email": best["value"],
            "email_source_page": best.get("source_page", source_page),
            "email_source_type": best.get("source_type", ""),
            "all_emails": candidates,
        }

    return {
        "email": "",
        "email_source_page": "",
        "email_source_type": "",
        "all_emails": candidates,
    }


def extract_emails_from_url(url: str) -> Dict[str, Any]:
    """Fetch a URL and extract the best email from its HTML.

    Parameters
    ----------
    url:
        The website URL to fetch and parse.

    Returns
    -------
    dict
        Same as extract_emails_from_html plus:
            "url": str,
            "pages_checked": list[str],
    """
    try:
        html = fetch_html(url)
        result = extract_emails_from_html(html, source_page=url)
    except Exception as e:
        return {
            "url": url,
            "email": "",
            "email_source_page": "",
            "email_source_type": "",
            "pages_checked": [],
            "_error": f"Failed to fetch {url}: {e}",
        }

    result["url"] = url
    result.setdefault("pages_checked", [url])
    return result


def enrich_email_for_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
    """Find an email for an existing lead by scraping its website.

    Attempts the homepage first; if no email is found, discovers internal
    pages (contact, about, team) and scrapes up to 3 of them.

    Parameters
    ----------
    lead:
        A lead dict that must contain a ``website`` key.

    Returns
    -------
    dict
        A copy of the original lead with ``email``, ``email_source_page``,
        ``email_source_type``, and ``pages_checked`` added/updated.
        Original lead fields are preserved.
    """
    website = lead.get("website", "")
    if not website or not isinstance(website, str):
        return {
            **lead,
            "email": "",
            "email_source_page": "",
            "email_source_type": "",
            "pages_checked": [],
        }

    result = dict(lead)
    pages_checked: List[str] = []

    # Try the homepage
    try:
        html = fetch_html(website)
    except Exception:
        return {
            **result,
            "email": "",
            "email_source_page": "",
            "email_source_type": "",
            "pages_checked": [],
        }

    pages_checked.append(website)
    homepage_result = extract_emails_from_html(html, source_page=website)

    if homepage_result["email"]:
        result["email"] = homepage_result["email"]
        result["email_source_page"] = homepage_result["email_source_page"]
        result["email_source_type"] = homepage_result["email_source_type"]
        result["pages_checked"] = pages_checked
        return result

    # Deep Contact Crawler: No email on homepage — construct standard contact paths + discover internal pages
    from urllib.parse import urljoin
    standard_paths = ["/contact", "/contact-us", "/about-us", "/about"]
    candidate_urls = [urljoin(website, path) for path in standard_paths]
    
    discovered_urls = discover_pages(website, html)
    for u in discovered_urls:
        if u not in candidate_urls and u != website:
            candidate_urls.append(u)

    for page_url in candidate_urls:
        if page_url in pages_checked:
            continue
        try:
            page_html = fetch_html(page_url)
        except Exception:
            continue

        pages_checked.append(page_url)
        page_result = extract_emails_from_html(page_html, source_page=page_url)

        if page_result["email"]:
            result["email"] = page_result["email"]
            result["email_source_page"] = page_result["email_source_page"]
            result["email_source_type"] = page_result["email_source_type"]
            result["pages_checked"] = pages_checked
            return result

    # No email found on any page
    result["email"] = ""
    result["email_source_page"] = ""
    result["email_source_type"] = ""
    result["pages_checked"] = pages_checked
    return result


from concurrent.futures import ThreadPoolExecutor, as_completed

def extract_emails_batch(
    leads: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Extract emails for a batch of leads in parallel, deduplicating by website.

    Parameters
    ----------
    leads:
        List of lead dicts, each expected to have a ``website`` key.

    Returns
    -------
    list[dict]
        Enriched lead dicts with email fields populated where possible.
        Duplicate websites within the batch are fetched only once.
    """
    enriched_cache: Dict[str, Dict[str, Any]] = {}
    unique_websites: Dict[str, Dict[str, Any]] = {}

    for lead in leads:
        if not isinstance(lead, dict):
            continue
        website = lead.get("website")
        if website and isinstance(website, str):
            norm_website = _normalize_url_for_dedup(website)
            if norm_website and norm_website not in unique_websites:
                unique_websites[norm_website] = lead

    # Fetch unique websites in parallel using ThreadPoolExecutor
    if unique_websites:
        with ThreadPoolExecutor(max_workers=min(8, len(unique_websites))) as executor:
            future_to_norm = {
                executor.submit(enrich_email_for_lead, sample_lead): norm_url
                for norm_url, sample_lead in unique_websites.items()
            }
            for future in as_completed(future_to_norm):
                norm_url = future_to_norm[future]
                try:
                    enriched_cache[norm_url] = future.result()
                except Exception:
                    enriched_cache[norm_url] = {
                        "email": "", "email_source_page": "", "email_source_type": "", "pages_checked": []
                    }

    results: List[Dict[str, Any]] = []
    for lead in leads:
        if not isinstance(lead, dict):
            continue
        website = lead.get("website")
        if not website or not isinstance(website, str):
            results.append({**lead})
            continue

        norm_website = _normalize_url_for_dedup(website)
        enriched_data = enriched_cache.get(norm_website, {})

        # Merge: preserve original lead fields, overlay email fields
        merged = dict(lead)
        for field in ("email", "email_source_page", "email_source_type", "pages_checked"):
            merged[field] = enriched_data.get(field, "")
        if "_error" in enriched_data:
            merged["_error"] = enriched_data["_error"]

        results.append(merged)

    return results
