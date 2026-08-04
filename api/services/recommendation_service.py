"""
Recommendation service for providing recommendation data to the API layer.
"""

from __future__ import annotations

from typing import Any, Dict, List
from pathlib import Path

from scraper.recommendations.recommendation_engine import RecommendationEngine
from scraper.recommendations.recommendation_models import Recommendation
import scraper.database as db


class RecommendationService:
    """Service layer for recommendation operations."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self.engine = RecommendationEngine()

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get recommendations for all leads.

        Returns:
            A list of dictionaries, each representing a recommendation.
        """
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads")
            rows = cursor.fetchall()
            leads = [dict(row) for row in rows]

        return [
            self._lead_to_recommendation_dict(lead)
            for lead in leads
        ]

    def get_recommendation(self, lead_id: int) -> Dict[str, Any]:
        """
        Get a recommendation for a specific lead by ID.

        Args:
            lead_id: The ID of the lead to get a recommendation for.

        Returns:
            A dictionary representing the recommendation.

        Raises:
            ValueError: If the lead is not found.
        """
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Lead with id {lead_id} not found")
            lead = dict(row)

        return self._lead_to_recommendation_dict(lead)

    def get_recommendations_summary(self) -> Dict[str, Any]:
        """
        Get a summary of recommendations across all leads.

        Returns:
            A dictionary representing the summary.
        """
        recommendations = self.get_recommendations()
        total = len(recommendations)
        if total == 0:
            return {
                "total_leads": 0,
                "priority_distribution": {},
                "next_action_distribution": {},
                "average_confidence": 0.0,
                "average_estimated_conversion": 0.0
            }

        priority_counts = {}
        action_counts = {}
        total_confidence = 0.0
        total_conversion = 0.0

        for rec in recommendations:
            p = rec["priority"]
            a = rec["next_action"]
            priority_counts[p] = priority_counts.get(p, 0) + 1
            action_counts[a] = action_counts.get(a, 0) + 1
            total_confidence += rec["confidence"]
            total_conversion += rec["estimated_conversion"]

        return {
            "total_leads": total,
            "priority_distribution": priority_counts,
            "next_action_distribution": action_counts,
            "average_confidence": round(total_confidence / total, 2),
            "average_estimated_conversion": round(total_conversion / total, 2)
        }

    def _lead_to_recommendation_dict(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a lead dictionary to a recommendation dictionary."""
        recommendation: Recommendation = self.engine.generate_recommendation(lead)
        return {
            "lead_id": recommendation.lead_id,
            "priority": recommendation.priority,
            "next_action": recommendation.next_action,
            "confidence": recommendation.confidence,
            "reasons": recommendation.reasons,
            "suggested_outreach": recommendation.suggested_outreach,
            "risk_level": recommendation.risk_level,
            "estimated_conversion": recommendation.estimated_conversion
        }