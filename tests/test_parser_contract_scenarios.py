import json
import unittest

from app.market_intelligence.intake_parser_contract import normalize_parser_output
from app.market_intelligence.intake_record_summary import build_intake_record_summary
from tests.fixtures.parser_contract_outputs import PARSER_CONTRACT_OUTPUTS


class TestParserContractScenarios(unittest.TestCase):
    def test_each_parser_output_normalizes_to_intake_record(self):
        self.assertGreaterEqual(len(PARSER_CONTRACT_OUTPUTS), 6)
        self.assertLessEqual(len(PARSER_CONTRACT_OUTPUTS), 8)

        for scenario in PARSER_CONTRACT_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(
                    scenario["raw_output"],
                    source_type=scenario.get("source_type", ""),
                    source_file_name=scenario.get("source_file_name", ""),
                    received_at_utc="2026-05-29T10:00:00Z",
                    intake_id=f"INTAKE-{scenario['scenario_id']}",
                )

                self.assertEqual(record["intake_id"], f"INTAKE-{scenario['scenario_id']}")
                self.assertEqual(record["received_at_utc"], "2026-05-29T10:00:00Z")
                self.assertIn("missing_fields", record)
                self.assertIn("needs_check_fields", record)

    def test_each_parser_output_can_be_summarized(self):
        for scenario in PARSER_CONTRACT_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(
                    scenario["raw_output"],
                    source_type=scenario.get("source_type", ""),
                    source_file_name=scenario.get("source_file_name", ""),
                )
                summary = build_intake_record_summary(record)

                self.assertEqual(summary["status"], scenario["expected_status"])

    def test_expected_missing_fields_match(self):
        for scenario in PARSER_CONTRACT_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(scenario["raw_output"])

                self.assertEqual(
                    record["missing_fields"],
                    scenario["expected_missing_fields"],
                )

    def test_expected_needs_check_fields_match(self):
        for scenario in PARSER_CONTRACT_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(scenario["raw_output"])

                self.assertEqual(
                    record["needs_check_fields"],
                    scenario["expected_needs_check_fields"],
                )

    def test_field_confidence_is_preserved(self):
        scenario = next(
            scenario
            for scenario in PARSER_CONTRACT_OUTPUTS
            if scenario["scenario_id"] == "weak_field_confidence"
        )
        record = normalize_parser_output(scenario["raw_output"])

        self.assertEqual(
            record["field_confidence"],
            {"rate": "LOW", "weight": "LOW"},
        )

    def test_special_requirements_are_preserved(self):
        scenario = next(
            scenario
            for scenario in PARSER_CONTRACT_OUTPUTS
            if scenario["scenario_id"] == "special_requirements"
        )
        record = normalize_parser_output(scenario["raw_output"])

        self.assertEqual(
            record["special_requirements"],
            ["TARPS", "APPOINTMENT_REQUIRED"],
        )

    def test_source_metadata_override_scenario(self):
        scenario = next(
            scenario
            for scenario in PARSER_CONTRACT_OUTPUTS
            if scenario["scenario_id"] == "source_metadata_override"
        )
        record = normalize_parser_output(
            scenario["raw_output"],
            source_type=scenario["source_type"],
            source_file_name=scenario["source_file_name"],
        )

        self.assertEqual(record["source_type"], scenario["expected_source_type"])
        self.assertEqual(
            record["source_file_name"],
            scenario["expected_source_file_name"],
        )

    def test_normalized_records_are_json_serializable(self):
        for scenario in PARSER_CONTRACT_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(scenario["raw_output"])

                json.dumps(record)

    def test_fixtures_use_synthetic_data_only(self):
        forbidden_terms = [
            "@",
            "phone",
            "driver",
            "real broker",
            "gmail",
            "contact",
        ]

        for scenario in PARSER_CONTRACT_OUTPUTS:
            with self.subTest(scenario=scenario["scenario_id"]):
                record = normalize_parser_output(scenario["raw_output"])
                serialized = json.dumps(record).lower()

                self.assertIn("synthetic", serialized)
                self.assertIn("SYNTH", record.get("reference_id", "SYNTH"))

                for term in forbidden_terms:
                    self.assertNotIn(term, serialized)


if __name__ == "__main__":
    unittest.main()
