import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_ratecon_load_source_line_diagnostics.py"
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_source_line_diagnostics"


class CreateRateconLoadSourceLineDiagnosticsTests(unittest.TestCase):
    def _output_dir(self, tmp_path: Path, name: str) -> Path:
        return tmp_path / ".local_outputs" / name

    def _run(self, tmp_path: Path, fixture: str, *extra_args: str) -> subprocess.CompletedProcess:
        fixture_dir = FIXTURES / fixture
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--eval-dir",
            str(fixture_dir / "eval"),
            "--audit",
            str(fixture_dir / "audit.jsonl"),
            "--output-dir",
            str(self._output_dir(tmp_path, fixture)),
            *extra_args,
        ]
        return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)

    def _summary(self, tmp_path: Path, fixture: str) -> dict:
        path = self._output_dir(tmp_path, fixture) / "load_source_line_diagnostics_summary.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _error_cases_text(self, tmp_path: Path, fixture: str) -> str:
        path = self._output_dir(tmp_path, fixture) / "load_source_line_error_cases.csv"
        return path.read_text(encoding="utf-8")

    def test_refuses_without_confirm_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(Path(tmp), "table_neighbor_wrong_cell")

        self.assertEqual(result.returncode, 1)
        self.assertIn("--confirm-private-local-run is required", result.stderr)

    def test_refuses_output_outside_local_outputs(self):
        fixture_dir = FIXTURES / "table_neighbor_wrong_cell"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--eval-dir",
                    str(fixture_dir / "eval"),
                    "--audit",
                    str(fixture_dir / "audit.jsonl"),
                    "--output-dir",
                    str(Path(tmp) / "outside"),
                    "--confirm-private-local-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output-dir must be inside .local_outputs", result.stderr)

    def test_diagnostic_fixtures_classify_expected_buckets(self):
        expected = {
            "table_neighbor_wrong_cell": "selected_table_neighbor_wrong_cell",
            "nearby_row_wrong_pair": "selected_nearby_row_wrong_pair",
            "footer_barcode_noise": "selected_footer_or_barcode_noise",
            "po_number_noise": "selected_po_number_noise",
            "pro_number_noise": "selected_pro_number_noise",
            "bol_number_noise": "selected_bol_number_noise",
            "gold_absent_from_candidates": "gold_not_in_candidates",
            "gold_present_not_selected": "gold_in_candidates_not_selected",
            "candidate_source_line_unavailable": "candidate_source_line_unavailable",
            "ambiguous_multiple_load_ids": "ambiguous_multiple_load_ids",
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for fixture, bucket in expected.items():
                with self.subTest(fixture=fixture):
                    result = self._run(tmp_path, fixture, "--confirm-private-local-run")
                    summary = self._summary(tmp_path, fixture)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual({bucket: 1}, summary["summary"]["diagnostic_bucket_counts"])
                    self.assertFalse(summary["summary"]["pdf_processing_attempted"])
                    self.assertFalse(summary["summary"]["ocr_attempted"])
                    self.assertFalse(summary["summary"]["google_called"])
                    self.assertFalse(summary["summary"]["model_or_cloud_called"])

    def test_outputs_redact_values_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(tmp_path, "table_neighbor_wrong_cell", "--confirm-private-local-run")
            text = self._error_cases_text(tmp_path, "table_neighbor_wrong_cell")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[redacted]", text)
        self.assertNotIn("LOAD12345", text)
        self.assertNotIn("REF33333", text)

    def test_include_private_values_local_only_requires_confirm_and_prints_fixture_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(
                tmp_path,
                "table_neighbor_wrong_cell",
                "--confirm-private-local-run",
                "--include-private-values-local-only",
            )
            text = self._error_cases_text(tmp_path, "table_neighbor_wrong_cell")
            summary = self._summary(tmp_path, "table_neighbor_wrong_cell")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("LOAD12345", text)
        self.assertIn("REF33333", text)
        self.assertTrue(summary["summary"]["private_values_included"])
        self.assertFalse(summary["summary"]["values_redacted"])

    def test_missing_detail_reports_detail_unavailable_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            eval_dir = tmp_path / "eval"
            eval_dir.mkdir()
            audit_path = tmp_path / "missing_audit.jsonl"
            output_dir = self._output_dir(tmp_path, "missing_detail")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--eval-dir",
                    str(eval_dir),
                    "--audit",
                    str(audit_path),
                    "--output-dir",
                    str(output_dir),
                    "--confirm-private-local-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            summary = json.loads(
                (output_dir / "load_source_line_diagnostics_summary.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual("detail_unavailable", summary["summary"]["detail_status"])
        self.assertEqual(
            {"evaluator_detail_unavailable": 1},
            summary["summary"]["diagnostic_bucket_counts"],
        )

    def test_outputs_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(tmp_path, "same_output_clean", "--confirm-private-local-run")
            output_dir = self._output_dir(tmp_path, "same_output_clean")
            existing = {
                name: (output_dir / name).exists()
                for name in (
                    "load_source_line_diagnostics_summary.json",
                    "load_source_line_diagnostics_report.md",
                    "load_source_line_error_cases.csv",
                    "load_source_line_pairing_diagnostics.csv",
                    "load_source_line_candidate_presence.csv",
                    "load_source_line_review_items.csv",
                )
            }

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(existing, {name: True for name in existing})

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
            hits.extend((path.as_posix(), marker) for marker in forbidden if marker in text)

        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
