# Ingredient similarity from legacy notebook

Recovers the core idea of `legacy_23/substitutes.ipynb`:
nearest-neighbor search in calorie/carbohydrate/fat/protein space, expressed
per 100 g of reference food and standardized to comparable scales.

```python
from food_health.nutrition.substitutes import nearest_foods
from food_health.nutrition.private_snapshot import read_private_snapshot

data = read_private_snapshot(".local/food-stock.json")  # PRIVATE
source_food_id = "<ID from an existing plan, not a food name>"
neighbors = nearest_foods(
    data["catalog"], source_food_id, limit=10,
    same_group=False, max_distance=None
)
# Keep specific search results local. IDs, names and distances are returned.
```

Unlike the notebook, this version does not use globally hard-coded standard
deviations, and excludes the exact source food **by stable ID**, rather than
dropping a ranking position that might not represent the source. Scales are
population standard deviations computed from eligible candidates, with
deterministic ties broken by food ID. A source with missing features is rejected;
candidates with missing or invalid features are filtered.

This is a **nutrient-space similarity index**, not an automatic food swap or
adequate meal formulation. Food allergy, intolerances, texture, quality,
preparation, price, local availability, packaging and diet/health constraints
are NOT checked. Do not automatically substitute ingredients on behalf of
the user without separate rules and review.

Notebook retirement status: PARTIAL. Visualizations, subjective features
and bespoke source comparisons remain to be explicitly triaged.

## Canonical catalog validation

In the current 29 active Food plan lines, 28 source ingredients have a
nonempty `Food Group` in the canonical catalog. The remaining one can still
be ranked without a group restriction; using `same_group=True` against it
must fail rather than silently widen the search. For a plan item with a
specified group, the filter works against the current read-only snapshot.
