import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts import audit_ratecon_candidate_model_ownership as audit_script


class RateconCandidateModelOwnershipAuditTests(unittest.TestCase):
    def _write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _make_repo(self):
        temp = tempfile.TemporaryDirectory()
        repo = Path(temp.name)
        (repo / "app" / "document_ai").mkdir(parents=True)
        (repo / "app" / "market_intelligence" / "intake").mkdir(parents=True)
        (repo / ".local_outputs").mkdir()
        (repo / "data" / "private_ratecons").mkdir(parents=True)
        sentinel = repo / "executed.txt"

        self._write(
            repo / "app" / "document_ai" / "field_candidate_provenance.py",
            "from dataclasses import dataclass\n"
            "from pathlib import Path\n"
            f"Path(r'{sentinel.as_posix()}').write_text('executed')\n"
            "SOURCE_NATIVE_TEXT = 'native_text'\n"
            "SOURCE_REGEX = 'regex'\n"
            "CONFIDENCE_SCORE_BY_LEVEL = {'high': 0.9, 'medium': 0.6}\n"
            "@dataclass(frozen=True)\n"
            "class FieldCandidate:\n"
            "    field: str\n"
            "    value: object\n"
            "    normalized_value: object | None = None\n"
            "    source: str = SOURCE_NATIVE_TEXT\n"
            "    confidence: float = 0.0\n"
            "def build_field_candidate(field, value, source=SOURCE_NATIVE_TEXT):\n"
            "    return {\n"
            "        'field': field,\n"
            "        'value': value,\n"
            "        'normalized_value': value,\n"
            "        'source': source,\n"
            "        'confidence': 0.8,\n"
            "        'evidence_text': '',\n"
            "    }\n",
        )
        self._write(
            repo / "app" / "document_ai" / "field_candidate_generators.py",
            "from app.document_ai.field_candidate_provenance import build_field_candidate\n"
            "GENERATOR_TEXT_CANDIDATES = 'text'\n"
            "def generate_field_candidates(text):\n"
            "    return [build_field_candidate('load_number', 'FAKE-LOAD-001')]\n",
        )
        self._write(
            repo / "app" / "document_ai" / "field_candidate_resolver.py",
            "FIELD_LOAD_NUMBER = 'load_number'\n"
            "def resolve_field_candidates(candidates):\n"
            "    return {'field': FIELD_LOAD_NUMBER, 'selected_candidate': None}\n",
        )
        self._write(
            repo / "app" / "document_ai" / "ratecon_candidates.py",
            "CANDIDATE_CONFIDENCE_HIGH = 'high'\n"
            "FIELD_LOAD_NUMBER = 'load_number'\n"
            "SOURCE_REGEX = 'regex'\n"
            "def build_field_candidate(field_name, raw_value):\n"
            "    return {\n"
            "        'candidate_id': 'c1',\n"
            "        'field_name': field_name,\n"
            "        'raw_value': raw_value,\n"
            "        'normalized_value': raw_value,\n"
            "        'confidence': CANDIDATE_CONFIDENCE_HIGH,\n"
            "        'source': SOURCE_REGEX,\n"
            "        'evidence_ref': 'safe-fixture',\n"
            "    }\n",
        )
        self._write(
            repo
            / "app"
            / "market_intelligence"
            / "intake"
            / "rate_confirmation_intake.py",
            "CRITICAL_FIELDS = ('load_number',)\n"
            "def build_rate_confirmation_intake(candidates):\n"
            "    return {'load_number': candidates.get('load_number')}\n",
        )
        self._write(
            repo / ".local_outputs" / "private.txt",
            "SENTINEL_PRIVATE_VALUE",
        )
        self._write(
            repo / "data" / "private_ratecons" / "private.pdf",
            "SENTINEL_PRIVATE_VALUE",
        )
        return temp, repo, sentinel

    def _run_audit(self, repo, output_dir=None):
        output_dir = output_dir or repo / ".local_outputs" / "candidate_audit"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = audit_script.main(
                [
                    "--repo-root",
                    str(repo),
                    "--output-dir",
                    str(output_dir),
                    "--confirm-local-audit-run",
                ]
            )
        self.assertEqual(result, 0)
        return output_dir, stdout.getvalue()

    def test_refuses_without_confirm_flag(self):
        with self.assertRaises(SystemExit) as raised:
            audit_script.main(["--repo-root", "."])
        self.assertEqual(raised.exception.code, 2)

    def test_refuses_output_outside_local_outputs(self):
        temp, repo, _sentinel = self._make_repo()
        with temp:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = audit_script.main(
                    [
                        "--repo-root",
                        str(repo),
                        "--output-dir",
                        str(repo / "audit"),
                        "--confirm-local-audit-run",
                    ]
                )
            self.assertEqual(result, 2)
            self.assertIn("Output directory must be under .local_outputs", stdout.getvalue())

    def test_writes_expected_outputs_and_detects_candidate_inventory(self):
        temp, repo, sentinel = self._make_repo()
        with temp:
            output_dir, stdout = self._run_audit(repo)
            self.assertIn("RateCon candidate model ownership audit", stdout)
            self.assertFalse(sentinel.exists(), "fixture candidate module must not execute")
            self.assertEqual(
                {
                    "candidate_model_ownership_summary.json",
                    "candidate_model_ownership_report.md",
                    "candidate_modules.csv",
                    "candidate_import_edges.csv",
                    "candidate_symbols.csv",
                    "candidate_shape_findings.csv",
                    "candidate_duplicate_constants.csv",
                    "candidate_status_recommendations.csv",
                    "candidate_risk_findings.csv",
                },
                {path.name for path in output_dir.iterdir()},
            )

            summary = json.loads(
                (output_dir / "candidate_model_ownership_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            module_paths = {row["module_path"] for row in summary["modules"]}
            self.assertIn("app/document_ai/field_candidate_provenance.py", module_paths)
            self.assertIn("app/document_ai/field_candidate_generators.py", module_paths)
            self.assertIn("app/document_ai/field_candidate_resolver.py", module_paths)
            self.assertIn("app/document_ai/ratecon_candidates.py", module_paths)
            self.assertIn(
                "app/market_intelligence/intake/rate_confirmation_intake.py",
                module_paths,
            )

    def test_detects_symbols_shapes_duplicates_and_ownership_roles(self):
        temp, repo, _sentinel = self._make_repo()
        with temp:
            output_dir, _stdout = self._run_audit(repo)
            summary = json.loads(
                (output_dir / "candidate_model_ownership_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            modules = {row["module_path"]: row for row in summary["modules"]}
            self.assertEqual(
                "canonical_contract",
                modules["app/document_ai/field_candidate_provenance.py"][
                    "canonical_owner_recommendation"
                ],
            )
            self.assertEqual(
                "compatibility_legacy",
                modules["app/document_ai/ratecon_candidates.py"][
                    "canonical_owner_recommendation"
                ],
            )
            self.assertEqual(
                "boundary_adapter",
                modules["app/market_intelligence/intake/rate_confirmation_intake.py"][
                    "canonical_owner_recommendation"
                ],
            )
            symbols = {
                (row["module_path"], row["symbol_name"], row["category"])
                for row in summary["symbols"]
            }
            self.assertIn(
                (
                    "app/document_ai/field_candidate_provenance.py",
                    "FieldCandidate",
                    "candidate_class",
                ),
                symbols,
            )
            self.assertIn(
                (
                    "app/document_ai/ratecon_candidates.py",
                    "build_field_candidate",
                    "build_candidate_function",
                ),
                symbols,
            )
            self.assertGreater(summary["candidate_shape_finding_count"], 0)
            duplicate_names = {row["constant_name"] for row in summary["duplicate_constants"]}
            self.assertIn("SOURCE_REGEX", duplicate_names)

    def test_ignores_private_dirs_and_records_safety_no_execution(self):
        temp, repo, _sentinel = self._make_repo()
        with temp:
            output_dir, _stdout = self._run_audit(repo)
            for path in output_dir.iterdir():
                self.assertNotIn(
                    "SENTINEL_PRIVATE_VALUE",
                    path.read_text(encoding="utf-8"),
                    msg=f"private value leaked into {path}",
                )
            summary = json.loads(
                (output_dir / "candidate_model_ownership_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            safety = summary["safety"]
            self.assertFalse(safety["project_modules_imported"])
            self.assertFalse(safety["extraction_executed"])
            self.assertFalse(safety["resolver_executed"])
            self.assertFalse(safety["pdf_processing_attempted"])
            self.assertFalse(safety["ocr_attempted"])
            self.assertFalse(safety["local_outputs_read"])
            self.assertFalse(safety["private_ratecons_read"])
            self.assertFalse(safety["google_called"])
            self.assertFalse(safety["model_or_cloud_called"])


if __name__ == "__main__":
    unittest.main()
