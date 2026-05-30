import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts import run_fake_pdf_triage_dry_run


class FakePdfTriageDryRunCliTests(unittest.TestCase):
    def test_generated_fixture_report_contains_routes(self):
        report = run_fake_pdf_triage_dry_run.build_fake_pdf_triage_report()

        self.assertEqual(report["total_files"], 3)
        self.assertTrue(report["dry_run_only"])
        self.assertFalse(report["private_documents_processed"])
        self.assertTrue(
            all(item["recommended_route"] for item in report["summaries"])
        )

    def test_cli_output_contains_safe_summary(self):
        output = io.StringIO()

        with redirect_stdout(output):
            run_fake_pdf_triage_dry_run.main([])

        text = output.getvalue()

        self.assertIn("FAKE PDF TRIAGE DRY RUN", text)
        self.assertIn("recommended_route:", text)
        self.assertIn(run_fake_pdf_triage_dry_run.DRY_RUN_WARNING, text)

    def test_cli_output_does_not_print_raw_fake_document_text(self):
        output = io.StringIO()

        with redirect_stdout(output):
            run_fake_pdf_triage_dry_run.main([])

        text = output.getvalue()

        self.assertNotIn("TRUCKLOAD RATE CONFIRMATION", text)
        self.assertNotIn("FAKE BROKER LLC", text)
        self.assertNotIn("FAKE-REF-001", text)

    def test_output_json_contains_safe_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "fake_triage.json"
            with redirect_stdout(io.StringIO()):
                run_fake_pdf_triage_dry_run.main(["--output-json", str(output_path)])
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["total_files"], 3)
        self.assertIn("summaries", payload)
        self.assertNotIn("TRUCKLOAD RATE CONFIRMATION", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
