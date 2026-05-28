import unittest

from app.market_intelligence.notes_parser_flags import (
    detect_dedicated_lane,
    detect_double_brokering_language,
    detect_mc_must_match,
)


class TestNotesParserFlags(unittest.TestCase):
    def test_detect_dedicated_lane(self):
        self.assertTrue(detect_dedicated_lane("dedicated lane"))
        self.assertTrue(detect_dedicated_lane("need solid drivers"))
        self.assertTrue(detect_dedicated_lane("need solid driver"))
        self.assertTrue(detect_dedicated_lane("consistent lane"))
        self.assertFalse(detect_dedicated_lane("regular one-time load"))

    def test_detect_double_brokering_language(self):
        self.assertTrue(detect_double_brokering_language("no double brokering"))
        self.assertTrue(detect_double_brokering_language("no double broker"))
        self.assertTrue(detect_double_brokering_language("double brokering"))
        self.assertFalse(detect_double_brokering_language("direct customer load"))

    def test_detect_mc_must_match(self):
        self.assertTrue(detect_mc_must_match("mc must match"))
        self.assertTrue(detect_mc_must_match("name must match"))
        self.assertTrue(detect_mc_must_match("carrier name must match"))
        self.assertFalse(detect_mc_must_match("normal carrier setup"))


if __name__ == "__main__":
    unittest.main()
