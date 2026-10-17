import csv
from pathlib import Path
import tempfile
import unittest

from food_health.measurements.analysis_tables import (
    period_comparisons, yearly_summary, pairwise_correlations,
)
from food_health.measurements.goals import load_goal_values, compare_goals
from food_health.measurements.plot_data import observed_frames


def records():
    from datetime import date,timedelta
    first=date(2025,1,1)
    return [{
        "date":(first+timedelta(days=i*7)).isoformat(),
        "source_row":i+4,
        "observed":{"Weight":75+i*.2, "Waist":82+i*.1, "Body Fat":20+i*.1},
    } for i in range(85)]


class AnalysisTableTests(unittest.TestCase):
    def test_comparisons_are_window_scoped_observed_days_only(self):
        _,daily=observed_frames(records())
        recent=period_comparisons(daily,["Weight","Waist"],window_days=90,min_days=3)
        self.assertEqual(len(recent),2)
        for item in recent:
            self.assertGreater(item["current_observed_days"],0)
            self.assertGreater(item["previous_observed_days"],0)
            self.assertGreater(item["change"],0)
        yearly=yearly_summary(daily,["Weight"])
        self.assertGreaterEqual(len(yearly),2)
        self.assertEqual(yearly[0]["year"],2025)
        pearson=pairwise_correlations(daily,["Weight","Waist","Body Fat"])
        self.assertEqual(len(pearson),3)
        self.assertTrue(all(r["paired_days"]==85 for r in pearson))

    def test_empty_or_sparse_period_omitted(self):
        _,daily=observed_frames(records()[:4])
        self.assertEqual(period_comparisons(daily,["Weight"],min_days=3),[])
        self.assertEqual(pairwise_correlations(daily,["Weight","Waist"],min_points=8),[])


class LegacyGoalsTests(unittest.TestCase):
    def test_explicit_historical_targets_only(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"legacy_goals.csv"
            path.write_text(",Weight,Waist,Calories\n2023-01-01,80,84,9999\n",encoding="utf-8")
            source=load_goal_values(path)
            self.assertEqual(source["source_label"],"2023-01-01")
            self.assertEqual(source["goals"],{"Weight":80,"Waist":84})
            _,daily=observed_frames(records())
            values=compare_goals(daily,source["goals"])
            self.assertEqual(len(values),2)
            self.assertTrue(all(v["observed_days"]==10 for v in values))
            for v in values:
                self.assertAlmostEqual(v["forty_pct_step"],
                    v["recent_mean"]+.4*(v["goal"]-v["recent_mean"]))
    def test_rejects_missing_or_multiple_target_rows(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"goals.csv"
            f.write_text(",Waist\n2024-01-01,84\n2025-01-01,85\n")
            with self.assertRaisesRegex(ValueError,"exactly one"):
                load_goal_values(f)
            f.write_text(",Waist\n2024-01-01,NaN\n")
            with self.assertRaisesRegex(ValueError,"Invalid historical"):
                load_goal_values(f)
