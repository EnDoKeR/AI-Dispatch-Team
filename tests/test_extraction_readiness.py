import json
import unittest

from app.document_ai.extraction_readiness import (
    READINESS_ASSESSMENT_VERSION,
    READINESS_LEVEL_DISPATCH_DECISION_READY,
    READINESS_LEVEL_EXTRACTION_REVIEW_READY,
    READINESS_LEVEL_INTAKE_CORE_READY,
    READINESS_LEVEL_NOT_READY,
    assess_extraction_readiness,
    build_readiness_assessment,
)


def _field(name, status):
    return {"field_name": name, "status": status}


class ExtractionReadinessTests(unittest.TestCase):
    def test_not_ready_without_signals(self):
        assessment = assess_extraction_readiness({"document_alias": "RATECON_001"})

        self.assertEqual(assessment["readiness_level"], READINESS_LEVEL_NOT_READY)
        self.assertFalse(assessment["extraction_review_ready"])

    def test_extraction_review_ready_with_candidates(self):
        assessment = assess_extraction_readiness(
            {
                "document_alias": "RATECON_002",
                "candidate_counts_by_field": {"rate": 1},
                "field_statuses": [_field("rate", "needs_review")],
            }
        )

        self.assertEqual(
            assessment["readiness_level"],
            READINESS_LEVEL_EXTRACTION_REVIEW_READY,
        )
        self.assertTrue(assessment["extraction_review_ready"])
        self.assertIn("broker_identity", assessment["blocking_fields"])

    def test_intake_core_ready_with_review_fields(self):
        row = {
            "document_alias": "RATECON_003",
            "field_statuses": [
                _field("broker_name", "needs_review"),
                _field("load_number", "resolved"),
                _field("rate", "resolved"),
                _field("pickup_location", "low_confidence"),
                _field("pickup_date", "needs_review"),
                _field("delivery_location", "resolved"),
                _field("delivery_date", "resolved"),
                _field("equipment", "needs_review"),
            ],
        }

        assessment = assess_extraction_readiness(row)

        self.assertEqual(assessment["readiness_level"], READINESS_LEVEL_INTAKE_CORE_READY)
        self.assertTrue(assessment["intake_core_ready"])
        self.assertFalse(assessment["dispatch_decision_ready"])
        self.assertIn("equipment", assessment["review_fields"])

    def test_broker_mc_missing_does_not_block_intake_core_by_itself(self):
        row = {
            "document_alias": "RATECON_CORE",
            "field_statuses": [
                _field("broker_name", "resolved"),
                _field("broker_mc", "missing"),
                _field("load_number", "resolved"),
                _field("rate", "resolved"),
                _field("pickup_location", "resolved"),
                _field("pickup_date", "resolved"),
                _field("delivery_location", "resolved"),
                _field("delivery_date", "resolved"),
            ],
        }

        assessment = assess_extraction_readiness(row)

        self.assertEqual(assessment["readiness_level"], READINESS_LEVEL_INTAKE_CORE_READY)
        self.assertTrue(assessment["intake_core_ready"])
        self.assertIn("broker_mc", assessment["review_fields"])
        self.assertNotIn("broker_mc", assessment["intake_core_blockers"])
        self.assertNotIn("broker_mc", assessment["dispatch_decision_blockers"])

    def test_equipment_missing_does_not_block_intake_core_by_itself(self):
        row = {
            "document_alias": "RATECON_CORE",
            "field_statuses": [
                _field("broker_name", "resolved"),
                _field("load_number", "resolved"),
                _field("rate", "resolved"),
                _field("pickup_location", "resolved"),
                _field("pickup_date", "resolved"),
                _field("delivery_location", "resolved"),
                _field("delivery_date", "resolved"),
                _field("equipment", "missing"),
            ],
        }

        assessment = assess_extraction_readiness(row)

        self.assertEqual(assessment["readiness_level"], READINESS_LEVEL_INTAKE_CORE_READY)
        self.assertTrue(assessment["intake_core_ready"])
        self.assertIn("equipment", assessment["review_fields"])
        self.assertIn("equipment", assessment["optional_missing_fields"])
        self.assertNotIn("equipment", assessment["intake_core_blockers"])
        self.assertIn("equipment", assessment["dispatch_decision_blockers"])

    def test_weight_and_commodity_missing_remain_visible_for_review(self):
        row = {
            "document_alias": "RATECON_CORE",
            "field_statuses": [
                _field("broker_name", "resolved"),
                _field("load_number", "resolved"),
                _field("rate", "resolved"),
                _field("pickup_location", "resolved"),
                _field("pickup_date", "resolved"),
                _field("delivery_location", "resolved"),
                _field("delivery_date", "resolved"),
                _field("weight", "missing"),
                _field("commodity", "missing"),
            ],
        }

        assessment = assess_extraction_readiness(row)

        self.assertTrue(assessment["intake_core_ready"])
        self.assertFalse(assessment["dispatch_decision_ready"])
        self.assertIn("weight", assessment["review_fields"])
        self.assertIn("commodity", assessment["review_fields"])
        self.assertIn("weight", assessment["optional_missing_fields"])
        self.assertIn("commodity", assessment["optional_missing_fields"])
        self.assertNotIn("weight", assessment["intake_core_blockers"])
        self.assertNotIn("commodity", assessment["intake_core_blockers"])

    def test_rate_missing_blocks_intake_core_ready(self):
        row = {
            "document_alias": "RATECON_CORE",
            "field_statuses": [
                _field("broker_name", "resolved"),
                _field("load_number", "resolved"),
                _field("rate", "missing"),
                _field("pickup_location", "resolved"),
                _field("pickup_date", "resolved"),
                _field("delivery_location", "resolved"),
                _field("delivery_date", "resolved"),
            ],
        }

        assessment = assess_extraction_readiness(row)

        self.assertEqual(
            assessment["readiness_level"],
            READINESS_LEVEL_EXTRACTION_REVIEW_READY,
        )
        self.assertFalse(assessment["intake_core_ready"])
        self.assertIn("rate", assessment["blocking_fields"])
        self.assertIn("rate", assessment["intake_core_blockers"])

    def test_pickup_or_delivery_core_missing_blocks_intake_core_ready(self):
        row = {
            "document_alias": "RATECON_CORE",
            "field_statuses": [
                _field("broker_name", "resolved"),
                _field("load_number", "resolved"),
                _field("rate", "resolved"),
                _field("pickup_location", "resolved"),
                _field("pickup_date", "missing"),
                _field("delivery_location", "resolved"),
                _field("delivery_date", "resolved"),
            ],
        }

        assessment = assess_extraction_readiness(row)

        self.assertFalse(assessment["intake_core_ready"])
        self.assertIn("pickup_date", assessment["blocking_fields"])
        self.assertIn("pickup_date", assessment["intake_core_blockers"])

    def test_dispatch_decision_ready_is_stricter(self):
        row = {
            "document_alias": "RATECON_004",
            "normal_load_movement": True,
            "field_statuses": [
                _field("broker_name", "resolved"),
                _field("broker_mc", "resolved"),
                _field("load_number", "resolved"),
                _field("rate", "resolved"),
                _field("pickup_location", "resolved"),
                _field("pickup_date", "resolved"),
                _field("pickup_time", "resolved"),
                _field("delivery_location", "resolved"),
                _field("delivery_date", "resolved"),
                _field("delivery_time", "resolved"),
                _field("equipment", "resolved"),
                _field("weight", "resolved"),
                _field("commodity", "resolved"),
                _field("special_requirement", "resolved"),
            ],
        }

        assessment = assess_extraction_readiness(row)

        self.assertEqual(
            assessment["readiness_level"],
            READINESS_LEVEL_DISPATCH_DECISION_READY,
        )
        self.assertTrue(assessment["dispatch_decision_ready"])

    def test_tonu_stop_fields_are_non_applicable_for_core(self):
        row = {
            "document_alias": "RATECON_TONU",
            "document_type": "TRUCK_ORDER_NOT_USED",
            "field_statuses": [
                _field("broker_name", "resolved"),
                _field("load_number", "resolved"),
                _field("rate", "needs_review"),
            ],
        }

        assessment = assess_extraction_readiness(row)

        self.assertEqual(assessment["readiness_level"], READINESS_LEVEL_INTAKE_CORE_READY)
        self.assertIn("pickup_location", assessment["non_applicable_fields"])
        self.assertIn("tonu_stop_fields_not_required_for_core_readiness", assessment["reasons"])
        self.assertNotIn("pickup_location", assessment["intake_core_blockers"])
        self.assertFalse(assessment["dispatch_decision_ready"])
        self.assertIn(
            "dispatch_decision_not_applicable_for_document_context",
            assessment["reasons"],
        )

    def test_supplemental_doc_can_be_review_ready_but_not_core_ready(self):
        row = {
            "document_alias": "RATECON_SUPP",
            "classification_status": "supplemental_only",
            "extraction_relevant": False,
            "field_statuses": [_field("rate", "resolved")],
        }

        assessment = assess_extraction_readiness(row)

        self.assertEqual(
            assessment["readiness_level"],
            READINESS_LEVEL_EXTRACTION_REVIEW_READY,
        )
        self.assertTrue(assessment["extraction_review_ready"])
        self.assertFalse(assessment["intake_core_ready"])
        self.assertFalse(assessment["dispatch_decision_ready"])
        self.assertEqual(assessment["intake_core_blockers"], [])
        self.assertIn(
            "intake_core_not_applicable_for_document_context",
            assessment["reasons"],
        )

    def test_ocr_doc_not_ready_without_digital_missing_core_blockers(self):
        row = {
            "document_alias": "RATECON_OCR",
            "extraction_status": "EMPTY_TEXT",
            "field_statuses": [_field("rate", "missing")],
        }

        assessment = assess_extraction_readiness(row)

        self.assertEqual(assessment["readiness_level"], READINESS_LEVEL_NOT_READY)
        self.assertFalse(assessment["extraction_review_ready"])
        self.assertIn("ocr_needed", assessment["extraction_review_blockers"])
        self.assertEqual(assessment["intake_core_blockers"], [])

    def test_serialization(self):
        assessment = build_readiness_assessment(
            document_alias="RATECON_005",
            readiness_level="intake core ready",
            extraction_review_ready=True,
            intake_core_ready=True,
            blocking_fields=["weight"],
            review_fields=["equipment"],
            warning_codes=["needs_ops_review"],
        )
        payload = json.loads(json.dumps(assessment, sort_keys=True))

        self.assertEqual(payload["assessment_version"], READINESS_ASSESSMENT_VERSION)
        self.assertEqual(payload["readiness_level"], READINESS_LEVEL_INTAKE_CORE_READY)
        self.assertIn("equipment", payload["review_fields"])


if __name__ == "__main__":
    unittest.main()
