import json
import unittest

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_MEDIUM,
    FIELD_LOAD_NUMBER,
    FIELD_RATE,
    build_field_candidate,
)
from app.document_ai.load_identifier_candidates import (
    LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
    LOAD_IDENTIFIER_TYPE_ORDER_NUMBER,
    LOAD_IDENTIFIER_TYPE_PO_NUMBER,
    LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
    LOAD_IDENTIFIER_TYPE_TENDER_ID,
    build_load_identifier_candidate,
)
from app.document_ai.ratecon_field_resolution import (
    FIELD_RESOLUTION_STATUS_CONFLICT,
    FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE,
    FIELD_RESOLUTION_STATUS_MISSING,
    FIELD_RESOLUTION_STATUS_NEEDS_REVIEW,
    FIELD_RESOLUTION_STATUS_RESOLVED,
    build_field_resolution,
    build_ratecon_field_resolution_result,
    resolve_ratecon_fields,
)


class RateConFieldResolutionContractTests(unittest.TestCase):
    def test_resolved_field_with_one_good_candidate(self):
        candidate = build_field_candidate(
            candidate_id="rate-p1-l4",
            field_name=FIELD_RATE,
            raw_value="$2,850.00",
            normalized_value="2850.00",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
            label="Carrier Pay",
            page_number=1,
            line_number=4,
            evidence_ref="p1-l4",
        )

        resolution = build_field_resolution(
            field_name=FIELD_RATE,
            status=FIELD_RESOLUTION_STATUS_RESOLVED,
            selected_candidate=candidate,
            confidence=CANDIDATE_CONFIDENCE_HIGH,
            reasons=["single_high_confidence_candidate"],
            evidence_refs=["p1-l4"],
        )

        self.assertEqual(resolution["status"], FIELD_RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(resolution["selected_candidate"]["normalized_value"], "2850.00")
        self.assertEqual(resolution["selected_candidate_id"], "rate-p1-l4")
        self.assertEqual(resolution["selected_candidate_value"], "2850.00")
        self.assertEqual(resolution["selected_candidate_label"], "Carrier Pay")
        self.assertEqual(resolution["selected_candidate_page"], 1)
        self.assertEqual(resolution["selected_candidate_line"], 4)
        self.assertIn("p1-l4", resolution["evidence_refs"])

    def test_missing_field_resolution(self):
        resolution = build_field_resolution(
            field_name=FIELD_RATE,
            status=FIELD_RESOLUTION_STATUS_MISSING,
            reasons=["no_candidate"],
        )

        self.assertEqual(resolution["selected_candidate"], {})
        self.assertEqual(resolution["selected_candidate_id"], "")
        self.assertEqual(resolution["selected_candidate_value"], "")
        self.assertEqual(resolution["status"], FIELD_RESOLUTION_STATUS_MISSING)
        self.assertIn("no_candidate", resolution["reasons"])

    def test_conflict_field_with_rejected_candidates(self):
        selected = build_field_candidate(
            candidate_id="rate-p1-l1",
            field_name=FIELD_RATE,
            raw_value="$2,850.00",
            normalized_value="2850.00",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
        )
        rejected = build_field_candidate(
            candidate_id="rate-p1-l2",
            field_name=FIELD_RATE,
            raw_value="$3,050.00",
            normalized_value="3050.00",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
        )

        resolution = build_field_resolution(
            field_name=FIELD_RATE,
            status=FIELD_RESOLUTION_STATUS_CONFLICT,
            selected_candidate=selected,
            rejected_candidates=[rejected],
            reasons=["multiple_strong_candidates"],
        )

        self.assertEqual(resolution["status"], FIELD_RESOLUTION_STATUS_CONFLICT)
        self.assertEqual(len(resolution["rejected_candidates"]), 1)
        self.assertEqual(resolution["rejected_candidate_ids"], ["rate-p1-l2"])
        self.assertEqual(
            resolution["conflict_candidate_ids"],
            ["rate-p1-l1", "rate-p1-l2"],
        )

    def test_low_confidence_field(self):
        candidate = build_field_candidate(
            field_name=FIELD_RATE,
            raw_value="$2,850.00",
            normalized_value="2850.00",
            confidence=CANDIDATE_CONFIDENCE_LOW,
        )

        resolution = build_field_resolution(
            field_name=FIELD_RATE,
            status=FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE,
            selected_candidate=candidate,
            confidence=CANDIDATE_CONFIDENCE_LOW,
            warnings=["review_required"],
        )

        self.assertEqual(resolution["status"], FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE)
        self.assertIn("review_required", resolution["warnings"])
        self.assertIn("review_required", resolution["warning_codes"])

    def test_resolution_result_serializes(self):
        result = build_ratecon_field_resolution_result(
            document_id="doc-fake-1",
            artifact_id="artifact-fake-1",
            missing_fields=[FIELD_RATE],
            needs_check_fields=["pickup_date"],
            conflict_fields=["load_number"],
            warnings=["fake_warning"],
        )

        json.dumps(result)
        self.assertIn(FIELD_RATE, result["missing_fields"])
        self.assertIn("pickup_date", result["needs_check_fields"])
        self.assertIn("load_number", result["conflict_fields"])

    def test_load_number_candidate_maps_to_core_field(self):
        result = resolve_ratecon_fields(
            {
                "candidates": [
                    build_load_identifier_candidate(
                        identifier_type=LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
                        raw_value="FAKE-LOAD-001",
                        confidence=CANDIDATE_CONFIDENCE_HIGH,
                        label="Load #",
                    )
                ]
            },
            field_names=[FIELD_LOAD_NUMBER],
        )

        resolution = result["resolutions"][0]
        self.assertEqual(resolution["status"], FIELD_RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(resolution["selected_candidate_value"], "FAKE-LOAD-001")

    def test_order_and_tender_candidates_map_to_core_field(self):
        for identifier_type, value in [
            (LOAD_IDENTIFIER_TYPE_ORDER_NUMBER, "FAKE-ORDER-002"),
            (LOAD_IDENTIFIER_TYPE_TENDER_ID, "FAKE-TENDER-003"),
        ]:
            with self.subTest(identifier_type=identifier_type):
                result = resolve_ratecon_fields(
                    {
                        "candidates": [
                            build_load_identifier_candidate(
                                identifier_type=identifier_type,
                                raw_value=value,
                                confidence=CANDIDATE_CONFIDENCE_HIGH,
                            )
                        ]
                    },
                    field_names=[FIELD_LOAD_NUMBER],
                )

                self.assertEqual(
                    result["resolutions"][0]["status"],
                    FIELD_RESOLUTION_STATUS_RESOLVED,
                )

    def test_po_bol_reference_does_not_map_to_load_number(self):
        result = resolve_ratecon_fields(
            {
                "candidates": [
                    build_load_identifier_candidate(
                        identifier_type=LOAD_IDENTIFIER_TYPE_PO_NUMBER,
                        raw_value="FAKE-PO-003",
                        confidence=CANDIDATE_CONFIDENCE_HIGH,
                    )
                ]
            },
            field_names=[FIELD_LOAD_NUMBER],
        )

        self.assertEqual(result["resolutions"][0]["status"], FIELD_RESOLUTION_STATUS_MISSING)

    def test_conflicting_strong_load_identifiers_require_review(self):
        result = resolve_ratecon_fields(
            {
                "candidates": [
                    build_load_identifier_candidate(
                        identifier_type=LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
                        raw_value="FAKE-LOAD-004",
                        confidence=CANDIDATE_CONFIDENCE_HIGH,
                    ),
                    build_load_identifier_candidate(
                        identifier_type=LOAD_IDENTIFIER_TYPE_ORDER_NUMBER,
                        raw_value="FAKE-ORDER-004",
                        confidence=CANDIDATE_CONFIDENCE_HIGH,
                    ),
                ]
            },
            field_names=[FIELD_LOAD_NUMBER],
        )

        resolution = result["resolutions"][0]
        self.assertEqual(resolution["status"], FIELD_RESOLUTION_STATUS_CONFLICT)
        self.assertIn("load_number", result["conflict_fields"])

    def test_header_reference_requires_review_when_no_stronger_id(self):
        result = resolve_ratecon_fields(
            {
                "candidates": [
                    build_load_identifier_candidate(
                        identifier_type=LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
                        raw_value="FAKE-REF-005",
                        confidence=CANDIDATE_CONFIDENCE_MEDIUM,
                        warnings=["generic_identifier_requires_review"],
                    )
                ]
            },
            field_names=[FIELD_LOAD_NUMBER],
        )

        resolution = result["resolutions"][0]
        self.assertEqual(resolution["status"], FIELD_RESOLUTION_STATUS_NEEDS_REVIEW)
        self.assertIn("load_number", result["needs_check_fields"])


if __name__ == "__main__":
    unittest.main()
