import io
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from food_health.cli import main
from food_health.nutrition.private_snapshot import read_private_snapshot


def synthetic_snapshot():
    names = (
        "Calories", "Carbohydrate (g)", "Fat (g)", "Protein (g)",
        "Fiber (g)", "Cholesterol (mg)", "Saturated Fats (g)"
    )
    return {
        "schema_version": 1,
        "plan": {"source_tab": "CURATED_PLAN", "period_days": 3,
                 "items": [{"food_id": "1", "grams": 200, "source_row": 2}]},
        "catalog": {
            "1": {"name": "SYNTHETIC", "source_row": 2,
                  "per_100g": {name: 10.0 for name in names}}
        },
        "stock": {"source_tab": "STOCK", "quantity_heading": "qty_g 10/01",
                  "snapshot_date_unresolved": True,
                  "items": [{"item": "SYNTHETIC", "quantity_g": 100, "source_row": 2}]},
    }


class FoodCliTests(unittest.TestCase):
    def test_sync_twice_then_summary_offline(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            data=synthetic_snapshot()
            with patch("food_health.nutrition.google_sheets.fetch_food_and_stock", return_value=data):
                first=io.StringIO()
                second=io.StringIO()
                with redirect_stdout(first):
                    self.assertEqual(main(["food-sync", "--root", td]), 0)
                with redirect_stdout(second):
                    self.assertEqual(main(["food-sync", "--root", td]), 0)
            self.assertIn("changed=true", first.getvalue())
            self.assertIn("changed=false", second.getvalue())
            output=io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["food-summary", "--root", td]), 0)
            self.assertIn("stock_currentness=unverified", output.getvalue())
            self.assertEqual(read_private_snapshot(root/".local"/"food-stock.json"),data)

    def test_failed_read_does_not_overwrite_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            before=synthetic_snapshot()
            with patch("food_health.nutrition.google_sheets.fetch_food_and_stock", return_value=before):
                with redirect_stdout(io.StringIO()):
                    main(["food-sync", "--root", td])
            with patch("food_health.nutrition.google_sheets.fetch_food_and_stock", side_effect=OSError("offline")):
                with self.assertRaises(OSError):
                    main(["food-sync", "--root", td])
            self.assertEqual(read_private_snapshot(Path(td)/".local"/"food-stock.json"),before)
