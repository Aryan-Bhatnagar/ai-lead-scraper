"""
Statistical functions for analytics.
"""

from __future__ import annotations

from typing import List, Optional, Union
import statistics as stats


def mean(data: List[float]) -> float:
    """Calculate the arithmetic mean of a list of numbers."""
    if not data:
        return 0.0
    return sum(data) / len(data)


def median(data: List[float]) -> float:
    """Calculate the median of a list of numbers."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    n = len(sorted_data)
    if n % 2 == 0:
        return (sorted_data[n//2 - 1] + sorted_data[n//2]) / 2
    else:
        return sorted_data[n//2]


def mode(data: List[float]) -> List[float]:
    """Calculate the mode(s) of a list of numbers.
    Returns a list of the most common value(s).
    """
    if not data:
        return []
    frequency = {}
    for item in data:
        frequency[item] = frequency.get(item, 0) + 1
    max_count = max(frequency.values())
    return [k for k, v in frequency.items() if v == max_count]


def standard_deviation(data: List[float]) -> float:
    """Calculate the standard deviation of a list of numbers."""
    if len(data) < 2:
        return 0.0
    m = mean(data)
    variance = sum((x - m) ** 2 for x in data) / (len(data) - 1)
    return variance ** 0.5


def percentile(data: List[float], p: float) -> float:
    """Calculate the p-th percentile of a list of numbers.
    p should be between 0 and 100.
    """
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = k - f
    if f + 1 < len(sorted_data):
        return sorted_data[f] + c * (sorted_data[f + 1] - sorted_data[f])
    else:
        return sorted_data[f]