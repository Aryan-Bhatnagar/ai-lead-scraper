"""Lead lifecycle state machine — Phase 19B.

Strict enforcement: illegal state jumps raise ``InvalidLifecycleTransition``
and are recorded only via the audit history table.

        NEW → DISCOVERED → ENRICHED → SCORED → CONTACTED → RESPONDED
                                                  ↘  QUALIFIED → CUSTOMER
        LOST is reachable from CONTACTED / RESPONDED / QUALIFIED.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, Optional

from .exceptions import InvalidLifecycleTransition


class LifecycleState(str, Enum):
    """The 9 canonical lead states (order matters for ``advance_lifecycle``)."""

    NEW = "NEW"
    DISCOVERED = "DISCOVERED"
    ENRICHED = "ENRICHED"
    SCORED = "SCORED"
    CONTACTED = "CONTACTED"
    RESPONDED = "RESPONDED"
    QUALIFIED = "QUALIFIED"
    LOST = "LOST"
    CUSTOMER = "CUSTOMER"

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Transition table
# ---------------------------------------------------------------------------

TRANSITIONS: Dict[LifecycleState, FrozenSet[LifecycleState]] = {
    LifecycleState.NEW: frozenset({LifecycleState.DISCOVERED, LifecycleState.LOST}),
    LifecycleState.DISCOVERED: frozenset({LifecycleState.ENRICHED, LifecycleState.LOST}),
    LifecycleState.ENRICHED: frozenset({LifecycleState.SCORED, LifecycleState.LOST}),
    LifecycleState.SCORED: frozenset({
        LifecycleState.CONTACTED, LifecycleState.QUALIFIED, LifecycleState.LOST,
    }),
    LifecycleState.CONTACTED: frozenset({LifecycleState.RESPONDED, LifecycleState.LOST}),
    LifecycleState.RESPONDED: frozenset({LifecycleState.QUALIFIED, LifecycleState.LOST}),
    LifecycleState.QUALIFIED: frozenset({LifecycleState.CUSTOMER, LifecycleState.LOST}),
    LifecycleState.CUSTOMER: frozenset(),          # terminal
    LifecycleState.LOST: frozenset(),              # terminal (reopen = future work)
}

# Canonical "next" state used by ``advance_lifecycle``.
_NEXT: Dict[LifecycleState, Optional[LifecycleState]] = {
    LifecycleState.NEW: LifecycleState.DISCOVERED,
    LifecycleState.DISCOVERED: LifecycleState.ENRICHED,
    LifecycleState.ENRICHED: LifecycleState.SCORED,
    LifecycleState.SCORED: LifecycleState.CONTACTED,
    LifecycleState.CONTACTED: LifecycleState.RESPONDED,
    LifecycleState.RESPONDED: LifecycleState.QUALIFIED,
    LifecycleState.QUALIFIED: LifecycleState.CUSTOMER,
    LifecycleState.CUSTOMER: None,
    LifecycleState.LOST: None,
}

TERMINAL_STATES: FrozenSet[LifecycleState] = frozenset(
    {LifecycleState.CUSTOMER, LifecycleState.LOST}
)


class LifecycleEngine:
    """Pure, stateless validator for lead lifecycle transitions."""

    # ------------------------------------------------------------------
    @staticmethod
    def coerce(state) -> LifecycleState:
        """Accept ``LifecycleState`` or its string value."""
        if isinstance(state, LifecycleState):
            return state
        try:
            return LifecycleState(str(state).upper())
        except ValueError as exc:
            raise InvalidLifecycleTransition("<unknown>", state) from exc

    # ------------------------------------------------------------------
    @classmethod
    def can_transition(cls, from_state, to_state) -> bool:
        src, dst = cls.coerce(from_state), cls.coerce(to_state)
        if src in TERMINAL_STATES:
            return False
        return dst in TRANSITIONS.get(src, frozenset())

    # ------------------------------------------------------------------
    @classmethod
    def validate(cls, from_state, to_state) -> LifecycleState:
        """Return the coerced target state or raise."""
        src, dst = cls.coerce(from_state), cls.coerce(to_state)
        if not cls.can_transition(src, dst):
            raise InvalidLifecycleTransition(src.value, dst.value)
        return dst

    # ------------------------------------------------------------------
    @classmethod
    def next_state(cls, state) -> LifecycleState:
        """Return the canonical advancement target or raise when terminal."""
        src = cls.coerce(state)
        nxt = _NEXT.get(src)
        if nxt is None:
            raise InvalidLifecycleTransition(src.value, "<advance>")
        return nxt

    # ------------------------------------------------------------------
    @staticmethod
    def is_terminal(state) -> bool:
        return LifecycleEngine.coerce(state) in TERMINAL_STATES
