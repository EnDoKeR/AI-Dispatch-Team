import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from app.document_ai.load_identifier_coverage_audit import (
    LOAD_IDENTIFIER_COVERAGE_ANALYSIS_JSON,
    LOAD_IDENTIFIER_COVERAGE_ANALYSIS_MD,
    LOAD_IDENTIFIER_COVERAGE_JSON,
)
from scripts import analyze_load_identifier_coverage as cli


def _write_fake_safe_summary(root, rows):
    (root / "safe_summary.json").write_text(
        json.dumps({"rows": rows}),
        encoding="utf-8",
    )


class AnalyzeLoadIdentifierCoverageCliTests(unittest.TestCase):
    def test_cli_writes_reports_and_console_is_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_safe_summary(
                root,
                [
                    {
                        "document_alias": "RATECON_001",
                        "load_identifier_audit_records": [
                            {
                                "measurement_alias": "RATECON_001",
                                "stage": "non_primary_reference_rejected",
                                "status": "rejected",
                                "reason": "only_non_primary_references_found",
                                "identifier_label_category": "po_number",
                                "typed_reference_count": 1,
                                "rejected_non_primary_count": 1,
                            }
                        ],
                    }
                ],
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(
                    [
                        "--input-dir",
                        str(root),
                        "--write-md",
                        "--write-json",
                    ]
                )

            output = stdout.getvalue()
            self.assertEqual(result, 0)
            self.assertIn("documents_analyzed: 1", output)
            self.assertIn("rejected_non_primary_count: 1", output)
            self.assertIn("private_values_printed: False", output)
            self.assertNotIn("FAKE-PO", output)
            self.assertTrue((root / LOAD_IDENTIFIER_COVERAGE_ANALYSIS_MD).exists())
            self.assertTrue((root / LOAD_IDENTIFIER_COVERAGE_ANALYSIS_JSON).exists())

    def test_cli_falls_back_to_safe_metrics_when_audit_rows_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_safe_summary(
                root,
                [
                    {
                        "document_alias": "RATECON_001",
                        "load_identifier_coverage_metrics": {
                            "identifier_label_feature_count": 2,
                            "primary_identifier_candidate_count": 0,
                            "typed_reference_candidate_count": 2,
                            "rejected_reference_as_load_id_count": 2,
                            "typed_reference_type_counts": {
                                "po_number": 1,
                                "bol_number": 1,
                            },
                            "rejected_reference_type_counts": {
                                "po_number": 1,
                                "bol_number": 1,
                            },
                        },
                    }
                ],
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", str(root)])

            self.assertEqual(result, 0)
            output = stdout.getvalue()
            self.assertIn("rejected_non_primary_count: 2", output)
            self.assertIn("po_number", output)
            self.assertIn("bol_number", output)

    def test_cli_prefers_current_audit_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / LOAD_IDENTIFIER_COVERAGE_JSON).write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "measurement_alias": "RATECON_001",
                                "stage": "core_load_number_mapped",
                                "status": "missing",
                                "reason": (
                                    "primary_candidate_generated_but_not_core_mapped"
                                ),
                                "identifier_label_category": "load_number",
                                "candidate_count": 1,
                                "primary_candidate_count": 1,
                                "core_mapping_count": 0,
                                "warning_codes": [],
                                "recommended_fix_bucket": "primary_to_core_mapping",
                            }
                        ],
                        "aggregate": {"document_count": 1},
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", str(root)])

            self.assertEqual(result, 0)
            self.assertIn("primary_candidate_count: 1", stdout.getvalue())
            self.assertIn("primary_to_core_mapping", stdout.getvalue())

    def test_cli_missing_output_returns_friendly_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", tmp])

        self.assertEqual(result, 2)
        self.assertIn("load_identifier_coverage_analysis_error", stdout.getvalue())

    def test_cli_can_omit_alias_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_safe_summary(
                root,
                [
                    {
                        "document_alias": "RATECON_001",
                        "load_identifier_coverage_metrics": {
                            "identifier_label_feature_count": 0,
                        },
                    }
                ],
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(
                    [
                        "--input-dir",
                        str(root),
                        "--no-console-alias-details",
                    ]
                )

        self.assertEqual(result, 0)
        self.assertNotIn("aliases_for_", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
