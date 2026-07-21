# scraper/scrape_api_helper.py
"""Background job executor for scrape jobs.

This module introduces a small helper that talks to the existing database
functions (`scraper.database`) and to the scraping routine
(`scraper.scrape_leads.scrape_site`). It launches a background thread that
uses a bounded :class:`concurrent.futures.ThreadPoolExecutor` to process
each URL in the job.

The implementation follows the constraints from Phase 6B:

* ``db_path`` is passed explicitly to every helper – the global
  ``DB_PATH`` from :mod:`scraper.database` is never mutated.
* The job is marked ``running`` early and ``completed`` when all URLs
  have been processed.
* Each URL is updated independently through
  :func:`scraper.database.update_job_item`.
* Successful leads are persisted via
  :func:`scraper.database.upsert_lead`.
* Job counters (completed_urls, successful_urls, no_data_urls,
  failed_urls) are incremented appropriately.
* Any exception raised by a thread is caught; the corresponding job
  item is marked ``failed`` and the overall job is still marked
  ``completed``.

The helper is intentionally simple: it does not attempt to retry failures
or to restart abandoned threads – those are out of scope for the unit
tests.  It does, however, keep the executor alive until the worker
finishes.
"""

from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Iterable, Tuple

# These imports are cheap and guaranteed to exist in the repository.
from scraper import database as db_module
from scraper.scrape_leads import (
    scrape_site,
    has_meaningful_data,
    quality_score,
    data_quality,
)

# ---------------------------------------------------------------------------
# Logging – Swallow the default Flask logger interference.
# ---------------------------------------------------------------------------
logging.getLogger("scrape_api_helper").addHandler(logging.NullHandler())

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def utc_now() -> str:
    """Return the current time in ISO‑8601 UTC, seconds‑precision.

    The :mod:`scraper.database` module defines ``utc_now``; to avoid importing
    the entire module (and any of its heavy dependencies) in tests that
    might mock ``scrape_site`` we replicate the helper here.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

# ---------------------------------------------------------------------------
# Background worker – runs in a dedicated thread.
# ---------------------------------------------------------------------------

def _process_url(job_id: int, url: str, db_path) -> Tuple[str, str, str]:
    """Process a single URL.

    The returned tuple is ``(url, status, error)`` where ``status`` is one
    of ``success``, ``no_data`` or ``failed``. ``error`` is the string
    representation of any exception. The function mutates the database
    atomically via the helper functions.
    """
    # Mark the item as running.
    db_module.update_job_item(job_id, url, "running", db_path=db_path)

    try:
        lead = scrape_site(url)
    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        db_module.update_job_item(job_id, url, "failed", error=error_msg, db_path=db_path)
        return url, "failed", error_msg

    # Decide if the lead contains real data.
    if not lead or not has_meaningful_data(lead):
        db_module.update_job_item(job_id, url, "no_data", db_path=db_path)
        return url, "no_data", ""

    # Attach the authoritative source URL before database persistence.
    lead["source_url"] = url

    # Calculate deterministic lead quality before persistence.
    score = quality_score(lead)
    lead["quality_score"] = score
    lead["data_quality"] = data_quality(score, "success")
    lead["status"] = "success"

    # Persist the fully scored lead.
    try:
     db_module.upsert_lead(lead, db_path)
    except Exception as exc:
        error_msg = f"DB insert error: {type(exc).__name__}: {exc}"
        db_module.update_job_item(job_id, url, "failed", error=error_msg, db_path=db_path)
        return url, "failed", error_msg

    db_module.update_job_item(job_id, url, "success", db_path=db_path)
    return url, "success", ""


def _background_worker(job_id: int, urls: Iterable[str], db_path) -> None:
    """Entry point for a long‑running background thread.

    The function creates a bounded ThreadPoolExecutor – the worker count
    is limited to a maximum of five threads or the number of URLs
    (whichever is smaller).  Each URL is processed independently as
    described in :func:`_process_url`.
    """
    total_urls = len(urls)
    if total_urls == 0:
        # Guard against accidental empty jobs (unlikely in tests).
        return

    # Mark the job as running.
    db_module.update_scrape_job(
        job_id, db_path, status="running", started_at=utc_now()
    )

    completed = 0
    successful = 0
    no_data = 0
    failed = 0

    max_workers = min(5, total_urls)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(_process_url, job_id, url, db_path): url
            for url in urls
        }
        for future in future_to_url:
            try:
                url, status, _ = future.result()
                completed += 1
                if status == "success":
                    successful += 1
                elif status == "no_data":
                    no_data += 1
                elif status == "failed":
                    failed += 1
            except Exception as exc:  # pragma: no cover – unlikely
                # A fatal thread‑level exception; treat entire job as failed.
                completed += 1
                failed += 1
                logging.exception("Fatal error while processing job %s", job_id)

    # Finalise the job.
    db_module.update_scrape_job(
        job_id,
        db_path,
        status="completed",
        completed_at=utc_now(),
        completed_urls=completed,
        successful_urls=successful,
        no_data_urls=no_data,
        failed_urls=failed,
    )


# ---------------------------------------------------------------------------
# Public API used by the Flask route.
# ---------------------------------------------------------------------------

def run_job_in_background(job_id: int, urls: Iterable[str], db_path) -> None:
    """Launch a background thread that processes a scrape job.

    The helper intentionally returns immediately; the caller does not
    wait for the thread to finish – the job status can be queried via
    :func:`scraper.database.get_scrape_job`.
    """
    thread = threading.Thread(
        target=_background_worker, args=(job_id, list(urls), db_path), daemon=True
    )
    thread.start()

# End of module.
