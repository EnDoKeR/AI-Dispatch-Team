import unittest

from app.document_ai.ratecon_gold_labels import (
    FIELD_DELIVERY_STOPS,
    FIELD_PICKUP_STOPS,
    evaluate_ratecon_against_gold,
    normalize_time,
)


def _gold_label():
    return {
        "schema_version": "ratecon_gold_label_v1",
        "document_id": "DOC-USABILITY",
        "file_hash": "hash-usability",
        "file_name": "doc.pdf",
        "label_status": "labeled",
        "gold": {
            "document_type": "rate_confirmation",
            "pickup_stops": [
                {
                    "role": "pickup",
                    "city": "Dallas",
                    "state": "TX",
                    "date": "06/01/2026",
                    "appointment_window": "07:00-15:00",
                }
            ],
            "delivery_stops": [
                {
                    "role": "delivery",
                    "city": "Houston",
                    "state": "TX",
                    "date": "06/02/2026",
                    "time": "13:00",
                }
            ],
        },
    }


def _audit(selected):
    return {
        "document_id": "DOC-USABILITY",
        "file_hash": "hash-usability",
        "file_name": "doc.pdf",
        "shadow": {"resolved_fields": {}},
        "legacy": {},
        "private_eval_values": {"shadow_selected": selected},
    }


class RateConStopUsabilityTests(unittest.TestCase):
    def test_time_window_normalization_equivalence(self):
        self.assertEqual(normalize_time("07:00-15:00"), "07:00-15:00")
        self.assertEqual(normalize_time("0700 to 1500"), "07:00-15:00")
        self.assertEqual(normalize_time("FCFS 08:00 to 14:00"), "08:00-14:00")
        self.assertEqual(normalize_time("Appt 13:00"), "13:00")

    def test_exact_complete_and_dispatch_usable_tiers(self):
        selected = {
            FIELD_PICKUP_STOPS: {
                "value": [
                    {
                        "role": "pickup",
                        "city": "Dallas",
                        "state": "TX",
                        "date": "2026-06-01",
                    }
                ],
                "confidence": 0.71,
                "source": "ocr",
                "parser_name": "ocr_stop_table_reconstructor",
                "metadata_summary": {"stop_role": "pickup", "has_location": True, "has_date": True},
            },
            FIELD_DELIVERY_STOPS: {
                "value": [
                    {
                        "role": "delivery",
                        "city": "Houston",
                        "state": "TX",
                        "date": "2026-06-02",
                        "time": "13:00",
                    }
                ],
                "confidence": 0.86,
                "source": "ocr",
                "parser_name": "ocr_stop_table_reconstructor",
                "metadata_summary": {"stop_role": "delivery", "has_location": True, "has_date": True, "has_time": True},
            },
        }

        evaluation = evaluate_ratecon_against_gold([_gold_label()], [_audit(selected)])
        usability = evaluation["stop_usability_summary"]

        self.assertEqual(usability["pickup"]["dispatch_usable"], 1)
        self.assertEqual(usability["delivery"]["exact_complete"], 1)

    def test_useful_partial_unsafe_wrong_and_serialized_gap(self):
        selected = {
            FIELD_PICKUP_STOPS: {
                "value": [{"role": "pickup", "city": "Dallas", "state": "TX"}],
                "confidence": 0.61,
                "source": "native_layout",
                "parser_name": "layout_stop_table_candidate_generator",
                "metadata_summary": {"stop_role": "pickup", "has_location": True},
            },
            FIELD_DELIVERY_STOPS: {
                "value": [{"role": "delivery", "city": "Austin", "state": "TX", "date": "2026-06-02"}],
                "confidence": 0.70,
                "source": "ocr",
                "parser_name": "ocr_stop_table_reconstructor",
                "metadata_summary": {"stop_role": "delivery", "has_location": True, "has_date": True},
            },
        }
        evaluation = evaluate_ratecon_against_gold([_gold_label()], [_audit(selected)])
        usability = evaluation["stop_usability_summary"]
        audit = evaluation["stop_gold_consistency_audit"]

        self.assertEqual(usability["pickup"]["useful_partial"], 1)
        self.assertEqual(usability["delivery"]["unsafe_wrong"], 1)
        self.assertIn("true_wrong_location", audit["reason_counts"])

        serialized = {
            FIELD_PICKUP_STOPS: {
                "value": "",
                "confidence": 0.0,
                "source_status": "shadow_component_not_serialized",
            }
        }
        evaluation = evaluate_ratecon_against_gold([_gold_label()], [_audit(serialized)])
        self.assertEqual(evaluation["stop_usability_summary"]["pickup"]["serialized_gap"], 1)


if __name__ == "__main__":
    unittest.main()
