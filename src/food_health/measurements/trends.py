"""Observed-only calendar statistics; no hidden interpolation."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import math
from statistics import mean


def _daily_observations(records: list[dict], field: str) -> list[tuple[date, float]]:
    """Collapse duplicate dates to a single daily mean, but never invent dates."""
    dates: dict[date, list[float]] = defaultdict(list)
    for row in records:
        observed = row.get("observed") or {}
        v = observed.get(field)
        if v is None:
            continue
        try:
            f = float(v)
        except (ValueError, TypeError):
            continue
        if not math.isfinite(f):
            continue
        try:
            when = date.fromisoformat(row["date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid date in observed row") from exc
        dates[when].append(f)
    return sorted((day, mean(values)) for day, values in dates.items())


def rolling_observed_mean(
    records: list[dict], field: str, *, window_days: int = 30, min_days: int = 3
) -> list[dict]:
    """Trailing calendar window over actually observed days; no gap filling."""
    if window_days < 1 or min_days < 1 or min_days > window_days:
        raise ValueError("invalid window or min_days")
    points = _daily_observations(records, field)
    out: list[dict] = []
    left = 0
    for right, (day, _) in enumerate(points):
        start = day - timedelta(days=window_days - 1)
        while points[left][0] < start:
            left += 1
        window = [value for _, value in points[left:right+1]]
        if len(window) >= min_days:
            out.append({
                "date": day.isoformat(), "observed_days": len(window),
                "mean": mean(window),
            })
    return out


def monthly_observed_summary(
    records: list[dict], field: str, *, min_days: int = 1
) -> list[dict]:
    """Calendar-month statistics, weighted by observed day (not raw row count)."""
    if min_days < 1:
        raise ValueError("min_days must be positive")
    months: dict[str, list[float]] = defaultdict(list)
    for day, value in _daily_observations(records, field):
        months[day.strftime("%Y-%m")].append(value)
    return [
        {
            "month": month, "observed_days": len(values),
            "mean": mean(values), "min": min(values), "max": max(values),
        }
        for month, values in sorted(months.items()) if len(values) >= min_days
    ]
