"""
Google Places Import Adapter.

Maps Google Places JSON export files to UnifiedLead model.
Handles all available fields from Google Places API.
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseImportAdapter, ImportResult
from ..discovery.model import UnifiedLead, LocationData, Provenance


class GooglePlacesImportAdapter(BaseImportAdapter):
    """Import adapter for Google Places JSON export files."""

    @property
    def source_name(self) -> str:
        return "Google Places"

    @property
    def supported_extensions(self) -> List[str]:
        return [".json"]

    def parse_file(self, file_path: str) -> ImportResult:
        """Parse Google Places JSON file."""
        result = ImportResult()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            result.add_error(f"Failed to parse JSON: {e}")
            return result

        # Google Places exports are typically arrays
        records = []
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            # Try common keys for the data array
            for key in ["data", "results", "places", "leads"]:
                if key in data and isinstance(data[key], list):
                    records = data[key]
                    break

        if not records:
            result.add_error("No records found in Google Places JSON")
            return result

        seen_place_ids = set()
        seen_websites = set()
        seen_phones = set()

        for record in records:
            try:
                lead = self.map_record(record)

                # Deduplication using multiple keys
                place_id = record.get("placeId", "").strip()
                website = lead.website.lower() if lead.website else None
                phone = lead.phones[0].lower() if lead.phones else None

                is_duplicate = False
                if place_id and place_id in seen_place_ids:
                    is_duplicate = True
                if website and website in seen_websites:
                    is_duplicate = True
                if phone and phone in seen_phones:
                    is_duplicate = True

                if is_duplicate:
                    result.add_duplicate()
                    continue

                if place_id:
                    seen_place_ids.add(place_id)
                if website:
                    seen_websites.add(website)
                if phone:
                    seen_phones.add(phone)

                result.add_lead(lead)

            except Exception as e:
                result.add_error(f"Failed to map record: {e}")

        return result

    def _safe_strip(self, value: Any, default: str = "") -> str:
        """Safely strip a value, handling None and non-string types."""
        if value is None:
            return default
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    def map_record(self, record: Dict[str, Any]) -> UnifiedLead:
        """Map a single Google Places record to UnifiedLead."""
        # Extract basic info
        name = self._safe_strip(record.get("title"))
        place_id = self._safe_strip(record.get("placeId"))
        website = self._safe_strip(record.get("website"))
        description = self._safe_strip(record.get("description"))

        # Contact info
        phone = self._safe_strip(record.get("phone"))
        phone_unformatted = self._safe_strip(record.get("phoneUnformatted"))

        # Address components
        address = self._safe_strip(record.get("address"))
        neighborhood = self._safe_strip(record.get("neighborhood"))
        street = self._safe_strip(record.get("street"))
        city = self._safe_strip(record.get("city"))
        postal_code = self._safe_strip(record.get("postalCode"))
        state = self._safe_strip(record.get("state"))
        country_code = self._safe_strip(record.get("countryCode"))

        # Rating and reviews
        rating = record.get("totalScore")
        reviews_count = record.get("reviewsCount")

        # Categories
        category_name = self._safe_strip(record.get("categoryName"))
        categories = record.get("categories", [])
        if not isinstance(categories, list):
            categories = [category_name] if category_name else []

        # Location/coordinates
        location_data = record.get("location", {})
        lat = location_data.get("lat")
        lng = location_data.get("lng")

        # Opening hours
        opening_hours = record.get("openingHours", [])
        hours_str = ""
        if opening_hours and isinstance(opening_hours, list):
            hours_parts = []
            for day_info in opening_hours:
                day = self._safe_strip(day_info.get("day"))
                hours = self._safe_strip(day_info.get("hours"))
                if day and hours:
                    hours_parts.append(f"{day}: {hours}")
            hours_str = "; ".join(hours_parts)

        # Additional info
        additional_info = record.get("additionalInfo", {})
        permanently_closed = record.get("permanentlyClosed", False)
        temporarily_closed = record.get("temporarilyClosed", False)

        # Images
        image_url = self._safe_strip(record.get("imageUrl"))
        images_count = record.get("imagesCount", 0)

        # URL references
        google_maps_url = self._safe_strip(record.get("url"))
        search_page_url = self._safe_strip(record.get("searchPageUrl"))

        # Build location
        location = self._create_location(
            city=city,
            country=country_code,
            region=state,
            address=address or street or neighborhood,
        )
        if lat is not None and lng is not None:
            location.latitude = lat
            location.longitude = lng

        # Industry from categories
        industry = ""
        if categories:
            business_categories = [c for c in categories if c not in ["point_of_interest", "establishment"]]
            industry = ", ".join(business_categories[:3])

        # Source URL - Google Maps place URL
        source_url = google_maps_url or (f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else f"googlemaps://{name}")

        # Provenance
        provenance = self._create_provenance(
            source_url=source_url,
            raw_ref=f"google_places:{place_id}",
        )
        provenance.discovery_query = {
            "industry": industry,
            "location": f"{city}, {state}, {country_code}",
            "category": category_name
        }

        # Social links - check for website
        socials = {}
        if website:
            socials["website"] = website
        if google_maps_url:
            socials["google_maps"] = google_maps_url

        # Build UnifiedLead
        lead = UnifiedLead(
            company_name=name,
            website=website,
            description=description,
            industry=industry,
            location=location,
            provenance=provenance,
            emails=[],  # Google Places doesn't typically provide emails
            phones=[phone] if phone else [],
            socials=socials,
        )

        # Store Google Places specific metadata
        lead.metadata["google_rating"] = rating
        lead.metadata["maps_review_count"] = reviews_count
        lead.metadata["google_place_id"] = place_id
        lead.metadata["google_categories"] = categories
        lead.metadata["google_category_name"] = category_name
        lead.metadata["opening_hours"] = hours_str
        lead.metadata["opening_hours_raw"] = opening_hours
        lead.metadata["additional_info"] = additional_info
        lead.metadata["permanently_closed"] = permanently_closed
        lead.metadata["temporarily_closed"] = temporarily_closed
        lead.metadata["images_count"] = images_count
        lead.metadata["image_url"] = image_url
        lead.metadata["postal_code"] = postal_code
        lead.metadata["neighborhood"] = neighborhood
        lead.metadata["search_page_url"] = search_page_url
        lead.metadata["search_string"] = record.get("searchString", "")
        lead.metadata["language"] = record.get("language", "")
        lead.metadata["rank"] = record.get("rank")
        lead.metadata["is_advertisement"] = record.get("isAdvertisement", False)
        lead.metadata["fid"] = record.get("fid", "")
        lead.metadata["cid"] = record.get("cid", "")
        lead.metadata["kgmid"] = record.get("kgmid", "")
        lead.metadata["google_raw"] = record

        # Set coordinates on lead
        if lat is not None and lng is not None:
            lead.coordinates = {"lat": lat, "lng": lng}

        # Set business status
        if permanently_closed:
            lead.business_status = "CLOSED_PERMANENTLY"
        elif temporarily_closed:
            lead.business_status = "CLOSED_TEMPORARILY"
        else:
            lead.business_status = "OPERATIONAL"

        # Set Google Maps fields
        lead.maps_rating = rating
        lead.maps_review_count = reviews_count

        return lead


# Register the adapter with the default registry
def register_google_places_adapter():
    """Register the Google Places import adapter."""
    from .registry import default_registry
    default_registry.register(GooglePlacesImportAdapter())


# Auto-register on module import
register_google_places_adapter()