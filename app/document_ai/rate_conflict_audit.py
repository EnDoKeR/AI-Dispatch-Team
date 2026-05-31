"""Safe rate conflict audit contracts.

Rate conflict audit artifacts store aliases, counts, statuses, and categories
only. They must not store or print money values, private labels, filenames,
local paths, or raw text.
"""

from collections import Counter, defaultdict

from app.document_ai.rate_candidate_forensics import (
    RATE_CATEGORY_ACCESSORIAL,
    RATE_CATEGORY_AGREED_AMOUNT,
    RATE_CATEGORY_BILLING_AMOUNT,
    RATE_CATEGORY_DEDUCTION,
    RATE_CATEGORY_DETENTION,
    RATE_CATEGORY_LAYOVER,
    RATE_CATEGORY_LINEHAUL,
    RATE_CATEGORY_LUMPER,
    RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY,
    RATE_CATEGORY_PENALTY,
    RATE_CATEGORY_QUICKPAY_DISCOUNT,
    RATE_CATEGORY_TERMS_AMOUNT,
    RATE_CATEGORY_TOTAL_CHARGE,
    RATE_CATEGORY_TONU,
    classify_rate_candidate_category,
)
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_MEDIUM,
    FIELD_ACCESSORIAL_TERM,
    FIELD_RATE,
    normalize_confidence,
)
from app.document_ai.ratecon_field_resolution import (
    FIELD_RESOLUTION_STATUS_CONFLICT,
    FIELD_RESOLUTION_STATUS_RESOLVED,
)


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


def _is_rate_candidate(candidate):
    return _text((candidate or {}).get("field_name")) in {
        FIELD_RATE,
        FIELD_ACCESSORIAL_TERM,
    }


def _resolution_for_rate(resolution_result):
    for resolution in (resolution_result or {}).get("resolutions", []) or []:
        if _text(resolution.get("field_name")) == FIELD_RATE:
            return resolution
    return {}


def _warnings(candidate):
    return {
        _token(item)
        for item in (candidate or {}).get("warnings", []) or []
        if _token(item)
    }


def _is_strong_candidate(candidate):
    confidence = normalize_confidence((candidate or {}).get("confidence"))
    return confidence in {CANDIDATE_CONFIDENCE_HIGH, CANDIDATE_CONFIDENCE_MEDIUM}


def _is_current_or_revised(candidate):
    text = " ".join(
        [
            _token((candidate or {}).get("label")),
            _token((candidate or {}).get("value_type")),
            " ".join(sorted(_warnings(candidate))),
        ]
    )
    return any(token in text for token in {"revised", "current", "updated"})


def _is_original_or_previous(candidate):
    text = " ".join(
        [
            _token((candidate or {}).get("label")),
            _token((candidate or {}).get("value_type")),
            " ".join(sorted(_warnings(candidate))),
        ]
    )
    return any(token in text for token in {"original", "previous", "prior"})


def _safe_rate_candidates(text_candidates=None, layout_candidates=None):
    return [
        candidate
        for candidate in list(text_candidates or []) + list(layout_candidates or [])
        if isinstance(candidate, dict) and _is_rate_candidate(candidate)
    ]


def _main_rate_candidates(candidates):
    main_categories = {
        RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY,
        RATE_CATEGORY_AGREED_AMOUNT,
        RATE_CATEGORY_LINEHAUL,
        RATE_CATEGORY_TOTAL_CHARGE,
    }
    return [
        candidate
        for candidate in candidates or []
        if classify_rate_candidate_category(candidate) in main_categories
    ]


def _has_explicit_total(candidates):
    return any(
        classify_rate_candidate_category(candidate)
        in {
            RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY,
            RATE_CATEGORY_AGREED_AMOUNT,
            RATE_CATEGORY_TOTAL_CHARGE,
        }
        for candidate in candidates or []
    )


def _equivalence_summary_for_candidates(candidates):
    from app.document_ai.rate_candidate_equivalence import (
        classify_rate_candidate_equivalence_group,
        group_equivalent_rate_candidates,
    )

    groups = group_equivalent_rate_candidates(candidates)
    equivalent_groups = [
        group
        for group in groups
        if len(group.get("candidates", [])) > 1
        and classify_rate_candidate_equivalence_group(group) != RATE_EQUIVALENT_UNKNOWN
    ]
    strong_main_groups = [
        group
        for group in groups
        if (group.get("fingerprint", {}) or {}).get("category_family") == "main_rate"
        and any(_is_strong_candidate(candidate) for candidate in group.get("candidates", []))
    ]
    return {
        "groups": groups,
        "equivalent_group_count": len(equivalent_groups),
        "strong_main_group_count": len(strong_main_groups),
    }


def build_rate_conflict_audit_record_from_candidates(
    measurement_alias="",
    text_candidates=None,
    layout_candidates=None,
    rate_fusion_result=None,
    resolution_result=None,
    document_type="",
):
    candidates = _safe_rate_candidates(text_candidates, layout_candidates)
    category_counts = Counter(
        classify_rate_candidate_category(candidate) for candidate in candidates
    )
    main_candidates = _main_rate_candidates(candidates)
    linehaul_candidate_count = category_counts.get(RATE_CATEGORY_LINEHAUL, 0)
    accessorial_candidate_count = sum(
        category_counts.get(category, 0)
        for category in {
            RATE_CATEGORY_ACCESSORIAL,
            RATE_CATEGORY_DETENTION,
            RATE_CATEGORY_LAYOVER,
            RATE_CATEGORY_LUMPER,
        }
    )
    quickpay_deduction_candidate_count = sum(
        category_counts.get(category, 0)
        for category in {
            RATE_CATEGORY_QUICKPAY_DISCOUNT,
            RATE_CATEGORY_DEDUCTION,
            RATE_CATEGORY_PENALTY,
        }
    )
    terms_billing_candidate_count = sum(
        category_counts.get(category, 0)
        for category in {
            RATE_CATEGORY_TERMS_AMOUNT,
            RATE_CATEGORY_BILLING_AMOUNT,
        }
    )
    revised_current_candidate_count = sum(
        1 for candidate in candidates if _is_current_or_revised(candidate)
    )
    original_previous_candidate_count = sum(
        1 for candidate in candidates if _is_original_or_previous(candidate)
    )

    equivalence = _equivalence_summary_for_candidates(main_candidates)
    different_strong_total_count = (
        equivalence["strong_main_group_count"]
        if equivalence["strong_main_group_count"] > 1
        else 0
    )
    fusion = rate_fusion_result or {}
    resolution = _resolution_for_rate(resolution_result)
    conflict_present = (
        fusion.get("fused_status") == "conflict"
        or _text(resolution.get("status")) == FIELD_RESOLUTION_STATUS_CONFLICT
    )
    selected_rate_present = bool(
        fusion.get("selected_candidate_id")
        or resolution.get("selected_candidate")
    )
    core_rate_mapped = _text(resolution.get("status")) == FIELD_RESOLUTION_STATUS_RESOLVED
    document_type_token = _token(document_type)

    reason = RATE_AUDIT_UNKNOWN
    if selected_rate_present and not core_rate_mapped:
        reason = RATE_AUDIT_SELECTED_RATE_NOT_CORE_MAPPED
    elif conflict_present and category_counts.get(RATE_CATEGORY_TONU, 0) and document_type_token in {
        "truck_order_not_used",
        "tonu",
    }:
        reason = RATE_AUDIT_TONU_NON_NORMAL_LOAD
    elif conflict_present and revised_current_candidate_count and original_previous_candidate_count:
        reason = RATE_AUDIT_REVISED_ORIGINAL_CONFLICT
    elif conflict_present and linehaul_candidate_count and _has_explicit_total(main_candidates):
        reason = RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT
    elif conflict_present and different_strong_total_count:
        reason = RATE_AUDIT_MULTIPLE_DIFFERENT_STRONG_TOTALS
    elif conflict_present and equivalence["equivalent_group_count"]:
        reason = RATE_AUDIT_SAME_AMOUNT_MULTIPLE_SOURCES
    elif conflict_present and accessorial_candidate_count:
        reason = RATE_AUDIT_ACCESSORIAL_NOISE_REMAINING
    elif conflict_present and quickpay_deduction_candidate_count:
        reason = RATE_AUDIT_QUICKPAY_DEDUCTION_NOISE_REMAINING
    elif conflict_present and terms_billing_candidate_count:
        reason = RATE_AUDIT_TERMS_BILLING_NOISE_REMAINING
    elif candidates and fusion.get("fused_status") in {"missing", "needs_review", "low_confidence", ""}:
        reason = RATE_AUDIT_CANDIDATE_NOT_RESOLVED

    return build_rate_conflict_audit_record(
        measurement_alias=measurement_alias,
        rate_candidate_count=len(candidates),
        main_rate_candidate_count=len(main_candidates),
        equivalent_candidate_group_count=equivalence["equivalent_group_count"],
        different_strong_total_count=different_strong_total_count,
        linehaul_candidate_count=linehaul_candidate_count,
        accessorial_candidate_count=accessorial_candidate_count,
        quickpay_deduction_candidate_count=quickpay_deduction_candidate_count,
        terms_billing_candidate_count=terms_billing_candidate_count,
        revised_current_candidate_count=revised_current_candidate_count,
        original_previous_candidate_count=original_previous_candidate_count,
        selected_rate_present=selected_rate_present,
        core_rate_mapped=core_rate_mapped,
        conflict_present=conflict_present,
        conflict_reason=reason,
        review_required=bool(fusion.get("review_required") or conflict_present),
        warning_codes=fusion.get("warning_codes", []),
    )


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
