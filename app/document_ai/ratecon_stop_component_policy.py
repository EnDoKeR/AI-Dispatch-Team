"""Shadow-only stop component selection policy for RateCon diagnostics.

The policy here is intentionally conservative. It annotates and demotes
ambiguous stop candidates only when an explicit stop ranking profile is
requested; it does not change legacy extraction or production output.
"""

from __future__ import annotations


STOP_RANKING_PROFILE_BASELINE = "baseline"
STOP_RANKING_PROFILE_COMPONENT_STRICT_V1 = "stop_component_strict_v1"
STOP_RANKING_PROFILES = {
    STOP_RANKING_PROFILE_BASELINE,
    STOP_RANKING_PROFILE_COMPONENT_STRICT_V1,
}

FIELD_PICKUP_STOPS = "pickup_stops"
FIELD_DELIVERY_STOPS = "delivery_stops"
STOP_FIELDS = {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}

STOP_SELECTION_ALLOWED = "allowed"
STOP_SELECTION_PARTIAL_REVIEW = "partial_review"
STOP_SELECTION_ABSTAIN = "abstain"

SOURCE_OCR = "ocr"
ROLE_PICKUP = "pickup"
ROLE_DELIVERY = "delivery"
ROLE_UNKNOWN = "unknown"

_BAD_SECTION_TERMS = {
    "instructions",
    "terms",
    "footer",
    "footer_signature",
    "signature",
    "payment",
    "quickpay",
}

_REFERENCE_TERMS = {
    "reference",
    "ref",
    "bol",
    "po",
    "pickup ref",
    "delivery ref",
    "appointment",
}


def _text(value) -> str:
    return str(value or "").strip()


def _lower(value) -> str:
    return _text(value).lower()


def _metadata(candidate) -> dict:
    metadata = (candidate or {}).get("metadata")
    return dict(metadata) if isinstance(metadata, dict) else {}


def _field(candidate) -> str:
    return _lower((candidate or {}).get("field")).replace(" ", "_").replace("-", "_")


def _copy_candidate(candidate):
    item = dict(candidate or {})
    item["metadata"] = _metadata(item)
    return item


def _is_stop_candidate(candidate) -> bool:
    return _field(candidate) in STOP_FIELDS


def _expected_role(field_name: str) -> str:
    return ROLE_PICKUP if field_name == FIELD_PICKUP_STOPS else ROLE_DELIVERY


def _candidate_role(candidate, metadata) -> str:
    return _lower(metadata.get("stop_role") or metadata.get("role"))


def _has_location(metadata) -> bool:
    return bool(
        metadata.get("has_location")
        or metadata.get("has_facility")
        or metadata.get("has_address")
    )


def _has_date(metadata) -> bool:
    return bool(metadata.get("has_date"))


def _has_time(metadata) -> bool:
    return bool(metadata.get("has_time"))


def _context_text(candidate, metadata) -> str:
    return " ".join(
        _lower(value)
        for value in [
            candidate.get("label"),
            candidate.get("evidence_text"),
            metadata.get("section_context"),
            metadata.get("document_region"),
            metadata.get("pairing_method"),
            metadata.get("table_context_role"),
            metadata.get("table_row_role"),
            metadata.get("source_field"),
            metadata.get("raw_field"),
        ]
        if _text(value)
    )


def classify_stop_candidate_policy(candidate) -> dict:
    """Return safe stop policy metadata for a structured stop candidate."""

    if not isinstance(candidate, dict) or not _is_stop_candidate(candidate):
        return {}

    metadata = _metadata(candidate)
    field_name = _field(candidate)
    expected_role = _expected_role(field_name)
    role = _candidate_role(candidate, metadata)
    context = _context_text(candidate, metadata)
    has_location = _has_location(metadata)
    has_date = _has_date(metadata)
    has_time = _has_time(metadata)
    source = _lower(candidate.get("source"))
    parser_name = _lower(candidate.get("parser_name"))
    section = _lower(metadata.get("section_context") or metadata.get("document_region"))

    reason = ""
    policy = STOP_SELECTION_ALLOWED
    role_confidence = 0.95 if role == expected_role else 0.0
    if role in {"", ROLE_UNKNOWN}:
        reason = "unknown_role"
        policy = STOP_SELECTION_ABSTAIN
        role_confidence = 0.0
    elif role != expected_role:
        reason = "role_mismatch"
        policy = STOP_SELECTION_ABSTAIN
        role_confidence = 0.15
    elif metadata.get("ambiguous_stop_candidate"):
        reason = "ambiguous_stop_candidate"
        policy = STOP_SELECTION_ABSTAIN
        role_confidence = 0.45
    elif any(term in section or term in context for term in _BAD_SECTION_TERMS):
        reason = "instructions_terms_or_footer_stop"
        policy = STOP_SELECTION_ABSTAIN
    elif any(term in context for term in _REFERENCE_TERMS) and not (has_location or has_date):
        reason = "reference_text_without_stop_components"
        policy = STOP_SELECTION_ABSTAIN
    elif not has_location and not has_date:
        reason = "no_location_or_date"
        policy = STOP_SELECTION_ABSTAIN
    elif has_location and not has_date:
        reason = "location_only_review"
        policy = STOP_SELECTION_PARTIAL_REVIEW
    elif has_date and not has_location:
        reason = "date_only_review"
        policy = STOP_SELECTION_PARTIAL_REVIEW
    elif source == SOURCE_OCR and not (has_location and has_date):
        reason = "ocr_partial_stop_review"
        policy = STOP_SELECTION_PARTIAL_REVIEW
    elif "stop_evidence_assembler" in parser_name and metadata.get("partial_only"):
        reason = "assembled_partial_stop_review"
        policy = STOP_SELECTION_PARTIAL_REVIEW

    component_count = int(bool(has_location)) + int(bool(has_date)) + int(bool(has_time))
    completeness = round(component_count / 3.0, 3)
    return {
        "stop_selection_policy": policy,
        "stop_abstained": policy == STOP_SELECTION_ABSTAIN,
        "stop_abstention_reason": reason,
        "role_confidence": round(role_confidence, 3),
        "component_completeness": completeness,
        "review_required": policy in {STOP_SELECTION_ABSTAIN, STOP_SELECTION_PARTIAL_REVIEW},
        "stop_profile_adjustments": [
            {"reason": reason, "amount": -0.45 if policy == STOP_SELECTION_ABSTAIN else -0.12}
        ]
        if reason
        else [],
    }


def apply_stop_component_strict_profile_to_candidates(candidates):
    """Return candidate copies annotated by the strict stop component profile."""

    adjusted = []
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        item = _copy_candidate(candidate)
        if _is_stop_candidate(item):
            metadata = _metadata(item)
            policy_metadata = classify_stop_candidate_policy(item)
            if policy_metadata:
                metadata.update(policy_metadata)
                if policy_metadata.get("stop_abstained"):
                    item["confidence"] = round(min(float(item.get("confidence") or 0.0), 0.34), 3)
                elif policy_metadata.get("stop_selection_policy") == STOP_SELECTION_PARTIAL_REVIEW:
                    item["confidence"] = round(min(float(item.get("confidence") or 0.0), 0.69), 3)
                item["metadata"] = metadata
        adjusted.append(item)
    return adjusted
