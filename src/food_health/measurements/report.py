"""Reproducible, local-only measurement reports derived from SQLite snapshots."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from .analytics import derived_metrics
from .trends import monthly_observed_summary, rolling_observed_mean

FIELDS = ("Weight", "Waist", "Body Fat", "Muscle")


def build_measurement_report(
    records: list[dict], *, height_m: float | None = None
) -> dict:
    """Return a private artifact with separate measured and derived sections.

    Never infer unobserved daily values; trends summarize observed days only.
    """
    if not records:
        raise ValueError("cannot report on an empty private snapshot")
    derived = [
        {
            "date": r["date"], "source_row": r["source_row"],
            "derived": derived_metrics(r["observed"], height_m=height_m),
        }
        for r in records
    ]
    return {
        "schema_version": 1,
        "authority": "Personal Measurements / MEDIDAS",
        "methodology": "observed-only; duplicated dates averaged in trends; no interpolation",
        "observed_rows": len(records),
        "observed_monthly": {
            field: monthly_observed_summary(records, field) for field in FIELDS
        },
        "observed_rolling_30d": {
            field: rolling_observed_mean(records, field, window_days=30, min_days=3)
            for field in FIELDS
        },
        "derived_records": derived,
    }


def save_private_report(path: str | Path, report: dict) -> Path:
    """Write a JSON artifact atomically, in a private directory."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(target.parent, 0o700)
    # mkstemp is 0600; keep the private artifact restrictive after replacement.
    fd, name = tempfile.mkstemp(prefix=".measurements-", suffix=".json", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        os.chmod(name, 0o600)
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return target
