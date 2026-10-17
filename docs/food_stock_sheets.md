# Food and Household Stock: live READ-ONLY integration

The service account must have **Viewer** access to the canonical original
`Food` spreadsheet (`CURATED_PLAN` and `SOURCE_NUTRIENTS`) and
`Household Stock` spreadsheet (`STOCK`). Requests use only the Google Sheets
readonly scope and Application Default Credentials; originals are never edited.

The live source schema inspected 2026-10-17 is:
- `CURATED_PLAN`: 29 rows with positive `cant 3d` and integer `ID`; also
  contains 6/12/24-day quantities and repeated calorie/macro columns.
  **Only** `cant 3d` and `ID` are parsed as the primary plan; the derived
  nutrient columns are never double-counted.
- `SOURCE_NUTRIENTS`: 14,165 unique numeric IDs; seven nutrients per 100 g
  are selected from its first 11 columns.
- `STOCK`: 47 rows and `qty_g 10/01`. The heading is preserved exactly;
  **the year/current validity cannot be inferred**, and non-numeric source
  values stay unknown rather than becoming zero.

## Runtime contract

Environment variables (local only; do not commit to Git):
`FOOD_HEALTH_FOOD_SHEET_ID`, `FOOD_HEALTH_STOCK_SHEET_ID`,
`GOOGLE_APPLICATION_CREDENTIALS`.

`fetch_food_and_stock` reads all three tabs (with a bounded column range),
checks the plan's IDs against the source catalog, and produces one Python
structure with explicit provenance. No consumption, nutrition goals,
or actual stock availability are inferred. Use `private_snapshot` to save
under the Git-ignored `.local` tree; it is atomic, permissions 0600/0700,
and idempotent for unchanged source data. Suspicious bulk truncations are
rejected before overwriting an established snapshot.

Next stages: canonical food/stock-only CLI sync and offline summaries,
possible cross-source reconciliation, then `nutrition.substitutes`.
The archived notebooks are kept until an explicit migration gate passes.

## CLI usage (local only)

After configuring the two spreadsheet IDs and external application-default
service account credentials, run:

```bash
cd ~/Documents/food
export GOOGLE_APPLICATION_CREDENTIALS="$PWD/secret/<service-account-key>.json"
export FOOD_HEALTH_FOOD_SHEET_ID="<Food canonical spreadsheet ID>"
export FOOD_HEALTH_STOCK_SHEET_ID="<Household Stock canonical spreadsheet ID>"
.venv/bin/python -m food_health food-sync
.venv/bin/python -m food_health food-sync  # expect changed=false
.venv/bin/python -m food_health food-summary
```

`food-sync` validates that all active recipe items resolve into the canonical
nutrient catalog and that the requested seven nutrient quantities are computable,
before replacing the local snapshot. It prints only counts and a change flag.
The result `.local/food-stock.json` contains private planning and stock data
and must not be committed or published.
