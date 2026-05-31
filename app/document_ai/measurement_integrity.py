"""Safe count integrity checks for private RateCon measurement outputs."""

from app.document_ai.ratecon_candidates import normalize_list


INTEGRITY_SEVERITY_INFO = "info"
INTEGRITY_SEVERITY_WARNING = "warning"
INTEGRITY_SEVERITY_ERROR = "error"

INTEGRITY_SEVERITIES = {
    INTEGRITY_SEVERITY_INFO,
    INTEGRITY_SEVERITY_WARNING,
    INTEGRITY_SEVERITY_ERROR,
}

ISSUE_STOP_TYPE_COUNT_MISMATCH = "STOP_TYPE_COUNT_MISMATCH"
ISSUE_SPAN_TYPE_COUNT_MISMATCH = "SPAN_TYPE_COUNT_MISMATCH"
ISSUE_REVIEW_COUNT_EXCEEDS_STOP_COUNT = "REVIEW_COUNT_EXCEEDS_STOP_COUNT"
ISSUE_FIELD_STATUS_DENOMINATOR_MISMATCH = "FIELD_STATUS_DENOMINATOR_MISMATCH"
ISSUE_SPAN_FIELD_STATUS_DENOMINATOR_MISMATCH = (
    "SPAN_FIELD_STATUS_DENOMINATOR_MISMATCH"
)
ISSUE_NEGATIVE_COUNT = "NEGATIVE_COUNT"
ISSUE_OCR_DOC_COUNTED_AS_NORMAL_FAILURE = "OCR_DOC_COUNTED_AS_NORMAL_FAILURE"

MEASUREMENT_INTEGRITY_VERSION = "measurement_integrity_v1"

STOP_STATUS_FIELDS = (
    "resolved",
    "missing",
    "conflict",
    "low_confidence",
    "needs_review",
    "non_applicable",
)


def _text(value):
    return str(value or "").strip()


def _severity(value):
    token = _text(value).lower().replace(" ", "_").replace("-", "_")
    return token if token in INTEGRITY_SEVERITIES else INTEGRITY_SEVERITY_WARNING


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def build_measurement_integrity_issue(
    issue_code="",
    severity=INTEGRITY_SEVERITY_WARNING,
    alias="",
    safe_message="",
    affected_counts=None,
    recommended_fix_bucket="",
):
    return {
        "issue_code": _text(issue_code),
        "severity": _severity(severity),
        "alias": _text(alias),
        "safe_message": _text(safe_message),
        "affected_counts": affected_counts if isinstance(affected_counts, dict) else {},
        "recommended_fix_bucket": _text(recommended_fix_bucket),
        "integrity_version": MEASUREMENT_INTEGRITY_VERSION,
        "raw_text_included": False,
        "private_values_redacted": True,
    }


def _issue(issue_code, alias="", counts=None, severity=INTEGRITY_SEVERITY_WARNING, bucket=""):
    return build_measurement_integrity_issue(
        issue_code=issue_code,
        severity=severity,
        alias=alias,
        safe_message=issue_code.lower(),
        affected_counts=counts or {},
        recommended_fix_bucket=bucket or "measurement_reporting",
    )


def _negative_count_issues(record, alias, keys):
    issues = []
    for key in keys:
        value = _int((record or {}).get(key, 0))
        if value < 0:
            issues.append(
                _issue(
                    ISSUE_NEGATIVE_COUNT,
                    alias=alias,
                    counts={key: value},
                    severity=INTEGRITY_SEVERITY_ERROR,
                    bucket="count_normalization",
                )
            )
    return issues


def _status_count_sum(status_counts):
    if not isinstance(status_counts, dict):
        return 0
    return sum(_int(status_counts.get(status, 0)) for status in STOP_STATUS_FIELDS)


def check_measurement_row_integrity(row):
    alias = _text((row or {}).get("document_alias"))
    issues = []
    count_keys = [
        "normalized_stop_count",
        "pickup_count",
        "delivery_count",
        "generic_stop_count",
        "unknown_stop_count",
        "stop_review_required_count",
        "span_normalized_stop_count",
        "span_pickup_count",
        "span_delivery_count",
        "span_generic_stop_count",
        "span_unknown_count",
        "span_review_required_count",
        "span_date_resolved_count",
        "span_date_missing_count",
        "span_date_conflict_count",
        "span_date_low_confidence_count",
        "span_date_non_applicable_count",
        "span_time_resolved_count",
        "span_time_missing_count",
        "span_time_conflict_count",
        "span_time_low_confidence_count",
        "span_time_non_applicable_count",
    ]
    issues.extend(_negative_count_issues(row, alias, count_keys))

    normalized_count = _int((row or {}).get("normalized_stop_count", 0))
    stop_type_sum = (
        _int((row or {}).get("pickup_count", 0))
        + _int((row or {}).get("delivery_count", 0))
        + _int((row or {}).get("generic_stop_count", 0))
        + _int((row or {}).get("unknown_stop_count", 0))
    )
    if normalized_count and stop_type_sum != normalized_count:
        issues.append(
            _issue(
                ISSUE_STOP_TYPE_COUNT_MISMATCH,
                alias=alias,
                counts={
                    "normalized_stop_count": normalized_count,
                    "stop_type_count_sum": stop_type_sum,
                    "generic_stop_count": _int((row or {}).get("generic_stop_count", 0)),
                },
                bucket="stop_count_reporting",
            )
        )

    span_count = _int((row or {}).get("span_normalized_stop_count", 0))
    span_type_sum = (
        _int((row or {}).get("span_pickup_count", 0))
        + _int((row or {}).get("span_delivery_count", 0))
        + _int((row or {}).get("span_generic_stop_count", 0))
        + _int((row or {}).get("span_unknown_count", 0))
    )
    if span_count and span_type_sum != span_count:
        issues.append(
            _issue(
                ISSUE_SPAN_TYPE_COUNT_MISMATCH,
                alias=alias,
                counts={
                    "span_normalized_stop_count": span_count,
                    "span_type_count_sum": span_type_sum,
                    "span_generic_stop_count": _int(
                        (row or {}).get("span_generic_stop_count", 0)
                    ),
                },
                bucket="span_stop_count_reporting",
            )
        )

    if _int((row or {}).get("stop_review_required_count", 0)) > normalized_count:
        issues.append(
            _issue(
                ISSUE_REVIEW_COUNT_EXCEEDS_STOP_COUNT,
                alias=alias,
                counts={
                    "stop_review_required_count": _int(
                        (row or {}).get("stop_review_required_count", 0)
                    ),
                    "normalized_stop_count": normalized_count,
                },
                bucket="stop_review_reporting",
            )
        )

    if _int((row or {}).get("span_review_required_count", 0)) > span_count:
        issues.append(
            _issue(
                ISSUE_REVIEW_COUNT_EXCEEDS_STOP_COUNT,
                alias=alias,
                counts={
                    "span_review_required_count": _int(
                        (row or {}).get("span_review_required_count", 0)
                    ),
                    "span_normalized_stop_count": span_count,
                },
                bucket="span_stop_review_reporting",
            )
        )

    for field_name in ("date", "time"):
        field_counts = ((row or {}).get("stop_field_status_counts", {}) or {}).get(
            field_name,
            {},
        )
        total = _status_count_sum(field_counts)
        if normalized_count and total and total != normalized_count:
            issues.append(
                _issue(
                    ISSUE_FIELD_STATUS_DENOMINATOR_MISMATCH,
                    alias=alias,
                    counts={
                        "field_name": field_name,
                        "field_status_total": total,
                        "normalized_stop_count": normalized_count,
                    },
                    bucket="stop_field_status_reporting",
                )
            )

    for field_name in ("date", "time"):
        total = (
            _int((row or {}).get(f"span_{field_name}_resolved_count", 0))
            + _int((row or {}).get(f"span_{field_name}_missing_count", 0))
            + _int((row or {}).get(f"span_{field_name}_conflict_count", 0))
            + _int((row or {}).get(f"span_{field_name}_low_confidence_count", 0))
            + _int((row or {}).get(f"span_{field_name}_non_applicable_count", 0))
        )
        if span_count and total and total != span_count:
            issues.append(
                _issue(
                    ISSUE_SPAN_FIELD_STATUS_DENOMINATOR_MISMATCH,
                    alias=alias,
                    counts={
                        "field_name": field_name,
                        "span_field_status_total": total,
                        "span_normalized_stop_count": span_count,
                    },
                    bucket="span_field_status_reporting",
                )
            )

    if (
        (row or {}).get("extraction_status") == "EMPTY_TEXT"
        and (row or {}).get("normal_load_movement")
    ):
        issues.append(
            _issue(
                ISSUE_OCR_DOC_COUNTED_AS_NORMAL_FAILURE,
                alias=alias,
                counts={"normal_load_movement": 1},
                bucket="measurement_denominator",
            )
        )

    return issues


def check_measurement_aggregate_integrity(aggregate):
    issues = []
    issues.extend(
        _negative_count_issues(
            aggregate,
            "",
            [
                "normalized_stop_count_total",
                "pickup_count_total",
                "delivery_count_total",
                "generic_stop_count_total",
                "unknown_stop_count_total",
                "span_normalized_stop_count_total",
                "span_pickup_count_total",
                "span_delivery_count_total",
                "span_generic_stop_count_total",
                "span_unknown_count_total",
                "span_date_resolved_count_total",
                "span_date_missing_count_total",
                "span_date_conflict_count_total",
                "span_date_low_confidence_count_total",
                "span_date_non_applicable_count_total",
                "span_time_resolved_count_total",
                "span_time_missing_count_total",
                "span_time_conflict_count_total",
                "span_time_low_confidence_count_total",
                "span_time_non_applicable_count_total",
            ],
        )
    )

    normalized = _int((aggregate or {}).get("normalized_stop_count_total", 0))
    stop_type_sum = (
        _int((aggregate or {}).get("pickup_count_total", 0))
        + _int((aggregate or {}).get("delivery_count_total", 0))
        + _int((aggregate or {}).get("generic_stop_count_total", 0))
        + _int((aggregate or {}).get("unknown_stop_count_total", 0))
    )
    if normalized and normalized != stop_type_sum:
        issues.append(
            _issue(
                ISSUE_STOP_TYPE_COUNT_MISMATCH,
                counts={
                    "normalized_stop_count_total": normalized,
                    "stop_type_count_sum": stop_type_sum,
                    "generic_stop_count_total": _int(
                        (aggregate or {}).get("generic_stop_count_total", 0)
                    ),
                },
                bucket="stop_count_reporting",
            )
        )

    span_normalized = _int((aggregate or {}).get("span_normalized_stop_count_total", 0))
    span_type_sum = (
        _int((aggregate or {}).get("span_pickup_count_total", 0))
        + _int((aggregate or {}).get("span_delivery_count_total", 0))
        + _int((aggregate or {}).get("span_generic_stop_count_total", 0))
        + _int((aggregate or {}).get("span_unknown_count_total", 0))
    )
    if span_normalized and span_normalized != span_type_sum:
        issues.append(
            _issue(
                ISSUE_SPAN_TYPE_COUNT_MISMATCH,
                counts={
                    "span_normalized_stop_count_total": span_normalized,
                    "span_type_count_sum": span_type_sum,
                    "span_generic_stop_count_total": _int(
                        (aggregate or {}).get("span_generic_stop_count_total", 0)
                    ),
                },
                bucket="span_stop_count_reporting",
            )
        )

    for field_name in ("date", "time"):
        field_counts = ((aggregate or {}).get("stop_field_status_counts", {}) or {}).get(
            field_name,
            {},
        )
        total = _status_count_sum(field_counts)
        if normalized and total and total != normalized:
            issues.append(
                _issue(
                    ISSUE_FIELD_STATUS_DENOMINATOR_MISMATCH,
                    counts={
                        "field_name": field_name,
                        "field_status_total": total,
                        "normalized_stop_count_total": normalized,
                    },
                    bucket="stop_field_status_reporting",
                )
            )

    for field_name in ("date", "time"):
        total = (
            _int((aggregate or {}).get(f"span_{field_name}_resolved_count_total", 0))
            + _int((aggregate or {}).get(f"span_{field_name}_missing_count_total", 0))
            + _int((aggregate or {}).get(f"span_{field_name}_conflict_count_total", 0))
            + _int(
                (aggregate or {}).get(f"span_{field_name}_low_confidence_count_total", 0)
            )
            + _int(
                (aggregate or {}).get(f"span_{field_name}_non_applicable_count_total", 0)
            )
        )
        if span_normalized and total and total != span_normalized:
            issues.append(
                _issue(
                    ISSUE_SPAN_FIELD_STATUS_DENOMINATOR_MISMATCH,
                    counts={
                        "field_name": field_name,
                        "span_field_status_total": total,
                        "span_normalized_stop_count_total": span_normalized,
                    },
                    bucket="span_field_status_reporting",
                )
            )

    return issues


def summarize_integrity_issues(issues):
    counts = {}
    severities = {}
    for issue in issues or []:
        if not isinstance(issue, dict):
            continue
        code = _text(issue.get("issue_code"))
        severity = _text(issue.get("severity"))
        if code:
            counts[code] = counts.get(code, 0) + 1
        if severity:
            severities[severity] = severities.get(severity, 0) + 1
    return {
        "issue_counts": dict(sorted(counts.items())),
        "severity_counts": dict(sorted(severities.items())),
        "issue_count": sum(counts.values()),
        "warning_codes": normalize_list(
            issue.get("issue_code")
            for issue in issues or []
            if isinstance(issue, dict)
        ),
        "raw_text_included": False,
        "private_values_redacted": True,
    }
