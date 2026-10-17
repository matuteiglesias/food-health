import copy
import unittest

from food_health.nutrition.optimize import optimize_quantities


def fixture():
    return {
        "A": {"name": "synthetic A", "per_100g": {"Calories": 100, "Protein (g)": 10}},
        "B": {"name": "synthetic B", "per_100g": {"Calories": 200, "Protein (g)": 0}},
    }


class OptimizerTests(unittest.TestCase):
    def test_feasible_solution_and_no_mutation(self):
        catalog = fixture()
        plan = [{"food_id": "A", "grams": 50}, {"food_id": "B", "grams": 50}]
        before = copy.deepcopy(plan)
        targets = {"Calories": 300, "Protein (g)": 10}
        result = optimize_quantities(
            catalog, plan, targets_per_day=targets,
            variable_ids=["A", "B"], period_days=1,
        )
        self.assertTrue(result.solver_success, result.solver_message)
        self.assertTrue(result.targets_met)
        self.assertAlmostEqual(result.grams_by_id["A"], 100, places=3)
        self.assertAlmostEqual(result.grams_by_id["B"], 100, places=3)
        self.assertLess(result.objective_after, result.objective_before)
        self.assertEqual(plan, before)

    def test_frozen_other_ingredient(self):
        result = optimize_quantities(
            fixture(), [{"food_id": "A", "grams": 50}, {"food_id": "B", "grams": 50}],
            targets_per_day={"Protein (g)": 10}, variable_ids=["A"], period_days=1,
        )
        self.assertTrue(result.targets_met)
        self.assertEqual(result.grams_by_id["B"], 50)
        self.assertAlmostEqual(result.grams_by_id["A"], 100, places=3)

    def test_infeasible_bounds_are_not_false_success(self):
        result = optimize_quantities(
            fixture(), [{"food_id": "A", "grams": 50}, {"food_id": "B", "grams": 50}],
            targets_per_day={"Calories": 300, "Protein (g)": 10}, variable_ids=["A", "B"],
            bounds_grams={"A": (0, 60), "B": (0, 60)}, period_days=1,
        )
        self.assertFalse(result.targets_met)
        self.assertGreater(result.max_relative_error, 0.02)
        self.assertLessEqual(result.grams_by_id["A"], 60)
        self.assertLessEqual(result.grams_by_id["B"], 60)

    def test_invalid_inputs_rejected(self):
        kwargs = {"catalog": fixture(), "plan": [{"food_id": "A", "grams": 50}],
                  "targets_per_day": {"Calories": 100}, "variable_ids": ["A"], "period_days": 1}
        for key, value in [
            ("targets_per_day", {}),
            ("targets_per_day", {"Calories": 0}),
            ("targets_per_day", {"Calories": float("nan")}),
            ("variable_ids", []),
            ("variable_ids", ["A", "A"]),
            ("variable_ids", ["none"]),
            ("bounds_grams", {"A": (-1, 30)}),
            ("bounds_grams", {"A": (40, 30)}),
            ("bounds_grams", {"B": (0, 20)}),
        ]:
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    optimize_quantities(**{**kwargs, key: value})

    def test_identity_targets_do_not_require_change(self):
        result = optimize_quantities(
            fixture(), [{"food_id": "A", "grams": 100}, {"food_id": "B", "grams": 100}],
            targets_per_day={"Calories": 300, "Protein (g)": 10},
            variable_ids=["A", "B"], period_days=1,
        )
        self.assertTrue(result.targets_met)
        self.assertAlmostEqual(result.objective_after, 0.0, places=10)
