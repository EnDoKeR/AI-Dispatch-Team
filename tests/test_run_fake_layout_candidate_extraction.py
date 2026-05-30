import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.run_fake_layout_candidate_extraction import (
    DEFAULT_FIXTURE_DIR,
    build_fake_layout_candidate_extraction_summary,
    format_summary_lines,
    main,
)


class FakeLayoutCandidateExtractionCliTests(unittest.TestCase):
    def test_summary_contains_candidate_counts(self):
        summary = build_fake_layout_candidate_extraction_summary(limit=1)

        self.assertEqual(summary["total_fixtures"], 1)
        self.assertTrue(summary["fake_only"])
        self.assertFalse(summary["raw_text_printed"])
        self.assertIn("candidate_counts_by_field", summary["summaries"][0])

    def test_formatted_output_contains_counts_not_values(self):
        summary = build_fake_layout_candidate_extraction_summary(DEFAULT_FIXTURE_DIR)

        output = "\n".join(format_summary_lines(summary))

        self.assertIn("candidate_counts_by_field", output)
        self.assertIn("evidence_type_counts", output)
        self.assertNotIn("FAKE ORIGIN ST", output)
        self.assertNotIn("$2800.00", output)
        self.assertNotIn("FAKE BROKER BLUE", output)

    def test_main_help_mentions_fake_only_safety(self):
        buffer = io.StringIO()

        with self.assertRaises(SystemExit) as raised:
            with redirect_stdout(buffer):
                main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        output = " ".join(buffer.getvalue().lower().split())
        self.assertIn("fake-only", output)
        self.assertIn("does not read private", output)

    def test_main_runs_fake_fixtures(self):
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = main(["--limit", "2"])

        output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("Fake layout candidate extraction dry run", output)
        self.assertIn("Total fixtures: 2", output)
        self.assertIn(".json", output)
        self.assertNotIn("FAKE TENDER ORIGIN", output)

    def test_main_writes_safe_json_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "layout_summary.json"
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(["--limit", "1", "--output-json", str(output_path)])
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["fake_only"])
        self.assertFalse(payload["raw_text_printed"])
        self.assertNotIn("FAKE ORIGIN ST", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
