"""Unit tests for the LeadDeduper (Phase 18B).

The tests exercise each priority rule and the merge behaviour required by the
specification.  They rely only on the pure ``LeadDeduper`` implementation and do
not need any external services.
"""

from datetime import datetime, timezone
from typing import List

import pytest

from scraper.discovery.model import UnifiedLead, Provenance, LocationData
from scraper.deduplication.deduper import LeadDeduper


def _make_lead(
    *,
    id_suffix: str,
    domain: str | None = None,
    website: str | None = None,
    company_name: str | None = None,
    emails: List[str] | None = None,
    phones: List[str] | None = None,
    source: str = "provider_a",
) -> UnifiedLead:
    """Factory helper to build a ``UnifiedLead`` with minimal required fields.

    ``id_suffix`` is appended to a dummy UUID string to make each lead unique.
    """
    lead = UnifiedLead(
        canonical_domain=domain,
        website=website,
        company_name=company_name,
        company_name_norm=company_name.lower() if company_name else None,
        emails=emails or [],
        phones=phones or [],
        provenance=Provenance(
            source=source,
            discovered_at=datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
        ),
    )
    # Populate a deterministic id via the dataclass default ``external_ids``
    lead.external_ids["uid"] = f"uid-{id_suffix}"
    return lead


@pytest.fixture
def deduper():
    return LeadDeduper()


def test_exact_domain_match(deduper: LeadDeduper):
    l1 = _make_lead(id_suffix="1", domain="example.com", website="https://example.com", company_name="Acme")
    l2 = _make_lead(id_suffix="2", domain="example.com", website="https://example.com", company_name="Acme Corp")
    result = deduper.deduplicate([l1, l2])
    assert len(result) == 1
    # The winner should retain the first lead's emails/phones (none) and have a combined source list.
    assert result[0].provenance.source == "provider_a"


def test_company_fuzzy_match(deduper: LeadDeduper):
    # No domain match, but company names are similar enough.
    l1 = _make_lead(id_suffix="1", company_name="OpenAI")
    l2 = _make_lead(id_suffix="2", company_name="Open AI")
    result = deduper.deduplicate([l1, l2])
    assert len(result) == 1
    # Ensure the combined provenance source still refers to the original (single) source.
    assert result[0].provenance.source == "provider_a"


def test_email_domain_match(deduper: LeadDeduper):
    l1 = _make_lead(id_suffix="1", emails=["alice@example.com"])
    l2 = _make_lead(id_suffix="2", emails=["bob@example.com"])
    result = deduper.deduplicate([l1, l2])
    assert len(result) == 1
    # Emails should be merged.
    assert set(result[0].emails) == {"alice@example.com", "bob@example.com"}


def test_phone_match(deduper: LeadDeduper):
    l1 = _make_lead(id_suffix="1", phones=["+15551234567"])
    l2 = _make_lead(id_suffix="2", phones=["+15551234567"])
    result = deduper.deduplicate([l1, l2])
    assert len(result) == 1
    assert result[0].phones == ["+15551234567"]


def test_no_duplicates(deduper: LeadDeduper):
    l1 = _make_lead(id_suffix="1", domain="a.com", company_name="Alpha")
    l2 = _make_lead(id_suffix="2", domain="b.com", company_name="Beta")
    result = deduper.deduplicate([l1, l2])
    assert len(result) == 2


def test_multi_provider_duplicates_and_merge(deduper: LeadDeduper):
    # Same domain but discovered by different providers – we want source aggregation.
    l1 = _make_lead(id_suffix="1", domain="example.com", website="https://example.com", emails=["a@example.com"], source="provider_a")
    l2 = _make_lead(id_suffix="2", domain="example.com", website="https://example.com", phones=["+1234567890"], source="provider_b")
    result = deduper.deduplicate([l1, l2])
    assert len(result) == 1
    merged = result[0]
    # Emails and phones from both leads must be present.
    assert set(merged.emails) == {"a@example.com"}
    assert set(merged.phones) == {"+1234567890"}
    # Source provenance should contain both providers (comma‑separated, sorted).
    sources = set(merged.provenance.source.split(","))
    assert sources == {"provider_a", "provider_b"}


def test_merge_timestamp_earliest(deduper: LeadDeduper):
    # Lead l1 discovered later than l2 – after merge we keep the earliest timestamp.
    later = Provenance(source="a", discovered_at=datetime(2023, 5, 1, tzinfo=timezone.utc))
    earlier = Provenance(source="b", discovered_at=datetime(2022, 5, 1, tzinfo=timezone.utc))
    l1 = UnifiedLead(canonical_domain="x.com", provenance=later)
    l2 = UnifiedLead(canonical_domain="x.com", provenance=earlier)
    result = deduper.deduplicate([l1, l2])
    assert len(result) == 1
    assert result[0].provenance.discovered_at == earlier.discovered_at
