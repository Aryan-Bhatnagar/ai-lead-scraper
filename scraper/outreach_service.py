"""
Outreach processing utilities for Phase 11A.

This module extracts the core dispatch workflow from ``api.app.dispatch_outreach``
so that it can be used both by the manual dispatch endpoint and by an automated
batch processor.  The public API is:

* ``dispatch_entry(entry_id: int, db_path: str | Path = DB_PATH, webhook_url: str | None = None) -> Tuple[bool, str | None]``
  Perform a single dispatch attempt. Returns ``(success, error_msg)`` where
  ``success`` is ``True`` when the entry is marked ``SENT``.  On failure ``error_msg``
  contains the exception message.

* ``process_batch(limit: int = 10, retry_limit: int = 3, db_path: str | Path = DB_PATH, webhook_url: str | None = None) -> dict``
  Select up to ``limit`` eligible entries (status ``PENDING`` or ``FAILED`` with
  ``attempt_count`` < ``retry_limit``) and dispatch each. Returns a summary
  ``{"processed": n, "sent": s, "failed": f, "skipped": sk}``.

Both functions operate without any Flask request context, making them suitable
for background jobs or direct API use.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple, Dict

import requests

import scraper.database as db


def _build_payload(entry: dict, lead: dict) -> dict:
    """Construct the webhook payload for an outreach entry.

    Mirrors the payload creation in ``api.app.dispatch_outreach`` to keep the two
    code paths identical.
    """
    return {
        "queue_id": entry["id"],
        "lead_id": entry["lead_id"],
        "company_name": lead.get("company_name"),
        "contact_name": lead.get("contact_name"),
        "contact_role": lead.get("contact_role"),
        "email": lead.get("email"),
        "phone": lead.get("phone"),
        "website": lead.get("website"),
        "outreach_channel": entry["outreach_channel"],
        "outreach_status": entry["outreach_status"],
    }


def dispatch_entry(
    entry_id: int,
    db_path: str | Path = db.DB_PATH,
    webhook_url: str | None = None,
) -> Tuple[bool, str | None]:
    """Dispatch a single outreach entry.

    The function follows the same steps as the Flask endpoint:
    1. Load the entry and its lead.
    2. Transition the row to ``PROCESSING`` using ``db.start_dispatch``.
    3. POST the payload to the webhook URL.
    4. On success mark ``SENT``; on exception mark ``FAILED`` and store the
       error message.
    Returns ``(True, None)`` on success or ``(False, error_message)`` on failure.
    """
    webhook_url = webhook_url or os.getenv("OUTREACH_WEBHOOK_URL")
    if not webhook_url:
        return False, "OUTREACH_WEBHOOK_URL is not configured"

    entry = db.get_outreach_entry_by_id(entry_id, db_path)
    if not entry:
        return False, "Outreach entry not found"
    if entry["outreach_status"] not in {"PENDING", "FAILED"}:
        return False, "Outreach entry cannot be dispatched in its current state"

    lead = db.get_lead_by_id(entry["lead_id"], db_path)
    if not lead:
        return False, "Associated lead not found"

    # Move to PROCESSING (this also increments attempt_count).
    if not db.start_dispatch(entry_id, db_path):
        return False, "Failed to start dispatch"

    payload = _build_payload(entry, lead)
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        db.mark_dispatch_failure(entry_id, db_path, error_msg=str(exc))
        return False, f"Webhook dispatch failed: {exc}"

    db.mark_dispatch_success(entry_id, db_path)
    return True, None


def process_batch(
    limit: int = 10,
    retry_limit: int = 3,
    db_path: str | Path = db.DB_PATH,
    webhook_url: str | None = None,
) -> dict:
    """Process a batch of eligible outreach entries.

    * Eligible entries have status ``PENDING`` or ``FAILED``.
    * ``FAILED`` entries are only eligible when ``attempt_count`` < ``retry_limit``.
    * The function respects ``limit`` to avoid unbounded processing.
    """
    webhook_url = webhook_url or os.getenv("OUTREACH_WEBHOOK_URL")
    # Gather candidates.
    all_entries = db.get_outreach_entries(db_path)
    eligible = []
    for e in all_entries:
        status = e["outreach_status"]
        if status == "PENDING":
            eligible.append(e)
        elif status == "FAILED" and e.get("attempt_count", 0) < retry_limit:
            eligible.append(e)
        if len(eligible) >= limit:
            break

    summary = {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}
    for entry in eligible:
        summary["processed"] += 1
        success, err = dispatch_entry(entry["id"], db_path, webhook_url)
        if success:
            summary["sent"] += 1
        else:
            # Distinguish permanent skips (e.g., no webhook URL) from runtime failures.
            if err and "cannot be dispatched" in err.lower():
                summary["skipped"] += 1
            else:
                summary["failed"] += 1
    return summary
