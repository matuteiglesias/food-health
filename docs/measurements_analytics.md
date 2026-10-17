# Migrated measurement analytics (2026-10-17)

Source notebooks remain untouched in ignored `archive/legacy/`.
This module ports *specific useful formulas* into pure, unit-tested Python;
a full notebook retirement has **not** been claimed.

| Legacy source | Migrated now | Intentionally pending |
| --- | --- | --- |
| `02 - interpolacion medidas.ipynb` | Fat mass, muscle mass estimate, lean body mass, BMI with configured height | Quadratic regression, stochastic imputation, resampling |
| `03 - plot time series.ipynb` | Observed-only monthly summaries and 30-day rolling mean | Graph rendering, yearly compare/boxplots, interpolated smoothed lines |
| `04 - plots_advanced.ipynb` | SWR, CWR and legacy WHR ratio formulas | Scatterplot/linear fits and extended exploratory views |

## Behavioral differences worth preserving

The original notebooks often interpolate missing dates before computing centered
rolling averages. The new `trends.py` performs **trailing calendar windows over
actually measured days only** and states the number of measured days represented.
The two procedures must never be treated as identical.

Original notebook `WHR` is `Hips / Waist`, which is the **inverse** of the
usual clinical waist-to-hip ratio. We label it `WHR_legacy_hips_over_waist`.
No clinical or weight-loss inference is made.

The notebook hardcoded a height of 1.81 m; the new BMI calculator accepts
`height_m` explicitly. Nothing assumes this is the user's current height.

## Local private report

After `measurements-sync`, run:

```bash
cd ~/Documents/food
export FOOD_HEALTH_MEASUREMENTS_SHEET_ID="<sheet ID>"
PYTHONPATH=src python3 -m food_health measurements-report
```

No Google credential is needed just to report from an already synced local SQLite
snapshot. The result is `.local/reports/measurements.json` (ignored by Git, chmod
0600). It contains per-month observed summaries, 30-day observed-only rolling means,
and explicitly labeled derived values per source row. Treat the report as private
health data; do **not** attach it to GitHub issues or CI artifacts.

No report upload to Drive, background automation, or deletion of historical notebooks
is done at this stage.
