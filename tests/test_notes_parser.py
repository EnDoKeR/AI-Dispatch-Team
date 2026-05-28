import unittest

from app.market_intelligence.notes_parser import (
    clean_text,
    detect_actual_pickup_city,
    detect_cash_or_zelle,
    detect_contact_override,
    detect_multiple_loads_available,
    detect_number_of_straps,
    detect_od,
    detect_stops_from_text,
    detect_straps_required,
    detect_tarp_required,
    detect_tarp_size,
    detect_weight_unknown,
    normalize_email,
    normalize_phone,
    parse_notes,
)


class TestNotesParserBasics(unittest.TestCase):
    def test_clean_text_normalizes_spacing_and_symbols(self):
        self.assertEqual(
            clean_text("  NEED_TARPS; strap|and go  "),
            "need tarps strap and go",
        )

    def test_normalize_email_fixes_common_dat_email_typos(self):
        self.assertEqual(
            normalize_email("Info@National-TransportServices`com"),
            "info@national-transportservices.com",
        )

    def test_normalize_phone_trims_and_collapses_spaces(self):
        self.assertEqual(
            normalize_phone("  555   111   2222  "),
            "555 111 2222",
        )

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

    def test_detect_od_detects_keywords_and_width(self):
        self.assertTrue(detect_od("permit load"))
        self.assertTrue(detect_od("wide load"))
        self.assertTrue(detect_od("109 inches wide"))
        self.assertTrue(detect_od("legal dimensions 58L x 109W x 7H"))

    def test_detect_od_does_not_detect_plain_od_inside_words(self):
        self.assertFalse(detect_od("good legal load"))
        self.assertFalse(detect_od("commodity is wood products"))

    def test_detect_cash_or_zelle_blocks_cash_payment_language(self):
        self.assertTrue(detect_cash_or_zelle("cash or zelle"))
        self.assertTrue(detect_cash_or_zelle("cash on delivery"))
        self.assertTrue(detect_cash_or_zelle("zelle"))
        self.assertTrue(detect_cash_or_zelle("cashapp"))

    def test_detect_weight_unknown_for_missing_or_placeholder_weight(self):
        self.assertTrue(detect_weight_unknown("weight TBD"))
        self.assertTrue(detect_weight_unknown("call for weight"))
        self.assertTrue(detect_weight_unknown("confirm weight"))
        self.assertTrue(detect_weight_unknown("clean notes", posted_weight=1))

    def test_detect_multiple_loads_available_is_not_stops(self):
        self.assertTrue(detect_multiple_loads_available("multiple loads available"))
        self.assertEqual(detect_stops_from_text("multiple loads available"), 0)

    def test_detect_stops_from_text_detects_multistop_language(self):
        self.assertGreaterEqual(detect_stops_from_text("multistop load"), 2)

    def test_detect_actual_pickup_city_detects_strict_city_state(self):
        self.assertEqual(
            detect_actual_pickup_city("actual pickup in Dallas, TX"),
            "Dallas, TX",
        )
        self.assertEqual(
            detect_actual_pickup_city("load actually in Chicago, IL"),
            "Chicago, IL",
        )

    def test_detect_contact_override_detects_obfuscated_email(self):
        result = detect_contact_override("email dispatch at example dot com")

        self.assertEqual(result["email"], "dispatch@example.com")

    def test_parse_notes_returns_core_flags_and_summary(self):
        result = parse_notes(
            notes="8 ft tarps required, need 6 straps, permit load, TWIC card required",
            commodity="steel",
            posted_trailer_type="Flatbed",
            posted_weight=40000,
        )

        self.assertTrue(result["requires_tarp"])
        self.assertEqual(result["tarp_size"], "8 ft")
        self.assertTrue(result["requires_straps"])
        self.assertEqual(result["strap_count"], 6)
        self.assertTrue(result["is_od"])
        self.assertTrue(result["twic_required"])

        self.assertIn("8 ft tarps detected", result["notes_summary"])
        self.assertIn("6 straps required", result["notes_summary"])
        self.assertIn("OD / permit / wide load detected", result["notes_summary"])
        self.assertIn("TWIC required", result["notes_summary"])


if __name__ == "__main__":
    unittest.main()
