"""Quick regression checks for the optional enriched chart mode."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from food_health.cli import main


class EnrichedDashboardCliTests(unittest.TestCase):
    def test_flag_uses_complete_values_and_keeps_original_atlas_separate(self):
        original=[{"date":"2026-10-16","source_row":4,"observed":{"Weight":80.0}}]
        enriched=[{
            "date":"2026-10-16","source_row":4,
            "observed":{"Weight":80.0},
            "estimated":{"Waist":{"value":83.0}},
            "values":{"Weight":80.0,"Waist":83.0},
            "provenance":{"Weight":"observed","Waist":"estimated_not_observed"},
        }]
        with tempfile.TemporaryDirectory() as temp:
            base=["--root",temp,"--sheet-id","synthetic"]
            with (
                patch("food_health.measurements.snapshot.load_snapshot",return_value=original),
                patch("food_health.measurements.enriched_view.load_enriched_view",return_value=enriched),
                patch("food_health.measurements.dashboard.generate_dashboard",return_value={
                    "index":Path(temp)/".local"/"fake-index.html","source_rows":1,
                    "figures":4,"activity_rows":0,
                }) as render,
            ):
                self.assertEqual(main(["measurements-dashboard",*base,"--include-estimates"]),0)
                args=render.call_args
                self.assertEqual(args.args[0][0]["observed"],{"Weight":80.0,"Waist":83.0})
                self.assertEqual(args.kwargs["data_mode"],"enriched")
                self.assertEqual(args.kwargs["estimated_value_count"],1)
                self.assertEqual(args.kwargs["output_dir"].name,"measurement-atlas-enriched")
                self.assertEqual(main(["measurements-dashboard",*base]),0)
                args=render.call_args
                self.assertEqual(args.args[0],original)
                self.assertEqual(args.kwargs["data_mode"],"observed")
                self.assertEqual(args.kwargs["estimated_value_count"],0)
                self.assertEqual(args.kwargs["output_dir"].name,"measurement-atlas")

    def test_public_output_path_rejected_before_private_snapshot_is_read(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("food_health.measurements.enriched_view.load_enriched_view") as read:
                with self.assertRaisesRegex(ValueError,"inside <root>/.local"):
                    main(["measurements-dashboard","--root",temp,"--sheet-id","synthetic",
                          "--include-estimates","--output-dir",str(Path(temp)/"public")])
                read.assert_not_called()


if __name__=="__main__":
    unittest.main()
