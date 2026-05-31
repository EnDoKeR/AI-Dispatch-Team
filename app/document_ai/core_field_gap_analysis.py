"""Safe core-field gap analysis contracts and local-output analyzer.

This module summarizes local review-output gaps by field, reason, and readiness
level. It must not expose private review values.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

from app.document_ai.local_review_analysis import (
    LocalReviewAnalysisError,
    load_document_summary_csv,
    load_field_review_csv,
    load_rate_review_csv,
    load_stop_review_csv,
)
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)
from app.document_ai.ratecon_candidates import normalize_list
from app.document_ai.ratecon_review_workbook import (
    REVIEW_DOCUMENT_SUMMARY_CSV,
    REVIEW_FIELD_REVIEW_CSV,
    REVIEW_RATE_REVIEW_CSV,
    REVIEW_STOP_REVIEW_CSV,
)


CORE_FIELD_BROKER_NAME = "broker_name"
CORE_FIELD_BROKER_MC = "broker_mc"
CORE_FIELD_LOAD_NUMBER = "load_number"
CORE_FIELD_RATE = "rate"
CORE_FIELD_PICKUP_LOCATION = "pickup_location"
CORE_FIELD_PICKUP_DATE = "pickup_date"
CORE_FIELD_PICKUP_TIME = "pickup_time"
CORE_FIELD_DELIVERY_LOCATION = "delivery_location"
CORE_FIELD_DELIVERY_DATE = "delivery_date"
CORE_FIELD_DELIVERY_TIME = "delivery_time"
CORE_FIELD_EQUIPMENT = "equipment"
CORE_FIELD_WEIGHT = "weight"
CORE_FIELD_COMMODITY = "commodity"
CORE_FIELD_SPECIAL_REQUIREMENT = "special_requirement"
CORE_FIELD_REFERENCE = "reference"
CORE_FIELD_UNKNOWN = "unknown"

CORE_FIELD_NAMES = {
    CORE_FIELD_BROKER_NAME,
    CORE_FIELD_BROKER_MC,
    CORE_FIELD_LOAD_NUMBER,
    CORE_FIELD_RATE,
    CORE_FIELD_PICKUP_LOCATION,
    CORE_FIELD_PICKUP_DATE,
    CORE_FIELD_PICKUP_TIME,
    CORE_FIELD_DELIVERY_LOCATION,
    CORE_FIELD_DELIVERY_DATE,
    CORE_FIELD_DELIVERY_TIME,
    CORE_FIELD_EQUIPMENT,
    CORE_FIELD_WEIGHT,
    CORE_FIELD_COMMODITY,
    CORE_FIELD_SPECIAL_REQUIREMENT,
    CORE_FIELD_REFERENCE,
    CORE_FIELD_UNKNOWN,
}

CORE_FIELD_GAP_NO_CANDIDATE = "no_candidate"
CORE_FIELD_GAP_CANDIDATE_EXISTS_BUT_UNRESOLVED = "candidate_exists_but_unresolved"
CORE_FIELD_GAP_CONFLICT = "conflict"
CORE_FIELD_GAP_LOW_CONFIDENCE = "low_confidence"
CORE_FIELD_GAP_SCOPE_FILTERED = "scope_filtered"
CORE_FIELD_GAP_OPTIONAL_MISCLASSIFIED = "optional_field_misclassified_as_core"
CORE_FIELD_GAP_NON_APPLICABLE = "non_applicable"
CORE_FIELD_GAP_OCR_NEEDED = "ocr_needed"
CORE_FIELD_GAP_REVIEW_REQUIRED = "review_required"
CORE_FIELD_GAP_UNKNOWN = "unknown"

CORE_FIELD_GAP_REASONS = {
    CORE_FIELD_GAP_NO_CANDIDATE,
    CORE_FIELD_GAP_CANDIDATE_EXISTS_BUT_UNRESOLVED,
    CORE_FIELD_GAP_CONFLICT,
    CORE_FIELD_GAP_LOW_CONFIDENCE,
    CORE_FIELD_GAP_SCOPE_FILTERED,
    CORE_FIELD_GAP_OPTIONAL_MISCLASSIFIED,
    CORE_FIELD_GAP_NON_APPLICABLE,
    CORE_FIELD_GAP_OCR_NEEDED,
    CORE_FIELD_GAP_REVIEW_REQUIRED,
    CORE_FIELD_GAP_UNKNOWN,
}

CORE_FIELD_GAP_ANALYSIS_VERSION = "core_field_gap_analysis_v1"
CORE_FIELD_GAP_ANALYSIS_MD = "core_field_gap_analysis.md"
CORE_FIELD_GAP_ANALYSIS_JSON = "core_field_gap_analysis.json"

INTAKE_CORE_FIELDS = {
    CORE_FIELD_BROKER_NAME,
    CORE_FIELD_LOAD_NUMBER,
    CORE_FIELD_RATE,
    CORE_FIELD_PICKUP_LOCATION,
    CORE_FIELD_PICKUP_DATE,
    CORE_FIELD_DELIVERY_LOCATION,
    CORE_FIELD_DELIVERY_DATE,
}

DISPATCH_DECISION_FIELDS = {
    CORE_FIELD_BROKER_NAME,
    CORE_FIELD_BROKER_MC,
    CORE_FIELD_LOAD_NUMBER,
    CORE_FIELD_RATE,
    CORE_FIELD_PICKUP_LOCATION,
    CORE_FIELD_PICKUP_DATE,
    CORE_FIELD_PICKUP_TIME,
    CORE_FIELD_DELIVERY_LOCATION,
    CORE_FIELD_DELIVERY_DATE,
    CORE_FIELD_DELIVERY_TIME,
    CORE_FIELD_EQUIPMENT,
    CORE_FIELD_WEIGHT,
    CORE_FIELD_COMMODITY,
    CORE_FIELD_SPECIAL_REQUIREMENT,
}

OPTIONAL_FOR_INTAKE_CORE = {
    CORE_FIELD_BROKER_MC,
    CORE_FIELD_PICKUP_TIME,
    CORE_FIELD_DELIVERY_TIME,
    CORE_FIELD_EQUIPMENT,
    CORE_FIELD_WEIGHT,
    CORE_FIELD_COMMODITY,
    CORE_FIELD_SPECIAL_REQUIREMENT,
    CORE_FIELD_REFERENCE,
}

ACTIONABLE_STATUSES = {
    "missing",
    "conflict",
    "low_confidence",
    "needs_review",
    "review_required",
}

TARGET_PRIORITY = [
    "broker_load_identity_extraction",
    "load_identifier_extraction",
    "rate_resolution_hardening",
    "stop_span_field_mapping",
    "local_human_review",
]


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _boolish(value):
    return _token(value) in {"1", "true", "yes", "y"}


def normalize_core_field_name(value):
    token = _token(value)
    return token if token in CORE_FIELD_NAMES else CORE_FIELD_UNKNOWN


def normalize_core_field_gap_reason(value):
    token = _token(value)
    return token if token in CORE_FIELD_GAP_REASONS else CORE_FIELD_GAP_UNKNOWN


def recommended_fix_bucket_for_field(field_name, gap_reason=CORE_FIELD_GAP_UNKNOWN):
    field = normalize_core_field_name(field_name)
    reason = normalize_core_field_gap_reason(gap_reason)
    if field in {CORE_FIELD_BROKER_NAME, CORE_FIELD_BROKER_MC}:
        return "broker_load_identity_extraction"
    if field in {CORE_FIELD_LOAD_NUMBER, CORE_FIELD_REFERENCE}:
        return "load_identifier_extraction"
    if field == CORE_FIELD_RATE:
        return "rate_resolution_hardening"
    if field in {
        CORE_FIELD_PICKUP_LOCATION,
        CORE_FIELD_PICKUP_DATE,
        CORE_FIELD_PICKUP_TIME,
        CORE_FIELD_DELIVERY_LOCATION,
        CORE_FIELD_DELIVERY_DATE,
        CORE_FIELD_DELIVERY_TIME,
    }:
        return "stop_span_field_mapping"
    if reason == CORE_FIELD_GAP_OCR_NEEDED:
        return "ocr_queue"
    return "local_human_review"


def classify_gap_reason(status, candidate_count=0, document_row=None, field_name=""):
    status_token = _token(status)
    field = normalize_core_field_name(field_name)
    if _boolish((document_row or {}).get("OCR Needed")):
        return CORE_FIELD_GAP_OCR_NEEDED
    if status_token in {"not_applicable", "non_applicable"}:
        return CORE_FIELD_GAP_NON_APPLICABLE
    if field in OPTIONAL_FOR_INTAKE_CORE and status_token == "missing":
        return CORE_FIELD_GAP_OPTIONAL_MISCLASSIFIED
    if status_token == "conflict":
        return CORE_FIELD_GAP_CONFLICT
    if status_token == "low_confidence":
        return CORE_FIELD_GAP_LOW_CONFIDENCE
    if status_token in {"needs_review", "review_required"}:
        return CORE_FIELD_GAP_REVIEW_REQUIRED
    if status_token == "missing":
        return (
            CORE_FIELD_GAP_CANDIDATE_EXISTS_BUT_UNRESOLVED
            if _int(candidate_count) > 0
            else CORE_FIELD_GAP_NO_CANDIDATE
        )
    return CORE_FIELD_GAP_UNKNOWN


def classify_readiness_blockers(field_name, gap_reason):
    field = normalize_core_field_name(field_name)
    reason = normalize_core_field_gap_reason(gap_reason)
    if reason in {CORE_FIELD_GAP_NON_APPLICABLE, CORE_FIELD_GAP_OCR_NEEDED}:
        return {
            "extraction_review_blocker": reason == CORE_FIELD_GAP_OCR_NEEDED,
            "intake_core_blocker": False,
            "dispatch_decision_blocker": False,
        }
    intake_core_blocker = field in INTAKE_CORE_FIELDS
    dispatch_decision_blocker = field in DISPATCH_DECISION_FIELDS
    return {
        "extraction_review_blocker": False,
        "intake_core_blocker": intake_core_blocker,
        "dispatch_decision_blocker": dispatch_decision_blocker,
    }


def build_core_field_gap_record(
    measurement_alias="",
    field_name=CORE_FIELD_UNKNOWN,
    status="",
    gap_reason=CORE_FIELD_GAP_UNKNOWN,
    candidate_count=0,
    conflict_count=0,
    confidence_bucket="",
    readiness_blocker=False,
    extraction_review_blocker=False,
    intake_core_blocker=False,
    dispatch_decision_blocker=False,
    warning_codes=None,
    recommended_fix_bucket="",
    safe_notes=None,
):
    field = normalize_core_field_name(field_name)
    reason = normalize_core_field_gap_reason(gap_reason)
    return {
        "measurement_alias": _text(measurement_alias),
        "field_name": field,
        "status": _token(status),
        "gap_reason": reason,
        "candidate_count": _int(candidate_count),
        "conflict_count": _int(conflict_count),
        "confidence_bucket": _token(confidence_bucket),
        "readiness_blocker": bool(readiness_blocker),
        "extraction_review_blocker": bool(extraction_review_blocker),
        "intake_core_blocker": bool(intake_core_blocker),
        "dispatch_decision_blocker": bool(dispatch_decision_blocker),
        "warning_codes": normalize_list(warning_codes),
        "recommended_fix_bucket": _text(recommended_fix_bucket)
        or recommended_fix_bucket_for_field(field, reason),
        "safe_notes": normalize_list(safe_notes),
    }


def _rows_by_alias(rows, alias_key="Measurement Alias"):
    return {
        _text(row.get(alias_key)): row
        for row in rows or []
        if isinstance(row, dict) and _text(row.get(alias_key))
    }


def _safe_summary_by_alias(rows):
    return {
        _text(row.get("document_alias")): row
        for row in rows or []
        if isinstance(row, dict) and _text(row.get("document_alias"))
    }


def _field_status_index(safe_summary_rows):
    indexed = {}
    for row in safe_summary_rows or []:
        alias = _text(row.get("document_alias"))
        if not alias:
            continue
        for field in row.get("field_statuses", []) or []:
            if not isinstance(field, dict):
                continue
            field_name = normalize_core_field_name(field.get("field_name"))
            indexed[(alias, field_name)] = field
    return indexed


def _safe_summary_rows_from_path(path):
    summary_path = Path(path)
    if not summary_path.exists():
        return []
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    return [
        row
        for row in payload.get("rows", []) or []
        if isinstance(row, dict)
    ]


def load_core_field_gap_inputs(input_dir=DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR):
    root = Path(input_dir)
    return {
        "document_rows": load_document_summary_csv(root / REVIEW_DOCUMENT_SUMMARY_CSV),
        "stop_rows": load_stop_review_csv(root / REVIEW_STOP_REVIEW_CSV),
        "field_rows": load_field_review_csv(root / REVIEW_FIELD_REVIEW_CSV),
        "rate_rows": load_rate_review_csv(root / REVIEW_RATE_REVIEW_CSV),
        "safe_summary_rows": _safe_summary_rows_from_path(root / "safe_summary.json"),
    }


def _record_from_field_row(field_row, document_rows_by_alias, status_index):
    alias = _text(field_row.get("Measurement Alias"))
    field = normalize_core_field_name(field_row.get("Field Name"))
    status = _token(field_row.get("Status"))
    field_status = status_index.get((alias, field), {})
    candidate_count = _int(field_status.get("candidate_count"))
    if not candidate_count:
        candidate_count = _int((field_status or {}).get("candidate_count"))
    reason = classify_gap_reason(
        status,
        candidate_count=candidate_count,
        document_row=document_rows_by_alias.get(alias),
        field_name=field,
    )
    blockers = classify_readiness_blockers(field, reason)
    warnings = normalize_list((field_status or {}).get("warning_codes"))
    notes = normalize_list((field_status or {}).get("safe_reasons"))
    return build_core_field_gap_record(
        measurement_alias=alias,
        field_name=field,
        status=status,
        gap_reason=reason,
        candidate_count=candidate_count,
        conflict_count=1 if reason == CORE_FIELD_GAP_CONFLICT else 0,
        confidence_bucket=(field_status or {}).get("confidence_bucket")
        or field_row.get("Confidence Bucket"),
        readiness_blocker=any(blockers.values()),
        extraction_review_blocker=blockers["extraction_review_blocker"],
        intake_core_blocker=blockers["intake_core_blocker"],
        dispatch_decision_blocker=blockers["dispatch_decision_blocker"],
        warning_codes=warnings,
        safe_notes=notes,
    )


def _stop_field_to_core_field(stop_type, field_name):
    stop_type_token = _token(stop_type)
    field_token = _token(field_name)
    if field_token == "date":
        if stop_type_token == "pickup":
            return CORE_FIELD_PICKUP_DATE
        if stop_type_token == "delivery":
            return CORE_FIELD_DELIVERY_DATE
    if field_token == "time":
        if stop_type_token == "pickup":
            return CORE_FIELD_PICKUP_TIME
        if stop_type_token == "delivery":
            return CORE_FIELD_DELIVERY_TIME
    if field_token == "location":
        if stop_type_token == "pickup":
            return CORE_FIELD_PICKUP_LOCATION
        if stop_type_token == "delivery":
            return CORE_FIELD_DELIVERY_LOCATION
    if field_token == "reference":
        return CORE_FIELD_REFERENCE
    return CORE_FIELD_UNKNOWN


def _record_from_stop_row(stop_row, document_rows_by_alias):
    alias = _text(stop_row.get("Measurement Alias"))
    field = _stop_field_to_core_field(stop_row.get("Stop Type"), stop_row.get("Field Name"))
    if field == CORE_FIELD_UNKNOWN:
        return None
    status = _token(stop_row.get("Status"))
    reason = classify_gap_reason(
        status,
        candidate_count=1 if status in {"conflict", "needs_review", "review_required"} else 0,
        document_row=document_rows_by_alias.get(alias),
        field_name=field,
    )
    blockers = classify_readiness_blockers(field, reason)
    warnings = []
    if field in {CORE_FIELD_PICKUP_DATE, CORE_FIELD_DELIVERY_DATE, CORE_FIELD_PICKUP_TIME, CORE_FIELD_DELIVERY_TIME}:
        warnings.append("stop_review_field_gap")
    return build_core_field_gap_record(
        measurement_alias=alias,
        field_name=field,
        status=status,
        gap_reason=reason,
        candidate_count=0,
        conflict_count=1 if reason == CORE_FIELD_GAP_CONFLICT else 0,
        confidence_bucket=stop_row.get("Confidence Bucket"),
        readiness_blocker=any(blockers.values()),
        extraction_review_blocker=blockers["extraction_review_blocker"],
        intake_core_blocker=blockers["intake_core_blocker"],
        dispatch_decision_blocker=blockers["dispatch_decision_blocker"],
        warning_codes=warnings,
    )


def analyze_core_field_gaps_from_rows(
    document_rows,
    stop_rows=None,
    field_rows=None,
    rate_rows=None,
    safe_summary_rows=None,
):
    del rate_rows
    document_rows_by_alias = _rows_by_alias(document_rows)
    status_index = _field_status_index(safe_summary_rows)
    records = []

    for row in field_rows or []:
        status = _token(row.get("Status"))
        field = normalize_core_field_name(row.get("Field Name"))
        if field == CORE_FIELD_UNKNOWN or status not in ACTIONABLE_STATUSES:
            continue
        records.append(_record_from_field_row(row, document_rows_by_alias, status_index))

    field_record_keys = {
        (record["measurement_alias"], record["field_name"], record["status"])
        for record in records
    }
    for row in stop_rows or []:
        status = _token(row.get("Status"))
        if status not in ACTIONABLE_STATUSES:
            continue
        record = _record_from_stop_row(row, document_rows_by_alias)
        if not record:
            continue
        key = (record["measurement_alias"], record["field_name"], record["status"])
        # Keep stop-level gaps only when the field review sheet does not already
        # carry the same alias/field/status.
        if key in field_record_keys:
            continue
        records.append(record)

    return {
        "records": records,
        "aggregate": build_core_field_gap_aggregate(
            records,
            document_count=len(document_rows or []),
        ),
        "analysis_version": CORE_FIELD_GAP_ANALYSIS_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
    }


def analyze_core_field_gaps(input_dir=DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR):
    inputs = load_core_field_gap_inputs(input_dir)
    return analyze_core_field_gaps_from_rows(**inputs)


def core_field_gap_markdown_lines(analysis):
    aggregate = (analysis or {}).get("aggregate", {})
    lines = [
        "# Core Field Gap Analysis",
        "",
        "Local-only analysis. Safe to share: aliases, counts, statuses, field names, and gap reasons.",
        "Do not share private values, raw text, filenames, local paths, rates, addresses, references, or broker identifiers.",
        "",
        f"Documents analyzed: {aggregate.get('document_count', 0)}",
        f"Recommended next target: {aggregate.get('recommended_next_target', 'local_human_review')}",
        "",
        "## Top Core Field Gaps",
    ]
    for field_name in aggregate.get("top_core_field_gaps", []) or []:
        count = aggregate.get("gap_counts_by_field", {}).get(field_name, 0)
        lines.append(f"- {field_name}: {count}")
    lines.extend(["", "## Top Conflict Fields"])
    for field_name in aggregate.get("top_conflict_fields", []) or []:
        count = aggregate.get("gap_counts_by_field", {}).get(field_name, 0)
        lines.append(f"- {field_name}: {count}")
    lines.extend(["", "## Gap Reasons"])
    for reason, count in (aggregate.get("gap_counts_by_reason", {}) or {}).items():
        lines.append(f"- {reason}: {count}")
    lines.extend(["", "## Readiness Blockers"])
    for level, count in (
        aggregate.get("blocker_counts_by_readiness_level", {}) or {}
    ).items():
        lines.append(f"- {level}: {count}")
    lines.extend(["", "## Aliases By Top Field"])
    for field_name in (aggregate.get("top_core_field_gaps", []) or [])[:5]:
        aliases = aggregate.get("aliases_by_field", {}).get(field_name, [])
        lines.append(f"- {field_name}: {', '.join(aliases)}")
    return lines


def write_core_field_gap_analysis_json(analysis, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "json": path.name,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def write_core_field_gap_analysis_md(analysis, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(core_field_gap_markdown_lines(analysis)) + "\n", encoding="utf-8")
    return {
        "md": path.name,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _sorted_counter(counter):
    return {
        key: count
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    }


def _aliases_by(records, key_name):
    grouped = defaultdict(set)
    for record in records or []:
        alias = _text((record or {}).get("measurement_alias"))
        key = _text((record or {}).get(key_name))
        if alias and key:
            grouped[key].add(alias)
    return {key: sorted(values) for key, values in sorted(grouped.items())}


def _top_fix_bucket(records):
    actionable_records = [
        record
        for record in records or []
        if (record or {}).get("intake_core_blocker")
        and (record or {}).get("gap_reason")
        not in {
            CORE_FIELD_GAP_OPTIONAL_MISCLASSIFIED,
            CORE_FIELD_GAP_NON_APPLICABLE,
            CORE_FIELD_GAP_OCR_NEEDED,
        }
    ]
    records_for_target = actionable_records or [
        record
        for record in records or []
        if (record or {}).get("gap_reason")
        not in {
            CORE_FIELD_GAP_OPTIONAL_MISCLASSIFIED,
            CORE_FIELD_GAP_NON_APPLICABLE,
            CORE_FIELD_GAP_OCR_NEEDED,
        }
    ]
    counts = Counter(
        (record or {}).get("recommended_fix_bucket", "local_human_review")
        for record in records_for_target
    )
    if not counts:
        return "local_human_review"
    priority = {bucket: index for index, bucket in enumerate(TARGET_PRIORITY)}
    return sorted(
        counts.items(),
        key=lambda item: (-item[1], priority.get(item[0], len(priority)), item[0]),
    )[0][0]


def build_core_field_gap_aggregate(records, document_count=0):
    normalized_records = [
        build_core_field_gap_record(**record)
        if isinstance(record, dict)
        else build_core_field_gap_record()
        for record in records or []
    ]
    gap_counts_by_field = Counter(record["field_name"] for record in normalized_records)
    gap_counts_by_reason = Counter(record["gap_reason"] for record in normalized_records)
    blocker_counts_by_readiness_level = Counter()
    for record in normalized_records:
        if record["extraction_review_blocker"]:
            blocker_counts_by_readiness_level["extraction_review"] += 1
        if record["intake_core_blocker"]:
            blocker_counts_by_readiness_level["intake_core"] += 1
        if record["dispatch_decision_blocker"]:
            blocker_counts_by_readiness_level["dispatch_decision"] += 1

    conflict_fields = Counter(
        record["field_name"]
        for record in normalized_records
        if record["gap_reason"] == CORE_FIELD_GAP_CONFLICT
    )
    top_core_field_gaps = list(_sorted_counter(gap_counts_by_field).keys())[:10]
    top_conflict_fields = list(_sorted_counter(conflict_fields).keys())[:10]

    return {
        "document_count": _int(document_count),
        "gap_counts_by_field": _sorted_counter(gap_counts_by_field),
        "gap_counts_by_reason": _sorted_counter(gap_counts_by_reason),
        "blocker_counts_by_readiness_level": _sorted_counter(
            blocker_counts_by_readiness_level
        ),
        "aliases_by_field": _aliases_by(normalized_records, "field_name"),
        "aliases_by_reason": _aliases_by(normalized_records, "gap_reason"),
        "top_core_field_gaps": top_core_field_gaps,
        "top_conflict_fields": top_conflict_fields,
        "recommended_next_target": _top_fix_bucket(normalized_records),
        "analysis_version": CORE_FIELD_GAP_ANALYSIS_VERSION,
    }
