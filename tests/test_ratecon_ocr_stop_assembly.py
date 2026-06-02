import json
from contextlib import redirect_stdout
from io import StringIO
import unittest

from app.document_ai.field_candidate_generators import generate_field_candidates
from app.document_ai.ocr_stop_block_assembler import (
    GENERATOR_OCR_STOP_BLOCK_ASSEMBLER,
    SOURCE_OCR,
    STOP_CANDIDATE_PROFILE_BASELINE,
    STOP_CANDIDATE_PROFILE_OCR_BLOCK_ASSEMBLY_V1,
    candidates_from_stop_evidence_blocks,
    detect_stop_evidence_blocks_from_artifact,
)
from app.document_ai.ratecon_gold_labels import evaluate_ratecon_against_gold
from scripts.run_private_ratecon_measurement import main as measurement_main


def _artifact(lines, source=SOURCE_OCR):
    return {
        "document_id": "DOC-OCR-STOPS",
        "source": "hybrid",
        "pages": [
            {
                "page_number": 1,
                "text": "\n".join(lines),
                "lines": [
                    {
                        "text": line,
                        "source": source,
                        "page": 1,
                        "line_index": index,
                    }
                    for index, line in enumerate(lines)
                ],
            }
        ],
        "full_text": "\n".join(lines),
    }


def _gold_label():
    return {
        "schema_version": "ratecon_gold_label_v1",
        "document_id": "DOC-OCR-STOPS",
        "file_hash": "hash-ocr-stops",
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
            "delivery_stops": [
                {
                    "stop_index": 1,
                    "facility": "South DC",
                    "address": "456 Oak Rd",
                    "city": "Houston",
                    "state": "TX",
                    "zip": "77001",
                    "date": "06/06/2026",
                    "time": "14:00",
                }
            ],
        },
    }


class RateConOcrStopAssemblyTests(unittest.TestCase):
    def test_detects_pickup_and_delivery_blocks_from_ocr_lines(self):
        artifact = _artifact(
            [
                "PU 1",
                "Name: North Warehouse",
                "Date: 06/05/2026",
                "123 Main St",
                "Dallas TX 75001",
                "SO 2",
                "Name: South DC",
                "Date: 06/06/2026",
                "456 Oak Rd",
                "Houston TX 77001",
                "Rate $2500.00",
            ]
        )

        blocks = detect_stop_evidence_blocks_from_artifact(artifact)

        self.assertEqual([block["role"] for block in blocks], ["pickup", "delivery"])
        self.assertTrue(blocks[0]["has_date_like_text"])
        self.assertTrue(blocks[0]["has_location_like_text"])
        self.assertTrue(blocks[1]["has_address_like_text"])
        self.assertNotIn("North Warehouse", json.dumps({k: v for k, v in blocks[0].items() if k != "lines"}))

    def test_drop_and_consignee_labels_create_delivery_blocks(self):
        artifact = _artifact(
            [
                "Drop 2 Location",
                "Date: 06/06/2026",
                "456 Oak Rd",
                "Houston TX 77001",
                "Consignee Delivery (Stop 2)",
                "Expected Date: 06/07/2026",
            ]
        )

        blocks = detect_stop_evidence_blocks_from_artifact(artifact)

        self.assertEqual(len(blocks), 2)
        self.assertTrue(all(block["role"] == "delivery" for block in blocks))

    def test_payment_or_instruction_section_stops_block_growth(self):
        artifact = _artifact(
            [
                "Shipper Pickup (Stop 1)",
                "Name: North Warehouse",
                "Date: 06/05/2026",
                "Special Instructions",
                "Do not treat this as a stop line",
                "Total Carrier Pay $1000.00",
            ]
        )

        blocks = detect_stop_evidence_blocks_from_artifact(artifact)

        self.assertEqual(len(blocks), 1)
        self.assertLessEqual(blocks[0]["line_count"], 3)

    def test_assembles_structured_and_component_candidates(self):
        artifact = _artifact(
            [
                "PU 1 Name: North Warehouse",
                "Date: 06/05/2026",
                "Time: 10:00",
                "123 Main St",
                "Dallas TX 75001",
            ]
        )
        blocks = detect_stop_evidence_blocks_from_artifact(artifact)
        candidates, diagnostics = candidates_from_stop_evidence_blocks(blocks)

        fields = {candidate["field"] for candidate in candidates}
        pickup = next(candidate for candidate in candidates if candidate["field"] == "pickup_stops")

        self.assertIn("pickup_stops", fields)
        self.assertIn("pickup_location", fields)
        self.assertIn("pickup_date", fields)
        self.assertIn("pickup_time", fields)
        self.assertEqual(pickup["source"], "ocr")
        self.assertEqual(pickup["parser_name"], GENERATOR_OCR_STOP_BLOCK_ASSEMBLER)
        self.assertTrue(pickup["metadata"]["structured_stop_candidate"])
        self.assertEqual(diagnostics["structured_stop_candidates"], 1)

    def test_partial_block_does_not_invent_missing_components(self):
        artifact = _artifact(["PU 1", "Name: North Warehouse"])
        blocks = detect_stop_evidence_blocks_from_artifact(artifact)
        candidates, _diagnostics = candidates_from_stop_evidence_blocks(blocks)
        pickup = next(candidate for candidate in candidates if candidate["field"] == "pickup_stops")
        stop = pickup["value"][0]

        self.assertEqual(stop["facility"], "North Warehouse")
        self.assertIsNone(stop["date"])
        self.assertTrue(pickup["metadata"]["partial_stop_candidate"])

    def test_stop_candidate_profile_is_opt_in(self):
        artifact = _artifact(["PU 1", "Name: North Warehouse", "Date: 06/05/2026"])

        baseline = generate_field_candidates(
            artifact,
            stop_candidate_profile=STOP_CANDIDATE_PROFILE_BASELINE,
        )
        enabled = generate_field_candidates(
            artifact,
            stop_candidate_profile=STOP_CANDIDATE_PROFILE_OCR_BLOCK_ASSEMBLY_V1,
        )

        baseline_generators = {
            summary["generator_name"] for summary in baseline["generator_summaries"]
        }
        enabled_generators = {
            summary["generator_name"] for summary in enabled["generator_summaries"]
        }

        self.assertNotIn(GENERATOR_OCR_STOP_BLOCK_ASSEMBLER, baseline_generators)
        self.assertIn(GENERATOR_OCR_STOP_BLOCK_ASSEMBLER, enabled_generators)
        self.assertGreater(
            sum(
                1
                for candidate in enabled["candidates"]
                if candidate.get("parser_name") == GENERATOR_OCR_STOP_BLOCK_ASSEMBLER
                and candidate.get("field") == "pickup_stops"
            ),
            0,
        )

    def test_evaluator_counts_structured_ocr_stop_candidates(self):
        artifact = _artifact(
            [
                "PU 1",
                "Name: North Warehouse",
                "Date: 06/05/2026",
                "Time: 10:00",
                "123 Main St",
                "Dallas TX 75001",
            ]
        )
        blocks = detect_stop_evidence_blocks_from_artifact(artifact)
        candidates, _diagnostics = candidates_from_stop_evidence_blocks(blocks)
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
            "document_id": "DOC-OCR-STOPS",
            "file_hash": "hash-ocr-stops",
            "file_name": "doc.pdf",
            "artifact_summary": {
                "ocr_provider_summary": {"status": "success", "ocr_text_page_count": 1}
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

        self.assertGreater(summary["ocr_structured_stop_candidates"], 0)
        self.assertEqual(summary["ocr_stop_candidates_selected"], 1)
        self.assertFalse(summary["raw_text_printed"])
        self.assertNotIn("North Warehouse", json.dumps(summary))

    def test_cli_parses_stop_candidate_profile(self):
        buffer = StringIO()
        with self.assertRaises(SystemExit) as raised, redirect_stdout(buffer):
            measurement_main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--ratecon-shadow-stop-candidate-profile", buffer.getvalue())
        self.assertIn(STOP_CANDIDATE_PROFILE_OCR_BLOCK_ASSEMBLY_V1, buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
