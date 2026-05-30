import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.run_fake_ratecon_candidate_extraction import (
    build_fake_candidate_extraction_summary,
    format_summary_lines,
    main,
)
from tests.fixtures.document_ai.broker_templates.fixture_loader import FIXTURE_DIR as TEMPLATE_DIR
from tests.fixtures.document_ai.ratecon_text.fixture_loader import (
    FIXTURE_DIR,
    HARD_LAYOUT_FIXTURE_DIR,
)

CLASSIFICATION_FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "document_classification"
)


class FakeRateConCandidateExtractionCliTests(unittest.TestCase):
    def test_summary_contains_candidate_counts(self):
        summary = build_fake_candidate_extraction_summary(FIXTURE_DIR, TEMPLATE_DIR)

        self.assertGreater(summary["total_fixtures"], 0)
        first = summary["summaries"][0]
        self.assertIn("candidate_counts_by_field", first)
        self.assertIn("template_match_status", first)
        self.assertIn("template_scoring_applied", first)
        self.assertIn("missing_fields", first)

    def test_summary_contains_selected_template_for_template_fixture(self):
        summary = build_fake_candidate_extraction_summary(FIXTURE_DIR, TEMPLATE_DIR)
        by_fixture = {
            item["fixture"]: item
            for item in summary["summaries"]
        }

        self.assertEqual(
            by_fixture["alpha_freight_mock_ratecon.txt"]["selected_template_id"],
            "alpha_freight_mock_v1",
        )

    def test_formatted_output_does_not_include_full_fixture_text(self):
        summary = build_fake_candidate_extraction_summary(FIXTURE_DIR, TEMPLATE_DIR)

        output = "\n".join(format_summary_lines(summary))

        self.assertIn("candidate_counts_by_field", output)
        self.assertIn("selected_template_id", output)
        self.assertIn("DRY RUN ONLY", output)
        self.assertNotIn("FAKE BROKER LLC", output)
        self.assertNotIn("TRUCKLOAD RATE CONFIRMATION", output)

    def test_include_hard_layouts_adds_hard_layout_fixtures(self):
        summary = build_fake_candidate_extraction_summary(
            FIXTURE_DIR,
            TEMPLATE_DIR,
            include_hard_layouts=True,
        )
        fixture_names = {
            item["fixture"]
            for item in summary["summaries"]
        }

        self.assertTrue(summary["include_hard_layouts"])
        self.assertIn("repeated_headers_terms_ratecon.txt", fixture_names)
        self.assertIn("unknown_hard_layout_ratecon.txt", fixture_names)

    def test_input_directory_can_be_hard_layout_directory(self):
        summary = build_fake_candidate_extraction_summary(
            HARD_LAYOUT_FIXTURE_DIR,
            TEMPLATE_DIR,
        )
        fixture_names = {
            item["fixture"]
            for item in summary["summaries"]
        }

        self.assertIn("table_like_stops_ratecon.txt", fixture_names)
        self.assertNotIn("simple_clean_ratecon.txt", fixture_names)

    def test_main_writes_safe_json_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "summary.json"
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = main([
                    "--input-dir",
                    str(FIXTURE_DIR),
                    "--template-dir",
                    str(TEMPLATE_DIR),
                    "--include-hard-layouts",
                    "--output-json",
                    str(output_path),
                ])

            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["dry_run_only"])
        self.assertTrue(payload["include_hard_layouts"])
        self.assertFalse(payload["raw_text_printed"])
        self.assertNotIn("FAKE BROKER LLC", output_path.name)
        self.assertIn("DRY RUN ONLY", buffer.getvalue())

    def test_main_help_mentions_fake_only_safety(self):
        buffer = io.StringIO()

        with self.assertRaises(SystemExit) as raised:
            with redirect_stdout(buffer):
                main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        output = " ".join(buffer.getvalue().lower().split())
        self.assertIn("fake-only", output)
        self.assertIn("does not read private", output)

    def test_classification_mode_classifies_fake_ratecon(self):
        summary = build_fake_candidate_extraction_summary(
            CLASSIFICATION_FIXTURE_DIR,
            TEMPLATE_DIR,
            classify_document=True,
            show_page_roles=True,
            show_section_roles=True,
            respect_extraction_scope=True,
        )
        by_fixture = {
            item["fixture"]: item
            for item in summary["summaries"]
        }

        item = by_fixture["fake_rate_load_confirmation_main_page.txt"]
        self.assertEqual(item["classification"]["document_type"], "RATE_LOAD_CONFIRMATION")
        self.assertTrue(item["classification"]["ratecon_eligible"])
        self.assertFalse(item["ratecon_extraction_skipped"])
        self.assertIn("MAIN_RATECONF", item["classification"]["page_roles"])

    def test_classification_mode_skips_fake_bol_and_supplemental_docs(self):
        summary = build_fake_candidate_extraction_summary(
            CLASSIFICATION_FIXTURE_DIR,
            TEMPLATE_DIR,
            classify_document=True,
            show_page_roles=True,
            show_section_roles=True,
            respect_extraction_scope=True,
        )
        by_fixture = {
            item["fixture"]: item
            for item in summary["summaries"]
        }

        bol = by_fixture["fake_bol_scanned_like_text.txt"]
        carrier_info = by_fixture["fake_driver_carrier_information_sheet.txt"]
        certificate = by_fixture["fake_certificate_of_signature.txt"]

        self.assertTrue(bol["ratecon_extraction_skipped"])
        self.assertTrue(carrier_info["ratecon_extraction_skipped"])
        self.assertTrue(certificate["ratecon_extraction_skipped"])
        self.assertEqual(bol["candidate_counts_by_field"], {})
        self.assertEqual(carrier_info["classification"]["document_type"], "DRIVER_CARRIER_INFO_SHEET")

    def test_classification_cli_output_is_safe(self):
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = main([
                "--input-dir",
                str(CLASSIFICATION_FIXTURE_DIR),
                "--template-dir",
                str(TEMPLATE_DIR),
                "--classify-document",
                "--show-page-roles",
                "--show-section-roles",
                "--respect-extraction-scope",
            ])

        output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("document_type", output)
        self.assertIn("ratecon_extraction_skipped", output)
        self.assertNotIn("Alpha Freight Mock", output)
        self.assertNotIn("Broker MC", output)


if __name__ == "__main__":
    unittest.main()
