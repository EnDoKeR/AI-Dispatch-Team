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

TOTAL_CARRIER_PAY_CONTEXT_MARKERS = (
    "total carrier pay",
    "amount due to carrier",
    "carrier total",
)
ESTIMATED_RATE_TO_TRUCK_CONTEXT_MARKERS = (
    "estimated rate to truck",
    "estimated rate (to truck)",
    "to truck",
)
AGREED_RATE_TOTAL_CONTEXT_MARKERS = (
    "agreed rate total",
    "agreed amount total",
)
CARRIER_FREIGHT_PAY_CONTEXT_MARKERS = (
    "carrier freight pay",
    "freight pay",
)
LINEHAUL_TOTAL_CONTEXT_MARKERS = (
    "linehaul total",
    "line haul total",
    "freight charge total",
)
TOTAL_COST_CONTEXT_MARKERS = ("total cost",)
TOTAL_RATE_CONTEXT_MARKERS = (
    "total rate-usd",
    "total rate usd",
    "total rate",
)
TOTAL_PAY_CONTEXT_MARKERS = (
    TOTAL_CARRIER_PAY_CONTEXT_MARKERS
    + ESTIMATED_RATE_TO_TRUCK_CONTEXT_MARKERS
    + AGREED_RATE_TOTAL_CONTEXT_MARKERS
    + CARRIER_FREIGHT_PAY_CONTEXT_MARKERS
    + LINEHAUL_TOTAL_CONTEXT_MARKERS
    + TOTAL_COST_CONTEXT_MARKERS
    + TOTAL_RATE_CONTEXT_MARKERS
)
TOTAL_PAY_STRONG_LABELS = (
    "total carrier pay",
    "total carrier rate",
    "carrier pay",
    "total rate",
    "agreed amount",
)
LEGACY_MAIN_RATE_LABELS = (
    "carrier pay",
    "total rate",
    "agreed amount",
    "linehaul",
    "line haul",
    "total carrier rate",
    "total carrier pay",
    "total charge",
    "freight charge",
    "rate",
)
LEGACY_MAIN_RATE_LABEL_TYPES = (
    ("total carrier pay", "total_carrier_pay"),
    ("total carrier rate", "total_carrier_pay"),
    ("carrier pay", "total_carrier_pay"),
    ("total rate", "total_carrier_pay"),
    ("agreed amount", "agreed_amount"),
    ("linehaul", "linehaul"),
    ("line haul", "linehaul"),
    ("total charge", "total_charge"),
    ("freight charge", "total_charge"),
    ("rate", "unknown_money"),
)
CONTEXT_FEATURE_TOTAL_CARRIER_PAY_MARKERS = (
    "total carrier pay",
    "amount due to carrier",
    "carrier total",
    "to truck",
)
CONTEXT_FEATURE_TOTAL_RATE_MARKERS = (
    "total cost",
    "total rate",
    "agreed rate total",
    "estimated rate",
)
CONTEXT_FEATURE_LINE_ITEM_MARKERS = (
    "linehaul",
    "line haul",
    "per mile",
    "per unit",
)
QUICK_PAY_NOISE_LABELS = (
    "quickpay",
    "quick pay",
)
COMCHECK_FEE_LABELS = (
    "comcheck",
    "com check",
)
TRACKING_HOLD_LABELS = (
    "tracking hold",
    "tracking fee",
    "holdback",
)
FUEL_ADVANCE_LABELS = (
    "fuel advance",
    "advance",
)
RATE_DEDUCTION_LABELS = (
    "deduction",
    "deduct",
    "chargeback",
)
FEE_PENALTY_NOISE_LABELS = (
    "penalty",
    "tonu",
    "truck order not used",
    "late fee",
)
ACCESSORIAL_CONTEXT_MARKERS = (
    "detention",
    "layover",
    "lumper",
    "accessorial",
)
BILLING_INSTRUCTION_NOISE_LABELS = (
    "payment terms",
    "net 30",
    "net30",
    "days to pay",
)
MONEY_CONTEXT_NOISE_MARKERS = (
    QUICK_PAY_NOISE_LABELS
    + COMCHECK_FEE_LABELS
    + TRACKING_HOLD_LABELS
    + FUEL_ADVANCE_LABELS
    + RATE_DEDUCTION_LABELS
    + FEE_PENALTY_NOISE_LABELS
    + ACCESSORIAL_CONTEXT_MARKERS
    + BILLING_INSTRUCTION_NOISE_LABELS
)
RATE_NEGATIVE_LABELS = (
    "fuel",
    "detention",
    "layover",
    "lumper",
    "quickpay",
    "quick pay",
    "deduction",
    "penalty",
    "tonu",
    "insurance",
    "advance",
    "accessorial",
)
ACCESSORIAL_CHARGE_LABELS = (
    "detention",
    "layover",
    "lumper",
    "tonu",
    "quick pay",
    "fuel surcharge",
    "accessorial",
    "fee",
    "penalty",
    "deduction",
)
ACCESSORIAL_LABEL_TYPES = (
    ("detention", "detention_pay"),
    ("layover", "layover_pay"),
    ("lumper", "lumper_pay"),
    ("tonu", "TONU_pay"),
    ("truck order not used", "TONU_pay"),
    ("quick pay", "quick_pay_discount"),
    ("fuel surcharge", "accessorial"),
    ("accessorial", "accessorial"),
    ("fee", "accessorial"),
    ("penalty", "deduction"),
    ("deduction", "deduction"),
)
LAYOUT_ACCESSORIAL_LABEL_TYPES = (
    ("tracking bonus", "tracking_bonus"),
    ("on time bonus", "on_time_bonus"),
    ("detention", "detention_pay"),
    ("tonu", "TONU_pay"),
    ("truck order not used", "TONU_pay"),
    ("deduction", "deduction"),
    ("penalty", "deduction"),
    ("quick pay", "quick_pay_discount"),
    ("discount", "quick_pay_discount"),
    ("accessorial", "accessorial"),
    ("fee", "accessorial"),
)
CONTEXT_FEATURE_PENALTY_MARKERS = (
    "tracking hold",
    "penalty",
    "tonu",
    "late fee",
)
CONTEXT_FEATURE_FUEL_ADVANCE_MARKERS = (
    "fuel advance",
    "advance",
    "comcheck",
)
OCR_UNSAFE_RATE_CONTEXTS = (
    MONEY_CONTEXT_ACCESSORIAL,
    MONEY_CONTEXT_DEDUCTION,
    MONEY_CONTEXT_FEE,
    MONEY_CONTEXT_QUICKPAY,
    MONEY_CONTEXT_FUEL_ADVANCE,
    MONEY_CONTEXT_COMCHECK_FEE,
    MONEY_CONTEXT_TRACKING_HOLD,
    MONEY_CONTEXT_PENALTY,
    MONEY_CONTEXT_PAYMENT_TERMS,
    MONEY_CONTEXT_LINE_ITEM_RATE,
    MONEY_CONTEXT_PER_UNIT_RATE,
)

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


def get_total_pay_positive_labels():
    """Return canonical total-pay/main-rate context markers in stable order."""
    return TOTAL_PAY_CONTEXT_MARKERS


def get_total_pay_strong_labels():
    """Return resolver-compatible strong total-pay labels in stable order."""
    return TOTAL_PAY_STRONG_LABELS


def get_total_pay_heading_labels():
    """Return legacy main-rate heading labels in stable order."""
    return LEGACY_MAIN_RATE_LABELS


def get_total_pay_context_markers():
    """Return canonical context markers used by money-context classification."""
    return TOTAL_PAY_CONTEXT_MARKERS


def get_legacy_main_rate_label_types():
    """Return legacy generator label-to-value-type mappings in stable order."""
    return LEGACY_MAIN_RATE_LABEL_TYPES


def get_total_pay_label_types():
    """Return legacy-compatible total-pay label-to-value-type mappings."""
    return get_legacy_main_rate_label_types()


def get_carrier_freight_pay_context_markers():
    """Return carrier-freight-pay context markers in stable order."""
    return CARRIER_FREIGHT_PAY_CONTEXT_MARKERS


def get_linehaul_total_context_markers():
    """Return linehaul-total context markers in stable order."""
    return LINEHAUL_TOTAL_CONTEXT_MARKERS


def get_context_feature_total_carrier_pay_markers():
    """Return context-feature compatibility markers for total carrier pay."""
    return CONTEXT_FEATURE_TOTAL_CARRIER_PAY_MARKERS


def get_context_feature_total_rate_markers():
    """Return context-feature compatibility markers for total rate context."""
    return CONTEXT_FEATURE_TOTAL_RATE_MARKERS


def get_context_feature_line_item_markers():
    """Return context-feature compatibility markers for line-item rates."""
    return CONTEXT_FEATURE_LINE_ITEM_MARKERS


def get_accessorial_charge_labels():
    """Return legacy accessorial charge labels in stable order."""
    return ACCESSORIAL_CHARGE_LABELS


def get_accessorial_noise_labels():
    """Return current non-total accessorial/noise markers in stable order."""
    return MONEY_CONTEXT_NOISE_MARKERS


def get_accessorial_label_types():
    """Return legacy accessorial label-to-value-type mappings."""
    return ACCESSORIAL_LABEL_TYPES


def get_layout_accessorial_label_types():
    """Return layout accessorial label-to-value-type mappings."""
    return LAYOUT_ACCESSORIAL_LABEL_TYPES


def get_rate_negative_labels():
    """Return resolver-compatible negative rate labels in stable order."""
    return RATE_NEGATIVE_LABELS


def get_rate_deduction_labels():
    """Return current deduction/chargeback context markers."""
    return RATE_DEDUCTION_LABELS


def get_quick_pay_noise_labels():
    """Return current quick-pay context markers."""
    return QUICK_PAY_NOISE_LABELS


def get_fee_penalty_noise_labels():
    """Return current penalty/TONU/late-fee context markers."""
    return FEE_PENALTY_NOISE_LABELS


def get_billing_instruction_noise_labels():
    """Return current payment-term/billing noise markers."""
    return BILLING_INSTRUCTION_NOISE_LABELS


def get_money_context_noise_markers():
    """Return current non-total money-context noise markers."""
    return MONEY_CONTEXT_NOISE_MARKERS


def get_comcheck_fee_labels():
    """Return current comcheck context markers."""
    return COMCHECK_FEE_LABELS


def get_tracking_hold_labels():
    """Return current tracking-hold context markers."""
    return TRACKING_HOLD_LABELS


def get_fuel_advance_labels():
    """Return current fuel-advance context markers."""
    return FUEL_ADVANCE_LABELS


def get_accessorial_context_markers():
    """Return current accessorial context markers."""
    return ACCESSORIAL_CONTEXT_MARKERS


def get_context_feature_penalty_markers():
    """Return context-feature compatibility markers for penalties."""
    return CONTEXT_FEATURE_PENALTY_MARKERS


def get_context_feature_fuel_advance_markers():
    """Return context-feature compatibility markers for fuel advances."""
    return CONTEXT_FEATURE_FUEL_ADVANCE_MARKERS


def get_ocr_unsafe_rate_contexts():
    """Return OCR policy contexts that remain unsafe/non-total."""
    return set(OCR_UNSAFE_RATE_CONTEXTS)


def is_total_pay_label(text: str) -> bool:
    """Return whether text matches current total-pay/main-rate context markers."""
    return _has_any(_lower(text), get_total_pay_context_markers())


def is_strong_total_pay_context(text: str) -> bool:
    """Return whether text matches current resolver strong total-pay labels."""
    return _has_any(_lower(text), get_total_pay_strong_labels())


def is_accessorial_money_context(text: str) -> bool:
    """Return whether text matches current accessorial money-context markers."""
    return _has_any(_lower(text), get_accessorial_context_markers())


def is_rate_deduction_or_fee_context(text: str) -> bool:
    """Return whether text matches current deduction/fee/penalty markers."""
    context = _lower(text)
    return (
        _has_any(context, get_rate_deduction_labels())
        or _has_any(context, get_comcheck_fee_labels())
        or _has_any(context, get_tracking_hold_labels())
        or _has_any(context, get_fuel_advance_labels())
        or _has_any(context, get_fee_penalty_noise_labels())
        or bool(re.search(r"\bfee\b", context))
    )


def is_quick_pay_or_billing_noise_context(text: str) -> bool:
    """Return whether text matches current quick-pay or billing noise markers."""
    context = _lower(text)
    return _has_any(context, get_quick_pay_noise_labels()) or _has_any(
        context,
        get_billing_instruction_noise_labels(),
    )


def is_non_total_money_noise_context(text: str) -> bool:
    """Return whether text matches current non-total money noise markers."""
    context = _lower(text)
    return _has_any(context, get_money_context_noise_markers()) or bool(
        re.search(r"\bfee\b", context)
    )


def _normalize_money_context(metadata, context: str) -> str:
    existing = _lower(metadata.get("money_context"))
    if _has_any(context, QUICK_PAY_NOISE_LABELS):
        return MONEY_CONTEXT_QUICKPAY
    if _has_any(context, COMCHECK_FEE_LABELS):
        return MONEY_CONTEXT_COMCHECK_FEE
    if _has_any(context, TRACKING_HOLD_LABELS):
        return MONEY_CONTEXT_TRACKING_HOLD
    if _has_any(context, FUEL_ADVANCE_LABELS):
        return MONEY_CONTEXT_FUEL_ADVANCE
    if _has_any(context, RATE_DEDUCTION_LABELS):
        return MONEY_CONTEXT_DEDUCTION
    if _has_any(context, FEE_PENALTY_NOISE_LABELS):
        return MONEY_CONTEXT_PENALTY
    if _has_any(context, ACCESSORIAL_CONTEXT_MARKERS):
        return MONEY_CONTEXT_ACCESSORIAL
    if re.search(r"\bfee\b", context):
        return MONEY_CONTEXT_FEE
    if _has_any(context, BILLING_INSTRUCTION_NOISE_LABELS):
        return MONEY_CONTEXT_PAYMENT_TERMS
    if _has_any(context, PER_UNIT_MARKERS):
        return MONEY_CONTEXT_PER_UNIT_RATE
    if _has_any(context, TOTAL_CARRIER_PAY_CONTEXT_MARKERS):
        return MONEY_CONTEXT_TOTAL_CARRIER_PAY
    if _has_any(context, ESTIMATED_RATE_TO_TRUCK_CONTEXT_MARKERS):
        return MONEY_CONTEXT_ESTIMATED_RATE_TO_TRUCK
    if _has_any(context, AGREED_RATE_TOTAL_CONTEXT_MARKERS):
        return MONEY_CONTEXT_AGREED_RATE_TOTAL
    if _has_any(context, CARRIER_FREIGHT_PAY_CONTEXT_MARKERS):
        return MONEY_CONTEXT_CARRIER_FREIGHT_PAY
    if _has_any(context, LINEHAUL_TOTAL_CONTEXT_MARKERS):
        return MONEY_CONTEXT_LINEHAUL_TOTAL
    if _has_any(context, ["linehaul", "line haul"]):
        return MONEY_CONTEXT_LINE_ITEM_RATE
    if _has_any(context, TOTAL_COST_CONTEXT_MARKERS):
        return MONEY_CONTEXT_TOTAL_COST
    if _has_any(context, TOTAL_RATE_CONTEXT_MARKERS):
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
