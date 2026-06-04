"""Generic money-context safety for shadow RateCon total-rate ranking.

This module is intentionally broker-agnostic. It adds safe metadata and an
explicit shadow-only abstention profile for total_carrier_rate candidates; it
does not change legacy authoritative extraction or production output.
"""

from __future__ import annotations

import re


FIELD_TOTAL_CARRIER_RATE = "total_carrier_rate"
FIELD_ACCESSORIAL_TERM = "accessorial_term"

RATE_MONEY_SAFE = "safe"
RATE_MONEY_RISKY = "risky"
RATE_MONEY_UNSAFE = "unsafe"
RATE_MONEY_UNKNOWN = "unknown"

RATE_SELECTION_ALLOWED = "allowed"
RATE_SELECTION_WEAK_ONLY = "weak_only"
RATE_SELECTION_ABSTAIN = "abstain"

MONEY_CONTEXT_TOTAL_CARRIER_PAY = "total_carrier_pay"
MONEY_CONTEXT_CARRIER_FREIGHT_PAY = "carrier_freight_pay"
MONEY_CONTEXT_TOTAL_RATE = "total_rate"
MONEY_CONTEXT_TOTAL_COST = "total_cost"
MONEY_CONTEXT_ESTIMATED_RATE_TO_TRUCK = "estimated_rate_to_truck"
MONEY_CONTEXT_AGREED_RATE_TOTAL = "agreed_rate_total"
MONEY_CONTEXT_LINEHAUL_TOTAL = "linehaul_total"
MONEY_CONTEXT_LINE_ITEM_RATE = "line_item_rate"
MONEY_CONTEXT_PER_UNIT_RATE = "per_unit_rate"
MONEY_CONTEXT_ACCESSORIAL = "accessorial"
MONEY_CONTEXT_DEDUCTION = "deduction"
MONEY_CONTEXT_FEE = "fee"
MONEY_CONTEXT_QUICKPAY = "quickpay"
MONEY_CONTEXT_FUEL_ADVANCE = "fuel_advance"
MONEY_CONTEXT_COMCHECK_FEE = "comcheck_fee"
MONEY_CONTEXT_TRACKING_HOLD = "tracking_hold"
MONEY_CONTEXT_PENALTY = "penalty"
MONEY_CONTEXT_PAYMENT_TERMS = "payment_terms_amount"
MONEY_CONTEXT_UNKNOWN = "unknown"

DOCUMENT_REGION_PAYMENT_SUMMARY = "payment_summary"
DOCUMENT_REGION_LOAD_INFO_RATE_TABLE = "load_info_rate_table"
DOCUMENT_REGION_RATE_LINE_ITEM = "rate_line_item"
DOCUMENT_REGION_ACCESSORIAL = "accessorial_section"
DOCUMENT_REGION_INSTRUCTIONS = "instructions"
DOCUMENT_REGION_QUICKPAY_TERMS = "quickpay_terms"
DOCUMENT_REGION_FOOTER = "footer_signature"
DOCUMENT_REGION_UNKNOWN = "unknown"

SAFE_TOTAL_CONTEXTS = {
    MONEY_CONTEXT_TOTAL_CARRIER_PAY,
    MONEY_CONTEXT_TOTAL_RATE,
    MONEY_CONTEXT_TOTAL_COST,
    MONEY_CONTEXT_ESTIMATED_RATE_TO_TRUCK,
    MONEY_CONTEXT_AGREED_RATE_TOTAL,
}

NEGATIVE_CONTEXTS = {
    MONEY_CONTEXT_ACCESSORIAL,
    MONEY_CONTEXT_DEDUCTION,
    MONEY_CONTEXT_FEE,
    MONEY_CONTEXT_QUICKPAY,
    MONEY_CONTEXT_FUEL_ADVANCE,
    MONEY_CONTEXT_COMCHECK_FEE,
    MONEY_CONTEXT_TRACKING_HOLD,
    MONEY_CONTEXT_PENALTY,
    MONEY_CONTEXT_PAYMENT_TERMS,
}

PER_UNIT_MARKERS = (
    "per mile",
    "per mi",
    "/mi",
    "rate/mi",
    "unit rate",
    "per unit",
    "rate per",
)


def _text(value) -> str:
    return str(value or "").strip()


def _lower(value) -> str:
    return _text(value).lower()


def _metadata(candidate) -> dict:
    metadata = (candidate or {}).get("metadata")
    return dict(metadata) if isinstance(metadata, dict) else {}


def _candidate_field(candidate) -> str:
    return _lower((candidate or {}).get("field")).replace(" ", "_").replace("-", "_")


def _context_text(candidate, metadata) -> str:
    return " ".join(
        _lower(value)
        for value in [
            (candidate or {}).get("label"),
            (candidate or {}).get("evidence_text"),
            metadata.get("raw_field"),
            metadata.get("section_context"),
            metadata.get("money_context"),
            metadata.get("value_type"),
            metadata.get("semantic_role"),
            metadata.get("pairing_method"),
            metadata.get("table_context_role"),
            metadata.get("table_row_role"),
            metadata.get("document_region"),
        ]
        if _text(value)
    )


def _has_any(text: str, markers) -> bool:
    return any(marker in text for marker in markers)


def _normalize_money_context(metadata, context: str) -> str:
    existing = _lower(metadata.get("money_context"))
    if _has_any(context, ["quickpay", "quick pay"]):
        return MONEY_CONTEXT_QUICKPAY
    if _has_any(context, ["comcheck", "com check"]):
        return MONEY_CONTEXT_COMCHECK_FEE
    if _has_any(context, ["tracking hold", "tracking fee", "holdback"]):
        return MONEY_CONTEXT_TRACKING_HOLD
    if _has_any(context, ["fuel advance", "advance"]):
        return MONEY_CONTEXT_FUEL_ADVANCE
    if _has_any(context, ["deduction", "deduct", "chargeback"]):
        return MONEY_CONTEXT_DEDUCTION
    if _has_any(context, ["penalty", "tonu", "truck order not used", "late fee"]):
        return MONEY_CONTEXT_PENALTY
    if _has_any(context, ["detention", "layover", "lumper", "accessorial"]):
        return MONEY_CONTEXT_ACCESSORIAL
    if re.search(r"\bfee\b", context):
        return MONEY_CONTEXT_FEE
    if _has_any(context, ["payment terms", "net 30", "net30", "days to pay"]):
        return MONEY_CONTEXT_PAYMENT_TERMS
    if _has_any(context, PER_UNIT_MARKERS):
        return MONEY_CONTEXT_PER_UNIT_RATE
    if _has_any(context, ["total carrier pay", "amount due to carrier", "carrier total"]):
        return MONEY_CONTEXT_TOTAL_CARRIER_PAY
    if _has_any(context, ["estimated rate to truck", "estimated rate (to truck)", "to truck"]):
        return MONEY_CONTEXT_ESTIMATED_RATE_TO_TRUCK
    if _has_any(context, ["agreed rate total", "agreed amount total"]):
        return MONEY_CONTEXT_AGREED_RATE_TOTAL
    if _has_any(context, ["carrier freight pay", "freight pay"]):
        return MONEY_CONTEXT_CARRIER_FREIGHT_PAY
    if _has_any(context, ["linehaul total", "line haul total", "freight charge total"]):
        return MONEY_CONTEXT_LINEHAUL_TOTAL
    if _has_any(context, ["linehaul", "line haul"]):
        return MONEY_CONTEXT_LINE_ITEM_RATE
    if _has_any(context, ["total cost"]):
        return MONEY_CONTEXT_TOTAL_COST
    if _has_any(context, ["total rate-usd", "total rate usd", "total rate"]):
        return MONEY_CONTEXT_TOTAL_RATE
    if existing in {"carrier_pay", "total_carrier_pay"}:
        return MONEY_CONTEXT_TOTAL_CARRIER_PAY
    if existing in {"total_rate", "agreed_amount", "agreed_rate"}:
        return MONEY_CONTEXT_TOTAL_RATE
    if existing in {"linehaul", "linehaul_total"}:
        return MONEY_CONTEXT_LINEHAUL_TOTAL
    if existing:
        return existing
    return MONEY_CONTEXT_UNKNOWN


def _document_region(metadata, context: str, money_context: str) -> str:
    existing = _lower(metadata.get("document_region"))
    section = _lower(metadata.get("section_context"))
    if money_context == MONEY_CONTEXT_QUICKPAY:
        return DOCUMENT_REGION_QUICKPAY_TERMS
    if money_context in NEGATIVE_CONTEXTS:
        return (
            DOCUMENT_REGION_INSTRUCTIONS
            if money_context
            in {
                MONEY_CONTEXT_QUICKPAY,
                MONEY_CONTEXT_FUEL_ADVANCE,
                MONEY_CONTEXT_COMCHECK_FEE,
                MONEY_CONTEXT_TRACKING_HOLD,
                MONEY_CONTEXT_PAYMENT_TERMS,
            }
            else DOCUMENT_REGION_ACCESSORIAL
        )
    if section in {"instructions", "terms"} or _has_any(
        context,
        ["instructions", "terms", "footer", "signature"],
    ):
        return DOCUMENT_REGION_INSTRUCTIONS
    if section in {"rate", "charges"} or money_context in SAFE_TOTAL_CONTEXTS:
        return DOCUMENT_REGION_PAYMENT_SUMMARY
    if money_context in {MONEY_CONTEXT_LINEHAUL_TOTAL, MONEY_CONTEXT_LINE_ITEM_RATE, MONEY_CONTEXT_PER_UNIT_RATE}:
        return DOCUMENT_REGION_RATE_LINE_ITEM
    if existing:
        return existing
    return DOCUMENT_REGION_UNKNOWN


def _rate_safety(money_context: str, document_region: str, metadata) -> tuple[str, str]:
    if document_region in {DOCUMENT_REGION_INSTRUCTIONS, DOCUMENT_REGION_FOOTER, DOCUMENT_REGION_QUICKPAY_TERMS}:
        return RATE_MONEY_UNSAFE, "instructions_terms_or_footer_money"
    if money_context in NEGATIVE_CONTEXTS:
        return RATE_MONEY_UNSAFE, money_context
    if money_context == MONEY_CONTEXT_PER_UNIT_RATE:
        return RATE_MONEY_UNSAFE, "per_unit_rate"
    if money_context == MONEY_CONTEXT_LINE_ITEM_RATE:
        return RATE_MONEY_UNSAFE, "line_item_rate"
    if money_context in SAFE_TOTAL_CONTEXTS:
        return RATE_MONEY_SAFE, ""
    if money_context == MONEY_CONTEXT_CARRIER_FREIGHT_PAY:
        return RATE_MONEY_RISKY, "carrier_freight_pay_requires_no_explicit_total"
    if money_context == MONEY_CONTEXT_LINEHAUL_TOTAL:
        return RATE_MONEY_RISKY, "linehaul_total_requires_no_addons"
    if int(metadata.get("money_like_cell_count_in_row") or 0) > 1:
        return RATE_MONEY_RISKY, "multi_money_row"
    return RATE_MONEY_UNKNOWN, "money_context_unknown"


def enrich_rate_money_safety(candidate):
    """Return a candidate copy with generic rate safety metadata."""
    if not isinstance(candidate, dict):
        return candidate
    item = dict(candidate)
    metadata = _metadata(item)
    context = _context_text(item, metadata)
    money_context = _normalize_money_context(metadata, context)
    document_region = _document_region(metadata, context, money_context)
    safety, reason = _rate_safety(money_context, document_region, metadata)
    metadata["money_context"] = money_context
    metadata["document_region"] = document_region
    metadata["is_total_pay_candidate"] = money_context in SAFE_TOTAL_CONTEXTS or money_context == MONEY_CONTEXT_CARRIER_FREIGHT_PAY
    metadata["is_total_rate_candidate"] = metadata["is_total_pay_candidate"]
    metadata["is_line_item_only"] = money_context in {
        MONEY_CONTEXT_LINE_ITEM_RATE,
        MONEY_CONTEXT_PER_UNIT_RATE,
    }
    metadata["is_per_unit_rate"] = money_context == MONEY_CONTEXT_PER_UNIT_RATE
    metadata["is_deduction_or_penalty"] = money_context in {
        MONEY_CONTEXT_DEDUCTION,
        MONEY_CONTEXT_FEE,
        MONEY_CONTEXT_QUICKPAY,
        MONEY_CONTEXT_FUEL_ADVANCE,
        MONEY_CONTEXT_COMCHECK_FEE,
        MONEY_CONTEXT_TRACKING_HOLD,
        MONEY_CONTEXT_PENALTY,
    }
    metadata["is_payment_terms_amount"] = money_context == MONEY_CONTEXT_PAYMENT_TERMS
    metadata["is_accessorial_only"] = money_context == MONEY_CONTEXT_ACCESSORIAL
    metadata["rate_safety"] = safety
    metadata["rate_safety_reason"] = reason
    if reason and not metadata.get("context_penalty_reason"):
        metadata["context_penalty_reason"] = reason
    item["metadata"] = metadata
    return item


def _money_value(candidate) -> str:
    return _text((candidate or {}).get("normalized_value") or (candidate or {}).get("value"))


def _normalized_amount_key(value: str) -> str:
    text = _text(value).upper().replace("USD", "").replace("$", "").replace(",", "")
    return re.sub(r"\s+", "", text)


def _candidate_is_rate(candidate) -> bool:
    return _candidate_field(candidate) == FIELD_TOTAL_CARRIER_RATE


def _explicit_safe_total_values(candidates):
    values = set()
    for candidate in candidates or []:
        if not _candidate_is_rate(candidate):
            continue
        item = enrich_rate_money_safety(candidate)
        metadata = _metadata(item)
        if metadata.get("money_context") in SAFE_TOTAL_CONTEXTS and metadata.get("rate_safety") == RATE_MONEY_SAFE:
            value = _normalized_amount_key(_money_value(item))
            if value:
                values.add(value)
    return values


def _negative_money_present(candidates) -> bool:
    for candidate in candidates or []:
        if not _candidate_is_rate(candidate):
            continue
        metadata = _metadata(enrich_rate_money_safety(candidate))
        if metadata.get("money_context") in NEGATIVE_CONTEXTS:
            return True
    return False


def _rate_abstention_decision(candidate, explicit_total_values, negative_money_present=False) -> dict:
    item = enrich_rate_money_safety(candidate)
    metadata = _metadata(item)
    money_context = _text(metadata.get("money_context"))
    safety = _text(metadata.get("rate_safety")) or RATE_MONEY_UNKNOWN
    value_key = _normalized_amount_key(_money_value(item))
    explicit_total_exists = bool(explicit_total_values)
    policy = RATE_SELECTION_ALLOWED
    reason = ""

    if safety == RATE_MONEY_UNSAFE:
        policy = RATE_SELECTION_ABSTAIN
        reason = metadata.get("rate_safety_reason") or f"{money_context}_unsafe"
    elif money_context == MONEY_CONTEXT_CARRIER_FREIGHT_PAY:
        if explicit_total_exists and value_key not in explicit_total_values:
            policy = RATE_SELECTION_ABSTAIN
            reason = "carrier_freight_pay_conflicts_with_explicit_total"
        else:
            policy = RATE_SELECTION_ALLOWED
    elif money_context == MONEY_CONTEXT_LINEHAUL_TOTAL:
        if explicit_total_exists:
            policy = RATE_SELECTION_ABSTAIN
            reason = "linehaul_total_conflicts_with_explicit_total"
        elif negative_money_present:
            policy = RATE_SELECTION_ABSTAIN
            reason = "linehaul_total_with_addons_or_deductions"
        else:
            policy = RATE_SELECTION_WEAK_ONLY
            reason = "linehaul_total_without_explicit_total"
    elif safety in {RATE_MONEY_RISKY, RATE_MONEY_UNKNOWN}:
        if explicit_total_exists:
            policy = RATE_SELECTION_ABSTAIN
            reason = metadata.get("rate_safety_reason") or "risky_money_context_with_explicit_total"
        else:
            policy = RATE_SELECTION_WEAK_ONLY
            reason = metadata.get("rate_safety_reason") or "risky_money_context"

    return {
        "rate_abstained": policy == RATE_SELECTION_ABSTAIN,
        "rate_abstention_reason": _text(reason),
        "selection_policy": policy,
        "review_required": policy != RATE_SELECTION_ALLOWED,
    }


def _append_adjustment(metadata, reason, amount):
    adjustments = list(metadata.get("rate_candidate_profile_adjustments") or [])
    adjustments.append({"reason": reason, "amount": round(float(amount), 3)})
    metadata["rate_candidate_profile_adjustments"] = adjustments


def _apply_rate_decision(candidate, decision):
    item = enrich_rate_money_safety(candidate)
    metadata = _metadata(item)
    metadata.update(decision)
    original_confidence = float(item.get("confidence") or 0.0)
    policy = decision.get("selection_policy")
    if policy == RATE_SELECTION_ABSTAIN:
        capped = min(original_confidence, 0.35)
        item["confidence"] = round(capped, 3)
        if _candidate_is_rate(item):
            item["field"] = FIELD_ACCESSORIAL_TERM
            metadata["rate_demoted_from_total_carrier_rate"] = True
        metadata["label_strength"] = "weak"
        _append_adjustment(
            metadata,
            decision.get("rate_abstention_reason") or "rate_money_abstained",
            capped - original_confidence,
        )
    elif policy == RATE_SELECTION_WEAK_ONLY:
        capped = min(original_confidence, 0.55)
        item["confidence"] = round(capped, 3)
        metadata["label_strength"] = "weak"
        _append_adjustment(
            metadata,
            decision.get("rate_abstention_reason") or "rate_money_weak_only",
            capped - original_confidence,
        )
    item["metadata"] = metadata
    return item


def apply_rate_money_abstention_profile_to_candidates(candidates):
    """Apply shadow-only total-rate money abstention to candidate copies."""
    enriched = [enrich_rate_money_safety(candidate) for candidate in candidates or []]
    explicit_total_values = _explicit_safe_total_values(enriched)
    has_negative_money = _negative_money_present(enriched)
    adjusted = []
    for candidate in enriched:
        if _candidate_is_rate(candidate):
            decision = _rate_abstention_decision(
                candidate,
                explicit_total_values,
                negative_money_present=has_negative_money,
            )
            adjusted.append(_apply_rate_decision(candidate, decision))
        else:
            adjusted.append(candidate)
    return adjusted
