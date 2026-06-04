import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "summarize_ratecon_selected_rate_closeout.py"
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_selected_rate_closeout"


class SummarizeRateconSelectedRateCloseoutTests(unittest.TestCase):
    def _output_dir(self, tmp_path: Path, name: str) -> Path:
        return tmp_path / ".local_outputs" / name

    def _run_fixture(self, tmp_path: Path, fixture: str) -> subprocess.CompletedProcess:
        fixture_dir = FIXTURES / fixture
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--selected-rate-snapshot-dir",
            str(fixture_dir / "selected_rate_snapshot"),
            "--aggregate-gate-dir",
            str(fixture_dir / "aggregate_gate"),
            "--rate-money-audit-dir",
            str(fixture_dir / "rate_money_audit"),
            "--output-dir",
            str(self._output_dir(tmp_path, fixture)),
            "--confirm-local-audit-run",
        ]
        return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)

    def _summary(self, tmp_path: Path, fixture: str) -> dict:
        return json.loads(
            (
                self._output_dir(tmp_path, fixture)
                / "selected_rate_closeout_summary.json"
            ).read_text(encoding="utf-8")
        )

    def _expected_status(self, fixture: str) -> str:
        return json.loads(
            (FIXTURES / fixture / "expected_closeout_status.json").read_text(
                encoding="utf-8"
            )
        )["closeout_status"]

    def test_refuses_without_confirm_flag(self):
        fixture_dir = FIXTURES / "complete_pass"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--selected-rate-snapshot-dir",
                    str(fixture_dir / "selected_rate_snapshot"),
                    "--aggregate-gate-dir",
                    str(fixture_dir / "aggregate_gate"),
                    "--rate-money-audit-dir",
                    str(fixture_dir / "rate_money_audit"),
                    "--output-dir",
                    str(self._output_dir(Path(tmp), "no_confirm")),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--confirm-local-audit-run is required", result.stderr)

    def test_refuses_output_outside_local_outputs(self):
        fixture_dir = FIXTURES / "complete_pass"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--selected-rate-snapshot-dir",
                    str(fixture_dir / "selected_rate_snapshot"),
                    "--aggregate-gate-dir",
                    str(fixture_dir / "aggregate_gate"),
                    "--rate-money-audit-dir",
                    str(fixture_dir / "rate_money_audit"),
                    "--output-dir",
                    str(Path(tmp) / "not_local_outputs"),
                    "--confirm-local-audit-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output-dir must be inside .local_outputs", result.stderr)

    def test_complete_pass_fixture_returns_behavior_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "complete_pass")
            summary = self._summary(tmp_path, "complete_pass")
            output_dir = self._output_dir(tmp_path, "complete_pass")
            outputs = {
                filename: (output_dir / filename).exists()
                for filename in (
                    "selected_rate_closeout_summary.json",
                    "selected_rate_closeout_report.md",
                    "selected_rate_closeout_success_criteria.csv",
                    "selected_rate_closeout_known_debt.csv",
                    "selected_rate_closeout_gate_inventory.csv",
                    "selected_rate_closeout_next_actions.csv",
                )
            }

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._expected_status("complete_pass"), summary["closeout_status"])
        self.assertEqual(outputs, {name: True for name in outputs})
        self.assertTrue(all(row["passed"] for row in summary["success_criteria"]))

    def test_known_debt_fixture_returns_known_debt_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "known_debt_only")
            summary = self._summary(tmp_path, "known_debt_only")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._expected_status("known_debt_only"), summary["closeout_status"])
        self.assertEqual(1, summary["selected_rate_snapshot"]["known_debt_count"])
        self.assertEqual("sanitized_known_debt_line_item", summary["known_debt"][0]["case_id"])

    def test_missing_optional_private_baseline_does_not_fail_required_closeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "missing_optional_private_baseline")
            summary = self._summary(tmp_path, "missing_optional_private_baseline")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._expected_status("missing_optional_private_baseline"),
            summary["closeout_status"],
        )
        self.assertEqual(
            "skipped_local_inputs_unavailable",
            summary["private_full_corpus_baseline_status"],
        )

    def test_missing_required_aggregate_gate_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "incomplete_required_gate")
            summary = self._summary(tmp_path, "incomplete_required_gate")

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            self._expected_status("incomplete_required_gate"),
            summary["closeout_status"],
        )

    def test_gate_failure_fixture_fails_closeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "gate_failure")
            summary = self._summary(tmp_path, "gate_failure")

        self.assertEqual(result.returncode, 1)
        self.assertEqual(self._expected_status("gate_failure"), summary["closeout_status"])
        self.assertFalse(summary["aggregate_gate"]["gate_passed"])

    def test_report_redacts_private_values_and_reports_no_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "complete_pass")
            output_dir = self._output_dir(tmp_path, "complete_pass")
            report = (output_dir / "selected_rate_closeout_report.md").read_text(
                encoding="utf-8"
            )
            summary = self._summary(tmp_path, "complete_pass")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("private_values_redacted: True", report)
        self.assertNotIn("3200.00", report)
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["google_called"])
        self.assertFalse(summary["model_or_cloud_called"])
        self.assertFalse(summary["private_measurement_run"])

    def test_committed_closeout_fixtures_are_sanitized(self):
        forbidden = (
            "data/private_ratecons",
            ".gold.json",
            "api_key",
            "secret",
            "service account",
            "google token",
            "raw extracted",
            "private pdf",
        )
        hits = []
        for path in FIXTURES.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8").lower()
            hits.extend((str(path), marker) for marker in forbidden if marker in text)

        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
