"""Aggregate safe private RateCon measurement rows."""

from collections import Counter

from app.document_ai.document_classification import (
    CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED,
    DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED,
)
from app.document_ai.private_measurement import (
    EXTRACTION_STATUS_EMPTY_TEXT,
    EXTRACTION_STATUS_TEXT_EXTRACTED,
    build_private_ratecon_measurement_aggregate as build_aggregate_contract,
)


CRITICAL_MEASUREMENT_FIELDS = (
    "broker_name",
    "broker_mc",
    "rate",
    "pickup_location",
    "pickup_date",
    "delivery_location",
    "delivery_date",
    "equipment",
    "weight",
)

KNOWN_PRIVATE_RATECON_BASELINE = {
    "RATECON_001": {
        "extraction_status": EXTRACTION_STATUS_TEXT_EXTRACTED,
        "page_count": 2,
        "char_count": 4636,
        "missing_fields": [
            "broker_name",
            "load_number",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "rate",
            "weight",
        ],
        "needs_check_fields": [],
        "conflict_fields": [],
    },
    "RATECON_002": {
        "extraction_status": EXTRACTION_STATUS_EMPTY_TEXT,
        "page_count": 2,
        "char_count": 0,
        "missing_fields": [],
        "needs_check_fields": [],
        "conflict_fields": [],
    },
    "RATECON_003": {
        "extraction_status": EXTRACTION_STATUS_TEXT_EXTRACTED,
        "page_count": 3,
        "char_count": 10694,
        "missing_fields": [
            "broker_name",
            "load_number",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "weight",
        ],
        "needs_check_fields": ["rate", "special_requirements"],
        "conflict_fields": [],
    },
}


def _count_by_key(rows, key):
    return dict(
        sorted(
            Counter(str(row.get(key) or "").strip() for row in rows if str(row.get(key) or "").strip()).items()
        )
    )


def _count_list_values(rows, key):
    counter = Counter()
    for row in rows:
        counter.update(
            str(item or "").strip()
            for item in row.get(key, [])
            if str(item or "").strip()
        )
    return dict(sorted(counter.items()))


def _field_status_counts(rows):
    counts = {}

    for row in rows:
        for field_status in row.get("field_statuses", []):
            if not isinstance(field_status, dict):
                continue

            field_name = str(field_status.get("field_name") or "").strip()
            status = str(field_status.get("status") or "").strip()
            if not field_name or not status:
                continue

            counts.setdefault(field_name, Counter())
            counts[field_name][status] += 1

    return {
        field_name: dict(sorted(counter.items()))
        for field_name, counter in sorted(counts.items())
    }


def _critical_missing_counts(rows):
    counter = Counter()
    critical = set(CRITICAL_MEASUREMENT_FIELDS)

    for row in rows:
        counter.update(
            field_name
            for field_name in row.get("missing_fields", [])
            if field_name in critical
        )

    return dict(sorted(counter.items()))


def _sum_mapping_values(rows, key):
    counter = Counter()
    for row in rows:
        value = row.get(key, {})
        if not isinstance(value, dict):
            continue
        for item, count in value.items():
            text = str(item or "").strip()
            if text:
                counter[text] += int(count or 0)
    return dict(sorted(counter.items()))


def _sum_nested_status_counts(rows, key):
    totals = {}
    for row in rows:
        value = row.get(key, {})
        if not isinstance(value, dict):
            continue
        for field_name, status_counts in value.items():
            field = str(field_name or "").strip()
            if not field or not isinstance(status_counts, dict):
                continue
            totals.setdefault(field, Counter())
            for status, count in status_counts.items():
                normalized_status = str(status or "").strip()
                if normalized_status:
                    totals[field][normalized_status] += int(count or 0)

    return {
        field_name: dict(sorted(counter.items()))
        for field_name, counter in sorted(totals.items())
    }


def _eligible_rows(rows):
    return [
        row
        for row in rows
        if row.get("ratecon_eligible")
    ]


def _extraction_relevant_rows(rows):
    return [
        row
        for row in rows
        if row.get("extraction_relevant") or row.get("ratecon_eligible")
    ]


def _normal_load_movement_rows(rows):
    return [
        row
        for row in rows
        if (
            row.get("normal_load_movement")
            or (
                row.get("ratecon_eligible")
                and row.get("document_type") != DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED
            )
        )
    ]


def _layout_status_counts(rows):
    return _count_by_key(
        [
            row
            for row in rows
            if str(row.get("layout_provider_status") or "").strip()
        ],
        "layout_provider_status",
    )


def _layout_attempted_count(rows):
    skipped_prefix = "skipped"
    return sum(
        1
        for row in rows
        if str(row.get("layout_provider_status") or "").strip()
        and not str(row.get("layout_provider_status") or "").startswith(skipped_prefix)
    )


def build_private_ratecon_measurement_aggregate(rows):
    safe_rows = [
        row
        for row in rows or []
        if isinstance(row, dict)
    ]

    extraction_status_counts = _count_by_key(safe_rows, "extraction_status")
    eligible_rows = _eligible_rows(safe_rows)
    extraction_relevant_rows = _extraction_relevant_rows(safe_rows)
    normal_load_rows = _normal_load_movement_rows(safe_rows)
    layout_provider_status_counts = _layout_status_counts(safe_rows)

    return build_aggregate_contract(
        document_count=len(safe_rows),
        total_documents=len(safe_rows),
        triage_route_counts=_count_by_key(safe_rows, "triage_route"),
        extraction_status_counts=extraction_status_counts,
        template_status_counts=_count_by_key(safe_rows, "template_status"),
        field_status_counts_by_field=_field_status_counts(safe_rows),
        blocker_category_counts=_count_list_values(safe_rows, "blocker_categories"),
        review_required_count=sum(1 for row in safe_rows if row.get("review_required")),
        empty_text_count=extraction_status_counts.get(EXTRACTION_STATUS_EMPTY_TEXT, 0),
        text_extracted_count=extraction_status_counts.get(EXTRACTION_STATUS_TEXT_EXTRACTED, 0),
        critical_field_missing_counts=_critical_missing_counts(safe_rows),
        conflict_counts_by_field=_count_list_values(safe_rows, "conflict_fields"),
        needs_check_counts_by_field=_count_list_values(safe_rows, "needs_check_fields"),
        unresolved_counts_by_field=_count_list_values(safe_rows, "unresolved_fields"),
        low_confidence_counts_by_field=_count_list_values(safe_rows, "low_confidence_fields"),
        non_applicable_counts_by_field=_count_list_values(safe_rows, "non_applicable_fields"),
        skipped_counts_by_field=_count_list_values(safe_rows, "skipped_fields"),
        document_type_counts=_count_by_key(safe_rows, "document_type"),
        ratecon_eligible_count=len(eligible_rows),
        extraction_relevant_count=len(extraction_relevant_rows),
        normal_load_movement_count=len(normal_load_rows),
        tonu_count=sum(
            1
            for row in safe_rows
            if row.get("document_type") == DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED
        ),
        supplemental_only_count=sum(1 for row in safe_rows if row.get("supplemental_only")),
        non_ratecon_count=sum(
            1
            for row in safe_rows
            if not row.get("ratecon_eligible") and not row.get("supplemental_only")
        ),
        unknown_review_required_count=sum(
            1
            for row in safe_rows
            if row.get("classification_status") == CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED
        ),
        ocr_needed_count=extraction_status_counts.get(EXTRACTION_STATUS_EMPTY_TEXT, 0),
        classification_status_counts=_count_by_key(safe_rows, "classification_status"),
        page_role_counts=_sum_mapping_values(safe_rows, "page_role_counts"),
        section_role_counts=_sum_mapping_values(safe_rows, "section_role_counts"),
        extraction_scope_counts=_sum_mapping_values(safe_rows, "extraction_scope_counts"),
        layout_provider_status_counts=layout_provider_status_counts,
        layout_attempted_count=_layout_attempted_count(safe_rows),
        layout_success_count=layout_provider_status_counts.get("success", 0),
        layout_skipped_count=sum(
            count
            for status, count in layout_provider_status_counts.items()
            if str(status).startswith("skipped")
        ),
        layout_failed_count=sum(
            count
            for status, count in layout_provider_status_counts.items()
            if status
            not in {
                "success",
                "skipped_non_digital",
                "skipped_not_extraction_relevant",
                "skipped_not_normal_load_movement",
            }
        ),
        layout_quality_bucket_counts=_count_by_key(safe_rows, "layout_quality_bucket"),
        layout_likely_issue_bucket_counts=_count_by_key(safe_rows, "layout_likely_issue_bucket"),
        layout_total_word_count=sum(int(row.get("layout_total_word_count", 0) or 0) for row in safe_rows),
        layout_total_line_count=sum(int(row.get("layout_total_line_count", 0) or 0) for row in safe_rows),
        layout_total_table_count=sum(int(row.get("layout_total_table_count", 0) or 0) for row in safe_rows),
        layout_total_table_cell_count=sum(int(row.get("layout_total_table_cell_count", 0) or 0) for row in safe_rows),
        layout_stop_signal_counts=_sum_mapping_values(safe_rows, "layout_stop_signal_counts"),
        fusion_attempted_count=sum(1 for row in safe_rows if row.get("fusion_attempted")),
        fusion_improved_counts_by_field=_count_list_values(safe_rows, "fusion_improved_fields"),
        fusion_worsened_counts_by_field=_count_list_values(safe_rows, "fusion_worsened_fields"),
        fusion_unchanged_counts_by_field=_count_list_values(safe_rows, "fusion_unchanged_fields"),
        fusion_conflict_counts_by_field=_count_list_values(safe_rows, "fusion_conflict_fields"),
        prevented_regression_counts_by_field=_count_list_values(safe_rows, "prevented_regression_fields"),
        prevented_regression_count=sum(len(row.get("prevented_regression_fields", []) or []) for row in safe_rows),
        stop_group_count_total=sum(int(row.get("stop_group_count", 0) or 0) for row in safe_rows),
        raw_stop_group_count_total=sum(int(row.get("raw_stop_group_count", 0) or 0) for row in safe_rows),
        normalized_stop_count_total=sum(int(row.get("normalized_stop_count", 0) or 0) for row in safe_rows),
        pickup_count_total=sum(int(row.get("pickup_count", 0) or 0) for row in safe_rows),
        delivery_count_total=sum(int(row.get("delivery_count", 0) or 0) for row in safe_rows),
        unknown_stop_count_total=sum(int(row.get("unknown_stop_count", 0) or 0) for row in safe_rows),
        stop_review_required_count_total=sum(
            int(row.get("stop_review_required_count", 0) or 0) for row in safe_rows
        ),
        stop_group_quality_bucket_counts=_count_by_key(safe_rows, "stop_group_quality_bucket"),
        stop_noise_removed_count_total=sum(
            int(row.get("stop_noise_removed_count", 0) or 0) for row in safe_rows
        ),
        stop_duplicate_removed_count_total=sum(
            int(row.get("stop_duplicate_removed_count", 0) or 0) for row in safe_rows
        ),
        stop_field_status_counts=_sum_nested_status_counts(safe_rows, "stop_field_status_counts"),
        normalized_stop_improved_counts_by_field=_count_list_values(
            safe_rows, "normalized_stop_improved_fields"
        ),
        normalized_stop_conflict_counts_by_field=_count_list_values(
            safe_rows, "normalized_stop_conflict_fields"
        ),
        normalized_stop_missing_counts_by_field=_count_list_values(
            safe_rows, "normalized_stop_missing_fields"
        ),
        eligible_critical_field_missing_counts=_critical_missing_counts(eligible_rows),
        eligible_critical_field_denominator=len(eligible_rows),
        normal_load_critical_field_missing_counts=_critical_missing_counts(normal_load_rows),
        normal_load_critical_field_denominator=len(normal_load_rows),
    )


def _status_score(record):
    return sum(
        len(record.get(key, []) or [])
        for key in ["missing_fields", "needs_check_fields", "conflict_fields"]
    )


def _status_change(current_row, baseline):
    current_status = current_row.get("extraction_status", "")
    baseline_status = baseline.get("extraction_status", "")

    if baseline_status == EXTRACTION_STATUS_EMPTY_TEXT:
        if current_status == EXTRACTION_STATUS_EMPTY_TEXT:
            return "unchanged"
        if current_status == EXTRACTION_STATUS_TEXT_EXTRACTED:
            return "improved"
        return "unknown"

    current_score = _status_score(current_row)
    baseline_score = _status_score(baseline)

    if current_score < baseline_score:
        return "improved"
    if current_score > baseline_score:
        return "worsened"
    return "unchanged"


def _compare_rows_to_baseline(rows, baseline):
    comparisons = []
    baseline_by_alias = baseline or KNOWN_PRIVATE_RATECON_BASELINE

    for row in rows:
        alias = str(row.get("document_alias") or "").strip()
        if alias not in baseline_by_alias:
            continue

        baseline_record = baseline_by_alias[alias]
        comparisons.append(
            {
                "document_alias": alias,
                "baseline_matched": True,
                "extraction_status_before": baseline_record.get("extraction_status", ""),
                "extraction_status_after": row.get("extraction_status", ""),
                "field_status_change": _status_change(row, baseline_record),
                "missing_fields_before_count": len(baseline_record.get("missing_fields", [])),
                "missing_fields_after_count": len(row.get("missing_fields", [])),
                "needs_check_fields_before_count": len(baseline_record.get("needs_check_fields", [])),
                "needs_check_fields_after_count": len(row.get("needs_check_fields", [])),
                "conflict_fields_before_count": len(baseline_record.get("conflict_fields", [])),
                "conflict_fields_after_count": len(row.get("conflict_fields", [])),
                "comparison_uses_private_values": False,
            }
        )

    return {
        "baseline_compared": bool(comparisons),
        "alias_comparisons": comparisons,
        "comparison_uses_private_values": False,
    }


def _compare_aggregate_to_baseline(aggregate, optional_known_baseline=None):
    baseline = optional_known_baseline or {}
    baseline_empty_text = int(baseline.get("empty_text_count", 0) or 0)
    baseline_text_extracted = int(baseline.get("text_extracted_count", 0) or 0)

    return {
        "baseline_compared": bool(baseline),
        "empty_text_count_delta": int(aggregate.get("empty_text_count", 0) or 0) - baseline_empty_text,
        "text_extracted_count_delta": int(aggregate.get("text_extracted_count", 0) or 0) - baseline_text_extracted,
        "comparison_uses_private_values": False,
    }


def compare_private_measurement_to_known_baseline(
    measurement,
    optional_known_baseline=None,
):
    if isinstance(measurement, list):
        return _compare_rows_to_baseline(measurement, optional_known_baseline)

    return _compare_aggregate_to_baseline(measurement or {}, optional_known_baseline)
