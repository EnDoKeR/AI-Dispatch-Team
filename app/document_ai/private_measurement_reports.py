"""Aggregate safe private RateCon measurement rows."""

from collections import Counter

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


def build_private_ratecon_measurement_aggregate(rows):
    safe_rows = [
        row
        for row in rows or []
        if isinstance(row, dict)
    ]

    extraction_status_counts = _count_by_key(safe_rows, "extraction_status")

    return build_aggregate_contract(
        document_count=len(safe_rows),
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
    )


def compare_private_measurement_to_known_baseline(
    aggregate,
    optional_known_baseline=None,
):
    baseline = optional_known_baseline or {}
    baseline_empty_text = int(baseline.get("empty_text_count", 0) or 0)
    baseline_text_extracted = int(baseline.get("text_extracted_count", 0) or 0)

    return {
        "baseline_compared": bool(baseline),
        "empty_text_count_delta": int(aggregate.get("empty_text_count", 0) or 0) - baseline_empty_text,
        "text_extracted_count_delta": int(aggregate.get("text_extracted_count", 0) or 0) - baseline_text_extracted,
        "comparison_uses_private_values": False,
    }
