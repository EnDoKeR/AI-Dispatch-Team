import unittest


class TestLoadIntakeParserImport(unittest.TestCase):
    def test_parser_imports_load_model_for_ratecon_flow(self):
        from app.load_intake import parser

        load = parser.Load(
            pickup="Dallas, TX",
            delivery="Houston, TX",
            rate="1200",
            loaded_miles=240,
            booked_at="01/01/2026 10:00 AM",
        )

        self.assertEqual(load.pickup, "Dallas, TX")
        self.assertEqual(load.delivery, "Houston, TX")
        self.assertEqual(load.rate, 1200)
        self.assertEqual(load.loaded_miles, 240)
        self.assertEqual(load.extra["booked_at"], "01/01/2026 10:00 AM")


if __name__ == "__main__":
    unittest.main()
