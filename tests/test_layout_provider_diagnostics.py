import json
import unittest

from app.document_ai.layout_provider_diagnostics import (
    QUALITY_EMPTY,
    QUALITY_RICH_LAYOUT,
    QUALITY_TABLE_LIKE,
    QUALITY_TEXT_ONLY,
    build_provider_document_diagnostics,
    build_provider_page_diagnostics,
    build_stop_evidence_signals,
    compute_layout_quality_bucket,
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


if __name__ == "__main__":
    unittest.main()
