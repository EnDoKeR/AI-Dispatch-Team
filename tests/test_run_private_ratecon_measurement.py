import io
import inspect
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts import run_private_ratecon_measurement
from scripts.run_private_ratecon_measurement import (
    build_private_ratecon_measurement_report,
    format_private_measurement_report,
    main,
)
from tests.fixtures.document_ai.pdf_triage.fake_pdf_factory import (
    write_fake_empty_text_pdf,
    write_fake_text_pdf,
)


class PrivateRateConMeasurementCliTests(unittest.TestCase):
    def _fake_pdf_dir(self, count=2):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        write_fake_text_pdf(root, file_name="b_fake.pdf")
        if count > 1:
            write_fake_empty_text_pdf(root, file_name="a_fake.pdf")
        return temp, root

    def test_cli_refuses_without_confirm_flag(self):
        temp, root = self._fake_pdf_dir()
        self.addCleanup(temp.cleanup)
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = main(["--input-dir", str(root)])

        self.assertEqual(exit_code, 2)
        self.assertIn("--confirm-private-local-run", buffer.getvalue())

    def test_cli_missing_input_directory_returns_friendly_error(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing-ratecon-measurement-cli-dir"

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "--input-dir",
                        str(missing),
                        "--confirm-private-local-run",
                    ]
                )

        combined_output = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(exit_code, 2)
        self.assertIn("Private RateCon measurement could not start.", stderr.getvalue())
        self.assertIn("private input directory does not exist", stderr.getvalue())
        self.assertIn("start with --limit 3", stderr.getvalue())
        self.assertNotIn("Traceback", combined_output)

    def test_cli_placeholder_input_directory_returns_friendly_error(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    r"C:\path\to\private\ratecons",
                    "--confirm-private-local-run",
                ]
            )

        combined_output = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(exit_code, 2)
        self.assertIn("looks like an example placeholder", stderr.getvalue())
        self.assertIn("Replace the example path", stderr.getvalue())
        self.assertNotIn("Traceback", combined_output)

    def test_cli_help_includes_safety_wording(self):
        buffer = io.StringIO()

        with self.assertRaises(SystemExit) as raised:
            with redirect_stdout(buffer):
                main(["--help"])

        output = buffer.getvalue().lower()
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("never prints raw text", output)
        self.assertIn("private values", output)

    def test_report_uses_aliases_and_safe_statuses(self):
        temp, root = self._fake_pdf_dir()
        self.addCleanup(temp.cleanup)

        report = build_private_ratecon_measurement_report(root, limit=2)
        output = "\n".join(format_private_measurement_report(report))

        self.assertEqual(report["document_count"], 2)
        self.assertIn("RATECON_001", output)
        self.assertIn("candidate_counts_by_field", output)
        self.assertNotIn("b_fake.pdf", output)
        self.assertNotIn("a_fake.pdf", output)
        self.assertNotIn("TRUCKLOAD RATE CONFIRMATION", output)
        self.assertNotIn("FAKE BROKER LLC", output)

    def test_cli_writes_safe_json_and_csv_to_custom_temp_output(self):
        temp, root = self._fake_pdf_dir()
        self.addCleanup(temp.cleanup)

        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "--input-dir",
                        str(root),
                        "--confirm-private-local-run",
                        "--output-dir",
                        output_dir,
                        "--allow-custom-output-dir",
                        "--write-json",
                        "--write-csv",
                        "--limit",
                        "1",
                    ]
                )
            summary_path = Path(output_dir) / "safe_summary.json"
            csv_path = Path(output_dir) / "safe_summary.csv"
            summary_exists = summary_path.exists()
            csv_exists = csv_path.exists()
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertTrue(summary_exists)
        self.assertTrue(csv_exists)
        self.assertEqual(len(payload["rows"]), 1)
        self.assertNotIn("FAKE BROKER LLC", json.dumps(payload))
        self.assertIn("safe_outputs_written", console_output)
        self.assertNotIn(str(root), console_output)
        self.assertNotIn(output_dir, console_output)

    def test_cli_limit_controls_processed_rows(self):
        temp, root = self._fake_pdf_dir(count=2)
        self.addCleanup(temp.cleanup)

        report = build_private_ratecon_measurement_report(root, limit=1)

        self.assertEqual(report["document_count"], 1)

    def test_cli_does_not_import_deprecated_or_adapter_flows(self):
        source = inspect.getsource(run_private_ratecon_measurement)
        forbidden = [
            "scripts.import_ratecon",
            "scripts.read_ratecon",
            "DecisionEngine",
            "telegram",
            "DispatchCase",
            "pytesseract",
            "openai",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
