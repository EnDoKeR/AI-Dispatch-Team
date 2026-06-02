import json
import unittest

from app.document_ai.load_identity_forensics import (
    analyze_load_identity_label_hits,
    summarize_load_identity_forensics,
)


def artifact(text, pages=None):
    return {
        "document_id": "DOC-001",
        "source": "native",
        "pages": pages or [{"page_number": 1, "text": text}],
        "full_text": text,
    }


class LoadIdentityForensicsTests(unittest.TestCase):
    def test_same_line_value_classified(self):
        records = analyze_load_identity_label_hits(artifact("Load #: FAKE123"))

        self.assertEqual(records[0]["hit_type"], "same_line_value_present")
        self.assertTrue(records[0]["candidate_extraction_attempts"][0]["accepted"])

    def test_adjacent_next_value_classified(self):
        records = analyze_load_identity_label_hits(artifact("Load #\nFAKE123"))

        self.assertEqual(records[0]["hit_type"], "adjacent_next_value_present")

    def test_adjacent_previous_value_classified(self):
        records = analyze_load_identity_label_hits(artifact("FAKE123\nLoad #"))

        self.assertEqual(records[0]["hit_type"], "adjacent_previous_value_present")

    def test_label_only_no_nearby_value_classified(self):
        records = analyze_load_identity_label_hits(artifact("Load #"))

        self.assertEqual(records[0]["hit_type"], "label_only_no_value_nearby")

    def test_rejected_shapes_have_reasons(self):
        records = analyze_load_identity_label_hits(
            artifact(
                "Load #: 06/10/2026\n"
                "Shipment #: 555-123-4567\n"
                "Tender #: 100.00\n"
                "Order #: 123 Fake Street"
            )
        )
        reasons = [
            attempt["rejection_reason"]
            for record in records
            for attempt in record["candidate_extraction_attempts"]
            if attempt["rejection_reason"]
        ]

        self.assertIn("candidate_looks_like_date", reasons)
        self.assertIn("candidate_looks_like_phone", reasons)
        self.assertIn("candidate_looks_like_money", reasons)
        self.assertIn("candidate_looks_like_address", reasons)

    def test_reference_only_label_is_weak_ambiguous_hit_type(self):
        records = analyze_load_identity_label_hits(artifact("PO #: FAKE123"))

        self.assertEqual(records[0]["hit_type"], "po_bol_reference_only")

    def test_summary_is_safe_without_raw_values(self):
        records = analyze_load_identity_label_hits(artifact("Load #: FAKE123"))
        summary = summarize_load_identity_forensics(records, emitted_candidates=1)
        payload = json.dumps(summary)

        self.assertNotIn("FAKE123", payload)
        self.assertEqual(summary["label_hits"], 1)
        self.assertEqual(summary["emitted_candidates"], 1)


if __name__ == "__main__":
    unittest.main()
