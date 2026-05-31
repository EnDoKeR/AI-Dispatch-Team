import json
import unittest

from app.document_ai.private_measurement_pipeline import (
    _load_identifier_audit_records,
    _load_identifier_coverage_metrics,
)
from app.document_ai.ratecon_candidates import FIELD_LOAD_NUMBER, FIELD_REFERENCE


def _candidate(identifier_type, field_name, primary=False, warnings=None):
    return {
        "field_name": field_name,
        "identifier_type": identifier_type,
        "value_type": identifier_type,
        "primary_load_identifier_candidate": primary,
        "warnings": warnings or [],
    }


def _resolution(status):
    return {
        "resolutions": [
            {
                "field_name": FIELD_LOAD_NUMBER,
                "status": status,
            }
        ]
    }


class LoadIdentifierCoverageInstrumentationTests(unittest.TestCase):
    def test_load_number_candidate_increments_primary_mapping(self):
        candidates = [
            _candidate("broker_load_number", FIELD_LOAD_NUMBER, primary=True)
        ]

        metrics = _load_identifier_coverage_metrics(candidates, _resolution("resolved"))
        records = _load_identifier_audit_records(
            "RATECON_001",
            candidates,
            _resolution("resolved"),
        )

        self.assertEqual(metrics["primary_identifier_candidate_count"], 1)
        self.assertEqual(metrics["core_load_number_mapping_count"], 1)
        self.assertTrue(
            any(record["identifier_label_category"] == "load_number" for record in records)
        )

    def test_order_number_candidate_increments_order_category(self):
        candidates = [_candidate("order_number", FIELD_LOAD_NUMBER, primary=True)]

        records = _load_identifier_audit_records(
            "RATECON_001",
            candidates,
            _resolution("resolved"),
        )

        self.assertTrue(
            any(record["identifier_label_category"] == "order_number" for record in records)
        )

    def test_po_and_bol_references_are_rejected_non_primary(self):
        candidates = [
            _candidate("po_number", FIELD_REFERENCE),
            _candidate("bol_number", FIELD_REFERENCE),
        ]

        metrics = _load_identifier_coverage_metrics(candidates, _resolution("missing"))
        records = _load_identifier_audit_records(
            "RATECON_001",
            candidates,
            _resolution("missing"),
        )

        self.assertEqual(metrics["typed_reference_candidate_count"], 2)
        self.assertEqual(metrics["rejected_reference_as_load_id_count"], 2)
        rejected_categories = {
            record["identifier_label_category"]
            for record in records
            if record["stage"] == "non_primary_reference_rejected"
        }
        self.assertEqual(rejected_categories, {"po_number", "bol_number"})

    def test_generic_header_reference_review_case_is_captured(self):
        candidates = [
            _candidate(
                "primary_reference",
                FIELD_LOAD_NUMBER,
                primary=True,
                warnings=["generic_identifier_requires_review"],
            )
        ]

        metrics = _load_identifier_coverage_metrics(
            candidates,
            _resolution("needs_review"),
        )
        records = _load_identifier_audit_records(
            "RATECON_001",
            candidates,
            _resolution("needs_review"),
        )

        self.assertEqual(metrics["weak_generic_reference_review_required"], 1)
        self.assertTrue(
            any(
                record["identifier_label_category"] == "generic_reference"
                for record in records
            )
        )

    def test_audit_records_do_not_include_private_values(self):
        candidates = [
            {
                "field_name": FIELD_REFERENCE,
                "identifier_type": "po_number",
                "value_type": "po_number",
                "value": "FAKE-PO-001",
                "primary_load_identifier_candidate": False,
            }
        ]

        records = _load_identifier_audit_records(
            "RATECON_001",
            candidates,
            _resolution("missing"),
        )

        self.assertNotIn("FAKE-PO-001", json.dumps(records))


if __name__ == "__main__":
    unittest.main()
