"""Flask application factory for AI Lead Scraper.

This module implements a fully‑fledged Flask app that
* reads configuration from a supplied dictionary,
* attaches CORS for development, and
* exposes a small REST API for leads and scrape jobs.

Only thin wrappers around :mod:`scraper.database` are used – the
actual database access logic lives there so the tests can monkey‑patch
the database path.

The factory accepts a ``config`` mapping which may specify:
    - ``TESTING`` – makes the returned app suitable for unit tests;
    - ``DATABASE`` – an SQLite file path.  When omitted, the production
      database at ``data/leads.db`` is used.

All endpoints return JSON with appropriate status codes and use
parameterized SQL to avoid injection.

The file intentionally contains no ``if __name__ == "__main__"``
block – the application is started through the standard WSGI
frontend used by the tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from flask import Flask, jsonify, request, abort
from flask_cors import CORS

# ``scraper.database`` is the only place where the concrete SQLite
# connection is created.  Importing it keeps the pipe to the tests
# straightforward – the test suite changes the ``DATABASE`` key before
# calling ``create_app``.
import scraper.database as db

# ---------------------------------------------------------------------------
# Helper functions – thin wrappers that delegate to the database module.  The
# database module exposes ``get_lead_by_id`` and ``get_all_scrape_jobs``.  We add
# a ``get_leads`` that supports optional filtering.
# ---------------------------------------------------------------------------

def get_leads(db_path: Path | str, filter_status: str | None = None, filter_q: str | None = None) -> List[Dict[str, Any]]:
    """Return all leads, optionally filtered by status or data quality.

    The helper accepts ``None`` for a missing filter, matching the API
    behaviour.
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

    # --- Leads ------------------------------------------------------------
    @app.route("/api/leads", methods=["GET"])
    def list_leads():
        status = request.args.get("status")
        q = request.args.get("data_quality")
        leads = get_leads(
            app.config["DATABASE"],
            status,
            q,
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

    # --- Jobs ------------------------------------------------------------
    @app.route("/api/jobs", methods=["GET"])
    def list_jobs():
        with db.get_connection(app.config["DATABASE"]) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scrape_jobs")
            jobs = [dict(row) for row in cursor.fetchall()]
        return jsonify({"jobs": jobs, "count": len(jobs)})

    @app.route("/api/jobs", methods=["POST"])
    def create_job():
        data = request.get_json(force=True, silent=True)
        if not data or "urls" not in data:
            abort(400, description="Missing 'urls' field")
        urls = data["urls"]
        if not isinstance(urls, list) or len(urls) == 0:
            abort(400, description="`urls` must be a non-empty list")
        for u in urls:
            if not isinstance(u, str) or not u.strip():
                abort(400, description="All `urls` must be non-empty strings")
        db_path = app.config["DATABASE"]
        job_id = db.create_scrape_job(urls, db_path)
        from scraper import scrape_api_helper as helper
        helper.run_job_in_background(job_id, urls, db_path)
        resp = {"job_id": job_id, "status": "queued"}
        return jsonify(resp), 202

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

    # ---------------------------------------------------------------------
    # Error handling – return JSON, hide stack traces.
    # ---------------------------------------------------------------------
    @app.errorhandler(404)
    def resource_not_found(e):  # pragma: no cover
        return jsonify({"error": e.description}), 404

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
