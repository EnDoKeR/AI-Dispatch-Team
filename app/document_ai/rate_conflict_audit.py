"""Safe rate conflict audit contracts.

Rate conflict audit artifacts store aliases, counts, statuses, and categories
only. They must not store or print money values, private labels, filenames,
local paths, or raw text.
"""

from collections import Counter, defaultdict


RATE_CONFLICT_AUDIT_VERSION = "rate_conflict_audit_v1"
RATE_CONFLICT_AUDIT_RAW_JSON = "rate_conflict_audit_raw.json"
RATE_CONFLICT_AUDIT_RAW_MD = "rate_conflict_audit_raw.md"
RATE_CONFLICT_AUDIT_JSON = "rate_conflict_audit.json"
RATE_CONFLICT_AUDIT_MD = "rate_conflict_audit.md"

RATE_AUDIT_DUPLICATE_EQUIVALENT = "duplicate_equivalent_candidates"
RATE_AUDIT_SAME_AMOUNT_MULTIPLE_SOURCES = "same_amount_multiple_sources"
RATE_AUDIT_MULTIPLE_DIFFERENT_STRONG_TOTALS = "multiple_different_strong_totals"
RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT = "linehaul_total_conflict"
RATE_AUDIT_REVISED_ORIGINAL_CONFLICT = "revised_original_conflict"
RATE_AUDIT_ACCESSORIAL_NOISE_REMAINING = "accessorial_noise_remaining"
RATE_AUDIT_QUICKPAY_DEDUCTION_NOISE_REMAINING = (
    "quickpay_deduction_noise_remaining"
)
RATE_AUDIT_TERMS_BILLING_NOISE_REMAINING = "terms_billing_noise_remaining"
RATE_AUDIT_TONU_NON_NORMAL_LOAD = "tonu_non_normal_load"
RATE_AUDIT_CANDIDATE_NOT_RESOLVED = "candidate_generated_but_not_resolved"
RATE_AUDIT_SELECTED_RATE_NOT_CORE_MAPPED = "selected_rate_not_core_mapped"
RATE_AUDIT_NO_SHARED_ROOT_CAUSE = "no_shared_root_cause"
RATE_AUDIT_UNKNOWN = "unknown"

RATE_CONFLICT_AUDIT_REASONS = {
    RATE_AUDIT_DUPLICATE_EQUIVALENT,
    RATE_AUDIT_SAME_AMOUNT_MULTIPLE_SOURCES,
    RATE_AUDIT_MULTIPLE_DIFFERENT_STRONG_TOTALS,
    RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT,
    RATE_AUDIT_REVISED_ORIGINAL_CONFLICT,
    RATE_AUDIT_ACCESSORIAL_NOISE_REMAINING,
    RATE_AUDIT_QUICKPAY_DEDUCTION_NOISE_REMAINING,
    RATE_AUDIT_TERMS_BILLING_NOISE_REMAINING,
    RATE_AUDIT_TONU_NON_NORMAL_LOAD,
    RATE_AUDIT_CANDIDATE_NOT_RESOLVED,
    RATE_AUDIT_SELECTED_RATE_NOT_CORE_MAPPED,
    RATE_AUDIT_NO_SHARED_ROOT_CAUSE,
    RATE_AUDIT_UNKNOWN,
}

RATE_EQUIVALENT_SAME_AMOUNT = "equivalent_same_amount"
RATE_EQUIVALENT_DIFFERENT_AMOUNT = "different_amount"
RATE_EQUIVALENT_SAME_LABEL_DUPLICATE = "same_label_duplicate"
RATE_EQUIVALENT_DIFFERENT_LABEL_SAME_AMOUNT = "different_label_same_amount"
RATE_EQUIVALENT_DIFFERENT_SOURCE_SAME_AMOUNT = "different_source_same_amount"
RATE_EQUIVALENT_UNKNOWN = "unknown"

RATE_CANDIDATE_EQUIVALENCE_STATUSES = {
    RATE_EQUIVALENT_SAME_AMOUNT,
    RATE_EQUIVALENT_DIFFERENT_AMOUNT,
    RATE_EQUIVALENT_SAME_LABEL_DUPLICATE,
    RATE_EQUIVALENT_DIFFERENT_LABEL_SAME_AMOUNT,
    RATE_EQUIVALENT_DIFFERENT_SOURCE_SAME_AMOUNT,
    RATE_EQUIVALENT_UNKNOWN,
}

CODE_FIXABLE_RATE_CONFLICT_REASONS = {
    RATE_AUDIT_DUPLICATE_EQUIVALENT,
    RATE_AUDIT_SAME_AMOUNT_MULTIPLE_SOURCES,
    RATE_AUDIT_MULTIPLE_DIFFERENT_STRONG_TOTALS,
    RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT,
    RATE_AUDIT_REVISED_ORIGINAL_CONFLICT,
    RATE_AUDIT_CANDIDATE_NOT_RESOLVED,
    RATE_AUDIT_SELECTED_RATE_NOT_CORE_MAPPED,
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


def normalize_rate_conflict_audit_reason(value):
    token = _token(value)
    return token if token in RATE_CONFLICT_AUDIT_REASONS else RATE_AUDIT_UNKNOWN


def normalize_rate_candidate_equivalence_status(value):
    token = _token(value)
    return token if token in RATE_CANDIDATE_EQUIVALENCE_STATUSES else RATE_EQUIVALENT_UNKNOWN


def recommended_rate_conflict_fix_bucket(reason):
    normalized = normalize_rate_conflict_audit_reason(reason)
    if normalized in {
        RATE_AUDIT_DUPLICATE_EQUIVALENT,
        RATE_AUDIT_SAME_AMOUNT_MULTIPLE_SOURCES,
    }:
        return "equivalent_candidate_dedupe_and_confidence_reinforcement"
    if normalized == RATE_AUDIT_MULTIPLE_DIFFERENT_STRONG_TOTALS:
        return "rate_conflict_review_routing"
    if normalized == RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT:
        return "total_priority_over_linehaul"
    if normalized == RATE_AUDIT_REVISED_ORIGINAL_CONFLICT:
        return "revised_current_priority"
    if normalized == RATE_AUDIT_SELECTED_RATE_NOT_CORE_MAPPED:
        return "selected_rate_core_mapping"
    if normalized == RATE_AUDIT_CANDIDATE_NOT_RESOLVED:
        return "rate_conflict_review_routing"
    return "local_human_review_for_rate"


def build_rate_conflict_audit_record(
    measurement_alias="",
    rate_candidate_count=0,
    main_rate_candidate_count=0,
    equivalent_candidate_group_count=0,
    different_strong_total_count=0,
    linehaul_candidate_count=0,
    accessorial_candidate_count=0,
    quickpay_deduction_candidate_count=0,
    terms_billing_candidate_count=0,
    revised_current_candidate_count=0,
    original_previous_candidate_count=0,
    selected_rate_present=False,
    core_rate_mapped=False,
    conflict_present=False,
    conflict_reason=RATE_AUDIT_UNKNOWN,
    review_required=False,
    recommended_fix_bucket="",
    warning_codes=None,
):
    reason = normalize_rate_conflict_audit_reason(conflict_reason)
    return {
        "measurement_alias": _text(measurement_alias),
        "rate_candidate_count": _int(rate_candidate_count),
        "main_rate_candidate_count": _int(main_rate_candidate_count),
        "equivalent_candidate_group_count": _int(equivalent_candidate_group_count),
        "different_strong_total_count": _int(different_strong_total_count),
        "linehaul_candidate_count": _int(linehaul_candidate_count),
        "accessorial_candidate_count": _int(accessorial_candidate_count),
        "quickpay_deduction_candidate_count": _int(
            quickpay_deduction_candidate_count
        ),
        "terms_billing_candidate_count": _int(terms_billing_candidate_count),
        "revised_current_candidate_count": _int(revised_current_candidate_count),
        "original_previous_candidate_count": _int(original_previous_candidate_count),
        "selected_rate_present": bool(selected_rate_present),
        "core_rate_mapped": bool(core_rate_mapped),
        "conflict_present": bool(conflict_present),
        "conflict_reason": reason,
        "review_required": bool(review_required),
        "recommended_fix_bucket": recommended_fix_bucket
        or recommended_rate_conflict_fix_bucket(reason),
        "warning_codes": [
            _token(code) for code in warning_codes or [] if _token(code)
        ],
        "private_values_included": False,
        "raw_text_included": False,
        "money_values_included": False,
    }


def build_rate_conflict_audit_aggregate(records, document_count=0):
    normalized_records = [
        build_rate_conflict_audit_record(
            measurement_alias=record.get("measurement_alias", ""),
            rate_candidate_count=record.get("rate_candidate_count", 0),
            main_rate_candidate_count=record.get("main_rate_candidate_count", 0),
            equivalent_candidate_group_count=record.get(
                "equivalent_candidate_group_count",
                0,
            ),
            different_strong_total_count=record.get("different_strong_total_count", 0),
            linehaul_candidate_count=record.get("linehaul_candidate_count", 0),
            accessorial_candidate_count=record.get("accessorial_candidate_count", 0),
            quickpay_deduction_candidate_count=record.get(
                "quickpay_deduction_candidate_count",
                0,
            ),
            terms_billing_candidate_count=record.get(
                "terms_billing_candidate_count",
                0,
            ),
            revised_current_candidate_count=record.get(
                "revised_current_candidate_count",
                0,
            ),
            original_previous_candidate_count=record.get(
                "original_previous_candidate_count",
                0,
            ),
            selected_rate_present=record.get("selected_rate_present", False),
            core_rate_mapped=record.get("core_rate_mapped", False),
            conflict_present=record.get("conflict_present", False),
            conflict_reason=record.get("conflict_reason", RATE_AUDIT_UNKNOWN),
            review_required=record.get("review_required", False),
            recommended_fix_bucket=record.get("recommended_fix_bucket", ""),
            warning_codes=record.get("warning_codes", []),
        )
        for record in records or []
        if isinstance(record, dict)
    ]

    reason_counts = Counter(record["conflict_reason"] for record in normalized_records)
    aliases_by_reason = defaultdict(list)
    for record in normalized_records:
        alias = record.get("measurement_alias", "")
        reason = record.get("conflict_reason", RATE_AUDIT_UNKNOWN)
        if alias and alias not in aliases_by_reason[reason]:
            aliases_by_reason[reason].append(alias)

    selected_root_cause = ""
    selected_count = 0
    for reason, count in sorted(
        reason_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        if reason in CODE_FIXABLE_RATE_CONFLICT_REASONS and count >= 3:
            selected_root_cause = reason
            selected_count = count
            break

    return {
        "document_count": _int(document_count),
        "records_by_conflict_reason": dict(sorted(reason_counts.items())),
        "aliases_by_conflict_reason": {
            key: sorted(values) for key, values in sorted(aliases_by_reason.items())
        },
        "equivalent_group_count": sum(
            record["equivalent_candidate_group_count"] for record in normalized_records
        ),
        "different_strong_total_count": sum(
            record["different_strong_total_count"] for record in normalized_records
        ),
        "selected_rate_present_count": sum(
            1 for record in normalized_records if record["selected_rate_present"]
        ),
        "core_rate_mapped_count": sum(
            1 for record in normalized_records if record["core_rate_mapped"]
        ),
        "conflict_count": sum(
            1 for record in normalized_records if record["conflict_present"]
        ),
        "review_required_count": sum(
            1 for record in normalized_records if record["review_required"]
        ),
        "selected_root_cause": selected_root_cause,
        "selected_root_cause_count": selected_count,
        "fix_allowed": bool(selected_root_cause),
        "recommended_next_action": (
            recommended_rate_conflict_fix_bucket(selected_root_cause)
            if selected_root_cause
            else "local_human_review_for_rate"
        ),
        "analysis_version": RATE_CONFLICT_AUDIT_VERSION,
    }


def build_rate_conflict_audit_result(records=None, document_count=0):
    normalized_records = [
        build_rate_conflict_audit_record(
            measurement_alias=record.get("measurement_alias", ""),
            rate_candidate_count=record.get("rate_candidate_count", 0),
            main_rate_candidate_count=record.get("main_rate_candidate_count", 0),
            equivalent_candidate_group_count=record.get(
                "equivalent_candidate_group_count",
                0,
            ),
            different_strong_total_count=record.get("different_strong_total_count", 0),
            linehaul_candidate_count=record.get("linehaul_candidate_count", 0),
            accessorial_candidate_count=record.get("accessorial_candidate_count", 0),
            quickpay_deduction_candidate_count=record.get(
                "quickpay_deduction_candidate_count",
                0,
            ),
            terms_billing_candidate_count=record.get(
                "terms_billing_candidate_count",
                0,
            ),
            revised_current_candidate_count=record.get(
                "revised_current_candidate_count",
                0,
            ),
            original_previous_candidate_count=record.get(
                "original_previous_candidate_count",
                0,
            ),
            selected_rate_present=record.get("selected_rate_present", False),
            core_rate_mapped=record.get("core_rate_mapped", False),
            conflict_present=record.get("conflict_present", False),
            conflict_reason=record.get("conflict_reason", RATE_AUDIT_UNKNOWN),
            review_required=record.get("review_required", False),
            recommended_fix_bucket=record.get("recommended_fix_bucket", ""),
            warning_codes=record.get("warning_codes", []),
        )
        for record in records or []
        if isinstance(record, dict)
    ]
    return {
        "analysis_version": RATE_CONFLICT_AUDIT_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
        "money_values_included": False,
        "records": normalized_records,
        "aggregate": build_rate_conflict_audit_aggregate(
            normalized_records,
            document_count=document_count,
        ),
    }
