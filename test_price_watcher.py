import unittest

from price_watcher import parse_price, valid_exact_model


class TestPriceWatcher(unittest.TestCase):
    def test_accepts_base_model(self):
        self.assertTrue(
            valid_exact_model("TwoTrees TTC450 Ultra CNC Router")
        )

    def test_rejects_pro_model(self):
        self.assertFalse(
            valid_exact_model("TwoTrees TTC450 Pro CNC Router")
        )

    def test_rejects_laser_bundle(self):
        self.assertFalse(
            valid_exact_model("TwoTrees TTC450 Ultra with Laser")
        )

    def test_rejects_fourth_axis_bundle(self):
        self.assertFalse(
            valid_exact_model("TwoTrees TTC450 Ultra 4th Axis Bundle")
        )

    def test_parses_german_price(self):
        self.assertEqual(parse_price("599,00 €"), 599.0)

    def test_parses_thousands_separator(self):
        self.assertEqual(parse_price("1.099,00 EUR"), 1099.0)

    def test_parses_plain_decimal(self):
        self.assertEqual(parse_price("499.00"), 499.0)

    def test_rejects_missing_price(self):
        self.assertIsNone(parse_price(None))


if __name__ == "__main__":
    unittest.main()
