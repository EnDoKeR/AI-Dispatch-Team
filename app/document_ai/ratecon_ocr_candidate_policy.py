"""Shadow-only OCR candidate policy for RateCon diagnostics.

The policy in this module is intentionally local and conservative. It never
invokes OCR, never changes legacy output, and only reshapes candidate metadata
for the shadow resolver when explicitly requested.
"""

from __future__ import annotations

from app.document_ai.ratecon_rate_money_safety import (
    FIELD_ACCESSORIAL_TERM,
    FIELD_TOTAL_CARRIER_RATE,
    RATE_MONEY_SAFE,
    RATE_MONEY_UNSAFE,
    RATE_MONEY_UNKNOWN,
    RATE_SELECTION_ABSTAIN,
    RATE_SELECTION_ALLOWED,
    enrich_rate_money_safety,
    get_ocr_unsafe_rate_contexts,
)


OCR_CANDIDATE_POLICY_BASELINE = "baseline"
OCR_CANDIDATE_POLICY_FILL_MISSING_STRICT_V1 = "fill_missing_strict_v1"
OCR_CANDIDATE_POLICIES = {
    OCR_CANDIDATE_POLICY_BASELINE,
    OCR_CANDIDATE_POLICY_FILL_MISSING_STRICT_V1,
}

FIELD_LOAD_NUMBER = "load_number"
FIELD_REFERENCE_NUMBERS = "reference_numbers"
SOURCE_OCR = "ocr"

_PRIMARY_OCR_LOAD_HINTS = {
    "load",
    "order",
    "shipment",
    "po",
    "pro",
    "freight_bill",
    "confirmation",
    "tender",
    "trip",
}
_PRIMARY_OCR_LOAD_REGIONS = {"document_title", "header", "load_info"}
_WEAK_OCR_LOAD_HINTS = {
    "pickup_ref",
    "delivery_ref",
    "bol",
    "reference",
    "vehicle_noise",
    "unknown",
}
_UNSAFE_OCR_RATE_CONTEXTS = get_ocr_unsafe_rate_contexts()


def _text(value) -> str:
    return str(value or "").strip()


def _lower(value) -> str:
    return _text(value).lower()


def _metadata(candidate) -> dict:
    metadata = (candidate or {}).get("metadata")
    return dict(metadata) if isinstance(metadata, dict) else {}


def _field(candidate) -> str:
    return _lower((candidate or {}).get("field")).replace(" ", "_").replace("-", "_")


def _is_ocr_candidate(candidate) -> bool:
    metadata = _metadata(candidate)
    return _lower((candidate or {}).get("source")) == SOURCE_OCR or bool(
        metadata.get("ocr_candidate")
    )


def _copy_candidate(candidate):
    item = dict(candidate or {})
    item["metadata"] = _metadata(item)
    return item


def _append_policy_adjustment(metadata, reason, amount=0.0):
    adjustments = list(metadata.get("ocr_candidate_policy_adjustments") or [])
    adjustments.append({"reason": reason, "amount": round(float(amount), 3)})
    metadata["ocr_candidate_policy_adjustments"] = adjustments


def _is_safe_ocr_header_load_alias(candidate) -> bool:
    metadata = _metadata(candidate)
    if not metadata.get("header_load_identity_candidate"):
        return False
    hint = _lower(metadata.get("id_type_hint"))
    region = _lower(metadata.get("document_region"))
    penalty = _lower(metadata.get("context_penalty_reason"))
    if (
        metadata.get("is_primary_identifier_candidate")
        and hint in _PRIMARY_OCR_LOAD_HINTS
        and region in _PRIMARY_OCR_LOAD_REGIONS
        and not penalty
    ):
        return True
    # OCR sectioning is coarse on low-text scans. Keep this narrow to explicit
    # primary-ID labels and reject stop/BOL/reference penalties.
    return bool(
        hint in _PRIMARY_OCR_LOAD_HINTS
        and hint not in {"po", "pro", "freight_bill"}
        and penalty in {"", "money_context_unknown"}
    )


def _apply_ocr_load_policy(candidate, policy):
    item = _copy_candidate(candidate)
    metadata = _metadata(item)
    if policy != OCR_CANDIDATE_POLICY_FILL_MISSING_STRICT_V1 or not _is_ocr_candidate(item):
        return item

    metadata["ocr_candidate"] = True
    metadata["ocr_candidate_policy"] = policy
    hint = _lower(metadata.get("id_type_hint"))
    if _field(item) == FIELD_REFERENCE_NUMBERS and _is_safe_ocr_header_load_alias(item):
        original_confidence = float(item.get("confidence") or 0.0)
        item["field"] = FIELD_LOAD_NUMBER
        if original_confidence < 0.75:
            item["confidence"] = 0.76
        metadata["ocr_load_promoted_to_load_number"] = True
        metadata["ocr_candidate_policy_reason"] = "ocr_header_load_identity_promoted"
        metadata["selection_policy"] = RATE_SELECTION_ALLOWED
        _append_policy_adjustment(
            metadata,
            "ocr_header_load_identity_promoted",
            float(item.get("confidence") or 0.0) - original_confidence,
        )
    elif hint in _WEAK_OCR_LOAD_HINTS:
        metadata["selection_policy"] = metadata.get("selection_policy") or "weak_only"
        metadata["ocr_candidate_policy_reason"] = "ocr_weak_or_reference_identifier"
    item["metadata"] = metadata
    return item


def _non_ocr_rate_candidate_available(candidates) -> bool:
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        if _field(candidate) != FIELD_TOTAL_CARRIER_RATE:
            continue
        if _is_ocr_candidate(candidate):
            continue
        metadata = _metadata(enrich_rate_money_safety(candidate))
        if metadata.get("rate_abstained") or metadata.get("rate_demoted_from_total_carrier_rate"):
            continue
        if _text(candidate.get("value")) or _text(candidate.get("normalized_value")):
            return True
    return False


def _apply_ocr_rate_policy(candidate, policy, non_ocr_rate_available=False):
    if policy != OCR_CANDIDATE_POLICY_FILL_MISSING_STRICT_V1:
        return candidate
    item = enrich_rate_money_safety(candidate)
    metadata = _metadata(item)
    if not _is_ocr_candidate(item):
        return item
    metadata["ocr_candidate"] = True
    metadata["ocr_candidate_policy"] = policy
    if _field(item) == FIELD_ACCESSORIAL_TERM:
        metadata["ocr_accessorial_diagnostic_only"] = True
        metadata.setdefault("selection_policy", RATE_SELECTION_ABSTAIN)
        item["metadata"] = metadata
        return item
    if _field(item) != FIELD_TOTAL_CARRIER_RATE:
        item["metadata"] = metadata
        return item

    money_context = _lower(metadata.get("money_context"))
    rate_safety = _lower(metadata.get("rate_safety")) or RATE_MONEY_UNKNOWN
    reason = ""
    if non_ocr_rate_available:
        reason = "non_ocr_rate_candidate_available"
    elif rate_safety in {RATE_MONEY_UNSAFE, RATE_MONEY_UNKNOWN}:
        reason = metadata.get("rate_safety_reason") or (
            "ocr_unknown_money_context"
            if rate_safety == RATE_MONEY_UNKNOWN
            else f"ocr_{money_context}_unsafe"
        )
    elif money_context in _UNSAFE_OCR_RATE_CONTEXTS:
        reason = f"ocr_{money_context}_not_total_rate"
    elif rate_safety != RATE_MONEY_SAFE:
        reason = metadata.get("rate_safety_reason") or "ocr_risky_money_context"

    if reason:
        original_confidence = float(item.get("confidence") or 0.0)
        capped = min(original_confidence, 0.35)
        item["confidence"] = round(capped, 3)
        item["field"] = FIELD_ACCESSORIAL_TERM
        metadata["rate_abstained"] = True
        metadata["rate_demoted_from_total_carrier_rate"] = True
        metadata["rate_abstention_reason"] = reason
        metadata["ocr_rate_abstained"] = True
        metadata["ocr_rate_abstention_reason"] = reason
        metadata["selection_policy"] = RATE_SELECTION_ABSTAIN
        metadata["label_strength"] = "weak"
        _append_policy_adjustment(metadata, reason, capped - original_confidence)
    else:
        metadata["selection_policy"] = RATE_SELECTION_ALLOWED
        metadata["ocr_rate_safety"] = RATE_MONEY_SAFE
    item["metadata"] = metadata
    return item


def apply_ocr_candidate_policy_to_candidates(candidates, policy=OCR_CANDIDATE_POLICY_BASELINE):
    """Return candidate copies adjusted by the explicit OCR candidate policy."""
    if policy not in OCR_CANDIDATE_POLICIES:
        raise ValueError(f"unknown OCR candidate policy: {policy}")
    if policy == OCR_CANDIDATE_POLICY_BASELINE:
        return list(candidates or [])

    non_ocr_rate_available = _non_ocr_rate_candidate_available(candidates)
    adjusted = []
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        item = _apply_ocr_load_policy(candidate, policy)
        item = _apply_ocr_rate_policy(
            item,
            policy,
            non_ocr_rate_available=non_ocr_rate_available,
        )
        adjusted.append(item)
    return adjusted
