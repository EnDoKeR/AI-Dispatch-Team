import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.field_candidate_resolver import resolve_candidates
from app.document_ai.ratecon_gold_labels import (
    FIELD_PICKUP_STOPS,
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

        packet = build_stop_gold_review_packet(gold, [audit])

        self.assertFalse(packet["gold_labels_modified"])
        self.assertTrue(packet["local_only"])
        self.assertIn("stop_gold_completeness_summary", packet)
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = write_packet(packet, Path(tmpdir))
            self.assertTrue(Path(paths["items_json"]).exists())
            self.assertTrue(Path(paths["summary_md"]).exists())
            self.assertTrue(Path(paths["items_csv"]).exists())
            self.assertTrue(Path(paths["patch_template_json"]).exists())

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
