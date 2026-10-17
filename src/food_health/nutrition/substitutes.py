"""Rank food catalog neighbors by nutrient similarity per 100 grams.

A catalog neighbor is **not** a dietary or culinary recommendation. This
does not account for allergies, preparation, cost, availability, portions,
medical constraints, protein quality, or personal tolerances.
"""
from __future__ import annotations

import math
from statistics import pstdev
from typing import Mapping

DEFAULT_FEATURES = (
    "Calories", "Carbohydrate (g)", "Fat (g)", "Protein (g)"
)


def nearest_foods(
    catalog: Mapping[str, dict],
    source_id: str,
    *,
    limit: int = 10,
    features: tuple[str, ...] = DEFAULT_FEATURES,
    feature_weights: Mapping[str, float] | None = None,
    max_distance: float | None = None,
    same_group: bool = False,
    exclude_ids: frozenset[str] = frozenset(),
) -> list[dict]:
    """Return stable-ID nearest neighbors with standardized Euclidean distance.

    Each feature is normalized by its population standard deviation among
    eligible foods with all selected nutrient values present. Zero-variance
    features have scale 1. Invalid/missing candidate nutrients exclude the
    candidate; invalid source nutrients reject the request.
    """
    source_id = str(source_id)
    if source_id not in catalog:
        raise KeyError("Source food ID not in catalog")
    if type(limit) is not int or limit < 1:
        raise ValueError("limit must be a positive integer")
    if not features or len(set(features)) != len(features):
        raise ValueError("Unique nonempty feature names are required")
    if not all(isinstance(x, str) and x for x in features):
        raise ValueError("Invalid feature labels")
    if feature_weights is not None and set(feature_weights) - set(features):
        raise ValueError("Weights provided for unselected nutrient features")
    weights = {}
    for key in features:
        value = float(feature_weights.get(key, 1.0) if feature_weights else 1.0)
        if not math.isfinite(value) or value < 0:
            raise ValueError("Feature weights must be finite and nonnegative")
        weights[key] = value
    if not any(weights.values()):
        raise ValueError("At least one feature weight must be positive")
    if max_distance is not None:
        max_distance = float(max_distance)
        if not math.isfinite(max_distance) or max_distance < 0:
            raise ValueError("max_distance must be finite and nonnegative")

    src = catalog[source_id]
    src_group = src.get("group")
    if same_group and not src_group:
        raise ValueError("Source group missing: cannot enforce same_group")

    def vector(food: dict) -> tuple[float, ...] | None:
        nutrients = food.get("per_100g") or {}
        result = []
        for key in features:
            raw = nutrients.get(key)
            if raw is None:
                return None
            try:
                value = float(raw)
            except (ValueError, TypeError):
                return None
            if not math.isfinite(value) or value < 0:
                return None
            result.append(value)
        return tuple(result)

    center = vector(src)
    if center is None:
        raise ValueError("Source missing one or more selected nutrients")
    eligible = []
    excluded = set(exclude_ids) | {source_id}
    for food_id, data in catalog.items():
        if food_id in excluded:
            continue
        if same_group and data.get("group") != src_group:
            continue
        values = vector(data)
        if values is not None:
            eligible.append((food_id, data, values))
    if not eligible:
        return []
    # Include source itself when calculating scales: candidates may be
    # constant while source differs. Distances remain interpretable.
    scales = []
    for index in range(len(features)):
        dispersion = pstdev([center[index], *(row[2][index] for row in eligible)])
        scales.append(dispersion if dispersion > 0 else 1.0)
    results = []
    for food_id, data, vector_ in eligible:
        distance = math.sqrt(sum(
            weights[key] * ((observed - expected) / scale) ** 2
            for key, observed, expected, scale
            in zip(features, vector_, center, scales)
        ))
        if max_distance is not None and distance > max_distance:
            continue
        results.append({
            "food_id": food_id,
            "name": data.get("name", ""),
            "distance": distance,
        })
    return sorted(results, key=lambda row: (row["distance"], row["food_id"]))[:limit]
