import json
import unittest

from app.document_ai.private_measurement import (
    BLOCKER_CONFLICTING_CRITICAL_FIELD,
    BLOCKER_OCR_NEEDED,
    EXTRACTION_STATUS_EMPTY_TEXT,
    EXTRACTION_STATUS_TEXT_EXTRACTED,
    FIELD_STATUS_CONFLICT,
    FIELD_STATUS_MISSING,
    FIELD_STATUS_RESOLVED,
    build_field_status_summary,
    build_private_ratecon_measurement_row,
)
from app.document_ai.private_measurement_reports import (
    build_private_ratecon_measurement_aggregate,
    compare_private_measurement_to_known_baseline,
)


class PrivateMeasurementReportTests(unittest.TestCase):
    def _rows(self):
        return [
            build_private_ratecon_measurement_row(
                document_alias="RATECON_001",
                triage_route="DIGITAL_TEXT",
                extraction_status=EXTRACTION_STATUS_TEXT_EXTRACTED,
                document_type="RATE_CONFIRMATION",
                ratecon_eligible=True,
                classification_status="ratecon_eligible",
                page_role_counts={"MAIN_RATECONF": 1},
                section_role_counts={"RATE_SUMMARY": 1},
                extraction_scope_counts={"RATECON_CORE_ALLOWED": 1},
                template_status="unknown",
                field_statuses=[
                    build_field_status_summary("rate", FIELD_STATUS_RESOLVED),
                    build_field_status_summary("weight", FIELD_STATUS_MISSING),
                ],
                missing_fields=["weight"],
                blocker_categories=["MISSING_CRITICAL_FIELD"],
                review_required=True,
            ),
            build_private_ratecon_measurement_row(
                document_alias="RATECON_002",
                triage_route="OCR_NEEDED",
                extraction_status=EXTRACTION_STATUS_EMPTY_TEXT,
                document_type="UNKNOWN",
                ratecon_eligible=False,
                classification_status="unknown_review_required",
                template_status="unknown",
                field_statuses=[
                    build_field_status_summary("rate", FIELD_STATUS_MISSING),
                ],
                missing_fields=["rate"],
                blocker_categories=[BLOCKER_OCR_NEEDED],
                review_required=True,
            ),
            build_private_ratecon_measurement_row(
                document_alias="RATECON_003",
                triage_route="DIGITAL_TEXT",
                extraction_status=EXTRACTION_STATUS_TEXT_EXTRACTED,
                document_type="RATE_CONFIRMATION",
                ratecon_eligible=True,
                classification_status="ratecon_eligible",
                page_role_counts={"MAIN_RATECONF": 1},
                section_role_counts={"RATE_SUMMARY": 1},
                extraction_scope_counts={"RATECON_CORE_ALLOWED": 1},
                template_status="matched",
                field_statuses=[
                    build_field_status_summary("rate", FIELD_STATUS_CONFLICT),
                ],
                conflict_fields=["rate"],
                unresolved_fields=["rate"],
                needs_check_fields=["rate"],
                blocker_categories=[BLOCKER_CONFLICTING_CRITICAL_FIELD],
                review_required=True,
            ),
        ]

    def test_aggregate_counts_core_statuses(self):
        aggregate = build_private_ratecon_measurement_aggregate(self._rows())

        self.assertEqual(aggregate["document_count"], 3)
        self.assertEqual(aggregate["total_documents"], 3)
        self.assertEqual(aggregate["text_extracted_count"], 2)
        self.assertEqual(aggregate["empty_text_count"], 1)
        self.assertEqual(aggregate["ocr_needed_count"], 1)
        self.assertEqual(aggregate["review_required_count"], 3)
        self.assertEqual(aggregate["template_status_counts"]["unknown"], 2)
        self.assertEqual(aggregate["document_type_counts"]["RATE_CONFIRMATION"], 2)
        self.assertEqual(aggregate["ratecon_eligible_count"], 2)
        self.assertEqual(aggregate["extraction_relevant_count"], 2)
        self.assertEqual(aggregate["normal_load_movement_count"], 2)
        self.assertEqual(aggregate["classification_status_counts"]["ratecon_eligible"], 2)
        self.assertEqual(aggregate["eligible_critical_field_denominator"], 2)
        self.assertEqual(aggregate["normal_load_critical_field_denominator"], 2)

    def test_aggregate_counts_missing_conflict_and_needs_check_fields(self):
        aggregate = build_private_ratecon_measurement_aggregate(self._rows())

        self.assertEqual(aggregate["critical_field_missing_counts"]["rate"], 1)
        self.assertEqual(aggregate["critical_field_missing_counts"]["weight"], 1)
        self.assertEqual(aggregate["eligible_critical_field_missing_counts"]["weight"], 1)
        self.assertEqual(aggregate["normal_load_critical_field_missing_counts"]["weight"], 1)
        self.assertNotIn("rate", aggregate["eligible_critical_field_missing_counts"])
        self.assertEqual(aggregate["conflict_counts_by_field"]["rate"], 1)
        self.assertEqual(aggregate["unresolved_counts_by_field"]["rate"], 1)
        self.assertEqual(aggregate["needs_check_counts_by_field"]["rate"], 1)

    def test_non_applicable_fields_are_counted_separately(self):
        rows = [
            build_private_ratecon_measurement_row(
                document_alias="DOC_BOL",
                document_type="BILL_OF_LADING",
                supplemental_only=True,
                non_applicable_fields=["rate", "pickup_location"],
                skipped_fields=["rate", "pickup_location"],
            )
        ]

        aggregate = build_private_ratecon_measurement_aggregate(rows)

        self.assertEqual(aggregate["non_applicable_counts_by_field"]["rate"], 1)
        self.assertEqual(aggregate["skipped_counts_by_field"]["pickup_location"], 1)

    def test_tonu_is_extraction_relevant_but_not_normal_load_denominator(self):
        rows = [
            build_private_ratecon_measurement_row(
                document_alias="DOC_TONU",
                document_type="TRUCK_ORDER_NOT_USED",
                ratecon_eligible=True,
                missing_fields=["pickup_location", "rate"],
            ),
            build_private_ratecon_measurement_row(
                document_alias="DOC_RATECON",
                document_type="RATE_CONFIRMATION",
                ratecon_eligible=True,
                missing_fields=["weight"],
            ),
        ]

        aggregate = build_private_ratecon_measurement_aggregate(rows)

        self.assertEqual(aggregate["ratecon_eligible_count"], 2)
        self.assertEqual(aggregate["extraction_relevant_count"], 2)
        self.assertEqual(aggregate["normal_load_movement_count"], 1)
        self.assertEqual(aggregate["tonu_count"], 1)
        self.assertEqual(aggregate["normal_load_critical_field_missing_counts"], {"weight": 1})

    def test_aggregate_counts_blockers(self):
        aggregate = build_private_ratecon_measurement_aggregate(self._rows())

        self.assertEqual(aggregate["blocker_category_counts"][BLOCKER_OCR_NEEDED], 1)
        self.assertEqual(
            aggregate["blocker_category_counts"][BLOCKER_CONFLICTING_CRITICAL_FIELD],
            1,
        )

    def test_aggregate_serializes_without_private_values(self):
        aggregate = build_private_ratecon_measurement_aggregate(self._rows())
        payload = json.dumps(aggregate)

        self.assertNotIn("FAKE BROKER LLC", payload)
        self.assertFalse(aggregate["raw_text_saved"])
        self.assertTrue(aggregate["private_values_redacted"])

    def test_aggregate_counts_stop_span_metrics(self):
        rows = [
            build_private_ratecon_measurement_row(
                document_alias="RATECON_SPAN_001",
                layout_provider_status="success",
                stop_span_extractor_enabled=True,
                span_anchor_count=2,
                stop_span_count=2,
                span_normalized_stop_count=2,
                span_pickup_count=1,
                span_delivery_count=1,
                span_date_resolved_count=2,
                span_time_missing_count=2,
                span_review_required_count=1,
                span_passthrough_detected=False,
            ),
            build_private_ratecon_measurement_row(
                document_alias="RATECON_SPAN_002",
                layout_provider_status="success",
                stop_span_extractor_enabled=True,
                span_anchor_count=4,
                stop_span_count=4,
                span_normalized_stop_count=4,
                span_unknown_count=4,
                span_date_missing_count=4,
                span_time_missing_count=4,
                span_passthrough_detected=True,
            ),
        ]

        aggregate = build_private_ratecon_measurement_aggregate(rows)

        self.assertEqual(aggregate["stop_span_extractor_attempted_count"], 2)
        self.assertEqual(aggregate["span_anchor_count_total"], 6)
        self.assertEqual(aggregate["span_normalized_stop_count_total"], 6)
        self.assertEqual(aggregate["span_pickup_count_total"], 1)
        self.assertEqual(aggregate["span_delivery_count_total"], 1)
        self.assertEqual(aggregate["span_unknown_count_total"], 4)
        self.assertEqual(aggregate["span_date_resolved_count_total"], 2)
        self.assertEqual(aggregate["span_date_missing_count_total"], 4)
        self.assertEqual(aggregate["span_time_missing_count_total"], 6)
        self.assertEqual(aggregate["span_review_required_count_total"], 1)
        self.assertEqual(aggregate["span_passthrough_count"], 1)

    def test_baseline_comparison_uses_counts_only(self):
        aggregate = build_private_ratecon_measurement_aggregate(self._rows())
        comparison = compare_private_measurement_to_known_baseline(
            aggregate,
            {"empty_text_count": 1, "text_extracted_count": 2},
        )

        self.assertTrue(comparison["baseline_compared"])
        self.assertEqual(comparison["empty_text_count_delta"], 0)
        self.assertFalse(comparison["comparison_uses_private_values"])

    def test_known_baseline_aliases_are_matched(self):
        comparison = compare_private_measurement_to_known_baseline(self._rows())
        aliases = {
            item["document_alias"]
            for item in comparison["alias_comparisons"]
        }

        self.assertTrue(comparison["baseline_compared"])
        self.assertIn("RATECON_001", aliases)
        self.assertIn("RATECON_002", aliases)
        self.assertIn("RATECON_003", aliases)

    def test_unknown_aliases_are_ignored(self):
        row = build_private_ratecon_measurement_row(document_alias="RATECON_999")

        comparison = compare_private_measurement_to_known_baseline([row])

        self.assertFalse(comparison["baseline_compared"])
        self.assertEqual(comparison["alias_comparisons"], [])

    def test_field_status_improvement_uses_status_counts_only(self):
        row = build_private_ratecon_measurement_row(
            document_alias="RATECON_001",
            extraction_status=EXTRACTION_STATUS_TEXT_EXTRACTED,
            missing_fields=["rate"],
        )

        comparison = compare_private_measurement_to_known_baseline([row])

        self.assertEqual(
            comparison["alias_comparisons"][0]["field_status_change"],
            "improved",
        )
        self.assertFalse(
            comparison["alias_comparisons"][0]["comparison_uses_private_values"]
        )

    def test_baseline_comparison_serializes_without_private_values(self):
        comparison = compare_private_measurement_to_known_baseline(self._rows())
        payload = json.dumps(comparison)

        self.assertNotIn("FAKE BROKER LLC", payload)
        self.assertNotIn("3200.00", payload)


if __name__ == "__main__":
    unittest.main()
