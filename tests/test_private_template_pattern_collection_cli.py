import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts.run_private_ratecon_template_pattern_collection import (
    build_private_template_pattern_collection_report,
    main,
)
from tests.fixtures.document_ai.pdf_triage.fake_pdf_factory import write_fake_text_pdf


PRIVATE_LIKE_TEXT = """TRUCKLOAD RATE CONFIRMATION
Broker: FAKE BROKER LLC
Load #: FAKE-REF-001
Carrier Pay: $2,850.00
Pickup: Fake City, ST 00000
Delivery: Example City, ST 00000
"""


class PrivateTemplatePatternCollectionCliTests(unittest.TestCase):
    def _fake_pdf_dir(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        write_fake_text_pdf(root, file_name="z_fake.pdf", text=PRIVATE_LIKE_TEXT)
        return temp, root

    def test_cli_refuses_without_confirmation(self):
        temp, root = self._fake_pdf_dir()
        self.addCleanup(temp.cleanup)
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["--input-dir", str(root)])

        self.assertEqual(exit_code, 2)
        self.assertIn("--confirm-private-local-run", stdout.getvalue())

    def test_cli_missing_input_dir_is_friendly(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "--input-dir",
                        str(missing),
                        "--confirm-private-local-run",
                    ]
                )

        combined = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(exit_code, 2)
        self.assertIn("could not start", stderr.getvalue())
        self.assertNotIn("Traceback", combined)

    def test_report_runs_on_fake_fixtures_without_raw_values(self):
        temp, root = self._fake_pdf_dir()
        self.addCleanup(temp.cleanup)

        report = build_private_template_pattern_collection_report(root, limit=1)
        output = "\n".join(
            [
                json.dumps(report["families"]),
                str(report["documents_scanned"]),
            ]
        )

        self.assertEqual(report["documents_scanned"], 1)
        self.assertGreaterEqual(len(report["families"]), 1)
        for forbidden in ["FAKE BROKER LLC", "FAKE-REF-001", "$2,850.00", "z_fake.pdf"]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, output)

    def test_cli_writes_safe_pattern_json_to_temp_output(self):
        temp, root = self._fake_pdf_dir()
        self.addCleanup(temp.cleanup)

        with tempfile.TemporaryDirectory() as output_dir:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--input-dir",
                        str(root),
                        "--confirm-private-local-run",
                        "--output-dir",
                        output_dir,
                        "--write-pattern-json",
                        "--write-family-md",
                        "--limit",
                        "1",
                    ]
                )
            pattern_path = Path(output_dir) / "redacted_template_patterns.json"
            family_path = Path(output_dir) / "template_family_candidates.md"
            pattern_exists = pattern_path.exists()
            family_exists = family_path.exists()
            payload = pattern_path.read_text(encoding="utf-8")
            console = stdout.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertTrue(pattern_exists)
        self.assertTrue(family_exists)
        self.assertIn("TEMPLATE_FAMILY_", console)
        self.assertIn("redacted_template_patterns.json", console)
        self.assertNotIn("FAKE BROKER LLC", payload)
        self.assertNotIn("FAKE BROKER LLC", console)
        self.assertNotIn(str(root), console)
        self.assertNotIn(output_dir, console)


if __name__ == "__main__":
    unittest.main()
