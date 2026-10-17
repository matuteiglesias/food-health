# Measurement notebooks: figure-by-figure recovery audit

**Scope:** private snapshots from the canonical Personal Measurements / MEDIDAS
Sheet, supplemented by the *archived* 2022–2023 activity CSV if present.
No raw data, notebook bodies or images belong in this public repository.

**Audit method:** static reading of notebook source cells, not execution of
obsolete notebooks. Cell numbers are zero-based. This is a migration
disposition ledger, not a claim of exact pixel reproduction.

| Legacy notebook / cells | Historical analysis / figure | New home | Disposition |
| --- | --- | --- | --- |
| 01 - Dias Actividad: 2 | Weekly recorded Resistance/Cardio/Calistenia bar | dashboard / historical-activity | REPLACED; clearer line chart, source is historical only |
| 01 - Dias Actividad: 3 | Weekday/week activity mark calendar | dashboard / historical-activity | REPLACED by archived weekday/date marks; not current training |
| Measurements: 2–3 | Exact source-code duplicates of activity notebook | same archived-activity figure | REDUNDANT: both files have identical notebook source hash |
| 02 - interpolacion medidas: 4 | Daily resampling/interpolation | plot_data observed-only | SUPERSEDED: do not present invented daily observations |
| 02 - interpolacion medidas: 6–8 | Quadratic regressions (x0-centered), fit-based imputation | dashboard relationship fits; estimates follow-up | PARTIAL: descriptive curves present; old imputation not mixed into source |
| 02 - interpolacion medidas: 11–12 | Random simulated gap filling | separate future estimates sandbox | HOLD: simulations would falsify apparent measurement coverage if unlabeled |
| 02 - interpolacion medidas: 13 | Group-based fill of missing Body Fat and Muscle | separate future estimates sandbox | HOLD: not raw observations; requires validation |
| 02 - interpolacion medidas: 14, 37 | Fat mass, muscle mass estimate, lean mass, BMI | measurements.analytics / body-composition | MIGRATED; BMI needs explicit current height |
| 02 - interpolacion medidas: 17–20, 29 | Weekly/10-day means, changes, percent changes and counts | plot_data.weekly_stats / ten_day_stats; coverage + changes | MIGRATED; available-only dates |
| 02 - interpolacion medidas: 32–33 | Recent polynomial trend / interpolated smooth moving mean | per-metric in-range fit; trailing 30d observed mean | MIGRATED semantics, intentionally no interpolation |
| 02 - interpolacion medidas: 35–36 | Old goal table / comparison | goals.compare_goals + opt-in plot/table | MIGRATED, opt-in because historical targets are not current goals |
| 03 - plot time series: 4–5 | Smoothed series and sequential year-month boxplots | per-metric chart 1–2 | MIGRATED with observed-only trend |
| 03 - plot time series: 7–8 | Year-colored points with polynomial fits and target lines | per-metric chart 3; opt-in goals overlay | MIGRATED; no fit outside observed x-range |
| 03 - plot time series: 10, 12 | Many duplicated per-metric dashboards; week/year boxplots | one maintained per-metric triptych + coverage and changes | CONSOLIDATED; same scientific comparisons |
| 03 - plot time series: 14–16 | Dated weight-loss/calorie speculative narrative and old goals | archival commentary only | RETIRED as historical personal assumptions, not current prescriptions |
| 03 - plot time series: 22 | Muscle percentage vs body-fat scatter | relationship-Muscle-Body-Fat chart | MIGRATED |
| 04 - plots_advanced: 4, 6 | Body Fat vs Muscle, fat mass vs muscle mass | relationship chart set | MIGRATED |
| 04 - plots_advanced: 8 | Lean body mass vs device muscle mass + fit | relationship chart set | MIGRATED; same-day pairs only |
| 04 - plots_advanced: 9–10 | Waist/Belly/Hips/Butt vs fat mass or Body Fat quadratic | relationship charts, restricted to observed x-range | MIGRATED; no extrapolated 9kg predicted targets |
| 04 - plots_advanced: 12 | Arm/Flexed vs derived muscle mass | relationship charts | MIGRATED |
| 04 - plots_advanced: 13 | Chest vs muscle/fat estimates, arbitrarily offset fat | relationship chart | PARTIAL; physical relationship kept, arbitrary visual fat offset deliberately omitted |
| 04 - plots_advanced: 14 | SWR, CWR and Hips/Waist ratios | ratios chart / analytics | MIGRATED; note WHR is inverse of usual clinical convention |
| 04 - plots_advanced: 15 | Weight vs Body Fat, recent 15 paired observations, regression | relationship chart | MIGRATED; no fixed axes or imputed points |
| 04 - plots_advanced: 16 | 2-bin weight change using 30-day bins and interpolation | changes plot 30-day bins | MIGRATED using real sample coverage; interpolated version superseded |
| Measurements-checkpoint: 2–3 | Activity CSV and legacy measurement CSV loader | existing Sheets adapter + optional archival activity | SUPERSEDED |
| Measurements-checkpoint: 5–11, 19 | Weekly/10d aggregation, counts, growth & percent changes | plot_data weekly/ten-day, coverage/changes, annual table | MIGRATED |
| Measurements-checkpoint: 22–23, 30–31 | Polynomial trend, smoothed line and reference levels | per-metric triptychs, goals opt-in | CONSOLIDATED; commented duplicate plots retired |
| Measurements-checkpoint: 25 | Last measurements vs old goals and 40% step | goals.compare_goals, opt-in goals table | MIGRATED with explicit historical labeling |
| Measurements-checkpoint: 42–49 | Body Fat/Muscle, fat vs muscle mass and fits | relationship chart set | CONSOLIDATED |
| Measurements-checkpoint: 51–52 | Arm/Flexed vs muscle mass and Chest vs mass estimates | relationship charts | MIGRATED, arbitrary constant offsets retired |
| Measurements-checkpoint: 53–54 | Ratios and recent Weight/Body Fat relationship | ratio + relationship charts | MIGRATED |
| Measurements-checkpoint: 55 | 18-day bin mean, difference 2 bins | changes plot 18-day bins | MIGRATED using observed bins only |

## Consolidated report gallery

The maintained graph families are:
1. All 16 separately named raw body metrics (including both distinct Butt
   columns) — temporal trajectories + monthly distributions + year overlays.
2. Coverage heatmap (by metric and calendar month).
3. Body composition estimates and anthropometric ratios.
4. Weekly and two-bin (18/30-day) differences without filling missing days.
5. Paired scatter relationships with recent points highlighted, linear or
   quadratic **descriptive** within-observed-range fits.
6. Pairwise correlation matrix with paired measured dates.
7. Private tables: last 90 vs prior 90 calendar days, annual means/counts;
   optional historical target table and overlay.
8. Archived activity chart (weekly recorded day counts + weekday/date marks).

*Not a clinical dashboard.* Device-based body fat and muscle percentages are
estimates; linear/quadratic fits describe correlations, not causes or forecasts.
Historical objective lines and old calorie conjectures are not current goals.

## Remaining retirement gates

- Standalone imputation/simulation experiments (02 cells 6–13) require a
  separate **opt-in estimates** API with provenance and no contamination of
  the canonical observations. They are not default Atlas graphs.
- Historical goal values are opt-in; do not silently adopt their targets.
- The archived activity CSV does not substitute a verified training session
  log, which needs its own implementation.
- A visual side-by-side review of the representative legacy figures, dates
  and sample counts should precede any notebook retirement. No originals
  have been modified or removed.
