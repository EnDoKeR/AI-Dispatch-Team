import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIDECAR_SCRIPT = ROOT / "scripts" / "create_ratecon_load_resolver_to_audit_provenance_sidecar.py"
BOUNDARY_SCRIPT = ROOT / "scripts" / "compare_ratecon_load_generated_provenance_boundaries.py"
FIXTURES = ROOT / "tests" / "fixtures" / "ratecon_load_generated_resolver_provenance" / "full_roundtrip"
RESOLVER_FIXTURE = ROOT / "tests" / "fixtures" / "ratecon_load_resolver_to_audit_provenance" / "preserved"


class RateconLoadResolverToAuditBoundaryIntegrationTests(unittest.TestCase):
    def test_preserved_sidecar_moves_boundary_to_audit_to_evaluator(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sidecar_output = tmp_path / ".local_outputs" / "resolver_to_audit"
            boundary_output = tmp_path / ".local_outputs" / "boundary"
            sidecar_result = subprocess.run(
                [
                    sys.executable,
                    str(SIDECAR_SCRIPT),
                    "--generated-resolver-sidecar-dir",
                    str(RESOLVER_FIXTURE / "generated_resolver_sidecars"),
                    "--audit",
                    str(RESOLVER_FIXTURE / "audit.jsonl"),
                    "--output-dir",
                    str(sidecar_output),
                    "--confirm-private-local-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            boundary_result = subprocess.run(
                [
                    sys.executable,
                    str(BOUNDARY_SCRIPT),
                    "--generated-resolver-sidecar-dir",
                    str(FIXTURES),
                    "--serialization-dir",
                    str(FIXTURES / "serialization"),
                    "--resolver-to-audit-sidecar-dir",
                    str(sidecar_output),
                    "--output-dir",
                    str(boundary_output),
                    "--confirm-local-audit-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            summary = json.loads(
                (boundary_output / "load_generated_provenance_boundary_summary.json").read_text(
                    encoding="utf-8"
                )
            )["summary"]
            with (sidecar_output / "load_resolver_to_audit_rows.csv").open(
                "r",
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = [dict(row) for row in csv.DictReader(handle)]

        self.assertEqual(0, sidecar_result.returncode, sidecar_result.stderr)
        self.assertEqual(0, boundary_result.returncode, boundary_result.stderr)
        self.assertEqual("boundary_audit_to_evaluator_loss", summary["first_loss_boundary"])
        self.assertEqual(1, summary["resolver_to_audit_preserved_count"])
        self.assertEqual("audit", rows[0]["stage"])
        self.assertEqual("native_text", rows[0]["source"])
        self.assertEqual("1", rows[0]["page_number"])


if __name__ == "__main__":
    unittest.main()
