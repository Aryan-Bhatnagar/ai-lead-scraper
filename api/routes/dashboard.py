"""
Dashboard API endpoints.
"""
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timedelta
import sqlalchemy
from sqlalchemy import text
import scraper.database as db

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


def _get_conn():
    # Use the same DB path as the main app; we need to get it from Flask current_app
    # Since we are in a blueprint, we can't directly access current_app without request context.
    # We'll use the same pattern as other routes: the DB path is stored in the app config,
    # but we need to get it from the current app. We'll use a helper that reads from
    # the global db module's default path, but better to get from current_app.
    # For simplicity, we'll use the same approach as in analytics_service: they take db_path.
    # We'll import the app from the current context? Instead, we can get the db path from
    # the Flask g object? Not available. We'll use a trick: we can get the app from
    # current_app proxy if we are in a request context. Since these endpoints are only
    # called during a request, we can use flask.current_app.
    from flask import current_app
    return db.get_connection(current_app.config["DATABASE"])


@dashboard_bp.route("/summary", methods=["GET"])
def dashboard_summary():
    """Return summary statistics for the dashboard."""
    with _get_conn() as conn:
        cursor = conn.cursor()
        # Total leads
        cursor.execute("SELECT COUNT(*) FROM leads")
        total_leads = cursor.fetchone()[0]

        # Leads added today
        today = datetime.now().date()
        cursor.execute(
            "SELECT COUNT(*) FROM leads WHERE DATE(created_at) = ?",
            (today.isoformat(),)
        )
        today_leads = cursor.fetchone()[0]

        # Leads added this week (Monday to Sunday)
        week_start = today - timedelta(days=today.weekday())
        cursor.execute(
            "SELECT COUNT(*) FROM leads WHERE DATE(created_at) >= ?",
            (week_start.isoformat(),)
        )
        week_leads = cursor.fetchone()[0]

        # Top countries
        cursor.execute("""
            SELECT country, COUNT(*) as count
            FROM leads
            WHERE country IS NOT NULL AND country != ''
            GROUP BY country
            ORDER BY count DESC
            LIMIT 5
        """)
        top_countries = [{"country": row[0], "count": row[1]} for row in cursor.fetchall()]

        # Top cities
        cursor.execute("""
            SELECT city, COUNT(*) as count
            FROM leads
            WHERE city IS NOT NULL AND city != ''
            GROUP BY city
            ORDER BY count DESC
            LIMIT 5
        """)
        top_cities = [{"city": row[0], "count": row[1]} for row in cursor.fetchall()]

        # Top industries
        cursor.execute("""
            SELECT industry, COUNT(*) as count
            FROM leads
            WHERE industry IS NOT NULL AND industry != ''
            GROUP BY industry
            ORDER BY count DESC
            LIMIT 5
        """)
        top_industries = [{"industry": row[0], "count": row[1]} for row in cursor.fetchall()]

        # Average discovery time (if we have scraped_at and created_at)
        # We'll approximate as the average time between scraped_at and created_at in seconds
        cursor.execute("""
            SELECT AVG(
                (CASE
                    WHEN scraped_at IS NOT NULL AND scraped_at != ''
                    THEN (strftime('%s', scraped_at) - strftime('%s', created_at))
                    ELSE 0
                END)
            ) FROM leads
        """)
        avg_discovery_seconds = cursor.fetchone()[0] or 0
        avg_discovery_hours = round(avg_discovery_seconds / 3600, 2)

        # Duplicate rate (approximate: leads with same source_url? but source_url is unique)
        # We'll compute duplicate company names as a proxy
        cursor.execute("""
            SELECT
                (COUNT(*) - COUNT(DISTINCT company_name)) * 100.0 / COUNT(*)
            FROM leads
            WHERE company_name IS NOT NULL AND company_name != ''
        """)
        duplicate_rate = cursor.fetchone()[0] or 0

        # Repository growth (total leads)
        # Already have total_leads

    return jsonify({
        "total_leads": total_leads,
        "leads_added_today": today_leads,
        "leads_added_this_week": week_leads,
        "top_countries": top_countries,
        "top_cities": top_cities,
        "top_industries": top_industries,
        "average_discovery_hours": avg_discovery_hours,
        "duplicate_rate": round(duplicate_rate, 2),
        "repository_growth": total_leads  # same as total_leads for now
    })


@dashboard_bp.route("/activity", methods=["GET"])
def dashboard_activity():
    """Return daily activity counts for the last 30 days."""
    with _get_conn() as conn:
        cursor = conn.cursor()
        thirty_days_ago = (datetime.now() - timedelta(days=30)).date()
        cursor.execute("""
            SELECT DATE(created_at) as day, COUNT(*) as count
            FROM leads
            WHERE DATE(created_at) >= ?
            GROUP BY day
            ORDER BY day
        """, (thirty_days_ago.isoformat(),))
        rows = cursor.fetchall()
        activity = [{"date": row[0], "count": row[1]} for row in rows]
    return jsonify({"activity": activity})


@dashboard_bp.route("/providers", methods=["GET"])
def dashboard_providers():
    """Return provider statistics."""
    with _get_conn() as conn:
        cursor = conn.cursor()
        # We need to get provider from source_url; we'll extract domain as a proxy
        cursor.execute("""
            SELECT
                CASE
                    WHEN source_url LIKE 'http://%' THEN
                        SUBSTR(source_url, 8,
                            CASE
                                WHEN INSTR(SUBSTR(source_url, 8), '/') > 0
                                THEN INSTR(SUBSTR(source_url, 8), '/') - 1
                                ELSE LENGTH(SUBSTR(source_url, 8))
                            END
                        )
                    WHEN source_url LIKE 'https://%' THEN
                        SUBSTR(source_url, 9,
                            CASE
                                WHEN INSTR(SUBSTR(source_url, 9), '/') > 0
                                THEN INSTR(SUBSTR(source_url, 9), '/') - 1
                                ELSE LENGTH(SUBSTR(source_url, 9))
                            END
                        )
                    ELSE source_url
                END as provider,
                COUNT(*) as total,
                AVG(quality_score) as avg_score,
                SUM(CASE WHEN data_quality IN ('HIGH', 'MEDIUM') THEN 1 ELSE 0 END) as success_count
            FROM leads
            WHERE source_url IS NOT NULL AND source_url != ''
            GROUP BY provider
            ORDER BY total DESC
        """)
        rows = cursor.fetchall()
        providers = []
        for row in rows:
            provider, total, avg_score, success_count = row
            success_rate = (success_count / total * 100) if total > 0 else 0
            providers.append({
                "provider": provider or "unknown",
                "total_leads": total,
                "average_score": round(avg_score or 0, 2),
                "success_rate": round(success_rate, 2)
            })
    return jsonify({"providers": providers})


@dashboard_bp.route("/growth", methods=["GET"])
def dashboard_growth():
    """Return week-over-week and month-over-month growth."""
    with _get_conn() as conn:
        cursor = conn.cursor()
        today = datetime.now().date()
        # This week Monday
        this_week_start = today - timedelta(days=today.weekday())
        # Last week Monday
        last_week_start = this_week_start - timedelta(days=7)
        # This month start
        this_month_start = today.replace(day=1)
        # Last month start
        if today.month == 1:
            last_month_start = today.replace(year=today.year-1, month=12, day=1)
        else:
            last_month_start = today.replace(month=today.month-1, day=1)

        # This week count
        cursor.execute(
            "SELECT COUNT(*) FROM leads WHERE DATE(created_at) >= ?",
            (this_week_start.isoformat(),)
        )
        this_week = cursor.fetchone()[0]

        # Last week count
        cursor.execute(
            "SELECT COUNT(*) FROM leads WHERE DATE(created_at) >= ? AND DATE(created_at) < ?",
            (last_week_start.isoformat(), this_week_start.isoformat())
        )
        last_week = cursor.fetchone()[0]

        # This month count
        cursor.execute(
            "SELECT COUNT(*) FROM leads WHERE DATE(created_at) >= ?",
            (this_month_start.isoformat(),)
        )
        this_month = cursor.fetchone()[0]

        # Last month count
        cursor.execute(
            "SELECT COUNT(*) FROM leads WHERE DATE(created_at) >= ? AND DATE(created_at) < ?",
            (last_month_start.isoformat(), this_month_start.isoformat())
        )
        last_month = cursor.fetchone()[0]

        wow_growth = ((this_week - last_week) / last_week * 100) if last_week > 0 else 0
        mom_growth = ((this_month - last_month) / last_month * 100) if last_month > 0 else 0

    return jsonify({
        "week_over_week": {
            "this_week": this_week,
            "last_week": last_week,
            "growth_percent": round(wow_growth, 2)
        },
        "month_over_month": {
            "this_month": this_month,
            "last_month": last_month,
            "growth_percent": round(mom_growth, 2)
        }
    })


def register_dashboard_routes(app):
    """Register dashboard routes with the Flask application."""
    app.register_blueprint(dashboard_bp)