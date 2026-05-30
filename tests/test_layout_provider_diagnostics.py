import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.document_ai.layout_provider_diagnostics import (
    ISSUE_PROVIDER_HAS_STOP_LABELS_BUT_NO_GROUPS,
    ISSUE_PROVIDER_NO_TABLES,
    QUALITY_EMPTY,
    QUALITY_RICH_LAYOUT,
    QUALITY_TABLE_LIKE,
    QUALITY_TEXT_ONLY,
    LAYOUT_PROVIDER_DIAGNOSTICS_MD,
    build_layout_provider_diagnostics,
    build_provider_document_diagnostics,
    build_provider_page_diagnostics,
    build_stop_evidence_signals,
    classify_layout_provider_diagnostic_issue,
    compare_pdfplumber_table_profiles,
    compute_layout_quality_bucket,
    summarize_layout_tables,
    summarize_stop_label_signals,
    write_layout_provider_diagnostics_report,
)
from app.document_ai.layout_artifacts import (
    build_layout_extraction_artifact,
    build_layout_line,
    build_layout_page_artifact,
    build_layout_table,
    build_layout_table_cell,
    build_layout_word,
)


class LayoutProviderDiagnosticsTests(unittest.TestCase):
    def test_page_diagnostics_serializes_safely(self):
        page = build_provider_page_diagnostics(
            page_number=1,
            word_count=12,
            line_count=4,
            table_count=1,
            table_cell_count=6,
            char_count=1000,
            warning_codes=["table_cells_sparse"],
        )

        dumped = json.dumps(page, sort_keys=True)

        self.assertIn('"page_number": 1', dumped)
        self.assertTrue(page["has_tables"])
        self.assertTrue(page["has_words"])
        self.assertTrue(page["has_lines"])
        self.assertNotIn("raw_text", dumped)

    def test_document_diagnostics_defaults_are_redacted(self):
        diagnostics = build_provider_document_diagnostics(
            document_alias="RATECON_001",
            provider_name="pdfplumber",
            provider_status="success",
            pages=[
                build_provider_page_diagnostics(
                    page_number=1,
                    word_count=80,
                    line_count=12,
                    table_count=1,
                    table_cell_count=16,
                )
            ],
            stop_evidence_signals=build_stop_evidence_signals(
                pickup_label_hits=1,
                delivery_label_hits=1,
                date_label_hits=2,
                table_stop_like_rows=2,
            ),
        )

        dumped = json.dumps(diagnostics, sort_keys=True)

        self.assertFalse(diagnostics["raw_text_included"])
        self.assertTrue(diagnostics["private_values_redacted"])
        self.assertEqual(diagnostics["layout_quality_bucket"], QUALITY_RICH_LAYOUT)
        self.assertEqual(
            diagnostics["stop_evidence_signals"]["table_stop_like_rows"],
            2,
        )
        self.assertNotIn("filename", dumped.lower())
        self.assertNotIn("broker", dumped.lower())

    def test_quality_bucket_computation(self):
        self.assertEqual(compute_layout_quality_bucket(), QUALITY_EMPTY)
        self.assertEqual(
            compute_layout_quality_bucket(total_word_count=100, total_line_count=20),
            QUALITY_TEXT_ONLY,
        )
        self.assertEqual(
            compute_layout_quality_bucket(total_table_count=1, total_table_cell_count=4),
            QUALITY_TABLE_LIKE,
        )
        self.assertEqual(
            compute_layout_quality_bucket(
                total_word_count=50,
                total_line_count=10,
                total_table_count=1,
                total_table_cell_count=12,
            ),
            QUALITY_RICH_LAYOUT,
        )

    def test_stop_evidence_signals_are_counts_only(self):
        signals = build_stop_evidence_signals(
            pickup_label_hits="2",
            delivery_label_hits=1,
            stop_label_hits=3,
            date_label_hits=2,
            time_label_hits=2,
            table_stop_like_rows=4,
        )

        self.assertEqual(signals["pickup_label_hits"], 2)
        self.assertEqual(set(signals), {
            "pickup_label_hits",
            "delivery_label_hits",
            "stop_label_hits",
            "date_label_hits",
            "time_label_hits",
            "table_stop_like_rows",
        })

    def test_diagnostics_builder_counts_synthetic_table_artifact(self):
        artifact = build_layout_extraction_artifact(
            provider="pdfplumber",
            pages=[
                build_layout_page_artifact(
                    page_number=1,
                    words=[
                        build_layout_word(text="Pickup"),
                        build_layout_word(text="Delivery"),
                    ],
                    lines=[
                        build_layout_line(
                            "line_1",
                            text_redacted="Pickup Date <DATE>",
                            page_number=1,
                        ),
                        build_layout_line(
                            "line_2",
                            text_redacted="Delivery Time <TIME>",
                            page_number=1,
                        ),
                    ],
                    tables=[
                        build_layout_table(
                            "table_1",
                            page_number=1,
                            cells=[
                                build_layout_table_cell(0, 0, "Stop"),
                                build_layout_table_cell(0, 1, "Date"),
                                build_layout_table_cell(0, 2, "Time"),
                                build_layout_table_cell(1, 0, "Pickup"),
                                build_layout_table_cell(1, 1, "<DATE>"),
                                build_layout_table_cell(1, 2, "<TIME>"),
                                build_layout_table_cell(2, 0, "Delivery"),
                                build_layout_table_cell(2, 1, "<DATE>"),
                                build_layout_table_cell(2, 2, "<TIME>"),
                            ],
                        )
                    ],
                )
            ],
        )
        provider_result = {
            "provider_name": "pdfplumber",
            "status": "success",
            "artifact": artifact,
            "page_count": 1,
        }

        diagnostics = build_layout_provider_diagnostics(provider_result)

        self.assertEqual(diagnostics["total_word_count"], 2)
        self.assertEqual(diagnostics["total_line_count"], 2)
        self.assertEqual(diagnostics["total_table_count"], 1)
        self.assertEqual(diagnostics["total_table_cell_count"], 9)
        self.assertGreaterEqual(
            diagnostics["stop_evidence_signals"]["pickup_label_hits"],
            1,
        )
        self.assertGreaterEqual(
            diagnostics["stop_evidence_signals"]["table_stop_like_rows"],
            2,
        )
        self.assertFalse(diagnostics["raw_text_included"])

    def test_table_and_stop_signal_summaries_do_not_return_values(self):
        artifact = build_layout_extraction_artifact(
            pages=[
                build_layout_page_artifact(
                    page_number=1,
                    tables=[
                        build_layout_table(
                            "table_1",
                            cells=[
                                build_layout_table_cell(0, 0, "Pickup"),
                                build_layout_table_cell(0, 1, "Date"),
                            ],
                        )
                    ],
                )
            ]
        )

        table_summary = summarize_layout_tables(artifact)
        signals = summarize_stop_label_signals(artifact)
        dumped = json.dumps({"table": table_summary, "signals": signals})

        self.assertEqual(table_summary["table_count"], 1)
        self.assertNotIn("Pickup", dumped)
        self.assertNotIn("Date", dumped)

    def test_issue_bucket_identifies_stop_signals_without_groups(self):
        diagnostics = build_provider_document_diagnostics(
            document_alias="RATECON_001",
            provider_status="success",
            pages=[
                build_provider_page_diagnostics(
                    page_number=1,
                    word_count=20,
                    line_count=5,
                    table_count=1,
                    table_cell_count=8,
                )
            ],
            stop_evidence_signals=build_stop_evidence_signals(
                pickup_label_hits=1,
                delivery_label_hits=1,
                table_stop_like_rows=1,
            ),
        )

        self.assertEqual(
            classify_layout_provider_diagnostic_issue(diagnostics),
            ISSUE_PROVIDER_HAS_STOP_LABELS_BUT_NO_GROUPS,
        )

    def test_issue_bucket_identifies_no_tables(self):
        diagnostics = build_provider_document_diagnostics(
            document_alias="RATECON_001",
            provider_status="success",
            pages=[
                build_provider_page_diagnostics(
                    page_number=1,
                    word_count=20,
                    line_count=5,
                )
            ],
        )

        self.assertEqual(
            classify_layout_provider_diagnostic_issue(diagnostics),
            ISSUE_PROVIDER_NO_TABLES,
        )

    def test_diagnostics_report_is_local_only_and_safe(self):
        diagnostics = build_provider_document_diagnostics(
            document_alias="RATECON_001",
            provider_status="success",
            pages=[
                build_provider_page_diagnostics(
                    page_number=1,
                    word_count=20,
                    line_count=5,
                    table_count=1,
                    table_cell_count=8,
                )
            ],
            stop_evidence_signals=build_stop_evidence_signals(stop_label_hits=1),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_layout_provider_diagnostics_report(
                [diagnostics],
                output_dir=temp_dir,
                allow_custom_output_dir=True,
            )
            text = path.read_text(encoding="utf-8")

        self.assertEqual(path.name, LAYOUT_PROVIDER_DIAGNOSTICS_MD)
        self.assertIn("RATECON_001", text)
        self.assertIn("provider_status", text)
        self.assertNotIn("FAKE BROKER LLC", text)
        self.assertNotIn("123 Main", text)
        self.assertNotIn("raw text", text.lower().replace("no raw text", ""))

    def test_default_diagnostics_report_path_is_ignored_local_outputs(self):
        path = Path(".local_outputs/private_ratecon_measurement") / LAYOUT_PROVIDER_DIAGNOSTICS_MD

        self.assertTrue(str(path).startswith(".local_outputs"))

    def test_table_profile_comparison_is_safe_and_selects_best_profiles(self):
        def fake_extract(_path, document_id="", table_settings_profile="default"):
            table_cells = 12 if table_settings_profile == "lines" else 0
            table_count = 1 if table_settings_profile == "lines" else 0
            artifact = build_layout_extraction_artifact(
                provider="pdfplumber",
                pages=[
                    build_layout_page_artifact(
                        page_number=1,
                        words=[build_layout_word(text="Pickup")],
                        lines=[
                            build_layout_line(
                                "line_1",
                                text_redacted="Pickup Date <DATE>",
                                page_number=1,
                            )
                        ],
                        tables=[
                            build_layout_table(
                                "table_1",
                                cells=[
                                    build_layout_table_cell(0, 0, "Pickup"),
                                    build_layout_table_cell(0, 1, "<DATE>"),
                                ],
                            )
                        ]
                        if table_count
                        else [],
                    )
                ],
            )
            return {
                "provider_name": "pdfplumber",
                "status": "success",
                "artifact": artifact,
                "page_count": 1,
                "warning_codes": [],
                "table_settings_profile": table_settings_profile,
            }

        with patch(
            "app.document_ai.pdfplumber_layout_provider.extract_pdfplumber_layout",
            side_effect=fake_extract,
        ):
            comparison = compare_pdfplumber_table_profiles(
                "private.pdf",
                profiles=["default", "lines"],
                document_alias="RATECON_001",
            )

        dumped = json.dumps(comparison, sort_keys=True)

        self.assertEqual(comparison["document_alias"], "RATECON_001")
        self.assertEqual(comparison["best_profile_by_table_count"], "lines")
        self.assertEqual(comparison["best_profile_by_stop_signal_count"], "lines")
        self.assertFalse(comparison["raw_text_included"])
        self.assertTrue(comparison["private_values_redacted"])
        self.assertNotIn("private.pdf", dumped)
        self.assertNotIn("Pickup Date", dumped)


if __name__ == "__main__":
    unittest.main()
