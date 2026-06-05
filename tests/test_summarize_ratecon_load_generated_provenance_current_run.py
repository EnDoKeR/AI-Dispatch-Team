import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "summarize_ratecon_load_generated_provenance_current_run.py"
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_generated_provenance_current_run"


class SummarizeRateconLoadGeneratedProvenanceCurrentRunTests(unittest.TestCase):
    def _output_dir(self, tmp_path: Path, fixture: str) -> Path:
        return tmp_path / ".local_outputs" / fixture

    def _run_fixture(self, tmp_path: Path, fixture: str) -> subprocess.CompletedProcess:
        fixture_dir = FIXTURES / fixture
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--generated-resolver-sidecar-dir",
                str(fixture_dir / "generated_resolver_sidecars"),
                "--output-dir",
                str(self._output_dir(tmp_path, fixture)),
                "--confirm-local-audit-run",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def _summary(self, tmp_path: Path, fixture: str) -> dict:
        return json.loads(
            (
                self._output_dir(tmp_path, fixture)
                / "load_generated_provenance_current_run_summary.json"
            ).read_text(encoding="utf-8")
        )

    def _expected_status(self, fixture: str) -> str:
        return json.loads(
            (FIXTURES / fixture / "expected_current_run_status.json").read_text(
                encoding="utf-8"
            )
        )["current_run_status"]

    def test_refuses_without_confirm_flag(self):
        fixture_dir = FIXTURES / "full_roundtrip_measurable"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--generated-resolver-sidecar-dir",
                    str(fixture_dir / "generated_resolver_sidecars"),
                    "--output-dir",
                    str(self._output_dir(Path(tmp), "no_confirm")),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertEqual(2, result.returncode)
        self.assertIn("--confirm-local-audit-run is required", result.stderr)

    def test_refuses_output_outside_local_outputs(self):
        fixture_dir = FIXTURES / "full_roundtrip_measurable"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--generated-resolver-sidecar-dir",
                    str(fixture_dir / "generated_resolver_sidecars"),
                    "--output-dir",
                    str(Path(tmp) / "outside"),
                    "--confirm-local-audit-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertEqual(2, result.returncode)
        self.assertIn("output-dir must be inside .local_outputs", result.stderr)

    def test_current_run_status_fixtures(self):
        fixtures = (
            "full_roundtrip_measurable",
            "partial_roundtrip_no_generated_rows",
            "generated_rows_absent",
            "generated_rows_present_missing_detail",
            "generated_rows_present_lost_later",
            "eval_audit_only_unmeasurable",
            "private_inputs_unavailable",
        )
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    result = self._run_fixture(tmp_path, fixture)
                    summary = self._summary(tmp_path, fixture)

                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(self._expected_status(fixture), summary["current_run_status"])

    def test_outputs_are_written_and_reports_redact_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_fixture(tmp_path, "full_roundtrip_measurable")
            output_dir = self._output_dir(tmp_path, "full_roundtrip_measurable")
            outputs = {
                filename: (output_dir / filename).exists()
                for filename in (
                    "load_generated_provenance_current_run_summary.json",
                    "load_generated_provenance_current_run_report.md",
                    "load_generated_provenance_current_run_gate.csv",
                    "load_generated_provenance_current_run_next_actions.csv",
                    "load_generated_provenance_current_run_known_debt.csv",
                )
            }
            report = (output_dir / "load_generated_provenance_current_run_report.md").read_text(
                encoding="utf-8"
            )
            summary = self._summary(tmp_path, "full_roundtrip_measurable")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(outputs, {name: True for name in outputs})
        self.assertTrue(summary["private_values_redacted"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["google_called"])
        self.assertFalse(summary["model_or_cloud_called"])
        for value in ("LOAD12345", "PO99999", "PRO77777", "BOL55555", "REF33333"):
            self.assertNotIn(value, report)

    def test_fixture_inputs_do_not_contain_private_markers(self):
        forbidden = (
            ".gold.json",
            "data/private_ratecons",
            "service account",
            "google token",
            "api_key",
        )
        for path in FIXTURES.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8").lower()
                for marker in forbidden:
                    self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
