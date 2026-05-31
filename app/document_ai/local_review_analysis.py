"""Safe local RateCon review-output analysis.

This module reads local-only review CSV rows and summarizes aliases, counts,
statuses, and field names. It must not expose private values from review rows.
"""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)
from app.document_ai.ratecon_review_workbook import (
    DOCUMENT_SUMMARY_COLUMNS,
    FIELD_REVIEW_COLUMNS,
    RATE_REVIEW_COLUMNS,
    REVIEW_DOCUMENT_SUMMARY_CSV,
    REVIEW_FIELD_REVIEW_CSV,
    REVIEW_RATE_REVIEW_CSV,
    REVIEW_STOP_REVIEW_CSV,
    STOP_REVIEW_COLUMNS,
)


LOCAL_REVIEW_ISSUE_MISSING_CORE_FIELD = "missing_core_field"
LOCAL_REVIEW_ISSUE_UNRESOLVED_CORE_FIELD = "unresolved_core_field"
LOCAL_REVIEW_ISSUE_CONFLICT_CORE_FIELD = "conflict_core_field"
LOCAL_REVIEW_ISSUE_LOW_CONFIDENCE_CORE_FIELD = "low_confidence_core_field"
LOCAL_REVIEW_ISSUE_EXTRA_STOP = "extra_stop"
LOCAL_REVIEW_ISSUE_DUPLICATE_STOP = "duplicate_stop"
LOCAL_REVIEW_ISSUE_MISSING_STOP_DATE = "missing_stop_date"
LOCAL_REVIEW_ISSUE_MISSING_STOP_TIME = "missing_stop_time"
LOCAL_REVIEW_ISSUE_AMBIGUOUS_STOP_TYPE = "ambiguous_stop_type"
LOCAL_REVIEW_ISSUE_RATE_CONFLICT = "rate_conflict"
LOCAL_REVIEW_ISSUE_RATE_MISSING = "rate_missing"
LOCAL_REVIEW_ISSUE_BROKER_IDENTITY_MISSING = "broker_identity_missing"
LOCAL_REVIEW_ISSUE_LOAD_NUMBER_MISSING = "load_number_missing"
LOCAL_REVIEW_ISSUE_EQUIPMENT_MISSING = "equipment_missing"
LOCAL_REVIEW_ISSUE_WEIGHT_MISSING = "weight_missing"
LOCAL_REVIEW_ISSUE_COMMODITY_MISSING = "commodity_missing"
LOCAL_REVIEW_ISSUE_OCR_NEEDED = "ocr_needed"
LOCAL_REVIEW_ISSUE_INTEGRITY = "integrity_issue"
LOCAL_REVIEW_ISSUE_NOT_READY = "not_ready"
LOCAL_REVIEW_ISSUE_UNKNOWN = "unknown"

LOCAL_REVIEW_ISSUE_CATEGORIES = {
    LOCAL_REVIEW_ISSUE_MISSING_CORE_FIELD,
    LOCAL_REVIEW_ISSUE_UNRESOLVED_CORE_FIELD,
    LOCAL_REVIEW_ISSUE_CONFLICT_CORE_FIELD,
    LOCAL_REVIEW_ISSUE_LOW_CONFIDENCE_CORE_FIELD,
    LOCAL_REVIEW_ISSUE_EXTRA_STOP,
    LOCAL_REVIEW_ISSUE_DUPLICATE_STOP,
    LOCAL_REVIEW_ISSUE_MISSING_STOP_DATE,
    LOCAL_REVIEW_ISSUE_MISSING_STOP_TIME,
    LOCAL_REVIEW_ISSUE_AMBIGUOUS_STOP_TYPE,
    LOCAL_REVIEW_ISSUE_RATE_CONFLICT,
    LOCAL_REVIEW_ISSUE_RATE_MISSING,
    LOCAL_REVIEW_ISSUE_BROKER_IDENTITY_MISSING,
    LOCAL_REVIEW_ISSUE_LOAD_NUMBER_MISSING,
    LOCAL_REVIEW_ISSUE_EQUIPMENT_MISSING,
    LOCAL_REVIEW_ISSUE_WEIGHT_MISSING,
    LOCAL_REVIEW_ISSUE_COMMODITY_MISSING,
    LOCAL_REVIEW_ISSUE_OCR_NEEDED,
    LOCAL_REVIEW_ISSUE_INTEGRITY,
    LOCAL_REVIEW_ISSUE_NOT_READY,
    LOCAL_REVIEW_ISSUE_UNKNOWN,
}

CORE_FIELD_NAMES = {
    "broker_name",
    "broker_mc",
    "load_number",
    "rate",
    "pickup_location",
    "pickup_date",
    "delivery_location",
    "delivery_date",
    "equipment",
    "weight",
    "commodity",
}

PRIVATE_VALUE_COLUMNS = {
    "Predicted Value LOCAL ONLY",
    "User Expected Value LOCAL ONLY",
    "User Notes Local Only",
}

LOCAL_REVIEW_ANALYSIS_VERSION = "local_review_analysis_v1"
LOCAL_REVIEW_ANALYSIS_MD = "local_review_analysis.md"
LOCAL_REVIEW_ANALYSIS_JSON = "local_review_analysis.json"


class LocalReviewAnalysisError(ValueError):
    """Raised when local review CSVs are missing or stale."""


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


def _split_codes(value):
    raw = _text(value)
    if not raw:
        return []
    normalized = raw.replace(",", ";")
    return [part.strip() for part in normalized.split(";") if part.strip()]


def _safe_row(row):
    return {
        key: value
        for key, value in dict(row or {}).items()
        if key not in PRIVATE_VALUE_COLUMNS
    }


def _load_csv(path, required_columns):
    csv_path = Path(path)
    if not csv_path.exists():
        raise LocalReviewAnalysisError(f"review CSV missing: {csv_path.name}")
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        missing = [column for column in required_columns if column not in fieldnames]
        if missing:
            raise LocalReviewAnalysisError(
                f"review CSV stale or invalid: {csv_path.name}"
            )
        return [_safe_row(row) for row in reader]


def load_document_summary_csv(path):
    return _load_csv(path, DOCUMENT_SUMMARY_COLUMNS)


def load_stop_review_csv(path):
    return _load_csv(path, STOP_REVIEW_COLUMNS)


def load_field_review_csv(path):
    return _load_csv(path, FIELD_REVIEW_COLUMNS)


def load_rate_review_csv(path):
    return _load_csv(path, RATE_REVIEW_COLUMNS)


def _field_specific_issue(field_name, status):
    field = _token(field_name)
    status_token = _token(status)
    if status_token not in {"missing", "conflict", "low_confidence", "needs_review"}:
        return ""
    if field in {"broker_name", "broker_mc"} and status_token == "missing":
        return LOCAL_REVIEW_ISSUE_BROKER_IDENTITY_MISSING
    if field == "load_number" and status_token == "missing":
        return LOCAL_REVIEW_ISSUE_LOAD_NUMBER_MISSING
    if field == "rate":
        if status_token == "missing":
            return LOCAL_REVIEW_ISSUE_RATE_MISSING
        if status_token == "conflict":
            return LOCAL_REVIEW_ISSUE_RATE_CONFLICT
    if field == "equipment" and status_token == "missing":
        return LOCAL_REVIEW_ISSUE_EQUIPMENT_MISSING
    if field == "weight" and status_token == "missing":
        return LOCAL_REVIEW_ISSUE_WEIGHT_MISSING
    if field == "commodity" and status_token == "missing":
        return LOCAL_REVIEW_ISSUE_COMMODITY_MISSING
    return ""


def _core_issue_for_status(status):
    token = _token(status)
    if token == "missing":
        return LOCAL_REVIEW_ISSUE_MISSING_CORE_FIELD
    if token in {"needs_review", "review_required"}:
        return LOCAL_REVIEW_ISSUE_UNRESOLVED_CORE_FIELD
    if token == "conflict":
        return LOCAL_REVIEW_ISSUE_CONFLICT_CORE_FIELD
    if token == "low_confidence":
        return LOCAL_REVIEW_ISSUE_LOW_CONFIDENCE_CORE_FIELD
    return ""


def _recommended_fix_bucket(issue_categories):
    categories = set(issue_categories or [])
    if (
        LOCAL_REVIEW_ISSUE_MISSING_STOP_DATE in categories
        or LOCAL_REVIEW_ISSUE_MISSING_STOP_TIME in categories
    ):
        return "stop_span_datetime"
    if (
        LOCAL_REVIEW_ISSUE_EXTRA_STOP in categories
        or LOCAL_REVIEW_ISSUE_DUPLICATE_STOP in categories
    ):
        return "stop_span_boundary_dedupe"
    if (
        LOCAL_REVIEW_ISSUE_RATE_CONFLICT in categories
        or LOCAL_REVIEW_ISSUE_RATE_MISSING in categories
    ):
        return "rate_review_hardening"
    if LOCAL_REVIEW_ISSUE_BROKER_IDENTITY_MISSING in categories:
        return "broker_identity_extraction"
    if LOCAL_REVIEW_ISSUE_LOAD_NUMBER_MISSING in categories:
        return "load_identifier_extraction"
    if LOCAL_REVIEW_ISSUE_OCR_NEEDED in categories:
        return "ocr_queue"
    return "local_human_review"


def build_alias_summaries(
    document_rows,
    stop_rows,
    field_rows,
    rate_rows,
    include_local_document_names=False,
):
    aliases = {}
    for row in document_rows or []:
        alias = _text(row.get("Measurement Alias"))
        if not alias:
            continue
        issues = set()
        warning_codes = []
        if _boolish(row.get("OCR Needed")):
            issues.add(LOCAL_REVIEW_ISSUE_OCR_NEEDED)
        if _token(row.get("Readiness Level")) == "not_ready":
            issues.add(LOCAL_REVIEW_ISSUE_NOT_READY)
        if _int(row.get("Date Missing")):
            issues.add(LOCAL_REVIEW_ISSUE_MISSING_STOP_DATE)
        if _int(row.get("Time Missing")):
            issues.add(LOCAL_REVIEW_ISSUE_MISSING_STOP_TIME)
        if _int(row.get("Unknown Count")) or _int(row.get("Generic Stop Count")):
            issues.add(LOCAL_REVIEW_ISSUE_AMBIGUOUS_STOP_TYPE)
        if _int(row.get("Old Normalized Stops")) > _int(row.get("Span Normalized Stops")):
            issues.add(LOCAL_REVIEW_ISSUE_EXTRA_STOP)
        integrity = _split_codes(row.get("Integrity Issues"))
        if integrity:
            issues.add(LOCAL_REVIEW_ISSUE_INTEGRITY)
            warning_codes.extend(integrity)

        aliases[alias] = {
            "measurement_alias": alias,
            "document_type": _text(row.get("Document Type")),
            "readiness_level": _token(row.get("Readiness Level")) or "unknown",
            "extraction_relevant": _boolish(row.get("Extraction Relevant")),
            "normal_load_movement": _boolish(row.get("Normal Load Movement")),
            "ocr_needed": _boolish(row.get("OCR Needed")),
            "old_normalized_stops": _int(row.get("Old Normalized Stops")),
            "span_normalized_stops": _int(row.get("Span Normalized Stops")),
            "stop_review_required_count": _int(row.get("Review Required Stops")),
            "missing_fields": [],
            "unresolved_fields": [],
            "conflict_fields": [],
            "low_confidence_fields": [],
            "issue_categories": sorted(issues),
            "recommended_fix_bucket": "",
            "warning_codes": sorted(set(warning_codes)),
        }
        if include_local_document_names:
            aliases[alias]["local_document_name"] = _text(
                row.get("Local Document Name / File Stem")
            )

    for row in field_rows or []:
        alias = _text(row.get("Measurement Alias"))
        if not alias:
            continue
        summary = aliases.setdefault(
            alias,
            {
                "measurement_alias": alias,
                "readiness_level": "unknown",
                "extraction_relevant": False,
                "normal_load_movement": False,
                "ocr_needed": False,
                "old_normalized_stops": 0,
                "span_normalized_stops": 0,
                "stop_review_required_count": 0,
                "missing_fields": [],
                "unresolved_fields": [],
                "conflict_fields": [],
                "low_confidence_fields": [],
                "issue_categories": [],
                "recommended_fix_bucket": "",
                "warning_codes": [],
            },
        )
        field_name = _token(row.get("Field Name"))
        status = _token(row.get("Status"))
        issues = set(summary.get("issue_categories", []))
        if field_name in CORE_FIELD_NAMES:
            core_issue = _core_issue_for_status(status)
            if core_issue:
                issues.add(core_issue)
            if status == "missing":
                summary["missing_fields"].append(field_name)
            elif status in {"needs_review", "review_required"}:
                summary["unresolved_fields"].append(field_name)
            elif status == "conflict":
                summary["conflict_fields"].append(field_name)
            elif status == "low_confidence":
                summary["low_confidence_fields"].append(field_name)
        specific = _field_specific_issue(field_name, status)
        if specific:
            issues.add(specific)
        summary["issue_categories"] = sorted(issues)

    for row in stop_rows or []:
        alias = _text(row.get("Measurement Alias"))
        if not alias:
            continue
        summary = aliases.setdefault(alias, {"measurement_alias": alias})
        issues = set(summary.get("issue_categories", []))
        field_name = _token(row.get("Field Name"))
        status = _token(row.get("Status"))
        if field_name == "date" and status == "missing":
            issues.add(LOCAL_REVIEW_ISSUE_MISSING_STOP_DATE)
        if field_name in {"time", "appointment_window"} and status == "missing":
            issues.add(LOCAL_REVIEW_ISSUE_MISSING_STOP_TIME)
        if _token(row.get("Stop Type")) in {"unknown", "stop"}:
            issues.add(LOCAL_REVIEW_ISSUE_AMBIGUOUS_STOP_TYPE)
        if _text(row.get("Integrity Issue")):
            issues.add(LOCAL_REVIEW_ISSUE_INTEGRITY)
        summary["issue_categories"] = sorted(issues)

    for row in rate_rows or []:
        alias = _text(row.get("Measurement Alias"))
        if not alias:
            continue
        summary = aliases.setdefault(alias, {"measurement_alias": alias})
        issues = set(summary.get("issue_categories", []))
        status = _token(row.get("Status"))
        if status == "missing":
            issues.add(LOCAL_REVIEW_ISSUE_RATE_MISSING)
        elif status == "conflict":
            issues.add(LOCAL_REVIEW_ISSUE_RATE_CONFLICT)
        summary["issue_categories"] = sorted(issues)

    for summary in aliases.values():
        summary["missing_fields"] = sorted(set(summary.get("missing_fields", [])))
        summary["unresolved_fields"] = sorted(set(summary.get("unresolved_fields", [])))
        summary["conflict_fields"] = sorted(set(summary.get("conflict_fields", [])))
        summary["low_confidence_fields"] = sorted(set(summary.get("low_confidence_fields", [])))
        summary["issue_categories"] = sorted(set(summary.get("issue_categories", [])))
        summary["recommended_fix_bucket"] = _recommended_fix_bucket(
            summary["issue_categories"]
        )
        summary.setdefault("document_type", "")
        summary.setdefault("warning_codes", [])
    return [aliases[key] for key in sorted(aliases)]


def build_local_review_aggregate(alias_summaries, stop_rows=None, field_rows=None, rate_rows=None):
    readiness_counts = Counter()
    issue_counts = Counter()
    field_issue_counts = Counter()
    stop_issue_counts = Counter()
    rate_issue_counts = Counter()
    aliases_by_issue = defaultdict(list)

    for summary in alias_summaries or []:
        readiness_counts[_token(summary.get("readiness_level")) or "unknown"] += 1
        for category in summary.get("issue_categories", []):
            aliases_by_issue[category].append(summary.get("measurement_alias", ""))
        for category in summary.get("issue_categories", []):
            if category in {
                LOCAL_REVIEW_ISSUE_OCR_NEEDED,
                LOCAL_REVIEW_ISSUE_NOT_READY,
                LOCAL_REVIEW_ISSUE_INTEGRITY,
                LOCAL_REVIEW_ISSUE_EXTRA_STOP,
                LOCAL_REVIEW_ISSUE_AMBIGUOUS_STOP_TYPE,
            }:
                issue_counts[category] += 1

    for row in field_rows or []:
        field = _token(row.get("Field Name"))
        status = _token(row.get("Status"))
        if status in {
            "missing",
            "needs_review",
            "review_required",
            "conflict",
            "low_confidence",
        }:
            field_issue_counts[field] += 1
        if field in CORE_FIELD_NAMES:
            core_issue = _core_issue_for_status(status)
            if core_issue:
                issue_counts[core_issue] += 1
            specific = _field_specific_issue(field, status)
            if specific:
                issue_counts[specific] += 1

    for row in stop_rows or []:
        field = _token(row.get("Field Name"))
        status = _token(row.get("Status"))
        if status in {"missing", "conflict", "low_confidence"}:
            stop_issue_counts[field] += 1
        if field == "date" and status == "missing":
            issue_counts[LOCAL_REVIEW_ISSUE_MISSING_STOP_DATE] += 1
        if field in {"time", "appointment_window"} and status == "missing":
            issue_counts[LOCAL_REVIEW_ISSUE_MISSING_STOP_TIME] += 1

    for row in rate_rows or []:
        status = _token(row.get("Status"))
        field = _token(row.get("Rate Field Type")) or "rate"
        if status in {"missing", "conflict", "low_confidence", "needs_review"}:
            rate_issue_counts[field] += 1
        if status == "missing":
            issue_counts[LOCAL_REVIEW_ISSUE_RATE_MISSING] += 1
        if status == "conflict":
            issue_counts[LOCAL_REVIEW_ISSUE_RATE_CONFLICT] += 1

    top_issue_categories = [name for name, _count in issue_counts.most_common(10)]
    top_fields_by_review_need = [
        name for name, _count in field_issue_counts.most_common(10)
    ]
    recommended_next_fix = (
        _recommended_fix_bucket(top_issue_categories[:1])
        if top_issue_categories
        else "local_human_review"
    )
    return {
        "document_count": len(alias_summaries or []),
        "readiness_counts": dict(sorted(readiness_counts.items())),
        "ocr_needed_count": issue_counts.get(LOCAL_REVIEW_ISSUE_OCR_NEEDED, 0),
        "issue_category_counts": dict(issue_counts.most_common()),
        "field_issue_counts": dict(field_issue_counts.most_common()),
        "stop_issue_counts": dict(stop_issue_counts.most_common()),
        "rate_issue_counts": dict(rate_issue_counts.most_common()),
        "top_issue_categories": top_issue_categories,
        "top_fields_by_review_need": top_fields_by_review_need,
        "aliases_by_issue_category": {
            key: sorted(set(value)) for key, value in sorted(aliases_by_issue.items())
        },
        "recommended_next_fix": recommended_next_fix,
        "analysis_version": LOCAL_REVIEW_ANALYSIS_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
    }


def build_local_review_analysis(
    document_rows,
    stop_rows,
    field_rows,
    rate_rows,
    include_local_document_names=False,
):
    alias_summaries = build_alias_summaries(
        document_rows,
        stop_rows,
        field_rows,
        rate_rows,
        include_local_document_names=include_local_document_names,
    )
    aggregate = build_local_review_aggregate(
        alias_summaries,
        stop_rows=stop_rows,
        field_rows=field_rows,
        rate_rows=rate_rows,
    )
    return {
        "aliases": alias_summaries,
        "aggregate": aggregate,
        "analysis_version": LOCAL_REVIEW_ANALYSIS_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
    }


def load_local_review_csvs(input_dir=DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR):
    root = Path(input_dir)
    return {
        "document_rows": load_document_summary_csv(root / REVIEW_DOCUMENT_SUMMARY_CSV),
        "stop_rows": load_stop_review_csv(root / REVIEW_STOP_REVIEW_CSV),
        "field_rows": load_field_review_csv(root / REVIEW_FIELD_REVIEW_CSV),
        "rate_rows": load_rate_review_csv(root / REVIEW_RATE_REVIEW_CSV),
    }


def analyze_local_review_outputs(
    input_dir=DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    include_local_document_names=False,
):
    rows = load_local_review_csvs(input_dir)
    return build_local_review_analysis(
        rows["document_rows"],
        rows["stop_rows"],
        rows["field_rows"],
        rows["rate_rows"],
        include_local_document_names=include_local_document_names,
    )


def write_local_review_analysis_json(analysis, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    return {"json": path.name, "private_values_printed": False}


def local_review_analysis_markdown_lines(analysis):
    aggregate = (analysis or {}).get("aggregate", {})
    lines = [
        "# Local RateCon Review Analysis",
        "",
        "Safe summary only. No private values, raw text, filenames, or local paths.",
        "",
        f"- documents_analyzed: {aggregate.get('document_count', 0)}",
        f"- readiness_counts: {aggregate.get('readiness_counts', {})}",
        f"- ocr_needed_count: {aggregate.get('ocr_needed_count', 0)}",
        f"- top_issue_categories: {aggregate.get('top_issue_categories', [])}",
        f"- top_fields_by_review_need: {aggregate.get('top_fields_by_review_need', [])}",
        f"- recommended_next_fix: {aggregate.get('recommended_next_fix', '')}",
        "",
        "## Issue Category Counts",
    ]
    for category, count in (aggregate.get("issue_category_counts", {}) or {}).items():
        lines.append(f"- {category}: {count}")
    lines.append("")
    lines.append("## Aliases By Issue Category")
    for category, aliases in (aggregate.get("aliases_by_issue_category", {}) or {}).items():
        lines.append(f"- {category}: {', '.join(aliases)}")
    return lines


def write_local_review_analysis_md(analysis, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(local_review_analysis_markdown_lines(analysis)) + "\n",
        encoding="utf-8",
    )
    return {"md": path.name, "private_values_printed": False}
