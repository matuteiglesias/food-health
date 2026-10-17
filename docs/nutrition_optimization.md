# Bounded nutrient quantity optimization

Migrates the reusable SciPy SLSQP optimization concepts from
`dieta.ipynb` / `nutrientes 24.ipynb`, without copying their hard-coded
calorie/protein goals, random search experiments, or notebook globals.

This is **mathematical scenario analysis**, not a prescription or medical
nutrition recommendation.

```python
from food_health.nutrition.optimize import optimize_quantities

result = optimize_quantities(
    catalog, plan,
    period_days=3,
    targets_per_day={"Calories": 2100, "Protein (g)": 100},  # EXAMPLE ONLY
    variable_ids=["food-id-a", "food-id-b"],
    bounds_grams={"food-id-a": (0, 600), "food-id-b": (100, 1200)},
)
if not result.targets_met:
    print("Configured targets infeasible or not reached under selected bounds")
```

Inputs must use stable food IDs, quantities in grams over `period_days`, and
catalog nutrients per 100 grams. Only the listed variables can change;
other ingredients remain fixed. The default allowed range per variable is
0–2 times its initial amount; **not** a dietary safety recommendation.
Missing nutrients for a selected ingredient reject the run. The function
returns solver convergence and target satisfaction separately, with relative
error and objective diagnostics; success from SciPy alone never implies an
adequate or appropriate eating plan.

No private catalog, actual personal goals or plan outputs are stored in GitHub.
A future product could provide UI and optional constraint types, but human
review is required before treating outputs as a food plan.

## Workstation compatibility gate

The local ThinkPad currently has Python 3.10, NumPy 1.26.4 and system
SciPy 1.8.0, which emits a compatibility warning requiring NumPy <1.25.
The 32-suite synthetic tests and the archived-plan identity smoke passed, but
**do not treat this as a supported runtime**. Before regular use, create an
ignored venv with mutually compatible NumPy, SciPy and pandas versions; test
in that venv, record versions, and only then merge/deploy this PR. Do not
modify global system packages or share personal target values in logs.
