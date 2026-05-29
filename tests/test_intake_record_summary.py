import copy
import inspect
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from app.market_intelligence import intake_record_summary
from app.market_intelligence.intake_record import build_intake_record
from app.market_intelligence.intake_record_summary import (
    build_intake_record_summary,
    format_intake_record_summary,
)


class FakeSource:
    broker_name = "Acme Logistics"
    broker_mc = "123456"
    rate = 3200
    pickup_location = "Dallas, TX"
    pickup_date = "2026-05-30"
    delivery_location = "Denver, CO"
    delivery_date = "2026-05-31"
    commodity = "Steel coils"
    weight = 42000
    reference_id = "REF-123"
    equipment = "Conestoga"
    special_requirements = ["TARPS"]


def clean_source():
    return {
        "broker_name": "Acme Logistics",
        "broker_mc": "123456",
        "rate": 3200,
        "pickup_location": "Dallas, TX",
        "pickup_date": "2026-05-30",
        "delivery_location": "Denver, CO",
        "delivery_date": "2026-05-31",
        "commodity": "Steel coils",
        "weight": 42000,
        "reference_id": "REF-123",
        "equipment": "Conestoga",
        "special_requirements": ["TARPS", "APPOINTMENT_REQUIRED"],
    }


class TestIntakeRecordSummary(unittest.TestCase):
    def test_clean_record_returns_ready_for_review(self):
        summary = build_intake_record_summary(clean_source())

        self.assertEqual(summary["status"], "READY_FOR_REVIEW")
        self.assertEqual(summary["missing_fields"], [])
        self.assertEqual(summary["needs_check_fields"], [])
        self.assertTrue(summary["ready_for_review"])
        self.assertFalse(summary["ready_for_dispatch_case_linking"])
        self.assertIn("broker_name", summary["imported_fields"])
        self.assertIn("reference_id", summary["imported_fields"])

    def test_missing_mandatory_fields_returns_missing_fields(self):
        summary = build_intake_record_summary({})

        self.assertEqual(summary["status"], "MISSING_FIELDS")
        self.assertFalse(summary["ready_for_review"])
        self.assertIn("broker_name", summary["missing_fields"])
        self.assertIn("rate", summary["missing_fields"])

    def test_partial_broker_info_shows_missing_and_needs_check(self):
        summary = build_intake_record_summary({"broker_name": "Acme Logistics"})

        self.assertEqual(summary["status"], "MISSING_FIELDS")
        self.assertIn("broker_mc", summary["missing_fields"])
        self.assertIn("broker_mc", summary["needs_check_fields"])

    def test_pickup_and_delivery_date_missing_are_shown_clearly(self):
        summary = build_intake_record_summary(
            {
                "pickup_location": "Dallas, TX",
                "delivery_location": "Denver, CO",
            }
        )
        text = format_intake_record_summary(summary)

        self.assertIn("pickup_date", summary["missing_fields"])
        self.assertIn("delivery_date", summary["missing_fields"])
        self.assertIn("Missing fields: ", text)
        self.assertIn("pickup_date", text)
        self.assertIn("delivery_date", text)

    def test_special_requirements_are_shown(self):
        summary = build_intake_record_summary(clean_source())
        text = format_intake_record_summary(summary)

        self.assertEqual(
            summary["intake_record"]["special_requirements"],
            ["TARPS", "APPOINTMENT_REQUIRED"],
        )
        self.assertIn("Special requirements: TARPS, APPOINTMENT_REQUIRED", text)

    def test_summary_does_not_mutate_inputs(self):
        source = clean_source()
        source_before = copy.deepcopy(source)
        fake = FakeSource()
        fake_before = dict(fake.__dict__)

        build_intake_record_summary(source)
        build_intake_record_summary(fake)

        self.assertEqual(source, source_before)
        self.assertEqual(fake.__dict__, fake_before)

    def test_summary_is_json_serializable(self):
        summary = build_intake_record_summary(clean_source())

        json.dumps(summary)

    def test_formatter_includes_dry_run_warning(self):
        summary = build_intake_record_summary(clean_source())
        text = format_intake_record_summary(summary)

        self.assertIn("DRY RUN ONLY - no parser/storage/integration used", text)

    def test_cli_exists_and_prints_sample_summary(self):
        script = Path("scripts/run_intake_record_dry_run.py")
        self.assertTrue(script.exists())

        from scripts import run_intake_record_dry_run

        output = io.StringIO()

        with redirect_stdout(output):
            result = run_intake_record_dry_run.main()

        text = output.getvalue()

        self.assertEqual(result, 0)
        self.assertIn("INTAKE RECORD DRY RUN", text)
        self.assertIn("DRY RUN ONLY - no parser/storage/integration used", text)

    def test_accepts_already_built_intake_record(self):
        record = build_intake_record(clean_source(), intake_id="INTAKE-1")
        summary = build_intake_record_summary(record)

        self.assertEqual(summary["intake_record"]["intake_id"], "INTAKE-1")
        self.assertEqual(summary["status"], "READY_FOR_REVIEW")

    def test_helper_and_cli_do_not_import_forbidden_layers(self):
        helper_source = inspect.getsource(intake_record_summary)
        script_source = Path("scripts/run_intake_record_dry_run.py").read_text()
        combined = helper_source + "\n" + script_source

        forbidden = [
            "import pypdf",
            "from pypdf",
            "PdfReader",
            "import gspread",
            "from google.oauth",
            "telegram_sender",
            "telegram_notifier",
            "import dispatch_case",
            "from app.market_intelligence.dispatch_case",
            "event_logger",
            "scheduler",
            "import threading",
            "googlemaps",
            "load_intake",
            "open(",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, combined)


if __name__ == "__main__":
    unittest.main()
