import json
from contextlib import redirect_stdout
from io import StringIO
import unittest

from app.document_ai.field_candidate_generators import generate_field_candidates
from app.document_ai.ocr_provider_contract import (
    OCR_STATUS_SUCCESS,
    build_ocr_page_result,
    build_ocr_provider_result,
)
from app.document_ai.ocr_stop_block_assembler import (
    STOP_CANDIDATE_PROFILE_BASELINE,
    STOP_CANDIDATE_PROFILE_OCR_GEOMETRY_COLUMN_V1,
)
from app.document_ai.ocr_stop_table_reconstructor import (
    GENERATOR_OCR_STOP_TABLE_RECONSTRUCTOR,
    generate_ocr_stop_column_candidates,
    reconstruct_ocr_stop_tables,
)
from app.document_ai.ratecon_gold_labels import evaluate_ratecon_against_gold
from app.document_ai.ratecon_stop_component_policy import (
    STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
    apply_stop_column_strict_profile_to_candidates,
)
from scripts.run_private_ratecon_measurement import main as measurement_main


def _bbox(left, top, width=80, height=16):
    return {
        "left": left,
        "top": top,
        "right": left + width,
        "bottom": top + height,
        "x0": left,
        "y0": top,
        "x1": left + width,
        "y1": top + height,
    }


def _line(text, left, top, line_num, width=180):
    return {
        "text": text,
        "bbox": _bbox(left, top, width=width),
        "block_num": 1,
        "par_num": 1,
        "line_num": line_num,
        "line_index": line_num - 1,
    }


def _words(text, left, top, line_num):
    words = []
    x = left
    for word_num, token in enumerate(text.split(), start=1):
        width = max(18, len(token) * 8)
        words.append(
            {
                "text": token,
                "bbox": _bbox(x, top, width=width),
                "confidence": 91.0,
                "block_num": 1,
                "par_num": 1,
                "line_num": line_num,
                "word_num": word_num,
            }
        )
        x += width + 8
    return words


def _artifact(lines):
    word_boxes = []
    line_boxes = []
    for line in lines:
        line_boxes.append(_line(*line))
        word_boxes.extend(_words(line[0], line[1], line[2], line[3]))
    text = "\n".join(line[0] for line in lines)
    return {
        "document_id": "DOC-OCR-COLUMN",
        "source": "hybrid",
        "pages": [{"page_number": 1, "text": text, "lines": []}],
        "full_text": text,
        "ocr_provider_result": build_ocr_provider_result(
            provider_name="tesseract",
            provider_requested="auto",
            available=True,
            status=OCR_STATUS_SUCCESS,
            pages=[
                build_ocr_page_result(
                    page_number=1,
                    text=text,
                    status=OCR_STATUS_SUCCESS,
                    word_boxes=word_boxes,
                    line_boxes=line_boxes,
                )
            ],
        ),
    }


def _gold_label():
    return {
        "schema_version": "ratecon_gold_label_v1",
        "document_id": "DOC-OCR-COLUMN",
        "file_hash": "hash-column",
        "file_name": "doc.pdf",
        "label_status": "labeled",
        "gold": {
            "document_type": "rate_confirmation",
            "pickup_stops": [
                {
                    "stop_index": 1,
                    "city": "Dallas",
                    "state": "TX",
                    "date": "2026-06-05",
                    "appointment_window": "07:00-15:00",
                }
            ],
            "delivery_stops": [
                {
                    "stop_index": 1,
                    "city": "Houston",
                    "state": "TX",
                    "date": "2026-06-06",
                    "time": "13:00",
                }
            ],
        },
    }


class RateConOcrStopColumnReconstructionTests(unittest.TestCase):
    def test_tsv_diagnostics_detect_columns_and_exclude_payment(self):
        artifact = _artifact(
            [
                ("PU 1", 40, 10, 1, 55),
                ("Dallas TX 75001", 120, 10, 2, 170),
                ("Date 06/05/2026 0700 to 1500", 430, 10, 3, 260),
                ("SO 2", 40, 70, 4, 55),
                ("Houston TX 77001", 120, 70, 5, 170),
                ("Date 06/06/2026 1300", 430, 70, 6, 220),
                ("Total Carrier Pay $1200.00", 40, 130, 7, 260),
            ]
        )

        tables, diagnostics = reconstruct_ocr_stop_tables(artifact)

        self.assertEqual(diagnostics["detected_stop_rows"], 2)
        self.assertTrue(diagnostics["page_summaries"][0]["detected_role_column"])
        self.assertTrue(diagnostics["page_summaries"][0]["detected_location_column"])
        self.assertTrue(diagnostics["page_summaries"][0]["detected_date_time_column"])
        self.assertTrue(diagnostics["page_summaries"][0]["payment_band_detected"])
        self.assertEqual([row["role"] for row in tables[0]["rows"]], ["pickup", "delivery"])
        self.assertNotIn("Total Carrier Pay", json.dumps(diagnostics))

    def test_column_candidates_emit_structured_pickup_and_delivery(self):
        artifact = _artifact(
            [
                ("PU 1", 40, 10, 1, 55),
                ("North Warehouse Dallas TX 75001", 120, 10, 2, 260),
                ("Date 06/05/2026 0700 to 1500", 430, 10, 3, 260),
                ("SO 2", 40, 70, 4, 55),
                ("South DC Houston TX 77001", 120, 70, 5, 250),
                ("Date 06/06/2026 1300", 430, 70, 6, 220),
            ]
        )

        candidates, diagnostics = generate_ocr_stop_column_candidates(artifact)

        structured = [
            candidate for candidate in candidates
            if candidate["field"] in {"pickup_stops", "delivery_stops"}
        ]
        self.assertEqual(
            {candidate["field"] for candidate in structured},
            {"pickup_stops", "delivery_stops"},
        )
        self.assertGreater(diagnostics["ocr_geometry_column_structured_stop_candidates"], 0)
        self.assertGreater(diagnostics["ocr_geometry_column_dispatch_usable_candidates"], 0)
        delivery = next(candidate for candidate in structured if candidate["field"] == "delivery_stops")
        self.assertEqual(delivery["parser_name"], GENERATOR_OCR_STOP_TABLE_RECONSTRUCTOR)
        self.assertEqual(delivery["metadata"]["pairing_method"], "ocr_geometry_column_row")
        self.assertEqual(delivery["metadata"]["component_alignment"]["date"], "date_time_column")

    def test_column_strict_profile_abstains_payment_overlap(self):
        artifact = _artifact(
            [
                ("PU 1", 40, 10, 1, 55),
                ("Dallas TX 75001", 120, 10, 2, 170),
                ("Date 06/05/2026 1000", 430, 10, 3, 220),
                ("Payment Terms", 40, 35, 4, 160),
            ]
        )
        candidates, _diagnostics = generate_ocr_stop_column_candidates(artifact)
        adjusted = apply_stop_column_strict_profile_to_candidates(candidates)
        pickup = next(candidate for candidate in adjusted if candidate["field"] == "pickup_stops")

        self.assertTrue(pickup["metadata"]["stop_abstained"])
        self.assertEqual(pickup["metadata"]["stop_selection_policy"], "abstain")

    def test_column_candidate_profile_is_opt_in_and_cli_parses(self):
        artifact = _artifact([("PU 1", 40, 10, 1, 55), ("Dallas TX 75001", 120, 10, 2, 170)])

        baseline = generate_field_candidates(
            artifact,
            stop_candidate_profile=STOP_CANDIDATE_PROFILE_BASELINE,
        )
        enabled = generate_field_candidates(
            artifact,
            stop_candidate_profile=STOP_CANDIDATE_PROFILE_OCR_GEOMETRY_COLUMN_V1,
        )

        baseline_generators = {summary["generator_name"] for summary in baseline["generator_summaries"]}
        enabled_generators = {summary["generator_name"] for summary in enabled["generator_summaries"]}
        self.assertNotIn(GENERATOR_OCR_STOP_TABLE_RECONSTRUCTOR, baseline_generators)
        self.assertIn(GENERATOR_OCR_STOP_TABLE_RECONSTRUCTOR, enabled_generators)

        buffer = StringIO()
        with self.assertRaises(SystemExit) as raised, redirect_stdout(buffer):
            measurement_main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn(STOP_CANDIDATE_PROFILE_OCR_GEOMETRY_COLUMN_V1, buffer.getvalue())
        self.assertIn(STOP_RANKING_PROFILE_COLUMN_STRICT_V1, buffer.getvalue())

    def test_evaluator_reports_usability_and_column_counts_safely(self):
        artifact = _artifact(
            [
                ("PU 1", 40, 10, 1, 55),
                ("Dallas TX 75001", 120, 10, 2, 170),
                ("Date 06/05/2026 FCFS 0700 to 1500", 430, 10, 3, 280),
            ]
        )
        candidates, _diagnostics = generate_ocr_stop_column_candidates(artifact)
        pickup = next(candidate for candidate in candidates if candidate["field"] == "pickup_stops")
        inventory = [
            {
                "field": candidate["field"],
                "source": candidate["source"],
                "parser_name": candidate["parser_name"],
                "metadata_summary": candidate["metadata"],
            }
            for candidate in candidates
        ]
        audit = {
            "document_id": "DOC-OCR-COLUMN",
            "file_hash": "hash-column",
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
        usability = evaluation["stop_usability_summary"]["pickup"]
        gap = evaluation["ocr_stop_evidence_gap_summary"]

        self.assertGreater(usability["exact_complete"] + usability["dispatch_usable"], 0)
        self.assertGreater(gap["ocr_geometry_column_structured_stop_candidates"], 0)
        self.assertGreater(gap["ocr_geometry_column_dispatch_usable_candidates"], 0)
        self.assertFalse(evaluation["stop_gold_consistency_audit"]["raw_text_printed"])
        self.assertNotIn("Dallas", json.dumps(gap))


if __name__ == "__main__":
    unittest.main()
