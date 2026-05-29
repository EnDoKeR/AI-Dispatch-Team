import inspect
import json
import re
import unittest

from app.market_intelligence.intake.parser_contract import normalize_parser_output
from tests.fixtures import pasted_text_ratecon_examples
from tests.fixtures.pasted_text_ratecon_examples import (
    PASTED_TEXT_RATECON_EXAMPLES,
)


class PastedTextRateConExamplesTests(unittest.TestCase):
    def test_fixture_count_is_safe(self):
        self.assertGreaterEqual(len(PASTED_TEXT_RATECON_EXAMPLES), 8)
        self.assertLessEqual(len(PASTED_TEXT_RATECON_EXAMPLES), 12)

    def test_fixtures_have_required_shape(self):
        required_keys = [
            "scenario_id",
            "scenario_name",
            "pasted_text",
            "expected_parser_output",
            "expected_missing_fields",
            "expected_needs_check_fields",
            "expected_confidence",
            "expected_special_requirements",
        ]

        for scenario in PASTED_TEXT_RATECON_EXAMPLES:
            with self.subTest(scenario=scenario["scenario_id"]):
                for key in required_keys:
                    self.assertIn(key, scenario)

                self.assertIsInstance(scenario["pasted_text"], str)
                self.assertIsInstance(scenario["expected_parser_output"], dict)
                self.assertIsInstance(scenario["expected_missing_fields"], list)
                self.assertIsInstance(scenario["expected_needs_check_fields"], list)
                self.assertIsInstance(scenario["expected_confidence"], dict)
                self.assertIsInstance(scenario["expected_special_requirements"], list)

    def test_expected_outputs_normalize_through_parser_contract(self):
        for scenario in PASTED_TEXT_RATECON_EXAMPLES:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(scenario["expected_parser_output"])

                self.assertEqual(
                    record["missing_fields"],
                    scenario["expected_missing_fields"],
                )
                self.assertEqual(
                    record["needs_check_fields"],
                    scenario["expected_needs_check_fields"],
                )

    def test_expected_confidence_is_preserved(self):
        for scenario in PASTED_TEXT_RATECON_EXAMPLES:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(scenario["expected_parser_output"])

                for field_name, confidence in scenario["expected_confidence"].items():
                    self.assertEqual(
                        record["field_confidence"].get(field_name),
                        confidence,
                    )

    def test_expected_special_requirements_match(self):
        for scenario in PASTED_TEXT_RATECON_EXAMPLES:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(scenario["expected_parser_output"])

                self.assertEqual(
                    record["special_requirements"],
                    scenario["expected_special_requirements"],
                )

    def test_fixtures_are_json_serializable(self):
        json.dumps(PASTED_TEXT_RATECON_EXAMPLES)

    def test_fixtures_use_synthetic_data_only(self):
        serialized = json.dumps(PASTED_TEXT_RATECON_EXAMPLES).lower()

        self.assertIn("synthetic", serialized)
        self.assertNotIn("private_ratecons", serialized)
        self.assertNotIn("real broker", serialized)
        self.assertNotIn("real customer", serialized)
        self.assertNotIn("real driver", serialized)
        self.assertNotIn("gmail", serialized)
        self.assertNotRegex(serialized, r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}")
        self.assertNotRegex(serialized, r"\b\d{3}[-.]\d{3}[-.]\d{4}\b")

    def test_fixture_module_has_no_file_or_parser_imports(self):
        source = inspect.getsource(pasted_text_ratecon_examples).lower()
        forbidden = [
            "pypdf",
            "pdfreader",
            "pytesseract",
            "ocr",
            "open(",
            "read_text(",
            "read_bytes(",
            "write_text(",
            "telegram_sender",
            "dispatch_case",
            "event_logger",
            "app.load_intake",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
