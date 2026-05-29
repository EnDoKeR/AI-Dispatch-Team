import inspect
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from app.market_intelligence import intake_scenario_runner
from app.market_intelligence.intake_scenario_runner import (
    build_intake_scenario_report,
    format_intake_scenario_report,
)
from tests.fixtures.synthetic_intake_records import SYNTHETIC_INTAKE_RECORDS


class TestIntakeScenarioRunner(unittest.TestCase):
    def test_runner_processes_all_fixtures(self):
        report = build_intake_scenario_report(SYNTHETIC_INTAKE_RECORDS)

        self.assertEqual(report["total_scenarios"], len(SYNTHETIC_INTAKE_RECORDS))
        self.assertEqual(len(report["scenario_results"]), len(SYNTHETIC_INTAKE_RECORDS))

    def test_clean_scenario_passes(self):
        report = build_intake_scenario_report(SYNTHETIC_INTAKE_RECORDS)
        clean = next(
            result
            for result in report["scenario_results"]
            if result["scenario_id"] == "clean_full_record"
        )

        self.assertTrue(clean["passed"])
        self.assertEqual(clean["status"], "READY_FOR_REVIEW")

    def test_missing_field_scenarios_report_expected_missing_fields(self):
        report = build_intake_scenario_report(SYNTHETIC_INTAKE_RECORDS)

        for result in report["scenario_results"]:
            with self.subTest(scenario=result["scenario_id"]):
                self.assertEqual(
                    result["missing_fields"],
                    result["expected_missing_fields"],
                )

    def test_needs_check_scenarios_report_expected_fields(self):
        report = build_intake_scenario_report(SYNTHETIC_INTAKE_RECORDS)

        for result in report["scenario_results"]:
            with self.subTest(scenario=result["scenario_id"]):
                self.assertEqual(
                    result["needs_check_fields"],
                    result["expected_needs_check_fields"],
                )

    def test_report_is_json_serializable(self):
        report = build_intake_scenario_report(SYNTHETIC_INTAKE_RECORDS)

        json.dumps(report)

    def test_formatted_report_includes_status_and_dry_run_warning(self):
        report = build_intake_scenario_report(SYNTHETIC_INTAKE_RECORDS)
        text = format_intake_scenario_report(report)

        self.assertIn("INTAKE SCENARIO DRY RUN", text)
        self.assertIn("clean_full_record", text)
        self.assertIn("Missing fields:", text)
        self.assertIn("Needs check fields:", text)
        self.assertIn("DRY RUN ONLY - synthetic intake scenarios only", text)

    def test_cli_exists_and_prints_dry_run_warning(self):
        script = Path("scripts/run_intake_scenarios.py")
        self.assertTrue(script.exists())

        from scripts import run_intake_scenarios

        output = io.StringIO()

        with redirect_stdout(output):
            result = run_intake_scenarios.main()

        text = output.getvalue()

        self.assertEqual(result, 0)
        self.assertIn("INTAKE SCENARIO DRY RUN", text)
        self.assertIn("DRY RUN ONLY - synthetic intake scenarios only", text)

    def test_runner_and_cli_do_not_import_forbidden_layers(self):
        helper_source = inspect.getsource(intake_scenario_runner)
        script_source = Path("scripts/run_intake_scenarios.py").read_text()
        combined = helper_source + "\n" + script_source

        forbidden = [
            "pypdf",
            "PdfReader",
            "gspread",
            "google.oauth",
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "event_logger",
            "scheduler",
            "threading",
            "googlemaps",
            "load_intake",
            "open(",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, combined)


if __name__ == "__main__":
    unittest.main()
