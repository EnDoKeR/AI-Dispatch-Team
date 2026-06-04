import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare_ratecon_private_selected_load_aggregates.py"
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_private_selected_load_aggregate_compare"


class CompareRateconPrivateSelectedLoadAggregatesTests(unittest.TestCase):
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
        path = self._output_dir(tmp_path, name) / "private_selected_load_aggregate_compare_summary.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_refuses_without_confirm_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(Path(tmp), "experiment_same")

        self.assertEqual(result.returncode, 1)
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
                "--fail-on-selected-load-regression",
            )
            summary = self._summary(tmp_path, "experiment_same")
            output_dir = self._output_dir(tmp_path, "experiment_same")
            existing_outputs = {
                filename: (output_dir / filename).exists()
                for filename in (
                    "private_selected_load_aggregate_compare_summary.json",
                    "private_selected_load_aggregate_compare_report.md",
                    "private_selected_load_field_metrics_delta.csv",
                    "private_selected_load_error_reason_delta.csv",
                    "private_selected_load_changed_documents.csv",
                    "private_selected_load_gate_result.csv",
                    "private_selected_load_review_items.csv",
                )
            }

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(summary["gate"]["passed"])
        self.assertEqual(summary["summary"]["selected_value_changed_count"], 0)
        self.assertEqual(existing_outputs, {name: True for name in existing_outputs})

    def test_wrong_count_regression_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(Path(tmp), "experiment_wrong_count_regression", "--confirm-private-local-run")

        self.assertEqual(result.returncode, 1)
        self.assertIn("gate_passed: False", result.stdout)
        self.assertIn("wrong_count_delta: 1", result.stdout)

    def test_high_confidence_wrong_regression_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(Path(tmp), "experiment_high_conf_wrong_regression", "--confirm-private-local-run")

        self.assertEqual(result.returncode, 1)
        self.assertIn("high_confidence_wrong_delta: 1", result.stdout)

    def test_table_neighbor_regression_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(Path(tmp), "experiment_table_neighbor_regression", "--confirm-private-local-run")

        self.assertEqual(result.returncode, 1)
        self.assertIn("selected_table_neighbor_wrong_cell_delta: 1", result.stdout)

    def test_missing_count_regression_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(Path(tmp), "experiment_missing_count_regression", "--confirm-private-local-run")

        self.assertEqual(result.returncode, 1)
        self.assertIn("missing_count_delta: 1", result.stdout)

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

    def test_private_values_unavailable_passes_aggregate_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(
                tmp_path,
                "experiment_private_values_unavailable",
                "--confirm-private-local-run",
                "--fail-on-selected-load-regression",
            )
            summary = self._summary(tmp_path, "experiment_private_values_unavailable")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            "private_values_unavailable",
            summary["summary"]["selected_value_comparison_status"],
        )
        self.assertTrue(summary["gate"]["passed"])

    def test_outputs_do_not_claim_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(tmp_path, "experiment_same", "--confirm-private-local-run")
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


if __name__ == "__main__":
    unittest.main()
