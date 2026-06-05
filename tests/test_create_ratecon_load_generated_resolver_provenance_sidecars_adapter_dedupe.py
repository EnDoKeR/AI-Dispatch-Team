import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_ratecon_load_generated_resolver_provenance_sidecars.py"
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_adapter_dedupe_stage_sidecars"


class CreateRateconLoadGeneratedResolverProvenanceSidecarsAdapterDedupeTests(unittest.TestCase):
    def _output_dir(self, tmp_path: Path, fixture: str) -> Path:
        return tmp_path / ".local_outputs" / f"adapter_dedupe_{fixture}"

    def _run(self, tmp_path: Path, fixture: str) -> subprocess.CompletedProcess:
        fixture_dir = FIXTURES / fixture
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--legacy-output-dir",
                str(fixture_dir),
                "--output-dir",
                str(self._output_dir(tmp_path, fixture)),
                "--confirm-private-local-run",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def test_adapter_dedupe_outputs_are_written_and_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = self._run(tmp_path, "adapter_input_output_complete")
            output_dir = self._output_dir(tmp_path, "adapter_input_output_complete")
            payload = json.loads(
                (output_dir / "load_generated_resolver_provenance_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            files = {
                name: (output_dir / name).exists()
                for name in (
                    "load_adapter_input_candidates.csv",
                    "load_adapter_output_candidates.csv",
                    "load_dedupe_input_candidates.csv",
                    "load_dedupe_output_candidates.csv",
                    "load_adapter_dedupe_loss_by_stage.csv",
                )
            }
            with (output_dir / "load_adapter_dedupe_loss_by_stage.csv").open(
                "r",
                encoding="utf-8",
                newline="",
            ) as handle:
                adapter_loss_rows = list(csv.DictReader(handle))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(files, {name: True for name in files})
        self.assertEqual(1, payload["summary"]["adapter_input_count"])
        self.assertEqual(1, payload["summary"]["adapter_output_count"])
        self.assertEqual(1, payload["summary"]["dedupe_input_count"])
        self.assertEqual(1, payload["summary"]["dedupe_output_count"])
        self.assertEqual("adapter_stage_complete", adapter_loss_rows[0]["adapter_stage_status"])
        self.assertEqual("dedupe_stage_complete", adapter_loss_rows[0]["dedupe_stage_status"])
        self.assertNotIn("LOAD12345", json.dumps(payload))
        self.assertFalse(payload["summary"]["pdf_processing_attempted"])
        self.assertFalse(payload["summary"]["ocr_attempted"])
        self.assertFalse(payload["summary"]["google_called"])
        self.assertFalse(payload["summary"]["model_or_cloud_called"])

    def test_committed_adapter_dedupe_fixtures_are_sanitized(self):
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
