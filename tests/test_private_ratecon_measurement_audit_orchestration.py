import inspect
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.document_ai.measurement_cli import ratecon_private_audit_orchestration
from app.document_ai.measurement_cli.ratecon_private_audit_orchestration import (
    PrivateRateconAuditTaskResult,
    build_private_ratecon_audit_task_plan,
    run_candidate_coverage_audit_if_enabled,
    run_layout_diagnostics_if_enabled,
    run_private_ratecon_audit_exports,
    run_ratecon_shadow_audit_if_enabled,
    run_stop_provenance_report_if_enabled,
)
from app.document_ai.measurement_cli.ratecon_private_output_paths import (
    PrivateRateconOutputPathError,
    build_private_ratecon_output_paths,
    layout_provider_diagnostics_path,
    stop_group_provenance_json_path,
    stop_group_provenance_md_path,
)


def _config(**overrides):
    values = {
        "allow_custom_output_dir": False,
        "dry_run": False,
        "write_candidate_coverage": False,
        "write_load_identifier_audit": False,
        "write_load_identifier_source_line_audit": False,
        "write_rate_forensics": False,
        "write_rate_conflict_audit": False,
        "write_ratecon_shadow_audit": False,
        "write_stop_provenance_report": False,
        "layout_diagnostics": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _report_rows():
    return [
        {
            "document_alias": "RATECON_001",
            "layout_provider_name": "fixture_layout",
            "layout_provider_status": "success",
            "page_count": 1,
            "layout_total_word_count": 5,
            "layout_total_line_count": 2,
            "layout_total_table_count": 1,
            "layout_total_table_cell_count": 4,
            "layout_table_settings_profile": "lines",
            "layout_quality_bucket": "fixture",
            "layout_stop_signal_counts": {"pickup": 1},
            "warning_codes": ["fixture_warning"],
        }
    ]


class PrivateRateconMeasurementAuditOrchestrationTests(unittest.TestCase):
    def test_task_plan_enables_expected_tasks_in_existing_order(self):
        config = _config(
            write_candidate_coverage=True,
            write_rate_forensics=True,
            write_stop_provenance_report=True,
            layout_diagnostics=True,
        )

        self.assertEqual(
            build_private_ratecon_audit_task_plan(config),
            [
                "candidate_coverage",
                "rate_forensics",
                "stop_provenance_report",
                "layout_diagnostics",
            ],
        )

    def test_task_plan_disables_tasks_when_flags_absent_or_dry_run(self):
        self.assertEqual(build_private_ratecon_audit_task_plan(_config()), [])
        self.assertEqual(
            build_private_ratecon_audit_task_plan(
                _config(write_candidate_coverage=True, dry_run=True)
            ),
            [],
        )

    def test_candidate_coverage_wrapper_uses_paths_and_preserves_labels(self):
        calls = {}
        output_paths = build_private_ratecon_output_paths(
            output_dir=".local_outputs/test_audit_orchestration"
        )

        def analyzer(rows, review_rows_by_sheet=None):
            calls["analyzer_rows"] = rows
            calls["review_rows_by_sheet"] = review_rows_by_sheet
            return {"analysis": "fixture"}

        def writer(analysis, output_dir=None, allow_custom_output_dir=False):
            calls["writer"] = {
                "analysis": analysis,
                "output_dir": output_dir,
                "allow_custom_output_dir": allow_custom_output_dir,
            }
            return {
                "paths": {
                    "csv": Path(output_dir) / "candidate_coverage.csv",
                    "md": Path(output_dir) / "candidate_coverage.md",
                },
                "aggregate": {
                    "document_count": 2,
                    "top_missing_candidate_fields": [
                        "field_1",
                        "field_2",
                        "field_3",
                        "field_4",
                        "field_5",
                        "field_6",
                        "field_7",
                        "field_8",
                        "field_9",
                    ],
                    "coverage_counts_by_stage": {"candidate": 1},
                    "gap_reason_counts": {"missing": 1},
                    "recommended_next_fix": "fixture_only",
                },
                "private_values_printed": False,
                "raw_text_printed": False,
            }

        result = run_candidate_coverage_audit_if_enabled(
            {"rows": _report_rows()},
            _config(write_candidate_coverage=True),
            output_paths,
            review_rows_by_sheet={"Summary": []},
            analyzer=analyzer,
            writer=writer,
        )

        self.assertIsInstance(result, PrivateRateconAuditTaskResult)
        self.assertEqual(result.message_label, "candidate_coverage_written")
        self.assertEqual(calls["analyzer_rows"], _report_rows())
        self.assertEqual(calls["review_rows_by_sheet"], {"Summary": []})
        self.assertEqual(calls["writer"]["analysis"], {"analysis": "fixture"})
        self.assertEqual(calls["writer"]["output_dir"], output_paths.output_dir)
        self.assertFalse(calls["writer"]["allow_custom_output_dir"])
        self.assertEqual(
            result.payload,
            {
                "files": {
                    "csv": "candidate_coverage.csv",
                    "md": "candidate_coverage.md",
                },
                "document_count": 2,
                "top_missing_candidate_fields": [
                    "field_1",
                    "field_2",
                    "field_3",
                    "field_4",
                    "field_5",
                    "field_6",
                    "field_7",
                    "field_8",
                ],
                "coverage_counts_by_stage": {"candidate": 1},
                "gap_reason_counts": {"missing": 1},
                "recommended_next_fix": "fixture_only",
                "private_values_printed": False,
                "raw_text_printed": False,
            },
        )

    def test_shadow_audit_wrapper_preserves_existing_summary_fields(self):
        output_paths = build_private_ratecon_output_paths(
            output_dir=".local_outputs/test_audit_orchestration"
        )
        calls = {}

        def record_builder(rows):
            calls["rows"] = rows
            return [{"document_alias": "RATECON_001"}]

        def writer(records, output_dir=None, allow_custom_output_dir=False):
            calls["records"] = records
            return {
                "files": {"jsonl": "ratecon_shadow_document_pipeline_audit.jsonl"},
                "aggregate": {
                    "documents_processed": 1,
                    "shadow_success": 1,
                    "shadow_failed": 0,
                    "review_gate": {"needs_review_count": 0},
                    "failure_attribution": {
                        "primary_layer_counts": {"candidate": 1}
                    },
                },
                "private_values_printed": False,
                "raw_text_printed": False,
                "money_values_printed": False,
            }

        result = run_ratecon_shadow_audit_if_enabled(
            {"rows": _report_rows()},
            _config(write_ratecon_shadow_audit=True),
            output_paths,
            record_builder=record_builder,
            writer=writer,
        )

        self.assertEqual(calls["rows"], _report_rows())
        self.assertEqual(calls["records"], [{"document_alias": "RATECON_001"}])
        self.assertEqual(result.message_label, "ratecon_shadow_audit_written")
        self.assertEqual(
            result.payload,
            {
                "files": {"jsonl": "ratecon_shadow_document_pipeline_audit.jsonl"},
                "documents_processed": 1,
                "shadow_success": 1,
                "shadow_failed": 0,
                "needs_review_count": 0,
                "primary_layer_counts": {"candidate": 1},
                "private_values_printed": False,
                "raw_text_printed": False,
                "money_values_printed": False,
            },
        )

    def test_stop_provenance_and_layout_labels_preserve_existing_filenames(self):
        output_paths = build_private_ratecon_output_paths(
            output_dir=".local_outputs/test_audit_orchestration"
        )

        stop_result = run_stop_provenance_report_if_enabled(
            {"rows": _report_rows()},
            _config(write_stop_provenance_report=True),
            output_paths,
            writer=lambda rows, output_dir=None, allow_custom_output_dir=False: {
                "json": stop_group_provenance_json_path(output_dir),
                "md": stop_group_provenance_md_path(output_dir),
                "row_count": len(rows),
            },
        )
        layout_result = run_layout_diagnostics_if_enabled(
            {"rows": _report_rows()},
            _config(layout_diagnostics=True),
            output_paths,
            writer=lambda diagnostics, output_dir=None, allow_custom_output_dir=False: (
                layout_provider_diagnostics_path(output_dir)
            ),
        )

        self.assertEqual(
            stop_result.payload,
            {
                "json": "stop_group_provenance.json",
                "md": "stop_group_provenance_report.md",
                "row_count": 1,
            },
        )
        self.assertEqual(layout_result.payload, "layout_provider_diagnostics.md")

    def test_orchestration_rejects_unsafe_output_paths_before_writing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_paths = build_private_ratecon_output_paths(output_dir=temp_dir)
            with self.assertRaises(PrivateRateconOutputPathError):
                run_private_ratecon_audit_exports(
                    {"rows": _report_rows()},
                    _config(write_candidate_coverage=True),
                    output_paths,
                    task_names=["candidate_coverage"],
                )

    def test_orchestration_runs_selected_tasks_only(self):
        output_paths = build_private_ratecon_output_paths(
            output_dir=".local_outputs/test_audit_orchestration"
        )

        results = run_private_ratecon_audit_exports(
            {"rows": _report_rows()},
            _config(write_candidate_coverage=True, write_stop_provenance_report=True),
            output_paths,
            task_names=["layout_diagnostics"],
        )

        self.assertEqual(results, [])

    def test_module_does_not_process_documents_call_services_or_generate_workbooks(self):
        source = inspect.getsource(ratecon_private_audit_orchestration)
        forbidden = [
            "discover_private_pdfs",
            "measure_private_ratecon_pdf",
            "pytesseract",
            "easyocr",
            "openai",
            "anthropic",
            "gemini",
            "google_sheets_review",
            "googleapiclient",
            "google.oauth",
            "Workbook",
            "openpyxl",
            "workbook.save",
            "requests.",
            "urllib.",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
