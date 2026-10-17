import tempfile
import unittest
from pathlib import Path
from food_health.cli import main


class CliTests(unittest.TestCase):
    def test_doctor_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main(["doctor", "--root", tmp]), 0)
            self.assertFalse((Path(tmp) / "archive").exists())
