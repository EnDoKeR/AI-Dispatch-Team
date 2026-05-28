import unittest

from app.market_intelligence.notes_parser_securement import (
    detect_number_of_straps,
    detect_straps_required,
    detect_tarp_required,
    detect_tarp_size,
)


class TestNotesParserSecurement(unittest.TestCase):
    def test_detect_tarp_required_detects_clear_tarp_requirements(self):
        self.assertTrue(detect_tarp_required("8 ft tarps required"))
        self.assertTrue(detect_tarp_required("need tarps"))
        self.assertTrue(detect_tarp_required("6FT"))

    def test_detect_tarp_required_respects_no_tarp_language(self):
        self.assertFalse(detect_tarp_required("no tarps required"))
        self.assertFalse(detect_tarp_required("no tarping"))
        self.assertFalse(detect_tarp_required("tarps not required"))
        self.assertFalse(detect_tarp_required("tarp not required"))

    def test_detect_tarp_required_does_not_trigger_on_bare_tarps_word(self):
        self.assertFalse(detect_tarp_required("tarps"))
        self.assertFalse(detect_tarp_required("tarp"))

    def test_detect_tarp_required_detects_only_supported_standalone_sizes(self):
        self.assertTrue(detect_tarp_required("4FT"))
        self.assertTrue(detect_tarp_required("6FT"))
        self.assertTrue(detect_tarp_required("8FT"))

        self.assertFalse(detect_tarp_required("5FT"))
        self.assertFalse(detect_tarp_required("7FT"))
        self.assertFalse(detect_tarp_required("10FT"))

    def test_detect_tarp_size_detects_supported_sizes(self):
        self.assertEqual(detect_tarp_size("need 8 ft tarps"), "8 ft")
        self.assertEqual(detect_tarp_size("6ft tarps required"), "6 ft")
        self.assertEqual(detect_tarp_size("clean load"), "")

    def test_detect_straps_required_and_count(self):
        self.assertTrue(detect_straps_required("strap and go"))
        self.assertTrue(detect_straps_required("need 6 straps"))
        self.assertEqual(detect_number_of_straps("need 6 straps"), 6)
        self.assertEqual(detect_number_of_straps("strap and go"), 0)


if __name__ == "__main__":
    unittest.main()
