import unittest

from food_health.nutrition.substitutes import nearest_foods


def fixture():
    def food(name, cal, carbs, fat, protein, group="grain"):
        return {"name": name, "group": group, "per_100g": {
            "Calories": cal, "Carbohydrate (g)": carbs,
            "Fat (g)": fat, "Protein (g)": protein,
        }}
    return {
        "1": food("synthetic source", 100, 20, 2, 5),
        "2": food("synthetic identical nutrition", 100, 20, 2, 5),
        "3": food("synthetic near", 105, 21, 2, 4),
        "4": food("synthetic far", 400, 60, 30, 20, "meat"),
        "5": food("synthetic missing", 100, 20, None, 5),
    }


class NearestFoodsTests(unittest.TestCase):
    def test_same_nutrients_different_id_are_nearest(self):
        results=nearest_foods(fixture(),"1",limit=3)
        self.assertEqual(results[0]["food_id"], "2")
        self.assertEqual(results[0]["distance"],0.0)
        self.assertEqual(results[1]["food_id"], "3")
        self.assertEqual({r["food_id"] for r in results},{"2","3","4"})
        self.assertNotIn("1",[r["food_id"] for r in results])
        self.assertNotIn("5",[r["food_id"] for r in results])

    def test_filter_group_and_exclude_by_id(self):
        results=nearest_foods(fixture(),"1",same_group=True,exclude_ids=frozenset({"2"}))
        self.assertEqual([r["food_id"] for r in results],["3"])

    def test_zero_variance_metric_valid(self):
        data={
            str(n): {"name":str(n),"per_100g":{"Calories":100,"Protein (g)":20}}
            for n in range(1,5)
        }
        result=nearest_foods(data,"1",features=("Calories","Protein (g)"))
        self.assertEqual([r["food_id"] for r in result],["2","3","4"])
        self.assertTrue(all(r["distance"]==0 for r in result))

    def test_missing_source_feature_rejected(self):
        data=fixture();data["1"]["per_100g"]["Protein (g)"]=None
        with self.assertRaisesRegex(ValueError,"Source missing"):
            nearest_foods(data,"1")

    def test_invalid_controls(self):
        kwargs={"catalog":fixture(),"source_id":"1"}
        for val in [0,-1,1.0,True]:
            with self.subTest(limit=val):
                with self.assertRaises(ValueError):
                    nearest_foods(**kwargs,limit=val)
        with self.assertRaises(ValueError):
            nearest_foods(**kwargs,features=("Calories","Calories"))
        with self.assertRaises(ValueError):
            nearest_foods(**kwargs,feature_weights={"Calories":-1})
        with self.assertRaises(ValueError):
            nearest_foods(**kwargs,max_distance=float("nan"))
        with self.assertRaises(KeyError):
            nearest_foods(fixture(),"missing")
        data=fixture(); data["1"]["group"]=""
        with self.assertRaisesRegex(ValueError,"group missing"):
            nearest_foods(data,"1",same_group=True)

    def test_distance_threshold_does_not_recommend_unrelated(self):
        out=nearest_foods(fixture(),"1",max_distance=0)
        self.assertEqual([r["food_id"] for r in out],["2"])


if __name__=="__main__":
    unittest.main()
