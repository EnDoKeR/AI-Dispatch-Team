import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers.ratecon_selected_rate_regression import (
    assert_no_private_fixture_values,
    load_selected_rate_cases,
    run_selected_rate_case,
    run_selected_rate_cases,
)


root = Path(__file__).resolve().parents[1]


class RateconSelectedRateRegressionHarnessTests(unittest.TestCase):
    def setUp(self):
        self.cases = load_selected_rate_cases()

    def test_fixture_groups_are_complete_and_sanitized(self):
        case_ids = {case["id"] for case in self.cases}
        self.assertEqual(
            {
                "strong_total_only",
                "total_plus_accessorial_noise",
                "line_haul_plus_total",
                "line_items_without_explicit_total",
                "total_with_fee_penalty_section",
                "quick_pay_and_billing_page_only",
                "estimated_rate_to_truck",
                "pay_capacity_total",
                "line_haul_accessorial_breakout",
                "tracking_hold_negative_adjustment",
                "per_unit_rate_breakout",
                "carrier_freight_pay_blank_total",
            },
            case_ids,
        )
        assert_no_private_fixture_values(self.cases)
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(case.get("candidates"))
                for candidate in case["candidates"]:
                    self.assertNotEqual("ocr", candidate.get("source"))
                    self.assertNotIn(".pdf", str(candidate).lower())

    def test_every_fixture_pins_current_selected_rate_output(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                actual = run_selected_rate_case(case)
                expected = dict(case["expected"])
                expected["case_id"] = case["id"]
                expected["known_debt"] = bool(case.get("known_debt"))
                self.assertEqual(expected, actual)

    def test_known_debt_cases_are_explicitly_labeled(self):
        known_debt = [case for case in self.cases if case.get("known_debt")]
        self.assertEqual(
            [
                "line_items_without_explicit_total",
                "pay_capacity_total",
                "line_haul_accessorial_breakout",
                "carrier_freight_pay_blank_total",
            ],
            [case["id"] for case in known_debt],
        )
        for case in known_debt:
            with self.subTest(case=case["id"]):
                self.assertTrue(case.get("debt_note"))

    def test_noise_and_fee_candidates_do_not_replace_explicit_totals(self):
        results = {result["case_id"]: result for result in run_selected_rate_cases(self.cases)}
        self.assertEqual(
            "2600.00",
            results["total_plus_accessorial_noise"]["selected_value"],
        )
        self.assertEqual(
            "2600.00",
            results["total_with_fee_penalty_section"]["selected_value"],
        )
        self.assertEqual(
            "2400.00",
            results["tracking_hold_negative_adjustment"]["selected_value"],
        )
        self.assertEqual(
            "safe",
            results["total_plus_accessorial_noise"]["selected_rate_safety"],
        )
        self.assertFalse(results["total_with_fee_penalty_section"]["needs_review"])

    def test_missing_or_no_total_behavior_is_pinned(self):
        results = {result["case_id"]: result for result in run_selected_rate_cases(self.cases)}
        self.assertEqual("", results["quick_pay_and_billing_page_only"]["selected_value"])
        self.assertEqual(
            ["MISSING_CRITICAL_FIELD"],
            results["quick_pay_and_billing_page_only"]["review_reasons"],
        )
        self.assertEqual(
            "3150.00",
            results["line_items_without_explicit_total"]["selected_value"],
        )
        self.assertEqual(
            ["LOW_CONFIDENCE_CRITICAL_FIELD"],
            results["line_items_without_explicit_total"]["review_reasons"],
        )

    def test_snapshot_script_refuses_without_confirm_flag(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / ".local_outputs" / "selected_rate"
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_ratecon_selected_rate_regression_snapshot.py",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("--confirm-local-audit-run is required", completed.stderr)

    def test_snapshot_script_refuses_output_outside_local_outputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "selected_rate"
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_ratecon_selected_rate_regression_snapshot.py",
                    "--output-dir",
                    str(output_dir),
                    "--confirm-local-audit-run",
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("output-dir must be inside .local_outputs", completed.stderr)

    def test_snapshot_script_writes_sanitized_outputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / ".local_outputs" / "selected_rate"
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_ratecon_selected_rate_regression_snapshot.py",
                    "--output-dir",
                    str(output_dir),
                    "--confirm-local-audit-run",
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual("", completed.stderr)
            self.assertEqual(0, completed.returncode)
            self.assertTrue((output_dir / "selected_rate_regression_snapshot.json").exists())
            self.assertTrue((output_dir / "selected_rate_regression_snapshot.md").exists())
            self.assertTrue((output_dir / "selected_rate_regression_cases.csv").exists())
            payload = (output_dir / "selected_rate_regression_snapshot.json").read_text(
                encoding="utf-8"
            )
        self.assertIn('"case_count": 12', payload)
        self.assertNotIn("private_ratecons", payload)
        self.assertNotIn(".pdf", payload.lower())


if __name__ == "__main__":
    unittest.main()
