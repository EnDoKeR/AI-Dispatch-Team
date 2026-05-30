"""Rate candidate fusion guardrails."""

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_MEDIUM,
    FIELD_ACCESSORIAL_TERM,
    FIELD_RATE,
    normalize_confidence,
)


RATE_FUSION_VERSION = "rate_fusion_v1"

_MAIN_RATE_VALUE_TYPES = {
    "total_carrier_pay",
    "carrier_freight_pay",
    "linehaul",
    "total_charge",
    "agreed_amount",
    "unknown_money",
}

_TERMS_WARNINGS = {
    "not_final_rate_candidate",
    "payment_terms_not_main_rate",
    "tonu_payment_not_normal_linehaul",
}

_UNRESOLVED_BASELINE_STATUSES = {
    "",
    "missing",
    "needs_review",
    "low_confidence",
    "conflict",
    "unknown",
}


def _text(value):
    return str(value or "").strip()


def _value(candidate):
    return _text((candidate or {}).get("normalized_value") or (candidate or {}).get("raw_value")).lower()


def _candidate_id(candidate, index):
    return _text((candidate or {}).get("candidate_id")) or f"rate_candidate_{index + 1}"


def _confidence_score(candidate):
    confidence = normalize_confidence((candidate or {}).get("confidence"))
    if confidence == CANDIDATE_CONFIDENCE_HIGH:
        return 0.9
    if confidence == CANDIDATE_CONFIDENCE_MEDIUM:
        return 0.65
    return 0.35


def _warnings(candidate):
    return set(str(item or "").strip() for item in (candidate or {}).get("warnings", []) if str(item or "").strip())


def _is_terms_or_payment_noise(candidate):
    section_role = _text((candidate or {}).get("layout_section_role")).upper()
    if _warnings(candidate) & _TERMS_WARNINGS:
        return True
    return section_role in {
        "LEGAL_TERMS",
        "DEDUCTIONS_PENALTIES",
        "PAYMENT_TERMS",
        "QUICK_PAY",
        "BILLING_INSTRUCTIONS",
    }


def _is_tonu_candidate(candidate):
    return _text((candidate or {}).get("value_type")) == "TONU_pay" or "tonu_payment_not_normal_linehaul" in _warnings(candidate)


def _is_main_rate_candidate(candidate, document_type=""):
    if (candidate or {}).get("field_name") != FIELD_RATE:
        return False
    if _is_tonu_candidate(candidate) and _text(document_type).upper() != "TRUCK_ORDER_NOT_USED":
        return False
    if _is_terms_or_payment_noise(candidate):
        return False
    value_type = _text((candidate or {}).get("value_type")) or "unknown_money"
    return value_type in _MAIN_RATE_VALUE_TYPES


def _rank_key(item):
    index, candidate = item
    section_role = _text(candidate.get("layout_section_role")).upper()
    section_boost = 0.1 if section_role in {"RATE_SUMMARY", "RATE_BREAKDOWN", "PAYMENT_SUMMARY"} else 0.0
    value_type = _text(candidate.get("value_type"))
    total_boost = 0.05 if value_type in {"total_carrier_pay", "carrier_freight_pay", "total_charge", "agreed_amount"} else 0.0
    return (_confidence_score(candidate) + section_boost + total_boost, -index)


def fuse_rate_candidates(
    text_candidates=None,
    layout_candidates=None,
    baseline_status="",
    document_type="",
):
    all_candidates = [
        candidate
        for candidate in (text_candidates or []) + (layout_candidates or [])
        if isinstance(candidate, dict)
    ]
    main_candidates = [
        candidate
        for candidate in all_candidates
        if _is_main_rate_candidate(candidate, document_type=document_type)
    ]
    excluded_ids = [
        _candidate_id(candidate, index)
        for index, candidate in enumerate(all_candidates)
        if candidate not in main_candidates
        and (
            candidate.get("field_name") == FIELD_ACCESSORIAL_TERM
            or _is_terms_or_payment_noise(candidate)
            or _is_tonu_candidate(candidate)
        )
    ]
    warnings = []

    if not main_candidates:
        status = "missing" if baseline_status != "resolved" else "resolved"
        selected = ""
        if baseline_status == "resolved":
            warnings.append("rate_fusion_preserved_resolved_baseline")
        return {
            "field_name": FIELD_RATE,
            "fused_status": status,
            "selected_candidate_id": selected,
            "excluded_candidate_ids": sorted(set(excluded_ids)),
            "conflict_candidate_ids": [],
            "did_improve_baseline": False,
            "did_worsen_baseline": False,
            "review_required": status != "resolved",
            "warning_codes": warnings,
            "fusion_version": RATE_FUSION_VERSION,
        }

    ranked = sorted(enumerate(main_candidates), key=_rank_key, reverse=True)
    selected_index, selected_candidate = ranked[0]
    selected_id = _candidate_id(selected_candidate, selected_index)
    selected_value = _value(selected_candidate)

    conflict_ids = []
    strong_candidates = [
        (index, candidate)
        for index, candidate in ranked
        if _confidence_score(candidate) >= 0.65
    ]
    for index, candidate in strong_candidates:
        if candidate is selected_candidate:
            continue
        if _value(candidate) and _value(candidate) != selected_value:
            conflict_ids.extend([selected_id, _candidate_id(candidate, index)])

    if conflict_ids:
        return {
            "field_name": FIELD_RATE,
            "fused_status": "conflict",
            "selected_candidate_id": "",
            "excluded_candidate_ids": sorted(set(excluded_ids)),
            "conflict_candidate_ids": sorted(set(conflict_ids)),
            "did_improve_baseline": False,
            "did_worsen_baseline": baseline_status == "resolved",
            "review_required": True,
            "warning_codes": ["rate_fusion_conflicting_strong_totals"],
            "fusion_version": RATE_FUSION_VERSION,
        }

    did_improve = baseline_status in _UNRESOLVED_BASELINE_STATUSES
    return {
        "field_name": FIELD_RATE,
        "fused_status": "resolved",
        "selected_candidate_id": selected_id,
        "excluded_candidate_ids": sorted(set(excluded_ids)),
        "conflict_candidate_ids": [],
        "did_improve_baseline": did_improve,
        "did_worsen_baseline": False,
        "review_required": False,
        "warning_codes": ["rate_fusion_reinforced_baseline"] if baseline_status == "resolved" else [],
        "fusion_version": RATE_FUSION_VERSION,
    }
