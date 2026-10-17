"""Synthetic tests only: no personal measurements in public repository."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest

from food_health.measurements.enrichment import (
    ALL_METRICS, BODY_DEVICE, PREDICTOR_GRAPH, MODEL_VERSION,
    _feature_examples, _fit_candidate, infer_missing, source_fingerprint,
)
from food_health.measurements.enriched_view import (
    refresh_enrichment, load_enriched_view,
)
from food_health.measurements.snapshot import sync_snapshot


def scenario():
    """81 measured days of correlated data + 19 dates with only weight."""
    first = date(2024, 1, 1)
    rows = []
    for i in range(100):
        day = (first + timedelta(days=i*7)).isoformat()
        weight=70 + i * 0.12 + 2 * __import__("math").sin(i / 8)
        observed={"Weight":float(weight)}
        if i < 81:
            observed["Waist"]=float(76 + .6 * (weight - 70) + .7 * __import__("math").sin(i / 5))
            observed["Belly"]=float(observed["Waist"] + 3.0)
            observed["Hips"]=float(90 + .25*(weight-70))
            observed["Body Fat"]=float(14+.35*(weight-70)+.15*__import__("math").sin(i/3))
            observed["Muscle"]=float(42 - .1*(weight-70))
            observed["Thigh"]=float(51+.3*(weight-70))
            observed["Calf"]=float(36 + .13*(weight-70))
        rows.append({"source_row":i+4,"date":day,"observed":observed})
    return rows


class ModelTests(unittest.TestCase):
    def test_all_routes_exclude_target_and_use_observed_only(self):
        self.assertEqual(set(PREDICTOR_GRAPH),set(ALL_METRICS))
        for target, routes in PREDICTOR_GRAPH.items():
            for route in routes:
                self.assertNotIn(target,route)
        rows=scenario()
        result=infer_missing(rows)
        self.assertEqual(result["model_version"],MODEL_VERSION)
        self.assertEqual(result["input_rows"],100)
        self.assertEqual(len(result["rows"]),100)
        self.assertGreater(result["estimation_count"],0)
        # Historical device values must remain intact, and late weight-only
        # rows have no invented observation of Body Fat or Muscle.
        for i, row in enumerate(rows):
            predicted=result["rows"][i]["estimated"]
            self.assertFalse(set(predicted) & set(row["observed"]))
            for name, info in predicted.items():
                self.assertEqual(info["status"],"estimated_not_observed")
                self.assertTrue(set(info["features"]) <= set(row["observed"]))
                self.assertLessEqual(info["lower"],info["value"])
                self.assertGreaterEqual(info["upper"],info["value"])
                self.assertGreater(info["validation_days"],0)
                self.assertGreaterEqual(info["training_rows"],38)
                self.assertEqual(info["model_version"],MODEL_VERSION)
                if name in BODY_DEVICE:
                    self.assertEqual(info["source_type"],"old_scale_proxy")
                    self.assertLessEqual(info["upper"],100)
        self.assertTrue(any("Body Fat" in r["estimated"] for r in result["rows"][81:]))
        self.assertTrue(any("Thigh" in r["estimated"] for r in result["rows"][81:]))

    def test_validation_uses_chronological_date_blocks(self):
        rows=scenario()
        examples=_feature_examples(rows,"Body Fat",("Weight",))
        fitted=_fit_candidate(examples,"Body Fat",("Weight",))
        self.assertIsNotNone(fitted)
        self.assertEqual(fitted["train_rows"],81)
        self.assertGreaterEqual(fitted["calibration_size"],10)
        self.assertGreaterEqual(fitted["val_mae"],0)
        self.assertGreaterEqual(fitted["base_uncertainty"],0)

    def test_do_not_infer_without_any_predictor_or_training(self):
        sparse=[
            {"date":(date(2025,1,1)+timedelta(days=i)).isoformat(),
             "source_row":4+i,"observed":{"Weight":float(60+i*.1)}}
            for i in range(10)
        ]
        inferred=infer_missing(sparse)
        self.assertEqual(inferred["estimation_count"],0)
        self.assertTrue(all(not row["estimated"] for row in inferred["rows"]))

    def test_fingerprint_ignores_order_but_not_value_edits(self):
        rows=scenario()
        old=source_fingerprint(rows)
        self.assertEqual(old,source_fingerprint(list(reversed(rows))))
        rows[0]["observed"]["Weight"]+=1.0
        self.assertNotEqual(old,source_fingerprint(rows))


class PersistenceTests(unittest.TestCase):
    def test_atomic_idempotent_derived_sidecar_and_staleness_detection(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/".local"/"measurements.sqlite3"
            sidecar=Path(td)/".local"/"measurements-enriched.json"
            rows=scenario()
            sync_snapshot(db,rows,source_id="synthetic")
            first=refresh_enrichment(db,source_id="synthetic",output_path=sidecar)
            self.assertTrue(first["changed"])
            self.assertEqual(first["input_rows"],100)
            self.assertGreater(first["estimation_count"],0)
            again=refresh_enrichment(db,source_id="synthetic",output_path=sidecar)
            self.assertFalse(again["changed"])
            enriched=load_enriched_view(db,source_id="synthetic",output_path=sidecar)
            self.assertEqual(len(enriched),100)
            self.assertEqual(enriched[-1]["provenance"]["Weight"],"observed")
            self.assertEqual(enriched[-1]["values"]["Weight"],rows[-1]["observed"]["Weight"])
            self.assertIn("Body Fat",enriched[-1]["estimated"])
            original_observed=dict(enriched[-1]["observed"])
            rows[-1]["observed"]["Weight"]+=2.0
            sync_snapshot(db,rows,source_id="synthetic")
            with self.assertRaisesRegex(ValueError,"Stale enrichment"):
                load_enriched_view(db,source_id="synthetic",output_path=sidecar)
            receipt=refresh_enrichment(db,source_id="synthetic",output_path=sidecar)
            self.assertTrue(receipt["changed"])
            corrected=load_enriched_view(db,source_id="synthetic",output_path=sidecar)
            self.assertNotEqual(corrected[-1]["observed"],original_observed)

    def test_cross_source_enrichment_not_silently_reused(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/".local"/"measurements.sqlite3"
            sidecar=Path(td)/".local"/"measurements-enriched.json"
            rows=scenario()
            sync_snapshot(db,rows,source_id="first")
            sync_snapshot(db,rows,source_id="second")
            refresh_enrichment(db,source_id="first",output_path=sidecar)
            with self.assertRaisesRegex(ValueError,"source/worksheet mismatch"):
                load_enriched_view(db,source_id="second",output_path=sidecar)
            self.assertTrue(refresh_enrichment(
                db,source_id="second",output_path=sidecar)["changed"])
            self.assertEqual(len(load_enriched_view(
                db,source_id="second",output_path=sidecar)),100)

    def test_sensitivity_band_widens_for_older_instrument_data(self):
        rows=scenario()
        # Equal weight-only query values at different future dates, same
        # conditional distribution, different transfer staleness.
        rows[99]["observed"]["Weight"]=rows[81]["observed"]["Weight"]
        result=infer_missing(rows)
        early=result["rows"][81]["estimated"]["Body Fat"]
        late=result["rows"][99]["estimated"]["Body Fat"]
        self.assertEqual(early["features"],late["features"])
        self.assertEqual(early["value"],late["value"])
        self.assertGreater(late["target_observation_staleness_days"],
                           early["target_observation_staleness_days"])
        self.assertGreaterEqual(late["upper"]-late["lower"],
                                early["upper"]-early["lower"])

    def test_no_overwrite_even_with_weird_observed_value(self):
        rows=scenario()
        rows[-1]["observed"]["Body Fat"]=0.0
        enriched=infer_missing(rows)
        self.assertNotIn("Body Fat",enriched["rows"][-1]["estimated"])

if __name__=="__main__":
    unittest.main()
