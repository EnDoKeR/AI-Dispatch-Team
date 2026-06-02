import json
import hashlib
import unittest

from app.document_ai.field_candidate_resolver import (
    FIELD_LOAD_NUMBER,
    FIELD_TOTAL_CARRIER_RATE,
    resolve_candidates,
)
from app.document_ai.ratecon_gold_labels import (
    evaluate_ratecon_against_gold,
    normalize_load_number,
)
from app.document_ai.ratecon_ocr_candidate_policy import (
    OCR_CANDIDATE_POLICY_BASELINE,
    OCR_CANDIDATE_POLICY_FILL_MISSING_STRICT_V1,
    apply_ocr_candidate_policy_to_candidates,
)


def _ocr_header_reference(value="LOAD-123", id_type_hint="load", primary=True):
    return {
        "field": "reference_numbers",
        "value": value,
        "normalized_value": value,
        "label": "Load #",
        "evidence_text": "Load # [ocr-header-value-present]",
        "source": "ocr",
        "parser_name": "header_load_identity_candidate_generator",
        "confidence": 0.82,
        "metadata": {
            "ocr_candidate": True,
            "header_load_identity_candidate": True,
            "is_primary_identifier_candidate": primary,
            "id_type_hint": id_type_hint,
            "document_region": "header",
            "label_strength": "strong",
        },
    }


def _rate_candidate(value, source="ocr", label="Total Carrier Pay", context="total_carrier_pay"):
    return {
        "field": FIELD_TOTAL_CARRIER_RATE,
        "value": value,
        "normalized_value": value,
        "label": label,
        "evidence_text": label,
        "source": source,
        "parser_name": "document_text_candidate_extractor",
        "confidence": 0.86,
        "metadata": {
            "ocr_candidate": source == "ocr",
            "money_context": context,
        },
    }


class RateConOcrCandidateForensicsTests(unittest.TestCase):
    def test_ocr_header_load_reference_promotes_under_strict_policy(self):
        adjusted = apply_ocr_candidate_policy_to_candidates(
            [_ocr_header_reference()],
            policy=OCR_CANDIDATE_POLICY_FILL_MISSING_STRICT_V1,
        )

        self.assertEqual(adjusted[0]["field"], FIELD_LOAD_NUMBER)
        self.assertTrue(adjusted[0]["metadata"]["ocr_load_promoted_to_load_number"])

        resolved = resolve_candidates(
            adjusted,
            field_names=[FIELD_LOAD_NUMBER],
            ocr_candidate_policy=OCR_CANDIDATE_POLICY_FILL_MISSING_STRICT_V1,
        )
        selected = resolved["resolved_fields"][FIELD_LOAD_NUMBER]
        self.assertEqual(selected["value"], "LOAD-123")
        self.assertEqual(selected["source"], "ocr")

    def test_ocr_pickup_reference_does_not_promote_to_load_number(self):
        candidate = _ocr_header_reference("PU-44", id_type_hint="pickup_ref", primary=False)
        adjusted = apply_ocr_candidate_policy_to_candidates(
            [candidate],
            policy=OCR_CANDIDATE_POLICY_FILL_MISSING_STRICT_V1,
        )

        self.assertEqual(adjusted[0]["field"], "reference_numbers")
        self.assertFalse(adjusted[0]["metadata"].get("ocr_load_promoted_to_load_number", False))

    def test_ocr_reference_section_confirmation_can_promote_when_penalty_is_generic(self):
        candidate = _ocr_header_reference(
            "CONF-44",
            id_type_hint="confirmation",
            primary=False,
        )
        candidate["confidence"] = 0.50
        candidate["metadata"]["document_region"] = "reference_section"
        candidate["metadata"]["context_penalty_reason"] = "money_context_unknown"
        candidate["metadata"]["label_strength"] = "weak"

        adjusted = apply_ocr_candidate_policy_to_candidates(
            [candidate],
            policy=OCR_CANDIDATE_POLICY_FILL_MISSING_STRICT_V1,
        )

        self.assertEqual(adjusted[0]["field"], FIELD_LOAD_NUMBER)
        self.assertEqual(adjusted[0]["confidence"], 0.76)
        self.assertEqual(
            adjusted[0]["metadata"]["ocr_candidate_policy_reason"],
            "ocr_header_load_identity_promoted",
        )

    def test_ocr_unknown_money_context_is_demoted_from_total_rate(self):
        candidate = _rate_candidate("$99.00", label="Amount", context="unknown")
        adjusted = apply_ocr_candidate_policy_to_candidates(
            [candidate],
            policy=OCR_CANDIDATE_POLICY_FILL_MISSING_STRICT_V1,
        )

        self.assertEqual(adjusted[0]["field"], "accessorial_term")
        self.assertTrue(adjusted[0]["metadata"]["ocr_rate_abstained"])
        self.assertTrue(adjusted[0]["metadata"]["rate_demoted_from_total_carrier_rate"])

    def test_ocr_safe_total_can_fill_missing_rate(self):
        adjusted = apply_ocr_candidate_policy_to_candidates(
            [_rate_candidate("$1,200.00")],
            policy=OCR_CANDIDATE_POLICY_FILL_MISSING_STRICT_V1,
        )

        self.assertEqual(adjusted[0]["field"], FIELD_TOTAL_CARRIER_RATE)
        self.assertEqual(adjusted[0]["metadata"]["selection_policy"], "allowed")

    def test_strict_policy_does_not_override_non_ocr_rate_candidate(self):
        candidates = [
            _rate_candidate("$1,100.00", source="native_layout"),
            _rate_candidate("$1,200.00", source="ocr"),
        ]
        adjusted = apply_ocr_candidate_policy_to_candidates(
            candidates,
            policy=OCR_CANDIDATE_POLICY_FILL_MISSING_STRICT_V1,
        )
        ocr = [candidate for candidate in adjusted if candidate["source"] == "ocr"][0]

        self.assertEqual(ocr["field"], "accessorial_term")
        self.assertEqual(
            ocr["metadata"]["ocr_rate_abstention_reason"],
            "non_ocr_rate_candidate_available",
        )

    def test_baseline_policy_preserves_candidates(self):
        candidate = _ocr_header_reference()
        adjusted = apply_ocr_candidate_policy_to_candidates(
            [candidate],
            policy=OCR_CANDIDATE_POLICY_BASELINE,
        )

        self.assertEqual(adjusted[0]["field"], "reference_numbers")

    def test_gold_evaluator_reports_ocr_load_gap_without_private_values(self):
        gold = {
            "schema_version": "ratecon_gold_label_v1",
            "document_id": "DOC-1",
            "file_hash": "hash-1",
            "file_name": "doc.pdf",
            "label_status": "labeled",
            "gold": {
                "document_type": "rate_confirmation",
                "load_number": {"value": "LOAD-123"},
                "total_carrier_rate": {"value": 1200.0, "currency": "USD"},
            },
        }
        audit = {
            "document_id": "DOC-1",
            "file_hash": "hash-1",
            "file_name": "doc.pdf",
            "artifact_summary": {
                "ocr_provider_summary": {
                    "provider_requested": "auto",
                    "status": "success",
                    "ocr_text_page_count": 1,
                },
                "ocr_document_classification": {"document_type": "rate_confirmation"},
            },
            "shadow": {"resolved_fields": {}},
            "legacy": {},
            "candidate_summary": {
                "ocr_candidate_summary": {
                    "ocr_candidates_total": 1,
                    "ocr_candidates_by_field": {"reference_numbers": 1},
                    "ocr_candidates_by_generator": {
                        "header_load_identity_candidate_generator": 1
                    },
                }
            },
            "private_eval_values": {
                "shadow_selected": {
                    FIELD_LOAD_NUMBER: {
                        "value": "LOAD-123",
                        "confidence": 0.76,
                        "source": "ocr",
                    }
                },
                "load_identity_candidate_inventory": [
                    {
                        "field": "reference_numbers",
                        "value": "LOAD-123",
                        "source": "ocr",
                        "metadata_summary": {
                            "header_load_identity_candidate": True,
                            "id_type_hint": "load",
                        },
                    }
                ],
                "rate_money_candidate_inventory": [],
                "load_visibility_probe": {
                    "full_text_token_hashes": [
                        hashlib.sha256(
                            normalize_load_number("LOAD-123").encode("utf-8")
                        ).hexdigest()
                    ]
                },
            },
        }

        evaluation = evaluate_ratecon_against_gold([gold], [audit])
        summary = evaluation["ocr_load_candidate_gap_summary"]

        self.assertEqual(summary["ocr_docs"], 1)
        self.assertEqual(summary["ocr_load_label_hits"], 1)
        self.assertEqual(
            summary["gap_reason_counts"]["ocr_load_candidate_selected"],
            1,
        )
        self.assertNotIn("LOAD-123", json.dumps(summary))
        self.assertFalse(summary["raw_text_printed"])

    def test_gold_evaluator_reports_ocr_rate_wrong_and_accessorial_noise(self):
        gold = {
            "schema_version": "ratecon_gold_label_v1",
            "document_id": "DOC-2",
            "file_hash": "hash-2",
            "file_name": "doc2.pdf",
            "label_status": "labeled",
            "gold": {
                "document_type": "rate_confirmation",
                "load_number": {"value": "LOAD-2"},
                "total_carrier_rate": {"value": 1200.0, "currency": "USD"},
            },
        }
        audit = {
            "document_id": "DOC-2",
            "file_hash": "hash-2",
            "file_name": "doc2.pdf",
            "artifact_summary": {
                "ocr_provider_summary": {
                    "provider_requested": "auto",
                    "status": "success",
                    "ocr_text_page_count": 1,
                },
                "ocr_document_classification": {"document_type": "rate_confirmation"},
            },
            "shadow": {"resolved_fields": {}},
            "legacy": {},
            "candidate_summary": {
                "ocr_candidate_summary": {
                    "ocr_accessorial_candidate_count": 3,
                    "ocr_accessorial_by_section": {"accessorial_section": 3},
                    "ocr_accessorial_deduped_or_demoted": 2,
                }
            },
            "private_eval_values": {
                "shadow_selected": {
                    FIELD_TOTAL_CARRIER_RATE: {
                        "value": "$99.00",
                        "confidence": 0.82,
                        "source": "ocr",
                        "metadata_summary": {
                            "money_context": "accessorial",
                            "rate_safety": "unsafe",
                        },
                    }
                },
                "load_identity_candidate_inventory": [],
                "rate_money_candidate_inventory": [
                    {
                        "field": "accessorial_term",
                        "value": "$99.00",
                        "source": "ocr",
                        "metadata_summary": {
                            "money_context": "accessorial",
                            "rate_safety": "unsafe",
                            "ocr_rate_abstained": True,
                        },
                    }
                ],
            },
        }

        evaluation = evaluate_ratecon_against_gold([gold], [audit])
        rate_summary = evaluation["ocr_rate_selection_summary"]
        accessorial = evaluation["ocr_accessorial_noise_summary"]

        self.assertEqual(rate_summary["ocr_wrong_rate_count"], 1)
        self.assertEqual(
            rate_summary["diagnosis_counts"]["ocr_accessorial_or_penalty"],
            1,
        )
        self.assertEqual(accessorial["ocr_accessorial_candidate_count"], 3)
        self.assertEqual(accessorial["ocr_accessorial_deduped_or_demoted"], 2)
        self.assertNotIn("$99", json.dumps(rate_summary))


if __name__ == "__main__":
    unittest.main()
