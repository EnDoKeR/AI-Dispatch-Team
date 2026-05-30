"""Safe private RateCon measurement contracts.

These helpers build JSON-ready summaries for local private measurement. They do
not store raw text or private field values.
"""

from collections import Counter


MEASUREMENT_VERSION = "private_ratecon_measurement_v1"

FIELD_STATUS_RESOLVED = "resolved"
FIELD_STATUS_MISSING = "missing"
FIELD_STATUS_NEEDS_REVIEW = "needs_review"
FIELD_STATUS_LOW_CONFIDENCE = "low_confidence"
FIELD_STATUS_CONFLICT = "conflict"
FIELD_STATUS_NOT_APPLICABLE = "not_applicable"

FIELD_STATUSES = {
    FIELD_STATUS_RESOLVED,
    FIELD_STATUS_MISSING,
    FIELD_STATUS_NEEDS_REVIEW,
    FIELD_STATUS_LOW_CONFIDENCE,
    FIELD_STATUS_CONFLICT,
    FIELD_STATUS_NOT_APPLICABLE,
}

CONFIDENCE_BUCKET_NONE = "none"
CONFIDENCE_BUCKET_LOW = "low"
CONFIDENCE_BUCKET_MEDIUM = "medium"
CONFIDENCE_BUCKET_HIGH = "high"
CONFIDENCE_BUCKET_UNKNOWN = "unknown"

CONFIDENCE_BUCKETS = {
    CONFIDENCE_BUCKET_NONE,
    CONFIDENCE_BUCKET_LOW,
    CONFIDENCE_BUCKET_MEDIUM,
    CONFIDENCE_BUCKET_HIGH,
    CONFIDENCE_BUCKET_UNKNOWN,
}

EXTRACTION_STATUS_EMPTY_TEXT = "EMPTY_TEXT"
EXTRACTION_STATUS_TEXT_EXTRACTED = "TEXT_EXTRACTED"
EXTRACTION_STATUS_BROKEN_OR_UNSUPPORTED = "BROKEN_OR_UNSUPPORTED"
EXTRACTION_STATUS_TRIAGE_ONLY = "TRIAGE_ONLY"
EXTRACTION_STATUS_EXTRACTION_FAILED = "EXTRACTION_FAILED"

BLOCKER_OCR_NEEDED = "OCR_NEEDED"
BLOCKER_DIGITAL_TEXT_EXTRACTION_GAP = "DIGITAL_TEXT_EXTRACTION_GAP"
BLOCKER_LAYOUT_EXTRACTION_GAP = "LAYOUT_EXTRACTION_GAP"
BLOCKER_TEMPLATE_GAP = "TEMPLATE_GAP"
BLOCKER_RESOLVER_GAP = "RESOLVER_GAP"
BLOCKER_VALIDATION_GAP = "VALIDATION_GAP"
BLOCKER_MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
BLOCKER_UNSUPPORTED_OR_BROKEN_PDF = "UNSUPPORTED_OR_BROKEN_PDF"
BLOCKER_LOW_CONFIDENCE_CRITICAL_FIELD = "LOW_CONFIDENCE_CRITICAL_FIELD"
BLOCKER_CONFLICTING_CRITICAL_FIELD = "CONFLICTING_CRITICAL_FIELD"
BLOCKER_MISSING_CRITICAL_FIELD = "MISSING_CRITICAL_FIELD"
BLOCKER_PARSED_HIGH_CONFIDENCE_CANDIDATE = "PARSED_HIGH_CONFIDENCE_CANDIDATE"


def _text(value):
    return str(value or "").strip()


def _bool(value):
    return bool(value)


def _normalize_list(value):
    if value is None:
        return []

    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]

    return [
        _text(item)
        for item in values
        if _text(item)
    ]


def _normalize_mapping(value):
    if not isinstance(value, dict):
        return {}

    return {
        _text(key): item
        for key, item in value.items()
        if _text(key)
    }


def _normalize_status(value):
    text = _text(value).lower().replace(" ", "_").replace("-", "_")
    if text in FIELD_STATUSES:
        return text
    return FIELD_STATUS_NOT_APPLICABLE


def _normalize_confidence_bucket(value):
    text = _text(value).lower().replace(" ", "_").replace("-", "_")
    if text in CONFIDENCE_BUCKETS:
        return text
    return CONFIDENCE_BUCKET_UNKNOWN


def build_private_document_alias(
    alias="",
    original_index=None,
    file_hash_prefix="",
    filename_included=False,
):
    return {
        "alias": _text(alias),
        "original_index": original_index if original_index is not None else "",
        "file_hash_prefix": _text(file_hash_prefix),
        "filename_included": _bool(filename_included),
    }


def build_field_status_summary(
    field_name="",
    status=FIELD_STATUS_NOT_APPLICABLE,
    confidence_bucket=CONFIDENCE_BUCKET_UNKNOWN,
    candidate_count=0,
    selected_candidate_present=False,
    warning_codes=None,
    safe_reasons=None,
):
    return {
        "field_name": _text(field_name),
        "status": _normalize_status(status),
        "confidence_bucket": _normalize_confidence_bucket(confidence_bucket),
        "candidate_count": int(candidate_count or 0),
        "selected_candidate_present": _bool(selected_candidate_present),
        "warning_codes": _normalize_list(warning_codes),
        "safe_reasons": _normalize_list(safe_reasons),
        "value_redacted": True,
    }


def build_private_ratecon_measurement_row(
    document_alias="",
    page_count=0,
    char_count=0,
    triage_route="",
    extraction_status=EXTRACTION_STATUS_TRIAGE_ONLY,
    has_text_layer=False,
    likely_image_based=False,
    template_status="unknown",
    selected_template_id="",
    template_source="",
    template_confidence_bucket=CONFIDENCE_BUCKET_UNKNOWN,
    candidate_counts_by_field=None,
    field_statuses=None,
    missing_fields=None,
    needs_check_fields=None,
    conflict_fields=None,
    warning_codes=None,
    blocker_categories=None,
    intake_status="",
    review_required=False,
):
    return {
        "document_alias": _text(document_alias),
        "page_count": int(page_count or 0),
        "char_count": int(char_count or 0),
        "triage_route": _text(triage_route),
        "extraction_status": _text(extraction_status),
        "has_text_layer": _bool(has_text_layer),
        "likely_image_based": _bool(likely_image_based),
        "template_status": _text(template_status) or "unknown",
        "selected_template_id": _text(selected_template_id),
        "template_source": _text(template_source),
        "template_confidence_bucket": _normalize_confidence_bucket(template_confidence_bucket),
        "candidate_counts_by_field": _normalize_mapping(candidate_counts_by_field),
        "field_statuses": [
            status
            for status in field_statuses or []
            if isinstance(status, dict)
        ],
        "missing_fields": _normalize_list(missing_fields),
        "needs_check_fields": _normalize_list(needs_check_fields),
        "conflict_fields": _normalize_list(conflict_fields),
        "warning_codes": _normalize_list(warning_codes),
        "blocker_categories": _normalize_list(blocker_categories),
        "intake_status": _text(intake_status),
        "review_required": _bool(review_required),
        "raw_text_saved": False,
        "private_values_redacted": True,
        "measurement_version": MEASUREMENT_VERSION,
    }


def build_private_ratecon_measurement_aggregate(
    document_count=0,
    triage_route_counts=None,
    extraction_status_counts=None,
    template_status_counts=None,
    field_status_counts_by_field=None,
    blocker_category_counts=None,
    review_required_count=0,
    empty_text_count=0,
    text_extracted_count=0,
    critical_field_missing_counts=None,
    conflict_counts_by_field=None,
    needs_check_counts_by_field=None,
    generated_at="",
    measurement_version=MEASUREMENT_VERSION,
):
    return {
        "document_count": int(document_count or 0),
        "triage_route_counts": _normalize_mapping(triage_route_counts),
        "extraction_status_counts": _normalize_mapping(extraction_status_counts),
        "template_status_counts": _normalize_mapping(template_status_counts),
        "field_status_counts_by_field": _normalize_mapping(field_status_counts_by_field),
        "blocker_category_counts": _normalize_mapping(blocker_category_counts),
        "review_required_count": int(review_required_count or 0),
        "empty_text_count": int(empty_text_count or 0),
        "text_extracted_count": int(text_extracted_count or 0),
        "critical_field_missing_counts": _normalize_mapping(critical_field_missing_counts),
        "conflict_counts_by_field": _normalize_mapping(conflict_counts_by_field),
        "needs_check_counts_by_field": _normalize_mapping(needs_check_counts_by_field),
        "generated_at": _text(generated_at),
        "measurement_version": _text(measurement_version or MEASUREMENT_VERSION),
        "raw_text_saved": False,
        "private_values_redacted": True,
    }


def build_safe_measurement_output_policy(
    include_filenames=False,
    include_file_hash_prefix=False,
    include_private_values=False,
    include_raw_text=False,
    output_is_shareable=None,
):
    if include_raw_text:
        raise ValueError("safe measurement output policy cannot include raw text")

    shareable = not any(
        [
            include_filenames,
            include_file_hash_prefix,
            include_private_values,
            include_raw_text,
        ]
    )
    if output_is_shareable is not None:
        requested_shareable = bool(output_is_shareable)
        if requested_shareable and include_private_values:
            raise ValueError("shareable output cannot include private values")
        shareable = requested_shareable and shareable

    return {
        "include_filenames": _bool(include_filenames),
        "include_file_hash_prefix": _bool(include_file_hash_prefix),
        "include_private_values": _bool(include_private_values),
        "include_raw_text": False,
        "output_is_shareable": shareable,
    }


def count_values(values):
    return dict(sorted(Counter(_normalize_list(values)).items()))
