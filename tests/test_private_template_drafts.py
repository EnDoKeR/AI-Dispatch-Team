import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.private_template_drafts import (
    DEFAULT_PRIVATE_TEMPLATE_DRAFT_DIR,
    build_private_template_draft_skeleton,
    write_private_template_draft_skeletons,
)


class PrivateTemplateDraftTests(unittest.TestCase):
    def test_skeleton_json_uses_safe_placeholders_and_warnings(self):
        family = {
            "family_alias": "TEMPLATE_FAMILY_001",
            "aliases": ["RATECON_001"],
            "common_redacted_markers": ["rate", "stop"],
            "likely_rate_labels_redacted": ["Carrier Pay: <MONEY>"],
            "likely_stop_labels_redacted": ["Pickup: <CITY_STATE_OR_LOCATION>"],
            "likely_reference_labels_redacted": ["Load #: <REF>"],
        }

        skeleton = build_private_template_draft_skeleton(family, index=1)
        payload = json.dumps(skeleton)

        self.assertEqual(skeleton["template_id"], "PRIVATE_TEMPLATE_DRAFT_001")
        self.assertEqual(skeleton["source"], "private_local_draft")
        self.assertFalse(skeleton["active"])
        self.assertIn("local_private_template_draft_only", skeleton["warnings"])
        self.assertIn("<MONEY>", payload)
        self.assertNotIn("FAKE BROKER LLC", payload)

    def test_write_skeletons_to_local_only_output_dir(self):
        families = [
            {
                "family_alias": "TEMPLATE_FAMILY_001",
                "aliases": ["RATECON_001"],
                "common_redacted_markers": ["rate"],
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_private_template_draft_skeletons(families, output_dir=temp_dir)
            payload = json.loads(paths[0].read_text(encoding="utf-8"))

        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].name, "TEMPLATE_FAMILY_001.template_skeleton.json")
        self.assertEqual(payload["template_id"], "PRIVATE_TEMPLATE_DRAFT_001")

    def test_default_output_path_is_local_measurement_tree(self):
        self.assertEqual(
            DEFAULT_PRIVATE_TEMPLATE_DRAFT_DIR,
            Path(".local_outputs/private_ratecon_measurement/private_template_drafts"),
        )


if __name__ == "__main__":
    unittest.main()
