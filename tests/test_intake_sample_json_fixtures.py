import json
import unittest
from pathlib import Path

from app.market_intelligence.intake_record_summary import (
    build_intake_record_summary,
)


FIXTURE_DIR = Path("tests/fixtures/intake_sample_records")

EXPECTED_FIELDS = {
    "clean_full_ratecon.json": {
        "missing": [],
        "needs_check": [],
    },
    "missing_broker_mc.json": {
        "missing": ["broker_mc"],
        "needs_check": ["broker_mc"],
    },
    "missing_weight_commodity.json": {
        "missing": ["weight", "commodity"],
        "needs_check": [],
    },
    "missing_pickup_delivery_dates.json": {
        "missing": ["pickup_date", "delivery_date"],
        "needs_check": ["pickup_date", "delivery_date"],
    },
    "special_requirements_needs_check.json": {
        "missing": ["broker_mc"],
        "needs_check": ["broker_mc"],
    },
}


def load_sample(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


class TestIntakeSampleJsonFixtures(unittest.TestCase):
    def test_sample_files_exist(self):
        paths = sorted(FIXTURE_DIR.glob("*.json"))

        self.assertEqual(len(paths), 5)
        self.assertEqual(
            set(EXPECTED_FIELDS),
            {path.name for path in paths},
        )

    def test_samples_are_valid_json_objects(self):
        for path in sorted(FIXTURE_DIR.glob("*.json")):
            with self.subTest(path=path.name):
                source = load_sample(path)

                self.assertIsInstance(source, dict)
                json.dumps(source)

    def test_each_sample_builds_intake_record(self):
        for path in sorted(FIXTURE_DIR.glob("*.json")):
            with self.subTest(path=path.name):
                summary = build_intake_record_summary(load_sample(path))

                self.assertIn("intake_record", summary)
                self.assertIn(
                    summary["status"],
                    {"READY_FOR_REVIEW", "MISSING_FIELDS", "NEEDS_CHECK"},
                )

    def test_expected_missing_fields_match(self):
        for path in sorted(FIXTURE_DIR.glob("*.json")):
            with self.subTest(path=path.name):
                summary = build_intake_record_summary(load_sample(path))

                self.assertEqual(
                    summary["missing_fields"],
                    EXPECTED_FIELDS[path.name]["missing"],
                )

    def test_expected_needs_check_fields_match(self):
        for path in sorted(FIXTURE_DIR.glob("*.json")):
            with self.subTest(path=path.name):
                summary = build_intake_record_summary(load_sample(path))

                self.assertEqual(
                    summary["needs_check_fields"],
                    EXPECTED_FIELDS[path.name]["needs_check"],
                )

    def test_clean_sample_has_no_missing_fields(self):
        summary = build_intake_record_summary(
            load_sample(FIXTURE_DIR / "clean_full_ratecon.json")
        )

        self.assertEqual(summary["status"], "READY_FOR_REVIEW")
        self.assertEqual(summary["missing_fields"], [])
        self.assertEqual(summary["needs_check_fields"], [])

    def test_special_requirements_sample_preserves_requirements(self):
        summary = build_intake_record_summary(
            load_sample(FIXTURE_DIR / "special_requirements_needs_check.json")
        )

        self.assertEqual(
            summary["intake_record"]["special_requirements"],
            ["TARPS", "APPOINTMENT_REQUIRED"],
        )

    def test_samples_use_synthetic_data_only(self):
        forbidden_terms = [
            "@",
            "phone",
            "driver",
            "customer",
            "real broker",
            "gmail",
            "contact",
        ]

        for path in sorted(FIXTURE_DIR.glob("*.json")):
            with self.subTest(path=path.name):
                source = load_sample(path)
                serialized = json.dumps(source).lower()

                self.assertIn("synthetic", serialized)
                self.assertIn("SYNTH", source.get("reference_id", "SYNTH"))

                for term in forbidden_terms:
                    self.assertNotIn(term, serialized)


if __name__ == "__main__":
    unittest.main()
