import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from app.document_ai.load_identifier_source_line_audit import (
    LOAD_ID_SOURCE_LINE_ANALYSIS_JSON,
    LOAD_ID_SOURCE_LINE_ANALYSIS_MD,
    LOAD_ID_SOURCE_LINE_RAW_JSON,
)
from scripts import analyze_load_identifier_source_lines as cli


def _write_fake_safe_summary(root, rows):
    (root / "safe_summary.json").write_text(
        json.dumps({"rows": rows}),
        encoding="utf-8",
    )


class AnalyzeLoadIdentifierSourceLinesCliTests(unittest.TestCase):
    def test_cli_runs_on_fake_source_line_metrics_and_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_safe_summary(
                root,
                [
                    {
                        "document_alias": "RATECON_001",
                        "triage_route": "DIGITAL_TEXT",
                        "extraction_status": "TEXT_EXTRACTED",
                        "char_count": 100,
                        "load_identifier_source_line_metrics": {
                            "identifier_like_source_line_count": 1,
                            "scoped_identifier_like_source_line_count": 1,
                            "label_detected_count": 1,
                            "label_classified_count": 0,
                            "typed_candidate_count": 0,
                            "primary_candidate_count": 0,
                            "core_mapping_count": 0,
                            "rejected_non_primary_count": 0,
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
                        "--write-md",
                        "--write-json",
                    ]
                )

            output = stdout.getvalue()
            self.assertEqual(result, 0)
            self.assertIn("documents_analyzed: 1", output)
            self.assertIn("label_classified_count: 0", output)
            self.assertIn("fix_allowed: False", output)
            self.assertIn("private_values_printed: False", output)
            self.assertTrue((root / LOAD_ID_SOURCE_LINE_ANALYSIS_MD).exists())
            self.assertTrue((root / LOAD_ID_SOURCE_LINE_ANALYSIS_JSON).exists())
            self.assertNotIn("FAKE-", output)

    def test_cli_prefers_raw_source_line_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / LOAD_ID_SOURCE_LINE_RAW_JSON).write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "measurement_alias": "RATECON_001",
                                "stage": "source_line",
                                "reason": "source_line_absent",
                                "identifier_like_line_count": 0,
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
            self.assertIn("source_line_absent", stdout.getvalue())

    def test_cli_missing_data_returns_friendly_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", tmp])

        self.assertEqual(result, 2)
        self.assertIn(
            "load_identifier_source_line_analysis_error",
            stdout.getvalue(),
        )

    def test_cli_can_omit_alias_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_safe_summary(
                root,
                [
                    {
                        "document_alias": "RATECON_001",
                        "triage_route": "OCR_NEEDED",
                        "extraction_status": "EMPTY_TEXT",
                        "char_count": 0,
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
