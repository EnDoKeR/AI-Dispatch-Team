import json
import unittest

from app.document_ai.layout_artifacts import (
    BLOCK_TYPE_TABLE,
    EVIDENCE_TABLE_CELL,
    LAYOUT_ARTIFACT_VERSION,
    build_bounding_box,
    build_layout_block,
    build_layout_evidence_ref,
    build_layout_extraction_artifact,
    build_layout_line,
    build_layout_page_artifact,
    build_layout_table,
    build_layout_table_cell,
    build_layout_word,
)


class LayoutArtifactContractTests(unittest.TestCase):
    def test_create_bounding_box(self):
        bbox = build_bounding_box(10, 20, 110, 40, unit="points", page_number=1)

        self.assertEqual(bbox["x0"], 10.0)
        self.assertEqual(bbox["y0"], 20.0)
        self.assertEqual(bbox["x1"], 110.0)
        self.assertEqual(bbox["y1"], 40.0)
        self.assertEqual(bbox["unit"], "points")
        self.assertEqual(bbox["page_number"], 1)

    def test_create_page_artifact(self):
        bbox = build_bounding_box(10, 10, 200, 30, page_number=1)
        line = build_layout_line(
            line_id="L1",
            text_redacted="Total Carrier Pay: <MONEY>",
            bbox=bbox,
            page_number=1,
            reading_order_index=1,
            section_role="RATE_SUMMARY",
        )
        block = build_layout_block(
            block_id="B1",
            text_redacted="Total Carrier Pay: <MONEY>",
            bbox=bbox,
            line_ids=["L1"],
            page_number=1,
            section_role="RATE_SUMMARY",
        )
        word = build_layout_word(text="Total", bbox=bbox, line_id="L1", block_id="B1")
        page = build_layout_page_artifact(
            page_number=1,
            width=612,
            height=792,
            words=[word],
            lines=[line],
            blocks=[block],
            page_roles=["MAIN_RATECONF"],
            section_roles=["RATE_SUMMARY"],
        )

        self.assertEqual(page["page_number"], 1)
        self.assertEqual(page["lines"][0]["line_id"], "L1")
        self.assertEqual(page["blocks"][0]["section_role"], "RATE_SUMMARY")
        self.assertIn("MAIN_RATECONF", page["page_roles"])

    def test_create_table_artifact(self):
        bbox = build_bounding_box(20, 80, 300, 140, page_number=1)
        cells = [
            build_layout_table_cell(0, 0, "Label", bbox=bbox),
            build_layout_table_cell(0, 1, "Value", bbox=bbox),
            build_layout_table_cell(1, 0, "Rate", bbox=bbox),
            build_layout_table_cell(1, 1, "<MONEY>", bbox=bbox),
        ]
        table = build_layout_table(
            table_id="T1",
            page_number=1,
            bbox=bbox,
            cells=cells,
            header_rows=[0],
            confidence="HIGH",
        )
        block = build_layout_block(
            block_id="B_TABLE",
            bbox=bbox,
            line_ids=[],
            page_number=1,
            block_type=BLOCK_TYPE_TABLE,
        )

        self.assertEqual(table["table_id"], "T1")
        self.assertEqual(table["cells"][3]["text_redacted"], "<MONEY>")
        self.assertEqual(block["block_type"], BLOCK_TYPE_TABLE)

    def test_serialization_round_trip(self):
        bbox = build_bounding_box(1, 2, 3, 4, page_number=1)
        page = build_layout_page_artifact(
            page_number=1,
            lines=[
                build_layout_line(
                    line_id="L1",
                    text_redacted="Load Number: <REF>",
                    bbox=bbox,
                    page_number=1,
                    reading_order_index=1,
                )
            ],
        )
        artifact = build_layout_extraction_artifact(
            artifact_id="LAYOUT-001",
            document_id="DOC-001",
            pages=[page],
        )

        payload = json.loads(json.dumps(artifact))

        self.assertEqual(payload["artifact_id"], "LAYOUT-001")
        self.assertEqual(payload["layout_version"], LAYOUT_ARTIFACT_VERSION)
        self.assertEqual(payload["page_count"], 1)

    def test_safe_defaults(self):
        artifact = build_layout_extraction_artifact()

        self.assertFalse(artifact["raw_text_included"])
        self.assertTrue(artifact["private_values_redacted"])
        self.assertNotIn("raw_text", artifact)

    def test_layout_evidence_ref_serializes(self):
        bbox = build_bounding_box(20, 80, 300, 140, page_number=2)
        evidence = build_layout_evidence_ref(
            page_number=2,
            bbox=bbox,
            table_id="T_RATE",
            cell_ref="r1c1",
            label="Total Carrier Pay",
            evidence_type=EVIDENCE_TABLE_CELL,
        )

        payload = json.loads(json.dumps(evidence))

        self.assertEqual(payload["page_number"], 2)
        self.assertEqual(payload["table_id"], "T_RATE")
        self.assertEqual(payload["cell_ref"], "r1c1")
        self.assertEqual(payload["evidence_type"], EVIDENCE_TABLE_CELL)


if __name__ == "__main__":
    unittest.main()
