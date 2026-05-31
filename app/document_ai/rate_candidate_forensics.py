"""Safe rate candidate forensics contracts.

Rate forensics stores aliases, counts, candidate categories, source sections,
and conflict reasons only. It must not store or print money values, raw text,
private labels, filenames, or local paths.
"""

from collections import Counter, defaultdict
import json
from pathlib import Path

from app.document_ai.local_review_analysis import LocalReviewAnalysisError
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    _normalize_output_dir,
)


RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY = "main_total_carrier_pay"
RATE_CATEGORY_AGREED_AMOUNT = "agreed_amount"
RATE_CATEGORY_LINEHAUL = "linehaul"
RATE_CATEGORY_TOTAL_CHARGE = "total_charge"
RATE_CATEGORY_ACCESSORIAL = "accessorial"
RATE_CATEGORY_DETENTION = "detention"
RATE_CATEGORY_LAYOVER = "layover"
RATE_CATEGORY_LUMPER = "lumper"
RATE_CATEGORY_TONU = "tonu"
RATE_CATEGORY_QUICKPAY_DISCOUNT = "quickpay_discount"
RATE_CATEGORY_DEDUCTION = "deduction"
RATE_CATEGORY_PENALTY = "penalty"
RATE_CATEGORY_BILLING_AMOUNT = "billing_amount"
RATE_CATEGORY_TERMS_AMOUNT = "terms_amount"
RATE_CATEGORY_UNKNOWN_MONEY = "unknown_money"

RATE_CANDIDATE_CATEGORIES = {
    RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY,
    RATE_CATEGORY_AGREED_AMOUNT,
    RATE_CATEGORY_LINEHAUL,
    RATE_CATEGORY_TOTAL_CHARGE,
    RATE_CATEGORY_ACCESSORIAL,
    RATE_CATEGORY_DETENTION,
    RATE_CATEGORY_LAYOVER,
    RATE_CATEGORY_LUMPER,
    RATE_CATEGORY_TONU,
    RATE_CATEGORY_QUICKPAY_DISCOUNT,
    RATE_CATEGORY_DEDUCTION,
    RATE_CATEGORY_PENALTY,
    RATE_CATEGORY_BILLING_AMOUNT,
    RATE_CATEGORY_TERMS_AMOUNT,
    RATE_CATEGORY_UNKNOWN_MONEY,
}

RATE_SECTION_RATE_SUMMARY = "rate_summary"
RATE_SECTION_RATE_BREAKDOWN = "rate_breakdown"
RATE_SECTION_PAYMENT_SUMMARY = "payment_summary"
RATE_SECTION_LOAD_IDENTITY_HEADER = "load_identity_header"
RATE_SECTION_BILLING = "billing"
RATE_SECTION_QUICKPAY = "quickpay"
RATE_SECTION_TERMS = "terms"
RATE_SECTION_LEGAL = "legal"
RATE_SECTION_STOP_SECTION = "stop_section"
RATE_SECTION_UNKNOWN = "unknown"

RATE_CANDIDATE_SOURCE_SECTIONS = {
    RATE_SECTION_RATE_SUMMARY,
    RATE_SECTION_RATE_BREAKDOWN,
    RATE_SECTION_PAYMENT_SUMMARY,
    RATE_SECTION_LOAD_IDENTITY_HEADER,
    RATE_SECTION_BILLING,
    RATE_SECTION_QUICKPAY,
    RATE_SECTION_TERMS,
    RATE_SECTION_LEGAL,
    RATE_SECTION_STOP_SECTION,
    RATE_SECTION_UNKNOWN,
}

RATE_CONFLICT_MULTIPLE_STRONG_TOTALS = "multiple_strong_totals"
RATE_CONFLICT_ACCESSORIAL_AS_MAIN_RATE = "accessorial_confused_with_main_rate"
RATE_CONFLICT_QUICKPAY_AS_MAIN_RATE = "quickpay_confused_with_main_rate"
RATE_CONFLICT_DEDUCTION_PENALTY_AS_MAIN_RATE = (
    "deduction_penalty_confused_with_main_rate"
)
RATE_CONFLICT_TERMS_AMOUNT_AS_MAIN_RATE = "terms_amount_confused_with_main_rate"
RATE_CONFLICT_LINEHAUL_TOTAL = "linehaul_total_conflict"
RATE_CONFLICT_TONU_NON_NORMAL_LOAD = "tonu_non_normal_load"
RATE_CONFLICT_CANDIDATE_NOT_RESOLVED = "candidate_generated_but_not_resolved"
RATE_CONFLICT_NORMALIZED_NOT_CORE_MAPPED = "normalized_rate_not_core_mapped"
RATE_CONFLICT_LOW_CONFIDENCE = "low_confidence"
RATE_CONFLICT_NO_SHARED_ROOT_CAUSE = "no_shared_root_cause"
RATE_CONFLICT_UNKNOWN = "unknown"

RATE_CONFLICT_REASONS = {
    RATE_CONFLICT_MULTIPLE_STRONG_TOTALS,
    RATE_CONFLICT_ACCESSORIAL_AS_MAIN_RATE,
    RATE_CONFLICT_QUICKPAY_AS_MAIN_RATE,
    RATE_CONFLICT_DEDUCTION_PENALTY_AS_MAIN_RATE,
    RATE_CONFLICT_TERMS_AMOUNT_AS_MAIN_RATE,
    RATE_CONFLICT_LINEHAUL_TOTAL,
    RATE_CONFLICT_TONU_NON_NORMAL_LOAD,
    RATE_CONFLICT_CANDIDATE_NOT_RESOLVED,
    RATE_CONFLICT_NORMALIZED_NOT_CORE_MAPPED,
    RATE_CONFLICT_LOW_CONFIDENCE,
    RATE_CONFLICT_NO_SHARED_ROOT_CAUSE,
    RATE_CONFLICT_UNKNOWN,
}

CODE_FIXABLE_RATE_REASONS = {
    RATE_CONFLICT_MULTIPLE_STRONG_TOTALS,
    RATE_CONFLICT_ACCESSORIAL_AS_MAIN_RATE,
    RATE_CONFLICT_QUICKPAY_AS_MAIN_RATE,
    RATE_CONFLICT_DEDUCTION_PENALTY_AS_MAIN_RATE,
    RATE_CONFLICT_TERMS_AMOUNT_AS_MAIN_RATE,
    RATE_CONFLICT_LINEHAUL_TOTAL,
    RATE_CONFLICT_CANDIDATE_NOT_RESOLVED,
    RATE_CONFLICT_NORMALIZED_NOT_CORE_MAPPED,
}

RATE_FORENSICS_VERSION = "rate_candidate_forensics_v1"
RATE_FORENSICS_RAW_JSON = "rate_candidate_forensics_raw.json"
RATE_FORENSICS_RAW_MD = "rate_candidate_forensics_raw.md"
RATE_FORENSICS_JSON = "rate_candidate_forensics.json"
RATE_FORENSICS_MD = "rate_candidate_forensics.md"


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def normalize_rate_category(value):
    token = _token(value)
    return token if token in RATE_CANDIDATE_CATEGORIES else RATE_CATEGORY_UNKNOWN_MONEY


def normalize_rate_source_section(value):
    token = _token(value)
    return token if token in RATE_CANDIDATE_SOURCE_SECTIONS else RATE_SECTION_UNKNOWN


def normalize_rate_conflict_reason(value):
    token = _token(value)
    return token if token in RATE_CONFLICT_REASONS else RATE_CONFLICT_UNKNOWN


def recommended_rate_fix_bucket(reason):
    normalized = normalize_rate_conflict_reason(reason)
    if normalized in {
        RATE_CONFLICT_ACCESSORIAL_AS_MAIN_RATE,
        RATE_CONFLICT_QUICKPAY_AS_MAIN_RATE,
        RATE_CONFLICT_DEDUCTION_PENALTY_AS_MAIN_RATE,
        RATE_CONFLICT_TERMS_AMOUNT_AS_MAIN_RATE,
    }:
        return "rate_source_priority_guardrails"
    if normalized == RATE_CONFLICT_MULTIPLE_STRONG_TOTALS:
        return "rate_conflict_review_routing"
    if normalized == RATE_CONFLICT_LINEHAUL_TOTAL:
        return "rate_breakdown_total_priority"
    if normalized == RATE_CONFLICT_NORMALIZED_NOT_CORE_MAPPED:
        return "normalized_rate_to_core_mapping"
    if normalized == RATE_CONFLICT_TONU_NON_NORMAL_LOAD:
        return "tonu_payment_review"
    return "local_human_review"


def _safe_counts(counts, normalizer):
    if not isinstance(counts, dict):
        return {}
    normalized = Counter()
    for key, value in counts.items():
        normalized[normalizer(key)] += _int(value)
    return dict(sorted(normalized.items()))


def build_rate_forensics_record(
    measurement_alias="",
    rate_candidate_count=0,
    main_rate_candidate_count=0,
    accessorial_candidate_count=0,
    quickpay_candidate_count=0,
    terms_candidate_count=0,
    billing_candidate_count=0,
    selected_rate_present=False,
    conflict_present=False,
    conflict_reason=RATE_CONFLICT_UNKNOWN,
    category_counts=None,
    source_section_counts=None,
    warning_codes=None,
    recommended_fix_bucket="",
):
    reason = normalize_rate_conflict_reason(conflict_reason)
    return {
        "measurement_alias": _text(measurement_alias),
        "rate_candidate_count": _int(rate_candidate_count),
        "main_rate_candidate_count": _int(main_rate_candidate_count),
        "accessorial_candidate_count": _int(accessorial_candidate_count),
        "quickpay_candidate_count": _int(quickpay_candidate_count),
        "terms_candidate_count": _int(terms_candidate_count),
        "billing_candidate_count": _int(billing_candidate_count),
        "selected_rate_present": bool(selected_rate_present),
        "conflict_present": bool(conflict_present),
        "conflict_reason": reason,
        "category_counts": _safe_counts(category_counts, normalize_rate_category),
        "source_section_counts": _safe_counts(
            source_section_counts,
            normalize_rate_source_section,
        ),
        "warning_codes": [
            _token(code) for code in warning_codes or [] if _token(code)
        ],
        "recommended_fix_bucket": recommended_fix_bucket
        or recommended_rate_fix_bucket(reason),
        "private_values_included": False,
        "raw_text_included": False,
        "money_values_included": False,
    }


def build_rate_forensics_aggregate(records, document_count=0):
    normalized_records = [
        build_rate_forensics_record(
            measurement_alias=record.get("measurement_alias", ""),
            rate_candidate_count=record.get("rate_candidate_count", 0),
            main_rate_candidate_count=record.get("main_rate_candidate_count", 0),
            accessorial_candidate_count=record.get("accessorial_candidate_count", 0),
            quickpay_candidate_count=record.get("quickpay_candidate_count", 0),
            terms_candidate_count=record.get("terms_candidate_count", 0),
            billing_candidate_count=record.get("billing_candidate_count", 0),
            selected_rate_present=record.get("selected_rate_present", False),
            conflict_present=record.get("conflict_present", False),
            conflict_reason=record.get("conflict_reason", RATE_CONFLICT_UNKNOWN),
            category_counts=record.get("category_counts", {}),
            source_section_counts=record.get("source_section_counts", {}),
            warning_codes=record.get("warning_codes", []),
            recommended_fix_bucket=record.get("recommended_fix_bucket", ""),
        )
        for record in records or []
        if isinstance(record, dict)
    ]
    reason_counts = Counter(record["conflict_reason"] for record in normalized_records)
    category_counts = Counter()
    source_counts = Counter()
    aliases_by_reason = defaultdict(list)
    for record in normalized_records:
        category_counts.update(record.get("category_counts", {}))
        source_counts.update(record.get("source_section_counts", {}))
        alias = record.get("measurement_alias", "")
        reason = record.get("conflict_reason", RATE_CONFLICT_UNKNOWN)
        if alias and alias not in aliases_by_reason[reason]:
            aliases_by_reason[reason].append(alias)

    selected_root_cause = ""
    selected_count = 0
    for reason, count in sorted(
        reason_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        if reason in CODE_FIXABLE_RATE_REASONS and count >= 3:
            selected_root_cause = reason
            selected_count = count
            break
    fix_allowed = bool(selected_root_cause)
    recommended_next_action = (
        recommended_rate_fix_bucket(selected_root_cause)
        if selected_root_cause
        else "local_human_review"
    )

    return {
        "document_count": _int(document_count),
        "records_by_conflict_reason": dict(sorted(reason_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "source_section_counts": dict(sorted(source_counts.items())),
        "aliases_by_conflict_reason": {
            key: sorted(values) for key, values in sorted(aliases_by_reason.items())
        },
        "selected_root_cause": selected_root_cause,
        "selected_root_cause_count": selected_count,
        "fix_allowed": fix_allowed,
        "recommended_next_action": recommended_next_action,
        "rate_candidate_count": sum(
            record["rate_candidate_count"] for record in normalized_records
        ),
        "main_rate_candidate_count": sum(
            record["main_rate_candidate_count"] for record in normalized_records
        ),
        "accessorial_candidate_count": sum(
            record["accessorial_candidate_count"] for record in normalized_records
        ),
        "quickpay_candidate_count": sum(
            record["quickpay_candidate_count"] for record in normalized_records
        ),
        "terms_candidate_count": sum(
            record["terms_candidate_count"] for record in normalized_records
        ),
        "billing_candidate_count": sum(
            record["billing_candidate_count"] for record in normalized_records
        ),
        "selected_rate_present_count": sum(
            1 for record in normalized_records if record["selected_rate_present"]
        ),
        "conflict_count": sum(
            1 for record in normalized_records if record["conflict_present"]
        ),
        "analysis_version": RATE_FORENSICS_VERSION,
    }


def build_rate_forensics_result(records=None, document_count=0):
    normalized_records = [
        build_rate_forensics_record(
            measurement_alias=record.get("measurement_alias", ""),
            rate_candidate_count=record.get("rate_candidate_count", 0),
            main_rate_candidate_count=record.get("main_rate_candidate_count", 0),
            accessorial_candidate_count=record.get("accessorial_candidate_count", 0),
            quickpay_candidate_count=record.get("quickpay_candidate_count", 0),
            terms_candidate_count=record.get("terms_candidate_count", 0),
            billing_candidate_count=record.get("billing_candidate_count", 0),
            selected_rate_present=record.get("selected_rate_present", False),
            conflict_present=record.get("conflict_present", False),
            conflict_reason=record.get("conflict_reason", RATE_CONFLICT_UNKNOWN),
            category_counts=record.get("category_counts", {}),
            source_section_counts=record.get("source_section_counts", {}),
            warning_codes=record.get("warning_codes", []),
            recommended_fix_bucket=record.get("recommended_fix_bucket", ""),
        )
        for record in records or []
        if isinstance(record, dict)
    ]
    return {
        "analysis_version": RATE_FORENSICS_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
        "money_values_included": False,
        "records": normalized_records,
        "aggregate": build_rate_forensics_aggregate(
            normalized_records,
            document_count=document_count,
        ),
    }


def _read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as exc:
        raise LocalReviewAnalysisError(f"invalid JSON: {Path(path).name}") from exc


def rate_forensics_markdown_lines(analysis):
    aggregate = (analysis or {}).get("aggregate", {}) or {}
    lines = [
        "# Rate Candidate Forensics",
        "",
        "Local-only analysis. Safe to share: aliases, counts, categories, sections, and conflict reasons.",
        "Do not share money values, raw text, private labels, filenames, local paths, or broker identifiers.",
        "",
        f"Documents analyzed: {aggregate.get('document_count', 0)}",
        f"Fix allowed: {aggregate.get('fix_allowed', False)}",
        f"Selected root cause: {aggregate.get('selected_root_cause', '')}",
        f"Recommended next action: {aggregate.get('recommended_next_action', '')}",
        "",
        "## Counts",
        f"- rate candidates: {aggregate.get('rate_candidate_count', 0)}",
        f"- main rate candidates: {aggregate.get('main_rate_candidate_count', 0)}",
        f"- accessorial candidates: {aggregate.get('accessorial_candidate_count', 0)}",
        f"- quickpay candidates: {aggregate.get('quickpay_candidate_count', 0)}",
        f"- terms candidates: {aggregate.get('terms_candidate_count', 0)}",
        f"- billing candidates: {aggregate.get('billing_candidate_count', 0)}",
        f"- conflicts: {aggregate.get('conflict_count', 0)}",
        "",
        "## Conflict Reasons",
    ]
    for reason, count in (aggregate.get("records_by_conflict_reason", {}) or {}).items():
        lines.append(f"- {reason}: {count}")
    lines.extend(["", "## Categories"])
    for category, count in (aggregate.get("category_counts", {}) or {}).items():
        lines.append(f"- {category}: {count}")
    lines.extend(["", "## Source Sections"])
    for section, count in (aggregate.get("source_section_counts", {}) or {}).items():
        lines.append(f"- {section}: {count}")
    return lines


def write_rate_forensics_json(analysis, output_path):
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
        "money_values_printed": False,
    }


def write_rate_forensics_md(analysis, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(rate_forensics_markdown_lines(analysis)) + "\n",
        encoding="utf-8",
    )
    return {
        "md": path.name,
        "private_values_printed": False,
        "raw_text_printed": False,
        "money_values_printed": False,
    }


def write_rate_forensics_artifacts(
    analysis,
    output_dir=None,
    allow_custom_output_dir=False,
    raw=False,
):
    output_root = _normalize_output_dir(
        output_dir or DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    json_name = RATE_FORENSICS_RAW_JSON if raw else RATE_FORENSICS_JSON
    md_name = RATE_FORENSICS_RAW_MD if raw else RATE_FORENSICS_MD
    json_result = write_rate_forensics_json(analysis, output_root / json_name)
    md_result = write_rate_forensics_md(analysis, output_root / md_name)
    return {
        "files": {"rate_forensics_json": json_result["json"], "rate_forensics_md": md_result["md"]},
        "aggregate": (analysis or {}).get("aggregate", {}),
        "private_values_printed": False,
        "raw_text_printed": False,
        "money_values_printed": False,
    }
