"""
Analytics service for coordinating analytics operations.
"""

from __future__ import annotations

from typing import Dict, Any
from pathlib import Path

from .analytics_engine import AnalyticsEngine


class AnalyticsService:
    """Service layer for analytics operations."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self.engine = AnalyticsEngine(db_path)

    def get_overview(self) -> Dict[str, Any]:
        """Get overall analytics overview."""
        overview = self.engine.get_overview_stats()
        quality = self.engine.get_quality_analytics()
        return {
            "total_leads": overview.total_leads,
            "total_companies": overview.total_companies,
            "average_score": overview.average_score,
            "median_score": overview.median_score,
            "highest_score": overview.highest_score,
            "lowest_score": overview.lowest_score,
            "lead_sources": overview.lead_sources,
            "countries": overview.countries,
            "cities": overview.cities,
            "industries": overview.industries,
            "lifecycle_distribution": overview.lifecycle_distribution,
            "quality_distribution": {
                "excellent": quality.excellent,
                "good": quality.good,
                "average": quality.average,
                "poor": quality.poor,
                "unknown": quality.unknown,
            },
        }

    def get_trends(self) -> Dict[str, Any]:
        """Get trend analysis data."""
        trends = self.engine.get_time_series()

        return {
            "daily": [
                {"timestamp": point.timestamp, "count": point.count}
                for point in trends.daily
            ],
            "weekly": [
                {"timestamp": point.timestamp, "count": point.count}
                for point in trends.weekly
            ],
            "monthly": [
                {"timestamp": point.timestamp, "count": point.count}
                for point in trends.monthly
            ],
            "growth_rate": trends.growth_rate,
            "rolling_average": trends.rolling_average,
            "moving_average": trends.moving_average,
        }

    def get_quality_analytics(self) -> Dict[str, Any]:
        """Get quality analytics based on score thresholds."""
        quality = self.engine.get_quality_analytics()
        return {
            "excellent": quality.excellent,
            "good": quality.good,
            "average": quality.average,
            "poor": quality.poor,
            "unknown": quality.unknown,
        }

    def get_provider_analytics(self) -> Dict[str, Any]:
        """Get provider analytics."""
        providers = self.engine.get_provider_analytics()
        return {
            "providers": [
                {
                    "provider_name": p.provider_name,
                    "total_leads": p.total_leads,
                    "average_leads_per_provider": p.average_leads_per_provider,
                    "success_rate": p.success_rate,
                    "failure_rate": p.failure_rate,
                    "duplicate_percentage": p.duplicate_percentage,
                    "unique_percentage": p.unique_percentage,
                }
                for p in providers
            ]
        }

    def get_lifecycle_distribution(self) -> Dict[str, Any]:
        """Get lifecycle distribution."""
        return self.engine.get_lifecycle_distribution()

    def get_insights(self) -> Dict[str, Any]:
        """Get business insights."""
        from .insights import get_business_insights
        return get_business_insights(self.db_path)