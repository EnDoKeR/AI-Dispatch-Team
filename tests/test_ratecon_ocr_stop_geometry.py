import json
from contextlib import redirect_stdout
from io import StringIO
import unittest

from app.document_ai.field_candidate_generators import generate_field_candidates
from app.document_ai.ocr_provider_contract import (
    OCR_STATUS_SUCCESS,
    build_ocr_page_result,
    build_ocr_provider_result,
    safe_ocr_provider_summary,
)
from app.document_ai.ocr_stop_block_assembler import (
    STOP_CANDIDATE_PROFILE_BASELINE,
    STOP_CANDIDATE_PROFILE_OCR_GEOMETRY_BLOCK_V1,
)
from app.document_ai.ocr_stop_geometry_assembler import (
    GENERATOR_OCR_STOP_GEOMETRY_ASSEMBLER,
    detect_geometry_stop_blocks_from_artifact,
    generate_ocr_stop_geometry_candidates,
)
from app.document_ai.ratecon_gold_labels import evaluate_ratecon_against_gold
from app.document_ai.ratecon_stop_component_policy import (
    STOP_RANKING_PROFILE_GEOMETRY_STRICT_V1,
    apply_stop_geometry_strict_profile_to_candidates,
)
from scripts.run_private_ratecon_measurement import main as measurement_main


def _line(text, top, left=40, width=240, height=16, index=0):
    return {
        "text": text,
        "source": "ocr",
        "page": 1,
        "line_index": index,
        "bbox": {
            "x0": left,
            "y0": top,
            "x1": left + width,
            "y1": top + height,
            "left": left,
            "top": top,
            "right": left + width,
            "bottom": top + height,
        },
    }


def _artifact(lines):
    return {
        "document_id": "DOC-OCR-GEO",
        "source": "hybrid",
        "pages": [
            {
                "page_number": 1,
                "text": "\n".join(line["text"] for line in lines),
                "lines": lines,
            }
        ],
        "full_text": "\n".join(line["text"] for line in lines),
    }


def _artifact_with_provider_line_boxes(lines):
    return {
        "document_id": "DOC-OCR-GEO",
        "source": "hybrid",
        "pages": [
            {
                "page_number": 1,
                "text": "\n".join(line["text"] for line in lines),
                "lines": [],
            }
        ],
        "full_text": "\n".join(line["text"] for line in lines),
        "ocr_provider_result": build_ocr_provider_result(
            provider_name="tesseract",
            provider_requested="auto",
            available=True,
            status=OCR_STATUS_SUCCESS,
            pages=[
                build_ocr_page_result(
                    page_number=1,
                    text="\n".join(line["text"] for line in lines),
                    status=OCR_STATUS_SUCCESS,
                    line_boxes=lines,
                )
            ],
        ),
    }


def _gold_label():
    return {
        "schema_version": "ratecon_gold_label_v1",
        "document_id": "DOC-OCR-GEO",
        "file_hash": "hash-ocr-geo",
        "file_name": "doc.pdf",
        "label_status": "labeled",
        "gold": {
            "document_type": "rate_confirmation",
            "pickup_stops": [
                {
                    "stop_index": 1,
                    "facility": "North Warehouse",
                    "address": "123 Main St",
                    "city": "Dallas",
                    "state": "TX",
                    "zip": "75001",
                    "date": "06/05/2026",
                    "time": "10:00",
                }
            ],
        },
    }


class RateConOcrStopGeometryTests(unittest.TestCase):
    def test_ocr_contract_reports_geometry_counts_without_raw_text(self):
        result = build_ocr_provider_result(
            provider_name="tesseract",
            provider_requested="auto",
            available=True,
            status=OCR_STATUS_SUCCESS,
            pages=[
                build_ocr_page_result(
                    page_number=1,
                    text="PRIVATE PU 1",
                    status=OCR_STATUS_SUCCESS,
                    word_boxes=[
                        {"text": "PRIVATE", "bbox": {"x0": 0, "y0": 0, "x1": 40, "y1": 10}}
                    ],
                    line_boxes=[
                        {"text": "PRIVATE PU 1", "bbox": {"x0": 0, "y0": 0, "x1": 80, "y1": 10}}
                    ],
                )
            ],
        )

        summary = safe_ocr_provider_summary(result)

        self.assertTrue(summary["ocr_geometry_available"])
        self.assertEqual(summary["ocr_word_box_count"], 1)
        self.assertEqual(summary["ocr_line_box_count"], 1)
        self.assertFalse(summary["raw_text_included"])
        self.assertNotIn("PRIVATE", json.dumps(summary))

    def test_geometry_blocks_segment_pu_so_and_exclude_payment(self):
        lines = [
            _line("PU 1", 10, index=0),
            _line("Name: North Warehouse", 30, left=90, index=1),
            _line("Date: 06/05/2026 10:00", 30, left=420, index=2),
            _line("123 Main St", 50, left=90, index=3),
            _line("Dallas TX 75001", 70, left=90, index=4),
            _line("SO 2", 110, index=5),
            _line("Name: South DC", 130, left=90, index=6),
            _line("Date: 06/06/2026 14:00", 130, left=420, index=7),
            _line("Total Carrier Pay $1200.00", 170, left=40, index=8),
        ]

        blocks, diagnostics = detect_geometry_stop_blocks_from_artifact(_artifact(lines))

        self.assertTrue(diagnostics["geometry_available"])
        self.assertEqual([block["role"] for block in blocks], ["pickup", "delivery"])
        self.assertEqual(blocks[0]["geometry"]["component_alignment"]["date"], "same_block_right_column")
        self.assertNotIn("Total Carrier Pay $1200.00", blocks[1]["lines"])

    def test_geometry_candidates_emit_structured_delivery_date(self):
        lines = [
            _line("SO 2", 10, index=0),
            _line("Consignee Delivery", 30, left=90, index=1),
            _line("Expected Date: 06/06/2026", 30, left=420, index=2),
            _line("Shipping/Receiving Hours: 0800-1600", 50, left=420, index=3),
            _line("456 Oak Rd", 70, left=90, index=4),
            _line("Houston TX 77001", 90, left=90, index=5),
            _line("Special Instructions", 130, index=6),
        ]

        candidates, diagnostics = generate_ocr_stop_geometry_candidates(_artifact(lines))

        fields = {candidate["field"] for candidate in candidates}
        delivery = next(candidate for candidate in candidates if candidate["field"] == "delivery_stops")
        self.assertIn("delivery_date", fields)
        self.assertIn("delivery_time", fields)
        self.assertEqual(delivery["parser_name"], GENERATOR_OCR_STOP_GEOMETRY_ASSEMBLER)
        self.assertEqual(delivery["metadata"]["pairing_method"], "ocr_geometry_block")
        self.assertTrue(delivery["metadata"]["geometry_available"])
        self.assertGreater(diagnostics["geometry_structured_stop_candidates"], 0)

    def test_geometry_candidates_read_provider_result_line_boxes(self):
        lines = [
            _line("PU 1", 10, index=0),
            _line("Name: North Warehouse", 30, left=90, index=1),
            _line("Date: 06/05/2026", 30, left=420, index=2),
            _line("Dallas TX 75001", 50, left=90, index=3),
            _line("SO 2", 100, index=4),
        ]

        candidates, diagnostics = generate_ocr_stop_geometry_candidates(
            _artifact_with_provider_line_boxes(lines)
        )

        self.assertTrue(diagnostics["geometry_available"])
        self.assertGreater(diagnostics["ocr_line_box_count"], 0)
        self.assertTrue(
            any(candidate["field"] == "pickup_stops" for candidate in candidates)
        )

    def test_geometry_strict_allows_strong_and_demotes_unclear_boundary(self):
        strong_lines = [
            _line("PU 1", 10, index=0),
            _line("Name: North Warehouse", 30, left=90, index=1),
            _line("Date: 06/05/2026", 30, left=420, index=2),
            _line("Dallas TX 75001", 50, left=90, index=3),
            _line("SO 2", 100, index=4),
        ]
        strong_candidates, _diagnostics = generate_ocr_stop_geometry_candidates(_artifact(strong_lines))
        adjusted = apply_stop_geometry_strict_profile_to_candidates(strong_candidates)
        pickup = next(candidate for candidate in adjusted if candidate["field"] == "pickup_stops")

        self.assertFalse(pickup["metadata"]["stop_abstained"])
        self.assertIn(pickup["metadata"]["stop_selection_policy"], {"allowed", "partial_review"})

        weak_lines = [
            _line("PU 1", 10, index=0),
            _line("North Warehouse", 30, left=90, index=1),
        ]
        weak_candidates, _diagnostics = generate_ocr_stop_geometry_candidates(_artifact(weak_lines))
        weak_adjusted = apply_stop_geometry_strict_profile_to_candidates(weak_candidates)
        weak_pickup = next(candidate for candidate in weak_adjusted if candidate["field"] == "pickup_stops")

        self.assertTrue(weak_pickup["metadata"]["stop_abstained"])
        self.assertEqual(weak_pickup["metadata"]["stop_selection_policy"], "abstain")

    def test_geometry_stop_candidate_profile_is_opt_in(self):
        lines = [
            _line("PU 1", 10, index=0),
            _line("Date: 06/05/2026", 30, left=420, index=1),
            _line("Dallas TX 75001", 50, left=90, index=2),
            _line("SO 2", 90, index=3),
        ]
        artifact = _artifact(lines)

        baseline = generate_field_candidates(
            artifact,
            stop_candidate_profile=STOP_CANDIDATE_PROFILE_BASELINE,
        )
        enabled = generate_field_candidates(
            artifact,
            stop_candidate_profile=STOP_CANDIDATE_PROFILE_OCR_GEOMETRY_BLOCK_V1,
        )

        baseline_generators = {
            summary["generator_name"] for summary in baseline["generator_summaries"]
        }
        enabled_generators = {
            summary["generator_name"] for summary in enabled["generator_summaries"]
        }
        self.assertNotIn(GENERATOR_OCR_STOP_GEOMETRY_ASSEMBLER, baseline_generators)
        self.assertIn(GENERATOR_OCR_STOP_GEOMETRY_ASSEMBLER, enabled_generators)

    def test_evaluator_reports_geometry_counts_without_raw_values(self):
        lines = [
            _line("PU 1", 10, index=0),
            _line("Name: North Warehouse", 30, left=90, index=1),
            _line("Date: 06/05/2026 10:00", 30, left=420, index=2),
            _line("123 Main St", 50, left=90, index=3),
            _line("Dallas TX 75001", 70, left=90, index=4),
            _line("SO 2", 110, index=5),
        ]
        candidates, _diagnostics = generate_ocr_stop_geometry_candidates(_artifact(lines))
        pickup = next(candidate for candidate in candidates if candidate["field"] == "pickup_stops")
        inventory = [
            {
                "field": candidate["field"],
                "value": candidate["value"],
                "source": candidate["source"],
                "parser_name": candidate["parser_name"],
                "metadata_summary": candidate["metadata"],
            }
            for candidate in candidates
        ]
        audit = {
            "document_id": "DOC-OCR-GEO",
            "file_hash": "hash-ocr-geo",
            "file_name": "doc.pdf",
            "artifact_summary": {
                "ocr_provider_summary": {
                    "status": "success",
                    "ocr_text_page_count": 1,
                    "ocr_geometry_available": True,
                }
            },
            "shadow": {"resolved_fields": {}},
            "legacy": {},
            "private_eval_values": {
                "shadow_selected": {
                    "pickup_stops": {
                        "value": pickup["value"],
                        "confidence": pickup["confidence"],
                        "source": "ocr",
                        "parser_name": pickup["parser_name"],
                        "metadata_summary": pickup["metadata"],
                    }
                },
                "stop_component_candidate_inventory": inventory,
            },
        }

        evaluation = evaluate_ratecon_against_gold([_gold_label()], [audit])
        summary = evaluation["ocr_stop_evidence_gap_summary"]

        self.assertGreater(summary["ocr_geometry_structured_stop_candidates"], 0)
        self.assertGreater(summary["geometry_available_counts"]["true"], 0)
        self.assertFalse(summary["raw_text_printed"])
        self.assertNotIn("North Warehouse", json.dumps(summary))

    def test_cli_parses_geometry_profiles(self):
        buffer = StringIO()
        with self.assertRaises(SystemExit) as raised, redirect_stdout(buffer):
            measurement_main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn(STOP_CANDIDATE_PROFILE_OCR_GEOMETRY_BLOCK_V1, buffer.getvalue())
        self.assertIn(STOP_RANKING_PROFILE_GEOMETRY_STRICT_V1, buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
