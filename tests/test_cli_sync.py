import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from food_health.cli import main
from food_health.measurements.snapshot import snapshot_summary


class CliSyncTests(unittest.TestCase):
    def test_sync_and_summary_are_idempotent(self):
        sample_rows = [
            {"date": "2026-10-16", "source_row": 4, "observed": {"Weight": 80.0}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            args = ["measurements-sync", "--root", tmp]
            with patch.dict(os.environ, {"FOOD_HEALTH_MEASUREMENTS_SHEET_ID": "fake-id"}):
                with patch("food_health.measurements.google_sheets.fetch_observed_measurements", return_value=sample_rows):
                    self.assertEqual(main(args), 0)
                    self.assertEqual(main(args), 0)
                self.assertEqual(main(["measurements-summary", "--root", tmp]), 0)
            db = Path(tmp) / ".local" / "measurements.sqlite3"
            self.assertTrue(db.is_file())
            self.assertEqual(snapshot_summary(db, source_id="fake-id")["rows"], 1)

    def test_upstream_failure_does_not_change_local_state(self):
        rows = [{"date": "2026-10-16", "source_row": 4, "observed": {"Weight": 80.0}}]
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"FOOD_HEALTH_MEASUREMENTS_SHEET_ID": "fake-id"}):
                with patch("food_health.measurements.google_sheets.fetch_observed_measurements", return_value=rows):
                    main(["measurements-sync", "--root", tmp])
                with patch("food_health.measurements.google_sheets.fetch_observed_measurements", side_effect=OSError("offline")):
                    with self.assertRaises(OSError):
                        main(["measurements-sync", "--root", tmp])
            db = Path(tmp) / ".local" / "measurements.sqlite3"
            self.assertEqual(snapshot_summary(db, source_id="fake-id")["rows"], 1)
