"""Bounded, non-mutating quantity optimization for a fixed ingredient set.

This is a mathematical scenario planner, NOT a recommended diet. Targets must
be supplied explicitly by the caller, who is responsible for their suitability.
No target is inferred from the user's health, training or archived notebooks.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Iterable

from .composition import composition, _number


@dataclass(frozen=True)
class PlanOptimization:
    solver_success: bool
    targets_met: bool
    objective_before: float
    objective_after: float
    max_relative_error: float
    grams_by_id: dict[str, float]
    target_per_day: dict[str, float]
    calculated_per_day: dict[str, float]
    solver_message: str


def optimize_quantities(
    catalog: Mapping[str, dict],
    plan: Iterable[dict],
    *,
    targets_per_day: Mapping[str, float],
    variable_ids: Iterable[str],
    period_days: float = 3,
    bounds_grams: Mapping[str, tuple[float, float]] | None = None,
    relative_tolerance: float = 0.02,
) -> PlanOptimization:
    """Find grams that minimize squared relative deviations from targets.

    All nonvariable ingredients are frozen. For each variable, the default
    permitted range is 0 to twice its current quantity. `bounds_grams` can
    impose explicit lower/upper gram limits. The solver's success flag is
    separate from target satisfaction.
    """
    try:
        from scipy.optimize import minimize
    except ImportError as exc:
        raise RuntimeError("Install optional dependency: food-health[nutrition]") from exc
    if not targets_per_day:
        raise ValueError("At least one explicit per-day target is required")
    targets = {
        str(k): _number(v, context=f"target {k}")
        for k, v in targets_per_day.items()
    }
    if not all(v > 0 for v in targets.values()):
        raise ValueError("All target denominators must be positive")
    tolerance = _number(relative_tolerance, context="relative_tolerance")
    if tolerance > 1:
        raise ValueError("relative_tolerance must be in [0,1]")

    fields = tuple(targets)
    baseline = composition(catalog, plan, period_days=period_days, fields=fields)
    grams = baseline["grams_by_id"]
    names = [str(i) for i in variable_ids]
    if not names or len(names) != len(set(names)):
        raise ValueError("variable_ids must be nonempty and unique")
    if set(names) - grams.keys():
        raise ValueError("variable_ids must reference active ingredients")
    if bounds_grams is not None and set(bounds_grams) - set(names):
        raise ValueError("bounds provided for frozen/unlisted ingredient")

    x0 = [grams[food_id] for food_id in names]
    bounds = []
    for food_id, current in zip(names, x0):
        lower, upper = (
            bounds_grams[food_id]
            if bounds_grams is not None and food_id in bounds_grams
            else (0, current * 2)
        )
        lower = _number(lower, context=f"min grams for {food_id}")
        upper = _number(upper, context=f"max grams for {food_id}")
        if lower > upper:
            raise ValueError("minimum grams exceeds maximum")
        bounds.append((lower, upper))

    def calc(candidates) -> dict:
        quantities = dict(grams)
        for name, value in zip(names, candidates):
            quantities[name] = float(value)
        trial = [{"food_id": i, "grams": v} for i, v in quantities.items()]
        return composition(catalog, trial, period_days=period_days, fields=fields)

    def loss(candidates) -> float:
        per_day = calc(candidates)["per_day"]
        return sum(((per_day[field] - target) / target)**2 for field, target in targets.items())

    old_loss = loss(x0)
    # SLSQP respects continuous gram bounds. No random search or hidden
    # default calorie/protein constraint inherited from legacy notebooks.
    solution = minimize(
        loss, x0=x0, method="SLSQP", bounds=bounds,
        options={"maxiter": 500, "ftol": 1e-12},
    )
    if not all(math.isfinite(float(v)) for v in solution.x):
        raise RuntimeError("Optimizer returned nonfinite quantities")
    candidate = [
        min(upper, max(lower, float(v)))
        for v, (lower, upper) in zip(solution.x, bounds)
    ]
    revised = calc(candidate)
    errors = {
        field: abs(revised["per_day"][field] / target - 1)
        for field, target in targets.items()
    }
    final_qty = dict(grams)
    final_qty.update(zip(names, candidate))
    return PlanOptimization(
        solver_success=bool(solution.success),
        targets_met=bool(solution.success and max(errors.values()) <= tolerance),
        objective_before=old_loss,
        objective_after=loss(candidate),
        max_relative_error=max(errors.values()),
        grams_by_id=final_qty,
        target_per_day=targets,
        calculated_per_day=revised["per_day"],
        solver_message=str(solution.message),
    )
