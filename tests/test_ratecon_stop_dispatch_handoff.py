import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.field_candidate_resolver import resolve_candidates
from app.document_ai.ratecon_gold_labels import (
    FIELD_PICKUP_STOPS,
    SYSTEM_SHADOW,
    SYSTEM_SHADOW_BEST_DISPATCH_USABLE_STOP,
    SYSTEM_SHADOW_BEST_OCR_COLUMN_STOP,
    SYSTEM_SHADOW_STOP_REVIEW_DRAFT,
    build_stop_gold_completeness_summary,
    evaluate_ratecon_against_gold,
)
from app.document_ai.ratecon_shadow_audit import build_private_eval_values
from app.document_ai.ratecon_stop_component_policy import (
    STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
    apply_stop_column_strict_profile_to_candidates,
)
from app.document_ai.ratecon_stop_draft_profile import (
    STOP_DRAFT_PROFILE_DISPATCH_USABLE_REVIEW_V1,
    STOP_DRAFT_PROFILE_NONE,
)
from scripts.create_ratecon_stop_gold_review_packets import (
    build_patch_template,
    build_stop_gold_review_packet,
    write_packet,
)
from scripts.apply_ratecon_stop_gold_review_patch import (
    _require_safe_path,
    plan_stop_gold_patch,
)


def _dispatch_candidate():
    return {
        "field": FIELD_PICKUP_STOPS,
        "value": [
            {
                "role": "pickup",
                "stop_index": 1,
                "city": "Dallas",
                "state": "TX",
                "date": "06/05/2026",
                "appointment_window": "0700 to 1500",
            }
        ],
        "confidence": 0.82,
        "source": "ocr",
        "parser_name": "ocr_stop_table_reconstructor",
        "metadata": {
            "candidate_id": "pickup-column-1",
            "structured_stop_candidate": True,
            "dispatch_usable": True,
            "assembled_from_column_geometry": True,
            "pairing_method": "ocr_geometry_column_row",
            "stop_role": "pickup",
            "has_location": True,
            "has_date": True,
            "has_time": True,
            "has_facility": False,
            "has_address": False,
            "row_boundary_confidence": 0.75,
            "column_alignment_confidence": 0.75,
            "stop_column_status": "medium",
            "stop_column_warnings": [],
        },
    }


def _placeholder_stop_candidate(candidate_id="placeholder-pickup", stop_abstained=False):
    return {
        "field": FIELD_PICKUP_STOPS,
        "value": "pickup_stop_complete",
        "confidence": 0.4,
        "source": "ocr",
        "parser_name": "ocr_stop_table_reconstructor",
        "metadata": {
            "candidate_id": candidate_id,
            "structured_stop_candidate": True,
            "assembled_from_column_geometry": True,
            "pairing_method": "ocr_geometry_column_row",
            "stop_role": "pickup",
            "stop_index": 1,
            "has_location": not stop_abstained,
            "has_date": False,
            "has_time": False,
            "stop_abstained": stop_abstained,
            "stop_selection_policy": "abstain" if stop_abstained else "partial_review",
            "stop_abstention_reason": "no_location_or_date" if stop_abstained else "location_only_review",
        },
    }


def _gold_label():
    return {
        "document_id": "DOC-HANDOFF",
        "file_hash": "hash-handoff",
        "file_name": "handoff.pdf",
        "label_status": "labeled",
        "gold": {
            "pickup_stops": [
                {
                    "city": "Dallas",
                    "state": "TX",
                    "date": "2026-06-05",
                    "appointment_window": "07:00-15:00",
                }
            ]
        },
    }


def _incomplete_gold_label():
    label = _gold_label()
    label["gold"] = {
        "pickup_stops": [
            {
                "date": "2026-06-05",
                "appointment_window": "07:00-15:00",
            }
        ]
    }
    return label


def _audit_record(candidates, resolved, stop_draft_profile=STOP_DRAFT_PROFILE_NONE):
    return {
        "document_id": "DOC-HANDOFF",
        "file_hash": "hash-handoff",
        "file_name": "handoff.pdf",
        "shadow": {
            "resolved_fields": resolved.get("resolved_fields", {}),
            "resolver_decision_traces": resolved.get("resolver_decision_traces", {}),
        },
        "legacy": {},
        "private_eval_values": build_private_eval_values(
            raw_resolved=resolved.get("resolved_fields", {}),
            candidates=candidates,
            stop_draft_profile=stop_draft_profile,
        ),
    }


class RateConStopDispatchHandoffTests(unittest.TestCase):
    def test_dispatch_candidate_handoff_and_candidate_best_groups(self):
        candidates = apply_stop_column_strict_profile_to_candidates([_dispatch_candidate()])
        resolved = resolve_candidates(
            candidates,
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
        )
        audit = _audit_record(
            candidates,
            resolved,
            stop_draft_profile=STOP_DRAFT_PROFILE_DISPATCH_USABLE_REVIEW_V1,
        )

        evaluation = evaluate_ratecon_against_gold([_gold_label()], [audit])
        handoff = evaluation["dispatch_usable_handoff_summary"]
        groups = evaluation["stop_candidate_group_metrics"]
        drafts = evaluation["stop_draft_profile_metrics"]

        self.assertEqual(handoff["dispatch_usable_candidates"], 1)
        self.assertEqual(handoff["kept_after_dedupe"], 1)
        self.assertEqual(handoff["resolver_eligible"], 1)
        self.assertEqual(handoff["serialized_for_eval"], 1)
        self.assertIn("evaluator_usability_tier_counts", handoff)
        self.assertEqual(handoff["serialized_gap_count"], 0)
        self.assertGreater(
            groups[SYSTEM_SHADOW_BEST_DISPATCH_USABLE_STOP]["pickup"]["dispatch_usable"]
            + groups[SYSTEM_SHADOW_BEST_DISPATCH_USABLE_STOP]["pickup"]["exact_complete"],
            0,
        )
        self.assertGreater(
            groups[SYSTEM_SHADOW_BEST_OCR_COLUMN_STOP]["pickup"]["dispatch_usable"]
            + groups[SYSTEM_SHADOW_BEST_OCR_COLUMN_STOP]["pickup"]["exact_complete"],
            0,
        )
        self.assertGreater(
            drafts[SYSTEM_SHADOW_STOP_REVIEW_DRAFT]["pickup"]["dispatch_usable"]
            + drafts[SYSTEM_SHADOW_STOP_REVIEW_DRAFT]["pickup"]["exact_complete"],
            0,
        )

    def test_draft_profile_default_none_and_explicit_review_draft(self):
        candidates = apply_stop_column_strict_profile_to_candidates([_dispatch_candidate()])
        resolved = resolve_candidates(
            candidates,
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
        )

        default_payload = build_private_eval_values(
            raw_resolved=resolved.get("resolved_fields", {}),
            candidates=candidates,
            stop_draft_profile=STOP_DRAFT_PROFILE_NONE,
        )
        explicit_payload = build_private_eval_values(
            raw_resolved=resolved.get("resolved_fields", {}),
            candidates=candidates,
            stop_draft_profile=STOP_DRAFT_PROFILE_DISPATCH_USABLE_REVIEW_V1,
        )

        self.assertEqual(default_payload["shadow_stop_review_draft"], {})
        self.assertIn(FIELD_PICKUP_STOPS, explicit_payload["shadow_stop_review_draft"])
        self.assertTrue(explicit_payload["shadow_stop_review_draft"][FIELD_PICKUP_STOPS]["review_required"])

    def test_selected_structured_stop_components_serialize_in_private_eval(self):
        candidates = apply_stop_column_strict_profile_to_candidates([_dispatch_candidate()])
        resolved = resolve_candidates(
            candidates,
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
        )
        payload = build_private_eval_values(
            raw_resolved=resolved.get("resolved_fields", {}),
            candidates=candidates,
            stop_draft_profile=STOP_DRAFT_PROFILE_NONE,
        )
        selected = payload["shadow_selected_stop"][FIELD_PICKUP_STOPS]

        self.assertTrue(selected["component_values_serialized"])
        self.assertIsInstance(selected["value"], list)
        self.assertEqual(selected["value"][0]["city"], "Dallas")
        self.assertNotEqual(selected.get("source_status"), "shadow_component_not_serialized")

    def test_abstained_selected_stop_placeholder_is_missing_not_serialized_gap(self):
        candidate = _placeholder_stop_candidate(stop_abstained=True)
        resolved = {
            "resolved_fields": {
                FIELD_PICKUP_STOPS: {
                    "selected_candidate": candidate,
                    "confidence": 0.4,
                }
            }
        }
        audit = _audit_record([candidate], resolved)

        selected = audit["private_eval_values"]["shadow_selected_stop"][FIELD_PICKUP_STOPS]
        evaluation = evaluate_ratecon_against_gold([_gold_label()], [audit])
        shadow_row = next(
            row
            for row in evaluation["comparison_rows"]
            if row["system"] == SYSTEM_SHADOW and row["field"] == FIELD_PICKUP_STOPS
        )

        self.assertEqual(selected["source_status"], "shadow_extractor_missing")
        self.assertEqual(selected["serialization_gap_reason"], "selected_stop_really_missing")
        self.assertEqual(shadow_row["dispatch_usability_tier"], "missing_review_required")
        self.assertEqual(evaluation["selected_stop_serialization_gap_summary"]["total"], 0)

    def test_candidate_id_mismatch_is_not_joined_to_wrong_structured_candidate(self):
        selected_candidate = _placeholder_stop_candidate(candidate_id="selected-other")
        structured_candidate = _dispatch_candidate()
        structured_candidate["source"] = selected_candidate["source"]
        structured_candidate["parser_name"] = selected_candidate["parser_name"]
        resolved = {
            "resolved_fields": {
                FIELD_PICKUP_STOPS: {
                    "selected_candidate": selected_candidate,
                    "confidence": 0.4,
                }
            }
        }
        audit = _audit_record([structured_candidate], resolved)
        selected = audit["private_eval_values"]["shadow_selected_stop"][FIELD_PICKUP_STOPS]
        evaluation = evaluate_ratecon_against_gold([_gold_label()], [audit])

        self.assertFalse(selected["component_values_serialized"])
        self.assertEqual(selected["source_status"], "shadow_component_not_serialized")
        self.assertEqual(selected["serialization_gap_reason"], "private_eval_sidecar_missing_components")
        self.assertEqual(
            evaluation["selected_stop_serialization_gap_summary"]["reason_counts"],
            {"private_eval_sidecar_missing_components": 1},
        )

    def test_stop_gold_review_packet_is_local_only_and_does_not_modify_gold(self):
        candidates = apply_stop_column_strict_profile_to_candidates([_dispatch_candidate()])
        resolved = resolve_candidates(
            candidates,
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
        )
        audit = _audit_record(
            candidates,
            resolved,
            stop_draft_profile=STOP_DRAFT_PROFILE_DISPATCH_USABLE_REVIEW_V1,
        )
        gold = [_gold_label()]

        packet = build_stop_gold_review_packet(
            gold,
            [audit],
            include_private_values_local_only=True,
        )

        self.assertFalse(packet["gold_labels_modified"])
        self.assertTrue(packet["local_only"])
        self.assertTrue(packet["private_values_printed"])
        self.assertIn("stop_gold_completeness_summary", packet)
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = write_packet(packet, Path(tmpdir))
            self.assertTrue(Path(paths["items_json"]).exists())
            self.assertTrue(Path(paths["summary_md"]).exists())
            self.assertTrue(Path(paths["items_csv"]).exists())
            self.assertTrue(Path(paths["code_issues_csv"]).exists())
            self.assertTrue(Path(paths["manual_review_items_csv"]).exists())
            self.assertTrue(Path(paths["patch_template_json"]).exists())
            self.assertTrue(Path(paths["selected_stop_serialization_gaps_csv"]).exists())
            self.assertTrue(Path(paths["selected_stop_serialization_gaps_json"]).exists())
            self.assertTrue(Path(paths["selected_stop_component_side_by_side_csv"]).exists())

    def test_patch_template_only_includes_true_gold_review_rows(self):
        candidates = apply_stop_column_strict_profile_to_candidates([_dispatch_candidate()])
        resolved = resolve_candidates(
            candidates,
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
        )
        audit = _audit_record(
            candidates,
            resolved,
            stop_draft_profile=STOP_DRAFT_PROFILE_DISPATCH_USABLE_REVIEW_V1,
        )

        complete_packet = build_stop_gold_review_packet([_gold_label()], [audit])
        incomplete_packet = build_stop_gold_review_packet([_incomplete_gold_label()], [audit])

        self.assertEqual(build_patch_template(complete_packet)["patches"], [])
        self.assertEqual(len(build_patch_template(incomplete_packet)["patches"]), 1)
        proposed = build_patch_template(incomplete_packet)["patches"][0]["proposed_gold"]
        self.assertTrue(all(value is None for value in proposed.values()))

    def test_candidate_has_dispatch_components_can_be_unsafe_against_gold(self):
        candidate = _dispatch_candidate()
        candidate["value"][0]["city"] = "Houston"
        candidate["value"][0]["facility"] = "Wrong Facility"
        candidates = apply_stop_column_strict_profile_to_candidates([candidate])
        resolved = resolve_candidates(
            candidates,
            field_names=[FIELD_PICKUP_STOPS],
            stop_ranking_profile=STOP_RANKING_PROFILE_COLUMN_STRICT_V1,
        )
        audit = _audit_record(
            candidates,
            resolved,
            stop_draft_profile=STOP_DRAFT_PROFILE_DISPATCH_USABLE_REVIEW_V1,
        )

        evaluation = evaluate_ratecon_against_gold([_gold_label()], [audit])
        rows = [
            row
            for row in evaluation["comparison_rows"]
            if row["system"] == SYSTEM_SHADOW_BEST_DISPATCH_USABLE_STOP
            and row["field"] == FIELD_PICKUP_STOPS
            and row.get("predicted")
        ]

        self.assertEqual(rows[0]["candidate_has_dispatch_components"], True)
        self.assertEqual(rows[0]["dispatch_usability_tier"], "unsafe_wrong")
        self.assertEqual(rows[0]["gold_dispatch_usable_match"], False)
        self.assertIn("structural only", rows[0]["dispatch_usability_note"])

    def test_stop_gold_completeness_counts_components(self):
        summary = build_stop_gold_completeness_summary([_gold_label()])

        pickup = summary["pickup"]
        self.assertEqual(pickup["stops_checked"], 1)
        self.assertEqual(pickup["component_present_counts"]["city"], 1)
        self.assertEqual(pickup["component_present_counts"]["date"], 1)
        self.assertEqual(pickup["component_present_counts"]["appointment_window"], 1)
        self.assertEqual(pickup["component_missing_counts"]["facility"], 1)
        self.assertEqual(pickup["complete_for_dispatch_usable"], 1)
        self.assertEqual(pickup["complete_for_exact"], 1)

    def test_stop_gold_patch_dry_run_uses_only_explicit_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gold_dir = Path(tmpdir)
            label_path = gold_dir / "handoff.gold.json"
            label_path.write_text(
                json.dumps(_gold_label()),
                encoding="utf-8",
            )
            patch = {
                "patches": [
                    {
                        "document_id": "DOC-HANDOFF",
                        "file_hash": "hash-handoff",
                        "file_name": "handoff.pdf",
                        "field": FIELD_PICKUP_STOPS,
                        "stop_index": 1,
                        "proposed_gold": {
                            "facility": None,
                            "address": "123 Main St",
                            "city": "",
                        },
                    }
                ]
            }

            planned, skipped = plan_stop_gold_patch(gold_dir, patch)

            self.assertEqual(len(planned), 1)
            self.assertEqual(skipped, [])
            self.assertEqual(planned[0]["updates"], {"address": "123 Main St"})
            self.assertNotIn("facility", planned[0]["updates"])

    def test_stop_gold_patch_refuses_unsafe_paths_without_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(SystemExit):
                _require_safe_path(Path(tmpdir), "gold dir")


if __name__ == "__main__":
    unittest.main()
