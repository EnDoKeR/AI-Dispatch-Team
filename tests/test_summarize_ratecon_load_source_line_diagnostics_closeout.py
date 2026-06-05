import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "summarize_ratecon_load_source_line_diagnostics_closeout.py"
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_source_line_closeout"


class SummarizeRateconLoadSourceLineDiagnosticsCloseoutTests(unittest.TestCase):
    def _output_dir(self, tmp_path: Path, name: str) -> Path:
        return tmp_path / ".local_outputs" / name

    def _run_fixture(
        self,
        tmp_path: Path,
        fixture: str,
        *extra_args: str,
    ) -> subprocess.CompletedProcess:
        fixture_dir = FIXTURES / fixture
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--diagnostics-dir",
            str(fixture_dir / "diagnostics"),
            "--ownership-audit-dir",
            str(fixture_dir / "ownership_audit"),
            "--source-line-audit-dir",
            str(fixture_dir / "source_line_audit"),
            "--aggregate-gate-dir",
            str(fixture_dir / "aggregate_gate"),
            "--output-dir",
            str(self._output_dir(tmp_path, fixture)),
            "--confirm-local-audit-run",
            *extra_args,
        ]
        return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)

    def _summary(self, tmp_path: Path, fixture: str) -> dict:
        return json.loads(
            (
                self._output_dir(tmp_path, fixture)
                / "load_source_line_closeout_summary.json"
            ).read_text(encoding="utf-8")
        )

    def _expected_status(self, fixture: str) -> str:
        return json.loads(
            (FIXTURES / fixture / "expected_closeout_status.json").read_text(
                encoding="utf-8"
            )
        )["closeout_status"]

    def test_refuses_without_confirm_flag(self):
        fixture_dir = FIXTURES / "complete_actionable"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--diagnostics-dir",
                    str(fixture_dir / "diagnostics"),
                    "--ownership-audit-dir",
                    str(fixture_dir / "ownership_audit"),
                    "--source-line-audit-dir",
                    str(fixture_dir / "source_line_audit"),
                    "--aggregate-gate-dir",
                    str(fixture_dir / "aggregate_gate"),
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
        fixture_dir = FIXTURES / "complete_actionable"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--diagnostics-dir",
                    str(fixture_dir / "diagnostics"),
                    "--ownership-audit-dir",
                    str(fixture_dir / "ownership_audit"),
                    "--source-line-audit-dir",
                    str(fixture_dir / "source_line_audit"),
                    "--aggregate-gate-dir",
                    str(fixture_dir / "aggregate_gate"),
                    "--output-dir",
                    str(Path(tmp) / "outside"),
                    "--confirm-local-audit-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output-dir must be inside .local_outputs", result.stderr)

    def test_complete_actionable_fixture_returns_actionable_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "complete_actionable")
            summary = self._summary(tmp_path, "complete_actionable")
            output_dir = self._output_dir(tmp_path, "complete_actionable")
            outputs = {
                filename: (output_dir / filename).exists()
                for filename in (
                    "load_source_line_closeout_summary.json",
                    "load_source_line_closeout_report.md",
                    "load_source_line_closeout_success_criteria.csv",
                    "load_source_line_closeout_known_debt.csv",
                    "load_source_line_closeout_gate_inventory.csv",
                    "load_source_line_closeout_readiness.csv",
                    "load_source_line_closeout_next_actions.csv",
                )
            }

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._expected_status("complete_actionable"),
            summary["closeout_status"],
        )
        self.assertEqual(outputs, {name: True for name in outputs})
        self.assertTrue(summary["aggregate_gate"]["gate_passed"])

    def test_mostly_unknown_fixture_returns_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "mostly_unknown_not_ready")
            summary = self._summary(tmp_path, "mostly_unknown_not_ready")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._expected_status("mostly_unknown_not_ready"),
            summary["closeout_status"],
        )
        self.assertGreaterEqual(summary["diagnostics"]["unknown_ratio"], 0.5)

    def test_detail_unavailable_fixture_returns_incomplete_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "detail_unavailable_not_ready")
            summary = self._summary(tmp_path, "detail_unavailable_not_ready")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._expected_status("detail_unavailable_not_ready"),
            summary["closeout_status"],
        )
        self.assertGreaterEqual(
            summary["diagnostics"]["source_line_unavailable_ratio"],
            0.5,
        )

    def test_missing_required_gate_fails_closeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "gate_missing_incomplete")
            summary = self._summary(tmp_path, "gate_missing_incomplete")

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            self._expected_status("gate_missing_incomplete"),
            summary["closeout_status"],
        )

    def test_known_debt_only_fixture_returns_known_debt_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "known_debt_only")
            summary = self._summary(tmp_path, "known_debt_only")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._expected_status("known_debt_only"),
            summary["closeout_status"],
        )
        self.assertEqual(3, summary["diagnostics"]["known_debt_count"])

    def test_private_baseline_skipped_does_not_fail_optional_closeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "private_baseline_skipped")
            summary = self._summary(tmp_path, "private_baseline_skipped")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._expected_status("private_baseline_skipped"),
            summary["closeout_status"],
        )
        self.assertEqual("missing", summary["diagnostics"]["status"])

    def test_report_redacts_private_values_and_reports_no_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "complete_actionable")
            output_dir = self._output_dir(tmp_path, "complete_actionable")
            report = (output_dir / "load_source_line_closeout_report.md").read_text(
                encoding="utf-8"
            )
            summary = self._summary(tmp_path, "complete_actionable")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("private_values_redacted: True", report)
        self.assertNotIn("LOAD12345", report)
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["google_called"])
        self.assertFalse(summary["model_or_cloud_called"])
        self.assertFalse(summary["private_measurement_run"])

    def test_missing_optional_detail_inventory_preserves_current_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(
                tmp_path,
                "complete_actionable",
                "--detail-inventory-dir",
                str(tmp_path / "missing_detail_inventory"),
            )
            summary = self._summary(tmp_path, "complete_actionable")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._expected_status("complete_actionable"),
            summary["closeout_status"],
        )
        self.assertEqual("skipped_missing_optional_dir", summary["detail_inventory"]["status"])

    def test_detail_inventory_with_dominant_missing_detail_blocks_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            detail_dir = tmp_path / "detail_inventory"
            detail_dir.mkdir()
            (detail_dir / "load_source_line_detail_inventory_summary.json").write_text(
                json.dumps(
                    {
                        "summary": {
                            "detail_input_status": "available",
                            "candidate_detail_row_count": 4,
                            "complete_source_detail_count": 1,
                            "missing_page_line_count": 3,
                            "missing_source_count": 0,
                            "dropped_detail_count": 0,
                            "unknown_caused_by_missing_detail_count": 3,
                            "private_values_included": False,
                            "values_redacted": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = self._run_fixture(
                tmp_path,
                "complete_actionable",
                "--detail-inventory-dir",
                str(detail_dir),
            )
            summary = self._summary(tmp_path, "complete_actionable")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            "load_source_line_diagnostics_incomplete_detail_unavailable",
            summary["closeout_status"],
        )
        self.assertEqual("present", summary["detail_inventory"]["status"])
        self.assertEqual(3, summary["detail_inventory"]["missing_page_line_count"])
        self.assertTrue(
            any(
                row["readiness_check"] == "detail_inventory_not_dominated_by_missing_detail"
                and not row["passed"]
                and row["blocking"]
                for row in summary["readiness"]
            )
        )

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
            hits.extend((path.as_posix(), marker) for marker in forbidden if marker in text)

        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
