"""Private period comparisons and exploratory correlations for measurement reports.

All statistics use actually observed daily means, never estimated dates.
They are descriptive, not causal, clinical or statistical significance claims.
"""
from __future__ import annotations

import math


def period_comparisons(daily, fields, *, window_days: int = 90, min_days: int = 3):
    """Compare the latest two consecutive calendar windows for each metric.

    Anchor to the last actual measurement date in the snapshot, not wall clock.
    """
    from datetime import timedelta
    if window_days < 1 or min_days < 1:
        raise ValueError("Invalid comparison window")
    anchor = daily.index.max()
    cur_start = anchor - timedelta(days=window_days - 1)
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=window_days - 1)
    rows = []
    for field in fields:
        if field not in daily.columns:
            continue
        current = daily.loc[(daily.index >= cur_start) & (daily.index <= anchor), field].dropna()
        prior = daily.loc[(daily.index >= prev_start) & (daily.index <= prev_end), field].dropna()
        if len(current) < min_days or len(prior) < min_days:
            continue
        now = float(current.mean())
        before = float(prior.mean())
        rows.append({
            "metric": field,
            "current_mean": now,
            "previous_mean": before,
            "change": now - before,
            "previous_observed_days": len(prior),
            "current_observed_days": len(current),
            "current_start":cur_start.date().isoformat(),
            "previous_start":prev_start.date().isoformat(),
        })
    return rows


def yearly_summary(daily, fields, *, min_days: int = 3):
    """Mean and observation count by year; no interpolation."""
    rows = []
    for name in fields:
        if name not in daily:
            continue
        for year, part in daily[name].dropna().groupby(daily[name].dropna().index.year):
            if len(part)<min_days:
                continue
            rows.append({
                "metric":name,"year":int(year),"observed_days":len(part),
                "mean":float(part.mean()),"first":float(part.iloc[0]),
                "last":float(part.iloc[-1]),
            })
    return rows


def pairwise_correlations(daily, fields, *, min_points: int = 8):
    """Pearson r and sample count for each same-date pair with sufficient spread."""
    names=[name for name in fields if name in daily.columns]
    results=[]
    for i, a in enumerate(names):
        for b in names[i+1:]:
            xy=daily[[a,b]].dropna()
            if len(xy)<min_points:
                continue
            if xy[a].nunique()<3 or xy[b].nunique()<3:
                continue
            r=float(xy[a].corr(xy[b]))
            if math.isfinite(r):
                results.append({"x":a,"y":b,"pearson_r":r,"paired_days":len(xy)})
    return results
