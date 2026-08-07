"""
Google Maps Import Adapter.

Maps Google Maps discovery results to UnifiedLead model.
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseImportAdapter, ImportResult
from ..discovery.model import UnifiedLead, LocationData, Provenance


class GoogleMapsImportAdapter(BaseImportAdapter):
    """Import adapter for Google Maps JSON export files."""

    @property
    def source_name(self) -> str:
        return "Google Maps"

    @property
    def supported_extensions(self) -> List[str]:
        return [".json"]

    def parse_file(self, file_path: str) -> ImportResult:
        """Parse Google Maps JSON file."""
        result = ImportResult()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            result.add_error(f"Failed to parse JSON: {e}")
            return result

        # Google Maps exports can be an array or an object with a data array
        records = []
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            for key in ["data", "results", "places", "leads"]:
                if key in data and isinstance(data[key], list):
                    records = data[key]
                    break

        if not records:
            result.add_error("No records found in Google Maps JSON")
            return result

        seen_place_ids = set()
        seen_websites = set()

        for record in records:
            try:
                lead = self.map_record(record)

                # Deduplication
                place_id = record.get("place_id", "").strip()
                website = lead.website.lower() if lead.website else None

                if place_id and place_id in seen_place_ids:
                    result.add_duplicate()
                    continue
                if website and website in seen_websites:
                    result.add_duplicate()
                    continue

                if place_id:
                    seen_place_ids.add(place_id)
                if website:
                    seen_websites.add(website)

                result.add_lead(lead)

            except Exception as e:
                result.add_error(f"Failed to map record: {e}")

        return result

    def map_record(self, record: Dict[str, Any]) -> UnifiedLead:
        """Map a single Google Maps record to UnifiedLead."""
        # Extract basic info
        name = record.get("name", "").strip()
        place_id = record.get("place_id", "").strip()
        website = record.get("website", "").strip()
        formatted_address = record.get("formatted_address", "").strip()
        vicinity = record.get("vicinity", "").strip()

        # Rating and reviews
        rating = record.get("rating")
        user_ratings_total = record.get("user_ratings_total", 0)

        # Types/categories
        types = record.get("types", [])

        # Geometry/location
        geometry = record.get("geometry", {})
        location_data = geometry.get("location", {})
        lat = location_data.get("lat")
        lng = location_data.get("lng")

        # Address components
        address_components = record.get("address_components", [])
        city = ""
        country = ""
        region = ""
        for component in address_components:
            component_types = component.get("types", [])
            if "locality" in component_types:
                city = component.get("long_name", "").strip()
            elif "administrative_area_level_1" in component_types:
                region = component.get("long_name", "").strip()
            elif "country" in component_types:
                country = component.get("long_name", "").strip()

        # Build location
        location = self._create_location(
            city=city,
            country=country,
            region=region,
            address=formatted_address or vicinity,
        )
        location.latitude = lat
        location.longitude = lng

        # Industry from types
        industry = ""
        if types:
            # Filter out generic types
            business_types = [t for t in types if t not in ["point_of_interest", "establishment"]]
            industry = ", ".join(business_types[:3])

        # Source URL - Google Maps place URL
        source_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else f"googlemaps://{name}"

        # Provenance
        provenance = self._create_provenance(
            source_url=source_url,
            raw_ref=f"google_maps:{place_id}",
        )

        # Social links - check for website
        socials = {}
        if website:
            socials["website"] = website

        # Build UnifiedLead
        lead = UnifiedLead(
            company_name=name,
            website=website,
            description="",
            industry=industry,
            location=location,
            provenance=provenance,
            emails=[],
            phones=[],
            socials=socials,
        )

        # Store Google Maps specific metadata
        lead.metadata["google_rating"] = rating
        lead.metadata["maps_review_count"] = user_ratings_total
        lead.metadata["google_place_id"] = place_id
        lead.metadata["google_types"] = types
        lead.metadata["google_raw"] = record

        return lead