import unittest

from app.market_intelligence.notes_parser_text_helpers import (
    clean_text,
    lower_text,
    normalize_email,
    normalize_phone,
    normalize_text,
)


class TestNotesParserTextHelpers(unittest.TestCase):
    def test_normalize_text_handles_none_and_spacing(self):
        self.assertEqual(normalize_text(None), "")
        self.assertEqual(normalize_text("  Hello  "), "Hello")

    def test_lower_text_normalizes_and_lowers(self):
        self.assertEqual(lower_text("  HELLO  "), "hello")

    def test_clean_text_normalizes_common_symbols(self):
        self.assertEqual(
            clean_text("  NEED_TARPS; strap|and go  "),
            "need tarps strap and go",
        )

    def test_normalize_email_handles_dat_typos_and_obfuscation(self):
        self.assertEqual(
            normalize_email("Info@National-TransportServices`com"),
            "info@national-transportservices.com",
        )
        self.assertEqual(
            normalize_email("dispatch at example dot com"),
            "dispatch@example.com",
        )
        self.assertEqual(
            normalize_email("dispatch(at)example(dot)com"),
            "dispatch@example.com",
        )

    def test_normalize_email_returns_empty_for_invalid_email(self):
        self.assertEqual(normalize_email("not an email"), "")
        self.assertEqual(normalize_email("broker@example"), "")

    def test_normalize_phone_trims_and_collapses_spaces(self):
        self.assertEqual(
            normalize_phone("  555   111   2222  "),
            "555 111 2222",
        )


if __name__ == "__main__":
    unittest.main()
