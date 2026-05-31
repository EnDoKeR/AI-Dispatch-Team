"""Safe load identifier source-line forensics.

The source-line audit tracks load identifier evidence as counts and categories
only. It must not include private identifier values, raw line text, filenames,
or local paths.
"""

from collections import Counter, defaultdict
import json
import re
from pathlib import Path

from app.document_ai.local_review_analysis import LocalReviewAnalysisError
from app.document_ai.load_identifier_candidates import (
    LOAD_IDENTIFIER_TYPE_BOL_NUMBER,
    LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
    LOAD_IDENTIFIER_TYPE_CARRIER_REFERENCE,
    LOAD_IDENTIFIER_TYPE_CUSTOMER_REFERENCE,
    LOAD_IDENTIFIER_TYPE_DELIVERY_CONFIRMATION,
    LOAD_IDENTIFIER_TYPE_DELIVERY_NUMBER,
    LOAD_IDENTIFIER_TYPE_DISPATCH_NUMBER,
    LOAD_IDENTIFIER_TYPE_FREIGHT_BILL_NUMBER,
    LOAD_IDENTIFIER_TYPE_ORDER_NUMBER,
    LOAD_IDENTIFIER_TYPE_PICKUP_CONFIRMATION,
    LOAD_IDENTIFIER_TYPE_PICKUP_NUMBER,
    LOAD_IDENTIFIER_TYPE_PO_NUMBER,
    LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
    LOAD_IDENTIFIER_TYPE_PRO_NUMBER,
    LOAD_IDENTIFIER_TYPE_SHIPMENT_NUMBER,
    LOAD_IDENTIFIER_TYPE_TENDER_ID,
    LOAD_IDENTIFIER_TYPE_TRIP_NUMBER,
    LOAD_IDENTIFIER_TYPES,
    NON_PRIMARY_REFERENCE_TYPES,
)
from app.document_ai.ratecon_candidates import FIELD_LOAD_NUMBER, FIELD_REFERENCE
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    _normalize_output_dir,
)


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

PRIMARY_LABEL_CATEGORIES = {
    LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER,
    LOAD_ID_LABEL_CATEGORY_ORDER_NUMBER,
    LOAD_ID_LABEL_CATEGORY_TENDER_ID,
    LOAD_ID_LABEL_CATEGORY_PRO_NUMBER,
    LOAD_ID_LABEL_CATEGORY_FREIGHT_BILL_NUMBER,
    LOAD_ID_LABEL_CATEGORY_SHIPMENT_NUMBER,
    LOAD_ID_LABEL_CATEGORY_TRIP_NUMBER,
    LOAD_ID_LABEL_CATEGORY_DISPATCH_NUMBER,
    LOAD_ID_LABEL_CATEGORY_GENERIC_REFERENCE,
}

NON_PRIMARY_LABEL_CATEGORIES = LOAD_ID_LABEL_CATEGORIES - PRIMARY_LABEL_CATEGORIES - {
    LOAD_ID_LABEL_CATEGORY_UNKNOWN,
}

IDENTIFIER_TYPE_TO_LABEL_CATEGORY = {
    LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER: LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER,
    LOAD_IDENTIFIER_TYPE_ORDER_NUMBER: LOAD_ID_LABEL_CATEGORY_ORDER_NUMBER,
    LOAD_IDENTIFIER_TYPE_TENDER_ID: LOAD_ID_LABEL_CATEGORY_TENDER_ID,
    LOAD_IDENTIFIER_TYPE_PRO_NUMBER: LOAD_ID_LABEL_CATEGORY_PRO_NUMBER,
    LOAD_IDENTIFIER_TYPE_SHIPMENT_NUMBER: LOAD_ID_LABEL_CATEGORY_SHIPMENT_NUMBER,
    LOAD_IDENTIFIER_TYPE_FREIGHT_BILL_NUMBER: (
        LOAD_ID_LABEL_CATEGORY_FREIGHT_BILL_NUMBER
    ),
    LOAD_IDENTIFIER_TYPE_TRIP_NUMBER: LOAD_ID_LABEL_CATEGORY_TRIP_NUMBER,
    LOAD_IDENTIFIER_TYPE_DISPATCH_NUMBER: LOAD_ID_LABEL_CATEGORY_DISPATCH_NUMBER,
    LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE: LOAD_ID_LABEL_CATEGORY_GENERIC_REFERENCE,
    LOAD_IDENTIFIER_TYPE_PO_NUMBER: LOAD_ID_LABEL_CATEGORY_PO_NUMBER,
    LOAD_IDENTIFIER_TYPE_BOL_NUMBER: LOAD_ID_LABEL_CATEGORY_BOL_NUMBER,
    LOAD_IDENTIFIER_TYPE_PICKUP_NUMBER: LOAD_ID_LABEL_CATEGORY_PICKUP_NUMBER,
    LOAD_IDENTIFIER_TYPE_PICKUP_CONFIRMATION: LOAD_ID_LABEL_CATEGORY_PICKUP_NUMBER,
    LOAD_IDENTIFIER_TYPE_DELIVERY_NUMBER: LOAD_ID_LABEL_CATEGORY_DELIVERY_NUMBER,
    LOAD_IDENTIFIER_TYPE_DELIVERY_CONFIRMATION: LOAD_ID_LABEL_CATEGORY_DELIVERY_NUMBER,
    LOAD_IDENTIFIER_TYPE_CUSTOMER_REFERENCE: LOAD_ID_LABEL_CATEGORY_CUSTOMER_REFERENCE,
    LOAD_IDENTIFIER_TYPE_CARRIER_REFERENCE: LOAD_ID_LABEL_CATEGORY_CARRIER_REFERENCE,
}

LABEL_CATEGORY_PATTERNS = (
    (LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER, re.compile(r"\bload\s*(?:#|no\.?|number|id)\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_ORDER_NUMBER, re.compile(r"\border\s*(?:#|no\.?|number|id)\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_TENDER_ID, re.compile(r"\btender\s*(?:#|no\.?|number|id|ref|reference)\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_PRO_NUMBER, re.compile(r"\bpro\s*(?:#|no\.?|number)\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_FREIGHT_BILL_NUMBER, re.compile(r"\bfreight\s+bill\s*(?:#|no\.?|number)?\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_SHIPMENT_NUMBER, re.compile(r"\bshipment\s*(?:#|no\.?|number|id)\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_TRIP_NUMBER, re.compile(r"\btrip\s*(?:#|no\.?|number|id)\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_DISPATCH_NUMBER, re.compile(r"\bdispatch\s*(?:#|no\.?|number|id)\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_PO_NUMBER, re.compile(r"\bpo\s*(?:#|no\.?|number)\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_BOL_NUMBER, re.compile(r"\bbol\s*(?:#|no\.?|number)\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_PICKUP_NUMBER, re.compile(r"\bpick\s*up\s*(?:#|no\.?|number)|\bpickup\s*(?:#|no\.?|number|confirmation)\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_DELIVERY_NUMBER, re.compile(r"\bdelivery\s*(?:#|no\.?|number|confirmation)\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_APPOINTMENT_NUMBER, re.compile(r"\bappointment\s*(?:#|no\.?|number)\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_CUSTOMER_REFERENCE, re.compile(r"\bcustomer\s*(?:ref|reference)\s*(?:#|no\.?|number)?\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_CARRIER_REFERENCE, re.compile(r"\bcarrier\s*(?:ref|reference)\s*(?:#|no\.?|number)?\b", re.I)),
    (LOAD_ID_LABEL_CATEGORY_GENERIC_REFERENCE, re.compile(r"\b(?:ref|reference|confirmation|booking)\s*(?:#|no\.?\b|number\b|id\b)", re.I)),
)

BROAD_IDENTIFIER_LIKE_PATTERN = re.compile(
    r"\b(?:load|order|tender|shipment|freight\s+bill|pro|trip|dispatch|"
    r"reference|ref|confirmation|booking|po|bol|pickup|delivery|appointment|"
    r"customer|carrier)\b.{0,30}(?:#|no\.?|number|id|ref|reference)",
    re.I,
)

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


def _artifact_pages(artifact):
    if isinstance(artifact, dict):
        return artifact.get("pages", []) or []
    return getattr(artifact, "pages", []) or []


def _line_categories(line):
    text = str(line or "")
    categories = [
        category
        for category, pattern in LABEL_CATEGORY_PATTERNS
        if pattern.search(text)
    ]
    if categories:
        return categories
    if BROAD_IDENTIFIER_LIKE_PATTERN.search(text):
        return [LOAD_ID_LABEL_CATEGORY_UNKNOWN]
    return []


def _section_for_line(lines, index):
    window = " ".join(
        str(lines[position] or "").strip().lower()
        for position in range(max(0, index - 3), min(len(lines), index + 4))
        if str(lines[position] or "").strip()
    )
    if any(marker in window for marker in ["signature", "authorized", "sign here"]):
        return LOAD_ID_SOURCE_SECTION_SIGNATURE
    if any(marker in window for marker in ["terms", "conditions", "agreement"]):
        return LOAD_ID_SOURCE_SECTION_TERMS
    if any(marker in window for marker in ["billing", "remit", "payment terms"]):
        return LOAD_ID_SOURCE_SECTION_BILLING
    if any(
        marker in window
        for marker in [
            "pickup",
            "pick up",
            "delivery",
            "shipper",
            "consignee",
            "receiver",
            "stop",
        ]
    ):
        return LOAD_ID_SOURCE_SECTION_STOP_SECTION
    if any(
        marker in window
        for marker in [
            "load confirmation",
            "rate confirmation",
            "carrier load tender",
            "load tender",
            "order confirmation",
            "route details",
            "load details",
        ]
    ):
        return LOAD_ID_SOURCE_SECTION_LOAD_IDENTITY
    if index <= 8:
        return LOAD_ID_SOURCE_SECTION_HEADER
    return LOAD_ID_SOURCE_SECTION_UNKNOWN


def scan_load_identifier_source_lines(artifact):
    """Return safe source-line counts for one text/layout artifact."""
    section_counts = Counter()
    label_counts = Counter()
    identifier_like_count = 0
    detected_label_count = 0
    classified_label_count = 0
    primary_label_count = 0
    non_primary_label_count = 0

    for page in _artifact_pages(artifact):
        lines = str((page or {}).get("text", "") or "").splitlines()
        for index, line in enumerate(lines):
            categories = _line_categories(line)
            if not categories:
                continue
            identifier_like_count += 1
            section = _section_for_line(lines, index)
            section_counts[section] += 1
            detected_label_count += 1
            for category in categories:
                normalized_category = normalize_load_id_label_category(category)
                label_counts[normalized_category] += 1
                if normalized_category != LOAD_ID_LABEL_CATEGORY_UNKNOWN:
                    classified_label_count += 1
                if normalized_category in PRIMARY_LABEL_CATEGORIES:
                    primary_label_count += 1
                elif normalized_category in NON_PRIMARY_LABEL_CATEGORIES:
                    non_primary_label_count += 1

    return {
        "identifier_like_line_count": identifier_like_count,
        "section_counts": dict(sorted(section_counts.items())),
        "label_category_counts": dict(sorted(label_counts.items())),
        "detected_label_count": detected_label_count,
        "classified_label_count": classified_label_count,
        "primary_label_count": primary_label_count,
        "non_primary_label_count": non_primary_label_count,
        "private_values_included": False,
        "raw_text_included": False,
        "line_text_included": False,
    }


def _identifier_type(candidate):
    return _token(
        (candidate or {}).get("identifier_type")
        or (candidate or {}).get("value_type")
    )


def _identifier_candidates(candidates):
    return [
        candidate
        for candidate in candidates or []
        if isinstance(candidate, dict) and _identifier_type(candidate) in LOAD_IDENTIFIER_TYPES
    ]


def _type_counts(candidates):
    counts = Counter()
    for candidate in candidates or []:
        category = IDENTIFIER_TYPE_TO_LABEL_CATEGORY.get(
            _identifier_type(candidate),
            LOAD_ID_LABEL_CATEGORY_UNKNOWN,
        )
        counts[category] += 1
    return dict(sorted(counts.items()))


def _resolution_core_mapping_count(resolution_result):
    for resolution in (resolution_result or {}).get("resolutions", []) or []:
        if not isinstance(resolution, dict):
            continue
        if str(resolution.get("field_name") or "").strip() != FIELD_LOAD_NUMBER:
            continue
        status = str(resolution.get("status") or "").strip()
        return 1 if status and status != "missing" else 0
    return 0


def build_load_identifier_source_line_metrics(
    full_artifact=None,
    scoped_artifact=None,
    candidates=None,
    resolution_result=None,
):
    full_scan = scan_load_identifier_source_lines(full_artifact or {})
    scoped_scan = scan_load_identifier_source_lines(scoped_artifact or full_artifact or {})
    identifier_candidates = _identifier_candidates(candidates)
    primary_candidates = [
        candidate
        for candidate in identifier_candidates
        if candidate.get("primary_load_identifier_candidate")
        and str(candidate.get("field_name") or "").strip() == FIELD_LOAD_NUMBER
    ]
    typed_reference_candidates = [
        candidate
        for candidate in identifier_candidates
        if str(candidate.get("field_name") or "").strip() == FIELD_REFERENCE
    ]
    rejected_non_primary_candidates = [
        candidate
        for candidate in typed_reference_candidates
        if _identifier_type(candidate) in NON_PRIMARY_REFERENCE_TYPES
    ]
    scope_filtered_count = max(
        0,
        full_scan["identifier_like_line_count"]
        - scoped_scan["identifier_like_line_count"],
    )
    return {
        "identifier_like_source_line_count": full_scan["identifier_like_line_count"],
        "scoped_identifier_like_source_line_count": scoped_scan[
            "identifier_like_line_count"
        ],
        "source_line_scope_filtered_count": scope_filtered_count,
        "header_identifier_like_line_count": full_scan["section_counts"].get(
            LOAD_ID_SOURCE_SECTION_HEADER,
            0,
        ),
        "load_identity_identifier_like_line_count": full_scan["section_counts"].get(
            LOAD_ID_SOURCE_SECTION_LOAD_IDENTITY,
            0,
        ),
        "stop_section_identifier_like_line_count": full_scan["section_counts"].get(
            LOAD_ID_SOURCE_SECTION_STOP_SECTION,
            0,
        ),
        "billing_terms_identifier_like_line_count": (
            full_scan["section_counts"].get(LOAD_ID_SOURCE_SECTION_BILLING, 0)
            + full_scan["section_counts"].get(LOAD_ID_SOURCE_SECTION_TERMS, 0)
        ),
        "source_section_counts": full_scan["section_counts"],
        "label_category_counts": full_scan["label_category_counts"],
        "label_detected_count": scoped_scan["detected_label_count"],
        "label_classified_count": scoped_scan["classified_label_count"],
        "primary_label_count": scoped_scan["primary_label_count"],
        "non_primary_label_count": scoped_scan["non_primary_label_count"],
        "typed_candidate_count": len(identifier_candidates),
        "primary_candidate_count": len(primary_candidates),
        "typed_reference_count": len(typed_reference_candidates),
        "rejected_non_primary_count": len(rejected_non_primary_candidates),
        "core_mapping_count": _resolution_core_mapping_count(resolution_result),
        "candidate_label_category_counts": _type_counts(identifier_candidates),
        "private_values_included": False,
        "raw_text_included": False,
        "line_text_included": False,
    }


def build_load_id_source_line_record_from_metrics(
    measurement_alias="",
    metrics=None,
    triage_route="",
    extraction_status="",
    char_count=0,
):
    metrics = metrics if isinstance(metrics, dict) else {}
    identifier_lines = _int(metrics.get("identifier_like_source_line_count"))
    scoped_identifier_lines = _int(
        metrics.get("scoped_identifier_like_source_line_count")
    )
    label_detected = _int(metrics.get("label_detected_count"))
    label_classified = _int(metrics.get("label_classified_count"))
    typed_candidates = _int(metrics.get("typed_candidate_count"))
    primary_candidates = _int(metrics.get("primary_candidate_count"))
    core_mappings = _int(metrics.get("core_mapping_count"))
    rejected_non_primary = _int(metrics.get("rejected_non_primary_count"))
    category_counts = metrics.get("label_category_counts", {}) or {}
    section_counts = metrics.get("source_section_counts", {}) or {}
    top_category = (
        max(sorted(category_counts.items()), key=lambda item: item[1])[0]
        if category_counts
        else LOAD_ID_LABEL_CATEGORY_UNKNOWN
    )
    top_section = (
        max(sorted(section_counts.items()), key=lambda item: item[1])[0]
        if section_counts
        else LOAD_ID_SOURCE_SECTION_UNKNOWN
    )

    if _token(triage_route) == "ocr_needed" or _token(extraction_status) in {
        "empty_text",
        "broken_or_unsupported",
        "extraction_failed",
    }:
        reason = LOAD_ID_SOURCE_REASON_OCR_NEEDED_OR_WEAK_TEXT
        stage = LOAD_ID_SOURCE_STAGE_SOURCE_LINE
    elif not _int(char_count) and not identifier_lines:
        reason = LOAD_ID_SOURCE_REASON_OCR_NEEDED_OR_WEAK_TEXT
        stage = LOAD_ID_SOURCE_STAGE_SOURCE_LINE
    elif identifier_lines == 0:
        reason = LOAD_ID_SOURCE_REASON_SOURCE_LINE_ABSENT
        stage = LOAD_ID_SOURCE_STAGE_SOURCE_LINE
    elif scoped_identifier_lines == 0 and identifier_lines:
        reason = LOAD_ID_SOURCE_REASON_SOURCE_LINE_SCOPE_FILTERED
        stage = LOAD_ID_SOURCE_STAGE_LINE_FEATURE
    elif label_detected == 0:
        reason = LOAD_ID_SOURCE_REASON_SOURCE_LINE_PRESENT_LABEL_MISSING
        stage = LOAD_ID_SOURCE_STAGE_LABEL_DETECTED
    elif label_classified == 0:
        reason = LOAD_ID_SOURCE_REASON_LABEL_DETECTED_UNCLASSIFIED
        stage = LOAD_ID_SOURCE_STAGE_LABEL_CLASSIFIED
    elif typed_candidates and primary_candidates == 0 and rejected_non_primary:
        reason = LOAD_ID_SOURCE_REASON_ONLY_NON_PRIMARY_REFS_VISIBLE
        stage = LOAD_ID_SOURCE_STAGE_PRIMARY_CLASSIFIED
    elif typed_candidates and primary_candidates == 0:
        reason = LOAD_ID_SOURCE_REASON_PRIMARY_CANDIDATE_NOT_GENERATED
        stage = LOAD_ID_SOURCE_STAGE_CANDIDATE_GENERATED
    elif primary_candidates and core_mappings == 0:
        reason = LOAD_ID_SOURCE_REASON_PRIMARY_CANDIDATE_NOT_CORE_MAPPED
        stage = LOAD_ID_SOURCE_STAGE_CORE_MAPPED
    elif rejected_non_primary:
        reason = LOAD_ID_SOURCE_REASON_LABEL_CLASSIFIED_NON_PRIMARY
        stage = LOAD_ID_SOURCE_STAGE_LABEL_CLASSIFIED
    else:
        reason = LOAD_ID_SOURCE_REASON_UNKNOWN
        stage = LOAD_ID_SOURCE_STAGE_REVIEW_ROW

    return build_load_id_source_line_record(
        measurement_alias=measurement_alias,
        stage=stage,
        reason=reason,
        label_category=top_category,
        source_section_category=top_section,
        identifier_like_line_count=identifier_lines,
        detected_label_count=label_detected,
        classified_label_count=label_classified,
        typed_candidate_count=typed_candidates,
        primary_candidate_count=primary_candidates,
        core_mapping_count=core_mappings,
        rejected_non_primary_count=rejected_non_primary,
    )


def analyze_load_id_source_lines_from_rows(measurement_rows):
    records = []
    for row in measurement_rows or []:
        if not isinstance(row, dict):
            continue
        explicit_records = row.get("load_identifier_source_line_records", []) or []
        if explicit_records:
            records.extend(
                build_load_id_source_line_record(**record)
                for record in explicit_records
                if isinstance(record, dict)
            )
            continue
        records.append(
            build_load_id_source_line_record_from_metrics(
                measurement_alias=row.get("document_alias", ""),
                metrics=row.get("load_identifier_source_line_metrics", {}),
                triage_route=row.get("triage_route", ""),
                extraction_status=row.get("extraction_status", ""),
                char_count=row.get("char_count", 0),
            )
        )
    return build_load_id_source_line_result(
        records,
        document_count=len(measurement_rows or []),
    )


def _read_json(path, default):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as exc:
        raise LocalReviewAnalysisError(f"invalid JSON: {Path(path).name}") from exc


def _safe_summary_rows(input_dir):
    payload = _read_json(Path(input_dir) / "safe_summary.json", default={}) or {}
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    return rows if isinstance(rows, list) else []


def analyze_load_identifier_source_lines(input_dir=None):
    root = Path(input_dir or DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR)
    artifact = _read_json(root / LOAD_ID_SOURCE_LINE_RAW_JSON, default=None)
    if isinstance(artifact, dict) and "records" in artifact and "aggregate" in artifact:
        return build_load_id_source_line_result(
            artifact.get("records", []),
            document_count=(artifact.get("aggregate", {}) or {}).get(
                "document_count",
                0,
            ),
        )
    if not (root / "safe_summary.json").exists():
        raise LocalReviewAnalysisError("missing safe_summary.json")
    return analyze_load_id_source_lines_from_rows(_safe_summary_rows(root))


def load_identifier_source_line_markdown_lines(analysis):
    aggregate = (analysis or {}).get("aggregate", {}) or {}
    lines = [
        "# Load Identifier Source-Line Audit",
        "",
        "Local-only analysis. Safe to share: aliases, counts, statuses, label categories, and stage categories.",
        "Do not share private values, line text, raw text, filenames, local paths, rates, addresses, references, or broker identifiers.",
        "",
        f"Documents analyzed: {aggregate.get('document_count', 0)}",
        f"Fix allowed: {aggregate.get('fix_allowed', False)}",
        f"Selected root cause: {aggregate.get('selected_root_cause', '')}",
        f"Recommended next action: {aggregate.get('recommended_next_action', '')}",
        "",
        "## Counts",
        f"- identifier-like source lines: {aggregate.get('identifier_like_line_count', 0)}",
        f"- labels detected: {aggregate.get('detected_label_count', 0)}",
        f"- labels classified: {aggregate.get('classified_label_count', 0)}",
        f"- typed candidates: {aggregate.get('typed_candidate_count', 0)}",
        f"- primary candidates: {aggregate.get('primary_candidate_count', 0)}",
        f"- core mappings: {aggregate.get('core_mapping_count', 0)}",
        f"- rejected non-primary references: {aggregate.get('rejected_non_primary_count', 0)}",
        "",
        "## Reasons",
    ]
    for reason, count in (aggregate.get("records_by_reason", {}) or {}).items():
        lines.append(f"- {reason}: {count}")
    lines.extend(["", "## Source Sections"])
    for section, count in (aggregate.get("records_by_source_section", {}) or {}).items():
        lines.append(f"- {section}: {count}")
    lines.extend(["", "## Label Categories"])
    for category, count in (aggregate.get("records_by_label_category", {}) or {}).items():
        lines.append(f"- {category}: {count}")
    return lines


def write_load_identifier_source_line_json(analysis, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "json": path.name,
        "private_values_printed": False,
        "raw_text_printed": False,
        "line_text_printed": False,
    }


def write_load_identifier_source_line_md(analysis, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(load_identifier_source_line_markdown_lines(analysis)) + "\n",
        encoding="utf-8",
    )
    return {
        "md": path.name,
        "private_values_printed": False,
        "raw_text_printed": False,
        "line_text_printed": False,
    }


def write_load_identifier_source_line_artifacts(
    analysis,
    output_dir=None,
    allow_custom_output_dir=False,
    raw=False,
):
    output_root = _normalize_output_dir(
        output_dir or DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    json_name = LOAD_ID_SOURCE_LINE_RAW_JSON if raw else LOAD_ID_SOURCE_LINE_ANALYSIS_JSON
    md_name = LOAD_ID_SOURCE_LINE_RAW_MD if raw else LOAD_ID_SOURCE_LINE_ANALYSIS_MD
    json_result = write_load_identifier_source_line_json(
        analysis,
        output_root / json_name,
    )
    md_result = write_load_identifier_source_line_md(
        analysis,
        output_root / md_name,
    )
    return {
        "paths": {
            "load_identifier_source_line_json": output_root / json_name,
            "load_identifier_source_line_md": output_root / md_name,
        },
        "aggregate": (analysis or {}).get("aggregate", {}),
        "private_values_printed": bool(
            json_result.get("private_values_printed")
            or md_result.get("private_values_printed")
        ),
        "raw_text_printed": bool(
            json_result.get("raw_text_printed") or md_result.get("raw_text_printed")
        ),
        "line_text_printed": bool(
            json_result.get("line_text_printed") or md_result.get("line_text_printed")
        ),
    }
