# Canonical measurements adapter

This module reads the original **Personal Measurements** spreadsheet, tab **MEDIDAS**, without modifying it.

## Configuration

- Install optional dependencies: `pip install -e '.[measurements]'`
- Supply `FOOD_HEALTH_MEASUREMENTS_SHEET_ID` through a **private environment variable**.
- Configure Google Application Default Credentials externally with access to the source spreadsheet. The adapter requests only `https://www.googleapis.com/auth/spreadsheets.readonly`.
- No background job, writeback, or local snapshot is enabled yet.

```python
from food_health.measurements.google_sheets import fetch_observed_measurements

rows = fetch_observed_measurements()
print(f"Rows with actual anthropometric observations: {len(rows)}")
```

Do not print the raw measurements to public logs. Returned rows are normalized observations only, with source row indexes to support provenance and future change detection. Derived values and interpolation will be implemented separately.

**Known limitation:** first iteration normalizes only the anthropometric fields. Other MEDIDAS columns (sleep, gym, substances, etc.) are intentionally excluded pending explicit data modeling and privacy review.
