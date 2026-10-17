# Canonical measurement snapshot — local-only

The authoritative **Personal Measurements / MEDIDAS** Google Sheet is read-only.
The snapshot is a **private local cache** with the physical spreadsheet row index as provenance.

## Run

```bash
cd ~/Documents/food
# The JSON lives in ignored secret/; never commit it or print it.
export GOOGLE_APPLICATION_CREDENTIALS="$PWD/secret/<your-service-account-file>.json"
export FOOD_HEALTH_MEASUREMENTS_SHEET_ID="<canonical-sheet-id>"
PYTHONPATH=src python3 -m food_health measurements-sync
PYTHONPATH=src python3 -m food_health measurements-summary
```

By default this writes `.local/measurements.sqlite3` with restrictive file permissions, and prints only aggregate counts.

Each sync fully reads the canonical Google Sheet, normalizes observed anthropometric fields,
then atomically reconciles changed, inserted and deleted physical rows in SQLite.
Repeat runs are idempotent. Duplicate dates are *not* silently merged.
No historical CSV records are replayed. No Google Sheets updates or scheduler are configured.

## Limitation
Worksheet row indices can change after insertion/deletion. They are provenance locators, not immutable event IDs.
Row moves will show as updates/removals in a full-snapshot diff. If a request fails before
writing the local snapshot, previous state is preserved.

For established datasets (20+ rows), the sync rejects removal of more than 10%
of existing rows in a single run. Investigate incomplete reads rather than
forcing a large deletion.
