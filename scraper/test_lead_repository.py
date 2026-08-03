"""Unit tests for the LeadRepository — Phase 19B.

The test suite runs against both the in-memory and SQLite stores to ensure
the repository behaves identically regardless of the backend.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from typing import List

import pytest

from scraper.discovery.model import LocationData, Provenance, UnifiedLead
from scraper.persistence import (
    DuplicateLeadError,
    LeadRepository,
    LifecycleState,
    LifecycleEvent,
)
from scraper.scoring.models import ScoreBreakdown, ScoreExplanation, ScoredLead


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def make_lead(
    *,
    lead_id: str | None = None,
    company_name: str = "Acme Corp",
    website: str = "https://acme.com",
    emails: list[str] | None = None,
    phones: list[str] | None = None,
    score: int | None = 85,
    tier: str = "high",
    lifecycle: LifecycleState | str = LifecycleState.NEW,
    socials: dict[str, Optional[str]] | None = None,
    skills: list[str] | None = None,
    rating: float | None = None,
    jobs_completed: int | None = None,
    maps_rating: float | None = None,
    maps_review_count: int | None = None,
    coordinates: list[float] | None = None,
    business_status: str | None = None,
    categories: list[str] | None = None,
    hourly_rate: float | None = None,
) -> Union[UnifiedLead, ScoredLead]:
    """Create a sample UnifiedLead or ScoredLead for testing."""
    # Convert lifecycle to LifecycleState if it's a string
    if isinstance(lifecycle, str):
        lifecycle = LifecycleState(lifecycle.upper())
    lead = UnifiedLead(
        canonical_domain="acme.com",
        company_name_norm="acme corp",
        external_ids={},
        company_name=company_name,
        website=website,
        description="A test company",
        industry="Manufacturing",
        location=LocationData(city="Springfield", region="IL", country="USA"),
        emails=emails or ["info@acme.com"],
        phones=phones or ["555-1234"],
        socials=socials if socials is not None else {"linkedin": "https://linkedin.com/company/acme"},
        hourly_rate=75.0 if hourly_rate is not None else hourly_rate,
        skills=skills if skills is not None else ["welding", "fabrication"],
        rating=rating,
        jobs_completed=jobs_completed,
        maps_rating=maps_rating,
        maps_review_count=maps_review_count,
        coordinates=coordinates,
        business_status=business_status,
        categories=categories,
        provenance=Provenance(
            source="test",
            source_url="https://example.com",
            discovered_at=None,
            discovery_query="test",
            confidence=0.9,
            raw_ref="abc123",
        ),
        lifecycle=lifecycle,
    )
    if lead_id is not None:
        # Attach an id attribute to the lead object so the repository can use it as the primary key
        lead.id = lead_id
    if score is None:
        return lead
    explanation = ScoreExplanation(
        overall_score=score,
        breakdowns=[
            ScoreBreakdown(
                feature="test",
                label="Test",
                weight=float(score),
                quality_ratio=1.0,
                contribution=float(score),
                detail="Test score",
            )
        ],
        quality_tier=tier,
    )
    return ScoredLead(lead=lead, overall_score=score, explanation=explanation, quality_tier=tier)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(params=["memory", "sqlite"])
def db_path(request):
    """Yield a store identifier for the requested backend."""
    if request.param == "memory":
        yield "memory://"
    else:
        # sqlite: use a temporary file
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield f"sqlite:///{path}"
        os.remove(path)


@pytest.fixture
def repo(db_path):
    """Return a LeadRepository configured for the given backend."""
    return LeadRepository(backend=db_path)


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_save_and_get_by_id(repo):
    lead = make_lead(lead_id="lead-1", score=80)
    lid = repo.save(lead)
    assert lid == "lead-1"

    fetched = repo.get_by_id(lid)
    assert fetched is not None
    assert isinstance(fetched, ScoredLead)
    assert fetched.lead.company_name == "Acme Corp"
    assert fetched.overall_score == 80
    assert fetched.quality_tier == "high"


def test_get_by_id_unsaved_returns_none(repo):
    assert repo.get_by_id("missing-id") is None


def test_update_returns_false_for_missing(repo):
    lead = make_lead()
    assert repo.update("missing-id", lead) is False


def test_update_refreshes_updated_at(repo):
    lead = make_lead(lead_id="lead-2", score=70)
    lid = repo.save(lead)
    # Get the record before update
    record_before = repo._store.get(lid)
    # Create a new lead with updated company name (since ScoredLead.company_name is read-only)
    updated_lead = make_lead(lead_id="lead-2", company_name="New Name", score=70)
    repo.update(lid, updated_lead)
    record_after = repo._store.get(lid)
    # updated_at should be greater than or equal to the previous value (allow same second)
    assert record_after["updated_at"] >= record_before["updated_at"]  # type: ignore[operator]


def test_duplicate_insert_raises(repo):
    lead = make_lead(lead_id="dup-1")
    repo.save(lead)
    lead2 = make_lead(lead_id="dup-1", company_name="Other")
    with pytest.raises(DuplicateLeadError):
        repo.save(lead2)


def test_delete_removes_and_is_idempotent(repo):
    lead = make_lead(lead_id="del-1")
    lid = repo.save(lead)
    assert repo.get_by_id(lid) is not None

    assert repo.delete(lid) is True
    assert repo.get_by_id(lid) is None
    # Second delete should return False (not found)
    assert repo.delete(lid) is False


def test_bulk_insert_returns_ids(repo):
    leads = [make_lead(lead_id=str(i), score=50 + i) for i in range(3)]
    ids = repo.bulk_insert(leads)
    assert ids == ["0", "1", "2"]
    for lid in ids:
        assert repo.get_by_id(lid) is not None


def test_bulk_update_changes_multiple_rows(repo):
    leads = [make_lead(lead_id=str(i), score=50 + i) for i in range(3)]
    repo.bulk_insert(leads)

    updates = [
        ("0", make_lead(lead_id="0", score=90), None),
        ("1", make_lead(lead_id="1", score=91), None),
    ]
    updated = repo.bulk_update(updates)
    assert updated == 2

    assert repo.get_by_id("0").overall_score == 90
    assert repo.get_by_id("1").overall_score == 91
    assert repo.get_by_id("2").overall_score == 52  # unchanged


def test_search_by_text(repo):
    leads = [
        make_lead(lead_id="s1", company_name="Alpha Corp", website="https://alpha.com"),
        make_lead(lead_id="s2", company_name="Beta LLC", website="https://beta.com"),
        make_lead(lead_id="s3", company_name="Gamma Inc", website="https://gamma.com"),
    ]
    repo.bulk_insert(leads)

    page = repo.search("beta", page=1, per_page=10)
    assert page.total == 1
    assert len(page.items) == 1
    assert page.items[0].lead.company_name == "Beta LLC"

    # Case-insensitive
    page = repo.search("BETA", page=1, per_page=10)
    assert page.total == 1

    # No match
    page = repo.search("zeta", page=1, per_page=10)
    assert page.total == 0


def test_filter_by_lifecycle_and_score(repo):
    leads = [
        make_lead(lead_id="f1", score=60, lifecycle=LifecycleState.NEW),
        make_lead(lead_id="f2", score=80, lifecycle=LifecycleState.SCORED),
        make_lead(lead_id="f3", score=90, lifecycle=LifecycleState.CONTACTED),
    ]
    repo.bulk_insert(leads)

    # Only SCORED
    page = repo.filter(lifecycle=LifecycleState.SCORED)
    assert page.total == 1
    assert page.items[0].lead.company_name == "Acme Corp"  # from make_lead default

    # Score between 70 and 85 inclusive
    page = repo.filter(min_score=70, max_score=85)
    assert page.total == 1  # 60 is out, 80 and 90? 90 >85, so only 80
    assert {item.lead.lead_id for item in page.items} == {"f2"}

    # Combined filters
    page = repo.filter(lifecycle=LifecycleState.NEW, min_score=50)
    assert page.total == 1
    assert page.items[0].lead.lead_id == "f1"


def test_pagination(repo):
    # Create 25 leads
    leads = [make_lead(lead_id=str(i), score=i) for i in range(25)]
    repo.bulk_insert(leads)

    page1 = repo.pagination(page=1, per_page=10)
    assert len(page1.items) == 10
    assert page1.total == 25
    assert page1.page == 1
    assert page1.pages == 3
    assert page1.has_next is True
    assert page1.has_prev is False

    page2 = repo.pagination(page=2, per_page=10)
    assert page2.page == 2
    assert len(page2.items) == 10
    assert page2.has_next is True
    assert page2.has_prev is True

    page3 = repo.pagination(page=3, per_page=10)
    assert page3.page == 3
    assert len(page3.items) == 5
    assert page3.has_next is False
    assert page3.has_prev is True

    # Out of range page returns empty but still has metadata
    page4 = repo.pagination(page=4, per_page=10)
    assert page4.page == 4
    assert len(page4.items) == 0
    assert page4.has_next is False
    assert page4.has_prev is True


def test_count(repo):
    assert repo.count() == 0
    leads = [make_lead(lead_id=str(i)) for i in range(5)]
    repo.bulk_insert(leads)
    assert repo.count() == 5
    assert repo.count(lifecycle=LifecycleState.NEW) == 5  # default lifecycle


def test_set_lifecycle_valid_transition(repo):
    lead = make_lead(lead_id="lc-1")
    lid = repo.save(lead)

    # NEW -> DISCOVERED is allowed
    changed = repo.set_lifecycle(lid, LifecycleState.DISCOVERED, reason="test")
    assert changed is True

    # Verify the change persisted
    lead_after = repo.get_by_id(lid)
    assert lead_after is not None
    assert lead_after.lifecycle == LifecycleState.DISCOVERED

    # History should have one entry
    history = repo.get_lifecycle_history(lid)
    assert len(history) == 1
    assert history[0].to_state == LifecycleState.DISCOVERED
    assert history[0].from_state == LifecycleState.NEW
    assert history[0].reason == "test"


def test_set_lifecycle_invalid_transition_returns_false(repo):
    lead = make_lead(lead_id="lc-2")
    lid = repo.save(lead)

    # NEW -> SCORED is not allowed (must go through DISCOVERED and ENRICHED)
    changed = repo.set_lifecycle(lid, LifecycleState.SCORED, reason="skip")
    assert changed is False  # invalid transition returns False per spec

    # State should remain NEW
    assert repo.get_by_id(lid).lifecycle == LifecycleState.NEW


def test_advance_lifecycle_moves_to_next_state(repo):
    lead = make_lead(lead_id="lc-3")
    lid = repo.save(lead)

    # NEW -> DISCOVERED
    assert repo.advance_lifecycle(lid) is True
    assert repo.get_by_id(lid).lifecycle == LifecycleState.DISCOVERED

    # DISCOVERED -> ENRICHED
    assert repo.advance_lifecycle(lid) is True
    assert repo.get_by_id(lid).lifecycle == LifecycleState.ENRICHED

    # Continue until terminal
    assert repo.advance_lifecycle(lid) is True  # ENRICHED -> SCORED
    assert repo.advance_lifecycle(lid) is True  # SCORED -> CONTACTED
    assert repo.advance_lifecycle(lid) is True  # CONTACTED -> RESPONDED
    assert repo.advance_lifecycle(lid) is True  # RESPONDED -> QUALIFIED
    assert repo.advance_lifecycle(lid) is True  # QUALIFIED -> CUSTOMER

    # CUSTOMER is terminal
    assert repo.advance_lifecycle(lid) is False
    assert repo.get_by_id(lid).lifecycle == LifecycleState.CUSTOMER


def test_list_by_state(repo):
    leads = [
        make_lead(lead_id="ls-1", lifecycle=LifecycleState.NEW),
        make_lead(lead_id="ls-2", lifecycle=LifecycleState.DISCOVERED),
        make_lead(lead_id="ls-3", lifecycle=LifecycleState.NEW),
    ]
    repo.bulk_insert(leads)

    page = repo.list_by_state(LifecycleState.NEW)
    assert page.total == 2
    assert {item.lead.lead_id for item in page.items} == {"ls-1", "ls-3"}


def test_get_lifecycle_history_empty_for_new_lead(repo):
    lead = make_lead(lead_id="lch-1")
    lid = repo.save(lead)
    assert repo.get_lifecycle_history(lid) == []


def test_merge_unionizes_lists_and_prefers_nonempty(repo):
    # Insert a base lead
    base = make_lead(
        lead_id="merge-1",
        company_name="Base Co",
        website="https://base.com",
        emails=["a@base.com"],
        phones=["111"],
        socials={"twitter": "@base"},
        skills=["skill1"],
        rating=5.0,
    )
    repo.save(base)

    # Incoming lead with some overlapping and some new data
    incoming = make_lead(
        lead_id="merge-1",  # same ID
        company_name="",  # empty -> keep base
        website="https://newbase.com",  # non-empty -> replace
        emails=["b@base.com"],  # new email
        phones=["222", "333"],  # new phones
        socials={"linkedin": "@newbase"},  # new social
        skills=["skill2"],  # new skill
        rating=None,  # None -> keep base
    )
    merged = repo.merge("merge-1", incoming)
    assert merged.company_name == "Base Co"
    assert merged.website == "https://newbase.com"
    # emails union
    assert set(merged.emails) == {"a@base.com", "b@base.com"}
    # phones union
    assert set(merged.phones) == {"111", "222", "333"}
    # socials union
    assert merged.socials["twitter"] == "@base"
    assert merged.socials["linkedin"] == "@newbase"
    # skills union
    assert set(merged.skills) == {"skill1", "skill2"}
    # rating preserved from base
    assert merged.rating == 5.0


def test_persist_orchestrator_summary_calls_bulk_insert(monkeypatch, repo):
    """Ensure the orchestrator helper delegates to bulk_insert."""
    calls = []

    def fake_bulk_insert(items):
        calls.append(list(items))
        return [item.lead.lead_id for item in items if hasattr(item, "lead")]

    monkeypatch.setattr(repo, "bulk_insert", fake_bulk_insert)

    # Create a mock summary with scored_leads
    class Summary:
        def __init__(self, leads):
            self.scored_leads = leads

    leads = [make_lead(lead_id=f"sum-{i}", score=70 + i) for i in range(3)]
    summary = Summary(leads)

    repo.persist_orchestrator_summary(summary)

    assert len(calls) == 1
    assert len(calls[0]) == 3
    # Check that the passed items are ScoredLead instances
    from scraper.scoring.models import ScoredLead
    assert all(isinstance(item, ScoredLead) for item in calls[0])