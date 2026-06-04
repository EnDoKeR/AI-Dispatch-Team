import io
import io
import inspect
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts import run_private_ratecon_measurement
from scripts.run_private_ratecon_measurement import (
    build_private_ratecon_measurement_report,
    format_private_measurement_report,
    main,
)
from app.document_ai.layout_provider import LayoutProviderDependencyError
from tests.fixtures.document_ai.broker_templates.fixture_loader import load_template_fixture
from tests.fixtures.document_ai.pdf_triage.fake_pdf_factory import (
    write_fake_empty_text_pdf,
    write_fake_text_pdf,
)


CLASSIFICATION_FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "document_classification"
    / "eligibility_calibration"
)


def load_classification_fixture(name):
    return (CLASSIFICATION_FIXTURE_DIR / name).read_text(encoding="utf-8")


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
        self.assertIn("extraction_relevant_count", output)
        self.assertIn("normal_load_movement_count", output)
        self.assertIn("classification_status_counts", output)
        self.assertIn("candidate_counts_by_field", output)
        self.assertNotIn("b_fake.pdf", output)
        self.assertNotIn("a_fake.pdf", output)
        self.assertNotIn("TRUCKLOAD RATE CONFIRMATION", output)
        self.assertNotIn("FAKE BROKER LLC", output)

    def test_cli_enable_layout_requires_provider(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    str(root),
                    "--confirm-private-local-run",
                    "--enable-layout-candidates",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("requires --layout-provider pdfplumber", stderr.getvalue())

    def test_cli_private_eval_values_require_shadow_audit(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    str(root),
                    "--confirm-private-local-run",
                    "--include-private-eval-values",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn(
            "--include-private-eval-values requires --ratecon-shadow-document-pipeline and --write-ratecon-shadow-audit",
            stderr.getvalue(),
        )

    def test_cli_refuses_unknown_layout_provider(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    str(root),
                    "--confirm-private-local-run",
                    "--layout-provider",
                    "unknown",
                    "--enable-layout-candidates",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("unknown layout provider", stderr.getvalue())

    def test_cli_explicit_pdfplumber_missing_dependency_returns_friendly_error(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch(
            "app.document_ai.measurement_cli.ratecon_private_safety.require_provider_dependency",
            side_effect=LayoutProviderDependencyError("missing"),
        ):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "--input-dir",
                        str(root),
                        "--confirm-private-local-run",
                        "--layout-provider",
                        "pdfplumber",
                        "--enable-layout-candidates",
                    ]
                )

        combined_output = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(exit_code, 2)
        self.assertIn("pdfplumber is not installed", stderr.getvalue())
        self.assertNotIn("Traceback", combined_output)

    def test_cli_shadow_mode_does_not_require_pdfplumber_dependency(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch(
            "app.document_ai.measurement_cli.ratecon_private_safety.require_provider_dependency",
            side_effect=AssertionError("pdfplumber dependency check should not run"),
        ):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "--input-dir",
                        str(root),
                        "--confirm-private-local-run",
                        "--ratecon-shadow-document-pipeline",
                        "--write-ratecon-shadow-audit",
                        "--dry-run",
                    ]
                )

        combined_output = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("documents_measured", stdout.getvalue())
        self.assertNotIn("Traceback", combined_output)

    def test_cli_accepts_shadow_layout_provider_flags_without_legacy_layout_provider(self):
        fake_report = {"rows": [], "aggregate": {}, "document_count": 0}
        with tempfile.TemporaryDirectory() as output_dir:
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ) as build_report:
                exit_code = main(
                    [
                        "--input-dir",
                        output_dir,
                        "--confirm-private-local-run",
                        "--ratecon-shadow-document-pipeline",
                        "--ratecon-shadow-layout-provider",
                        "auto",
                        "--ratecon-shadow-table-profile",
                        "lines",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            build_report.call_args.kwargs["ratecon_shadow_layout_provider"],
            "auto",
        )
        self.assertEqual(
            build_report.call_args.kwargs["ratecon_shadow_table_profile"],
            "lines",
        )

    def test_cli_accepts_shadow_load_candidate_profile_flag(self):
        fake_report = {"rows": [], "aggregate": {}, "document_count": 0}
        with tempfile.TemporaryDirectory() as output_dir:
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ) as build_report:
                exit_code = main(
                    [
                        "--input-dir",
                        output_dir,
                        "--confirm-private-local-run",
                        "--ratecon-shadow-document-pipeline",
                        "--ratecon-shadow-load-candidate-profile",
                        "header_recall_table_safety_v1",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            build_report.call_args.kwargs["ratecon_shadow_load_candidate_profile"],
            "header_recall_table_safety_v1",
        )

    def test_cli_accepts_field_scoped_shadow_ranking_flags(self):
        fake_report = {"rows": [], "aggregate": {}, "document_count": 0}
        with tempfile.TemporaryDirectory() as output_dir:
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ) as build_report:
                exit_code = main(
                    [
                        "--input-dir",
                        output_dir,
                        "--confirm-private-local-run",
                        "--ratecon-shadow-document-pipeline",
                        "--ratecon-shadow-load-ranking-profile",
                        "header_recall_table_safety_v1",
                        "--ratecon-shadow-rate-ranking-profile",
                        "gold_diagnostic_v1",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            build_report.call_args.kwargs["ratecon_shadow_load_ranking_profile"],
            "header_recall_table_safety_v1",
        )
        self.assertEqual(
            build_report.call_args.kwargs["ratecon_shadow_rate_ranking_profile"],
            "gold_diagnostic_v1",
        )

    def test_cli_accepts_shadow_load_abstention_profile(self):
        fake_report = {"rows": [], "aggregate": {}, "document_count": 0}
        with tempfile.TemporaryDirectory() as output_dir:
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ) as build_report:
                exit_code = main(
                    [
                        "--input-dir",
                        output_dir,
                        "--confirm-private-local-run",
                        "--ratecon-shadow-document-pipeline",
                        "--ratecon-shadow-load-ranking-profile",
                        "header_recall_table_abstain_v1",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            build_report.call_args.kwargs["ratecon_shadow_load_ranking_profile"],
            "header_recall_table_abstain_v1",
        )

    def test_cli_accepts_shadow_rate_money_abstention_profile(self):
        fake_report = {"rows": [], "aggregate": {}, "document_count": 0}
        with tempfile.TemporaryDirectory() as output_dir:
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ) as build_report:
                exit_code = main(
                    [
                        "--input-dir",
                        output_dir,
                        "--confirm-private-local-run",
                        "--ratecon-shadow-document-pipeline",
                        "--ratecon-shadow-rate-ranking-profile",
                        "money_abstain_v1",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            build_report.call_args.kwargs["ratecon_shadow_rate_ranking_profile"],
            "money_abstain_v1",
        )

    def test_cli_enable_layout_fusion_requires_layout_candidates(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    str(root),
                    "--confirm-private-local-run",
                    "--enable-layout-fusion",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("--enable-layout-fusion requires --enable-layout-candidates", stderr.getvalue())

    def test_cli_enable_stop_span_requires_layout_candidates(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    str(root),
                    "--confirm-private-local-run",
                    "--enable-stop-span-extractor",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("requires --enable-layout-candidates", stderr.getvalue())

    def test_cli_compare_stop_span_requires_extractor(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    str(root),
                    "--confirm-private-local-run",
                    "--layout-provider",
                    "pdfplumber",
                    "--enable-layout-candidates",
                    "--compare-stop-span-to-stop-group-pipeline",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("requires --enable-stop-span-extractor", stderr.getvalue())

    def test_report_includes_safe_layout_status_counts_when_enabled(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)

        report = build_private_ratecon_measurement_report(
            root,
            limit=1,
            layout_provider_name="pdfplumber",
            enable_layout_candidates=True,
            compare_layout_to_text_baseline=True,
        )
        output = "\n".join(format_private_measurement_report(report))

        self.assertIn("layout_provider_status_counts", output)
        self.assertIn("layout_candidate_counts_by_field", output)
        self.assertIn("layout_evidence_type_counts", output)
        self.assertNotIn("FAKE BROKER LLC", output)
        self.assertNotIn("TRUCKLOAD RATE CONFIRMATION", output)

    def test_report_includes_safe_fusion_fields_when_enabled(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)

        report = build_private_ratecon_measurement_report(
            root,
            limit=1,
            layout_provider_name="pdfplumber",
            enable_layout_candidates=True,
            enable_layout_fusion=True,
            compare_layout_to_text_baseline=True,
        )
        output = "\n".join(format_private_measurement_report(report))

        self.assertIn("fusion_attempted_count", output)
        self.assertIn("fusion_enabled", output)
        self.assertIn("stop_group_count", output)
        self.assertIn("normalized_stop_count_total", output)
        self.assertIn("premerge_stop_group_count_total", output)
        self.assertIn("post_dedupe_stop_group_count_total", output)
        self.assertIn("stop_field_status_counts", output)
        self.assertIn("normalized_stop_improved_fields", output)
        self.assertIn("prevented_regression_count", output)
        self.assertNotIn("FAKE BROKER LLC", output)
        self.assertNotIn("TRUCKLOAD RATE CONFIRMATION", output)

    def test_report_includes_stop_span_comparison_fields_when_enabled(self):
        fake_report = {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "stop_span_extractor_enabled": True,
                    "stop_span_comparison_enabled": True,
                    "old_raw_stop_groups": 8,
                    "old_normalized_stops": 8,
                    "span_anchor_count": 2,
                    "stop_span_count": 2,
                    "span_normalized_stop_count": 2,
                    "span_pickup_count": 1,
                    "span_delivery_count": 1,
                    "span_unknown_count": 0,
                    "span_date_resolved_count": 2,
                    "span_date_missing_count": 0,
                    "span_time_resolved_count": 1,
                    "span_time_missing_count": 1,
                    "span_review_required_count": 1,
                    "span_passthrough_detected": False,
                }
            ],
            "aggregate": {
                "stop_span_extractor_attempted_count": 1,
                "span_anchor_count_total": 2,
                "stop_span_count_total": 2,
                "span_normalized_stop_count_total": 2,
                "span_pickup_count_total": 1,
                "span_delivery_count_total": 1,
                "span_unknown_count_total": 0,
                "span_date_resolved_count_total": 2,
                "span_date_missing_count_total": 0,
                "span_time_resolved_count_total": 1,
                "span_time_missing_count_total": 1,
                "span_review_required_count_total": 1,
                "span_passthrough_count": 0,
            },
            "document_count": 1,
        }

        output = "\n".join(format_private_measurement_report(fake_report))

        self.assertIn("stop_span_extractor_attempted_count: 1", output)
        self.assertIn("old_raw_stop_groups: 8", output)
        self.assertIn("span_anchor_count: 2", output)
        self.assertIn("span_passthrough_detected: False", output)
        self.assertNotIn("FAKE BROKER LLC", output)

    def test_report_includes_safe_layout_diagnostics_when_enabled(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)

        report = build_private_ratecon_measurement_report(
            root,
            limit=1,
            layout_provider_name="pdfplumber",
            enable_layout_candidates=True,
            enable_layout_fusion=True,
            layout_diagnostics=True,
            pdfplumber_table_profile="lines",
        )
        output = "\n".join(format_private_measurement_report(report))

        self.assertIn("layout_quality_bucket_counts", output)
        self.assertIn("layout_total_word_count", output)
        self.assertIn("layout_stop_signal_counts", output)
        self.assertIn("layout_likely_issue_bucket", output)
        self.assertIn("layout_table_settings_profile", output)
        self.assertNotIn("FAKE BROKER LLC", output)

    def test_cli_writes_safe_layout_diagnostics_report(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)

        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with patch(
                "app.document_ai.measurement_cli.ratecon_private_safety.require_provider_dependency",
                return_value=True,
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            str(root),
                            "--confirm-private-local-run",
                            "--layout-provider",
                            "pdfplumber",
                            "--enable-layout-candidates",
                            "--layout-diagnostics",
                            "--output-dir",
                            output_dir,
                            "--allow-custom-output-dir",
                        ]
                    )
            diagnostics_path = Path(output_dir) / "layout_provider_diagnostics.md"
            exists = diagnostics_path.exists()
            text = diagnostics_path.read_text(encoding="utf-8")
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertTrue(exists)
        self.assertIn("layout_diagnostics_written", console_output)
        self.assertNotIn(str(root), console_output)
        self.assertNotIn(output_dir, console_output)
        self.assertNotIn("FAKE BROKER LLC", text)

    def test_cli_refuses_table_profile_comparison_without_pdfplumber(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    str(root),
                    "--confirm-private-local-run",
                    "--compare-pdfplumber-table-profiles",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("requires --layout-provider pdfplumber", stderr.getvalue())

    def test_report_can_compare_pdfplumber_table_profiles_safely(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)

        report = build_private_ratecon_measurement_report(
            root,
            limit=1,
            layout_provider_name="pdfplumber",
            enable_layout_candidates=True,
            compare_pdfplumber_table_profiles_enabled=True,
        )
        output = "\n".join(format_private_measurement_report(report))

        self.assertIn("table_profile_comparison_count", output)
        self.assertNotIn("FAKE BROKER LLC", output)
        self.assertNotIn("TRUCKLOAD RATE CONFIRMATION", output)

    def test_cli_invalid_pdfplumber_table_profile_exits_safely(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with self.assertRaises(SystemExit) as raised:
            with redirect_stderr(stderr):
                main(
                    [
                        "--input-dir",
                        str(root),
                        "--confirm-private-local-run",
                        "--layout-provider",
                        "pdfplumber",
                        "--enable-layout-candidates",
                        "--pdfplumber-table-profile",
                        "not-a-profile",
                    ]
                )

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("invalid choice", stderr.getvalue())

    def test_cli_refuses_regression_debug_without_fusion(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    str(root),
                    "--confirm-private-local-run",
                    "--allow-layout-regression-for-debug",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("requires --enable-layout-fusion", stderr.getvalue())

    def test_cli_refuses_private_stop_values_without_packet_write(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    str(root),
                    "--confirm-private-local-run",
                    "--include-private-stop-values-local-only",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("requires --write-stop-review-packet", stderr.getvalue())

    def test_cli_refuses_private_review_values_without_review_export(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    str(root),
                    "--confirm-private-local-run",
                    "--include-private-review-values-local-only",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("requires --write-review-workbook or --write-review-csvs", stderr.getvalue())

    def test_cli_refuses_google_sync_without_confirm(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    str(root),
                    "--confirm-private-local-run",
                    "--write-review-csvs",
                    "--sync-review-google-sheet",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("requires --confirm-google-review-sync", stderr.getvalue())

    def test_cli_refuses_google_sync_without_review_export(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    str(root),
                    "--confirm-private-local-run",
                    "--sync-review-google-sheet",
                    "--confirm-google-review-sync",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("requires --write-review-workbook or --write-review-csvs", stderr.getvalue())

    def test_cli_refuses_google_private_values_without_sync(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "--input-dir",
                    str(root),
                    "--confirm-private-local-run",
                    "--include-private-review-values-google-test-only",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("requires --sync-review-google-sheet", stderr.getvalue())

    def test_cli_writes_shareable_stop_review_packet_without_values(self):
        fake_report = {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "normalized_stop_set": {
                        "document_alias": "RATECON_001",
                        "stops": [
                            {
                                "stop_id": "STOP_001",
                                "stop_type": "pickup",
                                "sequence": 1,
                                "fields": [
                                    {
                                        "field_name": "location",
                                        "status": "resolved",
                                        "confidence": "HIGH",
                                        "selected_value": "FAKE_SECRET_STOP_VALUE",
                                        "evidence_refs": [{"evidence_type": "table_cell", "page_number": 1}],
                                        "warning_codes": [],
                                    }
                                ],
                            }
                        ],
                    },
                }
            ],
            "aggregate": {},
            "document_count": 1,
        }
        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            output_dir,
                            "--confirm-private-local-run",
                            "--output-dir",
                            output_dir,
                            "--allow-custom-output-dir",
                            "--write-stop-review-packet",
                        ]
                    )
            md_text = (Path(output_dir) / "stop_review_packet.md").read_text(encoding="utf-8")
            csv_text = (Path(output_dir) / "stop_review_packet.csv").read_text(encoding="utf-8")
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("stop_review_packet_written", console_output)
        self.assertNotIn("FAKE_SECRET_STOP_VALUE", console_output)
        self.assertNotIn("FAKE_SECRET_STOP_VALUE", md_text)
        self.assertNotIn("FAKE_SECRET_STOP_VALUE", csv_text)
        self.assertNotIn("selected_value_local_only", md_text)

    def test_cli_local_private_stop_review_packet_never_prints_values(self):
        fake_report = {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "normalized_stop_set": {
                        "document_alias": "RATECON_001",
                        "stops": [
                            {
                                "stop_id": "STOP_001",
                                "stop_type": "delivery",
                                "sequence": 2,
                                "fields": [
                                    {
                                        "field_name": "date",
                                        "status": "resolved",
                                        "confidence": "HIGH",
                                        "selected_value": "FAKE_PRIVATE_DATE_VALUE",
                                        "evidence_refs": [{"evidence_type": "table_cell", "page_number": 2}],
                                        "warning_codes": [],
                                    }
                                ],
                            }
                        ],
                    },
                }
            ],
            "aggregate": {},
            "document_count": 1,
        }
        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            output_dir,
                            "--confirm-private-local-run",
                            "--output-dir",
                            output_dir,
                            "--allow-custom-output-dir",
                            "--write-stop-review-packet",
                            "--include-private-stop-values-local-only",
                        ]
                    )
            md_text = (Path(output_dir) / "stop_review_packet.md").read_text(encoding="utf-8")
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("LOCAL PRIVATE REVIEW ONLY", md_text)
        self.assertIn("FAKE_PRIVATE_DATE_VALUE", md_text)
        self.assertNotIn("FAKE_PRIVATE_DATE_VALUE", console_output)

    def test_cli_writes_safe_stop_provenance_report(self):
        fake_report = {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "normalized_stop_count": 2,
                    "stop_duplicate_removed_count": 0,
                    "stop_noise_removed_count": 0,
                    "stop_group_provenance_summary": {
                        "document_alias": "RATECON_001",
                        "raw_group_count": 2,
                        "groups_by_source_type": {"table_row": 2},
                        "groups_by_page": {"1": 2},
                        "groups_by_table": {"T1": 2},
                        "groups_by_row_key": {"1|T1|1": 1, "1|T1|2": 1},
                        "groups_by_section_role": {"STOP_TABLE": 2},
                        "groups_by_trigger_label": {"pickup": 1, "delivery": 1},
                        "table_row_merge_candidate_count": 0,
                        "section_cluster_merge_candidate_count": 0,
                        "duplicate_candidate_count": 0,
                        "noise_candidate_count": 0,
                        "warning_codes": [],
                    },
                }
            ],
            "aggregate": {},
            "document_count": 1,
        }
        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            output_dir,
                            "--confirm-private-local-run",
                            "--output-dir",
                            output_dir,
                            "--allow-custom-output-dir",
                            "--write-stop-provenance-report",
                        ]
                    )
            md_text = (Path(output_dir) / "stop_group_provenance_report.md").read_text(
                encoding="utf-8"
            )
            json_text = (Path(output_dir) / "stop_group_provenance.json").read_text(
                encoding="utf-8"
            )
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("stop_provenance_report_written", console_output)
        self.assertIn("stop_group_provenance_report.md", console_output)
        self.assertNotIn(output_dir, console_output)
        self.assertIn("RATECON_001", md_text)
        self.assertIn("RATECON_001", json_text)
        self.assertNotIn("FAKE_SECRET_STOP_VALUE", md_text + json_text + console_output)

    def test_cli_writes_google_sheet_export_without_printing_names(self):
        fake_report = {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "document_type": "LOAD_CONFIRMATION",
                    "classification_status": "classified",
                    "extraction_relevant": True,
                    "normal_load_movement": True,
                    "extraction_status": "TEXT_EXTRACTED",
                    "layout_provider_status": "success",
                    "field_statuses": [{"field_name": "rate", "status": "resolved"}],
                    "stop_pipeline_trace": {
                        "passthrough_detected": False,
                        "first_stage_that_changed": "post_single_line_cluster",
                    },
                }
            ],
            "aggregate": {},
            "document_count": 1,
            "local_document_names_by_alias": {"RATECON_001": "LoadConfirmation1"},
        }
        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            output_dir,
                            "--confirm-private-local-run",
                            "--output-dir",
                            output_dir,
                            "--allow-custom-output-dir",
                            "--write-google-sheet-export",
                            "--natural-sort-inputs",
                        ]
                    )
            csv_text = (Path(output_dir) / "ratecon_review_google_sheet.csv").read_text(
                encoding="utf-8"
            )
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("google_sheet_export_written", console_output)
        self.assertIn("ratecon_review_google_sheet.csv", console_output)
        self.assertIn("LoadConfirmation1", csv_text)
        self.assertNotIn("LoadConfirmation1", console_output)
        self.assertNotIn(output_dir, console_output)

    def test_cli_writes_candidate_coverage_artifacts_without_values(self):
        fake_report = {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "document_type": "LOAD_CONFIRMATION",
                    "classification_status": "classified",
                    "extraction_relevant": True,
                    "normal_load_movement": True,
                    "extraction_status": "TEXT_EXTRACTED",
                    "layout_provider_status": "success",
                    "field_statuses": [
                        {
                            "field_name": "pickup_date",
                            "status": "missing",
                            "candidate_count": 0,
                            "selected_value": "FAKE_PRIVATE_DATE_VALUE",
                        }
                    ],
                    "missing_fields": ["pickup_date"],
                    "stop_span_coverage_metrics": {
                        "line_feature_count_by_label_category": {
                            "date": 1,
                            "pickup": 1,
                        },
                        "anchor_count_by_type": {"pickup": 1},
                        "span_count_by_type": {"pickup": 1},
                        "span_field_candidate_count_by_field": {},
                        "normalized_stop_field_count_by_field": {},
                        "core_field_mapping_count_by_field": {},
                    },
                }
            ],
            "aggregate": {},
            "document_count": 1,
        }
        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            output_dir,
                            "--confirm-private-local-run",
                            "--output-dir",
                            output_dir,
                            "--allow-custom-output-dir",
                            "--write-candidate-coverage",
                        ]
                    )
            json_text = (Path(output_dir) / "candidate_coverage.json").read_text(
                encoding="utf-8"
            )
            md_text = (Path(output_dir) / "candidate_coverage.md").read_text(
                encoding="utf-8"
            )
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("candidate_coverage_written", console_output)
        self.assertIn("candidate_coverage.json", console_output)
        self.assertIn("pickup_date", json_text)
        self.assertIn("Candidate Coverage Analysis", md_text)
        self.assertNotIn("FAKE_PRIVATE_DATE_VALUE", console_output + json_text + md_text)
        self.assertNotIn(output_dir, console_output)

    def test_cli_writes_load_identifier_audit_artifacts_without_values(self):
        fake_report = {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "load_identifier_audit_records": [
                        {
                            "measurement_alias": "RATECON_001",
                            "stage": "non_primary_reference_rejected",
                            "status": "rejected",
                            "reason": "only_non_primary_references_found",
                            "identifier_label_category": "po_number",
                            "typed_reference_count": 1,
                            "rejected_non_primary_count": 1,
                        }
                    ],
                    "load_identifier_coverage_metrics": {
                        "typed_reference_candidate_count": 1,
                        "rejected_reference_as_load_id_count": 1,
                        "private_values_included": False,
                        "raw_text_included": False,
                    },
                }
            ],
            "aggregate": {},
            "document_count": 1,
        }
        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            output_dir,
                            "--confirm-private-local-run",
                            "--output-dir",
                            output_dir,
                            "--allow-custom-output-dir",
                            "--write-load-identifier-audit",
                        ]
                    )
            json_text = (Path(output_dir) / "load_identifier_coverage.json").read_text(
                encoding="utf-8"
            )
            md_text = (Path(output_dir) / "load_identifier_coverage.md").read_text(
                encoding="utf-8"
            )
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("load_identifier_audit_written", console_output)
        self.assertIn("load_identifier_coverage.json", console_output)
        self.assertIn("only_non_primary_references_found", json_text)
        self.assertIn("Load Identifier Coverage Audit", md_text)
        self.assertNotIn("FAKE-PO", console_output + json_text + md_text)
        self.assertNotIn(output_dir, console_output)

    def test_cli_writes_load_identifier_source_line_audit_without_values(self):
        fake_report = {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "triage_route": "DIGITAL_TEXT",
                    "extraction_status": "TEXT_EXTRACTED",
                    "char_count": 100,
                    "load_identifier_source_line_metrics": {
                        "identifier_like_source_line_count": 1,
                        "scoped_identifier_like_source_line_count": 1,
                        "label_detected_count": 1,
                        "label_classified_count": 1,
                        "typed_candidate_count": 1,
                        "primary_candidate_count": 1,
                        "core_mapping_count": 0,
                        "rejected_non_primary_count": 0,
                    },
                }
            ],
            "aggregate": {},
            "document_count": 1,
        }
        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            output_dir,
                            "--confirm-private-local-run",
                            "--output-dir",
                            output_dir,
                            "--allow-custom-output-dir",
                            "--write-load-identifier-source-line-audit",
                        ]
                    )
            json_text = (
                Path(output_dir) / "load_identifier_source_line_audit_raw.json"
            ).read_text(encoding="utf-8")
            md_text = (
                Path(output_dir) / "load_identifier_source_line_audit_raw.md"
            ).read_text(encoding="utf-8")
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("load_identifier_source_line_audit_written", console_output)
        self.assertIn("load_identifier_source_line_audit_raw.json", console_output)
        self.assertIn("primary_candidate_not_core_mapped", json_text)
        self.assertIn("Load Identifier Source-Line Audit", md_text)
        self.assertNotIn("FAKE-", console_output + json_text + md_text)
        self.assertNotIn(output_dir, console_output)

    def test_cli_writes_rate_forensics_without_money_values(self):
        fake_report = {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "rate_forensics_records": [
                        {
                            "measurement_alias": "RATECON_001",
                            "rate_candidate_count": 2,
                            "main_rate_candidate_count": 2,
                            "conflict_present": True,
                            "conflict_reason": "multiple_strong_totals",
                            "category_counts": {"main_total_carrier_pay": 2},
                            "source_section_counts": {"rate_summary": 2},
                            "private_values_included": False,
                            "raw_text_included": False,
                            "money_values_included": False,
                        }
                    ],
                }
            ],
            "aggregate": {},
            "document_count": 1,
        }
        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            output_dir,
                            "--confirm-private-local-run",
                            "--output-dir",
                            output_dir,
                            "--allow-custom-output-dir",
                            "--write-rate-forensics",
                        ]
                    )
            json_text = (
                Path(output_dir) / "rate_candidate_forensics_raw.json"
            ).read_text(encoding="utf-8")
            md_text = (Path(output_dir) / "rate_candidate_forensics_raw.md").read_text(
                encoding="utf-8"
            )
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("rate_forensics_written", console_output)
        self.assertIn("rate_candidate_forensics_raw.json", console_output)
        self.assertIn("multiple_strong_totals", json_text)
        self.assertIn("Rate Candidate Forensics", md_text)
        self.assertNotIn("$", console_output + json_text + md_text)
        self.assertNotIn("FAKE_RATE", console_output + json_text + md_text)
        self.assertNotIn(output_dir, console_output)

    def test_cli_writes_rate_conflict_audit_without_money_values(self):
        fake_report = {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "rate_conflict_audit_records": [
                        {
                            "measurement_alias": "RATECON_001",
                            "rate_candidate_count": 2,
                            "main_rate_candidate_count": 2,
                            "different_strong_total_count": 2,
                            "conflict_present": True,
                            "conflict_reason": "multiple_different_strong_totals",
                            "review_required": True,
                            "private_values_included": False,
                            "raw_text_included": False,
                            "money_values_included": False,
                        }
                    ],
                }
            ],
            "aggregate": {},
            "document_count": 1,
        }
        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            output_dir,
                            "--confirm-private-local-run",
                            "--output-dir",
                            output_dir,
                            "--allow-custom-output-dir",
                            "--write-rate-conflict-audit",
                        ]
                    )
            json_text = (Path(output_dir) / "rate_conflict_audit_raw.json").read_text(
                encoding="utf-8"
            )
            md_text = (Path(output_dir) / "rate_conflict_audit_raw.md").read_text(
                encoding="utf-8"
            )
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("rate_conflict_audit_written", console_output)
        self.assertIn("rate_conflict_audit_raw.json", console_output)
        self.assertIn("multiple_different_strong_totals", json_text)
        self.assertIn("Rate Conflict Audit", md_text)
        self.assertNotIn("$", console_output + json_text + md_text)
        self.assertNotIn("FAKE_RATE", console_output + json_text + md_text)
        self.assertNotIn(output_dir, console_output)

    def test_cli_writes_ratecon_shadow_audit_without_console_values(self):
        fake_report = {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "ratecon_shadow_audit_records": [
                        {
                            "document_id": "RATECON_001",
                            "file_name": "",
                            "file_hash": "",
                            "legacy": {
                                "fields_present": ["load_number"],
                                "pickup_count": 1,
                                "delivery_count": 1,
                            },
                            "shadow": {
                                "success": True,
                                "needs_review": True,
                                "review_reasons": ["MISSING_CRITICAL_FIELD:load_number"],
                                "resolved_fields": {
                                    "load_number": {
                                        "value": "",
                                        "confidence": 0.0,
                                        "evidence_text": "",
                                        "source": "",
                                        "candidate_count": 0,
                                    }
                                },
                            },
                            "triage": {
                                "pdf_type": "born_digital",
                                "page_count": 1,
                                "native_text_available": True,
                                "native_text_token_count": 20,
                                "ocr_required": False,
                                "routing_decision": "native_layout",
                                "quality_flags": [],
                            },
                            "artifact_summary": {
                                "source": "native",
                                "page_count": 1,
                                "line_count": 4,
                                "word_count": 0,
                                "table_count": 0,
                                "full_text_length": 200,
                            },
                            "candidate_summary": {
                                "total_candidates": 1,
                                "candidates_by_field": {"total_carrier_rate": 1},
                                "candidates_by_source": {"native_text": 1},
                            },
                            "legacy_shadow_comparison": {
                                "load_number": "legacy_only",
                                "total_carrier_rate": "shadow_only",
                            },
                            "failure_attribution": {
                                "codes": ["MISSING_LOAD_NUMBER_CANDIDATE"],
                                "primary_suspected_layer": "candidate_generation",
                            },
                            "private_values_included": False,
                            "raw_text_included": False,
                        }
                    ],
                }
            ],
            "aggregate": {},
            "document_count": 1,
        }
        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            output_dir,
                            "--confirm-private-local-run",
                            "--output-dir",
                            output_dir,
                            "--allow-custom-output-dir",
                            "--ratecon-shadow-document-pipeline",
                            "--write-ratecon-shadow-audit",
                        ]
                    )
            jsonl_text = (
                Path(output_dir) / "ratecon_shadow_document_pipeline_audit.jsonl"
            ).read_text(encoding="utf-8")
            summary_text = (
                Path(output_dir) / "ratecon_shadow_document_pipeline_summary.json"
            ).read_text(encoding="utf-8")
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("ratecon_shadow_audit_written", console_output)
        self.assertIn("ratecon_shadow_document_pipeline_audit.jsonl", console_output)
        self.assertIn("MISSING_LOAD_NUMBER_CANDIDATE", jsonl_text)
        self.assertIn("candidate_generation", summary_text)
        self.assertNotIn("FAKE_PRIVATE", console_output + jsonl_text + summary_text)
        self.assertNotIn(output_dir, console_output)

    def test_shadow_audit_requires_shadow_pipeline_flag(self):
        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with redirect_stderr(buffer):
                exit_code = main(
                    [
                        "--input-dir",
                        output_dir,
                        "--confirm-private-local-run",
                        "--output-dir",
                        output_dir,
                        "--allow-custom-output-dir",
                        "--write-ratecon-shadow-audit",
                    ]
                )

        self.assertEqual(exit_code, 2)
        self.assertIn(
            "--write-ratecon-shadow-audit requires --ratecon-shadow-document-pipeline",
            buffer.getvalue(),
        )

    def test_cli_writes_local_review_workbook_export_without_printing_values(self):
        fake_report = {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "document_type": "LOAD_CONFIRMATION",
                    "classification_status": "classified",
                    "extraction_relevant": True,
                    "normal_load_movement": True,
                    "extraction_status": "TEXT_EXTRACTED",
                    "layout_provider_status": "success",
                    "span_normalized_stop_count": 1,
                    "span_pickup_count": 1,
                    "span_delivery_count": 0,
                    "span_unknown_count": 0,
                    "span_date_resolved_count": 0,
                    "span_date_missing_count": 1,
                    "span_time_resolved_count": 0,
                    "span_time_missing_count": 1,
                    "span_review_required_count": 1,
                    "span_normalized_stop_set": {
                        "document_alias": "RATECON_001",
                        "stops": [
                            {
                                "stop_id": "span_stop_001",
                                "stop_type": "pickup",
                                "sequence": 1,
                                "review_required": True,
                                "fields": [
                                    {
                                        "field_name": "location",
                                        "status": "resolved",
                                        "confidence": "high",
                                        "selected_value": "FAKE_PRIVATE_LOCATION",
                                        "evidence_refs": [
                                            {"evidence_type": "layout_line", "page_number": 1}
                                        ],
                                    }
                                ],
                            }
                        ],
                    },
                    "field_statuses": [
                        {
                            "field_name": "rate",
                            "status": "resolved",
                            "selected_value": "FAKE_PRIVATE_RATE",
                        },
                        {"field_name": "broker_name", "status": "needs_review"},
                        {"field_name": "load_number", "status": "resolved"},
                        {"field_name": "pickup_location", "status": "resolved"},
                        {"field_name": "pickup_date", "status": "needs_review"},
                        {"field_name": "delivery_location", "status": "resolved"},
                        {"field_name": "delivery_date", "status": "resolved"},
                    ],
                }
            ],
            "aggregate": {},
            "document_count": 1,
            "local_document_names_by_alias": {"RATECON_001": "LoadConfirmation1"},
        }
        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            output_dir,
                            "--confirm-private-local-run",
                            "--output-dir",
                            output_dir,
                            "--allow-custom-output-dir",
                            "--write-review-workbook",
                            "--write-review-csvs",
                            "--include-private-review-values-local-only",
                        ]
                    )
            stop_csv = (Path(output_dir) / "ratecon_review_stop_review.csv").read_text(
                encoding="utf-8"
            )
            rate_csv = (Path(output_dir) / "ratecon_review_rate_review.csv").read_text(
                encoding="utf-8"
            )
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("review_workbook_export_written", console_output)
        self.assertIn("ratecon_review_stop_review.csv", console_output)
        self.assertIn("readiness_level_counts", console_output)
        self.assertIn("integrity_issue_counts", console_output)
        self.assertIn("FAKE_PRIVATE_LOCATION", stop_csv)
        self.assertIn("FAKE_PRIVATE_RATE", rate_csv)
        self.assertNotIn("FAKE_PRIVATE_LOCATION", console_output)
        self.assertNotIn("FAKE_PRIVATE_RATE", console_output)
        self.assertNotIn("LoadConfirmation1", console_output)
        self.assertNotIn(output_dir, console_output)

    def test_cli_syncs_review_google_sheet_with_mock_client(self):
        fake_report = {
            "rows": [
                {
                    "document_alias": "RATECON_001",
                    "document_type": "LOAD_CONFIRMATION",
                    "classification_status": "classified",
                    "extraction_relevant": True,
                    "normal_load_movement": True,
                    "extraction_status": "TEXT_EXTRACTED",
                    "layout_provider_status": "success",
                    "span_normalized_stop_count": 1,
                    "span_pickup_count": 1,
                    "span_delivery_count": 0,
                    "span_generic_stop_count": 0,
                    "span_unknown_count": 0,
                    "span_date_resolved_count": 0,
                    "span_date_missing_count": 1,
                    "span_time_resolved_count": 0,
                    "span_time_missing_count": 1,
                    "span_review_required_count": 1,
                    "span_normalized_stop_set": {
                        "stops": [
                            {
                                "stop_id": "span_stop_001",
                                "stop_type": "pickup",
                                "sequence": 1,
                                "review_required": True,
                                "fields": [
                                    {
                                        "field_name": "location",
                                        "status": "resolved",
                                        "confidence": "high",
                                        "selected_value": "FAKE_PRIVATE_GOOGLE_VALUE",
                                    }
                                ],
                            }
                        ],
                    },
                    "field_statuses": [
                        {"field_name": "rate", "status": "resolved"},
                        {"field_name": "broker_name", "status": "needs_review"},
                        {"field_name": "load_number", "status": "resolved"},
                        {"field_name": "pickup_location", "status": "resolved"},
                        {"field_name": "pickup_date", "status": "needs_review"},
                        {"field_name": "delivery_location", "status": "resolved"},
                        {"field_name": "delivery_date", "status": "resolved"},
                    ],
                }
            ],
            "aggregate": {},
            "document_count": 1,
            "local_document_names_by_alias": {"RATECON_001": "LoadConfirmation1"},
        }

        class FakeGoogleClient:
            rows_by_tab = None

            def batch_update_review_tabs(self, rows_by_tab):
                self.rows_by_tab = rows_by_tab
                return {
                    "tabs_updated": list(rows_by_tab),
                    "row_counts": {title: len(rows) for title, rows in rows_by_tab.items()},
                    "private_values_printed": False,
                    "credentials_printed": False,
                    "spreadsheet_id_printed": False,
                }

        fake_client = FakeGoogleClient()
        fake_config = type(
            "Config",
            (),
            {
                "spreadsheet_id": "fake-spreadsheet",
                "credentials_json_path": "fake-credentials.json",
                "worksheet_prefix": "RC_",
                "service_account_email": "ai-dispatch-sheet@ai-dispatch-team.iam.gserviceaccount.com",
                "default_sync_mode": "status_only",
            },
        )()

        with tempfile.TemporaryDirectory() as output_dir:
            buffer = io.StringIO()
            with patch(
                "scripts.run_private_ratecon_measurement.build_private_ratecon_measurement_report",
                return_value=fake_report,
            ), patch(
                "scripts.run_private_ratecon_measurement.sheets_review.load_google_sheets_review_config",
                return_value=fake_config,
            ), patch(
                "scripts.run_private_ratecon_measurement.sheets_review.connect_to_google_sheet",
                return_value=fake_client,
            ):
                with redirect_stdout(buffer):
                    exit_code = main(
                        [
                            "--input-dir",
                            output_dir,
                            "--confirm-private-local-run",
                            "--output-dir",
                            output_dir,
                            "--allow-custom-output-dir",
                            "--write-review-csvs",
                            "--sync-review-google-sheet",
                            "--confirm-google-review-sync",
                        ]
                    )
            console_output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("google_sheet_sync", console_output)
        self.assertIn("RC_Document_Summary", console_output)
        self.assertNotIn("FAKE_PRIVATE_GOOGLE_VALUE", console_output)
        payload = "\n".join(
            str(cell)
            for rows in fake_client.rows_by_tab.values()
            for row in rows
            for cell in row
        )
        self.assertNotIn("FAKE_PRIVATE_GOOGLE_VALUE", payload)

    def test_report_shows_tonu_and_non_ratecon_without_core_failure_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_fake_text_pdf(
                root,
                file_name="a_tonu.pdf",
                text=load_classification_fixture("fake_truck_order_not_used_payment.txt"),
            )
            write_fake_text_pdf(
                root,
                file_name="b_bol.pdf",
                text=load_classification_fixture("fake_bol_only.txt"),
            )
            report = build_private_ratecon_measurement_report(root)
            output = "\n".join(format_private_measurement_report(report))

        self.assertIn("tonu_count: 1", output)
        self.assertIn("normal_load_movement_count: 0", output)
        self.assertIn("non_applicable_fields", output)
        self.assertIn("skipped_by_scope", output)
        self.assertNotIn("BOL-6006", output)
        self.assertNotIn("TONU-4004", output)

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

    def test_cli_refuses_private_template_dir_without_allow_flag(self):
        temp, root = self._fake_pdf_dir()
        self.addCleanup(temp.cleanup)
        stderr = io.StringIO()

        with tempfile.TemporaryDirectory() as overlay_dir:
            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        "--input-dir",
                        str(root),
                        "--confirm-private-local-run",
                        "--private-template-dir",
                        overlay_dir,
                    ]
                )

        self.assertEqual(exit_code, 2)
        self.assertIn("private template overlay requires", stderr.getvalue())

    def test_cli_loads_private_overlay_and_redacts_template_identity(self):
        temp, root = self._fake_pdf_dir(count=1)
        self.addCleanup(temp.cleanup)

        with tempfile.TemporaryDirectory() as overlay_dir:
            private_template = dict(load_template_fixture("alpha_freight_mock_v1.json"))
            private_template["template_id"] = "private_real_template_secret"
            private_template["broker_key"] = "private_real_template_secret"
            private_template["display_name"] = "PRIVATE REAL BROKER SECRET"
            private_template["match_rules"] = [
                {
                    "keywords": ["TRUCKLOAD RATE CONFIRMATION"],
                    "aliases": [],
                    "exclude_keywords": [],
                    "mc_numbers": [],
                    "email_domains": [],
                    "min_keyword_hits": 1,
                    "confidence_boost": 0.8,
                    "confidence_penalty": 0.0,
                }
            ]
            Path(overlay_dir, "private_real_template_secret.json").write_text(
                json.dumps(private_template),
                encoding="utf-8",
            )
            report = build_private_ratecon_measurement_report(
                root,
                private_template_dir=overlay_dir,
                allow_private_template_overlay=True,
                limit=1,
            )
            output = "\n".join(format_private_measurement_report(report))

        self.assertIn("PRIVATE_TEMPLATE_001", output)
        self.assertIn("private_local", output)
        self.assertNotIn("PRIVATE REAL BROKER SECRET", output)
        self.assertNotIn("FAKE BROKER LLC", output)

    def test_cli_limit_controls_processed_rows(self):
        temp, root = self._fake_pdf_dir(count=2)
        self.addCleanup(temp.cleanup)

        report = build_private_ratecon_measurement_report(root, limit=1)

        self.assertEqual(report["document_count"], 1)

    def test_cli_does_not_import_deprecated_or_adapter_flows(self):
        source = inspect.getsource(run_private_ratecon_measurement)
        forbidden = [
            "argparse.ArgumentParser",
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

        self.assertIn("parse_private_ratecon_measurement_args", source)
        self.assertIn("validate_private_ratecon_measurement_config", source)
        self.assertIn("build_private_ratecon_output_paths", source)
        self.assertIn("write_private_ratecon_safe_outputs", source)
        self.assertIn("write_private_ratecon_review_packet_exports", source)
        self.assertIn("private_ratecon_review_export_labels", source)
        self.assertIn("write_private_ratecon_review_workbook_if_enabled", source)
        self.assertIn("run_private_ratecon_audit_exports", source)
        self.assertIn("output_file_labels", source)


if __name__ == "__main__":
    unittest.main()
