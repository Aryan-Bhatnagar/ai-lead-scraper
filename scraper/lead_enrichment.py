"""
Phase 12C: Lead Enrichment using ScrapeGraphAI.

Provides functions to enrich lead data with information scraped from a business website.
Reuses existing ScrapeGraphAI configuration and scraping logic from scraper.scrape_leads.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Import the existing scraping functions and configuration from scrape_leads.py
from .scrape_leads import (
    scrape_site,
    LEAD_FIELDS,
    clean_lead,
    build_lead,
    harvest_contacts,
    EMAIL_REGEX,
    valid_email,
    valid_phone,
    normalize_company_name,
    valid_contact_name,
    split_contact_role,
    looks_like_role,
    same_company_domain,
    canonical_website,
)


def _normalize_url_for_dedup(url: str) -> str:
    """Normalize a URL for deduplication: lowercase, remove trailing slash, remove www."""
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
        # Reconstruct without port, params, query, fragment
        normalized = f"{parsed.scheme}://{host}"
        if parsed.port:
            normalized += f":{parsed.port}"
        # For deduplication, we want the base website (no path, params, etc.)
        return normalized.rstrip("/")
    except Exception:
        return url.lower().rstrip("/")


def enrich_lead(
    website: str,
    company_name: Optional[str] = None,
    industry: Optional[str] = None,
    location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enrich a lead by scraping its website for business/contact information.

    Args:
        website: The business website URL (required).
        company_name: Optional company name from discovery (may be used to fill gaps).
        industry: Optional industry from discovery.
        location: Optional location from discovery.

    Returns:
        A dictionary containing the lead fields (as per LEAD_FIELDS) and an optional
        '_error' key if scraping failed. Fields not found will be empty strings.
        The dictionary does NOT include the optional discovery parameters; merging
        with discovery data should be done by the caller.
    """
    # Normalize website to base URL (remove path, params, fragment, etc.) for scraping
    # This ensures we scrape the base website and avoid duplicate scraping of same site.
    base_website = _normalize_url_for_dedup(website)
    if not base_website:
        # If normalization fails, fall back to original website
        base_website = website

    # Initialize result with empty lead fields
    result: Dict[str, Any] = {field: "" for field in LEAD_FIELDS}
    error: Optional[str] = None

    try:
        # Use the existing scrape_site function which returns a lead dict in the same format
        # as the scraper's CSV output (including extra fields like _provenance, etc.)
        scraped_lead = scrape_site(base_website)
        # Extract only the lead fields we care about (the LEAD_FIELDS)
        for field in LEAD_FIELDS:
            result[field] = scraped_lead.get(field, "")
        # If scrape_site returns an error status, we might want to capture it.
        # The scrape_site function doesn't return an error status directly; it raises exceptions.
        # So if we get here without exception, we consider it successful.
    except Exception as e:
        # Scraping failed
        error = f"Failed to scrape {base_website}: {e}"
        # Leave result fields as empty strings

    # If we have an error, we can return it in the result dictionary under a special key
    if error:
        result["_error"] = error

    # Note: We do NOT merge the optional discovery parameters (company_name, industry, location)
    # into the result here. The caller (enrich_leads or the endpoint) should merge
    # discovery data with enriched data, preferring non-empty discovery data.
    return result


def enrich_leads(leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich a batch of leads by scraping their websites.

    Args:
        leads: A list of lead dictionaries, each expected to have a 'website' key.
               May also contain other keys (like company_name, industry, location) from discovery.

    Returns:
        A list of dictionaries, each being the enriched lead data merged with the original
        discovery data. The merge rules:
          - For each lead field, if the discovery data provides a non-empty value, use it.
          - Otherwise, use the enriched value (which may be empty).
          - The original discovery fields (company_name, industry, location) are preserved
            in the output under the same keys.
        If a lead fails to enrich, the enriched fields will be empty and an '_error' key
        will be present in the returned dictionary for that lead.
        Duplicate websites within the batch are scraped only once (cached).
    """
    # Cache for enriched results by normalized website to avoid duplicate scraping in the same batch
    enriched_cache: Dict[str, Dict[str, Any]] = {}
    enriched_leads: List[Dict[str, Any]] = []

    for lead in leads:
        if not isinstance(lead, dict):
            # Skip invalid entries
            continue

        website = lead.get("website")
        if not website or not isinstance(website, str):
            # No website to enrich, just pass through the lead as-is (no enrichment)
            enriched_leads.append(lead)
            continue

        # Normalize website for deduplication within this batch
        norm_website = _normalize_url_for_dedup(website)

        # Check if we have already enriched this website in the current batch
        if norm_website in enriched_cache:
            enriched_data = enriched_cache[norm_website]
        else:
            # Enrich the lead (this will scrape the website)
            enriched_data = enrich_lead(
                website=website,
                company_name=lead.get("company_name"),
                industry=lead.get("industry"),
                location=lead.get("location"),
            )
            # Cache the enriched data for this normalized website
            enriched_cache[norm_website] = enriched_data

        # Merge discovery data with enriched data, preferring non-empty discovery data
        merged_lead: Dict[str, Any] = {}
        # First, copy all discovery data (lead) into merged_lead
        for key, value in lead.items():
            merged_lead[key] = value

        # Then, for each lead field, apply merge rules:
        #   - For website: prefer enrichment if non-empty, else discovery
        #   - For all other fields: prefer discovery if non-empty, else enrichment
        for field in LEAD_FIELDS:
            discovery_value = lead.get(field, "")
            enriched_value = enriched_data.get(field, "")
            if field == "website":
                # For website, prefer enrichment if non-empty, else discovery
                if enriched_value:
                    # DEBUG
                    # print(f"DEBUG: Using enriched website: {enriched_value} for discovery {discovery_value}")
                    merged_lead[field] = enriched_value
                else:
                    # DEBUG
                    # print(f"DEBUG: Using discovery website: {discovery_value} because enriched_value is empty: '{enriched_value}'")
                    merged_lead[field] = discovery_value
            else:
                # For all other fields, prefer discovery if non-empty, else enrichment
                if discovery_value:
                    # DEBUG
                    # print(f"DEBUG: Using discovery {field}: {discovery_value}")
                    merged_lead[field] = discovery_value
                else:
                    # DEBUG
                    # print(f"DEBUG: Using enriched {field}: {enriched_value}")
                    merged_lead[field] = enriched_value

        # Preserve any error from enrichment (if present) in the merged lead
        if "_error" in enriched_data:
            merged_lead["_error"] = enriched_data["_error"]

        enriched_leads.append(merged_lead)

    return enriched_leads