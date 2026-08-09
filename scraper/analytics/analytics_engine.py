"""
Analytics engine for computing various metrics from the lead database.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from .analytics_models import (
    OverviewStats,
    TimeSeriesPoint,
    TrendData,
    QualityAnalytics,
    ProviderAnalytics,
    BusinessInsights,
    AnalyticsResult,
)
import scraper.database as db


def _opportunity_high_threshold() -> int:
    """Return the 'high' band for opportunity scores from lead_scoring.yaml.

    The score model's high band is unreachable if analytics hardcodes a value
    that doesn't match the config — keep the two in sync here.
    """
    import yaml
    from pathlib import Path
    for candidate in (
        Path.cwd() / "config" / "lead_scoring.yaml",
        Path(__file__).resolve().parent.parent.parent / "config" / "lead_scoring.yaml",
    ):
        if candidate.exists():
            try:
                with open(candidate, "r", encoding="utf-8") as fh:
                    cfg = yaml.safe_load(fh) or {}
                return int(cfg.get("opportunity_thresholds", {}).get("high", 80))
            except Exception:
                pass
    return 80


class AnalyticsEngine:
    """Core analytics engine for computing metrics from the lead database."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def get_overview_stats(self) -> OverviewStats:
        """Compute overall statistics about the leads."""
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Total leads
            cursor.execute("SELECT COUNT(*) FROM leads")
            total_leads = cursor.fetchone()[0]

            # Total unique companies (based on company_name, ignoring empty/null)
            cursor.execute(
                "SELECT COUNT(DISTINCT company_name) FROM leads WHERE company_name IS NOT NULL AND company_name != ''"
            )
            total_companies = cursor.fetchone()[0]

            # AI-scored leads (have a real opportunity score from the AI
            # enrichment pipeline).  CAST guards against text values (some
            # legacy rows stored '' — and '' > 0 is true for TEXT in SQLite).
            cursor.execute(
                "SELECT COUNT(*) FROM leads WHERE CAST(opportunity_score AS INTEGER) > 0"
            )
            ai_scored_leads = cursor.fetchone()[0]

            # High-quality leads (AI opportunity score in the high band, or an
            # excellent/good quality tier from the scoring engine)
            high_threshold = _opportunity_high_threshold()
            cursor.execute(
                f"SELECT COUNT(*) FROM leads WHERE CAST(opportunity_score AS INTEGER) >= {high_threshold} "
                "OR LOWER(COALESCE(quality_tier, '')) IN ('excellent', 'good')"
            )
            high_quality_leads = cursor.fetchone()[0]

            # Average, median, min, max of the AI opportunity score — this is the
            # headline "AI Score" surfaced across the CRM.  Fall back to
            # quality_score only when no opportunity scores exist yet.
            cursor.execute(
                "SELECT CAST(opportunity_score AS INTEGER) FROM leads "
                "WHERE CAST(opportunity_score AS INTEGER) > 0"
            )
            scores = [row[0] for row in cursor.fetchall()]
            if not scores:
                cursor.execute(
                    "SELECT quality_score FROM leads WHERE quality_score IS NOT NULL"
                )
                scores = [row[0] for row in cursor.fetchall()]
            if scores:
                average_score = sum(scores) / len(scores)
                sorted_scores = sorted(scores)
                n = len(sorted_scores)
                if n % 2 == 0:
                    median_score = (sorted_scores[n//2 - 1] + sorted_scores[n//2]) / 2
                else:
                    median_score = sorted_scores[n//2]
                highest_score = max(scores)
                lowest_score = min(scores)
            else:
                average_score = 0.0
                median_score = 0.0
                highest_score = 0
                lowest_score = 0

            # Lead sources — prefer the normalized `source` column (Apollo,
            # Upwork, Google Maps…) and fall back to the source_url domain for
            # legacy rows that predate the column.
            cursor.execute(
                "SELECT source, source_url FROM leads WHERE source IS NOT NULL AND source != '' "
                "OR source_url IS NOT NULL AND source_url != ''"
            )
            rows = cursor.fetchall()
            lead_sources = {}
            for src, url in rows:
                name = src
                if not name:
                    try:
                        if url.startswith('http://'):
                            url = url[7:]
                        elif url.startswith('https://'):
                            url = url[8:]
                        name = url.split('/')[0]
                    except Exception:
                        name = 'unknown'
                    if not name:
                        name = 'unknown'
                # Map raw provider keys to friendly names
                friendly = {
                    "google_maps": "Google Maps",
                    "google_maps_scraper_kit": "Google Maps Kit",
                    "google_search": "Google Search",
                    "website_discovery": "Website Discovery",
                    "apollo": "Apollo",
                    "apify": "Apify",
                    "upwork": "Upwork",
                    "freelancer": "Freelancer",
                    "guru": "Guru",
                    "peopleperhour": "PeoplePerHour",
                    "zoominfo": "ZoomInfo",
                    "lusha": "Lusha",
                    "linkedin": "LinkedIn",
                }
                name = friendly.get(name.lower(), name)
                # Normalize search result domains to "Google Search"
                if not src or src == '':
                    search_domains = ['techasoft.com', 'builtin.com', 'ambitionbox.com', 'webhopers.in',
                                      'goodfirms.co', 'careers.webdew.com', 'bebotechnologies.com', 'fixnhour.com', 'brandveda.in',
                                      'techbehemoths.com', 'digitalgriot.com', 'f6s.com', 'rankexdigital.com',
                                      'justdial.com', 'sulekha.com', 'aeroleads.com']
                    if any(d in name.lower() for d in search_domains):
                        name = 'Google Search'
                lead_sources[name] = lead_sources.get(name, 0) + 1

            # Countries
            cursor.execute("SELECT country FROM leads WHERE country IS NOT NULL AND country != ''")
            countries = [row[0] for row in cursor.fetchall()]
            country_counts = {}
            for country in countries:
                country_counts[country] = country_counts.get(country, 0) + 1

            # Cities
            cursor.execute("SELECT city FROM leads WHERE city IS NOT NULL AND city != ''")
            cities = [row[0] for row in cursor.fetchall()]
            city_counts = {}
            for city in cities:
                city_counts[city] = city_counts.get(city, 0) + 1

            # Industries
            cursor.execute("SELECT industry FROM leads WHERE industry IS NOT NULL AND industry != ''")
            industries = [row[0] for row in cursor.fetchall()]
            industry_counts = {}
            for industry in industries:
                industry_counts[industry] = industry_counts.get(industry, 0) + 1

            # Lifecycle distribution (lead_status)
            cursor.execute("SELECT lead_status FROM leads")
            lifecycle_statuses = [row[0] for row in cursor.fetchall()]
            lifecycle_dist = {}
            for status in lifecycle_statuses:
                lifecycle_dist[status] = lifecycle_dist.get(status, 0) + 1

            # Quality distribution (data_quality)
            cursor.execute("SELECT data_quality FROM leads")
            quality_values = [row[0] for row in cursor.fetchall()]
            quality_dist = {}
            for q in quality_values:
                quality_dist[q] = quality_dist.get(q, 0) + 1

        return OverviewStats(
            total_leads=total_leads,
            total_companies=total_companies,
            ai_scored_leads=ai_scored_leads,
            high_quality_leads=high_quality_leads,
            average_score=round(average_score, 2),
            median_score=round(median_score, 2),
            highest_score=highest_score,
            lowest_score=lowest_score,
            lead_sources=lead_sources,
            countries=country_counts,
            cities=city_counts,
            industries=industry_counts,
            lifecycle_distribution=lifecycle_dist,
            quality_distribution=quality_dist,
        )

    def get_quality_analytics(self) -> QualityAnalytics:
        """Compute quality analytics based on score thresholds."""
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT quality_score, quality_tier FROM leads")
            rows = cursor.fetchall()

        excellent = good = average = unknown = 0
        for score, tier in rows:
            if score is None or score == 0:
                unknown += 1
            elif tier:
                # Use the quality_tier field which is already computed by the scoring engine
                tier_lower = tier.lower()
                if tier_lower == "excellent":
                    excellent += 1
                elif tier_lower == "good":
                    good += 1
                elif tier_lower == "average":
                    average += 1
                else:
                    unknown += 1
            else:
                # Fallback to score-based thresholds if tier is not available
                if score >= 70:
                    excellent += 1
                elif score >= 50:
                    good += 1
                elif score >= 30:
                    average += 1
                else:
                    average += 1  # Below 30 still goes to average as lowest tier

        return QualityAnalytics(
            excellent=excellent,
            good=good,
            average=average,
            unknown=unknown,
        )

    def get_provider_analytics(self) -> List[ProviderAnalytics]:
        """Compute analytics per discovery provider (based on the source column).

        Returns only the four primary sources:
        1. Google Maps
        2. Upwork
        3. Apollo
        4. Google Search
        """
        # Prefer the normalized `source` column; fall back to source_url domain
        # for legacy rows. The data_quality drives success/failure rates.
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT source, source_url, data_quality
                FROM leads
                WHERE (source IS NOT NULL AND source != '')
                   OR (source_url IS NOT NULL AND source_url != '')
            """)
            rows = cursor.fetchall()

        friendly = {
            "google_maps": "Google Maps",
            "google_maps_scraper_kit": "Google Maps",
            "google_search": "Google Search",
            "website_discovery": "Website Discovery",
            "apollo": "Apollo",
            "apify": "Apify",
            "upwork": "Upwork",
            "freelancer": "Freelancer",
            "guru": "Guru",
            "peopleperhour": "PeoplePerHour",
            "zoominfo": "ZoomInfo",
            "lusha": "Lusha",
            "linkedin": "LinkedIn",
        }

        # Search result domains that should be categorized as "Google Search"
        search_domains = [
            'techasoft.com', 'builtin.com', 'ambitionbox.com', 'webhopers.in',
            'goodfirms.co', 'careers.webdew.com', 'bebotechnologies.com', 'fixnhour.com', 'brandveda.in',
            'techbehemoths.com', 'digitalgriot.com', 'f6s.com', 'rankexdigital.com',
            'justdial.com', 'sulekha.com', 'aeroleads.com'
        ]

        # Group by normalized provider category
        # We'll consolidate into 4 primary categories
        category_data = {
            "Google Maps": {'total': 0, 'success': 0, 'failure': 0},
            "Upwork": {'total': 0, 'success': 0, 'failure': 0},
            "Apollo": {'total': 0, 'success': 0, 'failure': 0},
            "Google Search": {'total': 0, 'success': 0, 'failure': 0},
        }

        for src, url, quality in rows:
            # Determine the normalized source name
            domain = src
            if not domain:
                try:
                    if url.startswith('http://'):
                        url = url[7:]
                    elif url.startswith('https://'):
                        url = url[8:]
                    domain = url.split('/')[0]
                except Exception:
                    domain = 'unknown'
                if not domain:
                    domain = 'unknown'

            domain_lower = domain.lower()

            # Categorize into one of the 4 primary sources
            category = None

            # Check if source column has a known value
            if src and src != '':
                src_lower = src.lower()
                if src_lower in ('google_maps', 'google_maps_scraper_kit'):
                    category = "Google Maps"
                elif src_lower == 'upwork':
                    category = "Upwork"
                elif src_lower == 'apollo':
                    category = "Apollo"
                elif src_lower == 'google_search':
                    category = "Google Search"
                else:
                    # Fall through to URL-based detection
                    pass

            # If not categorized by source column, infer from URL domain
            if not category:
                # Check if it's a known search result domain -> Google Search
                if any(d in domain_lower for d in search_domains):
                    category = "Google Search"
                else:
                    # Try friendly mapping
                    friendly_name = friendly.get(domain_lower, domain)
                    # Only map to our 4 categories if it matches
                    if friendly_name in category_data:
                        category = friendly_name

            # If still not categorized, skip (don't show unknown/other providers)
            if not category:
                continue

            # Update category stats
            category_data[category]['total'] += 1
            quality_lower = quality.lower() if quality else ''
            if quality_lower in ('high', 'medium', 'excellent', 'good'):
                category_data[category]['success'] += 1
            elif quality_lower in ('low', 'average'):
                category_data[category]['failure'] += 1

        # Now compute the ProviderAnalytics for each of the 4 categories
        providers = []
        total_leads_all = sum(data['total'] for data in category_data.values())

        for domain, data in category_data.items():
            total = data['total']
            success = data['success']
            failure = data['failure']
            success_rate = (success / total * 100) if total > 0 else 0.0
            failure_rate = (failure / total * 100) if total > 0 else 0.0

            # Calculate average leads per provider (across the 4 displayed providers)
            avg_leads = round(total_leads_all / 4, 2) if total_leads_all > 0 else 0.0

            providers.append(ProviderAnalytics(
                provider_name=domain,
                total_leads=total,
                average_leads_per_provider=avg_leads,
                success_rate=round(success_rate, 2),
                failure_rate=round(failure_rate, 2),
                duplicate_percentage=0.0,
                unique_percentage=100.0,
            ))

        # Sort by total_leads descending
        providers.sort(key=lambda p: p.total_leads, reverse=True)
        return providers

    def get_lifecycle_distribution(self) -> Dict[str, int]:
        """Get the distribution of leads by lifecycle status (lead_status)."""
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT lead_status, COUNT(*) FROM leads GROUP BY lead_status")
            rows = cursor.fetchall()
        return {status: count for status, count in rows}

    def get_time_series(self, days: int = 30) -> TrendData:
        """
        Get time series data for lead discoveries (based on scraped_at or created_at).
        We'll use the `scraped_at` field if available, otherwise `created_at`.
        We'll return daily, weekly, and monthly aggregates.
        """
        # We'll compute the date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            # We'll use the scraped_at field, but if it's null we can use created_at.
            # We'll convert the string to date for grouping. We assume the format is ISO-like.
            # We'll do the grouping in Python for simplicity.
            cursor.execute("""
                SELECT
                    COALESCE(scraped_at, created_at) as date_str
                FROM leads
                WHERE
                    (scraped_at IS NOT NULL AND scraped_at != '') OR
                    (created_at IS NOT NULL AND created_at != '')
            """)
            rows = [row[0] for row in cursor.fetchall()]

        # Convert string dates to datetime objects (assuming ISO format without timezone for simplicity)
        dates = []
        for date_str in rows:
            try:
                # If the string has timezone info, we'll strip it for simplicity.
                if 'T' in date_str:
                    date_str = date_str.split('T')[0]
                # Format: YYYY-MM-DD
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                dates.append(dt)
            except Exception:
                # If parsing fails, skip this record.
                continue

        # Filter by date range
        dates = [d for d in dates if start_date <= d <= end_date]

        # Group by day
        daily_counts = {}
        for d in dates:
            day_key = d.strftime('%Y-%m-%d')
            daily_counts[day_key] = daily_counts.get(day_key, 0) + 1

        # Create daily time series
        daily_series = []
        current = start_date
        while current <= end_date:
            key = current.strftime('%Y-%m-%d')
            count = daily_counts.get(key, 0)
            daily_series.append(TimeSeriesPoint(timestamp=key, count=count))
            current += timedelta(days=1)

        # Group by week (starting from Monday)
        weekly_counts = {}
        for d in dates:
            # Week starting on Monday
            week_start = d - timedelta(days=d.weekday())
            week_key = week_start.strftime('%Y-%m-%d')
            weekly_counts[week_key] = weekly_counts.get(week_key, 0) + 1

        weekly_series = []
        current_week = start_date - timedelta(days=start_date.weekday())  # start at Monday of the week
        end_week = end_date - timedelta(days=end_date.weekday())
        while current_week <= end_week:
            key = current_week.strftime('%Y-%m-%d')
            count = weekly_counts.get(key, 0)
            weekly_series.append(TimeSeriesPoint(timestamp=key, count=count))
            current_week += timedelta(weeks=1)

        # Group by month
        monthly_counts = {}
        for d in dates:
            month_key = d.strftime('%Y-%m')
            monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1

        monthly_series = []
        current_month = datetime(start_date.year, start_date.month, 1)
        end_month = datetime(end_date.year, end_date.month, 1)
        while current_month <= end_month:
            key = current_month.strftime('%Y-%m')
            count = monthly_counts.get(key, 0)
            monthly_series.append(TimeSeriesPoint(timestamp=key, count=count))
            # Increment month
            if current_month.month == 12:
                current_month = datetime(current_month.year + 1, 1, 1)
            else:
                current_month = datetime(current_month.year, current_month.month + 1, 1)

        # Compute growth rate (from first to last period in the time series? We'll use monthly for growth)
        if len(monthly_series) >= 2:
            first_month = monthly_series[0].count
            last_month = monthly_series[-1].count
            if first_month > 0:
                growth_rate = ((last_month - first_month) / first_month) * 100
            else:
                growth_rate = 0.0 if last_month == 0 else float('inf')
        else:
            growth_rate = 0.0

        # For simplicity, we'll compute rolling and moving averages on the daily counts.
        # We'll use a window of 7 days for rolling average and 30 days for moving average?
        # But note: the requirement says "rolling averages" and "moving averages", we'll do:
        #   rolling_average: 7-day rolling average of daily counts
        #   moving_average: 30-day moving average of daily counts
        daily_counts_list = [point.count for point in daily_series]
        def moving_average(data, window_size):
            if len(data) < window_size:
                return []
            return [sum(data[i:i+window_size])/window_size for i in range(len(data)-window_size+1)]

        raw_rolling = moving_average(daily_counts_list, 7)
        raw_moving = moving_average(daily_counts_list, 30)
        rolling_average = [round(x, 2) for x in raw_rolling]
        moving_average_30 = [round(x, 2) for x in raw_moving]

        return TrendData(
            daily=daily_series,
            weekly=weekly_series,
            monthly=monthly_series,
            growth_rate=round(growth_rate, 2),
            rolling_average=rolling_average,
            moving_average=moving_average_30,
        )

    def get_business_insights(self) -> BusinessInsights:
        """Generate business insights from the data."""
        # We'll implement a few insights based on the data we have.
        with db.get_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Top performing industries: by average score and count
            cursor.execute("""
                SELECT
                    industry,
                    COUNT(*) as count,
                    AVG(quality_score) as avg_score
                FROM leads
                WHERE industry IS NOT NULL AND industry != '' AND quality_score IS NOT NULL
                GROUP BY industry
                ORDER BY avg_score DESC, count DESC
                LIMIT 5
            """)
            top_industries = [
                {
                    "industry": row[0],
                    "lead_count": row[1],
                    "average_score": round(row[2], 2)
                }
                for row in cursor.fetchall()
            ]

            # Best countries: by average score and count
            cursor.execute("""
                SELECT
                    country,
                    COUNT(*) as count,
                    AVG(quality_score) as avg_score
                FROM leads
                WHERE country IS NOT NULL AND country != '' AND quality_score IS NOT NULL
                GROUP BY country
                ORDER BY avg_score DESC, count DESC
                LIMIT 5
            """)
            best_countries = [
                {
                    "country": row[0],
                    "lead_count": row[1],
                    "average_score": round(row[2], 2)
                }
                for row in cursor.fetchall()
            ]

            # Most valuable sources: by average score and count (source domain)
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
                    COUNT(*) as count,
                    AVG(quality_score) as avg_score
                FROM leads
                WHERE source_url IS NOT NULL AND source_url != '' AND quality_score IS NOT NULL
                GROUP BY source_domain
                ORDER BY avg_score DESC, count DESC
                LIMIT 5
            """)
            valuable_sources = [
                {
                    "source": row[0],
                    "lead_count": row[1],
                    "average_score": round(row[2], 2)
                }
                for row in cursor.fetchall()
            ]

            # Highest quality segments: we can look at the combination of industry and country?
            # For simplicity, we'll do industry and country together? But let's do just industry for now.
            # We already have top industries by average score.

            # Most contacted leads: we don't have a contact count in the leads table.
            # We have an outreach queue, but that's a separate table. We'll skip for now or set to empty.

            # Highest conversion states: we don't have a conversion state. We have lead_status, but we can consider CONVERTED as conversion.
            # We'll look at the lead_status and see which states (country) have the highest conversion rate.
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
                LIMIT 5
            """)
            conversion_states = [
                {
                    "country": row[0],
                    "total_leads": row[1],
                    "converted_leads": row[2],
                    "conversion_rate": round((row[2] / row[1]) * 100, 2) if row[1] > 0 else 0.0
                }
                for row in cursor.fetchall()
            ]

        return BusinessInsights(
            top_performing_industries=top_industries,
            best_countries=best_countries,
            most_valuable_sources=valuable_sources,
            highest_quality_segments=[],  # We'll leave empty for now, or we can use the same as top industries?
            most_contacted_leads=[],     # We don't have contact count data
            highest_conversion_states=conversion_states,
        )

    def compute_all_analytics(self) -> AnalyticsResult:
        """Compute all analytics and return as a single result."""
        return AnalyticsResult(
            overview=self.get_overview_stats(),
            trends=self.get_time_series(),
            quality=self.get_quality_analytics(),
            providers=self.get_provider_analytics(),
            lifecycle=self.get_lifecycle_distribution(),
            insights=self.get_business_insights(),
        )