import copy
import inspect
import json
import unittest

from app.market_intelligence.intake import rate_confirmation_intake
from app.market_intelligence.intake.rate_confirmation_intake import (
    STATUS_MISSING_FIELDS,
    STATUS_READY_FOR_REVIEW,
    STATUS_REVIEW_REQUIRED,
    build_broker_contact,
    build_extracted_field_evidence,
    build_field_candidate,
    build_money_amount,
    build_rate_confirmation_intake,
    build_reference,
    build_stop,
)


VALID_SOURCE = {
    "document_id": "DOC-001",
    "broker_name": "FAKE BROKER LLC",
    "load_number": "FAKE-LOAD-001",
    "rate": 2500,
    "pickup_location": "Fake City, ST 00000",
    "pickup_date": "2026-05-30",
    "delivery_location": "Example City, ST 00000",
    "delivery_date": "2026-05-31",
    "commodity": "FAKE COMMODITY",
    "weight": 42000,
    "equipment": "FAKE EQUIPMENT",
}


class RateConfirmationIntakeTests(unittest.TestCase):
    def test_builds_minimal_valid_intake(self):
        intake = build_rate_confirmation_intake(VALID_SOURCE)

        self.assertEqual(intake["document_id"], "DOC-001")
        self.assertEqual(intake["broker_name"], "FAKE BROKER LLC")
        self.assertEqual(intake["load_number"], "FAKE-LOAD-001")
        self.assertEqual(intake["rate"]["amount"], 2500)
        self.assertEqual(intake["status"], STATUS_READY_FOR_REVIEW)
        self.assertFalse(intake["review_required"])
        self.assertFalse(intake["raw_text_included"])
        self.assertFalse(intake["cases_created"])

    def test_missing_critical_fields_are_recorded(self):
        source = dict(VALID_SOURCE)
        source["rate"] = ""
        source["pickup_date"] = ""

        intake = build_rate_confirmation_intake(source)

        self.assertEqual(intake["status"], STATUS_MISSING_FIELDS)
        self.assertIn("rate", intake["missing_fields"])
        self.assertIn("pickup_date", intake["missing_fields"])
        self.assertTrue(intake["review_required"])

    def test_low_confidence_fields_are_recorded(self):
        source = dict(VALID_SOURCE)
        source["field_confidences"] = {
            "rate": "LOW",
        }

        intake = build_rate_confirmation_intake(source)

        self.assertEqual(intake["status"], STATUS_REVIEW_REQUIRED)
        self.assertIn("rate", intake["needs_check_fields"])
        self.assertTrue(intake["review_required"])

    def test_optional_broker_mc_and_equipment_do_not_block_ready_status(self):
        source = dict(VALID_SOURCE)
        source.pop("equipment")

        intake = build_rate_confirmation_intake(source)

        self.assertEqual(intake["status"], STATUS_READY_FOR_REVIEW)
        self.assertNotIn("broker_mc", intake["missing_fields"])
        self.assertNotIn("equipment", intake["missing_fields"])

    def test_typed_references_supported(self):
        source = dict(VALID_SOURCE)
        source["references"] = [
            build_reference(
                reference_type="PO",
                value="FAKE-PO-001",
                source="fake_fixture",
                confidence="HIGH",
            )
        ]

        intake = build_rate_confirmation_intake(source)

        self.assertEqual(intake["references"][0]["reference_type"], "PO")
        self.assertEqual(intake["references"][0]["value"], "FAKE-PO-001")

    def test_stops_supported(self):
        source = dict(VALID_SOURCE)
        source["stops"] = [
            build_stop(
                stop_type="PICKUP",
                sequence=1,
                location="Fake City, ST 00000",
                date="2026-05-30",
            ),
            build_stop(
                stop_type="DELIVERY",
                sequence=2,
                location="Example City, ST 00000",
                date="2026-05-31",
            ),
        ]

        intake = build_rate_confirmation_intake(source)

        self.assertEqual(len(intake["stops"]), 2)
        self.assertEqual(intake["stops"][0]["stop_type"], "PICKUP")

    def test_evidence_and_candidates_supported_without_raw_text(self):
        source = dict(VALID_SOURCE)
        source["rate"] = build_money_amount(
            amount=2500,
            confidence="HIGH",
            evidence_refs=["EVIDENCE-RATE-1"],
        )
        source["field_evidence"] = [
            build_extracted_field_evidence(
                evidence_id="EVIDENCE-RATE-1",
                document_id="DOC-001",
                page=1,
                source_method="synthetic",
                redacted_context="TOTAL: USD $ <AMOUNT>",
                confidence="HIGH",
            )
        ]
        source["field_candidates"] = [
            build_field_candidate(
                field_name="rate",
                candidate_value=2500,
                normalized_value=2500,
                confidence="HIGH",
                evidence_ref="EVIDENCE-RATE-1",
            )
        ]

        intake = build_rate_confirmation_intake(source)

        self.assertEqual(intake["rate"]["evidence_refs"], ["EVIDENCE-RATE-1"])
        self.assertEqual(
            intake["field_evidence"][0]["redacted_context"],
            "TOTAL: USD $ <AMOUNT>",
        )
        self.assertFalse(intake["raw_text_included"])

    def test_raw_text_is_not_included_by_default(self):
        source = dict(VALID_SOURCE)
        source["raw_text"] = "PRIVATE TEXT SHOULD NOT ENTER CONTRACT"
        source["extracted_text"] = "PRIVATE EXTRACTED TEXT SHOULD NOT ENTER CONTRACT"

        intake = build_rate_confirmation_intake(source)

        self.assertNotIn("raw_text", intake)
        self.assertNotIn("extracted_text", intake)
        self.assertFalse(intake["raw_text_included"])

    def test_conflicting_field_candidates_require_review(self):
        source = dict(VALID_SOURCE)
        source["field_candidates"] = [
            build_field_candidate(field_name="rate", normalized_value=2500),
            build_field_candidate(field_name="rate", normalized_value=2600),
        ]

        intake = build_rate_confirmation_intake(source)

        self.assertEqual(intake["status"], STATUS_REVIEW_REQUIRED)
        self.assertIn("rate", intake["needs_check_fields"])

    def test_broker_contact_shape(self):
        contact = build_broker_contact(
            name="FAKE CONTACT",
            phone="000-000-0000",
            email="fake@example.invalid",
            role="dispatcher",
            source="fake_fixture",
            confidence="medium",
        )

        self.assertEqual(contact["confidence"], "MEDIUM")
        self.assertEqual(contact["role"], "dispatcher")

    def test_serialization_round_trip(self):
        intake = build_rate_confirmation_intake(VALID_SOURCE)

        payload = json.loads(json.dumps(intake))

        self.assertEqual(payload["document_id"], "DOC-001")
        self.assertEqual(payload["status"], STATUS_READY_FOR_REVIEW)

    def test_does_not_mutate_input(self):
        source = copy.deepcopy(VALID_SOURCE)
        source["field_confidences"] = {"rate": "LOW"}
        before = copy.deepcopy(source)

        build_rate_confirmation_intake(source)

        self.assertEqual(source, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(rate_confirmation_intake).lower()
        forbidden = [
            "telegram",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "gspread",
            "googlemaps",
            "dat_api",
            "pypdf",
            "pdfplumber",
            "pytesseract",
            "openai",
            "gmail",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
