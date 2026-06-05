import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare_ratecon_load_generated_provenance_boundaries.py"
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_generated_provenance_later_boundary"


class CompareRateconLoadGeneratedProvenanceBoundariesTests(unittest.TestCase):
    def _output_dir(self, tmp_path: Path, fixture: str) -> Path:
        return tmp_path / ".local_outputs" / f"boundary_{fixture}"

    def _run(self, tmp_path: Path, fixture: str, *extra_args: str) -> subprocess.CompletedProcess:
        fixture_dir = FIXTURES / fixture
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--generated-resolver-sidecar-dir",
            str(fixture_dir),
            "--output-dir",
            str(self._output_dir(tmp_path, fixture)),
            *extra_args,
        ]
        return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)

    def _summary(self, tmp_path: Path, fixture: str) -> dict:
        return json.loads(
            (
                self._output_dir(tmp_path, fixture)
                / "load_generated_provenance_boundary_summary.json"
            ).read_text(encoding="utf-8")
        )

    def test_refuses_without_confirm_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(Path(tmp), "complete_roundtrip")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--confirm-local-audit-run is required", result.stderr)

    def test_refuses_output_outside_local_outputs(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--generated-resolver-sidecar-dir",
                str(FIXTURES / "complete_roundtrip"),
                "--output-dir",
                str(ROOT / "tmp_boundary_outside"),
                "--confirm-local-audit-run",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output-dir must be inside .local_outputs", result.stderr)

    def test_fixture_boundary_statuses_are_pinned(self):
        cases = {
            "generation_to_adapter_loss": "boundary_generation_to_adapter_loss",
            "adapter_to_dedupe_loss": "boundary_adapter_to_dedupe_loss",
            "dedupe_to_resolver_loss": "boundary_dedupe_to_resolver_loss",
            "resolver_to_audit_loss": "boundary_resolver_to_audit_loss",
            "audit_to_evaluator_loss": "boundary_audit_to_evaluator_loss",
            "evaluator_to_sidecar_loss": "boundary_evaluator_to_sidecar_loss",
            "complete_roundtrip": "boundary_no_loss_complete_roundtrip",
            "input_detail_missing": "boundary_input_detail_missing",
            "stage_unavailable": "boundary_stage_unavailable",
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for fixture, expected in cases.items():
                with self.subTest(fixture=fixture):
                    result = self._run(tmp_path, fixture, "--confirm-local-audit-run")
                    summary = self._summary(tmp_path, fixture)["summary"]

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(expected, summary["first_loss_boundary"])
                    self.assertFalse(summary["private_values_included"])
                    self.assertTrue(summary["private_values_redacted"])
                    self.assertFalse(summary["pdf_processing_attempted"])
                    self.assertFalse(summary["ocr_attempted"])
                    self.assertFalse(summary["google_called"])
                    self.assertFalse(summary["model_or_cloud_called"])

    def test_outputs_expected_files_and_redacted_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(tmp_path, "complete_roundtrip", "--confirm-local-audit-run")
            output_dir = self._output_dir(tmp_path, "complete_roundtrip")
            expected_files = (
                "load_generated_provenance_boundary_summary.json",
                "load_generated_provenance_boundary_report.md",
                "load_generated_provenance_boundary_rows.csv",
                "load_generated_provenance_boundary_loss_by_stage.csv",
                "load_generated_provenance_boundary_review_items.csv",
            )
            rows_text = (output_dir / "load_generated_provenance_boundary_rows.csv").read_text(
                encoding="utf-8"
            )
            file_results = {name: (output_dir / name).exists() for name in expected_files}

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(file_results, {name: True for name in expected_files})
        self.assertNotIn("LOAD12345", rows_text)
        self.assertIn("private_values_redacted", rows_text)

    def test_can_read_existing_generated_resolver_sidecar_shape_as_stricter_boundary(self):
        fixture_dir = ROOT / "tests" / "fixtures" / "ratecon_load_generated_resolver_provenance" / "full_roundtrip"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_dir = tmp_path / ".local_outputs" / "boundary_existing_sidecar"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--generated-resolver-sidecar-dir",
                    str(fixture_dir),
                    "--serialization-dir",
                    str(fixture_dir / "serialization"),
                    "--output-dir",
                    str(output_dir),
                    "--confirm-local-audit-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            summary = json.loads(
                (output_dir / "load_generated_provenance_boundary_summary.json").read_text(
                    encoding="utf-8"
                )
            )["summary"]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual("boundary_resolver_to_audit_loss", summary["first_loss_boundary"])
        self.assertEqual(0, summary["complete_roundtrip_count"])

    def test_committed_fixtures_are_sanitized(self):
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
