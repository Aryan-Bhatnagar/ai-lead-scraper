"""
Trend analysis for the AI Lead Scraper analytics.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from .analytics_models import TimeSeriesPoint, TrendData
import scraper.database as db


class TrendAnalyzer:
    """Analyzes trends in lead data over time."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_time_series(self, days: int = 30) -> TrendData:
        """Get time series data for leads discovery over the specified number of days."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # We'll get the daily counts of leads created in the date range
        # Note: We use the 'created_at' field in the leads table.
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            # We'll group by date (day) for the daily trend
            cursor.execute("""
                SELECT
                    date(created_at) as day,
                    COUNT(*) as count
                FROM leads
                WHERE created_at >= ? AND created_at <= ?
                GROUP BY day
                ORDER BY day
            """, (start_date.isoformat(), end_date.isoformat()))
            daily_rows = cursor.fetchall()

            # For weekly, we group by year and week
            cursor.execute("""
                SELECT
                    strftime('%Y-%W', created_at) as week,
                    COUNT(*) as count
                FROM leads
                WHERE created_at >= ? AND created_at <= ?
                GROUP BY week
                ORDER BY week
            """, (start_date.isoformat(), end_date.isoformat()))
            weekly_rows = cursor.fetchall()

            # For monthly, we group by year and month
            cursor.execute("""
                SELECT
                    strftime('%Y-%m', created_at) as month,
                    COUNT(*) as count
                FROM leads
                WHERE created_at >= ? AND created_at <= ?
                GROUP BY month
                ORDER BY month
            """, (start_date.isoformat(), end_date.isoformat()))
            monthly_rows = cursor.fetchall()

        # Convert to TimeSeriesPoint objects
        daily = [TimeSeriesPoint(timestamp=row[0], count=row[1]) for row in daily_rows]
        weekly = [TimeSeriesPoint(timestamp=row[0], count=row[1]) for row in weekly_rows]
        monthly = [TimeSeriesPoint(timestamp=row[0], count=row[1]) for row in monthly_rows]

        # Calculate growth rate (percentage change from first to last period in daily data)
        growth_rate = 0.0
        if len(daily) >= 2:
            first_count = daily[0].count
            last_count = daily[-1].count
            if first_count != 0:
                growth_rate = ((last_count - first_count) / first_count) * 100

        # Calculate rolling average (using a window of 7 days for daily data)
        rolling_average = []
        if daily:
            counts = [point.count for point in daily]
            window = 7
            for i in range(len(counts)):
                if i < window - 1:
                    # Not enough data for a full window, we can use partial or skip
                    # We'll use the average of available data up to i
                    subset = counts[:i+1]
                    avg = sum(subset) / len(subset)
                else:
                    subset = counts[i - window + 1:i + 1]
                    avg = sum(subset) / len(subset)
                rolling_average.append(round(avg, 2))

        # Calculate moving average (same as rolling average for now, but we can differentiate if needed)
        moving_average = rolling_average.copy()

        return TrendData(
            daily=daily,
            weekly=weekly,
            monthly=monthly,
            growth_rate=round(growth_rate, 2),
            rolling_average=rolling_average,
            moving_average=moving_average
        )