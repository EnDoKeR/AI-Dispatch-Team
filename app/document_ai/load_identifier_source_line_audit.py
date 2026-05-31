"""Safe load identifier source-line forensics.

The source-line audit tracks load identifier evidence as counts and categories
only. It must not include private identifier values, raw line text, filenames,
or local paths.
"""

from collections import Counter, defaultdict


LOAD_ID_SOURCE_STAGE_SOURCE_LINE = "source_line"
LOAD_ID_SOURCE_STAGE_LINE_FEATURE = "line_feature"
LOAD_ID_SOURCE_STAGE_LABEL_DETECTED = "label_detected"
LOAD_ID_SOURCE_STAGE_LABEL_CLASSIFIED = "label_classified"
LOAD_ID_SOURCE_STAGE_CANDIDATE_GENERATED = "candidate_generated"
LOAD_ID_SOURCE_STAGE_PRIMARY_CLASSIFIED = "primary_classified"
LOAD_ID_SOURCE_STAGE_CORE_MAPPED = "core_mapped"
LOAD_ID_SOURCE_STAGE_REVIEW_ROW = "review_row"

LOAD_ID_SOURCE_LINE_STAGES = {
    LOAD_ID_SOURCE_STAGE_SOURCE_LINE,
    LOAD_ID_SOURCE_STAGE_LINE_FEATURE,
    LOAD_ID_SOURCE_STAGE_LABEL_DETECTED,
    LOAD_ID_SOURCE_STAGE_LABEL_CLASSIFIED,
    LOAD_ID_SOURCE_STAGE_CANDIDATE_GENERATED,
    LOAD_ID_SOURCE_STAGE_PRIMARY_CLASSIFIED,
    LOAD_ID_SOURCE_STAGE_CORE_MAPPED,
    LOAD_ID_SOURCE_STAGE_REVIEW_ROW,
}

LOAD_ID_SOURCE_REASON_SOURCE_LINE_ABSENT = "source_line_absent"
LOAD_ID_SOURCE_REASON_SOURCE_LINE_PRESENT_LABEL_MISSING = (
    "source_line_present_label_missing"
)
LOAD_ID_SOURCE_REASON_LABEL_DETECTED_UNCLASSIFIED = "label_detected_unclassified"
LOAD_ID_SOURCE_REASON_LABEL_CLASSIFIED_NON_PRIMARY = "label_classified_non_primary"
LOAD_ID_SOURCE_REASON_PRIMARY_CANDIDATE_NOT_GENERATED = (
    "primary_candidate_not_generated"
)
LOAD_ID_SOURCE_REASON_PRIMARY_CANDIDATE_NOT_CORE_MAPPED = (
    "primary_candidate_not_core_mapped"
)
LOAD_ID_SOURCE_REASON_ONLY_NON_PRIMARY_REFS_VISIBLE = "only_non_primary_refs_visible"
LOAD_ID_SOURCE_REASON_SOURCE_LINE_SCOPE_FILTERED = "source_line_scope_filtered"
LOAD_ID_SOURCE_REASON_IMAGE_OR_LOGO_ONLY = "image_or_logo_only"
LOAD_ID_SOURCE_REASON_OCR_NEEDED_OR_WEAK_TEXT = "ocr_needed_or_weak_text"
LOAD_ID_SOURCE_REASON_NO_SHARED_ROOT_CAUSE = "no_shared_root_cause"
LOAD_ID_SOURCE_REASON_UNKNOWN = "unknown"

LOAD_ID_SOURCE_LINE_REASONS = {
    LOAD_ID_SOURCE_REASON_SOURCE_LINE_ABSENT,
    LOAD_ID_SOURCE_REASON_SOURCE_LINE_PRESENT_LABEL_MISSING,
    LOAD_ID_SOURCE_REASON_LABEL_DETECTED_UNCLASSIFIED,
    LOAD_ID_SOURCE_REASON_LABEL_CLASSIFIED_NON_PRIMARY,
    LOAD_ID_SOURCE_REASON_PRIMARY_CANDIDATE_NOT_GENERATED,
    LOAD_ID_SOURCE_REASON_PRIMARY_CANDIDATE_NOT_CORE_MAPPED,
    LOAD_ID_SOURCE_REASON_ONLY_NON_PRIMARY_REFS_VISIBLE,
    LOAD_ID_SOURCE_REASON_SOURCE_LINE_SCOPE_FILTERED,
    LOAD_ID_SOURCE_REASON_IMAGE_OR_LOGO_ONLY,
    LOAD_ID_SOURCE_REASON_OCR_NEEDED_OR_WEAK_TEXT,
    LOAD_ID_SOURCE_REASON_NO_SHARED_ROOT_CAUSE,
    LOAD_ID_SOURCE_REASON_UNKNOWN,
}

LOAD_ID_SOURCE_SECTION_HEADER = "header"
LOAD_ID_SOURCE_SECTION_LOAD_IDENTITY = "load_identity"
LOAD_ID_SOURCE_SECTION_STOP_SECTION = "stop_section"
LOAD_ID_SOURCE_SECTION_BILLING = "billing"
LOAD_ID_SOURCE_SECTION_TERMS = "terms"
LOAD_ID_SOURCE_SECTION_SIGNATURE = "signature"
LOAD_ID_SOURCE_SECTION_UNKNOWN = "unknown"

LOAD_ID_SOURCE_SECTIONS = {
    LOAD_ID_SOURCE_SECTION_HEADER,
    LOAD_ID_SOURCE_SECTION_LOAD_IDENTITY,
    LOAD_ID_SOURCE_SECTION_STOP_SECTION,
    LOAD_ID_SOURCE_SECTION_BILLING,
    LOAD_ID_SOURCE_SECTION_TERMS,
    LOAD_ID_SOURCE_SECTION_SIGNATURE,
    LOAD_ID_SOURCE_SECTION_UNKNOWN,
}

LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER = "load_number"
LOAD_ID_LABEL_CATEGORY_ORDER_NUMBER = "order_number"
LOAD_ID_LABEL_CATEGORY_TENDER_ID = "tender_id"
LOAD_ID_LABEL_CATEGORY_PRO_NUMBER = "pro_number"
LOAD_ID_LABEL_CATEGORY_FREIGHT_BILL_NUMBER = "freight_bill_number"
LOAD_ID_LABEL_CATEGORY_SHIPMENT_NUMBER = "shipment_number"
LOAD_ID_LABEL_CATEGORY_TRIP_NUMBER = "trip_number"
LOAD_ID_LABEL_CATEGORY_DISPATCH_NUMBER = "dispatch_number"
LOAD_ID_LABEL_CATEGORY_GENERIC_REFERENCE = "generic_reference"
LOAD_ID_LABEL_CATEGORY_PO_NUMBER = "po_number"
LOAD_ID_LABEL_CATEGORY_BOL_NUMBER = "bol_number"
LOAD_ID_LABEL_CATEGORY_PICKUP_NUMBER = "pickup_number"
LOAD_ID_LABEL_CATEGORY_DELIVERY_NUMBER = "delivery_number"
LOAD_ID_LABEL_CATEGORY_APPOINTMENT_NUMBER = "appointment_number"
LOAD_ID_LABEL_CATEGORY_CUSTOMER_REFERENCE = "customer_reference"
LOAD_ID_LABEL_CATEGORY_CARRIER_REFERENCE = "carrier_reference"
LOAD_ID_LABEL_CATEGORY_UNKNOWN = "unknown"

LOAD_ID_LABEL_CATEGORIES = {
    LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER,
    LOAD_ID_LABEL_CATEGORY_ORDER_NUMBER,
    LOAD_ID_LABEL_CATEGORY_TENDER_ID,
    LOAD_ID_LABEL_CATEGORY_PRO_NUMBER,
    LOAD_ID_LABEL_CATEGORY_FREIGHT_BILL_NUMBER,
    LOAD_ID_LABEL_CATEGORY_SHIPMENT_NUMBER,
    LOAD_ID_LABEL_CATEGORY_TRIP_NUMBER,
    LOAD_ID_LABEL_CATEGORY_DISPATCH_NUMBER,
    LOAD_ID_LABEL_CATEGORY_GENERIC_REFERENCE,
    LOAD_ID_LABEL_CATEGORY_PO_NUMBER,
    LOAD_ID_LABEL_CATEGORY_BOL_NUMBER,
    LOAD_ID_LABEL_CATEGORY_PICKUP_NUMBER,
    LOAD_ID_LABEL_CATEGORY_DELIVERY_NUMBER,
    LOAD_ID_LABEL_CATEGORY_APPOINTMENT_NUMBER,
    LOAD_ID_LABEL_CATEGORY_CUSTOMER_REFERENCE,
    LOAD_ID_LABEL_CATEGORY_CARRIER_REFERENCE,
    LOAD_ID_LABEL_CATEGORY_UNKNOWN,
}

LOAD_ID_SOURCE_LINE_ANALYSIS_VERSION = "load_identifier_source_line_audit_v1"
LOAD_ID_SOURCE_LINE_RAW_JSON = "load_identifier_source_line_audit_raw.json"
LOAD_ID_SOURCE_LINE_RAW_MD = "load_identifier_source_line_audit_raw.md"
LOAD_ID_SOURCE_LINE_ANALYSIS_JSON = "load_identifier_source_line_audit.json"
LOAD_ID_SOURCE_LINE_ANALYSIS_MD = "load_identifier_source_line_audit.md"

CODE_FIXABLE_REASONS = {
    LOAD_ID_SOURCE_REASON_SOURCE_LINE_PRESENT_LABEL_MISSING,
    LOAD_ID_SOURCE_REASON_LABEL_DETECTED_UNCLASSIFIED,
    LOAD_ID_SOURCE_REASON_PRIMARY_CANDIDATE_NOT_GENERATED,
    LOAD_ID_SOURCE_REASON_PRIMARY_CANDIDATE_NOT_CORE_MAPPED,
}

FIX_BLOCKED_REASONS = {
    LOAD_ID_SOURCE_REASON_SOURCE_LINE_ABSENT,
    LOAD_ID_SOURCE_REASON_LABEL_CLASSIFIED_NON_PRIMARY,
    LOAD_ID_SOURCE_REASON_ONLY_NON_PRIMARY_REFS_VISIBLE,
    LOAD_ID_SOURCE_REASON_IMAGE_OR_LOGO_ONLY,
    LOAD_ID_SOURCE_REASON_OCR_NEEDED_OR_WEAK_TEXT,
    LOAD_ID_SOURCE_REASON_NO_SHARED_ROOT_CAUSE,
}


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def normalize_load_id_source_stage(value):
    token = _token(value)
    return token if token in LOAD_ID_SOURCE_LINE_STAGES else LOAD_ID_SOURCE_STAGE_REVIEW_ROW


def normalize_load_id_source_reason(value):
    token = _token(value)
    return token if token in LOAD_ID_SOURCE_LINE_REASONS else LOAD_ID_SOURCE_REASON_UNKNOWN


def normalize_load_id_source_section(value):
    token = _token(value)
    return token if token in LOAD_ID_SOURCE_SECTIONS else LOAD_ID_SOURCE_SECTION_UNKNOWN


def normalize_load_id_label_category(value):
    token = _token(value)
    return token if token in LOAD_ID_LABEL_CATEGORIES else LOAD_ID_LABEL_CATEGORY_UNKNOWN


def recommended_fix_bucket_for_source_line(reason):
    normalized = normalize_load_id_source_reason(reason)
    if normalized == LOAD_ID_SOURCE_REASON_SOURCE_LINE_PRESENT_LABEL_MISSING:
        return "label_detection"
    if normalized == LOAD_ID_SOURCE_REASON_LABEL_DETECTED_UNCLASSIFIED:
        return "label_classification"
    if normalized == LOAD_ID_SOURCE_REASON_PRIMARY_CANDIDATE_NOT_GENERATED:
        return "primary_classification"
    if normalized == LOAD_ID_SOURCE_REASON_PRIMARY_CANDIDATE_NOT_CORE_MAPPED:
        return "core_mapping"
    if normalized == LOAD_ID_SOURCE_REASON_SOURCE_LINE_SCOPE_FILTERED:
        return "scope_filter_review"
    if normalized == LOAD_ID_SOURCE_REASON_OCR_NEEDED_OR_WEAK_TEXT:
        return "ocr_design_later"
    if normalized in FIX_BLOCKED_REASONS:
        return "local_human_review"
    return "local_human_review"


def build_load_id_source_line_record(
    measurement_alias="",
    stage=LOAD_ID_SOURCE_STAGE_REVIEW_ROW,
    reason=LOAD_ID_SOURCE_REASON_UNKNOWN,
    label_category=LOAD_ID_LABEL_CATEGORY_UNKNOWN,
    source_section_category=LOAD_ID_SOURCE_SECTION_UNKNOWN,
    identifier_like_line_count=0,
    detected_label_count=0,
    classified_label_count=0,
    typed_candidate_count=0,
    primary_candidate_count=0,
    core_mapping_count=0,
    rejected_non_primary_count=0,
    warning_codes=None,
    recommended_fix_bucket="",
):
    normalized_reason = normalize_load_id_source_reason(reason)
    return {
        "measurement_alias": _text(measurement_alias),
        "stage": normalize_load_id_source_stage(stage),
        "reason": normalized_reason,
        "label_category": normalize_load_id_label_category(label_category),
        "source_section_category": normalize_load_id_source_section(
            source_section_category
        ),
        "identifier_like_line_count": _int(identifier_like_line_count),
        "detected_label_count": _int(detected_label_count),
        "classified_label_count": _int(classified_label_count),
        "typed_candidate_count": _int(typed_candidate_count),
        "primary_candidate_count": _int(primary_candidate_count),
        "core_mapping_count": _int(core_mapping_count),
        "rejected_non_primary_count": _int(rejected_non_primary_count),
        "warning_codes": [
            _text(code) for code in warning_codes or [] if _text(code)
        ],
        "recommended_fix_bucket": recommended_fix_bucket
        or recommended_fix_bucket_for_source_line(normalized_reason),
    }


def _top_shared_root_cause(reason_counts):
    eligible = {
        reason: count
        for reason, count in reason_counts.items()
        if reason in CODE_FIXABLE_REASONS
    }
    if not eligible:
        return "", 0
    return max(sorted(eligible.items()), key=lambda item: item[1])


def build_load_id_source_line_aggregate(records, document_count=0):
    normalized_records = [
        build_load_id_source_line_record(**record) for record in records or []
    ]
    stage_counts = Counter(record["stage"] for record in normalized_records)
    reason_counts = Counter(record["reason"] for record in normalized_records)
    label_counts = Counter(record["label_category"] for record in normalized_records)
    section_counts = Counter(
        record["source_section_category"] for record in normalized_records
    )
    aliases_by_reason = defaultdict(list)
    aliases_by_stage = defaultdict(list)
    for record in normalized_records:
        alias = record["measurement_alias"]
        if alias and alias not in aliases_by_reason[record["reason"]]:
            aliases_by_reason[record["reason"]].append(alias)
        if alias and alias not in aliases_by_stage[record["stage"]]:
            aliases_by_stage[record["stage"]].append(alias)

    selected_root_cause, selected_count = _top_shared_root_cause(reason_counts)
    fix_allowed = bool(selected_root_cause and selected_count >= 3)
    if selected_root_cause:
        recommended_next_action = recommended_fix_bucket_for_source_line(
            selected_root_cause
        )
    elif reason_counts:
        recommended_next_action = "local_human_review"
    else:
        recommended_next_action = "run_source_line_audit"

    return {
        "document_count": _int(document_count),
        "records_by_stage": dict(sorted(stage_counts.items())),
        "records_by_reason": dict(sorted(reason_counts.items())),
        "records_by_label_category": dict(sorted(label_counts.items())),
        "records_by_source_section": dict(sorted(section_counts.items())),
        "aliases_by_reason": {
            key: sorted(values) for key, values in sorted(aliases_by_reason.items())
        },
        "aliases_by_stage": {
            key: sorted(values) for key, values in sorted(aliases_by_stage.items())
        },
        "shared_root_cause_candidates": {
            reason: count
            for reason, count in sorted(reason_counts.items())
            if reason in CODE_FIXABLE_REASONS and count >= 2
        },
        "selected_root_cause": selected_root_cause,
        "selected_root_cause_count": selected_count,
        "fix_allowed": fix_allowed,
        "recommended_next_action": recommended_next_action,
        "identifier_like_line_count": sum(
            record["identifier_like_line_count"] for record in normalized_records
        ),
        "detected_label_count": sum(
            record["detected_label_count"] for record in normalized_records
        ),
        "classified_label_count": sum(
            record["classified_label_count"] for record in normalized_records
        ),
        "typed_candidate_count": sum(
            record["typed_candidate_count"] for record in normalized_records
        ),
        "primary_candidate_count": sum(
            record["primary_candidate_count"] for record in normalized_records
        ),
        "core_mapping_count": sum(
            record["core_mapping_count"] for record in normalized_records
        ),
        "rejected_non_primary_count": sum(
            record["rejected_non_primary_count"] for record in normalized_records
        ),
        "analysis_version": LOAD_ID_SOURCE_LINE_ANALYSIS_VERSION,
    }


def build_load_id_source_line_result(records, document_count=0):
    normalized_records = [
        build_load_id_source_line_record(**record) for record in records or []
    ]
    return {
        "analysis_version": LOAD_ID_SOURCE_LINE_ANALYSIS_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
        "line_text_included": False,
        "records": normalized_records,
        "aggregate": build_load_id_source_line_aggregate(
            normalized_records,
            document_count=document_count,
        ),
    }
