import unittest
from unittest.mock import Mock, patch

from food_health.measurements.google_sheets import (
    MEDIDAS_RANGE, READ_ONLY_SCOPE,
    fetch_measurements_grid, fetch_observed_measurements,
)


class AdapterTests(unittest.TestCase):
    def fake_service(self, response):
        service = Mock()
        service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = response
        return service

    def test_readonly_request_and_observations(self):
        grid = [
            [], [],
            ["", "Weight", "Butt", "Butt", "GYM"],
            ["10/16/2026", 78.5, "", 96, 1],
            ["10/17/2026", "", "", "", 1],
        ]
        service = self.fake_service({"values": grid})
        result = fetch_observed_measurements("synthetic-id", service=service)
        self.assertEqual(result, [{
            "date": "2026-10-16",
            "source_row": 4,
            "observed": {"Weight": 78.5, "Butt#2": 96.0},
        }])
        _, kwargs = service.spreadsheets.return_value.values.return_value.get.call_args
        self.assertEqual(kwargs["spreadsheetId"], "synthetic-id")
        self.assertEqual(kwargs["range"], MEDIDAS_RANGE)
        self.assertEqual(kwargs["valueRenderOption"], "UNFORMATTED_VALUE")
        self.assertEqual(kwargs["dateTimeRenderOption"], "FORMATTED_STRING")
        self.assertIn("readonly", READ_ONLY_SCOPE)
        service.spreadsheets.return_value.values.return_value.update.assert_not_called()

    def test_no_sheet_id_no_service_call(self):
        service = self.fake_service({})
        with patch.dict("os.environ", {"FOOD_HEALTH_MEASUREMENTS_SHEET_ID": ""}):
            with self.assertRaises(ValueError):
                fetch_measurements_grid(service=service)
        service.spreadsheets.assert_not_called()

    def test_missing_data_is_not_silently_accepted(self):
        service = self.fake_service({})
        with self.assertRaises(ValueError):
            fetch_observed_measurements("synthetic-id", service=service)
