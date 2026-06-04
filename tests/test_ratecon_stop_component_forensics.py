import json
from contextlib import redirect_stdout
from io import StringIO
import unittest

from app.document_ai.field_candidate_resolver import (
    FIELD_DELIVERY_STOPS,
    FIELD_PICKUP_STOPS,
    resolve_candidates,
)
from app.document_ai.ratecon_gold_labels import evaluate_ratecon_against_gold
from app.document_ai.ratecon_stop_component_policy import (
    STOP_RANKING_PROFILE_BASELINE,
    STOP_RANKING_PROFILE_COMPONENT_STRICT_V1,
    apply_stop_component_strict_profile_to_candidates,
)
from scripts.run_private_ratecon_measurement import main as measurement_main


def _stop_candidate(field, role, city="Dallas", date="2026-06-01", source="native_layout", confidence=0.82):
    return {
        "field": field,
        "value": [
            {
                "role": role,
                "stop_index": 1,
                "city": city,
                "date": date,
            }
        ],
        "normalized_value": f"{role}_stop",
        "label": f"{role}_stop",
        "evidence_text": f"{role} stop structured evidence",
        "source": source,
        "parser_name": "layout_stop_table_candidate_generator",
        "confidence": confidence,
        "metadata": {
            "structured_stop_candidate": True,
            "stop_role": role,
            "has_location": bool(city),
            "has_date": bool(date),
            "has_time": False,
            "canonical_mapping_strength": "strong",
        },
    }


def _gold_label():
    return {
        "schema_version": "ratecon_gold_label_v1",
        "document_id": "DOC-STOP",
        "file_hash": "hash-stop",
        "file_name": "doc.pdf",
        "label_status": "labeled",
        "gold": {
            "document_type": "rate_confirmation",
            "load_number": {"value": "LOAD-1"},
            "total_carrier_rate": {"value": 1200.0, "currency": "USD"},
            "pickup_stops": [
                {
                    "stop_index": 1,
                    "city": "Dallas",
                    "state": "TX",
                    "date": "2026-06-01",
                    "time": "10:00",
                }
            ],
            "delivery_stops": [
                {
                    "stop_index": 1,
                    "city": "Houston",
                    "state": "TX",
                    "date": "2026-06-02",
                    "time": "13:00",
                }
            ],
        },
    }


class RateConStopComponentForensicsTests(unittest.TestCase):
    def test_stop_strict_abstains_unknown_role_candidate(self):
        unknown = _stop_candidate(FIELD_PICKUP_STOPS, "unknown")
        adjusted = apply_stop_component_strict_profile_to_candidates([unknown])

        self.assertTrue(adjusted[0]["metadata"]["stop_abstained"])
        self.assertEqual(adjusted[0]["metadata"]["stop_abstention_reason"], "unknown_role")

        resolved = resolve_candidates(
            adjusted,
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COMPONENT_STRICT_V1,
        )
        pickup = resolved["resolved_fields"][FIELD_PICKUP_STOPS]
        self.assertEqual(pickup["value"], "")
        self.assertTrue(pickup["needs_review"])

    def test_stop_strict_selects_complete_role_scoped_candidate(self):
        pickup = _stop_candidate(FIELD_PICKUP_STOPS, "pickup")
        resolved = resolve_candidates(
            [pickup],
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COMPONENT_STRICT_V1,
        )

        selected = resolved["resolved_fields"][FIELD_PICKUP_STOPS]
        self.assertIn("pickup_stop", selected["value"])
        self.assertEqual(selected["source"], "native_layout")

    def test_baseline_profile_preserves_unknown_role_selection_path(self):
        unknown = _stop_candidate(FIELD_PICKUP_STOPS, "unknown")
        resolved = resolve_candidates(
            [unknown],
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_BASELINE,
        )

        selected = resolved["resolved_fields"][FIELD_PICKUP_STOPS]
        self.assertIn("pickup_stop", selected["value"])
        self.assertNotIn(
            "stop_abstained",
            selected["selected_candidate"].get("metadata_summary", {}),
        )

    def test_gold_evaluator_counts_partial_stop_and_component_forensics(self):
        audit = {
            "document_id": "DOC-STOP",
            "file_hash": "hash-stop",
            "file_name": "doc.pdf",
            "shadow": {"resolved_fields": {}},
            "legacy": {},
            "private_eval_values": {
                "shadow_selected": {
                    FIELD_PICKUP_STOPS: {
                        "value": [{"role": "pickup", "city": "Dallas"}],
                        "confidence": 0.68,
                        "source": "native_layout",
                        "parser_name": "layout_stop_table_candidate_generator",
                        "metadata_summary": {
                            "stop_role": "pickup",
                            "has_location": True,
                            "has_date": False,
                            "stop_selection_policy": "partial_review",
                        },
                    }
                }
            },
        }

        evaluation = evaluate_ratecon_against_gold([_gold_label()], [audit])
        pickup_metric = evaluation["field_metrics"]["shadow"][FIELD_PICKUP_STOPS]
        forensics = evaluation["stop_component_forensics_summary"][FIELD_PICKUP_STOPS]

        self.assertEqual(pickup_metric["partial_match_count"], 1)
        self.assertEqual(forensics["partial_match"], 1)
        self.assertEqual(forensics["wrong"], 0)
        self.assertFalse(evaluation["stop_component_forensics_summary"]["raw_text_printed"])

    def test_gold_evaluator_detects_role_swap_and_serialized_gap(self):
        audit = {
            "document_id": "DOC-STOP",
            "file_hash": "hash-stop",
            "file_name": "doc.pdf",
            "shadow": {"resolved_fields": {}},
            "legacy": {},
            "private_eval_values": {
                "shadow_selected": {
                    FIELD_DELIVERY_STOPS: {
                        "value": [{"role": "pickup", "city": "Dallas"}],
                        "confidence": 0.82,
                        "source": "native_layout",
                        "parser_name": "layout_stop_table_candidate_generator",
                        "metadata_summary": {
                            "stop_role": "pickup",
                            "has_location": True,
                            "has_date": False,
                        },
                    },
                    FIELD_PICKUP_STOPS: {
                        "value": "",
                        "confidence": 0.0,
                        "source_status": "shadow_component_not_serialized",
                    },
                }
            },
        }

        evaluation = evaluate_ratecon_against_gold([_gold_label()], [audit])
        delivery = evaluation["stop_component_forensics_summary"][FIELD_DELIVERY_STOPS]
        pickup = evaluation["stop_component_forensics_summary"][FIELD_PICKUP_STOPS]

        self.assertEqual(delivery["role_swapped_count"], 1)
        self.assertEqual(delivery["wrong_reason_counts"]["pickup_delivery_swapped"], 1)
        self.assertEqual(pickup["serialized_gap"], 1)

    def test_ocr_stop_evidence_gap_summary_counts_ocr_components(self):
        audit = {
            "document_id": "DOC-STOP",
            "file_hash": "hash-stop",
            "file_name": "doc.pdf",
            "artifact_summary": {
                "ocr_provider_summary": {"status": "success", "ocr_text_page_count": 1}
            },
            "shadow": {"resolved_fields": {}},
            "legacy": {},
            "private_eval_values": {
                "shadow_selected": {},
                "stop_component_candidate_inventory": [
                    {
                        "field": "pickup_location",
                        "source": "ocr",
                        "value": "private-city",
                        "metadata_summary": {"ocr_candidate": True},
                    },
                    {
                        "field": "pickup_date",
                        "source": "ocr",
                        "value": "private-date",
                        "metadata_summary": {"ocr_candidate": True},
                    },
                    {
                        "field": "delivery_location",
                        "source": "ocr",
                        "value": "private-city",
                        "metadata_summary": {"ocr_candidate": True},
                    },
                ],
            },
        }

        evaluation = evaluate_ratecon_against_gold([_gold_label()], [audit])
        summary = evaluation["ocr_stop_evidence_gap_summary"]

        self.assertEqual(summary["ocr_docs"], 1)
        self.assertEqual(summary["ocr_pickup_location_candidates"], 1)
        self.assertEqual(summary["ocr_pickup_date_candidates"], 1)
        self.assertEqual(summary["ocr_delivery_location_candidates"], 1)
        self.assertEqual(summary["rejection_reason_counts"]["not_assembled_structured_stop"], 3)
        self.assertNotIn("private-city", json.dumps(summary))

    def test_cli_parses_stop_ranking_profile(self):
        buffer = StringIO()
        with self.assertRaises(SystemExit) as raised, redirect_stdout(buffer):
            measurement_main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--ratecon-shadow-stop-ranking-profile", buffer.getvalue())
        self.assertIn(STOP_RANKING_PROFILE_COMPONENT_STRICT_V1, buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
