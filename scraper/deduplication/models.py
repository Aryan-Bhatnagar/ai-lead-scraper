'''Deduplication core models.

This module defines the lightweight data structures used by the LeadDeduper.
It purposefully stays independent from any I/O so that unit‑tests can import it
without side‑effects.
'''

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple

from scraper.discovery.model import UnifiedLead


@dataclass(eq=False)
class DedupScore:
    """Result of comparing two leads.

    Attributes
    ----------
    domain_match: bool
        True when the normalized website domain is identical.
    company_sim: float
        Similarity in the range 0‑1 between the two normalized company names.
    email_domain_match: bool
        True when the part after '@' of any email address matches.
    phone_match: bool
        True when any phone number matches exactly after normalisation.
    numeric: float
        Weighted numeric score used for ranking within a cluster.  The weight
        values themselves live in ``LeadDeduper``; this field simply stores the
        computed total.
    """

    domain_match: bool = False
    company_sim: float = 0.0
    email_domain_match: bool = False
    phone_match: bool = False
    numeric: float = 0.0

    def __repr__(self) -> str:
        return (
            f"DedupScore(domain={self.domain_match}, comp={self.company_sim:.2f}, "
            f"email={self.email_domain_match}, phone={self.phone_match}, "
            f"numeric={self.numeric:.2f})"
        )


@dataclass
class LeadCluster:
    """A mutable set of leads that belong together.

    ``winner_id`` points to the lead that will survive after merging.
    """

    member_ids: Set[int] = field(default_factory=set)
    winner_id: int | None = None

    def add(self, lead_id: int) -> None:
        self.member_ids.add(lead_id)

    def size(self) -> int:
        return len(self.member_ids)


@dataclass
class DeduplicationReport:
    """Summary of a deduplication run.

    All fields are simple numbers / collections that are easy to serialise.
    """

    total_input: int = 0
    total_output: int = 0
    duplicates_removed: int = 0
    merge_statistics: Dict[str, int] = field(default_factory=lambda: {
        "domain": 0,
        "company": 0,
        "email_domain": 0,
        "phone": 0,
    })
    ambiguous_clusters: List[Tuple[int, List[int]]] = field(default_factory=list)
