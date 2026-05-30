"""Safe pattern classification for normalized stop review packets."""

from collections import Counter, defaultdict
import hashlib


PATTERN_TABLE_CELL_OVER_GROUPING = "TABLE_CELL_OVER_GROUPING"
PATTERN_TABLE_ROW_NOT_MERGED = "TABLE_ROW_NOT_MERGED"
PATTERN_DUPLICATE_STOP_GROUPS = "DUPLICATE_STOP_GROUPS"
PATTERN_HEADER_FOOTER_NOISE = "HEADER_FOOTER_NOISE"
PATTERN_TERMS_BILLING_NOISE = "TERMS_BILLING_NOISE"
PATTERN_DATE_CANDIDATE_NOT_GENERATED = "DATE_CANDIDATE_NOT_GENERATED"
PATTERN_DATE_CANDIDATE_NOT_ATTACHED = "DATE_CANDIDATE_NOT_ATTACHED"
PATTERN_TIME_CANDIDATE_NOT_ATTACHED = "TIME_CANDIDATE_NOT_ATTACHED"
PATTERN_LOCATION_DATE_SPLIT = "LOCATION_DATE_SPLIT"
PATTERN_PICKUP_DELIVERY_OVERCLASSIFIED = "PICKUP_DELIVERY_OVERCLASSIFIED"
PATTERN_SCOPE_FILTER_EXCLUDED_DATE = "SCOPE_FILTER_EXCLUDED_DATE"
PATTERN_UNKNOWN_REVIEW_NEEDED = "UNKNOWN_REVIEW_NEEDED"

STOP_REVIEW_PATTERN_CATEGORIES = {
    PATTERN_TABLE_CELL_OVER_GROUPING,
    PATTERN_TABLE_ROW_NOT_MERGED,
    PATTERN_DUPLICATE_STOP_GROUPS,
    PATTERN_HEADER_FOOTER_NOISE,
    PATTERN_TERMS_BILLING_NOISE,
    PATTERN_DATE_CANDIDATE_NOT_GENERATED,
    PATTERN_DATE_CANDIDATE_NOT_ATTACHED,
    PATTERN_TIME_CANDIDATE_NOT_ATTACHED,
    PATTERN_LOCATION_DATE_SPLIT,
    PATTERN_PICKUP_DELIVERY_OVERCLASSIFIED,
    PATTERN_SCOPE_FILTER_EXCLUDED_DATE,
    PATTERN_UNKNOWN_REVIEW_NEEDED,
}

FIX_BUCKET_STOP_GROUPING = "stop_grouping"
FIX_BUCKET_DEDUPE_NOISE = "dedupe_noise"
FIX_BUCKET_DATE_TIME_ASSOCIATION = "date_time_association"
FIX_BUCKET_SCOPE_FILTER = "scope_filter"
FIX_BUCKET_TYPE_CALIBRATION = "stop_type_calibration"
FIX_BUCKET_REVIEW = "review"

STOP_REVIEW_PATTERN_VERSION = "stop_review_pattern_classifier_v1"


def _text(value):
    return str(value or "").strip()


def _normalize_rows(rows):
    return [row for row in rows or [] if isinstance(row, dict)]


def _group_rows_by_stop(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[_text(row.get("stop_id"))].append(row)
    return {stop_id: stop_rows for stop_id, stop_rows in grouped.items() if stop_id}


def _unique(values):
    return sorted({item for item in values if _text(item)})


def _warning_tokens(rows):
    tokens = set()
    for row in rows:
        for item in _text(row.get("warning_codes")).replace(",", ";").split(";"):
            token = _text(item).lower()
            if token:
                tokens.add(token)
    return tokens


def _safe_value_digest(value):
    text = _text(value)
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _recommendation_for(pattern):
    if pattern in {
        PATTERN_TABLE_CELL_OVER_GROUPING,
        PATTERN_TABLE_ROW_NOT_MERGED,
    }:
        return FIX_BUCKET_STOP_GROUPING
    if pattern in {
        PATTERN_DUPLICATE_STOP_GROUPS,
        PATTERN_HEADER_FOOTER_NOISE,
        PATTERN_TERMS_BILLING_NOISE,
    }:
        return FIX_BUCKET_DEDUPE_NOISE
    if pattern in {
        PATTERN_DATE_CANDIDATE_NOT_GENERATED,
        PATTERN_DATE_CANDIDATE_NOT_ATTACHED,
        PATTERN_TIME_CANDIDATE_NOT_ATTACHED,
        PATTERN_LOCATION_DATE_SPLIT,
    }:
        return FIX_BUCKET_DATE_TIME_ASSOCIATION
    if pattern == PATTERN_SCOPE_FILTER_EXCLUDED_DATE:
        return FIX_BUCKET_SCOPE_FILTER
    if pattern == PATTERN_PICKUP_DELIVERY_OVERCLASSIFIED:
        return FIX_BUCKET_TYPE_CALIBRATION
    return FIX_BUCKET_REVIEW


def build_stop_review_pattern_summary(
    document_alias="",
    rows=None,
    include_private_values_local_only=False,
):
    safe_rows = _normalize_rows(rows)
    rows_by_stop = _group_rows_by_stop(safe_rows)
    stop_count = len(rows_by_stop)
    patterns = Counter()
    affected_fields = set()
    affected_stop_ids = set()
    warnings = set()

    field_status_counts = Counter(
        (_text(row.get("field_name")), _text(row.get("status")))
        for row in safe_rows
        if _text(row.get("field_name"))
    )
    evidence_counts = Counter(_text(row.get("evidence_type")) for row in safe_rows if _text(row.get("evidence_type")))
    type_counts = Counter(
        _text(stop_rows[0].get("stop_type"))
        for stop_rows in rows_by_stop.values()
        if stop_rows
    )
    sequence_counts = Counter(
        (
            _text(stop_rows[0].get("stop_type")),
            _text(stop_rows[0].get("sequence")),
            _text(stop_rows[0].get("page_number")),
        )
        for stop_rows in rows_by_stop.values()
        if stop_rows
    )
    tokens = _warning_tokens(safe_rows)
    warnings.update(tokens)

    location_resolved = field_status_counts.get(("location", "resolved"), 0)
    date_missing = field_status_counts.get(("date", "missing"), 0)
    time_missing = field_status_counts.get(("time", "missing"), 0)
    date_rows = sum(count for (field, _), count in field_status_counts.items() if field == "date")
    table_cell_rows = evidence_counts.get("table_cell", 0)

    if stop_count >= 6 and table_cell_rows >= stop_count:
        patterns[PATTERN_TABLE_CELL_OVER_GROUPING] += 1
        affected_fields.update(["location", "date", "time"])
        affected_stop_ids.update(rows_by_stop.keys())

    duplicate_sequence_groups = sum(1 for count in sequence_counts.values() if count > 1)
    if duplicate_sequence_groups:
        patterns[PATTERN_TABLE_ROW_NOT_MERGED] += duplicate_sequence_groups
        affected_fields.update(["location", "date", "time"])
        affected_stop_ids.update(rows_by_stop.keys())

    if include_private_values_local_only:
        value_to_stop_ids = defaultdict(set)
        for row in safe_rows:
            if _text(row.get("field_name")) != "location":
                continue
            digest = _safe_value_digest(row.get("selected_value_local_only"))
            if digest:
                value_to_stop_ids[digest].add(_text(row.get("stop_id")))
        duplicate_value_groups = [
            stop_ids for stop_ids in value_to_stop_ids.values() if len(stop_ids) > 1
        ]
        if duplicate_value_groups:
            patterns[PATTERN_DUPLICATE_STOP_GROUPS] += len(duplicate_value_groups)
            affected_fields.add("location")
            for stop_ids in duplicate_value_groups:
                affected_stop_ids.update(stop_ids)

    if tokens & {"header", "footer", "repeated_header", "page_footer"}:
        patterns[PATTERN_HEADER_FOOTER_NOISE] += 1
        affected_stop_ids.update(rows_by_stop.keys())

    if any(
        token in tokens
        for token in [
            "terms",
            "billing",
            "quick_pay",
            "payment_terms",
            "stop_group_noise_terms_or_billing",
        ]
    ):
        patterns[PATTERN_TERMS_BILLING_NOISE] += 1
        affected_stop_ids.update(rows_by_stop.keys())

    if stop_count and not date_rows:
        patterns[PATTERN_DATE_CANDIDATE_NOT_GENERATED] += 1
        affected_fields.add("date")
        affected_stop_ids.update(rows_by_stop.keys())
    elif stop_count and date_missing == stop_count:
        patterns[PATTERN_DATE_CANDIDATE_NOT_ATTACHED] += 1
        affected_fields.add("date")
        affected_stop_ids.update(rows_by_stop.keys())

    if stop_count and time_missing >= max(1, stop_count - 1):
        patterns[PATTERN_TIME_CANDIDATE_NOT_ATTACHED] += 1
        affected_fields.add("time")
        affected_stop_ids.update(rows_by_stop.keys())

    if location_resolved and date_missing:
        patterns[PATTERN_LOCATION_DATE_SPLIT] += 1
        affected_fields.update(["location", "date"])
        affected_stop_ids.update(rows_by_stop.keys())

    if stop_count >= 6 and type_counts.get("unknown", 0) == 0:
        patterns[PATTERN_PICKUP_DELIVERY_OVERCLASSIFIED] += 1
        affected_stop_ids.update(rows_by_stop.keys())

    if tokens & {"scope_filter_excluded_pages", "scope_filter_excluded_date"}:
        patterns[PATTERN_SCOPE_FILTER_EXCLUDED_DATE] += 1
        affected_fields.add("date")

    if not patterns and stop_count:
        patterns[PATTERN_UNKNOWN_REVIEW_NEEDED] += 1
        affected_stop_ids.update(rows_by_stop.keys())

    return {
        "document_alias": _text(document_alias),
        "pattern_counts": dict(sorted(patterns.items())),
        "affected_fields": sorted(affected_fields),
        "affected_stop_ids": sorted(affected_stop_ids),
        "warning_codes": sorted(warnings),
        "recommended_fix_buckets": sorted(
            {_recommendation_for(pattern) for pattern in patterns}
        ),
        "row_count": len(safe_rows),
        "stop_count": stop_count,
        "private_values_included": False,
        "raw_text_included": False,
        "pattern_classifier_version": STOP_REVIEW_PATTERN_VERSION,
    }


def classify_stop_review_packet_patterns(rows, include_private_values_local_only=False):
    grouped = defaultdict(list)
    for row in _normalize_rows(rows):
        grouped[_text(row.get("document_alias"))].append(row)
    summaries = [
        build_stop_review_pattern_summary(
            document_alias=alias,
            rows=alias_rows,
            include_private_values_local_only=include_private_values_local_only,
        )
        for alias, alias_rows in sorted(grouped.items())
        if alias
    ]
    aggregate = Counter()
    for summary in summaries:
        aggregate.update(summary.get("pattern_counts", {}))
    return {
        "summaries": summaries,
        "pattern_counts": dict(sorted(aggregate.items())),
        "document_count": len(summaries),
        "private_values_included": False,
        "raw_text_included": False,
        "pattern_classifier_version": STOP_REVIEW_PATTERN_VERSION,
    }

