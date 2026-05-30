import tempfile
import unittest
from pathlib import Path

from app.document_ai.layout_field_delta_audit import (
    DEBUG_BUCKET_DATE_TIME_ASSOCIATION,
    DEBUG_BUCKET_RATE_BREAKDOWN,
    DEBUG_BUCKET_STOP_ASSOCIATION,
    DELTA_NEWLY_CONFLICTING,
    DELTA_NEWLY_RESOLVED,
    DELTA_WORSENED,
    LAYOUT_FIELD_DELTA_AUDIT_MD,
    build_layout_field_delta_audit,
    write_layout_field_delta_audit_report,
)


class LayoutFieldDeltaAuditTests(unittest.TestCase):
    def _rows(self):
        return [
            {
                "document_alias": "RATECON_001",
                "candidate_counts_by_field": {"rate": 1, "pickup_location": 1},
                "layout_candidate_counts_by_field": {"rate": 2, "pickup_location": 2},
                "layout_evidence_type_counts": {"table_cell": 2, "same_row": 1},
                "layout_provider_status": "success",
                "baseline_field_statuses": {
                    "rate": "missing",
                    "pickup_location": "resolved",
                    "delivery_date": "resolved",
                },
                "layout_field_statuses": {
                    "rate": "resolved",
                    "pickup_location": "needs_review",
                    "delivery_date": "conflict",
                },
                "layout_improved_fields": ["rate"],
                "layout_worsened_fields": ["pickup_location", "delivery_date"],
                "warning_codes": ["layout_candidate_conflict"],
            }
        ]

    def test_audit_classifies_newly_resolved_and_conflicting_fields(self):
        audit = build_layout_field_delta_audit(self._rows())
        by_field = {entry["field_name"]: entry for entry in audit["entries"]}

        self.assertEqual(by_field["rate"]["delta"], DELTA_NEWLY_RESOLVED)
        self.assertEqual(by_field["delivery_date"]["delta"], DELTA_NEWLY_CONFLICTING)
        self.assertEqual(by_field["pickup_location"]["delta"], DELTA_WORSENED)

    def test_audit_buckets_worsened_fields_for_debugging(self):
        audit = build_layout_field_delta_audit(self._rows())
        by_field = {entry["field_name"]: entry for entry in audit["entries"]}

        self.assertEqual(
            by_field["pickup_location"]["recommended_debug_bucket"],
            DEBUG_BUCKET_STOP_ASSOCIATION,
        )
        self.assertEqual(
            by_field["delivery_date"]["recommended_debug_bucket"],
            DEBUG_BUCKET_DATE_TIME_ASSOCIATION,
        )
        self.assertEqual(
            by_field["rate"]["recommended_debug_bucket"],
            DEBUG_BUCKET_RATE_BREAKDOWN,
        )

    def test_report_is_alias_only_and_contains_no_private_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_layout_field_delta_audit_report(
                self._rows(),
                output_dir=temp_dir,
                allow_custom_output_dir=True,
            )
            text = path.read_text(encoding="utf-8")

        self.assertEqual(path.name, LAYOUT_FIELD_DELTA_AUDIT_MD)
        self.assertIn("RATECON_001", text)
        self.assertIn("pickup_location", text)
        self.assertNotIn("FAKE BROKER LLC", text)
        self.assertNotIn("123 Main", text)
        self.assertNotIn("raw text", text.lower().replace("no raw text", ""))

    def test_default_output_path_is_ignored_local_outputs(self):
        path = Path(".local_outputs/private_ratecon_measurement") / LAYOUT_FIELD_DELTA_AUDIT_MD

        self.assertTrue(str(path).startswith(".local_outputs"))


if __name__ == "__main__":
    unittest.main()
