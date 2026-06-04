import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare_ratecon_private_selected_rate_aggregates.py"
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_private_selected_rate_aggregate_compare"


class CompareRateconPrivateSelectedRateAggregatesTests(unittest.TestCase):
    def _output_dir(self, tmp_path: Path, name: str) -> Path:
        return tmp_path / ".local_outputs" / name

    def _run(self, tmp_path: Path, experiment: str, *extra_args: str) -> subprocess.CompletedProcess:
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--baseline-eval-dir",
            str(FIXTURES / "baseline"),
            "--experiment-eval-dir",
            str(FIXTURES / experiment),
            "--output-dir",
            str(self._output_dir(tmp_path, experiment)),
            *extra_args,
        ]
        return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)

    def _summary(self, tmp_path: Path, name: str) -> dict:
        path = (
            self._output_dir(tmp_path, name)
            / "private_selected_rate_aggregate_compare_summary.json"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_refuses_without_confirm_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(Path(tmp), "experiment_same")

        self.assertEqual(result.returncode, 2)
        self.assertIn("--confirm-private-local-run is required", result.stderr)

    def test_refuses_output_outside_local_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "not_local_outputs" / "compare"
            cmd = [
                sys.executable,
                str(SCRIPT),
                "--baseline-eval-dir",
                str(FIXTURES / "baseline"),
                "--experiment-eval-dir",
                str(FIXTURES / "experiment_same"),
                "--output-dir",
                str(output_dir),
                "--confirm-private-local-run",
            ]
            result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output-dir must be inside .local_outputs", result.stderr)

    def test_identical_outputs_pass_and_write_expected_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(
                tmp_path,
                "experiment_same",
                "--confirm-private-local-run",
                "--fail-on-selected-rate-regression",
            )
            summary = self._summary(tmp_path, "experiment_same")
            output_dir = self._output_dir(tmp_path, "experiment_same")
            existing_outputs = {
                filename: (output_dir / filename).exists()
                for filename in (
                    "private_selected_rate_aggregate_compare_summary.json",
                    "private_selected_rate_aggregate_compare_report.md",
                    "private_selected_rate_field_metrics_delta.csv",
                    "private_selected_rate_error_reason_delta.csv",
                    "private_selected_rate_changed_documents.csv",
                    "private_selected_rate_gate_result.csv",
                    "private_selected_rate_review_items.csv",
                )
            }

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(summary["gate"]["passed"])
        self.assertEqual(summary["summary"]["selected_value_changed_count"], 0)
        self.assertEqual(existing_outputs, {name: True for name in existing_outputs})

    def test_wrong_count_regression_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(
                Path(tmp),
                "experiment_regression",
                "--confirm-private-local-run",
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("gate_passed: False", result.stdout)
        self.assertIn("wrong_count_delta: 1", result.stdout)

    def test_high_confidence_wrong_regression_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(
                Path(tmp),
                "experiment_high_conf_wrong",
                "--confirm-private-local-run",
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("high_confidence_wrong_delta: 1", result.stdout)

    def test_selected_wrong_money_context_regression_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(
                Path(tmp),
                "experiment_wrong_money_context",
                "--confirm-private-local-run",
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("selected_wrong_money_context_delta: 1", result.stdout)

    def test_review_only_difference_passes_when_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(
                Path(tmp),
                "experiment_review_only",
                "--confirm-private-local-run",
                "--allow-review-only-differences",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("gate_passed: True", result.stdout)

    def test_selected_value_change_fails_with_private_value_compare(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(
                tmp_path,
                "experiment_selected_value_change",
                "--confirm-private-local-run",
                "--fail-on-selected-rate-regression",
            )
            summary = self._summary(tmp_path, "experiment_selected_value_change")
            changed_path = (
                self._output_dir(tmp_path, "experiment_selected_value_change")
                / "private_selected_rate_changed_documents.csv"
            )
            changed_text = changed_path.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 1)
        self.assertEqual(summary["summary"]["selected_value_changed_count"], 1)
        self.assertIn("[redacted]", changed_text)
        self.assertNotIn("3200.00", changed_text)

    def test_private_values_can_be_included_only_with_local_confirm(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            no_confirm = self._run(
                tmp_path,
                "experiment_selected_value_change",
                "--include-private-values-local-only",
            )
            confirmed = self._run(
                tmp_path,
                "experiment_selected_value_change",
                "--confirm-private-local-run",
                "--include-private-values-local-only",
                "--fail-on-selected-rate-regression",
            )
            changed_path = (
                self._output_dir(tmp_path, "experiment_selected_value_change")
                / "private_selected_rate_changed_documents.csv"
            )
            changed_text = changed_path.read_text(encoding="utf-8")

        self.assertEqual(no_confirm.returncode, 2)
        self.assertEqual(confirmed.returncode, 1)
        self.assertIn("3200.00", changed_text)

    def test_private_values_unavailable_passes_aggregate_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(
                tmp_path,
                "experiment_private_values_unavailable",
                "--confirm-private-local-run",
                "--fail-on-selected-rate-regression",
            )
            summary = self._summary(tmp_path, "experiment_private_values_unavailable")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            summary["summary"]["selected_value_comparison_status"],
            "private_values_unavailable",
        )
        self.assertTrue(summary["gate"]["passed"])

    def test_requires_private_values_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(
                Path(tmp),
                "experiment_private_values_unavailable",
                "--confirm-private-local-run",
                "--require-private-selected-values-local-only",
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("selected_value_comparison_status: private_values_unavailable", result.stdout)

    def test_outputs_do_not_claim_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(
                tmp_path,
                "experiment_same",
                "--confirm-private-local-run",
            )
            summary = self._summary(tmp_path, "experiment_same")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(summary["gate"]["pdf_processing_attempted"])
        self.assertFalse(summary["gate"]["ocr_attempted"])
        self.assertFalse(summary["gate"]["google_called"])
        self.assertFalse(summary["gate"]["model_or_cloud_called"])
        self.assertFalse(summary["gate"]["private_measurement_run"])

    def test_committed_fixtures_are_sanitized(self):
        forbidden = (
            "data/private_ratecons",
            ".gold.json",
            "api_key",
            "secret",
            "service account",
            "google token",
            "raw extracted",
        )
        hits = []
        for path in FIXTURES.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8").lower()
            hits.extend((str(path), marker) for marker in forbidden if marker in text)

        self.assertEqual(hits, [])

    def test_gate_result_csv_reports_failure_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._run(
                tmp_path,
                "experiment_regression",
                "--confirm-private-local-run",
            )
            gate_csv = (
                self._output_dir(tmp_path, "experiment_regression")
                / "private_selected_rate_gate_result.csv"
            )
            with gate_csv.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

        failed = [row for row in rows if row["check"] == "wrong_count_not_increased"]
        self.assertEqual(failed[0]["passed"], "False")


if __name__ == "__main__":
    unittest.main()
