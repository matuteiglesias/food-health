# Notebook migration ledger — keep original notebooks until exit gates pass

All 13 notebook files are preserved in the ignored local `archive/legacy/`.
Cloud GitHub has no raw private files. The `Personal Measurements` Google Sheet
is canonical; local historic CSVs are **not** replayed into it.

| Original notebook | Status (2026-10-17) | New implementation | Missing exit-gate capability |
| --- | --- | --- | --- |
| `Measurements.ipynb` | HOLD / duplicate candidate | — | Compare plot/activity output with `01 - Dias Actividad` |
| `01 - Dias Actividad.ipynb` | PENDING | — | Activity-day plot, input semantics |
| `02 - interpolacion medidas.ipynb` | PARTIAL | `measurements.analytics` | Fitting, explicit estimation channel, testable parity |
| `03 - plot time series.ipynb` | PARTIAL | `measurements.trends`, `measurements.report` | Year-by-year plots, boxplots, alternative smoothing |
| `04 - plots_advanced.ipynb` | PARTIAL | `measurements.analytics` | Scatterplots, regression, extended comparisons |
| `nutrientes.ipynb` | PARTIAL | `nutrition.composition` | Optimization experiments, diagnostics, further nutrient outputs |
| `nutrientes 24.ipynb` | PARTIAL | `nutrition.composition`, `nutrition.optimize` | Compare remaining solver variants, iteration diagnostics and chart outputs |
| `dieta.ipynb` | PARTIAL | `nutrition.composition`, `nutrition.optimize` | Meal suggestions, alternate random-search experiments, notebook output parity |
| `compras.ipynb` | PARTIAL | `nutrition.composition.scale_quantities` | Stock reconciliation and shopping projection |
| `legacy_23/substitutes.ipynb` | PARTIAL | `nutrition.substitutes` | Pairplot visualizations, non-nutrient filters and workflow validation |
| `tickets/ocr.ipynb` | PENDING | — | Private OCR pipeline and extraction validation |
| `printer dias de semana.ipynb` | PENDING / low priority | — | Only migrate if useful to operations |
| `.ipynb_checkpoints/Measurements-checkpoint.ipynb` | HOLD / checkpoint | — | Classify duplicate and retain only if needed |

## Retirement gate
A notebook may be tagged **RETIRE-READY** only when every desired output/function
is either covered by tests in the Python package or explicitly retired as an
experiment, and original/synthetic parity checks pass. A notebook may then stay
in cold archive; irreversible deletion requires separate human approval.

Priorities: measurements stable -> nutrition composition/optimizer -> inventory ->
training event logging -> receipts. Do not open all workstreams at once.
