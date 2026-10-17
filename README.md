# food-health

Python toolkit for personal measurements, training, nutrition, and household food operations.

**Privacy:** This GitHub repository is PUBLIC. Personal measurements, receipts, private archives, and extracts must remain local or in permission-controlled Google Drive. Never commit raw personal records. Google Sheets **Personal Measurements** is the canonical measurement source.

## Workstation

The local Git working tree is `~/Documents/food`. The original 89 files are safely in `archive/legacy/` (ignored by Git), with a local SHA-256 manifest.

```bash
cd ~/Documents/food
PYTHONPATH=src python3 -m food_health doctor
PYTHONPATH=src python3 -m unittest discover -s tests -v
# Optional:
python3 -m pip install -e .
```

No automatic writes to Google Sheets, processing of private data, background jobs, or credential access happen in this bootstrap.

See `docs/architecture.md` and `docs/migration_map.md`.


## Private measurements visual report

After a read-only canonical sync (requires the existing private Google service
account and spreadsheet ID), generate a local image-and-HTML dashboard:

```bash
export FOOD_HEALTH_MEASUREMENTS_SHEET_ID="<canonical-sheet-id>"
.venv/bin/python -m food_health measurements-dashboard
xdg-open .local/reports/measurement-atlas/index.html
```

This reads the private SQLite snapshot, **not** the legacy measurements CSV,
and produces an HTML gallery with observed-only per-metric trends, monthly
distributions, annual overlays, anthropometric relations, coverage, 18/30-day
changes and optional archive activity. Files stay under Git-ignored
`.local/reports/measurement-atlas/`. Configure reporting dependencies using
`pip install -e '.[reports]'` inside a local virtual environment.

See `docs/measurement_atlas.md` for interpretation and options, and
`docs/measurement_notebook_audit.md` for the explicit notebook-cell port map.


## Post-ingest inferred measurements (separate from observations)

`measurements-sync` now automatically builds a second private projection
`.local/measurements-enriched.json` after committing the canonical SQLite.
Its directed predictor graph uses only directly observed, same-row body
measurements, a Gaussian kernel conditional average, historical-date
holdouts, empirical conditional p10/p50/p90, and heuristic error ranges.
The source Google Sheet and observed SQLite table are never overwritten.

```bash
.venv/bin/python -m food_health measurements-enrich             # offline regenerate
.venv/bin/python -m food_health measurements-enrichment-summary # aggregate counts only
```

Python clients can opt in using
`measurements.enriched_view.load_enriched_view(...)`; it returns
`observed`, `estimated`, `values`, and `provenance` separately.
The original observed-only report and dashboard stay unchanged.
Inferences for old-scale Body Fat and Muscle are historical-device proxies
and are *not current direct measurements*. Details and caveats:
`docs/measurement_enrichment.md`.
