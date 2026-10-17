# Notebook migration ledger — keep original notebooks until exit gates pass

All 13 notebook files are preserved in the ignored local `archive/legacy/`.
Cloud GitHub has no raw private files. The `Personal Measurements` Google Sheet
is canonical; local historic CSVs are **not** replayed into it.

| Original notebook | Status (2026-10-17) | New implementation | Missing exit-gate capability |
| --- | --- | --- | --- |
| `Measurements.ipynb` | DUPLICATE | `measurements.activity`, `dashboard` | Identical notebook source code; redundant copy |
| `01 - Dias Actividad.ipynb` | HISTORICAL CHARTS MIGRATED | `measurements.activity`, `dashboard` | Current training event log remains distinct |
| `02 - interpolacion medidas.ipynb` | PARTIAL | `measurements.analytics`, `plot_data`, Atlas | Isolated experimental imputation/simulation, regression parity |
| `03 - plot time series.ipynb` | CHARTS MIGRATED | `measurements.dashboard`, `analysis_tables`, `goals` | Visual acceptance; interpolated smoothing intentionally superseded |
| `04 - plots_advanced.ipynb` | CHARTS MIGRATED | `measurements.dashboard`, `plot_data` | Visual acceptance; experimental old offsets deliberately retired |
| `nutrientes.ipynb` | PARTIAL | `nutrition.composition` | Optimization experiments, diagnostics, further nutrient outputs |
| `nutrientes 24.ipynb` | PARTIAL | `nutrition.composition`, `nutrition.optimize` | Compare remaining solver variants, iteration diagnostics and chart outputs |
| `dieta.ipynb` | PARTIAL | `nutrition.composition`, `nutrition.optimize` | Meal suggestions, alternate random-search experiments, notebook output parity |
| `compras.ipynb` | PARTIAL | `nutrition.composition.scale_quantities` | Stock reconciliation and shopping projection |
| `legacy_23/substitutes.ipynb` | PARTIAL | `nutrition.substitutes` | Pairplot visualizations, non-nutrient filters and workflow validation |
| `tickets/ocr.ipynb` | PENDING | — | Private OCR pipeline and extraction validation |
| `printer dias de semana.ipynb` | PENDING / low priority | — | Only migrate if useful to operations |
| `.ipynb_checkpoints/Measurements-checkpoint.ipynb` | CHARTS MIGRATED | `measurements.dashboard`, `plot_data`, `goals` | Historical estimators and goals opt-in; visual review |

## Retirement gate
A notebook may be tagged **RETIRE-READY** only when every desired output/function
is either covered by tests in the Python package or explicitly retired as an
experiment, and original/synthetic parity checks pass. A notebook may then stay
in cold archive; irreversible deletion requires separate human approval.

Priorities: measurements stable -> nutrition composition/optimizer -> inventory ->
training event logging -> receipts. Do not open all workstreams at once.

See `docs/measurement_notebook_audit.md` for cell-by-cell disposition and exact coverage of the measurement notebook visuals. No original notebook has been deleted.
