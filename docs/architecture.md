# Food & Health — architecture 0.1 (2026-10-17)

## Sources
- **Personal Measurements / MEDIDAS**: canonical; original history already included. No legacy backfill or reconciliation.
- **Training Routines — Reference**: historical program templates, not proof of workouts.
- **Food / CURATED_PLAN**: existing food plan; **SOURCE_NUTRIENTS** is a reference catalog.
- **Household Stock / STOCK**: current inventory candidate; check freshness before use.
- All source files retain their original locations; this repository stores no personal data.

## Boundaries
- GitHub is public: ONLY source code, tests, synthetic examples, nonsensitive docs.
- Local `archive/legacy/`: original notebook/code/data snapshots, not synchronized to GitHub.
- Google Drive **Food - Health**: owned document hub. Canonical Sheets remain where they live.
- SQLite and private derived reports will be local, under ignored directories.
- Raw observations must never be conflated with interpolations, estimates or simulations.
- Initial Sheets connectors must be read-only; credentials via external private config.

## Pull-based slices
1. Canonical sheet read adapter + sheet-independent normalization (with tests).
2. Idempotent local snapshot of observed rows, including edits to older dates.
3. Reproducible trends and reports with explicit provenance.
4. Food optimizer and substitutions extracted from legacy.
5. Inventory consumption forecasts, training sessions, optional receipt OCR.

No server, scheduler or Google Sheets write-back is deployed by this bootstrap.
