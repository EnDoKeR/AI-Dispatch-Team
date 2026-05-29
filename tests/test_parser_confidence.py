import inspect
import json
import unittest

from app.market_intelligence.intake import parser_confidence
from app.market_intelligence.intake.parser_confidence import (
    HIGH,
    LOW,
    MEDIUM,
    UNKNOWN,
    confidence_for_field,
    low_confidence_fields,
    normalize_confidence,
    normalize_field_confidence,
)


class ParserConfidenceTests(unittest.TestCase):
    def test_normalize_known_confidence_values(self):
        self.assertEqual(normalize_confidence("high"), HIGH)
        self.assertEqual(normalize_confidence(" MEDIUM "), MEDIUM)
        self.assertEqual(normalize_confidence("Low"), LOW)
        self.assertEqual(normalize_confidence("UNKNOWN"), UNKNOWN)

    def test_unknown_values_become_unknown(self):
        self.assertEqual(normalize_confidence("certain"), UNKNOWN)
        self.assertEqual(normalize_confidence(""), UNKNOWN)
        self.assertEqual(normalize_confidence(None), UNKNOWN)

    def test_missing_confidence_defaults_safely(self):
        self.assertEqual(normalize_field_confidence(), {})
        self.assertEqual(confidence_for_field(None, "rate"), UNKNOWN)
        self.assertEqual(confidence_for_field({}, "rate"), UNKNOWN)
        self.assertEqual(confidence_for_field({"rate": "HIGH"}, ""), UNKNOWN)

    def test_normalizes_field_confidence_dict(self):
        field_confidence = {
            "rate": "high",
            "weight": " low ",
            "commodity": "maybe",
            "": "HIGH",
        }

        self.assertEqual(
            normalize_field_confidence(field_confidence),
            {
                "rate": HIGH,
                "weight": LOW,
                "commodity": UNKNOWN,
            },
        )

    def test_expected_fields_can_be_filled_as_unknown(self):
        self.assertEqual(
            normalize_field_confidence(
                {"rate": "HIGH"},
                expected_fields=["rate", "weight", "commodity"],
            ),
            {
                "rate": HIGH,
                "weight": UNKNOWN,
                "commodity": UNKNOWN,
            },
        )

    def test_low_confidence_fields_are_reported(self):
        self.assertEqual(
            low_confidence_fields(
                {
                    "rate": "HIGH",
                    "pickup_time": "LOW",
                    "weight": "low",
                    "commodity": "UNKNOWN",
                }
            ),
            ["pickup_time", "weight"],
        )

    def test_output_is_json_serializable(self):
        normalized = normalize_field_confidence(
            {"rate": "HIGH"},
            expected_fields=["rate", "weight"],
        )

        json.dumps(normalized)

    def test_helper_has_no_forbidden_imports(self):
        source = inspect.getsource(parser_confidence).lower()

        forbidden = [
            "pypdf",
            "pdfreader",
            "gspread",
            "google.oauth",
            "gmail",
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "event_logger",
            "scheduler",
            "threading",
            "googlemaps",
            "dat_api",
            "app.load_intake",
            "open(",
            "read_text(",
            "write_text(",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
