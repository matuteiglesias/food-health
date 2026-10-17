import json
from pathlib import Path
import stat
import tempfile
import unittest

from food_health.measurements.plot_data import (
    observed_frames, observation_counts, weekly_stats, ten_day_stats,
    two_month_changes, paired_frame, descriptive_fit,
)
from food_health.measurements.dashboard import generate_dashboard
from food_health.measurements.activity import load_legacy_activity


def synthetic_observations(days=30):
    from datetime import date, timedelta
    result = []
    start = date(2025, 10, 1)
    for i in range(days):
        when = start + timedelta(days=7 * i)
        # Trends with real missing-date intervals (seven days between points).
        result.append({
            "date":when.isoformat(),"source_row":4+i,
            "observed":{
                "Weight":75 + i/10, "Body Fat":15 + i/30,
                "Muscle":35 + i/40,"Waist":80+i/20,
                "Shoulder":112,"Chest":98,"Hips":90,
                "Arm":32 + i/30,"Flexed":35+i/30,
                "Belly":84+i/20,"Butt":94+i/30,
                "Butt#2":95+i/30,
            },
        })
    return result


class FrameTests(unittest.TestCase):
    def test_duplicate_day_averaged_only_in_projection(self):
        data = synthetic_observations(12)
        duplicated = dict(data[0])
        duplicated["source_row"] = 104
        duplicated["observed"] = {"Weight": 85}
        raw, daily = observed_frames(data + [duplicated])
        self.assertEqual(len(raw), 13)
        self.assertEqual(len(daily), 12)
        self.assertAlmostEqual(daily.iloc[0]["Weight"], 80)
        self.assertEqual(observation_counts(raw)["Weight"], 13)
        self.assertNotIn("bmi_kg_m2", daily.columns)
        fit=descriptive_fit(paired_frame(daily,"Weight","Waist"),x="Weight",y="Waist",degree=1)
        self.assertIsNotNone(fit)
        self.assertEqual(fit["count"],12)

    def test_sparse_without_interpolation(self):
        data=synthetic_observations(15)
        _,daily=observed_frames(data)
        weekly=weekly_stats(daily,"Weight")
        self.assertLessEqual(len(weekly),15)
        ten=ten_day_stats(daily,"Weight")
        self.assertTrue((ten["count"]<=2).all())
        changed=two_month_changes(daily,"Weight",bin_days=30)
        self.assertTrue(changed["delta_2bins"].notna().all())

    def test_insufficient_pairs_skip_fit(self):
        _,daily=observed_frames(synthetic_observations(4))
        pair=paired_frame(daily,"Weight","Waist",min_points=3)
        self.assertIsNone(descriptive_fit(pair,x="Weight",y="Waist"))
        self.assertIsNone(paired_frame(daily,"missing","Weight"))


class DashboardTests(unittest.TestCase):
    def test_local_html_gallery_with_real_pngs_and_private_permissions(self):
        records=synthetic_observations(12)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/".local"/"reports"/"atlas"
            report=generate_dashboard(records,output_dir=root)
            self.assertGreaterEqual(report["figures"],10)
            self.assertTrue(report["index"].is_file())
            self.assertEqual(stat.S_IMODE(root.stat().st_mode),0o700)
            self.assertEqual(stat.S_IMODE(report["index"].stat().st_mode),0o600)
            man=json.loads(report["manifest"].read_text())
            self.assertEqual(man["source_rows"],12)
            self.assertEqual(man["unique_dates"],12)
            self.assertEqual(man["activity_archive_rows"],0)
            self.assertEqual(len(list(root.glob("*.png"))),report["figures"])
            for p in root.glob("*.png"):
                self.assertGreater(p.stat().st_size,1000)
                self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
            html=report["index"].read_text()
            self.assertIn("Measurement Atlas",html)
            self.assertIn("not predictions",html)
            self.assertNotIn("Body Fat: 15",html)

    def test_invalid_empty_input_refused(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                generate_dashboard([],output_dir=Path(td)/"private")


class ActivityTests(unittest.TestCase):
    def test_historical_day_reader(self):
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/"activity.csv"
            file.write_text(
                ",Resistance,Cardio,Calistenia\n"
                "2023-01-01,1,,\n"
                "2023-01-02,,1,\n"
            )
            df=load_legacy_activity(file)
            self.assertEqual(len(df),2)
            self.assertEqual(int(df["Resistance"].sum()),1)
            self.assertEqual(int(df["Cardio"].sum()),1)
            self.assertEqual(int(df["Calistenia"].sum()),0)
