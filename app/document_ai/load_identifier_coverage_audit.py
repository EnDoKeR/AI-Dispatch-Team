"""Safe load identifier coverage audit contracts.

The audit records load identifier pipeline progress as aliases, counts,
statuses, and label categories only. It must not carry private identifier
values or raw document text.
"""

from collections import Counter, defaultdict
import json
from pathlib import Path

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
)
from app.document_ai.local_review_analysis import LocalReviewAnalysisError
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    _normalize_output_dir,
)


LOAD_ID_AUDIT_STAGE_SOURCE_LINE = "source_line"
LOAD_ID_AUDIT_STAGE_LABEL_DETECTED = "label_detected"
LOAD_ID_AUDIT_STAGE_LABEL_CLASSIFIED = "label_classified"
LOAD_ID_AUDIT_STAGE_TYPED_CANDIDATE_GENERATED = "typed_candidate_generated"
LOAD_ID_AUDIT_STAGE_PRIMARY_CANDIDATE_CLASSIFIED = "primary_candidate_classified"
LOAD_ID_AUDIT_STAGE_NON_PRIMARY_REFERENCE_REJECTED = (
    "non_primary_reference_rejected"
)
LOAD_ID_AUDIT_STAGE_CORE_LOAD_NUMBER_MAPPED = "core_load_number_mapped"
LOAD_ID_AUDIT_STAGE_REVIEW_ROW_EMITTED = "review_row_emitted"

LOAD_IDENTIFIER_COVERAGE_STAGES = {
    LOAD_ID_AUDIT_STAGE_SOURCE_LINE,
    LOAD_ID_AUDIT_STAGE_LABEL_DETECTED,
    LOAD_ID_AUDIT_STAGE_LABEL_CLASSIFIED,
    LOAD_ID_AUDIT_STAGE_TYPED_CANDIDATE_GENERATED,
    LOAD_ID_AUDIT_STAGE_PRIMARY_CANDIDATE_CLASSIFIED,
    LOAD_ID_AUDIT_STAGE_NON_PRIMARY_REFERENCE_REJECTED,
    LOAD_ID_AUDIT_STAGE_CORE_LOAD_NUMBER_MAPPED,
    LOAD_ID_AUDIT_STAGE_REVIEW_ROW_EMITTED,
}

LOAD_ID_AUDIT_STATUS_PRESENT = "present"
LOAD_ID_AUDIT_STATUS_MISSING = "missing"
LOAD_ID_AUDIT_STATUS_REJECTED = "rejected"
LOAD_ID_AUDIT_STATUS_CONFLICT = "conflict"
LOAD_ID_AUDIT_STATUS_LOW_CONFIDENCE = "low_confidence"
LOAD_ID_AUDIT_STATUS_NON_APPLICABLE = "non_applicable"
LOAD_ID_AUDIT_STATUS_OCR_NEEDED = "ocr_needed"
LOAD_ID_AUDIT_STATUS_UNKNOWN = "unknown"

LOAD_IDENTIFIER_COVERAGE_STATUSES = {
    LOAD_ID_AUDIT_STATUS_PRESENT,
    LOAD_ID_AUDIT_STATUS_MISSING,
    LOAD_ID_AUDIT_STATUS_REJECTED,
    LOAD_ID_AUDIT_STATUS_CONFLICT,
    LOAD_ID_AUDIT_STATUS_LOW_CONFIDENCE,
    LOAD_ID_AUDIT_STATUS_NON_APPLICABLE,
    LOAD_ID_AUDIT_STATUS_OCR_NEEDED,
    LOAD_ID_AUDIT_STATUS_UNKNOWN,
}

LOAD_ID_AUDIT_REASON_IDENTIFIER_ABSENT = "identifier_absent_in_document"
LOAD_ID_AUDIT_REASON_LABEL_NOT_DETECTED = "identifier_label_not_detected"
LOAD_ID_AUDIT_REASON_LABEL_UNCLASSIFIED = (
    "identifier_label_detected_but_unclassified"
)
LOAD_ID_AUDIT_REASON_PRIMARY_NOT_GENERATED = "primary_candidate_not_generated"
LOAD_ID_AUDIT_REASON_PRIMARY_REJECTED_AS_NON_PRIMARY = (
    "primary_candidate_rejected_as_non_primary"
)
LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES = (
    "only_non_primary_references_found"
)
LOAD_ID_AUDIT_REASON_PRIMARY_NOT_CORE_MAPPED = (
    "primary_candidate_generated_but_not_core_mapped"
)
LOAD_ID_AUDIT_REASON_MULTIPLE_PRIMARY_CONFLICT = (
    "multiple_primary_identifiers_conflict"
)
LOAD_ID_AUDIT_REASON_CONTEXT_MISSING = "context_missing_header_or_load_identity"
LOAD_ID_AUDIT_REASON_SCOPE_FILTERED = "scope_filtered"
LOAD_ID_AUDIT_REASON_OCR_NEEDED = "ocr_needed"
LOAD_ID_AUDIT_REASON_UNKNOWN = "unknown"

LOAD_IDENTIFIER_COVERAGE_REASONS = {
    LOAD_ID_AUDIT_REASON_IDENTIFIER_ABSENT,
    LOAD_ID_AUDIT_REASON_LABEL_NOT_DETECTED,
    LOAD_ID_AUDIT_REASON_LABEL_UNCLASSIFIED,
    LOAD_ID_AUDIT_REASON_PRIMARY_NOT_GENERATED,
    LOAD_ID_AUDIT_REASON_PRIMARY_REJECTED_AS_NON_PRIMARY,
    LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES,
    LOAD_ID_AUDIT_REASON_PRIMARY_NOT_CORE_MAPPED,
    LOAD_ID_AUDIT_REASON_MULTIPLE_PRIMARY_CONFLICT,
    LOAD_ID_AUDIT_REASON_CONTEXT_MISSING,
    LOAD_ID_AUDIT_REASON_SCOPE_FILTERED,
    LOAD_ID_AUDIT_REASON_OCR_NEEDED,
    LOAD_ID_AUDIT_REASON_UNKNOWN,
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

LOAD_IDENTIFIER_LABEL_CATEGORIES = {
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

LOAD_IDENTIFIER_COVERAGE_ANALYSIS_VERSION = "load_identifier_coverage_audit_v1"
LOAD_IDENTIFIER_COVERAGE_JSON = "load_identifier_coverage.json"
LOAD_IDENTIFIER_COVERAGE_MD = "load_identifier_coverage.md"
LOAD_IDENTIFIER_COVERAGE_ANALYSIS_JSON = "load_identifier_coverage_audit.json"
LOAD_IDENTIFIER_COVERAGE_ANALYSIS_MD = "load_identifier_coverage_audit.md"

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


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def normalize_load_identifier_stage(value):
    token = _token(value)
    return (
        token
        if token in LOAD_IDENTIFIER_COVERAGE_STAGES
        else LOAD_ID_AUDIT_STAGE_REVIEW_ROW_EMITTED
    )


def normalize_load_identifier_status(value):
    token = _token(value)
    return (
        token
        if token in LOAD_IDENTIFIER_COVERAGE_STATUSES
        else LOAD_ID_AUDIT_STATUS_UNKNOWN
    )


def normalize_load_identifier_reason(value):
    token = _token(value)
    return (
        token
        if token in LOAD_IDENTIFIER_COVERAGE_REASONS
        else LOAD_ID_AUDIT_REASON_UNKNOWN
    )


def normalize_load_identifier_label_category(value):
    token = _token(value)
    return (
        token
        if token in LOAD_IDENTIFIER_LABEL_CATEGORIES
        else LOAD_ID_LABEL_CATEGORY_UNKNOWN
    )


def recommended_fix_bucket_for_load_identifier(reason, label_category=""):
    normalized_reason = normalize_load_identifier_reason(reason)
    category = normalize_load_identifier_label_category(label_category)
    if normalized_reason == LOAD_ID_AUDIT_REASON_OCR_NEEDED:
        return "ocr_queue"
    if normalized_reason == LOAD_ID_AUDIT_REASON_SCOPE_FILTERED:
        return "scope_filter_review"
    if normalized_reason in {
        LOAD_ID_AUDIT_REASON_LABEL_NOT_DETECTED,
        LOAD_ID_AUDIT_REASON_CONTEXT_MISSING,
    }:
        return "load_identifier_label_section_coverage"
    if normalized_reason == LOAD_ID_AUDIT_REASON_LABEL_UNCLASSIFIED:
        return "load_identifier_label_classification"
    if normalized_reason in {
        LOAD_ID_AUDIT_REASON_PRIMARY_NOT_GENERATED,
        LOAD_ID_AUDIT_REASON_PRIMARY_REJECTED_AS_NON_PRIMARY,
    }:
        return "primary_candidate_classification"
    if normalized_reason == LOAD_ID_AUDIT_REASON_PRIMARY_NOT_CORE_MAPPED:
        return "primary_to_core_mapping"
    if normalized_reason == LOAD_ID_AUDIT_REASON_MULTIPLE_PRIMARY_CONFLICT:
        return "local_human_review"
    if normalized_reason == LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES:
        return "header_context_or_human_review"
    if category == LOAD_ID_LABEL_CATEGORY_GENERIC_REFERENCE:
        return "generic_header_reference_review_candidate"
    return "local_human_review"


def build_load_identifier_coverage_record(
    measurement_alias="",
    stage=LOAD_ID_AUDIT_STAGE_REVIEW_ROW_EMITTED,
    status=LOAD_ID_AUDIT_STATUS_UNKNOWN,
    reason=LOAD_ID_AUDIT_REASON_UNKNOWN,
    identifier_label_category=LOAD_ID_LABEL_CATEGORY_UNKNOWN,
    candidate_count=0,
    primary_candidate_count=0,
    typed_reference_count=0,
    rejected_non_primary_count=0,
    core_mapping_count=0,
    warning_codes=None,
    recommended_fix_bucket="",
):
    normalized_reason = normalize_load_identifier_reason(reason)
    normalized_category = normalize_load_identifier_label_category(
        identifier_label_category
    )
    return {
        "measurement_alias": _text(measurement_alias),
        "stage": normalize_load_identifier_stage(stage),
        "status": normalize_load_identifier_status(status),
        "reason": normalized_reason,
        "identifier_label_category": normalized_category,
        "candidate_count": _int(candidate_count),
        "primary_candidate_count": _int(primary_candidate_count),
        "typed_reference_count": _int(typed_reference_count),
        "rejected_non_primary_count": _int(rejected_non_primary_count),
        "core_mapping_count": _int(core_mapping_count),
        "warning_codes": [str(code or "").strip() for code in warning_codes or [] if str(code or "").strip()],
        "recommended_fix_bucket": recommended_fix_bucket
        or recommended_fix_bucket_for_load_identifier(
            normalized_reason,
            normalized_category,
        ),
    }


def build_load_identifier_coverage_aggregate(records, document_count=0):
    normalized_records = [
        build_load_identifier_coverage_record(**record) for record in records
    ]
    reason_counts = Counter(record["reason"] for record in normalized_records)
    stage_counts = Counter(record["stage"] for record in normalized_records)
    label_counts = Counter(
        record["identifier_label_category"] for record in normalized_records
    )
    aliases_by_reason = defaultdict(list)
    aliases_by_label_category = defaultdict(list)
    fix_counts = Counter()
    for record in normalized_records:
        alias = record["measurement_alias"]
        if alias and alias not in aliases_by_reason[record["reason"]]:
            aliases_by_reason[record["reason"]].append(alias)
        category = record["identifier_label_category"]
        if alias and alias not in aliases_by_label_category[category]:
            aliases_by_label_category[category].append(alias)
        fix_counts[record["recommended_fix_bucket"]] += 1

    recommended_next_fix = (
        fix_counts.most_common(1)[0][0] if fix_counts else "local_human_review"
    )
    return {
        "document_count": _int(document_count),
        "records_by_reason": dict(sorted(reason_counts.items())),
        "records_by_stage": dict(sorted(stage_counts.items())),
        "records_by_label_category": dict(sorted(label_counts.items())),
        "primary_candidate_count": sum(
            record["primary_candidate_count"] for record in normalized_records
        ),
        "typed_reference_count": sum(
            record["typed_reference_count"] for record in normalized_records
        ),
        "rejected_non_primary_count": sum(
            record["rejected_non_primary_count"] for record in normalized_records
        ),
        "core_mapping_count": sum(
            record["core_mapping_count"] for record in normalized_records
        ),
        "aliases_by_reason": {
            key: sorted(values) for key, values in sorted(aliases_by_reason.items())
        },
        "aliases_by_label_category": {
            key: sorted(values)
            for key, values in sorted(aliases_by_label_category.items())
        },
        "recommended_next_fix": recommended_next_fix,
        "analysis_version": LOAD_IDENTIFIER_COVERAGE_ANALYSIS_VERSION,
    }


def build_load_identifier_coverage_result(records, document_count=0):
    normalized_records = [
        build_load_identifier_coverage_record(**record) for record in records
    ]
    return {
        "analysis_version": LOAD_IDENTIFIER_COVERAGE_ANALYSIS_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
        "records": normalized_records,
        "aggregate": build_load_identifier_coverage_aggregate(
            normalized_records,
            document_count=document_count,
        ),
    }


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


def _category_for_identifier_type(identifier_type):
    return IDENTIFIER_TYPE_TO_LABEL_CATEGORY.get(
        _token(identifier_type),
        LOAD_ID_LABEL_CATEGORY_UNKNOWN,
    )


def _records_from_metrics(row):
    alias = _text((row or {}).get("document_alias"))
    metrics = (row or {}).get("load_identifier_coverage_metrics", {}) or {}
    if not isinstance(metrics, dict):
        metrics = {}
    label_count = _int(metrics.get("identifier_label_feature_count"))
    primary_count = _int(metrics.get("primary_identifier_candidate_count"))
    typed_ref_count = _int(metrics.get("typed_reference_candidate_count"))
    rejected_count = _int(metrics.get("rejected_reference_as_load_id_count"))
    core_mapping_count = _int(metrics.get("core_load_number_mapping_count"))
    conflict_count = _int(metrics.get("conflicting_primary_identifiers"))
    primary_type_counts = metrics.get("primary_identifier_type_counts", {}) or {}
    typed_ref_type_counts = metrics.get("typed_reference_type_counts", {}) or {}
    rejected_type_counts = metrics.get("rejected_reference_type_counts", {}) or {}
    records = []

    if label_count == 0:
        records.append(
            build_load_identifier_coverage_record(
                measurement_alias=alias,
                stage=LOAD_ID_AUDIT_STAGE_LABEL_DETECTED,
                status=LOAD_ID_AUDIT_STATUS_MISSING,
                reason=LOAD_ID_AUDIT_REASON_LABEL_NOT_DETECTED,
            )
        )
    for identifier_type, count in sorted(primary_type_counts.items()):
        category = _category_for_identifier_type(identifier_type)
        for _ in range(_int(count)):
            records.append(
                build_load_identifier_coverage_record(
                    measurement_alias=alias,
                    stage=LOAD_ID_AUDIT_STAGE_PRIMARY_CANDIDATE_CLASSIFIED,
                    status=LOAD_ID_AUDIT_STATUS_PRESENT,
                    reason=LOAD_ID_AUDIT_REASON_UNKNOWN,
                    identifier_label_category=category,
                    candidate_count=1,
                    primary_candidate_count=1,
                )
            )
    for identifier_type, count in sorted(typed_ref_type_counts.items()):
        category = _category_for_identifier_type(identifier_type)
        for _ in range(_int(count)):
            records.append(
                build_load_identifier_coverage_record(
                    measurement_alias=alias,
                    stage=LOAD_ID_AUDIT_STAGE_LABEL_CLASSIFIED,
                    status=LOAD_ID_AUDIT_STATUS_PRESENT,
                    reason=LOAD_ID_AUDIT_REASON_UNKNOWN,
                    identifier_label_category=category,
                    candidate_count=1,
                )
            )
    for identifier_type, count in sorted(rejected_type_counts.items()):
        category = _category_for_identifier_type(identifier_type)
        for _ in range(_int(count)):
            records.append(
                build_load_identifier_coverage_record(
                    measurement_alias=alias,
                    stage=LOAD_ID_AUDIT_STAGE_NON_PRIMARY_REFERENCE_REJECTED,
                    status=LOAD_ID_AUDIT_STATUS_REJECTED,
                    reason=LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES,
                    identifier_label_category=category,
                    candidate_count=1,
                    typed_reference_count=1,
                    rejected_non_primary_count=1,
                )
            )
    if conflict_count:
        records.append(
            build_load_identifier_coverage_record(
                measurement_alias=alias,
                stage=LOAD_ID_AUDIT_STAGE_CORE_LOAD_NUMBER_MAPPED,
                status=LOAD_ID_AUDIT_STATUS_CONFLICT,
                reason=LOAD_ID_AUDIT_REASON_MULTIPLE_PRIMARY_CONFLICT,
                primary_candidate_count=primary_count,
            )
        )
    elif core_mapping_count:
        records.append(
            build_load_identifier_coverage_record(
                measurement_alias=alias,
                stage=LOAD_ID_AUDIT_STAGE_CORE_LOAD_NUMBER_MAPPED,
                status=LOAD_ID_AUDIT_STATUS_PRESENT,
                reason=LOAD_ID_AUDIT_REASON_UNKNOWN,
                primary_candidate_count=primary_count,
                core_mapping_count=core_mapping_count,
            )
        )
    elif primary_count:
        records.append(
            build_load_identifier_coverage_record(
                measurement_alias=alias,
                stage=LOAD_ID_AUDIT_STAGE_CORE_LOAD_NUMBER_MAPPED,
                status=LOAD_ID_AUDIT_STATUS_MISSING,
                reason=LOAD_ID_AUDIT_REASON_PRIMARY_NOT_CORE_MAPPED,
                primary_candidate_count=primary_count,
            )
        )
    elif label_count and rejected_count:
        records.append(
            build_load_identifier_coverage_record(
                measurement_alias=alias,
                stage=LOAD_ID_AUDIT_STAGE_PRIMARY_CANDIDATE_CLASSIFIED,
                status=LOAD_ID_AUDIT_STATUS_MISSING,
                reason=LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES,
                candidate_count=label_count,
            )
        )
    elif label_count:
        records.append(
            build_load_identifier_coverage_record(
                measurement_alias=alias,
                stage=LOAD_ID_AUDIT_STAGE_PRIMARY_CANDIDATE_CLASSIFIED,
                status=LOAD_ID_AUDIT_STATUS_MISSING,
                reason=LOAD_ID_AUDIT_REASON_PRIMARY_NOT_GENERATED,
                candidate_count=label_count,
            )
        )
    return records


def analyze_load_identifier_coverage_from_rows(measurement_rows):
    records = []
    for row in measurement_rows or []:
        if not isinstance(row, dict):
            continue
        audit_records = row.get("load_identifier_audit_records", []) or []
        if audit_records:
            records.extend(
                build_load_identifier_coverage_record(**record)
                for record in audit_records
                if isinstance(record, dict)
            )
        else:
            records.extend(_records_from_metrics(row))
    return build_load_identifier_coverage_result(
        records,
        document_count=len(measurement_rows or []),
    )


def analyze_load_identifier_coverage(input_dir=None):
    root = Path(input_dir or DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR)
    artifact = _read_json(root / LOAD_IDENTIFIER_COVERAGE_JSON, default=None)
    if isinstance(artifact, dict) and "records" in artifact and "aggregate" in artifact:
        return build_load_identifier_coverage_result(
            artifact.get("records", []),
            document_count=(artifact.get("aggregate", {}) or {}).get("document_count", 0),
        )
    if not (root / "safe_summary.json").exists():
        raise LocalReviewAnalysisError("missing safe_summary.json")
    return analyze_load_identifier_coverage_from_rows(_safe_summary_rows(root))


def load_identifier_coverage_markdown_lines(analysis):
    aggregate = (analysis or {}).get("aggregate", {})
    lines = [
        "# Load Identifier Coverage Audit",
        "",
        "Local-only analysis. Safe to share: aliases, counts, statuses, and label categories.",
        "Do not share private values, raw text, filenames, local paths, rates, addresses, references, or broker identifiers.",
        "",
        f"Documents analyzed: {aggregate.get('document_count', 0)}",
        f"Recommended next fix: {aggregate.get('recommended_next_fix', 'local_human_review')}",
        "",
        "## Counts",
        f"- primary candidates: {aggregate.get('primary_candidate_count', 0)}",
        f"- typed references: {aggregate.get('typed_reference_count', 0)}",
        f"- rejected non-primary references: {aggregate.get('rejected_non_primary_count', 0)}",
        f"- core mappings: {aggregate.get('core_mapping_count', 0)}",
        "",
        "## Reasons",
    ]
    for reason, count in (aggregate.get("records_by_reason", {}) or {}).items():
        lines.append(f"- {reason}: {count}")
    lines.extend(["", "## Label Categories"])
    for category, count in (
        aggregate.get("records_by_label_category", {}) or {}
    ).items():
        lines.append(f"- {category}: {count}")
    return lines


def write_load_identifier_coverage_json(analysis, output_path):
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
    }


def write_load_identifier_coverage_md(analysis, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(load_identifier_coverage_markdown_lines(analysis)) + "\n",
        encoding="utf-8",
    )
    return {
        "md": path.name,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def write_load_identifier_coverage_artifacts(
    analysis,
    output_dir=None,
    allow_custom_output_dir=False,
):
    output_root = _normalize_output_dir(
        output_dir or DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    json_result = write_load_identifier_coverage_json(
        analysis,
        output_root / LOAD_IDENTIFIER_COVERAGE_JSON,
    )
    md_result = write_load_identifier_coverage_md(
        analysis,
        output_root / LOAD_IDENTIFIER_COVERAGE_MD,
    )
    return {
        "paths": {
            "load_identifier_coverage_json": output_root
            / LOAD_IDENTIFIER_COVERAGE_JSON,
            "load_identifier_coverage_md": output_root / LOAD_IDENTIFIER_COVERAGE_MD,
        },
        "aggregate": (analysis or {}).get("aggregate", {}),
        "private_values_printed": bool(
            json_result.get("private_values_printed")
            or md_result.get("private_values_printed")
        ),
        "raw_text_printed": bool(
            json_result.get("raw_text_printed")
            or md_result.get("raw_text_printed")
        ),
    }
