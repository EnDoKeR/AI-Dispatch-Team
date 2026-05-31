import json
import unittest

from app.document_ai.stop_group_provenance import (
    STOP_GROUP_SOURCE_TYPE_SECTION_BLOCK,
    STOP_GROUP_SOURCE_TYPE_TABLE_CELL,
    STOP_GROUP_SOURCE_TYPE_TABLE_ROW,
    TRIGGER_LABEL_PICKUP,
    build_stop_group_provenance,
    build_stop_group_provenance_summary,
)


class StopGroupProvenanceTests(unittest.TestCase):
    def test_create_table_row_provenance(self):
        provenance = build_stop_group_provenance(
            source_type=STOP_GROUP_SOURCE_TYPE_TABLE_ROW,
            source_generator="layout_table_stop_groups",
            page_number=1,
            table_id="T_FAKE",
            row_index=2,
            trigger_label_category=TRIGGER_LABEL_PICKUP,
            candidate_field_names=["location", "date", "time"],
        )

        self.assertEqual(provenance["source_type"], STOP_GROUP_SOURCE_TYPE_TABLE_ROW)
        self.assertEqual(provenance["grouping_key"], "1|T_FAKE|2")
        self.assertTrue(provenance["has_location_candidate"])
        self.assertTrue(provenance["has_date_candidate"])
        self.assertTrue(provenance["has_time_candidate"])
        self.assertFalse(provenance["raw_text_included"])
        self.assertTrue(provenance["private_values_redacted"])

    def test_provenance_serializes_without_private_values(self):
        provenance = build_stop_group_provenance(
            source_type=STOP_GROUP_SOURCE_TYPE_SECTION_BLOCK,
            source_generator="layout_section_stop_groups",
            page_number=2,
            block_id="B_FAKE",
            section_role="PICKUP_SECTION",
            candidate_field_names=["location"],
        )

        payload = json.dumps(provenance, sort_keys=True)

        self.assertIn("PICKUP_SECTION", payload)
        self.assertNotIn("raw_text", provenance)
        self.assertNotIn("FAKE_PRIVATE_VALUE", payload)

    def test_summary_counts_by_source_type_table_and_row(self):
        provenances = [
            build_stop_group_provenance(
                source_type=STOP_GROUP_SOURCE_TYPE_TABLE_CELL,
                page_number=1,
                table_id="T_FAKE",
                row_index=1,
                col_index=1,
                candidate_field_names=["location"],
            ),
            build_stop_group_provenance(
                source_type=STOP_GROUP_SOURCE_TYPE_TABLE_CELL,
                page_number=1,
                table_id="T_FAKE",
                row_index=1,
                col_index=2,
                candidate_field_names=["date"],
            ),
            build_stop_group_provenance(
                source_type=STOP_GROUP_SOURCE_TYPE_TABLE_ROW,
                page_number=1,
                table_id="T_FAKE",
                row_index=2,
                candidate_field_names=["location", "time"],
            ),
        ]

        summary = build_stop_group_provenance_summary(
            document_alias="RATECON_FAKE",
            provenances=provenances,
        )

        self.assertEqual(summary["document_alias"], "RATECON_FAKE")
        self.assertEqual(summary["raw_group_count"], 3)
        self.assertEqual(summary["groups_by_source_type"][STOP_GROUP_SOURCE_TYPE_TABLE_CELL], 2)
        self.assertEqual(summary["groups_by_table"]["T_FAKE"], 3)
        self.assertEqual(summary["groups_by_row_key"]["1|T_FAKE|1"], 2)
        self.assertEqual(summary["one_group_per_cell_suspected_count"], 2)
        self.assertEqual(summary["table_row_merge_candidate_count"], 1)

    def test_summary_counts_noise_sections(self):
        summary = build_stop_group_provenance_summary(
            provenances=[
                build_stop_group_provenance(
                    source_type=STOP_GROUP_SOURCE_TYPE_SECTION_BLOCK,
                    page_number=1,
                    section_role="LEGAL_TERMS",
                    candidate_field_names=["reference"],
                )
            ]
        )

        self.assertEqual(summary["noise_candidate_count"], 1)
        self.assertFalse(summary["raw_text_included"])
        self.assertTrue(summary["private_values_redacted"])


if __name__ == "__main__":
    unittest.main()
