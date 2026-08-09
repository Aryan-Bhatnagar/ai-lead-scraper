"""LeadRepository — Phase 19B.

Domain-facing repository that persists UnifiedLead and ScoredLead objects
via a pluggable LeadStore backend.  The repository handles mapping, lifecycle
assignment, and provides a rich query interface.

Typical usage
-------------
    repo = LeadRepository()  # defaults to sqlite:///data/leads_repo.db
    lead_id = repo.save(unified_lead, scored_lead)
    scored = repo.get_by_id(lead_id)
    page = repo.filter(lifecycle=LifecycleState.NEW, page=1, per_page=50)
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

from .config import DEFAULT_CONFIG, PersistenceConfig
from .lifecycle import LifecycleState, LifecycleEngine
from .models import LifecycleEvent, LeadRecord, Page
from .mappers import lead_to_record, record_to_lead
from .stores import LeadStore, StoreRegistry, default_store_registry
from .stores.base import LeadQuery
from .exceptions import DuplicateLeadError, InvalidLifecycleTransition

from scraper.discovery.model import UnifiedLead
from scraper.scoring.models import ScoredLead


class LeadRepository:
    """Central persistence layer for leads.

    Parameters
    ----------
    backend:
        Either a URI string understood by :class:`StoreRegistry` or a
        pre-configured :class:`LeadStore` instance.  When omitted, the
        default is ``sqlite:///data/leads_repo.db`` (see :func:`default_sqlite_uri`).
    config:
        Runtime knobs (page sizes, etc.).  When omitted, uses :data:`DEFAULT_CONFIG`.
    registry:
        Store registry to resolve URI strings.  Defaults to the module-level
        ``default_store_registry``.
    """

    def __init__(
        self,
        backend: str | LeadStore = "sqlite:///data/leads_repo.db",
        *,
        config: Optional[PersistenceConfig] = None,
        registry: Optional[StoreRegistry] = None,
    ) -> None:
        self.config = config or DEFAULT_CONFIG
        self.registry = registry or default_store_registry

        if isinstance(backend, LeadStore):
            self._store: LeadStore = backend
        else:
            self._store = self.registry.resolve(backend)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------
    def save(self, lead: UnifiedLead, scored: Optional[ScoredLead] = None) -> str:
        """Insert a new lead (with optional score) and return its ID.

        The lifecycle is set to ``SCORED`` if a scored lead is provided,
        otherwise ``NEW`` (unless the caller overrides via direct store
        manipulation — not recommended).
        """
        record = lead_to_record(
            lead,
            scored,
            lead_id=getattr(lead, "id", None),
        )
        return self._store.insert(record)

    def update(
        self, lead_id: str, lead: UnifiedLead, scored: Optional[ScoredLead] = None
    ) -> bool:
        """Full overwrite of an existing lead.  Returns False when missing."""
        record = lead_to_record(
            lead,
            scored,
            lead_id=lead_id,
        )
        existing = self._store.get(lead_id)
        if existing is None:
            return False
        # Preserve the original created_at timestamp.
        if "created_at" not in record or not record["created_at"]:
            record["created_at"] = existing.get("created_at")
        # The lead_to_record helper already sets updated_at to the current time.
        return self._store.update(lead_id, record)

    def merge(
        self, lead_id: str, lead: Union[UnifiedLead, ScoredLead], scored: Optional[ScoredLead] = None
    ) -> UnifiedLead:
        """Merge incoming lead with existing record (non-empty wins, union lists).

        Returns the merged UnifiedLead (without score) after persisting.
        The `lead` argument can be either a UnifiedLead or a ScoredLead.
        If it is a ScoredLead, its score is used as the incoming score unless
        an explicit `scored` argument is provided.
        """
        # If the incoming lead is a ScoredLead, extract the UnifiedLead and its score.
        if isinstance(lead, ScoredLead):
            # Use the score from the lead if no explicit score was provided.
            if scored is None:
                scored = lead
            lead = lead.lead
        existing_record = self._store.get(lead_id)
        if existing_record is None:
            # Nothing to merge — just save
            self.save(lead, scored)
            return lead

        existing_lead, existing_scored = record_to_lead(existing_record)
        # Merge logic: prefer non-empty values from incoming, but keep existing if incoming empty.
        # For lists, we union (deduplicate by value where sensible).
        merged = UnifiedLead(
            id=lead_id,  # preserve the original ID
            canonical_domain=lead.canonical_domain or existing_lead.canonical_domain,
            company_name_norm=lead.company_name_norm or existing_lead.company_name_norm,
            external_ids={**existing_lead.external_ids, **lead.external_ids},
            company_name=lead.company_name or existing_lead.company_name,
            website=lead.website or existing_lead.website,
            description=lead.description or existing_lead.description,
            industry=lead.industry or existing_lead.industry,
            location=lead.location or existing_lead.location,
            emails=list(dict.fromkeys((lead.emails or []) + (existing_lead.emails or []))),
            phones=list(dict.fromkeys((lead.phones or []) + (existing_lead.phones or []))),
            socials={**existing_lead.socials, **lead.socials},
            hourly_rate=lead.hourly_rate if lead.hourly_rate is not None else existing_lead.hourly_rate,
            skills=list(dict.fromkeys((lead.skills or []) + (existing_lead.skills or []))),
            rating=lead.rating if lead.rating is not None else existing_lead.rating,
            jobs_completed=lead.jobs_completed if lead.jobs_completed is not None else existing_lead.jobs_completed,
            maps_rating=lead.maps_rating if lead.maps_rating is not None else existing_lead.maps_rating,
            maps_review_count=lead.maps_review_count if lead.maps_review_count is not None else existing_lead.maps_review_count,
            coordinates=lead.coordinates or existing_lead.coordinates,
            business_status=lead.business_status or existing_lead.business_status,
            categories=list(dict.fromkeys((lead.categories or []) + (existing_lead.categories or []))),
            provenance=lead.provenance or existing_lead.provenance,
        )
        # Merge score: if incoming has a score, use it; otherwise keep existing.
        merged_scored = scored or existing_scored
        # Persist merged record
        record = lead_to_record(
            merged,
            merged_scored,
            lead_id=lead_id,
        )
        # Preserve created_at, lifecycle, lifecycle_updated_at from existing record
        record["created_at"] = existing_record.get("created_at")
        record["lifecycle"] = existing_record.get("lifecycle")
        record["lifecycle_updated_at"] = existing_record.get("lifecycle_updated_at")
        self._store.update(lead_id, record)
        return merged

    def delete(self, lead_id: str) -> bool:
        """Delete a lead by ID.  Returns False when missing."""
        return self._store.delete(lead_id)

    def bulk_insert(
        self, items: Iterable[UnifiedLead | ScoredLead]
    ) -> List[str]:
        """Insert many leads/scored leads.  Returns list of IDs in input order.

        ScoredLead items are persisted with lifecycle=SCORED, UnifiedLead with NEW.
        """
        records: List[LeadRecord] = []
        for item in items:
            if isinstance(item, ScoredLead):
                records.append(
                    lead_to_record(
                        item.lead,
                        item,
                        lead_id=getattr(item.lead, "id", None),
                    )
                )
            else:
                records.append(
                    lead_to_record(
                        item,
                        None,
                        lead_id=getattr(item, "id", None),
                    )
                )
        return self._store.bulk_insert(records)

    def bulk_update(
        self, items: Iterable[Tuple[str, UnifiedLead, Optional[ScoredLead]]]
    ) -> int:
        """Update many (lead_id, lead, scored) tuples.  Returns number of rows changed."""
        to_update: List[Tuple[str, LeadRecord]] = []
        for lead_id, lead, scored in items:
            record = lead_to_record(
                lead,
                scored,
                lead_id=lead_id,
            )
            # Preserve created_at from existing record
            existing = self._store.get(lead_id)
            if existing is not None:
                record["created_at"] = existing.get("created_at")
            to_update.append((lead_id, record))
        return self._store.bulk_update(to_update)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------
    def get_by_id(self, lead_id: str) -> Optional[ScoredLead]:
        """Fetch a lead by ID, returning a ScoredLead if scored, else None.

        If the lead has a score, a ScoredLead is returned; otherwise None is
        returned (the UnifiedLead is not wrapped in a ScoredLead with a null
        score).
        """
        record = self._store.get(lead_id)
        if record is None:
            return None
        lead, scored = record_to_lead(record)
        return scored  # may be None

    def get_by_domain(self, domain: str) -> Optional[ScoredLead]:
        """Fetch the first lead matching a canonical domain (case-insensitive).

        Returns None if no match is found.
        """
        # Delegates to the store's get_by_domain method.
        record = self._store.get_by_domain(domain)
        if record is None:
            return None
        lead, _ = record_to_lead(record)
        # Wrap the lead in a ScoredLead with no score (None) to match the
        # return type of get_by_id (ScoredLead | None).  The Scoredlead
        # constructor requires a score, so we use 0 and a dummy explanation.
        from scraper.scoring.models import ScoreExplanation, ScoreBreakdown

        explanation = ScoreExplanation(
            overall_score=0,
            breakdowns=[],
            quality_tier="low",
        )
        return ScoredLead(
            lead=lead,
            overall_score=0,
            explanation=explanation,
            quality_tier="low",
        )

    def search(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 50,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> Page[ScoredLead]:
        """Search company_name, website, description for the given substring (case-insensitive)."""
        lead_query = lead_query = LeadQuery(
            search_text=query,
            page=page,
            per_page=per_page,
            order_by=order_by,
            descending=descending,
        )
        records, total = self._store.find(lead_query)
        scored_leads = []
        for record in records:
            lead, scored = record_to_lead(record)
            if scored is not None:
                scored_leads.append(scored)
            else:
                # For unscored leads, return a ScoredLead with a score of 0 and
                # a default explanation so the return type is always ScoredLead.
                from scraper.scoring.models import ScoreExplanation, ScoreBreakdown

                explanation = ScoreExplanation(
                    overall_score=0,
                    breakdowns=[],
                    quality_tier="low",
                )
                scored = ScoredLead(
                    lead=lead,
                    overall_score=0,
                    explanation=explanation,
                    quality_tier="low",
                )
                scored_leads.append(scored)
        return Page(
            items=scored_leads,
            total=total,
            page=page,
            per_page=per_page,
        )

    def filter(
        self,
        *,
        lifecycle: Optional[LifecycleState] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
        quality_tier: Optional[str] = None,
        sources: Optional[List[str]] = None,
        has_email: Optional[bool] = None,
        has_website: Optional[bool] = None,
        company_name: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> Page[ScoredLead]:
        """Filter leads by the given criteria."""
        lead_query = LeadQuery(
            lifecycle=lifecycle.value if lifecycle else None,
            min_score=min_score,
            max_score=max_score,
            quality_tier=quality_tier,
            sources=sources,
            has_email=has_email,
            has_website=has_website,
            company_name=company_name,
            page=page,
            per_page=per_page,
            order_by=order_by,
            descending=descending,
        )
        records, total = self._store.find(lead_query)
        # Debug print
        print(f"DEBUG filter: lifecycle={lifecycle}, min_score={min_score}, max_score={max_score}")
        print(f"DEBUG records count={len(records)} total={total}")
        for r in records:
            print(f"  record id={r.get('id')} score={r.get('score')} lifecycle={r.get('lifecycle')}")
        scored_leads = []
        for record in records:
            lead, scored = record_to_lead(record)
            if scored is not None:
                scored_leads.append(scored)
            else:
                # Same as search: wrap unscored lead in a ScoredLead with score=0.
                from scraper.scoring.models import ScoreExplanation, ScoreBreakdown

                explanation = ScoreExplanation(
                    overall_score=0,
                    breakdowns=[],
                    quality_tier="low",
                )
                scored = ScoredLead(
                    lead=lead,
                    overall_score=0,
                    explanation=explanation,
                    quality_tier="low",
                )
                scored_leads.append(scored)
        return Page(
            items=scored_leads,
            total=total,
            page=page,
            per_page=per_page,
        )

    def pagination(
        self,
        *,
        page: int = 1,
        per_page: int = 50,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> Page[ScoredLead]:
        """Return a paginated slice of all leads (no filtering)."""
        return self.filter(
            page=page,
            per_page=per_page,
            order_by=order_by,
            descending=descending,
        )

    def count(self, **filters) -> int:
        """Return the number of matches for the given filter criteria."""
        lead_query = LeadQuery(**filters)
        return self._store.count(lead_query)

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def set_lifecycle(self, lead_id: str, state: LifecycleState, *, reason: Optional[str] = None) -> bool:
        """Set the lifecycle state of a lead (with validation). Returns True if changed."""
        # If the lead does not exist, return False.
        if self._store.get(lead_id) is None:
            return False
        current_record = self._store.get(lead_id)
        current_lifecycle = current_record.get("lifecycle")
        try:
            LifecycleEngine.validate(current_lifecycle, state)
        except InvalidLifecycleTransition:
            return False
        _, changed = self._store.set_lifecycle(lead_id, state.value, reason)
        return changed

    def advance_lifecycle(self, lead_id: str, *, reason: Optional[str] = None) -> bool:
        """Advance to the canonical next state (see LifecycleEngine.next_state)."""
        current = self._store.get(lead_id)
        if current is None:
            return False
        current_lifecycle = LifecycleState(current.get("lifecycle", LifecycleState.NEW.value))
        try:
            next_state = LifecycleEngine.next_state(current_lifecycle)
        except InvalidLifecycleTransition:
            return False
        return self.set_lifecycle(lead_id, next_state, reason=reason)

    def list_by_state(self, state: LifecycleState, **page_kwargs) -> Page[ScoredLead]:
        """Convenience for filter(lifecycle=state, **page_kwargs)."""
        return self.filter(lifecycle=state, **page_kwargs)

    def get_lifecycle_history(self, lead_id: str) -> List[LifecycleEvent]:
        """Return the lifecycle audit trail for a lead."""
        history_dicts = self._store.get_lifecycle_history(lead_id)
        return [LifecycleEvent(**d) for d in history_dicts]

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def persist_orchestrator_summary(self, summary) -> None:
        """Persist the results of a DiscoveryRunSummary (called by orchestrator).

        This method is not part of the core repository interface but is a helper
        for the DiscoveryOrchestrator to persist its results.
        """
        if hasattr(summary, "scored_leads"):
            leads = getattr(summary, "scored_leads", [])
            if leads:
                self.bulk_insert(leads)

    def close(self) -> None:
        """Release any resources held by the underlying store."""
        self._store.close()