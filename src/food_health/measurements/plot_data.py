"""Data frames for descriptive analysis of canonical measured observations.

No estimated, synthetic or interpolated values are created. Multi-row dates
are averaged *within a day* for each measured field, after retaining raw
per-row provenance in the SQLite source. Derived fields carry their labels.
"""
from __future__ import annotations

from datetime import date
import math
from typing import Iterable

from .analytics import derived_metrics


def observed_frames(records: Iterable[dict], *, height_m: float | None = None):
    """Return (raw per-row frame, per-date measured mean) for charting.

    Raw rows may include duplicate calendar dates; their source rows are
    independent. Daily averaging is only a plotting/analysis projection.
    """
    import pandas as pd

    rows = []
    for item in records:
        when = date.fromisoformat(item["date"])
        observed = item.get("observed") or {}
        if not observed:
            continue
        # All original measurement fields remain untouched.
        vals = {
            k: float(v) for k, v in observed.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(float(v))
        }
        derived = derived_metrics(vals, height_m=height_m)
        rows.append({"date": pd.Timestamp(when), "source_row": item["source_row"], **vals, **derived})
    if not rows:
        raise ValueError("No observed measurements to chart")
    raw = pd.DataFrame(rows).sort_values(["date", "source_row"]).reset_index(drop=True)
    field_cols = [k for k in raw.columns if k not in {"date", "source_row"}]
    daily = raw.groupby("date", sort=True)[field_cols].mean(numeric_only=True)
    return raw, daily


def observation_counts(raw):
    """Number of actual measurement records per field; never count imputed."""
    return {
        col: int(raw[col].notna().sum())
        for col in raw.columns if col not in {"date", "source_row"}
    }


def weekly_stats(daily, field: str):
    """Weekly mean/count and absolute/relative changes, without interpolation."""
    import pandas as pd
    if field not in daily.columns:
        raise KeyError(field)
    weekly = daily[field].resample("W-SUN").agg(["mean", "count"]).dropna(subset=["mean"])
    weekly["change"] = weekly["mean"].diff()
    weekly["pct_change"] = 100 * weekly["mean"].pct_change(fill_method=None)
    return weekly


def ten_day_stats(daily, field: str):
    """Sparse 10-day bins; only mean of actually measured dates."""
    if field not in daily.columns:
        raise KeyError(field)
    return daily[field].resample("10D", origin="start").agg(["mean", "count"]).dropna(subset=["mean"])


def two_month_changes(daily, field: str = "Weight", *, bin_days: int = 30):
    """Change between two NONOVERLAPPING observed bins (about 60 days apart).

    Historic notebook interpolated daily weights and compared 30-day bin
    averages two bins apart. Here each bin must contain actual observations.
    """
    if field not in daily.columns or bin_days < 1:
        raise ValueError("Unknown field or invalid window")
    binned = daily[field].resample(f"{bin_days}D", origin="start").agg(["mean", "count"])
    binned["delta_2bins"] = binned["mean"].diff(2)
    binned.loc[
        (binned["count"] < 2) | (binned["count"].shift(2) < 2), "delta_2bins"
    ] = float("nan")
    return binned.dropna(subset=["delta_2bins"])


def paired_frame(daily, x: str, y: str, *, min_points: int = 3):
    """Pair same-day complete observations before any relationship analysis."""
    if x not in daily.columns or y not in daily.columns:
        return None
    paired = daily[[x, y]].dropna()
    if len(paired) < min_points:
        return None
    return paired


def descriptive_fit(pairs, *, x: str, y: str, degree: int = 1, min_points: int = 8):
    """In-sample polynomial description, never extrapolated or a prediction.

    Return None if undersampled or numerically degenerate. The fitted curve
    is strictly confined to the observed x range.
    """
    import numpy as np

    if degree not in (1, 2):
        raise ValueError("Only linear/quadratic descriptive fits are supported")
    if pairs is None or len(pairs) < max(min_points, degree + 3):
        return None
    xx = np.asarray(pairs[x], dtype=float)
    yy = np.asarray(pairs[y], dtype=float)
    if len(np.unique(xx)) < degree + 3:
        return None
    try:
        with __import__("warnings").catch_warnings():
            __import__("warnings").simplefilter("error", np.exceptions.RankWarning)
            coeff = np.polyfit(xx, yy, degree)
        pred = np.polyval(coeff, xx)
        ss = float(((yy - pred)**2).sum())
        tot = float(((yy - yy.mean())**2).sum())
        grid = np.linspace(float(xx.min()), float(xx.max()), 80)
        return {
            "x": grid, "y": np.polyval(coeff, grid),
            "r2": None if tot <= 0 else 1 - ss / tot,
            "degree": degree, "count": len(xx),
        }
    except (ValueError, FloatingPointError, np.linalg.LinAlgError, Warning):
        return None
