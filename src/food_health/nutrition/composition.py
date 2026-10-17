"""Nutrient composition from source-table per-100g values.

The reference catalog is a dataset, not a personal food diary or medical
recommendation. All quantities are **grams** of edible ingredient, with catalog
nutrition per **100 grams**. No default energy or protein targets are imposed.

Only the subset of fields with explicit units listed below is consumed.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable, Mapping

NUTRIENTS_PER_100G = (
    "Calories", "Carbohydrate (g)", "Fat (g)", "Protein (g)",
    "Fiber (g)", "Cholesterol (mg)", "Saturated Fats (g)",
)


def _number(value: object, *, context: str) -> float:
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{context}: expected number") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{context}: expected finite, nonnegative quantity")
    return number


def load_catalog(
    csv_path: str | Path, *, fields: tuple[str, ...] = NUTRIENTS_PER_100G
) -> dict[str, dict]:
    """Parse MyFoodData-style CSV with unique ID, name and per-100g nutrients.

    Caller controls input location. Never writes or uploads source data.
    """
    if not fields or len(set(fields)) != len(fields):
        raise ValueError("nonempty unique nutrient fields required")
    result: dict[str, dict] = {}
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {"ID", "name", *fields}
        if not reader.fieldnames or not expected.issubset(reader.fieldnames):
            raise ValueError("missing catalog headers: " + ", ".join(sorted(expected - set(reader.fieldnames or []))))
        for row_number, row in enumerate(reader, start=2):
            food_id = (row.get("ID") or "").strip()
            if not food_id or food_id in result:
                raise ValueError(f"catalog row {row_number}: missing or duplicate food ID")
            nutrients = {
                field: _number(row.get(field), context=f"catalog row {row_number}, {field}")
                for field in fields
            }
            result[food_id] = {
                "name": (row.get("name") or "").strip(),
                "per_100g": nutrients,
            }
    return result


def load_legacy_plan(csv_path: str | Path) -> list[dict]:
    """Read the archived 24template_diet schema (ID, cant in grams).

    An inactive zero-gram row without an ID may be safely ignored. Otherwise
    an unknown or missing ID causes an explicit validation error at composition.
    """
    lines: list[dict] = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"ID", "cant"}.issubset(reader.fieldnames):
            raise ValueError("expected ID and cant columns in legacy plan")
        for number, row in enumerate(reader, start=2):
            amount = _number(row.get("cant") or 0, context=f"plan row {number} cant")
            food_id = (row.get("ID") or "").strip()
            if amount == 0:
                continue
            if not food_id:
                raise ValueError(f"plan row {number}: quantity without food ID")
            lines.append({"food_id": food_id, "grams": amount})
    return lines


def composition(
    catalog: Mapping[str, dict],
    plan: Iterable[dict],
    *,
    period_days: float = 3,
    fields: tuple[str, ...] = NUTRIENTS_PER_100G,
) -> dict:
    """Calculate nutrient totals and per-day averages for an N-day plan.

    Missing ingredients/nutrients fail closed. Units are preserved in field names;
    source catalog values are not construed as measured intake.
    """
    duration = _number(period_days, context="period_days")
    if duration <= 0:
        raise ValueError("period_days must be positive")
    totals = {field: 0.0 for field in fields}
    quantities: dict[str, float] = {}
    for i, item in enumerate(plan):
        food_id = str(item.get("food_id", "")).strip()
        grams = _number(item.get("grams"), context=f"plan row {i} grams")
        if grams == 0:
            continue
        if food_id not in catalog:
            raise ValueError(f"plan row {i}: unmapped food ID")
        ingredient = catalog[food_id]["per_100g"]
        for field in fields:
            if field not in ingredient:
                raise ValueError(f"plan row {i}: missing nutrient field {field}")
            totals[field] += grams * _number(ingredient[field], context=field) / 100
        quantities[food_id] = quantities.get(food_id, 0.0) + grams
    return {
        "period_days": duration,
        "total_grams": sum(quantities.values()),
        "totals": totals,
        "per_day": {name: value / duration for name, value in totals.items()},
        "grams_by_id": quantities,
    }


def scale_quantities(
    grams_by_id: Mapping[str, float], *, source_days: float, target_days: float
) -> dict[str, dict[str, float]]:
    """Scale planning quantities by duration; output grams and kilograms."""
    source = _number(source_days, context="source_days")
    target = _number(target_days, context="target_days")
    if source <= 0 or target <= 0:
        raise ValueError("durations must be positive")
    factor = target / source
    result = {}
    for key, grams in grams_by_id.items():
        mass = _number(grams, context="grams")
        value = mass * factor
        result[str(key)] = {"grams": value, "kg": value / 1000}
    return result
