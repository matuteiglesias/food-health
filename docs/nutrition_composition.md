# Nutrition foundation: per-100g ingredient composition

Legacy notebooks `nutrientes.ipynb`, `nutrientes 24.ipynb`,
`dieta.ipynb` and `compras.ipynb` all assume source nutrient composition
per 100 grams, multiply by a quantity in grams/100 and often divide a
multi-day recipe total by three. This is now a **pure reusable Python API**.

The catalog is a **reference**, not a personal consumption record. Its
calorie and nutrient values are estimates and must not be treated as
clinical prescriptions.

## Local-only example

```python
from pathlib import Path
from food_health.nutrition.composition import (
    load_catalog, load_legacy_plan, composition, scale_quantities
)

archive = Path.home() / "Documents/food/archive/legacy"
catalog = load_catalog(archive / "data/myfood.csv")
plan = load_legacy_plan(archive / "BD/24template_diet.csv")
result = composition(catalog, plan, period_days=3)
weekly = scale_quantities(result["grams_by_id"], source_days=3, target_days=7)
# Both 'result' and 'weekly' contain private dietary plans; keep locally.
```

The template has one inactive zero-gram row without an ID. That row is skipped,
but an **active** unmapped food is rejected rather than silently dropped.

## Validation / migration status

- Uses `ID` as ingredient identity; distinct names are not reliable keys.
- Preserves calorie, carbohydrate, fat, protein, fiber, cholesterol, saturated-fat
  units from the source catalog.
- Source `cant` is **total grams over N days**, not grams per day.
- Unknown catalog nutrients (`NULL`, `NaN`, blank) remain `None`, never zero; composition fails when a selected ingredient needs a missing nutrient.
- No hard-coded nutritional targets or optimization objective.
- No mutation of the original CSVs, Google Sheets or personal measurements.
- Existing `Food` Google Sheet is still the intended curated source; a future
  read-only adapter will use the service account after sharing is enabled.
- This migrates only composition and period-scaling calculations; the four
  notebooks are **PARTIAL**, not retire-ready. Substitution, stock adjustment,
  optimizer and recipe selection remain distinct follow-up work packets.
