import csv
import math
from pathlib import Path
import tempfile
import unittest

from food_health.nutrition.composition import (
    NUTRIENTS_PER_100G, composition, load_catalog, load_legacy_plan,
    scale_quantities,
)


def synthetic_catalog(path):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        wr = csv.DictWriter(handle, fieldnames=["ID", "name", *NUTRIENTS_PER_100G])
        wr.writeheader()
        wr.writerow({"ID": "100", "name": "Test ingredient A",
                     **{"Calories": "200", "Carbohydrate (g)": "20",
                        "Fat (g)": "10", "Protein (g)": "12",
                        "Fiber (g)": "4", "Cholesterol (mg)": "0",
                        "Saturated Fats (g)": "1"}})
        wr.writerow({"ID": "200", "name": "Test ingredient B",
                     **{"Calories": "100", "Carbohydrate (g)": "5",
                        "Fat (g)": "4", "Protein (g)": "14",
                        "Fiber (g)": "3", "Cholesterol (mg)": "15",
                        "Saturated Fats (g)": "2"}})


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.catalog_csv = Path(self.tmp.name) / "catalog.csv"
        synthetic_catalog(self.catalog_csv)
        self.catalog = load_catalog(self.catalog_csv)

    def tearDown(self):
        self.tmp.cleanup()

    def test_per100g_three_day_plan_and_period_scaling(self):
        result = composition(
            self.catalog, [
                {"food_id": "100", "grams": 150},
                {"food_id": "200", "grams": 50},
                {"food_id": "100", "grams": 50},
            ], period_days=3,
        )
        self.assertEqual(result["total_grams"], 250)
        self.assertAlmostEqual(result["totals"]["Calories"], 450)
        self.assertAlmostEqual(result["per_day"]["Calories"], 150)
        self.assertAlmostEqual(result["totals"]["Protein (g)"], 31)
        self.assertAlmostEqual(result["totals"]["Cholesterol (mg)"], 7.5)
        self.assertEqual(result["grams_by_id"], {"100": 200, "200": 50})
        weekly = scale_quantities(result["grams_by_id"], source_days=3, target_days=7)
        self.assertAlmostEqual(weekly["100"]["kg"], 200 * 7 / 3 / 1000)

    def test_inactive_missing_id_ignored_but_active_missing_id_fails(self):
        p = Path(self.tmp.name) / "plan.csv"
        p.write_text("ID,cant\n,0\n100,120\n")
        self.assertEqual(load_legacy_plan(p), [{"food_id": "100", "grams": 120}])
        p.write_text("ID,cant\n,120\n")
        with self.assertRaisesRegex(ValueError, "without food ID"):
            load_legacy_plan(p)

    def test_malformed_and_unmapped_rejected(self):
        with self.assertRaisesRegex(ValueError, "unmapped"):
            composition(self.catalog, [{"food_id": "404", "grams": 100}])
        with self.assertRaises(ValueError):
            composition(self.catalog, [{"food_id": "100", "grams": -1}])
        with self.assertRaises(ValueError):
            composition(self.catalog, [{"food_id": "100", "grams": float("nan")}])
        with self.assertRaises(ValueError):
            composition(self.catalog, [], period_days=0)
        with self.assertRaises(ValueError):
            scale_quantities({"x": 100}, source_days=0, target_days=7)

    def test_duplicate_catalog_id_rejected(self):
        with open(self.catalog_csv, "a") as f:
            f.write("100,duplicate,200,20,10,12,4,0,1\n")
        with self.assertRaisesRegex(ValueError, "duplicate food ID"):
            load_catalog(self.catalog_csv)

    def test_missing_catalog_data_rejected(self):
        p = Path(self.tmp.name) / "malformed.csv"
        p.write_text("ID,name,Calories\n100,a,NaN\n")
        with self.assertRaisesRegex(ValueError, "missing catalog headers"):
            load_catalog(p)

    def test_null_nutrient_is_missing_not_zero(self):
        p = Path(self.tmp.name) / "missing.csv"
        synthetic_catalog(p)
        text = p.read_text()
        # Precisely one synthetic nutrient is unknown in ingredient B.
        text = text.replace("100,5,4,14,3,15,2", "100,5,4,14,NULL,15,2")
        assert "NULL" in text
        p.write_text(text)
        food = load_catalog(p)
        self.assertIsNone(food["200"]["per_100g"]["Fiber (g)"])
        macros = ("Calories", "Carbohydrate (g)", "Fat (g)", "Protein (g)")
        partial = composition(food, [{"food_id": "200", "grams": 100}], fields=macros)
        self.assertAlmostEqual(partial["totals"]["Calories"], 100)
        with self.assertRaisesRegex(ValueError, "missing nutrient value"):
            composition(food, [{"food_id": "200", "grams": 100}])

    def test_catalog_not_mutated(self):
        before = self.catalog["100"]["per_100g"].copy()
        composition(self.catalog, [{"food_id": "100", "grams": 100}])
        self.assertEqual(before, self.catalog["100"]["per_100g"])


if __name__ == "__main__":
    unittest.main()
