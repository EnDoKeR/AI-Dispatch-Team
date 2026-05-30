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
from tests.fixtures.document_ai.ratecon_text.fixture_loader import FIXTURE_DIR


class FakeRateConCandidateExtractionCliTests(unittest.TestCase):
    def test_summary_contains_candidate_counts(self):
        summary = build_fake_candidate_extraction_summary(FIXTURE_DIR, TEMPLATE_DIR)

        self.assertGreater(summary["total_fixtures"], 0)
        first = summary["summaries"][0]
        self.assertIn("candidate_counts_by_field", first)
        self.assertIn("template_match_status", first)
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
                    "--output-json",
                    str(output_path),
                ])

            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["dry_run_only"])
        self.assertFalse(payload["raw_text_printed"])
        self.assertNotIn("FAKE BROKER LLC", output_path.name)
        self.assertIn("DRY RUN ONLY", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
