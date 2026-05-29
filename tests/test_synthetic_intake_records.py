import json
import unittest

from app.market_intelligence.intake_record_summary import (
    build_intake_record_summary,
)
from tests.fixtures.synthetic_intake_records import SYNTHETIC_INTAKE_RECORDS


class TestSyntheticIntakeRecords(unittest.TestCase):
    def test_every_fixture_builds_an_intake_record(self):
        self.assertGreaterEqual(len(SYNTHETIC_INTAKE_RECORDS), 8)
        self.assertLessEqual(len(SYNTHETIC_INTAKE_RECORDS), 12)

        for scenario in SYNTHETIC_INTAKE_RECORDS:
            with self.subTest(scenario=scenario["scenario_id"]):
                summary = build_intake_record_summary(scenario["source"])

                self.assertIn("intake_record", summary)
                self.assertEqual(summary["status"], scenario["expected_status"])

    def test_expected_missing_fields_match(self):
        for scenario in SYNTHETIC_INTAKE_RECORDS:
            with self.subTest(scenario=scenario["scenario_id"]):
                summary = build_intake_record_summary(scenario["source"])

                self.assertEqual(
                    summary["missing_fields"],
                    scenario["expected_missing_fields"],
                )

    def test_expected_needs_check_fields_match(self):
        for scenario in SYNTHETIC_INTAKE_RECORDS:
            with self.subTest(scenario=scenario["scenario_id"]):
                summary = build_intake_record_summary(scenario["source"])

                self.assertEqual(
                    summary["needs_check_fields"],
                    scenario["expected_needs_check_fields"],
                )

    def test_clean_fixture_has_no_missing_fields(self):
        clean = next(
            scenario
            for scenario in SYNTHETIC_INTAKE_RECORDS
            if scenario["scenario_id"] == "clean_full_record"
        )
        summary = build_intake_record_summary(clean["source"])

        self.assertEqual(summary["status"], "READY_FOR_REVIEW")
        self.assertEqual(summary["missing_fields"], [])
        self.assertEqual(summary["needs_check_fields"], [])

    def test_fixture_set_is_json_serializable(self):
        json.dumps(SYNTHETIC_INTAKE_RECORDS)

    def test_fixtures_use_synthetic_data_only(self):
        for scenario in SYNTHETIC_INTAKE_RECORDS:
            with self.subTest(scenario=scenario["scenario_id"]):
                source = scenario["source"]

                self.assertIn("SYNTH", source.get("reference_id", "SYNTH"))

                if source.get("broker_name"):
                    self.assertIn("Synthetic", source["broker_name"])

                serialized = json.dumps(source).lower()
                self.assertNotIn("@", serialized)
                self.assertNotIn("phone", serialized)
                self.assertNotIn("driver", serialized)
                self.assertNotIn("customer", serialized)
                self.assertNotIn("real broker", serialized)


if __name__ == "__main__":
    unittest.main()
