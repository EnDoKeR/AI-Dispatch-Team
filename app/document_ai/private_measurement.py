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
BLOCKER_NON_RATECON_DOCUMENT = "NON_RATECON_DOCUMENT"
BLOCKER_SUPPLEMENTAL_DOCUMENT_ONLY = "SUPPLEMENTAL_DOCUMENT_ONLY"
BLOCKER_UNKNOWN_DOCUMENT_TYPE_REVIEW = "UNKNOWN_DOCUMENT_TYPE_REVIEW"


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
    document_type="UNKNOWN",
    ratecon_eligible=False,
    extraction_relevant=None,
    normal_load_movement=None,
    supplemental_only=False,
    page_role_counts=None,
    section_role_counts=None,
    extraction_scope_counts=None,
    classification_status="unknown_review_required",
    classification_warning_codes=None,
    candidate_counts_by_field=None,
    field_statuses=None,
    missing_fields=None,
    unresolved_fields=None,
    needs_check_fields=None,
    low_confidence_fields=None,
    conflict_fields=None,
    non_applicable_fields=None,
    skipped_fields=None,
    skipped_by_scope=False,
    layout_provider_status="",
    layout_candidate_counts_by_field=None,
    layout_evidence_type_counts=None,
    layout_improved_fields=None,
    layout_worsened_fields=None,
    layout_unchanged_fields=None,
    layout_quality_bucket="",
    layout_total_word_count=0,
    layout_total_line_count=0,
    layout_total_table_count=0,
    layout_total_table_cell_count=0,
    layout_stop_signal_counts=None,
    layout_likely_issue_bucket="",
    layout_table_settings_profile="",
    fusion_enabled=False,
    fusion_attempted=False,
    fusion_improved_fields=None,
    fusion_worsened_fields=None,
    fusion_unchanged_fields=None,
    fusion_conflict_fields=None,
    prevented_regression_fields=None,
    stop_group_count=0,
    raw_stop_group_count=0,
    raw_stop_signal_count=0,
    premerge_stop_group_count=0,
    post_single_line_cluster_stop_group_count=0,
    post_row_merge_stop_group_count=0,
    post_section_merge_stop_group_count=0,
    post_noise_filter_stop_group_count=0,
    post_dedupe_stop_group_count=0,
    post_date_time_attachment_stop_group_count=0,
    normalized_stop_count=0,
    pickup_count=0,
    delivery_count=0,
    generic_stop_count=0,
    unknown_stop_count=0,
    stop_review_required_count=0,
    stop_group_quality_bucket="",
    stop_noise_removed_count=0,
    stop_duplicate_removed_count=0,
    single_line_cluster_merge_count=0,
    table_row_merge_count=0,
    section_context_merge_count=0,
    stop_pipeline_trace=None,
    stop_pattern_counts=None,
    date_candidate_generated_count=0,
    date_candidate_attached_count=0,
    time_candidate_generated_count=0,
    time_candidate_attached_count=0,
    overclassified_stop_count=0,
    ambiguous_stop_count=0,
    duplicate_like_stop_count=0,
    noise_removed_count=0,
    unresolved_due_to_missing_date=0,
    unresolved_due_to_ambiguous_type=0,
    stop_field_status_counts=None,
    normalized_stop_improved_fields=None,
    normalized_stop_conflict_fields=None,
    normalized_stop_missing_fields=None,
    normalized_stop_set=None,
    stop_group_provenance_summary=None,
    stop_span_extractor_enabled=False,
    stop_span_comparison_enabled=False,
    old_raw_stop_groups=0,
    old_normalized_stops=0,
    span_anchor_count=0,
    stop_span_count=0,
    span_normalized_stop_count=0,
    span_pickup_count=0,
    span_delivery_count=0,
    span_generic_stop_count=0,
    span_unknown_count=0,
    span_date_resolved_count=0,
    span_date_missing_count=0,
    span_time_resolved_count=0,
    span_time_missing_count=0,
    span_review_required_count=0,
    span_passthrough_detected=False,
    stop_span_delta=0,
    span_normalized_stop_set=None,
    stop_span_coverage_metrics=None,
    load_identifier_coverage_metrics=None,
    load_identifier_audit_records=None,
    load_identifier_source_line_metrics=None,
    load_identifier_source_line_records=None,
    rate_forensics_records=None,
    rate_conflict_audit_records=None,
    warning_codes=None,
    blocker_categories=None,
    intake_status="",
    review_required=False,
):
    normalized_document_type = _text(document_type) or "UNKNOWN"
    normalized_ratecon_eligible = _bool(ratecon_eligible)
    normalized_extraction_relevant = (
        normalized_ratecon_eligible
        if extraction_relevant is None
        else _bool(extraction_relevant)
    )
    normalized_normal_load_movement = (
        normalized_ratecon_eligible
        and normalized_document_type != "TRUCK_ORDER_NOT_USED"
        if normal_load_movement is None
        else _bool(normal_load_movement)
    )

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
        "document_type": normalized_document_type,
        "ratecon_eligible": normalized_ratecon_eligible,
        "extraction_relevant": normalized_extraction_relevant,
        "normal_load_movement": normalized_normal_load_movement,
        "supplemental_only": _bool(supplemental_only),
        "page_role_counts": _normalize_mapping(page_role_counts),
        "section_role_counts": _normalize_mapping(section_role_counts),
        "extraction_scope_counts": _normalize_mapping(extraction_scope_counts),
        "classification_status": _text(classification_status) or "unknown_review_required",
        "classification_warning_codes": _normalize_list(classification_warning_codes),
        "candidate_counts_by_field": _normalize_mapping(candidate_counts_by_field),
        "field_statuses": [
            status
            for status in field_statuses or []
            if isinstance(status, dict)
        ],
        "missing_fields": _normalize_list(missing_fields),
        "unresolved_fields": _normalize_list(unresolved_fields),
        "needs_check_fields": _normalize_list(needs_check_fields),
        "low_confidence_fields": _normalize_list(low_confidence_fields),
        "conflict_fields": _normalize_list(conflict_fields),
        "non_applicable_fields": _normalize_list(non_applicable_fields),
        "skipped_fields": _normalize_list(skipped_fields),
        "skipped_by_scope": _bool(skipped_by_scope),
        "layout_provider_status": _text(layout_provider_status),
        "layout_candidate_counts_by_field": _normalize_mapping(layout_candidate_counts_by_field),
        "layout_evidence_type_counts": _normalize_mapping(layout_evidence_type_counts),
        "layout_improved_fields": _normalize_list(layout_improved_fields),
        "layout_worsened_fields": _normalize_list(layout_worsened_fields),
        "layout_unchanged_fields": _normalize_list(layout_unchanged_fields),
        "layout_quality_bucket": _text(layout_quality_bucket),
        "layout_total_word_count": int(layout_total_word_count or 0),
        "layout_total_line_count": int(layout_total_line_count or 0),
        "layout_total_table_count": int(layout_total_table_count or 0),
        "layout_total_table_cell_count": int(layout_total_table_cell_count or 0),
        "layout_stop_signal_counts": _normalize_mapping(layout_stop_signal_counts),
        "layout_likely_issue_bucket": _text(layout_likely_issue_bucket),
        "layout_table_settings_profile": _text(layout_table_settings_profile),
        "fusion_enabled": _bool(fusion_enabled),
        "fusion_attempted": _bool(fusion_attempted),
        "fusion_improved_fields": _normalize_list(fusion_improved_fields),
        "fusion_worsened_fields": _normalize_list(fusion_worsened_fields),
        "fusion_unchanged_fields": _normalize_list(fusion_unchanged_fields),
        "fusion_conflict_fields": _normalize_list(fusion_conflict_fields),
        "prevented_regression_fields": _normalize_list(prevented_regression_fields),
        "stop_group_count": int(stop_group_count or 0),
        "raw_stop_group_count": int(raw_stop_group_count or 0),
        "raw_stop_signal_count": int(raw_stop_signal_count or 0),
        "premerge_stop_group_count": int(premerge_stop_group_count or 0),
        "post_single_line_cluster_stop_group_count": int(
            post_single_line_cluster_stop_group_count or 0
        ),
        "post_row_merge_stop_group_count": int(post_row_merge_stop_group_count or 0),
        "post_section_merge_stop_group_count": int(post_section_merge_stop_group_count or 0),
        "post_noise_filter_stop_group_count": int(post_noise_filter_stop_group_count or 0),
        "post_dedupe_stop_group_count": int(post_dedupe_stop_group_count or 0),
        "post_date_time_attachment_stop_group_count": int(
            post_date_time_attachment_stop_group_count or 0
        ),
        "normalized_stop_count": int(normalized_stop_count or 0),
        "pickup_count": int(pickup_count or 0),
        "delivery_count": int(delivery_count or 0),
        "generic_stop_count": int(generic_stop_count or 0),
        "unknown_stop_count": int(unknown_stop_count or 0),
        "stop_review_required_count": int(stop_review_required_count or 0),
        "stop_group_quality_bucket": _text(stop_group_quality_bucket),
        "stop_noise_removed_count": int(stop_noise_removed_count or 0),
        "stop_duplicate_removed_count": int(stop_duplicate_removed_count or 0),
        "single_line_cluster_merge_count": int(single_line_cluster_merge_count or 0),
        "table_row_merge_count": int(table_row_merge_count or 0),
        "section_context_merge_count": int(section_context_merge_count or 0),
        "stop_pattern_counts": _normalize_mapping(stop_pattern_counts),
        "date_candidate_generated_count": int(date_candidate_generated_count or 0),
        "date_candidate_attached_count": int(date_candidate_attached_count or 0),
        "time_candidate_generated_count": int(time_candidate_generated_count or 0),
        "time_candidate_attached_count": int(time_candidate_attached_count or 0),
        "overclassified_stop_count": int(overclassified_stop_count or 0),
        "ambiguous_stop_count": int(ambiguous_stop_count or 0),
        "duplicate_like_stop_count": int(duplicate_like_stop_count or 0),
        "noise_removed_count": int(noise_removed_count or 0),
        "unresolved_due_to_missing_date": int(unresolved_due_to_missing_date or 0),
        "unresolved_due_to_ambiguous_type": int(unresolved_due_to_ambiguous_type or 0),
        "stop_field_status_counts": _normalize_mapping(stop_field_status_counts),
        "normalized_stop_improved_fields": _normalize_list(normalized_stop_improved_fields),
        "normalized_stop_conflict_fields": _normalize_list(normalized_stop_conflict_fields),
        "normalized_stop_missing_fields": _normalize_list(normalized_stop_missing_fields),
        "normalized_stop_set": normalized_stop_set if isinstance(normalized_stop_set, dict) else {},
        "stop_group_provenance_summary": _normalize_mapping(stop_group_provenance_summary),
        "stop_pipeline_trace": stop_pipeline_trace if isinstance(stop_pipeline_trace, dict) else {},
        "stop_span_extractor_enabled": _bool(stop_span_extractor_enabled),
        "stop_span_comparison_enabled": _bool(stop_span_comparison_enabled),
        "old_raw_stop_groups": int(old_raw_stop_groups or 0),
        "old_normalized_stops": int(old_normalized_stops or 0),
        "span_anchor_count": int(span_anchor_count or 0),
        "stop_span_count": int(stop_span_count or 0),
        "span_normalized_stop_count": int(span_normalized_stop_count or 0),
        "span_pickup_count": int(span_pickup_count or 0),
        "span_delivery_count": int(span_delivery_count or 0),
        "span_generic_stop_count": int(span_generic_stop_count or 0),
        "span_unknown_count": int(span_unknown_count or 0),
        "span_date_resolved_count": int(span_date_resolved_count or 0),
        "span_date_missing_count": int(span_date_missing_count or 0),
        "span_time_resolved_count": int(span_time_resolved_count or 0),
        "span_time_missing_count": int(span_time_missing_count or 0),
        "span_review_required_count": int(span_review_required_count or 0),
        "span_passthrough_detected": _bool(span_passthrough_detected),
        "stop_span_delta": int(stop_span_delta or 0),
        "span_normalized_stop_set": (
            span_normalized_stop_set
            if isinstance(span_normalized_stop_set, dict)
            else {}
        ),
        "stop_span_coverage_metrics": (
            stop_span_coverage_metrics
            if isinstance(stop_span_coverage_metrics, dict)
            else {}
        ),
        "load_identifier_coverage_metrics": (
            load_identifier_coverage_metrics
            if isinstance(load_identifier_coverage_metrics, dict)
            else {}
        ),
        "load_identifier_audit_records": [
            record
            for record in load_identifier_audit_records or []
            if isinstance(record, dict)
        ],
        "load_identifier_source_line_metrics": (
            load_identifier_source_line_metrics
            if isinstance(load_identifier_source_line_metrics, dict)
            else {}
        ),
        "load_identifier_source_line_records": [
            record
            for record in load_identifier_source_line_records or []
            if isinstance(record, dict)
        ],
        "rate_forensics_records": [
            record
            for record in rate_forensics_records or []
            if isinstance(record, dict)
        ],
        "rate_conflict_audit_records": [
            record
            for record in rate_conflict_audit_records or []
            if isinstance(record, dict)
        ],
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
    total_documents=0,
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
    unresolved_counts_by_field=None,
    low_confidence_counts_by_field=None,
    non_applicable_counts_by_field=None,
    skipped_counts_by_field=None,
    document_type_counts=None,
    ratecon_eligible_count=0,
    extraction_relevant_count=0,
    normal_load_movement_count=0,
    tonu_count=0,
    supplemental_only_count=0,
    non_ratecon_count=0,
    unknown_review_required_count=0,
    ocr_needed_count=0,
    classification_status_counts=None,
    page_role_counts=None,
    section_role_counts=None,
    extraction_scope_counts=None,
    layout_provider_status_counts=None,
    layout_attempted_count=0,
    layout_success_count=0,
    layout_skipped_count=0,
    layout_failed_count=0,
    layout_quality_bucket_counts=None,
    layout_likely_issue_bucket_counts=None,
    layout_total_word_count=0,
    layout_total_line_count=0,
    layout_total_table_count=0,
    layout_total_table_cell_count=0,
    layout_stop_signal_counts=None,
    fusion_attempted_count=0,
    fusion_improved_counts_by_field=None,
    fusion_worsened_counts_by_field=None,
    fusion_unchanged_counts_by_field=None,
    fusion_conflict_counts_by_field=None,
    prevented_regression_counts_by_field=None,
    prevented_regression_count=0,
    stop_group_count_total=0,
    raw_stop_group_count_total=0,
    raw_stop_signal_count_total=0,
    premerge_stop_group_count_total=0,
    post_single_line_cluster_stop_group_count_total=0,
    post_row_merge_stop_group_count_total=0,
    post_section_merge_stop_group_count_total=0,
    post_noise_filter_stop_group_count_total=0,
    post_dedupe_stop_group_count_total=0,
    post_date_time_attachment_stop_group_count_total=0,
    normalized_stop_count_total=0,
    pickup_count_total=0,
    delivery_count_total=0,
    generic_stop_count_total=0,
    unknown_stop_count_total=0,
    stop_review_required_count_total=0,
    stop_group_quality_bucket_counts=None,
    stop_noise_removed_count_total=0,
    stop_duplicate_removed_count_total=0,
    single_line_cluster_merge_count_total=0,
    table_row_merge_count_total=0,
    section_context_merge_count_total=0,
    stop_pipeline_passthrough_count=0,
    stop_pipeline_first_changed_stage_counts=None,
    stop_pattern_counts=None,
    date_candidate_generated_count_total=0,
    date_candidate_attached_count_total=0,
    time_candidate_generated_count_total=0,
    time_candidate_attached_count_total=0,
    overclassified_stop_count_total=0,
    ambiguous_stop_count_total=0,
    duplicate_like_stop_count_total=0,
    noise_removed_count_total=0,
    unresolved_due_to_missing_date_total=0,
    unresolved_due_to_ambiguous_type_total=0,
    stop_field_status_counts=None,
    normalized_stop_improved_counts_by_field=None,
    normalized_stop_conflict_counts_by_field=None,
    normalized_stop_missing_counts_by_field=None,
    stop_span_extractor_attempted_count=0,
    span_anchor_count_total=0,
    stop_span_count_total=0,
    span_normalized_stop_count_total=0,
    span_pickup_count_total=0,
    span_delivery_count_total=0,
    span_generic_stop_count_total=0,
    span_unknown_count_total=0,
    span_date_resolved_count_total=0,
    span_date_missing_count_total=0,
    span_time_resolved_count_total=0,
    span_time_missing_count_total=0,
    span_review_required_count_total=0,
    span_passthrough_count=0,
    eligible_critical_field_missing_counts=None,
    eligible_critical_field_denominator=0,
    normal_load_critical_field_missing_counts=None,
    normal_load_critical_field_denominator=0,
    generated_at="",
    measurement_version=MEASUREMENT_VERSION,
):
    normalized_document_count = int(document_count or 0)
    normalized_total_documents = int(total_documents or normalized_document_count or 0)
    return {
        "document_count": normalized_document_count,
        "total_documents": normalized_total_documents,
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
        "unresolved_counts_by_field": _normalize_mapping(unresolved_counts_by_field),
        "low_confidence_counts_by_field": _normalize_mapping(low_confidence_counts_by_field),
        "non_applicable_counts_by_field": _normalize_mapping(non_applicable_counts_by_field),
        "skipped_counts_by_field": _normalize_mapping(skipped_counts_by_field),
        "document_type_counts": _normalize_mapping(document_type_counts),
        "ratecon_eligible_count": int(ratecon_eligible_count or 0),
        "extraction_relevant_count": int(extraction_relevant_count or 0),
        "normal_load_movement_count": int(normal_load_movement_count or 0),
        "tonu_count": int(tonu_count or 0),
        "supplemental_only_count": int(supplemental_only_count or 0),
        "non_ratecon_count": int(non_ratecon_count or 0),
        "unknown_review_required_count": int(unknown_review_required_count or 0),
        "ocr_needed_count": int(ocr_needed_count or 0),
        "classification_status_counts": _normalize_mapping(classification_status_counts),
        "page_role_counts": _normalize_mapping(page_role_counts),
        "section_role_counts": _normalize_mapping(section_role_counts),
        "extraction_scope_counts": _normalize_mapping(extraction_scope_counts),
        "layout_provider_status_counts": _normalize_mapping(layout_provider_status_counts),
        "layout_attempted_count": int(layout_attempted_count or 0),
        "layout_success_count": int(layout_success_count or 0),
        "layout_skipped_count": int(layout_skipped_count or 0),
        "layout_failed_count": int(layout_failed_count or 0),
        "layout_quality_bucket_counts": _normalize_mapping(layout_quality_bucket_counts),
        "layout_likely_issue_bucket_counts": _normalize_mapping(layout_likely_issue_bucket_counts),
        "layout_total_word_count": int(layout_total_word_count or 0),
        "layout_total_line_count": int(layout_total_line_count or 0),
        "layout_total_table_count": int(layout_total_table_count or 0),
        "layout_total_table_cell_count": int(layout_total_table_cell_count or 0),
        "layout_stop_signal_counts": _normalize_mapping(layout_stop_signal_counts),
        "fusion_attempted_count": int(fusion_attempted_count or 0),
        "fusion_improved_counts_by_field": _normalize_mapping(
            fusion_improved_counts_by_field
        ),
        "fusion_worsened_counts_by_field": _normalize_mapping(
            fusion_worsened_counts_by_field
        ),
        "fusion_unchanged_counts_by_field": _normalize_mapping(
            fusion_unchanged_counts_by_field
        ),
        "fusion_conflict_counts_by_field": _normalize_mapping(
            fusion_conflict_counts_by_field
        ),
        "prevented_regression_counts_by_field": _normalize_mapping(
            prevented_regression_counts_by_field
        ),
        "prevented_regression_count": int(prevented_regression_count or 0),
        "stop_group_count_total": int(stop_group_count_total or 0),
        "raw_stop_group_count_total": int(raw_stop_group_count_total or 0),
        "raw_stop_signal_count_total": int(raw_stop_signal_count_total or 0),
        "premerge_stop_group_count_total": int(premerge_stop_group_count_total or 0),
        "post_single_line_cluster_stop_group_count_total": int(
            post_single_line_cluster_stop_group_count_total or 0
        ),
        "post_row_merge_stop_group_count_total": int(
            post_row_merge_stop_group_count_total or 0
        ),
        "post_section_merge_stop_group_count_total": int(
            post_section_merge_stop_group_count_total or 0
        ),
        "post_noise_filter_stop_group_count_total": int(
            post_noise_filter_stop_group_count_total or 0
        ),
        "post_dedupe_stop_group_count_total": int(
            post_dedupe_stop_group_count_total or 0
        ),
        "post_date_time_attachment_stop_group_count_total": int(
            post_date_time_attachment_stop_group_count_total or 0
        ),
        "normalized_stop_count_total": int(normalized_stop_count_total or 0),
        "pickup_count_total": int(pickup_count_total or 0),
        "delivery_count_total": int(delivery_count_total or 0),
        "generic_stop_count_total": int(generic_stop_count_total or 0),
        "unknown_stop_count_total": int(unknown_stop_count_total or 0),
        "stop_review_required_count_total": int(stop_review_required_count_total or 0),
        "stop_group_quality_bucket_counts": _normalize_mapping(stop_group_quality_bucket_counts),
        "stop_noise_removed_count_total": int(stop_noise_removed_count_total or 0),
        "stop_duplicate_removed_count_total": int(stop_duplicate_removed_count_total or 0),
        "single_line_cluster_merge_count_total": int(single_line_cluster_merge_count_total or 0),
        "table_row_merge_count_total": int(table_row_merge_count_total or 0),
        "section_context_merge_count_total": int(section_context_merge_count_total or 0),
        "stop_pipeline_passthrough_count": int(stop_pipeline_passthrough_count or 0),
        "stop_pipeline_first_changed_stage_counts": _normalize_mapping(
            stop_pipeline_first_changed_stage_counts
        ),
        "stop_pattern_counts": _normalize_mapping(stop_pattern_counts),
        "date_candidate_generated_count_total": int(date_candidate_generated_count_total or 0),
        "date_candidate_attached_count_total": int(date_candidate_attached_count_total or 0),
        "time_candidate_generated_count_total": int(time_candidate_generated_count_total or 0),
        "time_candidate_attached_count_total": int(time_candidate_attached_count_total or 0),
        "overclassified_stop_count_total": int(overclassified_stop_count_total or 0),
        "ambiguous_stop_count_total": int(ambiguous_stop_count_total or 0),
        "duplicate_like_stop_count_total": int(duplicate_like_stop_count_total or 0),
        "noise_removed_count_total": int(noise_removed_count_total or 0),
        "unresolved_due_to_missing_date_total": int(unresolved_due_to_missing_date_total or 0),
        "unresolved_due_to_ambiguous_type_total": int(unresolved_due_to_ambiguous_type_total or 0),
        "stop_field_status_counts": _normalize_mapping(stop_field_status_counts),
        "normalized_stop_improved_counts_by_field": _normalize_mapping(
            normalized_stop_improved_counts_by_field
        ),
        "normalized_stop_conflict_counts_by_field": _normalize_mapping(
            normalized_stop_conflict_counts_by_field
        ),
        "normalized_stop_missing_counts_by_field": _normalize_mapping(
            normalized_stop_missing_counts_by_field
        ),
        "stop_span_extractor_attempted_count": int(
            stop_span_extractor_attempted_count or 0
        ),
        "span_anchor_count_total": int(span_anchor_count_total or 0),
        "stop_span_count_total": int(stop_span_count_total or 0),
        "span_normalized_stop_count_total": int(
            span_normalized_stop_count_total or 0
        ),
        "span_pickup_count_total": int(span_pickup_count_total or 0),
        "span_delivery_count_total": int(span_delivery_count_total or 0),
        "span_generic_stop_count_total": int(span_generic_stop_count_total or 0),
        "span_unknown_count_total": int(span_unknown_count_total or 0),
        "span_date_resolved_count_total": int(span_date_resolved_count_total or 0),
        "span_date_missing_count_total": int(span_date_missing_count_total or 0),
        "span_time_resolved_count_total": int(span_time_resolved_count_total or 0),
        "span_time_missing_count_total": int(span_time_missing_count_total or 0),
        "span_review_required_count_total": int(span_review_required_count_total or 0),
        "span_passthrough_count": int(span_passthrough_count or 0),
        "eligible_critical_field_missing_counts": _normalize_mapping(
            eligible_critical_field_missing_counts
        ),
        "eligible_critical_field_denominator": int(eligible_critical_field_denominator or 0),
        "normal_load_critical_field_missing_counts": _normalize_mapping(
            normal_load_critical_field_missing_counts
        ),
        "normal_load_critical_field_denominator": int(
            normal_load_critical_field_denominator or 0
        ),
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
