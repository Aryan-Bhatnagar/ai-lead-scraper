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

    Includes rich lead intelligence fields (recommended_service, pain_points)
    and outreach_step for n8n AI personalization and 3-Day follow-up tracking.
    """
    return {
        "queue_id": entry["id"],
        "lead_id": entry["lead_id"],
        "business_name": lead.get("company_name"),
        "company_name": lead.get("company_name"),
        "contact_name": lead.get("contact_name"),
        "contact_role": lead.get("contact_role"),
        "email": lead.get("email"),
        "phone": lead.get("phone"),
        "website": lead.get("website"),
        "city": lead.get("city"),
        "recommended_service": lead.get("recommended_service"),
        "pain_points": lead.get("pain_points"),
        "outreach_channel": entry["outreach_channel"],
        "outreach_status": entry["outreach_status"],
        "outreach_step": entry.get("outreach_step", 1),
    }


def dispatch_entry(
    entry_id: int,
    db_path: str | Path = db.DB_PATH,
    webhook_url: str | None = None,
) -> Tuple[bool, str | None]:
    """Dispatch a single outreach entry.

    The function follows these steps:
    1. Load the entry and its lead.
    2. Transition row status to ``PROCESSING`` using ``db.start_dispatch``.
    3. POST payload to webhook URL.
    4. On success mark ``SENT`` and log event; on exception mark ``FAILED``.
    """
    webhook_url = webhook_url or os.getenv("OUTREACH_WEBHOOK_URL")
    if not webhook_url:
        return False, "OUTREACH_WEBHOOK_URL is not configured"

    entry = db.get_outreach_entry_by_id(entry_id, db_path)
    if not entry:
        return False, "Outreach entry not found"
    if entry["outreach_status"] not in {"PENDING", "FAILED", "SENT"}:
        return False, "Outreach entry cannot be dispatched in its current state"

    lead = db.get_lead_by_id(entry["lead_id"], db_path)
    if not lead:
        return False, "Associated lead not found"

    # Move to PROCESSING (this also increments attempt_count).
    if not db.start_dispatch(entry_id, db_path):
        # If entry is SENT (for follow-up steps), start_dispatch allows transition
        with db.get_connection(db_path) as conn:
            now = db.utc_now()
            conn.execute(
                """
                UPDATE outreach_queue
                SET outreach_status = 'PROCESSING',
                    attempt_count = attempt_count + 1,
                    last_contacted_at = ?,
                    error_message = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, now, entry_id),
            )

    payload = _build_payload(entry, lead)
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        db.mark_dispatch_failure(entry_id, db_path, error_msg=str(exc))
        db.log_outreach_event(
            lead_id=entry["lead_id"],
            queue_id=entry_id,
            outreach_step=entry.get("outreach_step", 1),
            outreach_channel=entry["outreach_channel"],
            event_type="FAILED",
            message_snippet=str(exc),
            db_path=db_path,
        )
        return False, f"Webhook dispatch failed: {exc}"

    db.mark_dispatch_success(entry_id, db_path)
    db.log_outreach_event(
        lead_id=entry["lead_id"],
        queue_id=entry_id,
        outreach_step=entry.get("outreach_step", 1),
        outreach_channel=entry["outreach_channel"],
        event_type="DISPATCHED",
        message_snippet=f"Dispatched step {entry.get('outreach_step', 1)} via {entry['outreach_channel']}",
        db_path=db_path,
    )
    return True, None


def process_batch(
    limit: int = 10,
    retry_limit: int = 3,
    db_path: str | Path = db.DB_PATH,
    webhook_url: str | None = None,
    queue_ids: list[int] | None = None,
    outreach_channel: str | None = None,
    outreach_status: str | None = None,
    outreach_step: int | None = None,
    source: str | None = None,
    industry: str | None = None,
    quality_tier: str | None = None,
    date_preset: str | None = None,
    search: str | None = None,
) -> dict:
    """Process a batch of eligible outreach entries (including Day 2 & Day 3 follow-ups).

    If ``queue_ids`` is provided, ONLY those explicit IDs are processed.
    Otherwise, filters are applied strictly before picking up to ``limit`` entries.
    """
    webhook_url = webhook_url or os.getenv("OUTREACH_WEBHOOK_URL")
    
    # CASE A: Explicit Checkbox Selection
    if queue_ids and len(queue_ids) > 0:
        target_ids = set(queue_ids)
        all_entries = [e for e in db.get_outreach_entries(db_path) if e["id"] in target_ids]
        eligible = all_entries
    else:
        # CASE B: Filter-Aware Batch Processing
        all_entries = db.get_outreach_entries(
            db_path=db_path,
            outreach_channel=outreach_channel,
            outreach_status=outreach_status,
            outreach_step=outreach_step,
            source=source,
            industry=industry,
            quality_tier=quality_tier,
            date_preset=date_preset,
            search=search,
        )
        now_str = db.utc_now()
        eligible = []

        for e in all_entries:
            status = e.get("outreach_status")
            step = e.get("outreach_step", 1)
            next_follow_up = e.get("next_follow_up_at")

            if status == "PENDING":
                eligible.append(e)
            elif status == "FAILED" and e.get("attempt_count", 0) < retry_limit:
                eligible.append(e)
            elif status == "SENT" and step < 3 and next_follow_up and next_follow_up <= now_str:
                lead = db.get_lead_by_id(e["lead_id"], db_path)
                if lead and lead.get("lead_status") == "CONTACTED":
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
            if err and "cannot be dispatched" in err.lower():
                summary["skipped"] += 1
            else:
                summary["failed"] += 1
    return summary

