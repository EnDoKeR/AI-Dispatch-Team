import inspect
import unittest
from unittest.mock import patch

from app.document_ai.layout_provider import LayoutProviderDependencyError
from app.document_ai.measurement_cli import ratecon_private_args, ratecon_private_safety
from app.document_ai.measurement_cli.ratecon_private_args import (
    parse_private_ratecon_measurement_args,
)
from app.document_ai.measurement_cli.ratecon_private_config import (
    build_private_ratecon_measurement_config,
)
from app.document_ai.measurement_cli.ratecon_private_safety import (
    PrivateRateconMeasurementSafetyError,
    validate_private_ratecon_measurement_config,
)


def _config(*argv):
    args = parse_private_ratecon_measurement_args(list(argv))
    return build_private_ratecon_measurement_config(args)


class PrivateRateconMeasurementCliSafetyTests(unittest.TestCase):
    def assertSafetyErrorContains(self, argv, expected_text):
        with self.assertRaises(PrivateRateconMeasurementSafetyError) as raised:
            validate_private_ratecon_measurement_config(_config(*argv))
        self.assertIn(expected_text, str(raised.exception))
        return raised.exception

    def test_rejects_missing_confirm_flag(self):
        error = self.assertSafetyErrorContains(
            ["--input-dir", "tests/fixtures/document_ai"],
            "--confirm-private-local-run",
        )

        self.assertEqual(error.stream, "stdout")

    def test_rejects_unsafe_output_path_without_custom_flag_when_writing(self):
        error = self.assertSafetyErrorContains(
            [
                "--input-dir",
                "tests/fixtures/document_ai",
                "--confirm-private-local-run",
                "--output-dir",
                "unsafe_audit_outputs",
                "--write-json",
            ],
            "custom output directory requires",
        )

        self.assertEqual(error.style, "expected")

    def test_allows_local_outputs_path(self):
        config = _config(
            "--input-dir",
            "tests/fixtures/document_ai",
            "--confirm-private-local-run",
            "--output-dir",
            ".local_outputs/private_ratecon_measurement_cli_safety_test",
            "--write-json",
        )

        validate_private_ratecon_measurement_config(config)

    def test_allows_custom_output_path_when_explicit(self):
        config = _config(
            "--input-dir",
            "tests/fixtures/document_ai",
            "--confirm-private-local-run",
            "--output-dir",
            "sanitized_custom_output",
            "--allow-custom-output-dir",
            "--write-json",
        )

        validate_private_ratecon_measurement_config(config)

    def test_layout_candidates_require_provider(self):
        self.assertSafetyErrorContains(
            [
                "--input-dir",
                "tests/fixtures/document_ai",
                "--confirm-private-local-run",
                "--enable-layout-candidates",
            ],
            "requires --layout-provider pdfplumber",
        )

    def test_private_eval_values_require_shadow_audit(self):
        self.assertSafetyErrorContains(
            [
                "--input-dir",
                "tests/fixtures/document_ai",
                "--confirm-private-local-run",
                "--include-private-eval-values",
            ],
            "requires --ratecon-shadow-document-pipeline and --write-ratecon-shadow-audit",
        )

    def test_private_stop_values_require_review_packet(self):
        self.assertSafetyErrorContains(
            [
                "--input-dir",
                "tests/fixtures/document_ai",
                "--confirm-private-local-run",
                "--include-private-stop-values-local-only",
            ],
            "requires --write-stop-review-packet",
        )

    def test_private_review_values_require_review_export(self):
        self.assertSafetyErrorContains(
            [
                "--input-dir",
                "tests/fixtures/document_ai",
                "--confirm-private-local-run",
                "--include-private-review-values-local-only",
            ],
            "requires --write-review-workbook or --write-review-csvs",
        )

    def test_google_sync_requires_confirm_and_review_export(self):
        self.assertSafetyErrorContains(
            [
                "--input-dir",
                "tests/fixtures/document_ai",
                "--confirm-private-local-run",
                "--write-review-csvs",
                "--sync-review-google-sheet",
            ],
            "requires --confirm-google-review-sync",
        )
        self.assertSafetyErrorContains(
            [
                "--input-dir",
                "tests/fixtures/document_ai",
                "--confirm-private-local-run",
                "--sync-review-google-sheet",
                "--confirm-google-review-sync",
            ],
            "requires --write-review-workbook or --write-review-csvs",
        )

    def test_google_private_values_require_sync(self):
        self.assertSafetyErrorContains(
            [
                "--input-dir",
                "tests/fixtures/document_ai",
                "--confirm-private-local-run",
                "--include-private-review-values-google-test-only",
            ],
            "requires --sync-review-google-sheet",
        )

    def test_rejects_unknown_layout_provider(self):
        self.assertSafetyErrorContains(
            [
                "--input-dir",
                "tests/fixtures/document_ai",
                "--confirm-private-local-run",
                "--layout-provider",
                "unknown",
                "--enable-layout-candidates",
            ],
            "unknown layout provider",
        )

    def test_pdfplumber_dependency_error_is_friendly(self):
        config = _config(
            "--input-dir",
            "tests/fixtures/document_ai",
            "--confirm-private-local-run",
            "--layout-provider",
            "pdfplumber",
            "--enable-layout-candidates",
        )

        with patch(
            "app.document_ai.measurement_cli.ratecon_private_safety.require_provider_dependency",
            side_effect=LayoutProviderDependencyError("missing"),
        ):
            with self.assertRaises(PrivateRateconMeasurementSafetyError) as raised:
                validate_private_ratecon_measurement_config(config)

        self.assertIn("pdfplumber is not installed", str(raised.exception))

    def test_no_provider_dependency_check_for_shadow_only_pipeline(self):
        config = _config(
            "--input-dir",
            "tests/fixtures/document_ai",
            "--confirm-private-local-run",
            "--ratecon-shadow-document-pipeline",
            "--write-ratecon-shadow-audit",
            "--dry-run",
        )

        with patch(
            "app.document_ai.measurement_cli.ratecon_private_safety.require_provider_dependency",
            side_effect=AssertionError("provider dependency should not be checked"),
        ):
            validate_private_ratecon_measurement_config(config)

    def test_modules_do_not_process_pdfs_or_call_model_cloud_or_ocr(self):
        source = (
            inspect.getsource(ratecon_private_args)
            + inspect.getsource(ratecon_private_safety)
        )
        forbidden = [
            "measure_private_ratecon_pdf",
            "discover_private_pdfs",
            "write_private_measurement_outputs",
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
