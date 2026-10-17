# Measurement Atlas — private graphical report

## Generate from the canonical private SQLite snapshot

The Atlas is **read-only**. It does not call Google Sheets and it does not
modify source measurements. To refresh the underlying canonical data first,
run the previously implemented read-only sync using local credentials.

```bash
cd ~/Documents/food
export FOOD_HEALTH_MEASUREMENTS_SHEET_ID="<canonical personal-measurements sheet ID>"
# Optional, only for a fresh sync: set GOOGLE_APPLICATION_CREDENTIALS to the
# existing ignored local service-account JSON path.
.venv/bin/python -m food_health measurements-sync

# Build the HTML image gallery from locally stored data.
.venv/bin/python -m food_health measurements-dashboard

# View locally (Ubuntu):
xdg-open .local/reports/measurement-atlas/index.html
```

Results are private files under `.local/reports/measurement-atlas/`:
- `index.html` — local HTML report, gallery, 90-day period comparison,
  yearly descriptive table and interpretation cautions.
- `manifest.json` — provenance and raw observation counts by metric,
  generated timestamp, generated image names and descriptive comparison data.
- `*.png` — overview, coverage, composition, ratios, change analyses,
  per-metric triptychs and paired relationship charts. The archive activity
  figure is included if the original `archive/legacy/legacy_23/volume.csv`
  remains present.

Source measurements remain in ignored `.local/measurements.sqlite3`.
Do not upload PNGs, HTML, manifest, SQLite or screenshots of these artifacts
to public GitHub; they contain private health data. Files have 0600 permissions;
Atlas directory is restricted to owner 0700.

## Explicitly optional settings

```bash
# Height is NOT hardcoded; BMI appears only if you provide one.
.venv/bin/python -m food_health measurements-dashboard --height-m <meters>

# Compare against OLD goals from archive (these are NOT current targets).
.venv/bin/python -m food_health measurements-dashboard \
  --legacy-goals-file "archive/legacy/legacy_23/goal_measurements.csv"

# Omit historical activity chart.
.venv/bin/python -m food_health measurements-dashboard --no-legacy-activity

# Alternative private output directory:
.venv/bin/python -m food_health measurements-dashboard --output-dir .local/reports/my-atlas
```

`--legacy-goals-file` is **opt-in**. Nothing in a years-old goal CSV should be
interpreted as today's training/health objective or as an endorsed target.

## What each plot means

- The 16 raw metric panels show observation dates, trailing 30-calendar-day
  mean over actually observed dates (minimum three distinct observed days).
  **The trend line is broken across intervals longer than 30 days without a
  computed observation**, preventing misleading continuity.
  A recency table shows the latest actual observation date for each field,
  sequential-month boxplots and overlaid day-of-year trajectories.
- Two physical columns both originally headed `Butt` are represented
  independently (`Butt` and `Butt#2`); the source has not established
  their anatomical meaning, so they are explicitly labeled as first/second
  source columns rather than silently merged.
- The paired scatters join measurements taken on the **same calendar day**.
  Linear/quadratic curves are only descriptive and drawn within the range
  measured. The latest 15 paired observations are highlighted.
- Weekly/18-day/30-day change diagnostics require measured observations in
  the relevant time bins; they never interpolate whole missing periods.
- Historical recorded training occurrences come from the 2022–2023
  archived CSV, not the still-unimplemented present-day workout log.

## Remaining methodological risks

- Charts are retrospective descriptive exploration; correlation is not causal.
- Historical device estimates of Body Fat and Muscle may be inaccurate.
- Averages based on different counts and measurement frequency can be biased.
- Quadratic fits with enough data are still poor predictive models outside
  the observed range; no extrapolations are presented.
- Stochastic imputation and model-based fills from legacy notebooks remain
  intentionally outside the primary report. They need their own isolated
  experimental estimate pipeline before any notebook deletion.
- The catalogue maps every notebook figure to its destination or explicit
  supersession/hold in `docs/measurement_notebook_audit.md`.
