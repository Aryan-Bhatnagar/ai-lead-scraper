"""
Flask application factory for AI Lead Scraper.

This module implements a fully‑fledged Flask app that
* reads configuration from a supplied dictionary,
* attaches CORS for development, and
* exposes a small REST API for leads and scrape jobs.

Only thin wrappers around :mod:`scraper.database` are used – the actual
database access logic lives there so the tests can monkey‑patch the database
path.

The factory accepts a ``config`` mapping which may specify:
    - ``TESTING`` – makes the returned app suitable for unit tests;
    - ``DATABASE`` – an SQLite file path.  When omitted, the production
      database at ``data/leads.db`` is used.

All endpoints return JSON with appropriate status codes and use
parameterized SQL to avoid injection.

The file intentionally contains no ``if __name__ == "__main__"``
block – the application is started through the standard WSGI frontend used
by the tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from flask import Flask, jsonify, request, abort
import json
import os
import requests
from urllib.parse import urlparse
from flask_cors import CORS

# ``scraper.database`` is the only place where the concrete SQLite
# connection is created.  Importing it keeps the pipe to the tests
# straightforward – the test suite changes the ``DATABASE`` key before
# calling ``create_app``.
import scraper.database as db

from scraper.lead_discovery import discover_leads
from scraper.google_maps_discovery import discover_google_maps

# ---------------------------------------------------------------------------
# Helper functions – thin wrappers that delegate to the database module.
# The database module exposes ``get_lead_by_id`` and ``update_lead_status``.
# We add ``get_leads`` that supports optional filtering by the scraper ``status``,
# the CRM ``lead_status`` and ``data_quality`` fields.
# ---------------------------------------------------------------------------

def get_leads(
    db_path: Path | str,
    filter_status: str | None = None,
    filter_q: str | None = None,
    filter_lead_status: str | None = None,
) -> List[Dict[str, Any]]:
    """Return all leads, optionally filtered by:
    * ``status`` – the scraper‑generated status field,
    * ``data_quality`` – the quality bucket,
    * ``lead_status`` – the new CRM lifecycle status.
    ``None`` for any filter means no filtering on that column.
    """
    query = "SELECT * FROM leads"
    clauses: List[str] = []
    params: List[Any] = []
    if filter_status:
        clauses.append("status = ?")
        params.append(filter_status)
    if filter_q:
        clauses.append("data_quality = ?")
        params.append(filter_q)
    if filter_lead_status:
        clauses.append("lead_status = ?")
        params.append(filter_lead_status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    with db.get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
    # ``dict(row)`` works because the database connection is set to Row
    leads: List[Dict[str, Any]] = [dict(row) for row in rows]
    return leads


def create_app(config: Dict[str, Any] | None = None) -> Flask:
    """Factory function that creates the Flask application.

    Parameters
    ----------
    config:
        Optional mapping containing configuration keys.  Known keys
        are ``TESTING`` and ``DATABASE``.

    Returns
    -------
    Flask
        A fully initialised Flask application.
    """
    app = Flask("ai_lead_scraper")
    CORS(app)  # Enable CORS for development.

    # Apply configuration – ``getattr`` is used so the caller can pass a
    # plain dict or an object with attributes.
    if config is not None:
        app.config.update(config)

    # Determine the database path – default to ``data/leads.db``.
    db_path = Path(app.config.get("DATABASE", "data/leads.db"))
    # store the path in app config for use by endpoints
    app.config["DATABASE"] = str(db_path)

    # Health check endpoint – always available.
    @app.route("/api/health", methods=["GET"])
    def health():  # pragma: no cover - trivial
        return jsonify({"status": "ok"})

    # -------------------------------------------------------------------
    # Leads endpoints
    # -------------------------------------------------------------------
    @app.route("/api/leads", methods=["GET"])
    def list_leads():
        status = request.args.get("status")
        q = request.args.get("data_quality")
        lead_status = request.args.get("lead_status")
        leads = get_leads(
            app.config["DATABASE"],
            status,
            q,
            lead_status,
        )
        return jsonify({"leads": leads, "count": len(leads)})

    @app.route("/api/leads/<int:lead_id>", methods=["GET"])
    def get_lead(lead_id: int):
        lead = db.get_lead_by_id(
            lead_id,
            app.config["DATABASE"],
        )
        if lead is None:
            abort(404, description="Lead not found")
        return jsonify(lead)

    @app.route("/api/leads/<int:lead_id>", methods=["DELETE"])
    def delete_lead(lead_id: int):
        with db.get_connection(app.config["DATABASE"]) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            deleted = cursor.rowcount > 0

        if not deleted:
            abort(404, description="Lead not found")

        return jsonify({"deleted": True})

    # -------------------------------------------------------------------
    # PATCH endpoint for CRM lead_status
    # -------------------------------------------------------------------
    @app.route("/api/leads/<int:lead_id>/status", methods=["PATCH"])
    def patch_lead_status(lead_id: int):
        # Expect a JSON body with a ``lead_status`` field.
        raw = request.get_data(cache=False)
        if not raw:
            abort(400, description="Request body is missing")
        try:
            payload = json.loads(raw)
        except Exception:
            abort(400, description="Invalid JSON payload")
        if not isinstance(payload, dict):
            abort(400, description="JSON body must be an object")
        lead_status = payload.get("lead_status")
        if lead_status is None:
            abort(400, description="Missing 'lead_status' field")
        # Validate against the allowed set defined in ``scraper.database``.
        if lead_status not in db.LEAD_STATUSES:
            abort(400, description=f"Invalid lead_status: {lead_status}")
        # Attempt the update.
        updated = db.update_lead_status(
            lead_id,
            lead_status,
            app.config["DATABASE"],
        )
        if not updated:
            abort(404, description="Lead not found")
        # Return the updated lead for convenience.
        lead = db.get_lead_by_id(
            lead_id,
            app.config["DATABASE"],
        )
        return jsonify(lead), 200

    # -------------------------------------------------------------------
    # Outreach Queue endpoints (Phase 10B)
    # -------------------------------------------------------------------
    @app.route("/api/outreach", methods=["GET"])
    def list_outreach():
        lead_id = request.args.get("lead_id", type=int)
        channel = request.args.get("outreach_channel")
        status = request.args.get("outreach_status")
        entries = db.get_outreach_entries(
            app.config["DATABASE"], lead_id=lead_id, outreach_channel=channel, outreach_status=status
        )
        return jsonify({"outreach": entries, "count": len(entries)})

    @app.route("/api/outreach", methods=["POST"])
    def create_outreach():
        raw = request.get_data(cache=False)
        if not raw:
            abort(400, description="Request body is missing")
        try:
            payload = json.loads(raw)
        except Exception:
            abort(400, description="Invalid JSON payload")
        if not isinstance(payload, dict):
            abort(400, description="JSON body must be an object")
        lead_id = payload.get("lead_id")
        channel = payload.get("outreach_channel")
        next_follow_up = payload.get("next_follow_up_at")
        if lead_id is None or channel is None:
            abort(400, description="'lead_id' and 'outreach_channel' are required")
        # Validate channel
        if channel not in db.OUTREACH_CHANNELS:
            abort(400, description=f"Invalid outreach_channel: {channel}")
        # Validate lead existence and eligibility
        lead = db.get_lead_by_id(lead_id, app.config["DATABASE"])  # noqa: E501
        if not lead:
            abort(400, description=f"Lead id {lead_id} does not exist")
        # Eligibility – lead_status must be QUALIFIED or INTERESTED
        if lead.get("lead_status") not in {"QUALIFIED", "INTERESTED"}:
            abort(400, description="Lead not eligible for outreach (status must be QUALIFIED or INTERESTED)")
        # Contact info checks
        if channel == "EMAIL" and not lead.get("email"):
            abort(400, description="Lead missing email for EMAIL outreach")
        if channel in {"WHATSAPP", "CALL"} and not lead.get("phone"):
            abort(400, description=f"Lead missing phone for {channel} outreach")
        # Create entry – underlying function will raise ValueError for duplicate active.
        try:
            entry_id = db.create_outreach_entry(
                lead_id, channel, app.config["DATABASE"], next_follow_up_at=next_follow_up
            )
        except ValueError as ve:
            abort(400, description=str(ve))
        entry = db.get_outreach_entry_by_id(entry_id, app.config["DATABASE"])
        return jsonify(entry), 201

    @app.route("/api/outreach/<int:queue_id>", methods=["PATCH"])
    def patch_outreach(queue_id: int):
        raw = request.get_data(cache=False)
        if not raw:
            abort(400, description="Request body is missing")
        try:
            payload = json.loads(raw)
        except Exception:
            abort(400, description="Invalid JSON payload")
        if not isinstance(payload, dict):
            abort(400, description="JSON body must be an object")
        # Only allow known mutable fields – the helper will validate further.
        try:
            updated = db.update_outreach_entry(queue_id, app.config["DATABASE"], **payload)
        except ValueError as ve:
            abort(400, description=str(ve))
        if not updated:
            abort(404, description="Outreach entry not found")
        entry = db.get_outreach_entry_by_id(queue_id, app.config["DATABASE"])
        return jsonify(entry), 200

    @app.route("/api/outreach/<int:queue_id>", methods=["DELETE"])
    def delete_outreach(queue_id: int):
        # Only allow deletion of PENDING or FAILED entries – logic inside DB helper.
        deleted = db.delete_outreach_entry(queue_id, app.config["DATABASE"])
        if not deleted:
            abort(400, description="Outreach entry cannot be deleted (must be PENDING or FAILED)")
        return jsonify({"deleted": True}), 200

    @app.route("/api/outreach/<int:queue_id>/dispatch", methods=["POST"])
    def dispatch_outreach(queue_id: int):
        webhook_url = os.getenv("OUTREACH_WEBHOOK_URL")
        if not webhook_url:
            return jsonify({
                "error": "OUTREACH_WEBHOOK_URL is not configured"
            }), 500

        entry = db.get_outreach_entry_by_id(
            queue_id, app.config["DATABASE"]
        )
        if not entry:
            abort(404, description="Outreach entry not found")

        if entry["outreach_status"] not in {"PENDING", "FAILED"}:
            abort(
                400,
                description=(
                    "Outreach entry cannot be dispatched "
                    "in its current state"
                ),
            )

        lead = db.get_lead_by_id(
            entry["lead_id"], app.config["DATABASE"]
        )
        if not lead:
            return jsonify({
                "error": "Associated lead not found"
            }), 500

        payload = {
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

        if not db.start_dispatch(
            queue_id, app.config["DATABASE"]
        ):
            return jsonify({
                "error": "Failed to start dispatch"
            }), 500

        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            db.mark_dispatch_failure(
                queue_id,
                app.config["DATABASE"],
                error_msg=str(exc),
            )
            return jsonify({
                "error": f"Webhook dispatch failed: {exc}"
            }), 502

        db.mark_dispatch_success(
            queue_id, app.config["DATABASE"]
        )

        entry = db.get_outreach_entry_by_id(
            queue_id, app.config["DATABASE"]
        )
        return jsonify(entry), 200

    # -------------------------------------------------------------------
    # Automated outreach batch processor (Phase 11A)
    # -------------------------------------------------------------------
    @app.route("/api/outreach/process", methods=["POST"])
    def process_outreach_batch():
        # Configuration – limit of entries per batch and retry ceiling.
        batch_limit = app.config.get("OUTREACH_BATCH_LIMIT", 10)
        retry_limit = app.config.get("OUTREACH_MAX_RETRY", 3)
        # Ensure the webhook URL is configured before any work.
        if not os.getenv("OUTREACH_WEBHOOK_URL"):
            return jsonify({
                "error": "OUTREACH_WEBHOOK_URL is not configured"
            }), 500
        # Import the shared service (local import to avoid circular at module load).
        from scraper import outreach_service as out_srv
        summary = out_srv.process_batch(
            limit=batch_limit,
            retry_limit=retry_limit,
            db_path=app.config["DATABASE"],
        )
        return jsonify(summary), 200

    # -------------------------------------------------------------------
    # Jobs endpoints
    # -------------------------------------------------------------------
    @app.route("/api/jobs", methods=["GET"])
    def list_jobs():
        with db.get_connection(app.config["DATABASE"]) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scrape_jobs")
            jobs = [dict(row) for row in cursor.fetchall()]
        return jsonify({"jobs": jobs, "count": len(jobs)})

    @app.route("/api/jobs", methods=["POST"])
    def create_job():
        # Step 1: Ensure a body exists
        raw = request.get_data(cache=False)
        if not raw:
            abort(400, description="Request body is missing")
        # Step 2: Parse JSON
        try:
            payload = json.loads(raw)
        except Exception:
            abort(400, description="Invalid JSON payload")
        if not isinstance(payload, dict):
            abort(400, description="JSON root must be an object")
        # Step 3: Validate presence of 'urls'
        if "urls" not in payload:
            abort(400, description="Missing 'urls' field")
        urls_raw = payload["urls"]
        # Step 4: Validate that urls_raw is a non-empty list
        if not isinstance(urls_raw, list) or len(urls_raw) == 0:
            abort(400, description="`urls` must be a non-empty list")
        cleaned_urls: list[str] = []
        seen: set[str] = set()
        for entry in urls_raw:
            if not isinstance(entry, str):
                abort(400, description="All `urls` must be strings")
            raw_url = entry.strip()
            if not raw_url:
                abort(400, description="URL entries cannot be empty or whitespace only")
            parsed = urlparse(raw_url)
            if parsed.scheme not in ("http", "https"):
                abort(400, description="URL must use http:// or https:// scheme")
            if not parsed.hostname:
                abort(400, description="URL missing host")
            if raw_url not in seen:
                seen.add(raw_url)
                cleaned_urls.append(raw_url)
        if not cleaned_urls:
            abort(400, description="No valid URLs provided")
        db_path = app.config["DATABASE"]
        job_id = db.create_scrape_job(cleaned_urls, db_path)
        from scraper import scrape_api_helper as helper
        helper.run_job_in_background(job_id, cleaned_urls, db_path)
        resp = {"job_id": job_id, "status": "queued"}
        return jsonify(resp), 202

    @app.route("/api/discover-and-scrape", methods=["POST"])
    def discover_and_scrape():
        # Parse incoming JSON payload
        raw = request.get_data(cache=False)
        if not raw:
            abort(400, description="Request body is missing")
        try:
            payload = json.loads(raw)
        except Exception:
            abort(400, description="Invalid JSON payload")
        if not isinstance(payload, dict):
            abort(400, description="JSON root must be an object")
        # Validate industry
        if "industry" not in payload:
            abort(400, description="Missing 'industry' field")
        industry = payload["industry"]
        if not isinstance(industry, str):
            abort(400, description="'industry' must be a string")
        industry = industry.strip()
        if not industry:
            abort(400, description="'industry' cannot be empty")
        # Validate location
        if "location" not in payload:
            abort(400, description="Missing 'location' field")
        location = payload["location"]
        if not isinstance(location, str):
            abort(400, description="'location' must be a string")
        location = location.strip()
        if not location:
            abort(400, description="'location' cannot be empty")
        # Validate max_results with defaults and bounds; reject booleans
        max_results = payload.get("max_results", 10)
        if not isinstance(max_results, int) or isinstance(max_results, bool):
            abort(400, description="'max_results' must be an integer")
        if max_results < 1 or max_results > 50:
            abort(400, description="'max_results' must be between 1 and 50")
        # Run discovery
        try:
            results = discover_leads(
                industry=industry,
                location=location,
                max_results=max_results,
            )
        except Exception:
            app.logger.exception("Lead discovery failed")
            return jsonify({"error": "Lead discovery failed"}), 500
        # Extract URLs, validate them and deduplicate preserving order
        urls: list[str] = []
        seen: set[str] = set()
        for entry in results:
            url_val = None
            if isinstance(entry, dict):
                url_val = entry.get("url")
            else:
                continue
            if not isinstance(url_val, str):
                continue
            url_str = url_val.strip()
            if not url_str:
                continue
            if not (url_str.startswith("http://") or url_str.startswith("https://")):
                continue
            if url_str not in seen:
                seen.add(url_str)
                urls.append(url_str)
        if len(urls) == 0:
            return jsonify({"status": "no_candidates", "discovered_count": 0, "urls": []}), 200
        db_path = app.config["DATABASE"]
        job_id = db.create_scrape_job(urls, db_path)
        from scraper import scrape_api_helper as helper
        helper.run_job_in_background(job_id, urls, db_path)
        return jsonify({"status": "queued", "job_id": job_id, "discovered_count": len(urls), "urls": urls}), 202

    @app.route("/api/jobs/<int:job_id>", methods=["GET"])
    def get_job(job_id: int):
        with db.get_connection(app.config["DATABASE"]) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scrape_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
        if row is None:
            abort(404, description="Job not found")
        return jsonify(dict(row))

    @app.route("/api/jobs/<int:job_id>/items", methods=["GET"])
    def job_items(job_id: int):
        with db.get_connection(app.config["DATABASE"]) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scrape_job_items WHERE job_id = ?", (job_id,))
            items = [dict(row) for row in cursor.fetchall()]
        return jsonify({"items": items, "count": len(items)})

    # -------------------------------------------------------------------
    # Lead discovery endpoint (unchanged from Phase 8C)
    # -------------------------------------------------------------------
    @app.route("/api/discover", methods=["POST"])
    def discover():
        # Step 1: Ensure a request body exists
        raw = request.get_data(cache=False)

        if not raw:
            abort(400, description="Request body is missing")

        # Step 2: Parse JSON
        try:
            payload = json.loads(raw)
        except Exception:
            abort(400, description="Invalid JSON payload")

        if not isinstance(payload, dict):
            abort(400, description="JSON root must be an object")

        # Step 3: Validate industry
        if "industry" not in payload:
            abort(400, description="Missing 'industry' field")

        industry = payload["industry"]

        if not isinstance(industry, str):
            abort(400, description="'industry' must be a string")

        industry = industry.strip()

        if not industry:
            abort(400, description="'industry' cannot be empty")

        # Step 4: Validate location
        if "location" not in payload:
            abort(400, description="Missing 'location' field")

        location = payload["location"]

        if not isinstance(location, str):
            abort(400, description="'location' must be a string")

        location = location.strip()

        if not location:
            abort(400, description="'location' cannot be empty")

        # Step 5: Validate max_results
        max_results = payload.get("max_results", 10)

        if not isinstance(max_results, int) or isinstance(max_results, bool):
            abort(400, description="'max_results' must be an integer")

        if max_results < 1 or max_results > 50:
            abort(
                400,
                description="'max_results' must be between 1 and 50"
            )

        # Step 6: Run discovery
        try:
            results = discover_leads(
                industry=industry,
                location=location,
                max_results=max_results,
            )
        except Exception:
            app.logger.exception("Lead discovery failed")
            return jsonify({
                "error": "Lead discovery failed"
            }), 500

        # Step 7: Return candidate websites
        return jsonify({
            "results": results,
            "count": len(results),
            "industry": industry,
            "location": location,
        }), 200

    # ---------------------------------------------------------------------
    # Error handling – return JSON, hide stack traces.

    @app.route("/api/discover/google-maps", methods=["POST"])
    def discover_google_maps_endpoint():
        # Step 1: Ensure a request body exists
        raw = request.get_data(cache=False)
        if not raw:
            abort(400, description="Request body is missing")
        # Step 2: Parse JSON
        try:
            payload = json.loads(raw)
        except Exception:
            abort(400, description="Invalid JSON payload")
        if not isinstance(payload, dict):
            abort(400, description="JSON root must be an object")
        # Step 3: Validate industry
        if "industry" not in payload:
            abort(400, description="Missing 'industry' field")
        industry = payload["industry"]
        if not isinstance(industry, str):
            abort(400, description="'industry' must be a string")
        industry = industry.strip()
        if not industry:
            abort(400, description="'industry' cannot be empty")
        # Step 4: Validate location
        if "location" not in payload:
            abort(400, description="Missing 'location' field")
        location = payload["location"]
        if not isinstance(location, str):
            abort(400, description="'location' must be a string")
        location = location.strip()
        if not location:
            abort(400, description="'location' cannot be empty")
        # Step 5: Validate max_results
        max_results = payload.get("max_results", 10)
        if not isinstance(max_results, int) or isinstance(max_results, bool):
            abort(400, description="'max_results' must be an integer")
        if max_results < 1 or max_results > 50:
            abort(400, description="'max_results' must be between 1 and 50")
        # Step 6: Run Google Maps discovery
        try:
            results = discover_google_maps(
                industry=industry,
                location=location,
                max_results=max_results,
            )
        except Exception as exc:
            app.logger.exception("Google Maps discovery failed")
            return jsonify({"error": str(exc)}), 500
        # Step 7: Return normalized results
        return jsonify({
            "results": results,
            "count": len(results),
            "industry": industry,
            "location": location,
        }), 200

    # ---------------------------------------------------------------------
    # Free lead discovery endpoint (Phase 12B)
    # ---------------------------------------------------------------------
    @app.route("/api/discover/free", methods=["POST"])
    def discover_free_endpoint():
        # Step 1: Ensure a request body exists
        raw = request.get_data(cache=False)
        if not raw:
            abort(400, description="Request body is missing")
        # Step 2: Parse JSON
        try:
            payload = json.loads(raw)
        except Exception:
            abort(400, description="Invalid JSON payload")
        if not isinstance(payload, dict):
            abort(400, description="JSON root must be an object")
        # Step 3: Validate industry
        if "industry" not in payload:
            abort(400, description="Missing 'industry' field")
        industry = payload["industry"]
        if not isinstance(industry, str):
            abort(400, description="'industry' must be a string")
        industry = industry.strip()
        if not industry:
            abort(400, description="'industry' cannot be empty")
        # Step 4: Validate location
        if "location" not in payload:
            abort(400, description="Missing 'location' field")
        location = payload["location"]
        if not isinstance(location, str):
            abort(400, description="'location' must be a string")
        location = location.strip()
        if not location:
            abort(400, description="'location' cannot be empty")
        # Step 5: Validate max_results
        max_results = payload.get("max_results", 10)
        if not isinstance(max_results, int) or isinstance(max_results, bool):
            abort(400, description="'max_results' must be an integer")
        if max_results < 1 or max_results > 50:
            abort(400, description="'max_results' must be between 1 and 50")
        # Step 6: Run free discovery
        try:
            from scraper.free_lead_discovery import discover_free_leads
            results = discover_free_leads(
                industry=industry,
                location=location,
                max_results=max_results,
            )
        except Exception as exc:
            app.logger.exception("Free lead discovery failed")
            return jsonify({"error": str(exc)}), 500
        # Step 7: Return normalized results
        return jsonify({
            "results": results,
            "count": len(results),
            "industry": industry,
            "location": location,
            "source": "free_web"
        }), 200
    # ---------------------------------------------------------------------
    @app.errorhandler(404)
    def resource_not_found(e):  # pragma: no cover
        return jsonify({"error": e.description}), 404

    @app.errorhandler(400)
    def bad_request_handler(e):  # pragma: no cover
        return jsonify({"error": e.description or "Bad request"}), 400

    @app.errorhandler(405)
    def method_not_allowed_handler(e):  # pragma: no cover
        return jsonify({"error": e.description or "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):  # pragma: no cover
        app.logger.exception("Internal server error")
        return jsonify({"error": "Internal server error"}), 500

    return app

# ----------------------------------------------------------------------------
# When imported, expose ``create_app`` but do not run the app.  The test suite
# imports this module and uses the factory.
# ----------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    # pragma: no cover – used only for manual debugging.
    app = create_app()
    app.run(debug=True)
