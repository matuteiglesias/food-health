# Notebook-to-package migration map

| Local legacy notebook | Future capability | Gate |
| --- | --- | --- |
| 01 - Dias Actividad.ipynb | training.activity | Verify logged vs planned activity |
| Measurements.ipynb | training.activity | Check duplicate of 01 |
| 02 - interpolacion medidas.ipynb | measurements.estimates | Simulated/imputed values separate from observed |
| 03 - plot time series.ipynb | measurements.trends | Quarterly/yearly/time-series visualizations |
| 04 - plots_advanced.ipynb | measurements.analytics | Ratios and comparative exploratory plots |
| dieta.ipynb | nutrition.optimize | Parameterize energy/macro goals, constraints |
| nutrientes.ipynb | nutrition.composition | Recover composition calculations |
| nutrientes 24.ipynb | nutrition.optimize | Deduplicate optimizers, exclude dead experiments |
| compras.ipynb | inventory.planning | Compute stock-to-shopping requirements |
| legacy_23/substitutes.ipynb | nutrition.substitutes | Nutrient-space similarity |
| tickets/ocr.ipynb | receipts.extract | Optional, private receipt extraction |
| printer dias de semana.ipynb | utils.calendar | Low priority |

Archive originals are available privately in `archive/legacy/`. Do not migrate notebook outputs into the public repo.

## Acceptance gates for next PR
- Read original Google Sheet without mutating it.
- Test date parsing, duplicated headings, missing values and unit invariants.
- Ensure changes in historical cells are detected, not append-only.
- Make writes idempotent into local private state, with source provenance.
- Test a rerun, missing credentials and partial network failure.
