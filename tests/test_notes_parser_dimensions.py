import unittest

from app.market_intelligence.notes_parser_dimensions import (
    detect_dimensions,
    detect_od,
    detect_overweight,
)


class TestNotesParserDimensions(unittest.TestCase):
    def test_detect_od_detects_keywords_and_width(self):
        self.assertTrue(detect_od("permit load"))
        self.assertTrue(detect_od("wide load"))
        self.assertTrue(detect_od("109 inches wide"))
        self.assertTrue(detect_od("legal dimensions 58L x 109W x 7H"))

    def test_detect_od_does_not_detect_plain_od_inside_words(self):
        self.assertFalse(detect_od("good legal load"))
        self.assertFalse(detect_od("commodity is wood products"))

    def test_detect_od_detects_dimension_width_over_legal(self):
        self.assertTrue(detect_od("58L x 111W x 7H"))
        self.assertTrue(detect_od("58 x 111 x 7"))
        self.assertTrue(detect_od("58 long x 111 wide"))

    def test_detect_od_detects_9_ft_or_more_width(self):
        self.assertTrue(detect_od("9 ft wide"))
        self.assertTrue(detect_od("10' wide"))
        self.assertFalse(detect_od("8 ft wide"))

    def test_detect_dimensions_extracts_lwh(self):
        result = detect_dimensions("58L x 111W x 7H")

        self.assertEqual(result["length"], "58")
        self.assertEqual(result["width"], "111")
        self.assertEqual(result["height"], "7")
        self.assertEqual(result["raw"], "58l x 111w x 7h")

    def test_detect_dimensions_returns_empty_result_when_missing(self):
        result = detect_dimensions("legal flatbed load")

        self.assertEqual(
            result,
            {
                "length": "",
                "width": "",
                "height": "",
                "raw": "",
            },
        )

    def test_detect_overweight_detects_heavy_keywords(self):
        self.assertTrue(detect_overweight("overweight"))
        self.assertTrue(detect_overweight("over weight"))
        self.assertTrue(detect_overweight("heavy haul"))
        self.assertFalse(detect_overweight("normal legal load"))


if __name__ == "__main__":
    unittest.main()
