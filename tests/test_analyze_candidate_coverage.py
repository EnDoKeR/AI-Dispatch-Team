import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from app.document_ai.candidate_coverage_analysis import (
    CANDIDATE_COVERAGE_JSON,
    CANDIDATE_COVERAGE_ANALYSIS_JSON,
    CANDIDATE_COVERAGE_ANALYSIS_MD,
)
from app.document_ai.candidate_coverage_target_selector import (
    CANDIDATE_COVERAGE_TARGET_SELECTION_JSON,
    CANDIDATE_COVERAGE_TARGET_SELECTION_MD,
)
from app.document_ai.ratecon_review_workbook import (
    FIELD_REVIEW_COLUMNS,
    REVIEW_FIELD_REVIEW_CSV,
    REVIEW_STOP_REVIEW_CSV,
    STOP_REVIEW_COLUMNS,
)
from scripts import analyze_candidate_coverage as cli


def _write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _write_fake_outputs(root):
    (root / "safe_summary.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "document_alias": "RATECON_001",
                        "stop_span_coverage_metrics": {
                            "line_feature_count_by_label_category": {
                                "date": 1,
                                "pickup": 1,
                            },
                            "anchor_count_by_type": {"pickup": 1},
                            "span_count_by_type": {"pickup": 1},
                            "span_field_candidate_count_by_field": {},
                            "normalized_stop_field_count_by_field": {},
                            "core_field_mapping_count_by_field": {},
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (root / "core_field_gap_analysis.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "measurement_alias": "RATECON_001",
                        "field_name": "pickup_date",
                        "status": "missing",
                        "gap_reason": "no_candidate",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    _write_csv(
        root / REVIEW_STOP_REVIEW_CSV,
        STOP_REVIEW_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Stop Type": "pickup",
                "Field Name": "date",
                "Predicted Value LOCAL ONLY": "Fake Private Date",
                "Status": "missing",
            }
        ],
    )
    _write_csv(
        root / REVIEW_FIELD_REVIEW_CSV,
        FIELD_REVIEW_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "broker_name",
                "Predicted Value LOCAL ONLY": "Fake Broker",
                "Status": "missing",
            }
        ],
    )


class AnalyzeCandidateCoverageCliTests(unittest.TestCase):
    def test_cli_writes_reports_and_console_is_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_outputs(root)
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
            self.assertIn("recommended_next_fix", output)
            self.assertIn("private_values_printed: False", output)
            self.assertNotIn("Fake Broker", output)
            self.assertNotIn("Fake Private Date", output)
            self.assertTrue((root / CANDIDATE_COVERAGE_ANALYSIS_MD).exists())
            self.assertTrue((root / CANDIDATE_COVERAGE_ANALYSIS_JSON).exists())
            payload = (root / CANDIDATE_COVERAGE_ANALYSIS_JSON).read_text(
                encoding="utf-8"
            )
            self.assertNotIn("Fake Private Date", payload)

    def test_cli_missing_output_returns_friendly_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", tmp])

        self.assertEqual(result, 2)
        self.assertIn("candidate_coverage_analysis_error", stdout.getvalue())

    def test_cli_can_omit_alias_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_outputs(root)
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

    def test_cli_prefers_current_candidate_coverage_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / CANDIDATE_COVERAGE_JSON).write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "measurement_alias": "RATECON_001",
                                "field_name": "load_number",
                                "stage": "review_row",
                                "status": "missing",
                                "gap_reason": "candidate_not_generated",
                                "candidate_count": 0,
                                "normalized_field_count": 0,
                                "review_row_count": 0,
                                "evidence_type_counts": {},
                                "warning_codes": [],
                                "recommended_fix_bucket": (
                                    "load_identifier_candidate_generation"
                                ),
                            }
                        ],
                        "aggregate": {
                            "document_count": 1,
                            "top_missing_candidate_fields": ["load_number"],
                            "coverage_counts_by_stage": {"review_row": 1},
                            "gap_reason_counts": {"candidate_not_generated": 1},
                            "aliases_by_gap_reason": {
                                "candidate_not_generated": ["RATECON_001"]
                            },
                            "top_gap_reasons": ["candidate_not_generated"],
                            "recommended_next_fix": (
                                "load_identifier_candidate_generation"
                            ),
                        },
                        "analysis_version": "candidate_coverage_analysis_v1",
                        "private_values_included": False,
                        "raw_text_included": False,
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", str(root)])

        self.assertEqual(result, 0)
        output = stdout.getvalue()
        self.assertIn("load_identifier_candidate_generation", output)
        self.assertIn("load_number", output)

    def test_cli_selects_next_target_and_writes_target_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_outputs(root)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(
                    [
                        "--input-dir",
                        str(root),
                        "--write-md",
                        "--write-json",
                        "--select-next-target",
                    ]
                )

            output = stdout.getvalue()
            self.assertEqual(result, 0)
            self.assertIn("Candidate coverage target selection", output)
            self.assertIn("selected_target: stop_span_date_candidate_generation", output)
            self.assertIn("private_values_printed: False", output)
            self.assertNotIn("Fake Private Date", output)
            self.assertTrue((root / CANDIDATE_COVERAGE_TARGET_SELECTION_MD).exists())
            self.assertTrue((root / CANDIDATE_COVERAGE_TARGET_SELECTION_JSON).exists())


if __name__ == "__main__":
    unittest.main()
