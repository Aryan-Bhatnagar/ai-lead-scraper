"""
Flask application factory for Bilvaleaf Business Development Platform.

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

from dotenv import load_dotenv

load_dotenv()

from pathlib import Path
import sys
from typing import Any, Dict, List

from flask import Flask, jsonify, request, abort
import json
import os
import re
import requests
from urllib.parse import urlparse
from flask_cors import CORS

# Ensure the project root is on the Python path so that we can import the
# `scraper` package regardless of the current working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# Also add the current working directory for safety
if '.' not in sys.path:
    sys.path.insert(0, '.')

# ``scraper.database`` is the only place where the concrete SQLite
# connection is created.  Importing it keeps the pipe to the tests
# straightforward – the test suite changes the ``DATABASE`` key before
# calling ``create_app``.
import scraper.database as db
from api.services import lead_service
from scraper.persistence.lifecycle import LifecycleEngine, InvalidLifecycleTransition
from scraper.analytics.analytics_service import AnalyticsService
from api.services.recommendation_service import RecommendationService
from api.routes.opportunities import register_opportunities_routes
from api.routes.dashboard import register_dashboard_routes

from scraper.lead_discovery import discover_leads
from scraper.google_maps_discovery import discover_google_maps

from scraper.lead_discovery import discover_leads
from scraper.google_maps_discovery import discover_google_maps
from scraper.discovery.orchestrator import DiscoveryOrchestrator
from scraper.discovery.query import DiscoveryQuery

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
    sort_by: str = "id",
    sort_desc: bool = True,
    limit: int | None = None,
    offset: int | None = None,
    filter_source: str | None = None,
    search: str | None = None,
) -> List[Dict[str, Any]]:
    """Return all leads, optionally filtered by:
    * ``status`` – the scraper‑generated status field,
    * ``data_quality`` – the quality bucket,
    * ``lead_status`` – the new CRM lifecycle status,
    * ``filter_source`` – the normalized source (Apollo, Upwork, …),
    * ``search`` – keyword search on company, contact, email, or normalized phone digits.
    ``None`` for any filter means no filtering on that column.

    Supports sorting (default: id DESC) and pagination.
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
    if filter_source:
        clauses.append("(source = ? OR source_url LIKE ?)")
        params.extend([filter_source, f"%{filter_source}%"])

    if search and search.strip():
        s_clean = search.strip()
        clean_digits = re.sub(r'\D', '', s_clean)
        norm_phone_sql = "REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(COALESCE(phone, ''), '+', ''), ' ', ''), '-', ''), '(', ''), ')', ''), '.', '')"
        
        search_clauses = []
        if clean_digits and len(clean_digits) >= 6:
            phone_patterns = [f"%{clean_digits}%"]
            if clean_digits.startswith("91") and len(clean_digits) == 12:
                phone_patterns.append(f"%{clean_digits[2:]}%")
            
            phone_sub = " OR ".join([f"{norm_phone_sql} LIKE ?" for _ in phone_patterns])
            
            # Check if search term is purely a phone number (digits and phone formatting characters only)
            if len(clean_digits) == len(re.sub(r'[\s+()-]', '', s_clean)):
                search_clauses.append(f"({phone_sub})")
                params.extend(phone_patterns)
            else:
                text_pattern = f"%{s_clean}%"
                search_clauses.append(f"({phone_sub} OR company_name LIKE ? OR contact_name LIKE ? OR email LIKE ?)")
                params.extend(phone_patterns + [text_pattern, text_pattern, text_pattern])
        else:
            text_pattern = f"%{s_clean}%"
            search_clauses.append(f"({norm_phone_sql} LIKE ? OR company_name LIKE ? OR contact_name LIKE ? OR email LIKE ? OR CAST(id AS TEXT) = ?)")
            params.extend([text_pattern, text_pattern, text_pattern, text_pattern, s_clean])
        
        clauses.extend(search_clauses)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    # Apply sorting
    valid_sort_fields = ["id", "company_name", "contact_name", "email", "phone",
                         "website", "country", "city", "company_size_estimate",
                         "source", "opportunity_score", "quality_score",
                         "data_quality", "lead_status", "status", "scraped_at",
                         "created_at", "updated_at"]
    if sort_by in valid_sort_fields:
        direction = "DESC" if sort_desc else "ASC"
        query += f" ORDER BY {sort_by} {direction}"
    else:
        query += " ORDER BY scraped_at DESC, id DESC"

    # Apply pagination
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    if offset is not None:
        query += " OFFSET ?"
        params.append(offset)

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
    app = Flask("bilvaleaf_bdp")
    CORS(app, resources={r"/api/*": {"origins": "*"}})  # Enable CORS for development.

    # Apply configuration – ``getattr`` is used so the caller can pass a
    # plain dict or an object with attributes.
    if config is not None:
        app.config.update(config)

    # Determine the database path – default to ``data/leads.db``.
    db_path = Path(app.config.get("DATABASE", "data/leads.db"))
    # store the path in app config for use by endpoints
    app.config["DATABASE"] = str(db_path)

    # Ensure database schema, tables, and migrations are initialized
    try:
        db.initialize_database(db_path)
    except Exception as exc:
        app.logger.warning(f"Database initialization warning: {exc}")

    # Health check endpoint – always available.
    @app.route("/api/health", methods=["GET"])
    def health():  # pragma: no cover - trivial
        return jsonify({"status": "ok"})

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response

    # -------------------------------------------------------------------
    # Leads endpoints
    # -------------------------------------------------------------------
    @app.route("/api/leads", methods=["GET"])
    def list_leads():
        status = request.args.get("status")
        q = request.args.get("data_quality")
        lead_status = request.args.get("lead_status")
        filter_source = request.args.get("source")
        search = request.args.get("search") or request.args.get("q_search")
        sort_by = request.args.get("sort", "id")
        sort_desc = request.args.get("order", "desc").lower() == "desc"
        try:
            limit = int(request.args.get("limit", 50))
        except ValueError:
            limit = 50
        try:
            offset = int(request.args.get("offset", 0))
        except ValueError:
            offset = 0
        leads = get_leads(
            app.config["DATABASE"],
            status,
            q,
            lead_status,
            sort_by=sort_by,
            sort_desc=sort_desc,
            limit=limit,
            offset=offset,
            filter_source=filter_source,
            search=search,
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
    # Lead CRUD endpoints (Phase 20A)
    # -------------------------------------------------------------------
    @app.route("/api/leads", methods=["POST"])
    def create_lead():
        """Create a new lead."""
        raw = request.get_data(cache=False)
        if not raw:
            abort(400, description="Request body is missing")
        try:
            payload = json.loads(raw)
        except Exception:
            abort(400, description="Invalid JSON payload")
        if not isinstance(payload, dict):
            abort(400, description="JSON body must be an object")

        # Validate required fields
        if not payload.get("source_url"):
            abort(400, description="Lead must have a source_url")

        try:
            lead_id = lead_service.create_lead(app.config["DATABASE"], payload)
            lead = lead_service.get_lead_by_id(app.config["DATABASE"], lead_id)
            return jsonify(lead), 201
        except ValueError as e:
            abort(400, description=str(e))
        except Exception as e:
            app.logger.exception("Lead creation failed")
            abort(500, description=f"Lead creation failed: {str(e)}")

    @app.route("/api/leads/<int:lead_id>", methods=["PUT"])
    def update_lead(lead_id: int):
        """Update a lead by ID."""
        raw = request.get_data(cache=False)
        if not raw:
            abort(400, description="Request body is missing")
        try:
            payload = json.loads(raw)
        except Exception:
            abort(400, description="Invalid JSON payload")
        if not isinstance(payload, dict):
            abort(400, description="JSON body must be an object")

        # Prevent updating source_url via this endpoint
        if "source_url" in payload:
            abort(400, description="Cannot update source_url via this endpoint")

        # First check if lead exists
        existing_lead = lead_service.get_lead_by_id(app.config["DATABASE"], lead_id)
        if not existing_lead:
            abort(404, description="Lead not found")

        try:
            updated = lead_service.update_lead(app.config["DATABASE"], lead_id, payload)
            if not updated:
                # This shouldn't happen if the lead exists, but handle just in case
                abort(400, description="Lead update failed")
            lead = lead_service.get_lead_by_id(app.config["DATABASE"], lead_id)
            return jsonify(lead), 200
        except Exception as e:
            app.logger.exception("Lead update failed")
            abort(500, description=f"Lead update failed: {str(e)}")

    @app.route("/api/leads/bulk", methods=["POST"])
    def create_leads_bulk():
        """Create multiple leads."""
        raw = request.get_data(cache=False)
        if not raw:
            abort(400, description="Request body is missing")
        try:
            payload = json.loads(raw)
        except Exception:
            abort(400, description="Invalid JSON payload")
        if not isinstance(payload, dict):
            abort(400, description="JSON body must be an object")

        leads = payload.get("leads")
        if not isinstance(leads, list):
            abort(400, description="'leads' must be a list")
        if len(leads) == 0:
            abort(400, description="'leads' list cannot be empty")

        try:
            lead_ids = lead_service.bulk_create_leads(app.config["DATABASE"], leads)
            return jsonify({"lead_ids": lead_ids, "count": len(lead_ids)}), 201
        except Exception as e:
            app.logger.exception("Bulk lead creation failed")
            abort(500, description=f"Bulk lead creation failed: {str(e)}")

    @app.route("/api/leads/search", methods=["GET"])
    def search_leads():
        """Search leads by various criteria."""
        # Extract query parameters
        filters = {}
        if request.args.get("search"):
            filters["search"] = request.args.get("search")
        if request.args.get("company"):
            filters["company_name"] = request.args.get("company")
        if request.args.get("website"):
            filters["website"] = request.args.get("website")
        if request.args.get("country"):
            filters["country"] = request.args.get("country")
        if request.args.get("city"):
            filters["city"] = request.args.get("city")
        if request.args.get("min_score"):
            try:
                filters["min_score"] = int(request.args.get("min_score"))
            except ValueError:
                abort(400, description="'min_score' must be an integer")
        if request.args.get("max_score"):
            try:
                filters["max_score"] = int(request.args.get("max_score"))
            except ValueError:
                abort(400, description="'max_score' must be an integer")
        if request.args.get("quality_tier"):
            filters["quality_tier"] = request.args.get("quality_tier")
        if request.args.get("source"):
            filters["source"] = request.args.get("source")
        if request.args.get("status"):
            filters["status"] = request.args.get("status")
        if request.args.get("lead_status"):
            filters["lead_status"] = request.args.get("lead_status")

        # Pagination
        try:
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))
        except ValueError:
            abort(400, description="'limit' and 'offset' must be integers")

        # Sorting
        sort_by = request.args.get("sort_by")
        sort_desc = request.args.get("sort_desc", "false").lower() == "true"

        try:
            leads = lead_service.get_leads(
                app.config["DATABASE"],
                filters=filters if filters else None,
                sort_by=sort_by,
                sort_desc=sort_desc,
                limit=limit,
                offset=offset,
            )
            total = lead_service.count_leads(app.config["DATABASE"], filters=filters if filters else None)
            return jsonify({
                "leads": leads,
                "count": len(leads),
                "total": total,
                "limit": limit,
                "offset": offset
            }), 200
        except Exception as e:
            app.logger.exception("Lead search failed")
            abort(500, description=f"Lead search failed: {str(e)}")

    @app.route("/api/leads/filter", methods=["GET"])
    def filter_leads():
        """Filter leads (alias for search with same functionality)."""
        return search_leads()

    @app.route("/api/leads/<int:lead_id>/lifecycle", methods=["PATCH"])
    def update_lead_lifecycle(lead_id: int):
        """Update a lead's lifecycle status with validation."""
        raw = request.get_data(cache=False)
        if not raw:
            abort(400, description="Request body is missing")
        try:
            payload = json.loads(raw)
        except Exception:
            abort(400, description="Invalid JSON payload")
        if not isinstance(payload, dict):
            abort(400, description="JSON body must be an object")

        new_status = payload.get("lead_status")
        if not new_status:
            abort(400, description="Missing 'lead_status' field")

        # First, check if lead exists
        lead = lead_service.get_lead_by_id(app.config["DATABASE"], lead_id)
        if not lead:
            abort(404, description="Lead not found")

        # Validate the lifecycle transition
        current_status = lead.get("lead_status", "NEW")
        try:
            LifecycleEngine.validate(current_status, new_status)
        except InvalidLifecycleTransition:
            abort(400, description=f"Invalid lifecycle transition from '{current_status}' to '{new_status}'")

        # Update the lead's lifecycle status
        try:
            updated = lead_service.update_lead(app.config["DATABASE"], lead_id, {"lead_status": new_status})
            if not updated:
                abort(500, description="Failed to update lead")
            updated_lead = lead_service.get_lead_by_id(app.config["DATABASE"], lead_id)
            return jsonify(updated_lead), 200
        except Exception as e:
            app.logger.exception("Lifecycle update failed")
            abort(500, description=f"Lifecycle update failed: {str(e)}")

    @app.route("/api/leads/statistics", methods=["GET"])
    def get_lead_statistics():
        """Get lead statistics."""
        try:
            stats = lead_service.get_lead_statistics(app.config["DATABASE"])
            return jsonify(stats), 200
        except Exception as e:
            app.logger.exception("Failed to get lead statistics")
            abort(500, description=f"Failed to get lead statistics: {str(e)}")

    @app.route("/api/leads/cities", methods=["GET"])
    def get_unique_cities():
        """Get unique cities from leads for filter dropdown."""
        try:
            with db.get_connection(app.config["DATABASE"]) as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT city FROM leads
                    WHERE city IS NOT NULL AND city != ''
                    ORDER BY city ASC
                """)
                cities = [row[0] for row in cursor.fetchall()]
            return jsonify({"cities": cities, "count": len(cities)}), 200
        except Exception as e:
            app.logger.exception("Failed to get cities")
            abort(500, description=f"Failed to get cities: {str(e)}")

    @app.route("/api/leads/bulk", methods=["DELETE"])
    def bulk_delete_leads():
        """Delete multiple leads by IDs."""
        raw = request.get_data(cache=False)
        if not raw:
            abort(400, description="Request body is missing")
        try:
            payload = json.loads(raw)
        except Exception:
            abort(400, description="Invalid JSON payload")
        if not isinstance(payload, dict):
            abort(400, description="JSON body must be an object")

        lead_ids = payload.get("lead_ids")
        if not isinstance(lead_ids, list):
            abort(400, description="'lead_ids' must be a list")
        if len(lead_ids) == 0:
            abort(400, description="'lead_ids' list cannot be empty")

        # Validate all IDs are integers
        for i, lid in enumerate(lead_ids):
            if not isinstance(lid, int):
                abort(400, description=f"Lead ID at index {i} must be an integer")

        try:
            deleted_count = lead_service.bulk_delete_leads(app.config["DATABASE"], lead_ids)
            return jsonify({"deleted_count": deleted_count}), 200
        except Exception:
            app.logger.exception("Bulk delete failed")
            abort(500, description="Bulk delete failed")

    # -------------------------------------------------------------------
    # Analytics endpoints (Phase 21A)
    # -------------------------------------------------------------------
    @app.route("/api/analytics/overview", methods=["GET"])
    def analytics_overview():
        """Get analytics overview."""
        try:
            analytics_service = AnalyticsService(app.config["DATABASE"])
            data = analytics_service.get_overview()
            return jsonify(data), 200
        except Exception as e:
            app.logger.exception("Analytics overview failed")
            abort(500, description=f"Analytics overview failed: {str(e)}")

    @app.route("/api/analytics/trends", methods=["GET"])
    def analytics_trends():
        """Get analytics trends."""
        try:
            analytics_service = AnalyticsService(app.config["DATABASE"])
            data = analytics_service.get_trends()
            return jsonify(data), 200
        except Exception as e:
            app.logger.exception("Analytics trends failed")
            abort(500, description=f"Analytics trends failed: {str(e)}")

    @app.route("/api/analytics/quality", methods=["GET"])
    def analytics_quality():
        """Get analytics quality."""
        try:
            analytics_service = AnalyticsService(app.config["DATABASE"])
            data = analytics_service.get_quality_analytics()
            return jsonify(data), 200
        except Exception as e:
            app.logger.exception("Analytics quality failed")
            abort(500, description=f"Analytics quality failed: {str(e)}")

    @app.route("/api/analytics/providers", methods=["GET"])
    def analytics_providers():
        """Get analytics providers."""
        try:
            analytics_service = AnalyticsService(app.config["DATABASE"])
            data = analytics_service.get_provider_analytics()
            # Return the list of providers directly
            return jsonify(data), 200
        except Exception as e:
            app.logger.exception("Analytics providers failed")
            abort(500, description=f"Analytics providers failed: {str(e)}")

    @app.route("/api/analytics/lifecycle", methods=["GET"])
    def analytics_lifecycle():
        """Get analytics lifecycle."""
        try:
            analytics_service = AnalyticsService(app.config["DATABASE"])
            data = analytics_service.get_lifecycle_distribution()
            # Return the lifecycle distribution dict directly
            return jsonify(data), 200
        except Exception as e:
            app.logger.exception("Analytics lifecycle failed")
            abort(500, description=f"Analytics lifecycle failed: {str(e)}")

    @app.route("/api/analytics/insights", methods=["GET"])
    def analytics_insights():
        """Get analytics insights."""
        try:
            analytics_service = AnalyticsService(app.config["DATABASE"])
            data = analytics_service.get_insights()
            return jsonify(data), 200
        except Exception as e:
            app.logger.exception("Analytics insights failed")
            abort(500, description=f"Analytics insights failed: {str(e)}")

    # -------------------------------------------------------------------
    # Recommendation endpoints (Phase 21B)
    # -------------------------------------------------------------------
    @app.route("/api/recommendations", methods=["GET"])
    def recommendations_list():
        """Get recommendations for all leads."""
        try:
            rec_service = RecommendationService(app.config["DATABASE"])
            data = rec_service.get_recommendations()
            return jsonify(data), 200
        except Exception as e:
            app.logger.exception("Recommendations list failed")
            abort(500, description=f"Recommendations list failed: {str(e)}")

    # -------------------------------------------------------------------
    # Opportunity endpoints (Phase 22A)
    # -------------------------------------------------------------------
    register_opportunities_routes(app)
    register_dashboard_routes(app)
    print("DEBUG: Dashboard routes registered")

    @app.route("/api/recommendations/<int:lead_id>", methods=["GET"])
    def recommendation_detail(lead_id: int):
        """Get recommendation for a specific lead."""
        try:
            rec_service = RecommendationService(app.config["DATABASE"])
            data = rec_service.get_recommendation(lead_id)
            return jsonify(data), 200
        except ValueError as e:
            abort(404, description=str(e))
        except Exception as e:
            app.logger.exception("Recommendation detail failed")
            abort(500, description=f"Recommendation detail failed: {str(e)}")

    @app.route("/api/recommendations/summary", methods=["GET"])
    def recommendations_summary():
        """Get summary of recommendations."""
        try:
            rec_service = RecommendationService(app.config["DATABASE"])
            data = rec_service.get_recommendations_summary()
            return jsonify(data), 200
        except Exception as e:
            app.logger.exception("Recommendations summary failed")
            abort(500, description=f"Recommendations summary failed: {str(e)}")

    # -------------------------------------------------------------------
    # Outreach Queue endpoints (Phase 10B)
    # -------------------------------------------------------------------
    @app.route("/api/outreach", methods=["GET"])
    def list_outreach():
        lead_id = request.args.get("lead_id", type=int)
        channel = request.args.get("outreach_channel") or request.args.get("channel")
        status = request.args.get("outreach_status") or request.args.get("status")
        step = request.args.get("outreach_step", type=int) or request.args.get("step", type=int)
        source = request.args.get("source")
        industry = request.args.get("industry")
        quality_tier = request.args.get("quality_tier")
        date_preset = request.args.get("date_preset")
        search = request.args.get("search")

        entries = db.get_outreach_entries(
            app.config["DATABASE"],
            lead_id=lead_id,
            outreach_channel=channel,
            outreach_status=status,
            outreach_step=step,
            source=source,
            industry=industry,
            quality_tier=quality_tier,
            date_preset=date_preset,
            search=search,
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
        # Eligibility check – allow active leads (NEW, QUALIFIED, INTERESTED, Enriched, etc.)
        lead_st = (lead.get("lead_status") or "").upper()
        if lead_st in {"REJECTED", "CONVERTED"}:
            abort(400, description=f"Lead not eligible for outreach (status is {lead.get('lead_status')})")
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
        
        payload = request.get_json(silent=True) or {}
        queue_ids = payload.get("queue_ids")
        channel = payload.get("outreach_channel") or payload.get("channel")
        status = payload.get("outreach_status") or payload.get("status")
        step = payload.get("outreach_step") or payload.get("step")
        source = payload.get("source")
        industry = payload.get("industry")
        quality_tier = payload.get("quality_tier")
        date_preset = payload.get("date_preset")
        search = payload.get("search")

        # Import the shared service (local import to avoid circular at module load).
        from scraper import outreach_service as out_srv
        summary = out_srv.process_batch(
            limit=batch_limit,
            retry_limit=retry_limit,
            db_path=app.config["DATABASE"],
            queue_ids=queue_ids,
            outreach_channel=channel,
            outreach_status=status,
            outreach_step=step,
            source=source,
            industry=industry,
            quality_tier=quality_tier,
            date_preset=date_preset,
            search=search,
        )
        return jsonify(summary), 200

    # -------------------------------------------------------------------
    # Outreach Callback & 3-Day Cadence Endpoints
    # -------------------------------------------------------------------
    @app.route("/api/outreach/callback", methods=["POST"])
    def outreach_callback():
        """Callback endpoint called by n8n after sending Email/WhatsApp outreach.

        Payload:
          - queue_id (int)
          - lead_id (int)
          - outreach_status ('SENT' | 'FAILED')
          - outreach_channel ('EMAIL' | 'WHATSAPP') [optional]
          - outreach_step (int) [optional]
          - message_snippet (str) [optional]
        """
        payload = request.get_json(silent=True) or {}

        def _clean_int(val):
            if val is None:
                return None
            try:
                return int(str(val).replace("=", "").strip())
            except (ValueError, TypeError):
                return None

        def _clean_str(val, default=""):
            if val is None:
                return default
            return str(val).replace("=", "").strip()

        queue_id = _clean_int(payload.get("queue_id"))
        lead_id = _clean_int(payload.get("lead_id"))
        outreach_status = _clean_str(payload.get("outreach_status"), "SENT").upper()
        outreach_channel = _clean_str(payload.get("outreach_channel"), "EMAIL").upper()
        step = _clean_int(payload.get("outreach_step"))

        if not queue_id and not lead_id:
            abort(400, description="'queue_id' or 'lead_id' required")

        db_path = app.config["DATABASE"]
        now = db.utc_now()
        from datetime import datetime, timedelta, timezone
        next_24h = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

        with db.get_connection(db_path) as conn:
            cur_entry = None
            if queue_id:
                cur_entry = db.get_outreach_entry_by_id(queue_id, db_path)
            if not cur_entry and lead_id:
                entries = db.get_outreach_entries(db_path, lead_id=lead_id)
                cur_entry = entries[0] if entries else None
                if cur_entry:
                    queue_id = cur_entry["id"]

            if not cur_entry:
                abort(404, description=f"Outreach entry not found for queue_id={queue_id}, lead_id={lead_id}")

            lead_id = cur_entry["lead_id"]
            current_step = step if step is not None else cur_entry.get("outreach_step", 1)

            if outreach_status == "SENT":
                if current_step < 3:
                    new_step = current_step + 1
                    conn.execute(
                        """
                        UPDATE outreach_queue
                        SET outreach_status = 'SENT',
                            outreach_step = ?,
                            last_contacted_at = ?,
                            next_follow_up_at = ?,
                            error_message = NULL,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (new_step, now, next_24h, now, queue_id),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE outreach_queue
                        SET outreach_status = 'COMPLETED',
                            outreach_step = ?,
                            last_contacted_at = ?,
                            next_follow_up_at = NULL,
                            error_message = NULL,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (current_step, now, now, queue_id),
                    )
                # Update lead status to CONTACTED if currently NEW or QUALIFIED
                conn.execute(
                    """
                    UPDATE leads
                    SET lead_status = 'CONTACTED', updated_at = ?
                    WHERE id = ? AND lead_status IN ('NEW', 'QUALIFIED')
                    """,
                    (now, lead_id),
                )
                db.log_outreach_event(
                    lead_id=lead_id,
                    queue_id=queue_id,
                    outreach_step=current_step,
                    outreach_channel=outreach_channel,
                    event_type="SENT",
                    message_snippet=payload.get("message_snippet", f"Step {current_step} sent successfully"),
                    db_path=db_path,
                    conn=conn,
                )
            else:
                conn.execute(
                    """
                    UPDATE outreach_queue
                    SET outreach_status = 'FAILED',
                        error_message = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (payload.get("error_message", "Webhook callback reported failure"), now, queue_id),
                )
                db.log_outreach_event(
                    lead_id=lead_id,
                    queue_id=queue_id,
                    outreach_step=current_step,
                    outreach_channel=outreach_channel,
                    event_type="FAILED",
                    message_snippet=payload.get("error_message", "Callback reported failure"),
                    db_path=db_path,
                    conn=conn,
                )

        return jsonify({"status": "success", "lead_id": lead_id, "queue_id": queue_id}), 200

    @app.route("/api/outreach/enqueue_all", methods=["POST"])
    def enqueue_all_leads():
        """Bulk enqueues all qualified leads with email or phone into outreach_queue."""
        db_path = app.config["DATABASE"]
        now = db.utc_now()

        with db.get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, email, phone FROM leads
                WHERE (email IS NOT NULL AND TRIM(email) != '')
                   OR (phone IS NOT NULL AND TRIM(phone) != '')
                """
            )
            leads = cursor.fetchall()
            enqueued = 0
            skipped = 0

            for l in leads:
                lead_id = l["id"]
                email = (l["email"] or "").strip()
                phone = (l["phone"] or "").strip()
                channel = "EMAIL" if email else "WHATSAPP"

                # Check if active queue entry exists
                active = cursor.execute(
                    """
                    SELECT 1 FROM outreach_queue
                    WHERE lead_id = ? AND outreach_status IN ('PENDING', 'PROCESSING', 'SENT')
                    """,
                    (lead_id,),
                ).fetchone()

                if not active:
                    cursor.execute(
                        """
                        INSERT INTO outreach_queue (
                            lead_id, outreach_channel, outreach_status, outreach_step,
                            created_at, updated_at
                        ) VALUES (?, ?, 'PENDING', 1, ?, ?)
                        """,
                        (lead_id, channel, now, now),
                    )
                    enqueued += 1
                else:
                    skipped += 1

        return jsonify({"enqueued": enqueued, "skipped": skipped}), 200

    @app.route("/api/outreach/clear_all", methods=["POST"])
    def clear_all_queue():
        """Clears/dequeues all outreach items except test lead #2131."""
        db_path = app.config["DATABASE"]
        with db.get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM outreach_queue WHERE lead_id != 2131")
            deleted_count = cursor.rowcount
        return jsonify({"status": "success", "cleared": deleted_count}), 200

    @app.route("/api/outreach/options", methods=["GET"])
    def get_outreach_filter_options():
        """Return available dynamic filter options (sources, industries, tiers) from the database."""
        db_path = app.config["DATABASE"]
        with db.get_connection(db_path) as conn:
            sources = [r[0] for r in conn.execute("SELECT DISTINCT source FROM leads WHERE source IS NOT NULL AND source != '' ORDER BY source").fetchall()]
            raw_industries = [r[0] for r in conn.execute("SELECT DISTINCT industry FROM leads WHERE industry IS NOT NULL AND industry != ''").fetchall()]
            quality_tiers = [r[0] for r in conn.execute("SELECT DISTINCT quality_tier FROM leads WHERE quality_tier IS NOT NULL AND quality_tier != '' ORDER BY quality_tier").fetchall()]
        
        category_rules = {
            "Healthcare & Medical": ["hospital", "medical", "clinic", "doctor", "health", "physician", "pediatric", "dermatologist", "optician", "surgeon", "pathologist", "imaging"],
            "Dental & Oral Care": ["dentist", "dental", "orthodontist", "endodontist", "periodontist"],
            "IT & Software": ["software", "it ", "information technology", "web", "app", "devops", "cloud", "data", "tech", "computer", "analytics", "ai ", "artificial intelligence"],
            "Marketing & Advertising": ["marketing", "advertising", "seo", "media", "brand", "digital marketing", "pr "],
            "Finance & Accounting": ["finance", "financial", "accounting", "accountant", "fintech", "banking", "tax", "audit", "investment"],
            "Real Estate & Construction": ["real estate", "construction", "property", "building", "architect", "contractor"],
            "Education & Training": ["school", "education", "college", "university", "coaching", "training", "learning", "academy"],
            "Beauty & Wellness": ["salon", "spa", "beauty", "fitness", "gym", "wellness", "massage", "tattoo"],
            "Food & Hospitality": ["restaurant", "food", "cafe", "hotel", "catering", "beverage", "bakery"],
            "Legal & Professional Services": ["legal", "lawyer", "attorney", "consulting", "consultant", "bpo", "kpo", "advisory"]
        }

        active_categories = set()
        has_others = False

        for ind in raw_industries:
            matched = False
            ind_lower = ind.lower()
            for cat, keywords in category_rules.items():
                if any(k in ind_lower for k in keywords):
                    active_categories.add(cat)
                    matched = True
                    break
            if not matched:
                has_others = True

        sorted_industries = [cat for cat in category_rules if cat in active_categories]
        if has_others:
            sorted_industries.append("Other Industries")

        return jsonify({
            "sources": sources,
            "industries": sorted_industries,
            "quality_tiers": quality_tiers,
        }), 200

    @app.route("/api/outreach/stats", methods=["GET"])
    def get_outreach_dashboard_stats():
        """Return summary metrics for the Outreach Dashboard."""
        stats = db.get_outreach_stats(app.config["DATABASE"])
        return jsonify(stats), 200

    @app.route("/api/outreach/lead/<int:lead_id>/history", methods=["GET"])
    def get_lead_outreach_history(lead_id: int):
        """Return chronological outreach activity logs for a lead."""
        logs = db.get_outreach_logs_for_lead(lead_id, app.config["DATABASE"])
        return jsonify({"lead_id": lead_id, "logs": logs, "count": len(logs)}), 200

    @app.route("/api/outreach/reply_callback", methods=["POST"])
    def outreach_reply_callback():
        """Callback endpoint called by n8n Reply Classification workflow when a client replies.

        Payload:
          - sender_email (str) [optional]
          - sender_phone (str) [optional]
          - channel ('email' | 'whatsapp') [optional]
          - intent ('POSITIVE' | 'NEGATIVE' | 'OTHER')
          - reply_text (str) [optional]
        """
        payload = request.get_json(silent=True) or {}
        sender_email = payload.get("sender_email")
        sender_phone = payload.get("sender_phone")
        channel = str(payload.get("channel") or "email").replace("=", "").strip().upper()
        intent = str(payload.get("intent") or "OTHER").replace("=", "").strip().upper()
        reply_text = payload.get("reply_text") or payload.get("email_body") or ""

        db_path = app.config["DATABASE"]
        lead = db.find_lead_by_email_or_phone(email=sender_email, phone=sender_phone, db_path=db_path)

        if not lead:
            return jsonify({
                "status": "unmatched",
                "message": f"No lead matched sender_email='{sender_email}' or sender_phone='{sender_phone}'",
            }), 404

        lead_id = lead["id"]
        now = db.utc_now()

        with db.get_connection(db_path) as conn:
            entries = db.get_outreach_entries(db_path, lead_id=lead_id)
            queue_id = entries[0]["id"] if entries else None
            step = entries[0].get("outreach_step", 1) if entries else 1

            if intent == "POSITIVE":
                # Update lead status to INTERESTED
                conn.execute(
                    "UPDATE leads SET lead_status = 'INTERESTED', updated_at = ? WHERE id = ?",
                    (now, lead_id),
                )
                # Stop 3-day follow-up cadence in outreach_queue
                if queue_id:
                    conn.execute(
                        """
                        UPDATE outreach_queue
                        SET outreach_status = 'COMPLETED',
                            next_follow_up_at = NULL,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (now, queue_id),
                    )
                db.log_outreach_event(
                    lead_id=lead_id,
                    queue_id=queue_id,
                    outreach_step=step,
                    outreach_channel=channel,
                    event_type="REPLY_RECEIVED",
                    message_snippet=f"Intent: POSITIVE — {reply_text[:120]}",
                    db_path=db_path,
                    conn=conn,
                )
                new_status = "INTERESTED"

            elif intent == "NEGATIVE":
                # Update lead status to REJECTED
                conn.execute(
                    "UPDATE leads SET lead_status = 'REJECTED', updated_at = ? WHERE id = ?",
                    (now, lead_id),
                )
                # Stop 3-day follow-up cadence in outreach_queue
                if queue_id:
                    conn.execute(
                        """
                        UPDATE outreach_queue
                        SET outreach_status = 'COMPLETED',
                            next_follow_up_at = NULL,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (now, queue_id),
                    )
                db.log_outreach_event(
                    lead_id=lead_id,
                    queue_id=queue_id,
                    outreach_step=step,
                    outreach_channel=channel,
                    event_type="REPLY_RECEIVED",
                    message_snippet=f"Intent: NEGATIVE — {reply_text[:120]}",
                    db_path=db_path,
                    conn=conn,
                )
                new_status = "REJECTED"

            else:  # OTHER
                db.log_outreach_event(
                    lead_id=lead_id,
                    queue_id=queue_id,
                    outreach_step=step,
                    outreach_channel=channel,
                    event_type="REPLY_RECEIVED",
                    message_snippet=f"Intent: OTHER (Manual Team Alerted) — {reply_text[:120]}",
                    db_path=db_path,
                    conn=conn,
                )
                new_status = lead.get("lead_status", "CONTACTED")

        return jsonify({
            "status": "success",
            "lead_id": lead_id,
            "company_name": lead.get("company_name"),
            "intent": intent,
            "new_lead_status": new_status,
        }), 200

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
    # Intelligence endpoints (Phase 15A)
    # -------------------------------------------------------------------
    @app.route("/api/enrich/<int:lead_id>", methods=["POST"])
    def enrich_lead(lead_id: int):
        from api.services.enrichment.engine import uee_engine
        lead = db.get_lead_by_id(lead_id, app.config["DATABASE"])
        if not lead:
            abort(404, description="Lead not found")

        website = lead.get("website")
        company_name = lead.get("company_name", "the company")

        try:
            profile = uee_engine.enrich_lead(lead_id, website or "", company_name)
            return jsonify({"status": "success", "profile": profile}), 200
        except Exception as e:
            app.logger.exception("Lead enrichment failed")
            abort(500, description=f"Enrichment failed: {str(e)}")

    @app.route("/api/enrich/profile/<int:lead_id>", methods=["GET"])
    def get_enrichment_profile(lead_id: int):
        from api.services.enrichment.engine import uee_engine
        profile = uee_engine.get_profile(lead_id)
        if not profile:
            return jsonify({"lead_id": lead_id, "profile": None}), 200
        return jsonify({"lead_id": lead_id, "profile": profile}), 200

    @app.route("/api/intelligence/<int:lead_id>", methods=["GET"])
    def get_intelligence(lead_id: int):

        insights = db.get_ai_insights_by_lead_id(lead_id, app.config["DATABASE"])
        if not insights:
            return jsonify({"lead_id": lead_id, "insights": None}), 200
        return jsonify({"lead_id": lead_id, "insights": dict(insights)}), 200

    @app.route("/api/intelligence/generate/<int:lead_id>", methods=["POST"])
    def generate_intelligence(lead_id: int):
        from api.services.ai_intelligence import intelligence_manager
        from api.services.enrichment.engine import uee_engine

        lead = db.get_lead_by_id(lead_id, app.config["DATABASE"])
        if not lead:
            abort(404, description="Lead not found")

        # Ensure we have a business profile first
        profile = uee_engine.get_profile(lead_id)
        if not profile:
            # Trigger on-the-fly enrichment if profile is missing
            website = lead.get("website", "")
            company_name = lead.get("company_name", "the company")
            profile = uee_engine.enrich_lead(lead_id, website, company_name)

        company_description = lead.get("company_description", "")

        try:
            insights = intelligence_manager.get_or_generate_intelligence(
                lead_id=lead_id,
                business_profile=profile,
                context=company_description
            )
            return jsonify({"status": "success", "insights": insights}), 200
        except Exception as e:
            app.logger.exception("AI Intelligence generation failed")
            abort(500, description=f"AI Generation failed: {str(e)}")

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

        # Step 6: Run discovery using orchestrator with legacy persistence
        try:
            # Create query for the orchestrator
            query = DiscoveryQuery(
                industry=industry,
                location=location,
                max_results=max_results
            )

            # Map frontend provider IDs to backend source names
            providers_input = payload.get("providers") or payload.get("provider")
            sources = None
            if isinstance(providers_input, list):
                sources = ["google_search" if p == "google" else p for p in providers_input]
            elif isinstance(providers_input, str) and providers_input.strip():
                sources = ["google_search" if providers_input.strip() == "google" else providers_input.strip()]

            # Create orchestrator with legacy persistence enabled
            orchestrator = DiscoveryOrchestrator(legacy_persistence=True)

            # Run the discovery across requested sources
            summary = orchestrator.run(query, sources=sources)

            # Convert scored leads to format expected by frontend (filtering & interleaving by requested sources)
            all_scored = summary.scored_leads
            
            if sources:
                norm_sources = [s.lower() for s in sources]
                source_groups = {}
                for sl in all_scored:
                    prov_src = sl.lead.provenance.source if (getattr(sl, "lead", None) and getattr(sl.lead, "provenance", None) and sl.lead.provenance.source) else ""
                    src = (prov_src or getattr(sl.lead, "source", "") or "").lower()
                    web = (getattr(sl.lead, "website", "") or "").lower()
                    
                    matched = False
                    for req_src in norm_sources:
                        if req_src in src or (req_src == "google_maps" and ("google_maps" in src or "maps" in src or "place" in web)) or (req_src == "freelancer" and "freelancer" in web) or (req_src == "upwork" and "upwork" in web) or (req_src == "linkedin" and "linkedin" in web):
                            source_groups.setdefault(req_src, []).append(sl)
                            matched = True
                            break

                # Round-robin interleave across requested sources
                interleaved = []
                max_group_len = max([len(v) for v in source_groups.values()]) if source_groups else 0
                for i in range(max_group_len):
                    for req_src in norm_sources:
                        grp = source_groups.get(req_src, [])
                        if i < len(grp):
                            interleaved.append(grp[i])
                
                selected_leads = interleaved if interleaved else all_scored
            else:
                selected_leads = all_scored

            results = []
            for scored_lead in selected_leads[:max_results]:
                lead = scored_lead.lead
                detected_ind = getattr(lead, "industry", None) or getattr(lead, "category", None) or getattr(lead, "source_type", None)
                src_val = getattr(lead, "source", "") or (lead.provenance.source if getattr(lead, "provenance", None) else "")
                sk_list = getattr(lead, "skills", []) or getattr(lead, "categories", []) or []
                sk_str = ", ".join(sk_list) if isinstance(sk_list, list) else str(sk_list)
                results.append({
                    "title": lead.company_name or "",
                    "url": lead.website or "",
                    "description": lead.description or "",
                    "industry": detected_ind or "Target Client Prospect",
                    "has_requirement_evidence": getattr(lead, "has_requirement_evidence", False) or getattr(lead, "has_intent", False),
                    "source": src_val,
                    "ai_summary": getattr(lead, "ai_summary", None) or lead.description or "",
                    "outreach_strategy": getattr(lead, "outreach_strategy", None) or "",
                    "buying_signals": getattr(lead, "buying_signals", None) or "",
                    "proposals_str": getattr(lead, "proposals_str", None) or "",
                    "posted_time_str": getattr(lead, "posted_time_str", None) or "",
                    "time_left_str": getattr(lead, "time_left_str", None) or "",
                    "skills": sk_list,
                    "skills_str": sk_str,
                    "email": getattr(lead, "emails", [""])[0] if (getattr(lead, "emails", None) and len(lead.emails) > 0) else "Apply & Chat Directly ↗",
                    "phone": getattr(lead, "phones", [""])[0] if (getattr(lead, "phones", None) and len(lead.phones) > 0) else "Verified Client Project",
                    "score": getattr(scored_lead, "overall_score", 95)
                })
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
            app.logger.exception("Free prospect intelligence failed")
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
    # Lead enrichment endpoint (Phase 12C)
    # ---------------------------------------------------------------------
    @app.route("/api/leads/enrich", methods=["POST"])
    def enrich_leads_endpoint():
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
        # Step 3: Validate 'leads' field
        if "leads" not in payload:
            abort(400, description="Missing 'leads' field")
        leads = payload["leads"]
        if not isinstance(leads, list):
            abort(400, description="'leads' must be a list")
        if len(leads) == 0:
            abort(400, description="'leads' list cannot be empty")
        # Step 4: Validate each lead
        for i, lead in enumerate(leads):
            if not isinstance(lead, dict):
                abort(400, description=f"Lead at index {i} must be an object")
            if "website" not in lead or not lead["website"] or not isinstance(lead["website"], str):
                abort(400, description=f"Lead at index {i} must have a non-empty 'website' string")
            # Optional: validate website format
            website = lead["website"].strip()
            if not website.lower().startswith(("http://", "https://")):
                # We'll still allow it as it will be normalized in enrichment
                pass
        # Step 5: Run enrichment
        try:
            from scraper.lead_enrichment import enrich_leads
            enriched_leads = enrich_leads(leads)
        except Exception as exc:
            app.logger.exception("Lead enrichment failed")
            return jsonify({"error": str(exc)}), 500
        # Step 6: Return results
        return jsonify({
            "results": enriched_leads,
            "count": len(enriched_leads)
        }), 200

    # ---------------------------------------------------------------------
    # Standalone email extraction endpoint (Phase 12F)
    # ---------------------------------------------------------------------
    @app.route("/api/leads/extract-emails", methods=["POST"])
    def extract_emails_endpoint():
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
        # Step 3: Validate 'leads' field
        if "leads" not in payload:
            abort(400, description="Missing 'leads' field")
        leads = payload["leads"]
        if not isinstance(leads, list):
            abort(400, description="'leads' must be a list")
        if len(leads) == 0:
            abort(400, description="'leads' list cannot be empty")
        # Step 4: Validate each lead
        for i, lead in enumerate(leads):
            if not isinstance(lead, dict):
                abort(400, description=f"Lead at index {i} must be an object")
            if "website" not in lead or not lead["website"] or not isinstance(lead["website"], str):
                abort(400, description=f"Lead at index {i} must have a non-empty 'website' string")
        # Step 5: Run email extraction & persist found emails to SQLite database
        try:
            from scraper.email_extractor import extract_emails_batch
            results = extract_emails_batch(leads)
            
            # Step 5b: Persist extracted emails to database
            db_path = app.config["DATABASE"]
            updated_count = 0
            with db.get_connection(db_path) as conn:
                cursor = conn.cursor()
                for item in results:
                    found_email = item.get("email")
                    website_url = item.get("website")
                    lead_id = item.get("id")
                    if found_email and isinstance(found_email, str) and found_email.strip():
                        email_clean = found_email.strip()
                        if lead_id:
                            cursor.execute(
                                "UPDATE leads SET email = ?, lead_status = CASE WHEN lead_status = 'NEW' THEN 'QUALIFIED' ELSE lead_status END, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                (email_clean, lead_id)
                            )
                            updated_count += cursor.rowcount
                        elif website_url:
                            cursor.execute(
                                "UPDATE leads SET email = ?, lead_status = CASE WHEN lead_status = 'NEW' THEN 'QUALIFIED' ELSE lead_status END, updated_at = CURRENT_TIMESTAMP WHERE website = ?",
                                (email_clean, website_url)
                            )
                            updated_count += cursor.rowcount
                conn.commit()
            app.logger.info(f"Persisted {updated_count} extracted emails to leads database")
        except Exception as exc:
            app.logger.exception("Email extraction failed")
            return jsonify({"error": str(exc)}), 500
        # Step 6: Return results
        return jsonify({
            "results": results,
            "count": len(results),
            "db_updated": updated_count
        }), 200

    # ---------------------------------------------------------------------
    # Free discovery + enrichment endpoint (Phase 12C)
    # ---------------------------------------------------------------------
    @app.route("/api/discover/free-and-enrich", methods=["POST"])
    def discover_free_and_enrich_endpoint():
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
            discovered_leads = discover_free_leads(
                industry=industry,
                location=location,
                max_results=max_results,
            )
        except Exception as exc:
            app.logger.exception("Free prospect intelligence failed")
            return jsonify({"error": str(exc)}), 500
        # Step 7: Run enrichment on discovered leads
        try:
            from scraper.lead_enrichment import enrich_leads
            enriched_leads = enrich_leads(discovered_leads)
        except Exception as exc:
            app.logger.exception("Lead enrichment failed")
            return jsonify({"error": str(exc)}), 500
        # Step 8: Return results
        return jsonify({
            "results": enriched_leads,
            "count": len(enriched_leads),
            "industry": industry,
            "location": location,
            "source": "free_web"
        }), 200

    # ---------------------------------------------------------------------
    # Team Members & Work Assignment API Endpoints
    # ---------------------------------------------------------------------
    @app.route("/api/team", methods=["GET"])
    def get_team_members():
        db_path = app.config["DATABASE"]
        with db.get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM team_members ORDER BY id ASC")
            members = [dict(row) for row in cursor.fetchall()]
            
            # Fetch assigned lead count per member
            cursor.execute("SELECT assigned_member_id, COUNT(*) as lead_count FROM leads WHERE assigned_member_id IS NOT NULL GROUP BY assigned_member_id")
            counts = {row["assigned_member_id"]: row["lead_count"] for row in cursor.fetchall()}
            
            for m in members:
                m["domains"] = json.loads(m["domains"]) if isinstance(m["domains"], str) and m["domains"].startswith("[") else [m["domains"]]
                m["expertise_tags"] = json.loads(m["expertise_tags"]) if isinstance(m["expertise_tags"], str) and m["expertise_tags"].startswith("[") else []
                m["assigned_count"] = counts.get(m["id"], 0)
                
        return jsonify({"team": members, "count": len(members)}), 200

    @app.route("/api/team", methods=["POST"])
    def add_team_member():
        payload = request.get_json(silent=True) or {}
        name = payload.get("name", "").strip()
        role = payload.get("role", "Specialist").strip()
        domains = payload.get("domains", ["Development"])
        expertise_tags = payload.get("expertise_tags", [])
        email = payload.get("email", f"{name.lower().replace(' ', '.')}@bilvaleaf.com").strip()

        if not name:
            return jsonify({"error": "Employee name is required"}), 400

        db_path = app.config["DATABASE"]
        with db.get_connection(db_path) as conn:
            cursor = conn.cursor()
            domains_json = json.dumps(domains) if isinstance(domains, list) else json.dumps([domains])
            tags_json = json.dumps(expertise_tags) if isinstance(expertise_tags, list) else json.dumps([])
            
            cursor.execute("""
                INSERT INTO team_members (name, email, role, domains, expertise_tags, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?)
            """, (name, email, role, domains_json, tags_json, db.utc_now()))
            member_id = cursor.lastrowid
            
        return jsonify({"message": f"Team member {name} created successfully", "id": member_id}), 201

    @app.route("/api/leads/<int:lead_id>/assign", methods=["POST"])
    def assign_lead_to_member(lead_id: int):
        payload = request.get_json(silent=True) or {}
        member_id = payload.get("member_id")
        member_name = payload.get("member_name")
        member_domain = payload.get("member_domain", "")
        notes = payload.get("notes", "")

        if not member_id or not member_name:
            return jsonify({"error": "member_id and member_name are required"}), 400

        db_path = app.config["DATABASE"]
        with db.get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE leads 
                SET assigned_member_id = ?, 
                    assigned_member_name = ?, 
                    assigned_member_domain = ?, 
                    assigned_at = CURRENT_TIMESTAMP, 
                    assignment_notes = ?, 
                    lead_status = 'QUALIFIED',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (member_id, member_name, member_domain, notes, lead_id))
            if cursor.rowcount == 0:
                return jsonify({"error": f"Lead with id {lead_id} not found"}), 404

        return jsonify({
            "message": f"Lead #{lead_id} successfully assigned to {member_name}",
            "lead_id": lead_id,
            "assigned_to": member_name,
            "lead_status": "QUALIFIED"
        }), 200

    @app.route("/api/leads/assign-direct", methods=["POST"])
    def assign_lead_direct():
        payload = request.get_json(silent=True) or {}
        member_id = payload.get("member_id")
        member_name = payload.get("member_name")
        member_domain = payload.get("member_domain", "")
        lead_data = payload.get("lead", {})

        if not member_id or not member_name or not lead_data:
            return jsonify({"error": "member_id, member_name, and lead payload are required"}), 400

        url = lead_data.get("url") or lead_data.get("source_url") or lead_data.get("website")
        if not url:
            return jsonify({"error": "Lead source URL is required"}), 400

        db_path = app.config["DATABASE"]
        with db.get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM leads WHERE source_url = ? OR website = ?", (url, url))
            row = cursor.fetchone()
            if row:
                lead_id = row["id"]
                cursor.execute("""
                    UPDATE leads 
                    SET assigned_member_id = ?, 
                        assigned_member_name = ?, 
                        assigned_member_domain = ?, 
                        assigned_at = CURRENT_TIMESTAMP, 
                        lead_status = 'QUALIFIED',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (member_id, member_name, member_domain, lead_id))
            else:
                title = lead_data.get("title") or lead_data.get("company_name") or "Client Lead"
                source = lead_data.get("source", "discover")
                desc = lead_data.get("description") or lead_data.get("ai_summary") or ""
                ai_sum = lead_data.get("ai_summary", "")
                buying = lead_data.get("buying_signals", "")
                outreach = lead_data.get("outreach_strategy", "")
                
                cursor.execute("""
                    INSERT INTO leads (
                        company_name, source_url, website, company_description, source, 
                        lead_status, assigned_member_id, assigned_member_name, 
                        assigned_member_domain, assigned_at, ai_summary, 
                        buying_signals, outreach_strategy, scraped_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'QUALIFIED', ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (title, url, url, desc, source, member_id, member_name, member_domain, ai_sum, buying, outreach))
                lead_id = cursor.lastrowid

        return jsonify({
            "message": f"Lead successfully saved & assigned to {member_name}",
            "lead_id": lead_id,
            "assigned_to": member_name,
            "lead_status": "QUALIFIED"
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
