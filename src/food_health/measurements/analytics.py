"""Derived body measurements from observed numeric inputs.

Ported *formulas*, not historical notebook assumptions. Results are derived,
never measured. Device-provided body-fat or muscle percentages may be noisy
and should not be interpreted as clinical body-composition assessments.
"""
from __future__ import annotations

import math
from typing import Mapping


def derived_metrics(
    observed: Mapping[str, float], *, height_m: float | None = None
) -> dict[str, float]:
    """Return computable metrics using only supplied observations.

    Units assumed: Weight kg; circumferences cm; Body Fat / Muscle percentages.
    Returns no result for missing, zero-denominator or invalid inputs.
    `WHR` uses the historical notebook convention Hips/Waist, not the
    more usual clinical waist-to-hip ratio (Waist/Hips).
    """
    def valid(key: str) -> float | None:
        v = observed.get(key)
        if v is None:
            return None
        try:
            x = float(v)
        except (ValueError, TypeError):
            return None
        return x if math.isfinite(x) and x >= 0 else None

    values: dict[str, float] = {}
    weight = valid("Weight")
    bodyfat = valid("Body Fat")
    muscle = valid("Muscle")
    if weight is not None and weight > 0:
        if bodyfat is not None and bodyfat <= 100:
            values["fat_mass_kg"] = weight * bodyfat / 100
            values["lean_body_mass_kg"] = weight * (1 - bodyfat / 100)
        if muscle is not None and muscle <= 100:
            values["device_muscle_mass_kg"] = weight * muscle / 100
        if height_m is not None:
            try:
                h = float(height_m)
            except (ValueError, TypeError) as exc:
                raise ValueError("height_m must be a positive finite number") from exc
            if not math.isfinite(h) or h <= 0:
                raise ValueError("height_m must be a positive finite number")
            values["bmi_kg_m2"] = weight / h**2

    waist = valid("Waist")
    if waist is not None and waist > 0:
        for name, field in (
            ("SWR", "Shoulder"), ("CWR", "Chest"), ("WHR_legacy_hips_over_waist", "Hips")
        ):
            numerator = valid(field)
            if numerator is not None:
                values[name] = numerator / waist
    return values
