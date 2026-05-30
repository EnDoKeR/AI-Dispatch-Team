import json
import unittest

from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_FIELD_DATE,
    NORMALIZED_STOP_FIELD_LOCATION,
    NORMALIZED_STOP_FIELD_STATUS_CONFLICT,
    NORMALIZED_STOP_FIELD_STATUS_MISSING,
    NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
    NORMALIZED_STOP_FIELD_STATUS_REVIEW_REQUIRED,
    NORMALIZED_STOP_SET_VERSION,
    NORMALIZED_STOP_TYPE_DELIVERY,
    NORMALIZED_STOP_TYPE_PICKUP,
    NORMALIZED_STOP_TYPE_UNKNOWN,
    build_normalized_stop,
    build_normalized_stop_field,
    build_normalized_stop_set,
)
from app.document_ai.ratecon_candidates import CANDIDATE_CONFIDENCE_HIGH


class NormalizedStopContractTests(unittest.TestCase):
    def test_create_pickup_stop(self):
        field = build_normalized_stop_field(
            field_name=NORMALIZED_STOP_FIELD_LOCATION,
            status=NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
            selected_candidate_id="cand_pickup_location",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
            evidence_refs=[{"table_id": "T1", "cell_ref": "r1c2"}],
        )
        stop = build_normalized_stop(
            stop_id="stop_001",
            sequence=1,
            stop_type=NORMALIZED_STOP_TYPE_PICKUP,
            source_group_ids=["group_001"],
            page_numbers=[1],
            table_ids=["T1"],
            row_indices=[1],
            fields=[field],
            confidence=CANDIDATE_CONFIDENCE_HIGH,
        )

        self.assertEqual(stop["stop_type"], NORMALIZED_STOP_TYPE_PICKUP)
        self.assertEqual(stop["sequence"], 1)
        self.assertEqual(stop["fields"][0]["status"], NORMALIZED_STOP_FIELD_STATUS_RESOLVED)

    def test_create_delivery_stop(self):
        stop = build_normalized_stop(
            stop_id="stop_002",
            stop_type=NORMALIZED_STOP_TYPE_DELIVERY,
            fields=[
                build_normalized_stop_field(
                    NORMALIZED_STOP_FIELD_DATE,
                    NORMALIZED_STOP_FIELD_STATUS_MISSING,
                )
            ],
        )

        self.assertEqual(stop["stop_type"], NORMALIZED_STOP_TYPE_DELIVERY)
        self.assertEqual(stop["fields"][0]["field_name"], NORMALIZED_STOP_FIELD_DATE)

    def test_multi_stop_set_counts_types(self):
        stop_set = build_normalized_stop_set(
            document_alias="RATECON_001",
            stops=[
                build_normalized_stop("stop_001", 1, NORMALIZED_STOP_TYPE_PICKUP),
                build_normalized_stop("stop_002", 2, NORMALIZED_STOP_TYPE_DELIVERY),
                build_normalized_stop("stop_003", 3, NORMALIZED_STOP_TYPE_DELIVERY),
            ],
        )

        self.assertEqual(stop_set["pickup_count"], 1)
        self.assertEqual(stop_set["delivery_count"], 2)
        self.assertEqual(stop_set["unknown_count"], 0)

    def test_conflict_field_is_reported(self):
        stop = build_normalized_stop(
            stop_id="stop_conflict",
            stop_type=NORMALIZED_STOP_TYPE_PICKUP,
            fields=[
                build_normalized_stop_field(
                    NORMALIZED_STOP_FIELD_DATE,
                    NORMALIZED_STOP_FIELD_STATUS_CONFLICT,
                    warning_codes=["conflicting_stop_date"],
                )
            ],
        )
        stop_set = build_normalized_stop_set(stops=[stop])

        self.assertIn("stop_conflict.date", stop_set["conflict_fields"])

    def test_review_required_stop_serializes(self):
        stop = build_normalized_stop(
            stop_id="stop_unknown",
            stop_type="unclear",
            review_required=True,
            fields=[
                build_normalized_stop_field(
                    NORMALIZED_STOP_FIELD_LOCATION,
                    NORMALIZED_STOP_FIELD_STATUS_REVIEW_REQUIRED,
                )
            ],
        )
        stop_set = build_normalized_stop_set(stops=[stop])
        payload = json.loads(json.dumps(stop_set, sort_keys=True))

        self.assertEqual(payload["stop_set_version"], NORMALIZED_STOP_SET_VERSION)
        self.assertEqual(payload["stops"][0]["stop_type"], NORMALIZED_STOP_TYPE_UNKNOWN)
        self.assertTrue(payload["stops"][0]["review_required"])
        self.assertIn("stop_unknown.location", payload["unresolved_fields"])

    def test_contract_requires_no_private_values(self):
        field = build_normalized_stop_field(
            NORMALIZED_STOP_FIELD_LOCATION,
            NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
            selected_candidate_id="candidate_alias_only",
        )

        self.assertNotIn("raw_value", field)
        self.assertNotIn("normalized_value", field)


if __name__ == "__main__":
    unittest.main()
