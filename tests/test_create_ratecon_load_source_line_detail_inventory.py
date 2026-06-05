import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_ratecon_load_source_line_detail_inventory.py"
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_source_line_detail_inventory"


class CreateRateconLoadSourceLineDetailInventoryTests(unittest.TestCase):
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
            "--diagnostics-dir",
            str(fixture_dir / "diagnostics"),
            "--output-dir",
            str(self._output_dir(tmp_path, fixture)),
            *extra_args,
        ]
        return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)

    def _summary(self, tmp_path: Path, fixture: str) -> dict:
        path = self._output_dir(tmp_path, fixture) / "load_source_line_detail_inventory_summary.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _detail_rows(self, tmp_path: Path, fixture: str) -> list[dict[str, str]]:
        path = self._output_dir(tmp_path, fixture) / "load_source_line_detail_rows.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    def _expected(self, fixture: str) -> dict:
        return json.loads((FIXTURES / fixture / "expected_summary.json").read_text(encoding="utf-8"))

    def test_refuses_without_confirm_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(Path(tmp), "complete_source_detail")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--confirm-private-local-run is required", result.stderr)

    def test_refuses_output_outside_local_outputs(self):
        fixture_dir = FIXTURES / "complete_source_detail"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--eval-dir",
                    str(fixture_dir / "eval"),
                    "--audit",
                    str(fixture_dir / "audit.jsonl"),
                    "--diagnostics-dir",
                    str(fixture_dir / "diagnostics"),
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

    def test_fixture_detail_loss_buckets_are_pinned(self):
        expected_fixtures = (
            "complete_source_detail",
            "missing_page_line",
            "missing_candidate_id",
            "missing_pairing_method",
            "dropped_before_audit",
            "missing_evaluator_detail",
            "all_inputs_missing",
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for fixture in expected_fixtures:
                with self.subTest(fixture=fixture):
                    result = self._run(tmp_path, fixture, "--confirm-private-local-run")
                    payload = self._summary(tmp_path, fixture)
                    rows = self._detail_rows(tmp_path, fixture)
                    expected = self._expected(fixture)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(
                        expected["detail_input_status"],
                        payload["summary"]["detail_input_status"],
                    )
                    self.assertEqual(
                        expected["detail_loss_bucket"],
                        rows[0]["detail_loss_bucket"],
                    )
                    self.assertEqual(
                        expected["complete_source_detail_count"],
                        payload["summary"]["complete_source_detail_count"],
                    )
                    self.assertEqual(
                        expected["missing_page_line_count"],
                        payload["summary"]["missing_page_line_count"],
                    )
                    self.assertEqual(
                        expected["missing_source_count"],
                        payload["summary"]["missing_source_count"],
                    )
                    self.assertEqual(
                        expected["dropped_detail_count"],
                        payload["summary"]["dropped_detail_count"],
                    )
                    self.assertFalse(payload["summary"]["pdf_processing_attempted"])
                    self.assertFalse(payload["summary"]["ocr_attempted"])
                    self.assertFalse(payload["summary"]["google_called"])
                    self.assertFalse(payload["summary"]["model_or_cloud_called"])
                    self.assertFalse(payload["summary"]["private_measurement_run"])

    def test_default_output_redacts_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(tmp_path, "private_values_redacted", "--confirm-private-local-run")
            rows = self._detail_rows(tmp_path, "private_values_redacted")
            payload = self._summary(tmp_path, "private_values_redacted")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual("[redacted]", rows[0]["value_preview"])
        self.assertEqual("[redacted]", rows[0]["gold_value_preview"])
        self.assertNotIn("LOAD12345", json.dumps(payload))
        self.assertFalse(payload["summary"]["private_values_included"])
        self.assertTrue(payload["summary"]["values_redacted"])

    def test_private_values_only_appear_with_explicit_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            no_confirm = self._run(
                tmp_path,
                "private_values_redacted",
                "--include-private-values-local-only",
            )
            result = self._run(
                tmp_path,
                "private_values_redacted",
                "--confirm-private-local-run",
                "--include-private-values-local-only",
            )
            rows = self._detail_rows(tmp_path, "private_values_redacted")
            payload = self._summary(tmp_path, "private_values_redacted")

        self.assertNotEqual(no_confirm.returncode, 0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual("LOAD12345", rows[0]["value_preview"])
        self.assertEqual("LOAD12345", rows[0]["gold_value_preview"])
        self.assertTrue(payload["summary"]["private_values_included"])
        self.assertFalse(payload["summary"]["values_redacted"])

    def test_unknown_heavy_fixture_reports_missing_detail_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(
                tmp_path,
                "mixed_current_like_unknown_heavy",
                "--confirm-private-local-run",
            )
            payload = self._summary(tmp_path, "mixed_current_like_unknown_heavy")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(3, payload["summary"]["candidate_detail_row_count"])
        self.assertEqual(1, payload["summary"]["complete_source_detail_count"])
        self.assertEqual(2, payload["summary"]["missing_page_line_count"])
        self.assertEqual(2, payload["summary"]["unknown_caused_by_missing_detail_count"])

    def test_outputs_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(tmp_path, "complete_source_detail", "--confirm-private-local-run")
            output_dir = self._output_dir(tmp_path, "complete_source_detail")
            existing = {
                name: (output_dir / name).exists()
                for name in (
                    "load_source_line_detail_inventory_summary.json",
                    "load_source_line_detail_inventory_report.md",
                    "load_source_line_detail_rows.csv",
                    "load_source_line_detail_loss.csv",
                    "load_source_line_candidate_detail_coverage.csv",
                    "load_source_line_detail_review_items.csv",
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
