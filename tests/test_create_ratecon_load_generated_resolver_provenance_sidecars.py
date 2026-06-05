import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_ratecon_load_generated_resolver_provenance_sidecars.py"
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_generated_resolver_provenance"


class CreateRateconLoadGeneratedResolverProvenanceSidecarsTests(unittest.TestCase):
    def _output_dir(self, tmp_path: Path, fixture: str) -> Path:
        return tmp_path / ".local_outputs" / f"generated_resolver_{fixture}"

    def _run(self, tmp_path: Path, fixture: str, *extra_args: str) -> subprocess.CompletedProcess:
        fixture_dir = FIXTURES / fixture
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--audit",
            str(fixture_dir / "audit.jsonl"),
            "--legacy-output-dir",
            str(fixture_dir),
            "--serialization-dir",
            str(fixture_dir / "serialization"),
            "--generated-candidates",
            str(fixture_dir / "generated_candidates.csv"),
            "--adapter-input",
            str(fixture_dir / "adapter_input.csv"),
            "--adapter-output",
            str(fixture_dir / "adapter_output.csv"),
            "--dedupe-input",
            str(fixture_dir / "dedupe_input.csv"),
            "--dedupe-output",
            str(fixture_dir / "dedupe_output.csv"),
            "--resolver-trace",
            str(fixture_dir / "resolver_trace.csv"),
            "--output-dir",
            str(self._output_dir(tmp_path, fixture)),
            *extra_args,
        ]
        return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)

    def _summary(self, tmp_path: Path, fixture: str) -> dict:
        return json.loads(
            (
                self._output_dir(tmp_path, fixture)
                / "load_generated_resolver_provenance_summary.json"
            ).read_text(encoding="utf-8")
        )

    def _loss_rows(self, tmp_path: Path, fixture: str) -> list[dict[str, str]]:
        with (
            self._output_dir(tmp_path, fixture) / "load_provenance_loss_by_stage.csv"
        ).open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    def _expected(self, fixture: str) -> dict:
        return json.loads((FIXTURES / fixture / "expected_summary.json").read_text(encoding="utf-8"))

    def test_refuses_without_confirm_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(Path(tmp), "full_roundtrip")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--confirm-private-local-run is required", result.stderr)

    def test_refuses_output_outside_local_outputs(self):
        fixture_dir = FIXTURES / "full_roundtrip"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--legacy-output-dir",
                    str(fixture_dir),
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

    def test_fixture_stage_loss_buckets_are_pinned(self):
        fixtures = (
            "full_roundtrip",
            "generation_missing_detail",
            "lost_between_generation_and_adapter",
            "lost_between_adapter_and_dedupe",
            "lost_between_dedupe_and_resolver",
            "resolver_trace_unavailable",
            "dedupe_lineage_unavailable",
            "current_like_eval_audit_only_unmeasurable",
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for fixture in fixtures:
                with self.subTest(fixture=fixture):
                    result = self._run(tmp_path, fixture, "--confirm-private-local-run")
                    payload = self._summary(tmp_path, fixture)
                    rows = self._loss_rows(tmp_path, fixture)
                    expected = self._expected(fixture)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(expected["stage_loss_bucket"], rows[0]["stage_loss_bucket"])
                    self.assertEqual(
                        expected["current_artifacts_status"],
                        payload["summary"]["current_artifacts_status"],
                    )
                    self.assertEqual(
                        expected["complete_roundtrip_count"],
                        payload["summary"]["complete_roundtrip_count"],
                    )
                    self.assertEqual(
                        expected["generated_candidate_count"],
                        payload["summary"]["generated_candidate_count"],
                    )
                    self.assertEqual(
                        expected["resolver_visible_candidate_count"],
                        payload["summary"]["resolver_visible_candidate_count"],
                    )
                    self.assertFalse(payload["summary"]["pdf_processing_attempted"])
                    self.assertFalse(payload["summary"]["ocr_attempted"])
                    self.assertFalse(payload["summary"]["google_called"])
                    self.assertFalse(payload["summary"]["model_or_cloud_called"])
                    self.assertFalse(payload["summary"]["private_measurement_run"])

    def test_outputs_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(tmp_path, "full_roundtrip", "--confirm-private-local-run")
            output_dir = self._output_dir(tmp_path, "full_roundtrip")
            files = {
                name: (output_dir / name).exists()
                for name in (
                    "load_generated_resolver_provenance_summary.json",
                    "load_generated_resolver_provenance_report.md",
                    "load_generated_candidates.csv",
                    "load_adapter_roundtrip_rows.csv",
                    "load_resolver_visible_candidates.csv",
                    "load_dedupe_lineage_rows.csv",
                    "load_provenance_loss_by_stage.csv",
                    "load_generated_resolver_review_items.csv",
                )
            }

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(files, {name: True for name in files})

    def test_values_redacted_by_default_and_explicit_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(
                tmp_path,
                "private_values_redacted",
                "--confirm-private-local-run",
            )
            summary = self._summary(tmp_path, "private_values_redacted")
            generated_rows = (
                self._output_dir(tmp_path, "private_values_redacted")
                / "load_generated_candidates.csv"
            ).read_text(encoding="utf-8")
            included = self._run(
                tmp_path,
                "private_values_redacted",
                "--confirm-private-local-run",
                "--include-private-values-local-only",
            )
            included_rows = (
                self._output_dir(tmp_path, "private_values_redacted")
                / "load_generated_candidates.csv"
            ).read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("LOAD82345", json.dumps(summary))
        self.assertIn("[redacted]", generated_rows)
        self.assertEqual(included.returncode, 0, included.stderr)
        self.assertIn("LOAD82345", included_rows)

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
