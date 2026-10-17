# Post-ingest measurement enrichment (canonical observations remain untouched)

**Intent:** estimate missing anthropometric values *conditional on measurements
already present in that exact source row*. No interpolation of dates, no new
calendar rows, no write-back to the original Sheet, and no silent substitution
of estimates for direct observations.

## End-to-end workflow

```bash
cd ~/Documents/food
export GOOGLE_APPLICATION_CREDENTIALS="$PWD/secret/<service-account>.json"
export FOOD_HEALTH_MEASUREMENTS_SHEET_ID="<canonical sheet id>"
.venv/bin/python -m food_health measurements-sync   # NOW updates observed, then enriched
.venv/bin/python -m food_health measurements-enrichment-summary
# Can also be re-run without any Google permission/network:
.venv/bin/python -m food_health measurements-enrich
```

The canonical private SQLite snapshot `.local/measurements.sqlite3` remains
the observed-only authority. A new ignored private sidecar is stored at
`.local/measurements-enriched.json` (atomic 0600, under owner-only 0700
directory). Identical source fingerprints are idempotent. Reading an out-of-date
derived sidecar fails closed. A failed enrichment cannot overwrite the observed
snapshot; a later offline `measurements-enrich` can repair it.

Read an explicit downstream merged view:

```python
from food_health.measurements.enriched_view import load_enriched_view
rows = load_enriched_view(
    ".local/measurements.sqlite3",
    source_id="<canonical sheet id>",
    output_path=".local/measurements-enriched.json",
)
# rows[i]["observed"]["Weight"]: canonical observed value (never overwritten).
# rows[i]["estimated"]["Body Fat"]: separate estimate metadata if available.
# rows[i]["values"]["Body Fat"]: a convenient merged number, if estimated.
# rows[i]["provenance"]["Body Fat"]: "estimated_not_observed" when estimated.
```

**Important:** existing consumers of `load_snapshot`, the JSON
`measurements-report`, and the default Measurement Atlas are unchanged:
they continue to process *observed-only* data. Downstream modules needing
educated guesses can switch to `load_enriched_view`, which carries uncertainty
and provenance. We do not silently contaminate longitudinal measured trends.

## Directed predictor graph

Each target has 4–6 ordered permitted combinations of up to three
**directly observed** features. Examples:

- Body Fat (%): (Weight, Waist, Belly) -> (Weight, Waist) ->
  (Weight, Belly) -> (Weight) -> (Waist).
- Muscle (%): corresponding measured predictors, **not** estimated Body Fat.
- Thigh: (Weight, Hips, Waist) -> (Weight, Hips) -> (Hips, Waist)
  -> (Hips) -> (Weight).
- Calf: (Weight, Thigh, Waist) -> (Weight, Thigh) ->
  (Weight, Waist) -> (Thigh) -> (Weight).
- Butt/Butt#2: (Weight, Hips, Waist) with smaller feature subsets.

All targets have some one-feature routes. Thus weight-only rows may receive
conditional estimates when enough *historical co-observations* exist. If no
feature route is supported, the system abstains rather than inventing a number.
The two source columns `Butt` and `Butt#2` are independent targets.

For each route:
1. Train an RBF-kernel Nadaraya-Watson conditional mean on complete, direct
   observations. Standardize each predictor by training spread.
2. Reserve the most recent quarter of *distinct observed dates* as a temporal
   validation set; require >=28 earlier training dates, >=10 later evaluable
   dates. No same-day training/validation mixing.
3. Compare holdout MAE to a training-set median baseline. Routes with >=5%
   improvement receive the descriptive status `validated_on_historical_holdout`.
   Other routes may still produce `weak` educated guesses, **not** a performance
   claim. Models with insufficient local support (effective kernel sample
   size <5, nearest standardized distance >2.5) abstain.
4. Estimate a conservative *heuristic* predictive range based on historical
   validation errors, local target dispersion, and increasing staleness
   (for targets last observed years ago). This is NOT calibrated 90% coverage
   and is not a Bayesian posterior.

Candidate routes are ranked on their historical holdout results; this is a
screening/selection strategy, **not** a final unbiased generalization estimate.
A future independent temporal backtest should quantify performance on
newer data, especially for targets recorded through 2023 only.

## Device-based Body Fat and Muscle are not current measurements

Historically, the balance's displayed fat/muscle percentages were
**device-dependent BIA-derived estimates**. The latest directly observed Body
Fat/Muscle readings are from 2023; a 2026 inference reports only the old scale's
expected output conditional on other measurements, **not a true/current
body-fat percentage or medical-grade measurement**. These rows get status
`historical_device_proxy__temporal_transfer_unvalidated` whenever the direct
target hasn't been observed for >365 days.

BIA estimates can depend on hydration, timing, device, algorithm and reference
population, and may disagree with criterion body-composition measurements:
- [2026 expert methodological standards for body composition](https://pmc.ncbi.nlm.nih.gov/articles/PMC13197919/)
- [2026 systematic review versus four-compartment reference](https://pmc.ncbi.nlm.nih.gov/articles/PMC12922097/)
- [scikit-learn guidance on evaluating time-dependent data](https://scikit-learn.org/stable/modules/cross_validation.html)

Do not treat estimated body composition as an input to medical decisions or
automated calorie prescriptions.

## Safety/integrity invariants

- Only explicit source-row observations enter **both** predictors and labels
  in training. Never train on previously estimated predictors or targets.
- A row's already-observed values always take precedence, even when atypical.
- Training-time temporal holdout uses **distinct calendar dates**.
- Source edits invalidate the derived fingerprint; rerunning the sync
  recomputes estimates from scratch.
- No stochastic gap filling, no future-date/backfill changes to Sheets, no new
  observation records, no implied interpolation between old/next measurements.
- No actual health values, model JSON, private screenshots or service-account
  keys are stored in the public GitHub repository.

## Next refinement

Evaluate out-of-time performance in date periods not used to rank predictor
routes; consider reliability diagnostics by available-feature pattern,
regime/measurement-device changes, train-size/coverage thresholds, and an
**explicit opt-in estimate overlay** for the Measurement Atlas with distinct
point styles and uncertainty bands. Do not replace the observed-only default.
