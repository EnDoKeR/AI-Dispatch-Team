import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.target_disposition import (
    TARGET_DISPOSITION_REGISTRY_JSON,
    TARGET_DISPOSITION_STATUS_COMPLETED,
    TARGET_DISPOSITION_STATUS_DEFERRED_UNTIL_REVIEW,
    TARGET_DISPOSITION_STATUS_NO_SHARED_CODE_ROOT_CAUSE,
    apply_target_dispositions_to_selection,
    build_target_disposition_record,
    build_target_disposition_registry,
    is_target_selectable,
    load_target_dispositions,
    mark_target_deferred,
    save_target_dispositions,
)


class TargetDispositionTests(unittest.TestCase):
    def test_mark_target_deferred(self):
        registry = mark_target_deferred(
            build_target_disposition_registry(),
            "load_identifier_candidate_generation",
            status=TARGET_DISPOSITION_STATUS_NO_SHARED_CODE_ROOT_CAUSE,
            reason="shared code root cause not proven",
            supporting_counts={"affected_aliases": 2},
        )

        record = registry["records"][0]
        self.assertEqual(record["target_name"], "load_identifier_candidate_generation")
        self.assertEqual(record["status"], "no_shared_code_root_cause")
        self.assertEqual(record["supporting_counts"]["affected_aliases"], 2)
        self.assertFalse(record["private_values_included"])

    def test_deferred_target_is_not_selectable_by_default(self):
        registry = build_target_disposition_registry(
            [
                build_target_disposition_record(
                    target_name="load_identifier_candidate_generation",
                    status=TARGET_DISPOSITION_STATUS_DEFERRED_UNTIL_REVIEW,
                )
            ]
        )

        self.assertFalse(
            is_target_selectable(
                "load_identifier_candidate_generation",
                registry,
            )
        )
        self.assertTrue(
            is_target_selectable(
                "load_identifier_candidate_generation",
                registry,
                allow_deferred_targets=True,
            )
        )

    def test_completed_target_is_not_selectable_unless_explicit(self):
        registry = build_target_disposition_registry(
            [
                build_target_disposition_record(
                    target_name="rate_candidate_generation_or_resolution",
                    status=TARGET_DISPOSITION_STATUS_COMPLETED,
                )
            ]
        )

        self.assertFalse(
            is_target_selectable(
                "rate_candidate_generation_or_resolution",
                registry,
            )
        )
        self.assertTrue(
            is_target_selectable(
                "rate_candidate_generation_or_resolution",
                registry,
                allow_completed_targets=True,
            )
        )

    def test_apply_target_dispositions_skips_deferred_selection(self):
        registry = mark_target_deferred(
            build_target_disposition_registry(),
            "load_identifier_candidate_generation",
            status=TARGET_DISPOSITION_STATUS_NO_SHARED_CODE_ROOT_CAUSE,
        )
        selection = {
            "selected_target": "load_identifier_candidate_generation",
            "warning_codes": [],
        }

        updated = apply_target_dispositions_to_selection(selection, registry)

        self.assertEqual(updated["previous_selected_target"], "load_identifier_candidate_generation")
        self.assertEqual(updated["selected_target"], "human_review_required")
        self.assertIn(
            "load_identifier_candidate_generation",
            updated["skipped_deferred_targets"],
        )
        self.assertIn("selected_target_deferred", updated["warning_codes"])

    def test_registry_serializes_without_private_values(self):
        registry = mark_target_deferred(
            build_target_disposition_registry(),
            "load_identifier_candidate_generation",
            status=TARGET_DISPOSITION_STATUS_NO_SHARED_CODE_ROOT_CAUSE,
            reason="source-line audit did not prove a shared code root cause",
            notes_safe="aliases and counts only",
        )

        payload = json.loads(json.dumps(registry))

        self.assertFalse(payload["private_values_included"])
        self.assertFalse(payload["raw_text_included"])
        self.assertNotIn("FAKE-LOAD", json.dumps(payload))

    def test_save_and_load_registry(self):
        registry = mark_target_deferred(
            build_target_disposition_registry(),
            "load_identifier_candidate_generation",
            status=TARGET_DISPOSITION_STATUS_DEFERRED_UNTIL_REVIEW,
        )

        with tempfile.TemporaryDirectory() as tmp:
            result = save_target_dispositions(
                registry,
                output_dir=tmp,
                allow_custom_output_dir=True,
            )
            loaded = load_target_dispositions(tmp)

            self.assertEqual(result["json"], TARGET_DISPOSITION_REGISTRY_JSON)
            self.assertTrue((Path(tmp) / TARGET_DISPOSITION_REGISTRY_JSON).exists())
            self.assertEqual(
                loaded["records"][0]["target_name"],
                "load_identifier_candidate_generation",
            )


if __name__ == "__main__":
    unittest.main()
