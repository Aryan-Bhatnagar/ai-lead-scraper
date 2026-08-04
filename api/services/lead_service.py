"""
Lead service layer for business logic related to leads.
Provides functions for CRUD operations, filtering, sorting, pagination,
bulk operations, lifecycle transitions, and statistics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

import scraper.database as db
from scraper.database import LEAD_STATUSES
from scraper.persistence.lifecycle import LifecycleEngine, InvalidLifecycleTransition


def _apply_filters(
    base_query: str,
    params: list,
    filters: dict[str, Any],
) -> tuple[str, list]:
    """Apply filters to a SQL query.

    Supported filters:
    - company_name (str): case-insensitive partial match
    - website (str): exact match
    - country (str): exact match
    - city (str): exact match
    - min_score (int): quality_score >= value
    - max_score (int): quality_score <= value
    - quality_tier (str): data_quality exact match
    - source (str): source_url contains
    - status (str): scraper status exact match
    - lead_status (str): CRM lead_status exact match
    """
    clauses: list[str] = []
    if filters.get("company_name"):
        clauses.append("company_name LIKE ?")
        params.append(f"%{filters['company_name']}%")
    if filters.get("website"):
        clauses.append("website = ?")
        params.append(filters["website"])
    if filters.get("country"):
        clauses.append("country = ?")
        params.append(filters["country"])
    if filters.get("city"):
        clauses.append("city = ?")
        params.append(filters["city"])
    if filters.get("min_score") is not None:
        clauses.append("quality_score >= ?")
        params.append(filters["min_score"])
    if filters.get("max_score") is not None:
        clauses.append("quality_score <= ?")
        params.append(filters["max_score"])
    if filters.get("quality_tier"):
        clauses.append("data_quality = ?")
        params.append(filters["quality_tier"])
    if filters.get("source"):
        clauses.append("source_url LIKE ?")
        params.append(f"%{filters['source']}%")
    if filters.get("status"):
        clauses.append("status = ?")
        params.append(filters["status"])
    if filters.get("lead_status"):
        clauses.append("lead_status = ?")
        params.append(filters["lead_status"])

    if clauses:
        base_query += " WHERE " + " AND ".join(clauses)
    return base_query, params


def _apply_sorting(
    base_query: str,
    sort_by: Optional[str],
    sort_desc: bool = False,
) -> str:
    """Apply sorting to a SQL query.

    Supported sort fields: id, company_name, quality_score, data_quality,
    lead_status, status, scraped_at, created_at, updated_at, website, country, city.
    Default sort by id ascending.
    """
    valid_fields = {
        "id": "id",
        "company_name": "company_name",
        "quality_score": "quality_score",
        "data_quality": "data_quality",
        "lead_status": "lead_status",
        "status": "status",
        "scraped_at": "scraped_at",
        "created_at": "created_at",
        "updated_at": "updated_at",
        "website": "website",
        "country": "country",
        "city": "city",
    }
    if sort_by and sort_by in valid_fields:
        direction = "DESC" if sort_desc else "ASC"
        base_query += f" ORDER BY {valid_fields[sort_by]} {direction}"
    else:
        # default
        base_query += " ORDER BY id ASC"
    return base_query


def get_leads(
    db_path: Path | str,
    *,
    filters: Optional[dict[str, Any]] = None,
    sort_by: Optional[str] = None,
    sort_desc: bool = False,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Get leads with filtering, sorting, and pagination.

    Args:
        db_path: Path to SQLite database.
        filters: Dictionary of filter criteria (see _apply_filters).
        sort_by: Field to sort by (see _apply_sorting for valid fields).
        sort_desc: Whether to sort descending.
        limit: Maximum number of rows to return.
        offset: Number of rows to skip.

    Returns:
        List of lead dictionaries.
    """
    base_query = "SELECT * FROM leads"
    params: list = []

    if filters:
        base_query, params = _apply_filters(base_query, params, filters)

    base_query = _apply_sorting(base_query, sort_by, sort_desc)

    if limit is not None:
        base_query += " LIMIT ?"
        params.append(limit)
    if offset is not None:
        base_query += " OFFSET ?"
        params.append(offset)

    with db.get_connection(db_path) as conn:
        cursor = conn.execute(base_query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def count_leads(db_path: Path | str, filters: Optional[dict[str, Any]] = None) -> int:
    """Count leads matching filters.

    Args:
        db_path: Path to SQLite database.
        filters: Dictionary of filter criteria (same as get_leads).

    Returns:
        Number of leads matching filters.
    """
    base_query = "SELECT COUNT(*) FROM leads"
    params: list = []
    if filters:
        base_query, params = _apply_filters(base_query, params, filters)
    with db.get_connection(db_path) as conn:
        cursor = conn.execute(base_query, params)
        row = cursor.fetchone()
        return row[0] if row else 0


def create_lead(db_path: Path | str, lead: dict[str, Any]) -> int:
    """Create a new lead.

    Args:
        db_path: Path to SQLite database.
        lead: Dictionary of lead data (must include source_url for uniqueness).

    Returns:
        The ID of the newly created lead.

    Raises:
        ValueError: If source_url is missing.
    """
    if not lead.get("source_url"):
        raise ValueError("Lead must have a source_url")
    # Use upsert_lead which will insert if not exists or update if exists.
    # For creation we expect it to be new, but upsert is fine.
    lead_id = db.upsert_lead(lead, db_path)
    return lead_id


def get_lead_by_id(db_path: Path | str, lead_id: int) -> dict[str, Any] | None:
    """Get a lead by its ID.

    Args:
        db_path: Path to SQLite database.
        lead_id: Lead ID.

    Returns:
        Lead dictionary or None if not found.
    """
    return db.get_lead_by_id(lead_id, db_path)


def update_lead(
    db_path: Path | str,
    lead_id: int,
    updates: dict[str, Any],
) -> bool:
    """Update a lead by ID.

    Only updates fields that are present in the LEAD_COLUMNS (except source_url
    which is immutable via upsert). The lead_status field can be updated via
    this function, but note that upsert_lead does not touch lead_status, so
    manual updates to lead_status are preserved.

    Args:
        db_path: Path to SQLite database.
        lead_id: Lead ID.
        updates: Dictionary of fields to update.

    Returns:
        True if a row was updated, False if lead_id not found.
    """
    # Remove fields that should not be updated via this function
    updates = {k: v for k, v in updates.items() if k != "source_url"}
    if not updates:
        return False

    # Add updated_at timestamp
    updates["updated_at"] = db.utc_now()

    columns = ", ".join(f"{k} = :{k}" for k in updates.keys())
    params = {**updates, "id": lead_id}

    with db.get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE leads SET {columns} WHERE id = :id",
            params,
        )
        return cursor.rowcount > 0


def delete_lead(db_path: Path | str, lead_id: int) -> bool:
    """Delete a lead by ID.

    Args:
        db_path: Path to SQLite database.
        lead_id: Lead ID.

    Returns:
        True if a row was deleted, False if not found.
    """
    return db.delete_lead(lead_id, db_path)


def bulk_create_leads(db_path: Path | str, leads: list[dict[str, Any]]) -> list[int]:
    """Create multiple leads.

    Args:
        db_path: Path to SQLite database.
        leads: List of lead dictionaries.

    Returns:
        List of lead IDs for the created leads.
    """
    ids = []
    for lead in leads:
        try:
            lead_id = create_lead(db_path, lead)
            ids.append(lead_id)
        except ValueError:
            # Skip leads without source_url
            continue
    return ids


def bulk_update_leads(
    db_path: Path | str,
    updates: list[dict[str, Any]],
) -> int:
    """Update multiple leads.

    Each element in updates should be a dict with an 'id' key and other fields
    to update.

    Args:
        db_path: Path to SQLite database.
        updates: List of dictionaries, each containing 'id' and fields to update.

    Returns:
        Number of leads successfully updated.
    """
    updated_count = 0
    for update in updates:
        lead_id = update.pop("id", None)
        if lead_id is None:
            continue
        if update_lead(db_path, lead_id, update):
            updated_count += 1
    return updated_count


def bulk_delete_leads(db_path: Path | str, lead_ids: list[int]) -> int:
    """Delete multiple leads.

    Args:
        db_path: Path to SQLite database.
        lead_ids: List of lead IDs to delete.

    Returns:
        Number of leads successfully deleted.
    """
    deleted_count = 0
    for lead_id in lead_ids:
        if delete_lead(db_path, lead_id):
            deleted_count += 1
    return deleted_count


def validate_lead_status_transition(
    current_status: str,
    new_status: str,
) -> bool:
    """Validate a lead status transition using the lifecycle state machine.

    Args:
        current_status: Current lead_status.
        new_status: Desired lead_status.

    Returns:
        True if transition is valid, False otherwise.
    """
    try:
        LifecycleEngine.validate(current_status, new_status)
        return True
    except InvalidLifecycleTransition:
        return False


def update_lead_lifecycle_status(
    db_path: Path | str,
    lead_id: int,
    new_status: str,
) -> dict[str, Any] | None:
    """Update a lead's lifecycle status with validation using the lifecycle state machine.

    Args:
        db_path: Path to SQLite database.
        lead_id: Lead ID.
        new_status: Desired lead_status.

    Returns:
        Updated lead dictionary if successful, None if lead not found or
        transition invalid.

    Raises:
        ValueError: If new_status is not a valid lead status.
    """
    # Validate that new_status is a known lifecycle state
    try:
        LifecycleEngine.coerce(new_status)
    except ValueError:
        raise ValueError(f"Invalid lead status: {new_status}")

    lead = get_lead_by_id(db_path, lead_id)
    if not lead:
        return None

    current_status = lead.get("lead_status", "NEW")
    try:
        LifecycleEngine.validate(current_status, new_status)
    except InvalidLifecycleTransition:
        return None

    if update_lead(db_path, lead_id, {"lead_status": new_status}):
        return get_lead_by_id(db_path, lead_id)
    return None


def get_lead_statistics(db_path: Path | str) -> dict[str, Any]:
    """Get various statistics about leads.

    Returns a dictionary with:
    - total_leads: total number of leads
    - lead_sources: count of leads by source_url domain (or 'unknown')
    - quality_distribution: count of leads by data_quality
    - lifecycle_distribution: count of leads by lead_status
    - average_score: average quality_score (float)
    - top_companies: list of top 10 company names by frequency

    Args:
        db_path: Path to SQLite database.

    Returns:
        Dictionary of statistics.
    """
    with db.get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Total leads
        cursor.execute("SELECT COUNT(*) FROM leads")
        total_leads = cursor.fetchone()[0]

        # Lead sources (extract domain from source_url)
        cursor.execute("""
            SELECT
                CASE
                    WHEN source_url LIKE 'http://%' THEN
                        SUBSTR(source_url, 8,
                            CASE
                                WHEN INSTR(SUBSTR(source_url, 8), '/') > 0
                                THEN INSTR(SUBSTR(source_url, 8), '/') - 1
                                ELSE LENGTH(SUBSTR(source_url, 8)) + 1
                            END)
                    WHEN source_url LIKE 'https://%' THEN
                        SUBSTR(source_url, 9,
                            CASE
                                WHEN INSTR(SUBSTR(source_url, 9), '/') > 0
                                THEN INSTR(SUBSTR(source_url, 9), '/') - 1
                                ELSE LENGTH(SUBSTR(source_url, 9)) + 1
                            END)
                    ELSE
                        source_url
                END AS source_domain,
                COUNT(*) AS count
            FROM leads
            GROUP BY source_domain
            ORDER BY count DESC
        """)
        lead_sources = [
            {"source": row[0] or "unknown", "count": row[1]} for row in cursor.fetchall()
        ]

        # Quality distribution
        cursor.execute("""
            SELECT data_quality, COUNT(*) AS count
            FROM leads
            GROUP BY data_quality
            ORDER BY count DESC
        """)
        quality_distribution = [
            {"quality": row[0] or "unknown", "count": row[1]} for row in cursor.fetchall()
        ]

        # Lifecycle distribution
        cursor.execute("""
            SELECT lead_status, COUNT(*) AS count
            FROM leads
            GROUP BY lead_status
            ORDER BY count DESC
        """)
        lifecycle_distribution = [
            {"status": row[0], "count": row[1]} for row in cursor.fetchall()
        ]

        # Average score
        cursor.execute("SELECT AVG(quality_score) FROM leads WHERE quality_score IS NOT NULL")
        avg_row = cursor.fetchone()
        average_score = float(avg_row[0]) if avg_row and avg_row[0] is not None else 0.0

        # Top companies (by frequency)
        cursor.execute("""
            SELECT company_name, COUNT(*) AS count
            FROM leads
            WHERE company_name IS NOT NULL AND company_name != ''
            GROUP BY company_name
            ORDER BY count DESC
            LIMIT 10
        """)
        top_companies = [
            {"company": row[0], "count": row[1]} for row in cursor.fetchall()
        ]

        return {
            "total_leads": total_leads,
            "lead_sources": lead_sources,
            "quality_distribution": quality_distribution,
            "lifecycle_distribution": lifecycle_distribution,
            "average_score": average_score,
            "top_companies": top_companies,
        }