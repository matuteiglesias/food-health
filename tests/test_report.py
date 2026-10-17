import json
from pathlib import Path
import stat
import tempfile
import unittest

from food_health.measurements.report import (
    build_measurement_report, save_private_report,
)
from food_health.measurements.snapshot import load_snapshot, sync_snapshot


class ReportsTests(unittest.TestCase):
    def test_real_pipeline_shape_on_synthetic_data_only(self):
        rows = [
            {"source_row": 4, "date": "2026-09-01",
             "observed": {"Weight": 80.0, "Waist": 85.0, "Body Fat": 20.0}},
            {"source_row": 5, "date": "2026-09-04",
             "observed": {"Weight": 79.5}},
            {"source_row": 6, "date": "2026-09-06",
             "observed": {"Weight": 79.0}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / ".local" / "data.sqlite3"
            sync_snapshot(db, rows, source_id="synthetic")
            recorded = load_snapshot(db, source_id="synthetic")
            self.assertEqual(recorded, rows)
            report = build_measurement_report(recorded, height_m=1.8)
            self.assertEqual(report["observed_rows"], 3)
            self.assertEqual(report["observed_monthly"]["Weight"][0]["observed_days"], 3)
            self.assertIn("bmi_kg_m2", report["derived_records"][0]["derived"])
            self.assertNotIn("bmi_kg_m2", build_measurement_report(recorded)["derived_records"][0]["derived"])
            path = save_private_report(Path(tmp) / ".local" / "reports" / "body.json", report)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
            self.assertEqual(json.loads(path.read_text())["schema_version"], 1)

    def test_empty_report_fails(self):
        with self.assertRaises(ValueError):
            build_measurement_report([])
