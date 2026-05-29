import inspect
import json
import unittest

from app.market_intelligence.intake.parser_contract import normalize_parser_output
from app.market_intelligence.intake.summary import build_intake_record_summary
from tests.fixtures import parser_expected_outputs
from tests.fixtures.parser_expected_outputs import PARSER_EXPECTED_OUTPUTS


class ParserExpectedOutputsTests(unittest.TestCase):
    def test_expected_outputs_have_safe_size(self):
        self.assertGreaterEqual(len(PARSER_EXPECTED_OUTPUTS), 6)
        self.assertLessEqual(len(PARSER_EXPECTED_OUTPUTS), 10)

    def test_each_example_normalizes_through_parser_contract(self):
        for scenario in PARSER_EXPECTED_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(
                    scenario["raw_parser_output"],
                    source_type="synthetic_expected_parser_output",
                    source_file_name=f"{scenario['scenario_id']}.txt",
                    received_at_utc="2026-05-29T10:00:00Z",
                    intake_id=f"INTAKE-{scenario['scenario_id']}",
                )

                self.assertEqual(record["intake_id"], f"INTAKE-{scenario['scenario_id']}")
                self.assertEqual(record["source_type"], "synthetic_expected_parser_output")
                self.assertEqual(record["source_file_name"], f"{scenario['scenario_id']}.txt")
                self.assertEqual(record["received_at_utc"], "2026-05-29T10:00:00Z")

    def test_each_example_can_build_intake_summary(self):
        for scenario in PARSER_EXPECTED_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(scenario["raw_parser_output"])
                summary = build_intake_record_summary(record)

                self.assertIn(
                    summary["status"],
                    ["READY_FOR_REVIEW", "MISSING_FIELDS", "NEEDS_CHECK"],
                )
                self.assertEqual(
                    summary["missing_fields"],
                    scenario["expected_missing_fields"],
                )
                self.assertEqual(
                    summary["needs_check_fields"],
                    scenario["expected_needs_check_fields"],
                )

    def test_expected_missing_fields_match(self):
        for scenario in PARSER_EXPECTED_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(scenario["raw_parser_output"])

                self.assertEqual(
                    record["missing_fields"],
                    scenario["expected_missing_fields"],
                )

    def test_expected_needs_check_fields_match(self):
        for scenario in PARSER_EXPECTED_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(scenario["raw_parser_output"])

                self.assertEqual(
                    record["needs_check_fields"],
                    scenario["expected_needs_check_fields"],
                )

    def test_expected_confidence_keys_are_preserved(self):
        for scenario in PARSER_EXPECTED_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(scenario["raw_parser_output"])

                self.assertEqual(
                    sorted(record["field_confidence"].keys()),
                    sorted(scenario["expected_confidence_keys"]),
                )

    def test_special_requirements_match_expected_values(self):
        for scenario in PARSER_EXPECTED_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(scenario["raw_parser_output"])

                self.assertEqual(
                    record["special_requirements"],
                    scenario["expected_special_requirements"],
                )

    def test_examples_are_json_serializable(self):
        json.dumps(PARSER_EXPECTED_OUTPUTS)

        for scenario in PARSER_EXPECTED_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(scenario["raw_parser_output"])
                json.dumps(record)

    def test_examples_use_synthetic_data_only(self):
        forbidden_terms = [
            "@",
            "phone",
            "driver",
            "customer",
            "real broker",
            "gmail",
            "contact",
        ]

        for scenario in PARSER_EXPECTED_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                serialized = json.dumps(scenario).lower()

                self.assertIn("synthetic", serialized)
                self.assertIn("SYNTH", scenario["raw_parser_output"]["reference_id"])

                for term in forbidden_terms:
                    self.assertNotIn(term, serialized)

    def test_fixture_has_no_parser_pdf_or_ocr_imports(self):
        source = inspect.getsource(parser_expected_outputs).lower()

        forbidden_terms = [
            "pypdf",
            "pdfreader",
            "pytesseract",
            "ocr",
            "open(",
            "read_text(",
            "read_bytes(",
            "write_text(",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
