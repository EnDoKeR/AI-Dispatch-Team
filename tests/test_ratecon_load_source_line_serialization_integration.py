import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_ratecon_load_source_line_serialization.py"
DETAIL_SCRIPT = ROOT / "scripts" / "create_ratecon_load_source_line_detail_inventory.py"
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_source_line_serialization"
DETAIL_FIXTURE = ROOT / "tests" / "fixtures" / "ratecon_load_source_line_detail_inventory" / "complete_source_detail"


class RateconLoadSourceLineSerializationIntegrationTests(unittest.TestCase):
    def _serialization_output_dir(self, tmp_path: Path, fixture: str) -> Path:
        return tmp_path / ".local_outputs" / f"serialization_{fixture}"

    def _detail_output_dir(self, tmp_path: Path, name: str) -> Path:
        return tmp_path / ".local_outputs" / f"detail_{name}"

    def _run_serialization(
        self,
        tmp_path: Path,
        fixture: str,
        *extra_args: str,
    ) -> subprocess.CompletedProcess:
        fixture_dir = FIXTURES / fixture
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--generated-candidates",
            str(fixture_dir / "generated_candidates.csv"),
            "--resolver-trace",
            str(fixture_dir / "resolver_trace.csv"),
            "--audit",
            str(fixture_dir / "audit.jsonl"),
            "--eval-dir",
            str(fixture_dir / "eval"),
            "--output-dir",
            str(self._serialization_output_dir(tmp_path, fixture)),
            *extra_args,
        ]
        return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)

    def _summary(self, tmp_path: Path, fixture: str) -> dict:
        path = self._serialization_output_dir(tmp_path, fixture) / "load_source_line_serialization_summary.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _rows(self, tmp_path: Path, fixture: str) -> list[dict[str, str]]:
        path = self._serialization_output_dir(tmp_path, fixture) / "load_source_line_serialization_rows.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    def _expected(self, fixture: str) -> dict:
        return json.loads((FIXTURES / fixture / "expected_summary.json").read_text(encoding="utf-8"))

    def test_refuses_without_confirm_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run_serialization(Path(tmp), "complete_detail_roundtrip")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--confirm-private-local-run is required", result.stderr)

    def test_refuses_output_outside_local_outputs(self):
        fixture_dir = FIXTURES / "complete_detail_roundtrip"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--generated-candidates",
                    str(fixture_dir / "generated_candidates.csv"),
                    "--resolver-trace",
                    str(fixture_dir / "resolver_trace.csv"),
                    "--audit",
                    str(fixture_dir / "audit.jsonl"),
                    "--eval-dir",
                    str(fixture_dir / "eval"),
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

    def test_serialization_loss_fixture_buckets_are_pinned(self):
        fixtures = (
            "complete_detail_roundtrip",
            "lost_in_candidate_adapter",
            "lost_in_dedupe",
            "lost_in_resolver_trace",
            "lost_in_shadow_audit",
            "lost_in_gold_evaluator",
            "missing_at_generation",
            "current_like_no_complete_detail",
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for fixture in fixtures:
                with self.subTest(fixture=fixture):
                    result = self._run_serialization(
                        tmp_path,
                        fixture,
                        "--confirm-private-local-run",
                    )
                    payload = self._summary(tmp_path, fixture)
                    row = self._rows(tmp_path, fixture)[0]
                    expected = self._expected(fixture)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(
                        expected["serialization_loss_bucket"],
                        row["serialization_loss_bucket"],
                    )
                    self.assertEqual(
                        expected["complete_detail_serialized_count"],
                        payload["summary"]["complete_detail_serialized_count"],
                    )
                    self.assertEqual(
                        expected["missing_at_generation_count"],
                        payload["summary"]["missing_at_generation_count"],
                    )
                    self.assertEqual(
                        expected["lost_after_generation_count"],
                        payload["summary"]["lost_after_generation_count"],
                    )
                    self.assertFalse(payload["summary"]["pdf_processing_attempted"])
                    self.assertFalse(payload["summary"]["ocr_attempted"])
                    self.assertFalse(payload["summary"]["google_called"])
                    self.assertFalse(payload["summary"]["model_or_cloud_called"])
                    self.assertFalse(payload["summary"]["private_measurement_run"])

    def test_values_are_redacted_by_default_and_explicit_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run_serialization(
                tmp_path,
                "private_values_redacted",
                "--confirm-private-local-run",
            )
            rows = self._rows(tmp_path, "private_values_redacted")
            payload = self._summary(tmp_path, "private_values_redacted")
            included = self._run_serialization(
                tmp_path,
                "private_values_redacted",
                "--confirm-private-local-run",
                "--include-private-values-local-only",
            )
            included_rows = self._rows(tmp_path, "private_values_redacted")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual("[redacted]", rows[0]["value_preview"])
        self.assertNotIn("LOAD82345", json.dumps(payload))
        self.assertEqual(included.returncode, 0, included.stderr)
        self.assertEqual("LOAD82345", included_rows[0]["value_preview"])

    def test_detail_inventory_can_consume_serialization_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            serialization_result = self._run_serialization(
                tmp_path,
                "complete_detail_roundtrip",
                "--confirm-private-local-run",
            )
            serialization_dir = self._serialization_output_dir(
                tmp_path,
                "complete_detail_roundtrip",
            )
            output_dir = self._detail_output_dir(tmp_path, "with_serialization")
            detail_result = subprocess.run(
                [
                    sys.executable,
                    str(DETAIL_SCRIPT),
                    "--eval-dir",
                    str(DETAIL_FIXTURE / "eval"),
                    "--audit",
                    str(DETAIL_FIXTURE / "audit.jsonl"),
                    "--diagnostics-dir",
                    str(DETAIL_FIXTURE / "diagnostics"),
                    "--serialization-dir",
                    str(serialization_dir),
                    "--output-dir",
                    str(output_dir),
                    "--confirm-private-local-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            payload = json.loads(
                (output_dir / "load_source_line_detail_inventory_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            with (output_dir / "load_source_line_detail_rows.csv").open(
                "r",
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = [dict(row) for row in csv.DictReader(handle)]

        self.assertEqual(serialization_result.returncode, 0, serialization_result.stderr)
        self.assertEqual(detail_result.returncode, 0, detail_result.stderr)
        self.assertEqual("present", payload["summary"]["serialization_sidecar_status"])
        self.assertEqual(1, payload["summary"]["serialization_complete_detail_count"])
        self.assertEqual("complete_detail_serialized", rows[0]["serialization_loss_stage"])
        self.assertEqual("complete", rows[0]["source_detail_roundtrip_status"])

    def test_committed_serialization_fixtures_are_sanitized(self):
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
