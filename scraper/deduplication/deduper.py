"""Lead deduplication implementation.

The design follows the approved architecture: index building, candidate
generation, scoring, cluster resolution and merge.  The implementation is
intentionally straightforward – it favours clarity over extreme
performance because the typical lead volume (a few thousand) is easily
handled in‑memory.
"""

from __future__ import annotations

import difflib
import itertools
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from .config import DedupConfig
from .models import DedupScore, LeadCluster, DeduplicationReport
from scraper.discovery.model import UnifiedLead


def _extract_domain(lead: UnifiedLead) -> str | None:
    """Return a normalised domain string for the lead.

    Preference order:
    * ``canonical_domain`` – already stripped of scheme / sub‑domains.
    * ``website`` – parse out the netloc.
    """
    if lead.canonical_domain:
        return lead.canonical_domain.lower()
    if lead.website:
        # naïve extraction – split on '/' and remove protocol if present
        url = lead.website.lower().split("//")[-1]
        domain = url.split("/")[0]
        return domain
    return None


def _email_domains(lead: UnifiedLead) -> Set[str]:
    domains: Set[str] = set()
    for email in lead.emails:
        parts = email.split("@")
        if len(parts) == 2:
            domains.add(parts[1].lower())
    return domains


def _phones_set(lead: UnifiedLead) -> Set[str]:
    # Assume phones are already stored in a comparable E.164‑like format.
    return {p.strip() for p in lead.phones if p}


def _company_name_norm(lead: UnifiedLead) -> str | None:
    if lead.company_name_norm:
        return lead.company_name_norm.lower()
    if lead.company_name:
        return lead.company_name.lower()
    return None


def _similarity(a: str, b: str) -> float:
    """Return a 0‑1 similarity using difflib.SequenceMatcher."""
    return difflib.SequenceMatcher(None, a, b).ratio()


class LeadDeduper:
    """Deduplicate a list of :class:`UnifiedLead` objects.

    The public entry point is :meth:`deduplicate`.  Internally the class
    builds a few in‑memory indexes, scores candidate pairs, resolves clusters
    with a Union‑Find structure and finally merges the secondary leads into the
    chosen *winner*.
    """

    def __init__(self, config: DedupConfig | None = None):
        self.config = config or DedupConfig.default()
        # Weight constants used for the numeric score (higher priority gets
        # larger weight so that it dominates lower‑priority matches).
        self._weights = {
            "domain": 4_000,
            "company": 3_000,
            "email": 2_000,
            "phone": 1_000,
        }

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def deduplicate(self, leads: List[UnifiedLead]) -> List[UnifiedLead]:
        """Return a deduplicated list of leads.

        The method also populates a :class:`DeduplicationReport` that can be
        inspected via the ``report`` attribute after the call.
        """
        if not leads:
            self.report = DeduplicationReport(total_input=0, total_output=0)
            return []

        self.report = DeduplicationReport(total_input=len(leads))

        # 1️⃣ Build indexes
        domain_index: Dict[str, List[int]] = defaultdict(list)
        company_index: Dict[str, List[int]] = defaultdict(list)
        email_index: Dict[str, List[int]] = defaultdict(list)
        phone_index: Dict[str, List[int]] = defaultdict(list)

        for idx, lead in enumerate(leads):
            d = _extract_domain(lead)
            if d:
                domain_index[d].append(idx)
            cn = _company_name_norm(lead)
            if cn:
                company_index[cn].append(idx)
            for ed in _email_domains(lead):
                email_index[ed].append(idx)
            for ph in _phones_set(lead):
                phone_index[ph].append(idx)

        # 2️⃣ Union‑Find structure
        parent: List[int] = list(range(len(leads)))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(a: int, b: int, winner: int) -> None:
            ra, rb = find(a), find(b)
            if ra == rb:
                return
            # Attach the poorer root to the winner root
            if winner == a:
                parent[rb] = ra
            else:
                parent[ra] = rb

        # Helper to compute a DedupScore between two indices
        def score_pair(i: int, j: int) -> DedupScore:
            lead_i, lead_j = leads[i], leads[j]
            # Domain match
            di = _extract_domain(lead_i)
            dj = _extract_domain(lead_j)
            domain_match = di is not None and di == dj
            # Company similarity (only if needed later)
            ci = _company_name_norm(lead_i)
            cj = _company_name_norm(lead_j)
            company_sim = 0.0
            if ci and cj:
                company_sim = _similarity(ci, cj)
            # Email domain match
            email_match = bool(_email_domains(lead_i) & _email_domains(lead_j))
            # Phone match
            phone_match = bool(_phones_set(lead_i) & _phones_set(lead_j))

            # Compute weighted numeric score – higher‑priority matches get the
            # larger weight; company similarity is scaled by the weight.
            numeric = (
                (self._weights["domain"] if domain_match else 0)
                + (self._weights["company"] * company_sim if not domain_match else 0)
                + (self._weights["email"] if email_match else 0)
                + (self._weights["phone"] if phone_match else 0)
            )
            return DedupScore(
                domain_match=domain_match,
                company_sim=company_sim,
                email_domain_match=email_match,
                phone_match=phone_match,
                numeric=numeric,
            )

        # 3️⃣ Generate candidate pairs respecting priority order
        # We iterate over each index collection; for each lead we only compare it
        # with later‑indexed leads to avoid duplicate work.
        for idx, lead in enumerate(leads):
            # Priority 1 – domain
            d = _extract_domain(lead)
            if d and len(domain_index[d]) > 1:
                for other in domain_index[d]:
                    if other <= idx:
                        continue
                    s = score_pair(idx, other)
                    if s.domain_match:
                        # winner is the one with higher numeric score
                        winner = idx if s.numeric >= 0 else other  # numeric always >=0 here
                        union(idx, other, winner)
                        self.report.merge_statistics["domain"] += 1
                continue  # domain already resolved – move to next lead

            # Priority 2 – fuzzy company name
            cn = _company_name_norm(lead)
            if cn:
                # Find candidates whose normalized name is within the similarity
                # threshold – we naïvely compare against the whole index.
                for other_idx, other_lead in enumerate(leads[idx + 1 :], start=idx + 1):
                    other_cn = _company_name_norm(other_lead)
                    if not other_cn:
                        continue
                    sim = _similarity(cn, other_cn)
                    if sim >= self.config.company_name_min_similarity:
                        s = score_pair(idx, other_idx)
                        # Company similarity already satisfied – union
                        winner = idx if s.numeric >= 0 else other_idx
                        union(idx, other_idx, winner)
                        self.report.merge_statistics["company"] += 1
                continue

            # Priority 3 – email domain
            eds = _email_domains(lead)
            for ed in eds:
                if len(email_index[ed]) > 1:
                    for other in email_index[ed]:
                        if other <= idx:
                            continue
                        s = score_pair(idx, other)
                        if s.email_domain_match:
                            winner = idx if s.numeric >= 0 else other
                            union(idx, other, winner)
                            self.report.merge_statistics["email_domain"] += 1
                    break  # processed all leads for this email domain

            # Priority 4 – phone
            phs = _phones_set(lead)
            for ph in phs:
                if len(phone_index[ph]) > 1:
                    for other in phone_index[ph]:
                        if other <= idx:
                            continue
                        s = score_pair(idx, other)
                        if s.phone_match:
                            winner = idx if s.numeric >= 0 else other
                            union(idx, other, winner)
                            self.report.merge_statistics["phone"] += 1
                    break

        # 4️⃣ Build clusters from the union‑find structure
        clusters: Dict[int, List[int]] = defaultdict(list)
        for i in range(len(leads)):
            root = find(i)
            clusters[root].append(i)

        # 5️⃣ Merge members of each cluster
        deduped: List[UnifiedLead] = []
        for root, members in clusters.items():
            # Choose the *winner* – the lead with the highest numeric score when
            # compared pairwise against every other member.  For simplicity we
            # reuse the first member as winner if scores are equal.
            if len(members) == 1:
                deduped.append(leads[members[0]])
                continue

            # Compute pairwise numeric scores to pick the strongest lead.
            best_idx = members[0]
            best_score = -1.0
            for i in members:
                # Accumulate numeric contribution of i against all others.
                acc = 0.0
                for j in members:
                    if i == j:
                        continue
                    acc += score_pair(i, j).numeric
                if acc > best_score:
                    best_score = acc
                    best_idx = i

            winner = leads[best_idx]
            # Merge secondary leads into winner
            for i in members:
                if i == best_idx:
                    continue
                sec = leads[i]
                # emails / phones – deduplicate while preserving order
                winner.emails = list(dict.fromkeys(winner.emails + sec.emails))
                winner.phones = list(dict.fromkeys(winner.phones + sec.phones))
                # sources – we collect provenance.source strings
                src_set = {winner.provenance.source}
                src_set.update({sec.provenance.source})
                # store back as a comma‑separated string in provenance.source
                winner.provenance.source = ",".join(sorted(src_set))
                # raw_fields – not explicitly modeled; we simply keep the
                # provenance.raw_ref of the winner if present, otherwise the
                # first secondary that has it.
                if not winner.provenance.raw_ref and sec.provenance.raw_ref:
                    winner.provenance.raw_ref = sec.provenance.raw_ref
                # timestamps – use the earliest discovery timestamp
                if (
                    sec.provenance.discovered_at
                    and (
                        not winner.provenance.discovered_at
                        or sec.provenance.discovered_at < winner.provenance.discovered_at
                    )
                ):
                    winner.provenance.discovered_at = sec.provenance.discovered_at

            deduped.append(winner)

        self.report.total_output = len(deduped)
        self.report.duplicates_removed = self.report.total_input - self.report.total_output

        # Identify ambiguous clusters (size > 2) for the report
        for root, members in clusters.items():
            if len(members) > 2:
                self.report.ambiguous_clusters.append((root, members))

        return deduped
