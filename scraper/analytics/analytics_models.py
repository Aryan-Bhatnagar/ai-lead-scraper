"""
Analytics models for the AI Lead Scraper.
Defines data structures for analytics results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class OverviewStats:
    """Overview statistics of the lead database."""
    total_leads: int = 0
    total_companies: int = 0
    average_score: float = 0.0
    median_score: float = 0.0
    highest_score: int = 0
    lowest_score: int = 0
    lead_sources: Dict[str, int] = field(default_factory=dict)
    countries: Dict[str, int] = field(default_factory=dict)
    cities: Dict[str, int] = field(default_factory=dict)
    industries: Dict[str, int] = field(default_factory=dict)
    lifecycle_distribution: Dict[str, int] = field(default_factory=dict)
    quality_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class TimeSeriesPoint:
    """A point in a time series."""
    timestamp: str  # ISO format date string
    count: int = 0


@dataclass
class TrendData:
    """Trend data over time."""
    daily: List[TimeSeriesPoint] = field(default_factory=list)
    weekly: List[TimeSeriesPoint] = field(default_factory=list)
    monthly: List[TimeSeriesPoint] = field(default_factory=list)
    growth_rate: float = 0.0  # percentage growth over the period
    rolling_average: List[float] = field(default_factory=list)
    moving_average: List[float] = field(default_factory=list)


@dataclass
class QualityAnalytics:
    """Quality distribution based on score thresholds."""
    excellent: int = 0   # score >= 90
    good: int = 0        # 70 <= score < 90
    average: int = 0     # 50 <= score < 70
    poor: int = 0        # score < 50
    unknown: int = 0     # score is None or not available


@dataclass
class ProviderAnalytics:
    """Analytics per discovery provider."""
    provider_name: str = ""
    total_leads: int = 0
    average_leads_per_provider: float = 0.0
    success_rate: float = 0.0  # percentage of leads with data_quality HIGH or MEDIUM
    failure_rate: float = 0.0  # percentage of leads with data_value LOW or failed
    duplicate_percentage: float = 0.0
    unique_percentage: float = 0.0


@dataclass
class BusinessInsights:
    """Business insights derived from the data."""
    top_performing_industries: List[Dict[str, Any]] = field(default_factory=list)
    best_countries: List[Dict[str, Any]] = field(default_factory=list)
    most_valuable_sources: List[Dict[str, Any]] = field(default_factory=list)
    highest_quality_segments: List[Dict[str, Any]] = field(default_factory=list)
    most_contacted_leads: List[Dict[str, Any]] = field(default_factory=list)
    highest_conversion_states: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AnalyticsResult:
    """Container for all analytics data."""
    overview: OverviewStats = field(default_factory=OverviewStats)
    trends: TrendData = field(default_factory=TrendData)
    quality: QualityAnalytics = field(default_factory=QualityAnalytics)
    providers: List[ProviderAnalytics] = field(default_factory=list)
    lifecycle: Dict[str, int] = field(default_factory=dict)
    insights: BusinessInsights = field(default_factory=BusinessInsights)