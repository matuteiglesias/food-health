import copy
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

from food_health.nutrition.composition import composition
from food_health.nutrition.google_sheets import (
    FOOD_CATALOG_RANGE, FOOD_PLAN_RANGE, STOCK_RANGE, READ_ONLY_SCOPE,
    fetch_food_and_stock, parse_catalog, parse_curated_plan, parse_stock,
)
from food_health.nutrition.private_snapshot import (
    read_private_snapshot, private_summary, write_private_snapshot
)

PLAN=[
    ["index", "label_en", "label_es", "cant 6 dias", "cant 12 (15) dias",
     "cant 24 dias (mes)", "", "cant 3d", "ID"],
    [0, "food A", "", 400, 800, 1600, "", 200, 100],
    [1, "food B", "", 300, 600, 1200, "", 150, 200],
    [2, "inactive", "", 0, 0, 0, "", 0, ""],
    ["", "TOTAL", "", "", "", "", "", "summary", ""],
]
CATALOG=[
    ["ID", "name", "Food Group", "Calories", "Fat (g)", "Protein (g)",
     "Carbohydrate (g)", "Sugars (g)", "Fiber (g)",
     "Cholesterol (mg)", "Saturated Fats (g)"],
    [100, "synthetic A", "group", 200, 10, 20, 25, 5, "NULL", 0, 3],
    [200, "synthetic B", "group", 100, 5, 10, 10, 3, 2, 0, 1],
]
STOCK=[
    ["item", "storage", "urgency", "notes", "qty_g 10/01"],
    ["synthetic item A", "freezer", "medium", "", 750],
    ["synthetic item B", "pantry", "low", "unknown", "TBD"],
]


class ReaderTests(unittest.TestCase):
    def test_curated_uses_unscaled_three_day_grams(self):
        plan=parse_curated_plan(PLAN)
        self.assertEqual(plan["period_days"], 3)
        self.assertEqual(plan["items"], [
            {"food_id": "100", "grams": 200.0, "source_row": 2},
            {"food_id": "200", "grams": 150.0, "source_row": 3},
        ])

    def test_catalog_preserves_null_and_composition_works_for_subset(self):
        catalog=parse_catalog(CATALOG)
        self.assertIsNone(catalog["100"]["per_100g"]["Fiber (g)"])
        protein_only=composition(
            catalog, parse_curated_plan(PLAN)["items"], period_days=3,
            fields=("Calories", "Protein (g)"),
        )
        self.assertAlmostEqual(protein_only["totals"]["Calories"], 550)
        with self.assertRaisesRegex(ValueError, "missing nutrient"):
            composition(catalog, parse_curated_plan(PLAN)["items"], period_days=3)

    def test_stock_date_unresolved_and_unknown_not_zero(self):
        result=parse_stock(STOCK)
        self.assertEqual(result["quantity_heading"], "qty_g 10/01")
        self.assertTrue(result["snapshot_date_unresolved"])
        self.assertIsNone(result["items"][1]["quantity_g"])
        self.assertEqual(result["items"][1]["quantity_raw"], "TBD")

    def test_missing_food_id_and_duplicate_catalog_rejected(self):
        bad=copy.deepcopy(PLAN)
        bad[1][8]=""
        with self.assertRaisesRegex(ValueError,"no food ID"):
            parse_curated_plan(bad)
        bad_catalog=copy.deepcopy(CATALOG)
        bad_catalog[2][0]=100
        with self.assertRaisesRegex(ValueError,"Duplicate food ID"):
            parse_catalog(bad_catalog)

    def test_no_sheet_writes_and_fail_closed_partial_read(self):
        responses={
            FOOD_PLAN_RANGE: PLAN,
            FOOD_CATALOG_RANGE: CATALOG,
            STOCK_RANGE: STOCK,
        }
        service=Mock()
        def call(**kwargs):
            area=kwargs["range"]
            response=Mock()
            response.execute.return_value={"values":responses[area]}
            return response
        service.spreadsheets.return_value.values.return_value.get.side_effect=call
        payload=fetch_food_and_stock(food_sheet_id="a",stock_sheet_id="b",service=service)
        self.assertEqual(len(payload["plan"]["items"]),2)
        self.assertEqual(len(payload["catalog"]),2)
        self.assertEqual(len(payload["stock"]["items"]),2)
        service.spreadsheets.return_value.values.return_value.update.assert_not_called()
        self.assertIn("readonly",READ_ONLY_SCOPE)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/".local"/"food-stock.json"
            self.assertTrue(write_private_snapshot(path,payload))
            self.assertFalse(write_private_snapshot(path,payload))
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
            self.assertEqual(read_private_snapshot(path),payload)
            self.assertFalse(private_summary(payload)["stock_is_current"])

    def test_suspicious_truncation_rejected(self):
        payload={
            "schema_version":1,
            "plan":{"items":[{"id":i} for i in range(30)]},
            "catalog":{str(i):{} for i in range(50)},
            "stock":{"items":[{"id":i} for i in range(50)],"quantity_heading":"qty_g 10/01"},
        }
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/".local"/"snapshot.json"
            write_private_snapshot(p,payload)
            new=copy.deepcopy(payload)
            new["catalog"]={str(i):{} for i in range(30)}
            with self.assertRaisesRegex(ValueError,"truncation"):
                write_private_snapshot(p,new)
            self.assertEqual(read_private_snapshot(p),payload)


if __name__=="__main__":
    unittest.main()
