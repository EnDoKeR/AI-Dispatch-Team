import tempfile
import unittest
from pathlib import Path

from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_FIELD_DATE,
    NORMALIZED_STOP_FIELD_LOCATION,
    NORMALIZED_STOP_FIELD_STATUS_MISSING,
    NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
    NORMALIZED_STOP_FIELD_TIME,
    NORMALIZED_STOP_TYPE_PICKUP,
    build_normalized_stop,
    build_normalized_stop_field,
    build_normalized_stop_set,
)
from app.document_ai.stop_review_packet import (
    LOCAL_PRIVATE_REVIEW_WARNING,
    STOP_REVIEW_PACKET_CSV,
    STOP_REVIEW_PACKET_MD,
    build_stop_review_packet_summary,
    stop_review_rows,
    write_stop_review_packet,
)


def _stop_set_with_private_value():
    field = build_normalized_stop_field(
        NORMALIZED_STOP_FIELD_LOCATION,
        NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
        selected_candidate_id="candidate_001",
        evidence_refs=[{"page_number": 1, "evidence_type": "table_cell"}],
    )
    field["selected_value"] = "FAKE_LOCAL_PRIVATE_VALUE"
    stop = build_normalized_stop(
        "stop_001",
        1,
        NORMALIZED_STOP_TYPE_PICKUP,
        fields=[field],
    )
    return build_normalized_stop_set(document_alias="RATECON_001", stops=[stop])


class StopReviewPacketTests(unittest.TestCase):
    def test_shareable_packet_has_no_values(self):
        rows = stop_review_rows([_stop_set_with_private_value()])

        self.assertEqual(len(rows), 1)
        self.assertNotIn("selected_value_local_only", rows[0])
        self.assertNotIn("FAKE_LOCAL_PRIVATE_VALUE", str(rows))

    def test_local_only_mode_requires_explicit_flag(self):
        rows = stop_review_rows(
            [_stop_set_with_private_value()],
            include_private_values_local_only=True,
        )

        self.assertEqual(rows[0]["selected_value_local_only"], "FAKE_LOCAL_PRIVATE_VALUE")

    def test_local_only_header_warning_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = write_stop_review_packet(
                [_stop_set_with_private_value()],
                output_dir=tmp,
                include_private_values_local_only=True,
            )
            md_text = Path(result["md"]).read_text(encoding="utf-8")

        self.assertIn(LOCAL_PRIVATE_REVIEW_WARNING, md_text)

    def test_output_files_written_without_console_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = write_stop_review_packet([_stop_set_with_private_value()], output_dir=tmp)
            csv_text = (Path(tmp) / STOP_REVIEW_PACKET_CSV).read_text(encoding="utf-8")
            md_text = (Path(tmp) / STOP_REVIEW_PACKET_MD).read_text(encoding="utf-8")

        self.assertEqual(result["row_count"], 1)
        self.assertNotIn("FAKE_LOCAL_PRIVATE_VALUE", csv_text)
        self.assertNotIn("FAKE_LOCAL_PRIVATE_VALUE", md_text)
        self.assertFalse(result["raw_text_included"])

    def test_default_output_path_is_local_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = write_stop_review_packet(
                [_stop_set_with_private_value()],
                output_dir=Path(tmp) / ".local_outputs" / "private_ratecon_measurement",
            )

        self.assertIn(".local_outputs", str(result["csv"]))

    def test_summary_counts_date_time_and_pattern_statuses_without_values(self):
        date = build_normalized_stop_field(
            NORMALIZED_STOP_FIELD_DATE,
            NORMALIZED_STOP_FIELD_STATUS_MISSING,
            warning_codes=["normalized_stop_field_missing"],
        )
        time = build_normalized_stop_field(
            NORMALIZED_STOP_FIELD_TIME,
            NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
            selected_candidate_id="candidate_time",
            evidence_refs=[{"page_number": 1, "evidence_type": "section_context"}],
        )
        stop = build_normalized_stop(
            "stop_001",
            1,
            NORMALIZED_STOP_TYPE_PICKUP,
            fields=[
                build_normalized_stop_field(
                    NORMALIZED_STOP_FIELD_LOCATION,
                    NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
                    evidence_refs=[{"page_number": 1, "evidence_type": "section_context"}],
                ),
                date,
                time,
            ],
        )
        stop_set = build_normalized_stop_set(document_alias="RATECON_001", stops=[stop])
        stop_set["table_row_merge_count"] = 2

        summary = build_stop_review_packet_summary([stop_set])

        self.assertEqual(summary["date_candidate_generated_count"], 0)
        self.assertEqual(summary["time_candidate_generated_count"], 1)
        self.assertEqual(summary["table_row_merge_count"], 2)
        self.assertEqual(summary["unresolved_due_to_missing_date"], 1)
        self.assertFalse(summary["private_values_included"])
        self.assertNotIn("FAKE_LOCAL_PRIVATE_VALUE", str(summary))


if __name__ == "__main__":
    unittest.main()
