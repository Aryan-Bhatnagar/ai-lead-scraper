"""Repository-specific exceptions — Phase 19B.

A small, closed hierarchy so callers can catch all persistence problems with
``PersistenceError`` without knowing which backend raised them.
"""

from __future__ import annotations


class PersistenceError(Exception):
    """Base class for every Lead Repository error."""


class LeadNotFoundError(PersistenceError):
    """Raised when the requested lead id does not exist."""

    def __init__(self, lead_id: str) -> None:
        super().__init__(f"Lead not found: {lead_id}")
        self.lead_id = lead_id


class DuplicateLeadError(PersistenceError):
    """Raised when inserting a lead whose id is already present."""

    def __init__(self, lead_id: str) -> None:
        super().__init__(f"Lead already exists: {lead_id}")
        self.lead_id = lead_id


class InvalidLifecycleTransition(PersistenceError):
    """Raised when a lifecycle state change violates the transition table."""

    def __init__(self, from_state, to_state) -> None:
        super().__init__(
            f"Invalid lifecycle transition: {from_state} → {to_state}"
        )
        self.from_state = from_state
        self.to_state = to_state


class StoreConfigurationError(PersistenceError):
    """Raised when a backend URI cannot be resolved to a LeadStore."""
