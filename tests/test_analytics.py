import math
import unittest
from food_health.measurements.analytics import derived_metrics
from food_health.measurements.trends import (
    rolling_observed_mean, monthly_observed_summary,
)


def rec(date, value, row=4):
    return {"date": date, "source_row": row, "observed": {"Weight": value}}


class DerivedTests(unittest.TestCase):
    def test_notebook_formulas_without_hardcoded_height(self):
        got = derived_metrics({
            "Weight": 80, "Body Fat": 20, "Muscle": 40,
            "Shoulder": 120, "Chest": 100, "Waist": 80, "Hips": 96,
        }, height_m=1.8)
        self.assertAlmostEqual(got["fat_mass_kg"], 16)
        self.assertAlmostEqual(got["lean_body_mass_kg"], 64)
        self.assertAlmostEqual(got["device_muscle_mass_kg"], 32)
        self.assertAlmostEqual(got["bmi_kg_m2"], 80 / 1.8**2)
        self.assertAlmostEqual(got["SWR"], 1.5)
        self.assertAlmostEqual(got["CWR"], 1.25)
        self.assertAlmostEqual(got["WHR_legacy_hips_over_waist"], 1.2)
        self.assertNotIn("bmi_kg_m2", derived_metrics({"Weight": 80}))

    def test_missing_zero_and_invalid_are_not_imputed(self):
        self.assertEqual(derived_metrics({"Waist": 0, "Shoulder": 100}), {})
        self.assertNotIn("fat_mass_kg", derived_metrics({"Weight": 80, "Body Fat": float("nan")}))
        self.assertNotIn("lean_body_mass_kg", derived_metrics({"Weight": 80, "Body Fat": 101}))
        with self.assertRaises(ValueError):
            derived_metrics({"Weight": 80}, height_m=0)


class TrendTests(unittest.TestCase):
    def test_monthly_and_trailing_no_interpolation(self):
        data = [
            rec("2026-01-01", 80, 4), rec("2026-01-01", 82, 5),
            rec("2026-01-03", 78, 6), rec("2026-02-01", 79, 7),
        ]
        monthly = monthly_observed_summary(data, "Weight")
        self.assertEqual([m["observed_days"] for m in monthly], [2, 1])
        self.assertAlmostEqual(monthly[0]["mean"], 79.5)
        trailing = rolling_observed_mean(data, "Weight", window_days=3, min_days=2)
        self.assertEqual(len(trailing), 1)
        self.assertEqual(trailing[0]["date"], "2026-01-03")
        self.assertAlmostEqual(trailing[0]["mean"], 79.5)
        self.assertEqual(trailing[0]["observed_days"], 2)

    def test_missing_days_not_fabricated(self):
        data = [rec("2026-01-01", 80), rec("2026-01-30", 70)]
        self.assertEqual(rolling_observed_mean(data, "Weight", window_days=7), [])
        self.assertEqual(len(monthly_observed_summary(data, "Weight")), 1)
