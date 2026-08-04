"""
Next action determination for lead recommendations.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..database import LEAD_STATUSES


def determine_next_action(lead: dict, priority: str, score: int, lifecycle: str,
                          has_website: bool, has_email: bool) -> str:
    """
    Determine the next recommended action for a lead.

    Returns one of:
    - "Research Website"
    - "Find Email"
    - "Contact Immediately"
    - "Follow Up"
    - "LinkedIn Outreach"
    - "Phone Call"
    - "Ignore"
    """
    # If no contact info and low score, ignore
    if not has_website and not has_email and score < 50:
        return "Ignore"

    # If we have email and high score, contact immediately
    if has_email and score >= 80:
        return "Contact Immediately"

    # If we have phone (we don't have phone field reliably, but if we did)
    # For now, we'll treat website as a way to contact via form
    if has_website and not has_email and score >= 70:
        return "Contact Immediately"

    # If we have been contacted but not responded, follow up
    if lifecycle in ["CONTACTED", "RESPONDED"] and has_email:
        return "Follow Up"

    # If we have website but no email, try to find email
    if has_website and not has_email:
        return "Find Email"

    # If we have email but haven't contacted yet, consider LinkedIn outreach as alternative
    if has_email and lifecycle in ["NEW", "DISCOVERED"]:
        # Could also do LinkedIn, but we'll prioritize email
        return "Contact Immediately"

    # Default: research website to find contact info
    if has_website:
        return "Research Website"
    else:
        # No website, no email - try to find email via other means or LinkedIn
        return "LinkedIn Outreach"