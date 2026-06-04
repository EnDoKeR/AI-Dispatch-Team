import io
import unittest
from contextlib import redirect_stdout

from app.document_ai.measurement_cli.ratecon_private_args import (
    build_private_ratecon_measurement_parser,
    parse_private_ratecon_measurement_args,
)
from app.document_ai.measurement_cli.ratecon_private_config import (
    build_private_ratecon_measurement_config,
)


class PrivateRateconMeasurementCliArgsTests(unittest.TestCase):
    def _option_strings(self):
        parser = build_private_ratecon_measurement_parser()
        return {
            option
            for action in parser._actions
            for option in action.option_strings
        }

    def test_parser_includes_existing_important_flags(self):
        options = self._option_strings()
        expected_flags = [
            "--input-dir",
            "--confirm-private-local-run",
            "--output-dir",
            "--write-json",
            "--write-csv",
            "--write-md",
            "--write-value-review-template",
            "--write-stop-review-packet",
            "--write-stop-provenance-report",
            "--write-google-sheet-export",
            "--write-review-workbook",
            "--write-review-csvs",
            "--ratecon-shadow-document-pipeline",
            "--write-ratecon-shadow-audit",
            "--ratecon-shadow-layout-provider",
            "--ratecon-shadow-table-profile",
            "--ratecon-shadow-load-ranking-profile",
            "--ratecon-shadow-rate-ranking-profile",
            "--ratecon-shadow-ocr-provider",
            "--include-private-eval-values",
            "--include-document-ai-debug",
            "--include-private-stop-values-local-only",
            "--include-private-review-values-local-only",
            "--include-private-review-values-google-test-only",
            "--sync-review-google-sheet",
            "--confirm-google-review-sync",
            "--allow-custom-output-dir",
        ]

        for flag in expected_flags:
            with self.subTest(flag=flag):
                self.assertIn(flag, options)

    def test_config_builder_maps_parsed_args(self):
        args = parse_private_ratecon_measurement_args(
            [
                "--input-dir",
                "tests/fixtures/document_ai",
                "--confirm-private-local-run",
                "--output-dir",
                ".local_outputs/private_ratecon_measurement_cli_args_test",
                "--limit",
                "7",
                "--write-json",
                "--ratecon-shadow-document-pipeline",
                "--write-ratecon-shadow-audit",
                "--include-private-eval-values",
            ]
        )

        config = build_private_ratecon_measurement_config(args)

        self.assertEqual(config.input_dir, "tests/fixtures/document_ai")
        self.assertTrue(config.confirm_private_local_run)
        self.assertEqual(config.limit, 7)
        self.assertTrue(config.write_json)
        self.assertTrue(config.ratecon_shadow_document_pipeline)
        self.assertTrue(config.write_ratecon_shadow_audit)
        self.assertTrue(config.include_private_eval_values)
        self.assertIn("output_dir", config.as_dict())

    def test_help_still_exits_successfully(self):
        output = io.StringIO()

        with self.assertRaises(SystemExit) as raised:
            with redirect_stdout(output):
                parse_private_ratecon_measurement_args(["--help"])

        self.assertEqual(raised.exception.code, 0)
        text = output.getvalue().lower()
        self.assertIn("never prints raw text", text)
        self.assertIn("private values", text)


if __name__ == "__main__":
    unittest.main()
