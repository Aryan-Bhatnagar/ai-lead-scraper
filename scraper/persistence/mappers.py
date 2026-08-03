"""Domain mappers — Phase 19B.

Pure functions that convert between discovery-domain objects
(``UnifiedLead`` + optional ``ScoredLead``) and the storage-neutral
``LeadRecord`` dict consumed by every LeadStore.  No SQL, no I/O, no
back-references into provider/scoring modules.

Both directions are total: fields missing on one side are filled with safe
defaults on the other so records survive schema drift gracefully.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from scraper.discovery.model import LocationData, Provenance, UnifiedLead
from scraper.scoring.models import ScoreBreakdown, ScoreExplanation, ScoredLead

from .lifecycle import LifecycleState
from .models import LeadRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_domain(website: Optional[str]) -> Optional[str]:
    if not website:
        return None
    # naive netloc extraction — consistent with dedup's _extract_domain
    url = website.lower().split("//")[-1]
    return url.split("/")[0] or None


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if isinstance(dt, datetime) else None


def _loads(raw: Any):
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw
    return raw


# ---------------------------------------------------------------------------
# Domain → record
# ---------------------------------------------------------------------------

def lead_to_record(
    lead: UnifiedLead | ScoredLead,
    scored: Optional[ScoredLead] = None,
    *,
    lead_id: Optional[str] = None,
    lifecycle: LifecycleState | str | None = None,
    lifecycle_updated_at: Optional[str] = None,
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> LeadRecord:
    """Flatten a UnifiedLead (+optional ScoredLead) into a LeadRecord dict.

    Complex fields (lists/dicts) are stored as JSON strings so the record is
    backend-agnostic — a column of type TEXT works everywhere.
    """
    # If the first argument is a ScoredLead, extract the lead and use it as the scored lead
    if isinstance(lead, ScoredLead):
        scored = lead
        lead = lead.lead
    now = _utc_now_iso()
    # Determine the effective lead ID: use the provided lead_id, or fall back to the lead's id attribute,
    # or generate a new UUID if neither is available.
    effective_lead_id = lead_id
    if effective_lead_id is None:
        effective_lead_id = getattr(lead, "id", None)
    final_id = effective_lead_id or uuid.uuid4().hex
    loc: LocationData = lead.location or LocationData()
    prov: Provenance = lead.provenance or Provenance()
    score = scored.overall_score if scored else None
    tier = (scored.quality_tier if scored else None) or "low"
    explanation = None
    if scored and scored.explanation:
        explanation = [
            {
                "feature": b.feature, "label": b.label, "weight": b.weight,
                "quality_ratio": b.quality_ratio, "contribution": b.contribution,
                "detail": b.detail,
            }
            for b in scored.explanation.breakdowns
        ]
    provenance = {
        "source": prov.source,
        "source_url": prov.source_url,
        "discovered_at": _iso(prov.discovered_at),
        "discovery_query": prov.discovery_query,
        "confidence": prov.confidence,
        "raw_ref": prov.raw_ref,
    }

    # Determine the effective lifecycle
    if lifecycle is not None:
        if isinstance(lifecycle, LifecycleState):
            effective_lifecycle = lifecycle
        else:
            # Assume it's a string
            effective_lifecycle = LifecycleState(lifecycle.upper())
    else:
        # Use the lead's lifecycle if set, otherwise fall back to convention:
        # scored leads -> SCORED, raw leads -> NEW.
        lead_lifecycle = getattr(lead, 'lifecycle', None)
        if lead_lifecycle is not None:
            if isinstance(lead_lifecycle, LifecycleState):
                effective_lifecycle = lead_lifecycle
            else:
                effective_lifecycle = LifecycleState(lead_lifecycle.upper())
        else:
            effective_lifecycle = LifecycleState.SCORED if scored else LifecycleState.NEW

    return {
        "id": final_id,
        "canonical_domain": lead.canonical_domain or _canonical_domain(lead.website),
        "company_name_norm": lead.company_name_norm,
        "external_ids_json": json.dumps(lead.external_ids or {}),
        "company_name": lead.company_name,
        "website": lead.website,
        "description": lead.description,
        "industry": lead.industry,
        "location": loc,
        "emails_json": json.dumps(lead.emails or []),
        "phones_json": json.dumps(lead.phones or []),
        "socials_json": json.dumps(lead.socials or {}),
        "hourly_rate": lead.hourly_rate,
        "skills_json": json.dumps(lead.skills or []),
        "rating": lead.rating,
        "jobs_completed": lead.jobs_completed,
        "maps_rating": lead.maps_rating,
        "maps_review_count": lead.maps_review_count,
        "coordinates_json": json.dumps(lead.coordinates) if lead.coordinates else None,
        "business_status": lead.business_status,
        "categories_json": json.dumps(lead.categories or []),
        "provenance_json": json.dumps(provenance),
        "score": score,
        "quality_tier": tier,
        "explanation_json": json.dumps(explanation) if explanation else None,
        "lifecycle": effective_lifecycle.value,
        "lifecycle_updated_at": lifecycle_updated_at,
        "created_at": created_at or now,
        "updated_at": updated_at or now,
    }


# ---------------------------------------------------------------------------
# Record → domain
# ---------------------------------------------------------------------------

def record_to_lead(record: LeadRecord) -> Tuple[UnifiedLead, Optional[ScoredLead]]:
    """Rebuild (UnifiedLead, ScoredLead|None) from a LeadRecord dict.

    ``ScoredLead`` is only reconstructed when the record actually carries a
    score — raw leads stored before scoring return ``None``.
    """
    loc = LocationData(
        city=record.get("city"),
        region=record.get("region"),
        country=record.get("country"),
        address=record.get("address"),
    )
    prov_raw = _loads(record.get("provenance_json")) or {}
    discovered_at = prov_raw.get("discovered_at")
    prov = Provenance(
        source=prov_raw.get("source", ""),
        source_url=prov_raw.get("source_url"),
        discovered_at=(
            datetime.fromisoformat(discovered_at) if discovered_at else None
        ),
        discovery_query=prov_raw.get("discovery_query"),
        confidence=prov_raw.get("confidence", 1.0),
        raw_ref=prov_raw.get("raw_ref"),
    )

    lifecycle_str = record.get("lifecycle")
    lifecycle = LifecycleState(lifecycle_str) if lifecycle_str else None
    lead = UnifiedLead(
        id=record.get("id"),
        canonical_domain=record.get("canonical_domain"),
        company_name_norm=record.get("company_name_norm"),
        external_ids=_loads(record.get("external_ids_json")) or {},
        company_name=record.get("company_name"),
        website=record.get("website"),
        description=record.get("description"),
        industry=record.get("industry"),
        location=loc,
        emails=_loads(record.get("emails_json")) or [],
        phones=_loads(record.get("phones_json")) or [],
        socials=_loads(record.get("socials_json")) or {},
        hourly_rate=record.get("hourly_rate"),
        skills=_loads(record.get("skills_json")) or [],
        rating=record.get("rating"),
        jobs_completed=record.get("jobs_completed"),
        maps_rating=record.get("maps_rating"),
        maps_review_count=record.get("maps_review_count"),
        coordinates=_loads(record.get("coordinates_json")),
        business_status=record.get("business_status"),
        categories=_loads(record.get("categories_json")) or [],
        provenance=prov,
        lifecycle=lifecycle,
    )

    score = record.get("score")
    if score is None:
        return lead, None

    breakdown_raw = _loads(record.get("explanation_json")) or []
    explanation = ScoreExplanation(
        overall_score=int(score),
        breakdowns=[
            ScoreBreakdown(
                feature=b.get("feature", ""),
                label=b.get("label", ""),
                weight=float(b.get("weight", 0.0)),
                quality_ratio=float(b.get("quality_ratio", 0.0)),
                contribution=float(b.get("contribution", 0.0)),
                detail=b.get("detail", ""),
            )
            for b in breakdown_raw
        ],
        quality_tier=record.get("quality_tier") or "low",
    )
    scored = ScoredLead(
        lead=lead,
        overall_score=int(score),
        explanation=explanation,
        quality_tier=record.get("quality_tier") or "low",
    )
    return lead, scored
