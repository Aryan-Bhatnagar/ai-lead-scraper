"""
Business insights generation for the AI Lead Scraper analytics.
"""

from __future__ import annotations

from typing import List, Dict, Any
import scraper.database as db


class InsightsGenerator:
    """Generates business insights from lead data."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_top_performing_industries(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top performing industries by average score and lead count."""
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    industry,
                    COUNT(*) as lead_count,
                    AVG(quality_score) as avg_score
                FROM leads
                WHERE industry IS NOT NULL AND industry != '' AND quality_score IS NOT NULL
                GROUP BY industry
                ORDER BY avg_score DESC, lead_count DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
        return [
            {
                "industry": row[0],
                "lead_count": row[1],
                "average_score": round(row[2], 2)
            }
            for row in rows
        ]

    def get_best_countries(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get best countries by average score and lead count."""
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    country,
                    COUNT(*) as lead_count,
                    AVG(quality_score) as avg_score
                FROM leads
                WHERE country IS NOT NULL AND country != '' AND quality_score IS NOT NULL
                GROUP BY country
                ORDER BY avg_score DESC, lead_count DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
        return [
            {
                "country": row[0],
                "lead_count": row[1],
                "average_score": round(row[2], 2)
            }
            for row in rows
        ]

    def get_most_valuable_sources(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most valuable sources (domains) by average score and lead count."""
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            # Extract domain from source_url (simplified)
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
                    COUNT(*) as lead_count,
                    AVG(quality_score) as avg_score
                FROM leads
                WHERE source_url IS NOT NULL AND source_url != '' AND quality_score IS NOT NULL
                GROUP BY source_domain
                ORDER BY avg_score DESC, lead_count DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
        return [
            {
                "source": row[0],
                "lead_count": row[1],
                "average_score": round(row[2], 2)
            }
            for row in rows
        ]

    def get_highest_quality_segments(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get highest quality segments (combination of industry and country)."""
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    industry,
                    country,
                    COUNT(*) as lead_count,
                    AVG(quality_score) as avg_score
                FROM leads
                WHERE industry IS NOT NULL AND industry != ''
                  AND country IS NOT NULL AND country != ''
                  AND quality_score IS NOT NULL
                GROUP BY industry, country
                ORDER BY avg_score DESC, lead_count DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
        return [
            {
                "industry": row[0],
                "country": row[1],
                "lead_count": row[2],
                "average_score": round(row[3], 2)
            }
            for row in rows
        ]

    def get_most_contacted_leads(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most contacted leads (based on outreach attempts).
        We'll join with outreach_queue to count contact attempts per lead.
        """
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    l.id,
                    l.company_name,
                    l.contact_name,
                    COUNT(oq.id) as contact_attempts
                FROM leads l
                LEFT JOIN outreach_queue oq ON l.id = oq.lead_id
                GROUP BY l.id, l.company_name, l.contact_name
                ORDER BY contact_attempts DESC, l.company_name
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
        return [
            {
                "lead_id": row[0],
                "company_name": row[1],
                "contact_name": row[2],
                "contact_attempts": row[3]
            }
            for row in rows
        ]

    def get_highest_conversion_states(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get states/countries with highest conversion rates (where lead_status = CUSTOMER)."""
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    country,
                    COUNT(*) as total_leads,
                    SUM(CASE WHEN lead_status = 'CUSTOMER' THEN 1 ELSE 0 END) as converted_leads
                FROM leads
                WHERE country IS NOT NULL AND country != ''
                GROUP BY country
                HAVING total_leads > 0
                ORDER BY (CAST(converted_leads AS FLOAT) / total_leads) DESC, total_leads DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
        return [
            {
                "country": row[0],
                "total_leads": row[1],
                "converted_leads": row[2],
                "conversion_rate": round((row[2] / row[1]) * 100, 2) if row[1] > 0 else 0.0
            }
            for row in rows
        ]


def get_business_insights(db_path: str) -> dict:
    """Convenience function to get all business insights."""
    generator = InsightsGenerator(db_path)
    return {
        "top_performing_industries": generator.get_top_performing_industries(),
        "best_countries": generator.get_best_countries(),
        "most_valuable_sources": generator.get_most_valuable_sources(),
        "highest_quality_segments": generator.get_highest_quality_segments(),
        "most_contacted_leads": generator.get_most_contacted_leads(),
        "highest_conversion_states": generator.get_highest_conversion_states(),
    }