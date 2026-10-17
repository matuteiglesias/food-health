import unittest
from food_health.measurements.normalize import normalize_measurements


class MeasurementTests(unittest.TestCase):
    def test_observed_only_and_duplicate_header_provenance(self):
        grid = [
            ["", "ALERT", "1.0"],
            [],
            ["", "Weight", "Butt", "Butt", "Body Fat", "GYM"],
            ["10/15/2026", "80", "", "97", "", "1"],
            ["10/16/2026", "", "", "", "", "1"],
            ["10/17/2026", "", "", "", "", ""],
        ]
        self.assertEqual(normalize_measurements(grid), [{
            "date": "2026-10-15", "source_row": 4,
            "observed": {"Weight": 80.0, "Butt#2": 97.0}
        }])

    def test_missing_header_fails(self):
        with self.assertRaises(ValueError):
            normalize_measurements([[]])
