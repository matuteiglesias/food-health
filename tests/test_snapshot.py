import os
from pathlib import Path
import stat
import tempfile
import unittest

from food_health.measurements.snapshot import (
    snapshot_summary, sync_snapshot,
)


def sample(row, day="2026-10-16", value=80):
    return {"source_row": row, "date": day, "observed": {"Weight": float(value)}}


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / ".local" / "health.sqlite3"

    def tearDown(self):
        self.tmp.cleanup()

    def sync(self, rows):
        return sync_snapshot(self.path, rows, source_id="fake-sheet-id")

    def test_initial_duplicate_dates_and_idempotency(self):
        rows = [sample(4), sample(5)]
        first = self.sync(rows)
        self.assertEqual((first.rows, first.inserted, first.duplicate_dates), (2, 2, 1))
        repeated = self.sync(rows)
        self.assertEqual(
            (repeated.inserted, repeated.updated, repeated.deleted, repeated.unchanged),
            (0, 0, 0, 2),
        )
        self.assertEqual(snapshot_summary(self.path, source_id="fake-sheet-id")["duplicate_dates"], 1)

    def test_historical_edit_and_removed_row(self):
        self.sync([sample(4), sample(5)])
        result = self.sync([sample(4, value=81)])
        self.assertEqual((result.updated, result.deleted, result.inserted), (1, 1, 0))
        self.assertEqual(snapshot_summary(self.path, source_id="fake-sheet-id")["rows"], 1)

    def test_malformed_full_snapshot_leaves_prior_rows_intact(self):
        self.sync([sample(4)])
        with self.assertRaises(ValueError):
            self.sync([sample(4, value=81), sample(4, value=82)])
        self.assertEqual(snapshot_summary(self.path, source_id="fake-sheet-id")["rows"], 1)

    def test_local_permissions(self):
        self.sync([sample(4)])
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)

    def test_large_partial_read_is_rejected_without_data_loss(self):
        history = [sample(i) for i in range(4, 54)]
        self.sync(history)
        with self.assertRaisesRegex(ValueError, "over 10%"):
            self.sync(history[:10])
        self.assertEqual(snapshot_summary(self.path, source_id="fake-sheet-id")["rows"], 50)

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            self.sync([sample(4, value=float("nan"))])
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
