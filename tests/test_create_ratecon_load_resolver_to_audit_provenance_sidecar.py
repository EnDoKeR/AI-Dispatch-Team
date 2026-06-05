import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_ratecon_load_resolver_to_audit_provenance_sidecar.py"
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_resolver_to_audit_provenance"


class CreateRateconLoadResolverToAuditProvenanceSidecarTests(unittest.TestCase):
    def _output_dir(self, tmp_path: Path, fixture: str) -> Path:
        return tmp_path / ".local_outputs" / f"resolver_to_audit_{fixture}"

    def _run(self, tmp_path: Path, fixture: str, *extra_args: str) -> subprocess.CompletedProcess:
        fixture_dir = FIXTURES / fixture
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--generated-resolver-sidecar-dir",
            str(fixture_dir / "generated_resolver_sidecars"),
            "--audit",
            str(fixture_dir / "audit.jsonl"),
            "--output-dir",
            str(self._output_dir(tmp_path, fixture)),
            *extra_args,
        ]
        return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)

    def _summary(self, tmp_path: Path, fixture: str) -> dict:
        return json.loads(
            (
                self._output_dir(tmp_path, fixture)
                / "load_resolver_to_audit_provenance_summary.json"
            ).read_text(encoding="utf-8")
        )

    def _expected(self, fixture: str) -> dict:
        return json.loads((FIXTURES / fixture / "expected_summary.json").read_text(encoding="utf-8"))

    def test_refuses_without_confirm_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(Path(tmp), "preserved")

        self.assertNotEqual(0, result.returncode)
        self.assertIn("--confirm-private-local-run is required", result.stderr)

    def test_refuses_output_outside_local_outputs(self):
        fixture_dir = FIXTURES / "preserved"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--generated-resolver-sidecar-dir",
                    str(fixture_dir / "generated_resolver_sidecars"),
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

        self.assertNotEqual(0, result.returncode)
        self.assertIn("output-dir must be inside .local_outputs", result.stderr)

    def test_fixture_statuses_are_pinned(self):
        fixtures = (
            "preserved",
            "missing_audit_row",
            "candidate_id_lost",
            "source_lost",
            "page_line_lost",
            "pairing_method_lost",
            "selected_flag_lost",
            "stage_unavailable",
            "candidate_not_comparable",
            "current_like_resolver_to_audit_loss",
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for fixture in fixtures:
                with self.subTest(fixture=fixture):
                    result = self._run(tmp_path, fixture, "--confirm-private-local-run")
                    summary = self._summary(tmp_path, fixture)["summary"]
                    expected = self._expected(fixture)

                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertEqual(
                        expected["resolver_to_audit_preserved_count"],
                        summary["resolver_to_audit_preserved_count"],
                    )
                    self.assertEqual(
                        expected["resolver_to_audit_loss_count"],
                        summary["resolver_to_audit_loss_count"],
                    )
                    self.assertIn(
                        expected["resolver_to_audit_status"],
                        summary["resolver_to_audit_status_counts"],
                    )
                    self.assertFalse(summary["pdf_processing_attempted"])
                    self.assertFalse(summary["ocr_attempted"])
                    self.assertFalse(summary["google_called"])
                    self.assertFalse(summary["model_or_cloud_called"])

    def test_outputs_expected_files_and_redacts_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(tmp_path, "preserved", "--confirm-private-local-run")
            output_dir = self._output_dir(tmp_path, "preserved")
            files = {
                name: (output_dir / name).exists()
                for name in (
                    "load_resolver_to_audit_provenance_summary.json",
                    "load_resolver_to_audit_provenance_report.md",
                    "load_resolver_to_audit_rows.csv",
                    "load_resolver_to_audit_loss_by_field.csv",
                    "load_resolver_to_audit_review_items.csv",
                )
            }
            with (output_dir / "load_resolver_to_audit_rows.csv").open(
                "r",
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = [dict(row) for row in csv.DictReader(handle)]
            report = (output_dir / "load_resolver_to_audit_provenance_report.md").read_text(
                encoding="utf-8"
            )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(files, {name: True for name in files})
        self.assertEqual("[redacted]", rows[0]["value_preview"])
        self.assertNotIn("LOAD12345", report)

    def test_private_values_only_appear_with_explicit_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(
                tmp_path,
                "preserved",
                "--confirm-private-local-run",
                "--include-private-values-local-only",
            )
            rows_text = (
                self._output_dir(tmp_path, "preserved") / "load_resolver_to_audit_rows.csv"
            ).read_text(encoding="utf-8")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("LOAD12345", rows_text)

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
            if path.is_file():
                text = path.read_text(encoding="utf-8").lower()
                hits.extend((path.as_posix(), marker) for marker in forbidden if marker in text)

        self.assertEqual([], hits)


if __name__ == "__main__":
    unittest.main()
