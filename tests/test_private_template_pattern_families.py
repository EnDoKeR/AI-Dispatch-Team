import json
import unittest

from app.document_ai.private_template_pattern_collector import (
    collect_redacted_template_patterns_from_text,
)
from app.document_ai.private_template_pattern_families import (
    group_redacted_patterns_into_template_families,
)


class PrivateTemplatePatternFamilyTests(unittest.TestCase):
    def test_similar_fake_templates_group_together(self):
        one = collect_redacted_template_patterns_from_text(
            "Carrier Pay: $1,000.00\nPickup: Fake City, ST\nDelivery: Other City, ST",
            "RATECON_001",
        )
        two = collect_redacted_template_patterns_from_text(
            "Carrier Pay: $2,000.00\nPickup: Example City, ST\nDelivery: Other City, ST",
            "RATECON_002",
        )

        families = group_redacted_patterns_into_template_families([one, two])

        self.assertEqual(len(families), 1)
        self.assertEqual(families[0]["aliases"], ["RATECON_001", "RATECON_002"])
        self.assertEqual(families[0]["confidence_bucket"], "medium")

    def test_different_fake_layouts_split(self):
        rate_layout = collect_redacted_template_patterns_from_text(
            "Carrier Pay: $1,000.00\nPickup: Fake City, ST",
            "RATECON_001",
        )
        table_layout = collect_redacted_template_patterns_from_text(
            "Stop 1 | Pickup | Fake City, ST | 2026-06-01",
            "RATECON_002",
        )

        families = group_redacted_patterns_into_template_families([rate_layout, table_layout])

        self.assertEqual(len(families), 2)
        self.assertEqual([family["family_alias"] for family in families], ["TEMPLATE_FAMILY_001", "TEMPLATE_FAMILY_002"])

    def test_ocr_needed_docs_group_separately(self):
        ocr = collect_redacted_template_patterns_from_text("", "RATECON_003")
        digital = collect_redacted_template_patterns_from_text(
            "Carrier Pay: $1,000.00",
            "RATECON_004",
        )

        families = group_redacted_patterns_into_template_families([ocr, digital])

        self.assertEqual(len(families), 2)
        self.assertTrue(any("ocr_needed_family_no_text_patterns" in family["warnings"] for family in families))

    def test_no_raw_values_in_family_output(self):
        summary = collect_redacted_template_patterns_from_text(
            "Broker: FAKE BROKER LLC\nLoad #: FAKE-REF-001\nCarrier Pay: $1,000.00",
            "RATECON_001",
        )
        families = group_redacted_patterns_into_template_families([summary])
        payload = json.dumps(families)

        self.assertNotIn("FAKE BROKER LLC", payload)
        self.assertNotIn("FAKE-REF-001", payload)
        self.assertNotIn("$1,000.00", payload)


if __name__ == "__main__":
    unittest.main()
