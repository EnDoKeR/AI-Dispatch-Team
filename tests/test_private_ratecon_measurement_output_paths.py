import inspect
import unittest
from pathlib import Path

from app.document_ai.measurement_cli import ratecon_private_output_paths
from app.document_ai.measurement_cli.ratecon_private_args import (
    parse_private_ratecon_measurement_args,
)
from app.document_ai.measurement_cli.ratecon_private_config import (
    build_private_ratecon_measurement_config,
)
from app.document_ai.measurement_cli.ratecon_private_output_paths import (
    DEFAULT_PRIVATE_RATECON_OUTPUT_DIR,
    PrivateRateconOutputPathError,
    build_private_ratecon_output_paths,
    output_file_labels,
    private_measurement_report_path,
    private_measurement_rows_path,
    private_measurement_summary_path,
    ratecon_shadow_audit_jsonl_path,
    ratecon_shadow_summary_json_path,
    review_workbook_path,
    validate_private_ratecon_output_dir,
)


def _config(*argv):
    args = parse_private_ratecon_measurement_args(list(argv))
    return build_private_ratecon_measurement_config(args)


class PrivateRateconMeasurementOutputPathTests(unittest.TestCase):
    def test_default_output_dir_remains_unchanged(self):
        config = _config(
            "--input-dir",
            "tests/fixtures/document_ai",
            "--confirm-private-local-run",
        )

        paths = build_private_ratecon_output_paths(config)

        self.assertEqual(paths.output_dir, Path(".local_outputs/private_ratecon_measurement"))
        self.assertEqual(DEFAULT_PRIVATE_RATECON_OUTPUT_DIR, paths.output_dir)

    def test_known_output_filenames_remain_unchanged(self):
        root = DEFAULT_PRIVATE_RATECON_OUTPUT_DIR
        paths = build_private_ratecon_output_paths(output_dir=root)

        expected = {
            "safe_summary_json": "safe_summary.json",
            "safe_summary_csv": "safe_summary.csv",
            "safe_aggregate_json": "safe_aggregate.json",
            "safe_aggregate_md": "safe_aggregate.md",
            "value_review_template_csv": "value_review_template.csv",
            "ratecon_shadow_audit_jsonl": "ratecon_shadow_document_pipeline_audit.jsonl",
            "ratecon_shadow_summary_json": "ratecon_shadow_document_pipeline_summary.json",
            "review_workbook_xlsx": "ratecon_review_workbook.xlsx",
            "review_google_sheet_csv": "ratecon_review_google_sheet.csv",
            "review_document_summary_csv": "ratecon_review_document_summary.csv",
            "review_stop_review_csv": "ratecon_review_stop_review.csv",
            "review_field_review_csv": "ratecon_review_field_review.csv",
            "review_rate_review_csv": "ratecon_review_rate_review.csv",
            "review_v2_workbook_xlsx": "ratecon_review_v2_workbook.xlsx",
            "review_v2_document_summary_csv": "ratecon_review_v2_document_summary.csv",
            "review_v2_core_fields_csv": "ratecon_review_v2_core_fields.csv",
            "review_v2_stops_csv": "ratecon_review_v2_stops.csv",
            "review_v2_rates_csv": "ratecon_review_v2_rates.csv",
            "review_v2_load_ids_csv": "ratecon_review_v2_load_ids.csv",
            "review_v2_instructions_csv": "ratecon_review_v2_instructions.csv",
            "stop_review_packet_csv": "stop_review_packet.csv",
            "stop_review_packet_md": "stop_review_packet.md",
            "stop_group_provenance_json": "stop_group_provenance.json",
            "stop_group_provenance_md": "stop_group_provenance_report.md",
            "layout_provider_diagnostics_md": "layout_provider_diagnostics.md",
        }

        for attr, filename in expected.items():
            with self.subTest(attr=attr):
                self.assertEqual(getattr(paths, attr).name, filename)

    def test_named_path_helpers_keep_existing_names(self):
        root = DEFAULT_PRIVATE_RATECON_OUTPUT_DIR

        self.assertEqual(private_measurement_summary_path(root).name, "safe_summary.json")
        self.assertEqual(private_measurement_rows_path(root).name, "safe_summary.csv")
        self.assertEqual(private_measurement_report_path(root).name, "safe_aggregate.md")
        self.assertEqual(
            ratecon_shadow_audit_jsonl_path(root).name,
            "ratecon_shadow_document_pipeline_audit.jsonl",
        )
        self.assertEqual(
            ratecon_shadow_summary_json_path(root).name,
            "ratecon_shadow_document_pipeline_summary.json",
        )
        self.assertEqual(review_workbook_path(root).name, "ratecon_review_workbook.xlsx")

    def test_output_paths_reject_nonlocal_output_without_custom_flag_when_writing(self):
        config = _config(
            "--input-dir",
            "tests/fixtures/document_ai",
            "--confirm-private-local-run",
            "--output-dir",
            "unsafe-output",
            "--write-json",
        )

        with self.assertRaises(PrivateRateconOutputPathError):
            build_private_ratecon_output_paths(config)

    def test_local_outputs_paths_are_allowed(self):
        config = _config(
            "--input-dir",
            "tests/fixtures/document_ai",
            "--confirm-private-local-run",
            "--output-dir",
            ".local_outputs/alternate_private_ratecon_measurement",
            "--write-json",
        )

        paths = build_private_ratecon_output_paths(config)

        self.assertEqual(
            paths.output_dir,
            Path(".local_outputs/alternate_private_ratecon_measurement"),
        )

    def test_custom_output_path_allowed_when_explicit(self):
        validate_private_ratecon_output_dir(
            "sanitized-custom-output",
            allow_custom_output_dir=True,
        )

    def test_output_file_labels_returns_names_only(self):
        labels = output_file_labels(
            {
                "json": DEFAULT_PRIVATE_RATECON_OUTPUT_DIR / "safe_summary.json",
                "csv": "custom/safe_summary.csv",
            }
        )

        self.assertEqual(labels, {"json": "safe_summary.json", "csv": "safe_summary.csv"})

    def test_module_does_not_write_files_or_process_documents(self):
        source = inspect.getsource(ratecon_private_output_paths)
        forbidden = [
            ".write_text(",
            ".open(",
            ".mkdir(",
            "discover_private_pdfs",
            "measure_private_ratecon_pdf",
            "pytesseract",
            "openai",
            "anthropic",
            "gemini",
            "requests.",
            "urllib.",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
