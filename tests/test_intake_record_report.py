import copy
import inspect
import tempfile
from pathlib import Path
import unittest

from app.market_intelligence.intake_record_repository import save_intake_records
from app.market_intelligence.intake_record_report import (
    build_intake_record_report,
    format_intake_record_report,
)


def temp_file(directory):
    return Path(directory) / "intake_records.json"


def record(intake_id, status="READY_FOR_REVIEW", **overrides):
    data = {
        "intake_id": intake_id,
        "status": status,
        "broker_name": "Synthetic Report Broker",
        "broker_mc": "SYNTH-MC-4001",
        "rate": 3200,
        "pickup_location": "Dallas, TX",
        "pickup_date": "2026-05-30",
        "delivery_location": "Denver, CO",
        "delivery_date": "2026-05-31",
        "commodity": "Steel coils",
        "weight": 42000,
        "reference_id": f"SYNTH-REPORT-{intake_id}",
        "equipment": "Conestoga",
    }
    data.update(overrides)

    return data


class TestIntakeRecordReport(unittest.TestCase):
    def test_missing_file_returns_empty_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = build_intake_record_report(temp_file(temp_dir))

            self.assertEqual(report["total_records"], 0)
            self.assertEqual(report["records"], [])
            self.assertIn("No intake records found.", format_intake_record_report(report))

    def test_status_counts_are_correct(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            save_intake_records(
                [
                    record("READY-1", "READY_FOR_REVIEW"),
                    record("READY-2", "READY_FOR_REVIEW"),
                    record("MISSING-1", "MISSING_FIELDS"),
                    record("CHECK-1", "NEEDS_CHECK"),
                ],
                file_path,
            )

            report = build_intake_record_report(file_path)

            self.assertEqual(report["total_records"], 4)
            self.assertEqual(report["status_counts"]["READY_FOR_REVIEW"], 2)
            self.assertEqual(report["status_counts"]["MISSING_FIELDS"], 1)
            self.assertEqual(report["status_counts"]["NEEDS_CHECK"], 1)

    def test_report_lists_key_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            save_intake_records([record("INTAKE-1")], file_path)

            text = format_intake_record_report(build_intake_record_report(file_path))

            self.assertIn("INTAKE RECORDS DRY-RUN REPORT", text)
            self.assertIn("Intake ID: INTAKE-1", text)
            self.assertIn("Broker: Synthetic Report Broker", text)
            self.assertIn("Rate: $3200", text)
            self.assertIn("Pickup: Dallas, TX", text)
            self.assertIn("Delivery: Denver, CO", text)

    def test_missing_fields_are_shown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            save_intake_records(
                [
                    record(
                        "MISSING-1",
                        "MISSING_FIELDS",
                        broker_mc="",
                        missing_fields=["broker_mc"],
                        needs_check_fields=["broker_mc"],
                    )
                ],
                file_path,
            )

            text = format_intake_record_report(build_intake_record_report(file_path))

            self.assertIn("Missing fields: broker_mc", text)

    def test_needs_check_fields_are_shown(self):
        report = {
            "total_records": 1,
            "status_counts": {"NEEDS_CHECK": 1},
            "records": [
                {
                    "intake_id": "CHECK-1",
                    "status": "NEEDS_CHECK",
                    "needs_check_fields": ["broker_mc"],
                }
            ],
        }

        text = format_intake_record_report(report)

        self.assertIn("Needs-check fields: broker_mc", text)

    def test_invalid_repository_file_is_empty_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            file_path.write_text("{bad json", encoding="utf-8")

            report = build_intake_record_report(file_path)

            self.assertEqual(report["total_records"], 0)
            self.assertEqual(report["records"], [])

    def test_helper_does_not_mutate_saved_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            records = [record("INTAKE-1")]
            before = copy.deepcopy(records)
            save_intake_records(records, file_path)

            build_intake_record_report(file_path)

            self.assertEqual(records, before)

    def test_cli_exists_and_prints_human_report(self):
        script_path = Path("scripts/report_intake_records.py")
        self.assertTrue(script_path.exists())

        from scripts import report_intake_records

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            save_intake_records([record("INTAKE-1")], file_path)

            import io
            from contextlib import redirect_stdout

            output = io.StringIO()
            with redirect_stdout(output):
                result = report_intake_records.main(["--file-path", str(file_path)])

        text = output.getvalue()

        self.assertEqual(result, 0)
        self.assertIn("INTAKE RECORDS DRY-RUN REPORT", text)
        self.assertIn("INTAKE-1", text)

    def test_report_does_not_import_forbidden_layers(self):
        import app.market_intelligence.intake_record_report as report_module

        helper_source = inspect.getsource(report_module).lower()
        script_source = Path("scripts/report_intake_records.py").read_text(
            encoding="utf-8"
        ).lower()
        combined = helper_source + "\n" + script_source

        forbidden = [
            "pypdf",
            "pdfreader",
            "ocr",
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
            "from app.load_intake",
            "import app.load_intake",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, combined)


if __name__ == "__main__":
    unittest.main()
