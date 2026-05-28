import unittest

from app.market_intelligence.notes_parser_weight_stops import (
    detect_stops_from_text,
    detect_weight_from_text,
    detect_weight_unknown,
)


class TestNotesParserWeightStops(unittest.TestCase):
    def test_detect_weight_unknown_for_missing_or_placeholder_weight(self):
        self.assertTrue(detect_weight_unknown("weight TBD"))
        self.assertTrue(detect_weight_unknown("call for weight"))
        self.assertTrue(detect_weight_unknown("confirm weight"))
        self.assertTrue(detect_weight_unknown("weight 1 lb"))
        self.assertTrue(detect_weight_unknown("posted weight 1"))
        self.assertTrue(detect_weight_unknown("clean notes", posted_weight=1))

    def test_detect_weight_from_text_detects_common_weight_formats(self):
        self.assertEqual(detect_weight_from_text("weight 45k"), 45000)
        self.assertEqual(detect_weight_from_text("weight 45 k lbs"), 45000)
        self.assertEqual(detect_weight_from_text("weight 45,000 lbs"), 45000)
        self.assertEqual(detect_weight_from_text("clean notes"), 0)

    def test_detect_stops_from_text_detects_dat_style_stops(self):
        self.assertEqual(detect_stops_from_text("1P/1D"), 2)
        self.assertEqual(detect_stops_from_text("2P/1D"), 3)
        self.assertEqual(detect_stops_from_text("1 pickup 2 drops"), 3)

    def test_detect_multiple_loads_available_is_not_stops(self):
        self.assertEqual(detect_stops_from_text("multiple loads available"), 0)

    def test_detect_stops_from_text_detects_multistop_language(self):
        self.assertGreaterEqual(detect_stops_from_text("multistop load"), 2)
        self.assertGreaterEqual(detect_stops_from_text("multi stop load"), 2)
        self.assertGreaterEqual(detect_stops_from_text("multiple drops"), 2)
        self.assertGreaterEqual(detect_stops_from_text("multiple pickups"), 2)


if __name__ == "__main__":
    unittest.main()
