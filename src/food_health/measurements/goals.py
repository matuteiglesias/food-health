"""Opt-in reference comparison of historical goals.

Historical goals are NOT inferred prescriptions and are never activated by
default. The archived file is private and read only.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path


def load_goal_values(path: str | Path) -> dict:
    """Parse one legacy goal_measurements CSV row; ignore non-measurement columns."""
    from .dashboard import METRICS

    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Historical goal file missing headers")
        rows = list(reader)
    if len(rows) != 1:
        raise ValueError("Require exactly one explicit historical goals row")
    row = rows[0]
    goals = {}
    for name in METRICS:
        raw = row.get(name)
        if raw in (None, ""):
            continue
        try:
            value = float(raw)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid historical target: {name}") from exc
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"Invalid historical target: {name}")
        goals[name] = value
    if not goals:
        raise ValueError("No numeric measurement goals found")
    return {"source_label":row.get("") or "historical, date not specified", "goals":goals}


def compare_goals(daily, goals: dict, *, recent_observations: int = 10) -> list[dict]:
    """Average last N actually measured dates per metric and compare to goal."""
    if recent_observations < 1:
        raise ValueError("recent_observations must be positive")
    out = []
    for name, target in goals.items():
        if name not in daily.columns:
            continue
        recent = daily[name].dropna().tail(recent_observations)
        if len(recent) < 2:
            continue
        observed = float(recent.mean())
        out.append({
            "metric":name, "recent_mean":observed, "goal":float(target),
            "gap":float(target)-observed,
            "forty_pct_step":observed+0.4*(float(target)-observed),
            "observed_days":len(recent),
        })
    return out
