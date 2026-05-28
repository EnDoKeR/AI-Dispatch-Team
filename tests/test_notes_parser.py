import unittest

from app.market_intelligence.notes_parser import (
    clean_text,
    detect_actual_pickup_city,
    detect_cash_or_zelle,
    detect_quickpay_review,
    detect_contact_override,
    detect_conestoga_ok,
    detect_flatbed_preferred,
    detect_flatbed_required,
    detect_no_conestoga,
    detect_iso_tank_required,
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

    def test_detect_conestoga_notes_logic(self):
        self.assertTrue(detect_no_conestoga("no conestoga"))
        self.assertTrue(detect_no_conestoga("no stoga"))
        self.assertTrue(detect_no_conestoga("flatbed only"))
        self.assertTrue(detect_no_conestoga("flat only"))

        self.assertTrue(detect_flatbed_required("flatbed only"))
        self.assertTrue(detect_flatbed_required("flat only"))

        self.assertTrue(detect_conestoga_ok("conestoga ok"))
        self.assertTrue(detect_conestoga_ok("stoga ok"))
        self.assertTrue(detect_conestoga_ok("conestoga accepted"))

    def test_detect_flatbed_preferred_for_conestoga_verify(self):
        self.assertTrue(detect_flatbed_preferred("flatbed preferred"))
        self.assertTrue(detect_flatbed_preferred("prefer flatbed"))

        self.assertFalse(detect_no_conestoga("flatbed preferred"))
        self.assertFalse(detect_flatbed_required("flatbed preferred"))

        result = parse_notes(notes="flatbed preferred")

        self.assertTrue(result["flatbed_preferred"])
        self.assertFalse(result["no_conestoga"])
        self.assertFalse(result["flatbed_required"])
        self.assertIn(
            "flatbed preferred; verify Conestoga acceptance",
            result["notes_summary"],
        )

    def test_detect_cash_or_zelle_blocks_cash_payment_language(self):
        self.assertTrue(detect_cash_or_zelle("cash or zelle"))
        self.assertTrue(detect_cash_or_zelle("cash on delivery"))
        self.assertTrue(detect_cash_or_zelle("zelle"))
        self.assertTrue(detect_cash_or_zelle("cashapp"))

    def test_detect_quickpay_review_detects_quickpay_but_not_cash_block(self):
        self.assertTrue(detect_quickpay_review("quickpay available"))
        self.assertTrue(detect_quickpay_review("quick pay available"))
        self.assertFalse(detect_cash_or_zelle("quickpay available"))

    def test_detect_iso_tank_required_creates_document_review_warning(self):
        self.assertTrue(detect_iso_tank_required("ISO tank load"))
        self.assertTrue(detect_iso_tank_required("iso tanks"))
        self.assertFalse(detect_iso_tank_required("regular steel load"))

        result = parse_notes(notes="ISO tank load")

        self.assertTrue(result["iso_tank_required"])
        self.assertIn(
            "ISO tank document/review warning detected",
            result["notes_summary"],
        )

    def test_detect_weight_unknown_for_missing_or_placeholder_weight(self):
        self.assertTrue(detect_weight_unknown("weight TBD"))
        self.assertTrue(detect_weight_unknown("call for weight"))
        self.assertTrue(detect_weight_unknown("confirm weight"))
        self.assertTrue(detect_weight_unknown("weight 1 lb"))
        self.assertTrue(detect_weight_unknown("posted weight 1"))
        self.assertTrue(detect_weight_unknown("clean notes", posted_weight=1))

    def test_detect_multiple_loads_available_is_not_stops(self):
        self.assertTrue(detect_multiple_loads_available("multiple loads available"))
        self.assertEqual(detect_stops_from_text("multiple loads available"), 0)

    def test_detect_stops_from_text_detects_multistop_language(self):
        self.assertGreaterEqual(detect_stops_from_text("multistop load"), 2)
        self.assertGreaterEqual(detect_stops_from_text("multi stop load"), 2)
        self.assertGreaterEqual(detect_stops_from_text("multiple drops"), 2)
        self.assertGreaterEqual(detect_stops_from_text("multiple pickups"), 2)

    def test_detect_actual_pickup_city_detects_explicit_actual_city_state(self):
        cases = [
            ("actual pickup in Dallas, TX", "Dallas, TX"),
            ("load actually in Chicago, IL", "Chicago, IL"),
            ("actual pickup city Dallas TX", "Dallas, TX"),
            ("actual pick up -- Dallas (TX)", "Dallas, TX"),
            ("actual PU: Atlanta (GA)", "Atlanta, GA"),
            ("pickup is actually in Phoenix, AZ", "Phoenix, AZ"),
        ]

        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(detect_actual_pickup_city(text), expected)

    def test_detect_actual_pickup_city_ignores_normal_pickup_city_without_actual_signal(self):
        self.assertEqual(detect_actual_pickup_city("pickup in Dallas, TX"), "")
        self.assertEqual(detect_actual_pickup_city("load in Dallas, TX"), "")
        self.assertEqual(detect_actual_pickup_city("pu in Dallas, TX"), "")
        self.assertEqual(detect_actual_pickup_city("load in Dallas"), "")

    def test_detect_contact_override_detects_obfuscated_email(self):
        result = detect_contact_override("email dispatch at example dot com")

        self.assertEqual(result["email"], "dispatch@example.com")

    def test_detect_contact_override_detects_more_obfuscated_email_formats(self):
        cases = [
            "email dispatch(at)example(dot)com",
            "email dispatch [at] example [dot] com",
            "email dispatch at example.com",
            "email dispatch@example dot com",
            "email d i s p a t c h at example dot com",
        ]

        for case in cases:
            with self.subTest(case=case):
                result = detect_contact_override(case)
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
        self.assertFalse(result["quickpay_review"])
        self.assertFalse(result["iso_tank_required"])
        self.assertFalse(result["flatbed_preferred"])

        self.assertIn("8 ft tarps detected", result["notes_summary"])
        self.assertIn("6 straps required", result["notes_summary"])
        self.assertIn("OD / permit / wide load detected", result["notes_summary"])
        self.assertIn("TWIC required", result["notes_summary"])


if __name__ == "__main__":
    unittest.main()
