"""Shadow-only stop component selection policy for RateCon diagnostics.

The policy here is intentionally conservative. It annotates and demotes
ambiguous stop candidates only when an explicit stop ranking profile is
requested; it does not change legacy extraction or production output.
"""

from __future__ import annotations


STOP_RANKING_PROFILE_BASELINE = "baseline"
STOP_RANKING_PROFILE_COMPONENT_STRICT_V1 = "stop_component_strict_v1"
STOP_RANKING_PROFILE_ALIGNMENT_STRICT_V1 = "stop_alignment_strict_v1"
STOP_RANKING_PROFILE_GEOMETRY_STRICT_V1 = "stop_geometry_strict_v1"
STOP_RANKING_PROFILES = {
    STOP_RANKING_PROFILE_BASELINE,
    STOP_RANKING_PROFILE_COMPONENT_STRICT_V1,
    STOP_RANKING_PROFILE_ALIGNMENT_STRICT_V1,
    STOP_RANKING_PROFILE_GEOMETRY_STRICT_V1,
}

FIELD_PICKUP_STOPS = "pickup_stops"
FIELD_DELIVERY_STOPS = "delivery_stops"
STOP_FIELDS = {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}

STOP_SELECTION_ALLOWED = "allowed"
STOP_SELECTION_PARTIAL_REVIEW = "partial_review"
STOP_SELECTION_ABSTAIN = "abstain"

STOP_ALIGNMENT_STRONG = "strong"
STOP_ALIGNMENT_MEDIUM = "medium"
STOP_ALIGNMENT_WEAK = "weak"
STOP_ALIGNMENT_UNSAFE = "unsafe"
STOP_ALIGNMENT_UNKNOWN = "unknown"
STOP_GEOMETRY_STRONG = STOP_ALIGNMENT_STRONG
STOP_GEOMETRY_MEDIUM = STOP_ALIGNMENT_MEDIUM
STOP_GEOMETRY_WEAK = STOP_ALIGNMENT_WEAK
STOP_GEOMETRY_UNSAFE = STOP_ALIGNMENT_UNSAFE
STOP_GEOMETRY_UNKNOWN = STOP_ALIGNMENT_UNKNOWN

SOURCE_OCR = "ocr"
PAIRING_METHOD_OCR_GEOMETRY_BLOCK = "ocr_geometry_block"
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


def _is_ocr_candidate(candidate, metadata) -> bool:
    return _lower((candidate or {}).get("source")) == SOURCE_OCR or bool(
        metadata.get("ocr_candidate")
    )


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


def _alignment_warnings(metadata):
    warnings = metadata.get("stop_alignment_warnings") or metadata.get("alignment_warnings") or []
    if isinstance(warnings, str):
        return [warnings] if warnings else []
    if isinstance(warnings, (list, tuple, set)):
        return [_text(item) for item in warnings if _text(item)]
    return []


def classify_stop_alignment_policy(candidate) -> dict:
    """Return stricter OCR alignment policy metadata for structured stops."""

    base = classify_stop_candidate_policy(candidate)
    if not isinstance(candidate, dict) or not _is_stop_candidate(candidate):
        return base

    metadata = _metadata(candidate)
    if not _is_ocr_candidate(candidate, metadata):
        return base

    has_location = _has_location(metadata)
    has_date = _has_date(metadata)
    has_time = _has_time(metadata)
    has_datetime = has_date or has_time
    role = _candidate_role(candidate, metadata)
    expected_role = _expected_role(_field(candidate))
    warnings = set(_alignment_warnings(metadata))
    status = _lower(metadata.get("stop_alignment_status") or metadata.get("alignment_status"))

    unsafe_warnings = {
        "component_from_instructions",
        "component_from_payment_section",
        "component_from_footer",
        "pickup_delivery_overlap",
        "date_from_neighbor_block",
        "location_from_neighbor_block",
        "reference_text_as_location",
    }
    if role in {"", ROLE_UNKNOWN} or role != expected_role:
        inferred_status = STOP_ALIGNMENT_UNSAFE
        reason = "alignment_role_mismatch"
    elif warnings.intersection(unsafe_warnings):
        inferred_status = STOP_ALIGNMENT_UNSAFE
        reason = sorted(warnings.intersection(unsafe_warnings))[0]
    elif status in {
        STOP_ALIGNMENT_STRONG,
        STOP_ALIGNMENT_MEDIUM,
        STOP_ALIGNMENT_WEAK,
        STOP_ALIGNMENT_UNSAFE,
        STOP_ALIGNMENT_UNKNOWN,
    }:
        inferred_status = status
        reason = ""
    elif has_location and has_datetime and not warnings:
        inferred_status = STOP_ALIGNMENT_STRONG
        reason = ""
    elif has_location or has_datetime:
        inferred_status = STOP_ALIGNMENT_MEDIUM
        reason = ""
    else:
        inferred_status = STOP_ALIGNMENT_WEAK
        reason = "role_only_ocr_stop"

    if not reason:
        if "multiple_dates_unpaired" in warnings or "multiple_locations_unpaired" in warnings:
            reason = "multiple_components_unpaired"
        elif "no_clear_role_boundary" in warnings or "no_clear_block_end" in warnings:
            reason = "unclear_role_boundary"
        elif "delivery_date_missing" in warnings and expected_role == ROLE_DELIVERY and has_location:
            reason = "delivery_date_missing"
        elif inferred_status == STOP_ALIGNMENT_WEAK:
            reason = "weak_ocr_stop_alignment"

    policy = STOP_SELECTION_ALLOWED
    if inferred_status == STOP_ALIGNMENT_STRONG:
        policy = STOP_SELECTION_ALLOWED
    elif inferred_status == STOP_ALIGNMENT_MEDIUM:
        policy = STOP_SELECTION_PARTIAL_REVIEW
        reason = reason or "medium_ocr_stop_alignment"
    else:
        policy = STOP_SELECTION_ABSTAIN
        reason = reason or f"{inferred_status}_ocr_stop_alignment"

    if base.get("stop_abstained"):
        policy = STOP_SELECTION_ABSTAIN
        reason = base.get("stop_abstention_reason") or reason
    elif base.get("stop_selection_policy") == STOP_SELECTION_PARTIAL_REVIEW and policy == STOP_SELECTION_ALLOWED:
        policy = STOP_SELECTION_PARTIAL_REVIEW
        reason = base.get("stop_abstention_reason") or "component_strict_partial_review"

    score_by_status = {
        STOP_ALIGNMENT_STRONG: 0.9,
        STOP_ALIGNMENT_MEDIUM: 0.62,
        STOP_ALIGNMENT_WEAK: 0.32,
        STOP_ALIGNMENT_UNSAFE: 0.12,
        STOP_ALIGNMENT_UNKNOWN: 0.0,
    }
    adjustments = list(base.get("stop_profile_adjustments") or [])
    if reason:
        adjustments.append(
            {
                "reason": reason,
                "amount": -0.45 if policy == STOP_SELECTION_ABSTAIN else -0.14,
            }
        )
    return {
        **base,
        "stop_alignment_score": round(float(metadata.get("stop_alignment_score") or score_by_status.get(inferred_status, 0.0)), 3),
        "stop_alignment_status": inferred_status,
        "stop_alignment_warnings": sorted(warnings),
        "stop_selection_policy": policy,
        "stop_abstained": policy == STOP_SELECTION_ABSTAIN,
        "stop_abstention_reason": reason,
        "review_required": policy in {STOP_SELECTION_ABSTAIN, STOP_SELECTION_PARTIAL_REVIEW},
        "stop_profile_adjustments": adjustments,
    }


def classify_stop_geometry_policy(candidate) -> dict:
    """Return strict geometry-aware OCR stop policy metadata."""

    base = classify_stop_alignment_policy(candidate)
    if not isinstance(candidate, dict) or not _is_stop_candidate(candidate):
        return base

    metadata = _metadata(candidate)
    if not _is_ocr_candidate(candidate, metadata):
        return base
    if _lower(metadata.get("pairing_method")) != PAIRING_METHOD_OCR_GEOMETRY_BLOCK:
        return base

    warnings = set(_alignment_warnings(metadata))
    geometry_warnings = metadata.get("stop_geometry_warnings") or []
    if isinstance(geometry_warnings, str):
        geometry_warnings = [geometry_warnings] if geometry_warnings else []
    warnings.update(_text(warning) for warning in geometry_warnings if _text(warning))

    has_location = _has_location(metadata)
    has_date = _has_date(metadata)
    has_time = _has_time(metadata)
    has_datetime = has_date or has_time
    status = _lower(
        metadata.get("stop_geometry_status")
        or metadata.get("stop_alignment_status")
        or STOP_GEOMETRY_UNKNOWN
    )
    expected_role = _expected_role(_field(candidate))
    role = _candidate_role(candidate, metadata)
    has_role_anchor = bool(metadata.get("has_clear_role_anchor"))
    has_boundary = bool(metadata.get("has_clear_horizontal_boundary"))
    unsafe_warnings = {
        "component_from_instructions",
        "component_from_payment_section",
        "component_from_footer",
        "component_from_neighbor_block",
        "date_from_neighbor_block",
        "location_from_neighbor_block",
        "pickup_delivery_overlap",
    }
    reason = ""
    if role in {"", ROLE_UNKNOWN} or role != expected_role or not has_role_anchor:
        status = STOP_GEOMETRY_UNSAFE
        reason = "geometry_role_anchor_missing"
    elif warnings.intersection(unsafe_warnings):
        status = STOP_GEOMETRY_UNSAFE
        reason = sorted(warnings.intersection(unsafe_warnings))[0]
    elif not has_boundary and has_location and has_datetime:
        status = STOP_GEOMETRY_MEDIUM
        reason = "geometry_boundary_unclear"

    complete = bool(has_location and has_datetime)
    policy = STOP_SELECTION_ALLOWED
    if status == STOP_GEOMETRY_STRONG and complete and has_boundary:
        policy = STOP_SELECTION_ALLOWED
    elif status in {STOP_GEOMETRY_STRONG, STOP_GEOMETRY_MEDIUM} and (
        has_location or has_datetime
    ):
        policy = STOP_SELECTION_PARTIAL_REVIEW
        reason = reason or "geometry_partial_review"
    else:
        policy = STOP_SELECTION_ABSTAIN
        reason = reason or f"{status}_geometry_stop"

    if base.get("stop_abstained"):
        policy = STOP_SELECTION_ABSTAIN
        reason = base.get("stop_abstention_reason") or reason
    elif base.get("stop_selection_policy") == STOP_SELECTION_PARTIAL_REVIEW and policy == STOP_SELECTION_ALLOWED:
        policy = STOP_SELECTION_PARTIAL_REVIEW
        reason = base.get("stop_abstention_reason") or "alignment_partial_review"

    score_by_status = {
        STOP_GEOMETRY_STRONG: 0.9,
        STOP_GEOMETRY_MEDIUM: 0.64,
        STOP_GEOMETRY_WEAK: 0.28,
        STOP_GEOMETRY_UNSAFE: 0.1,
        STOP_GEOMETRY_UNKNOWN: 0.0,
    }
    adjustments = list(base.get("stop_profile_adjustments") or [])
    if reason:
        adjustments.append(
            {
                "reason": reason,
                "amount": -0.48 if policy == STOP_SELECTION_ABSTAIN else -0.16,
            }
        )
    return {
        **base,
        "stop_geometry_score": round(
            float(metadata.get("stop_geometry_score") or score_by_status.get(status, 0.0)),
            3,
        ),
        "stop_geometry_status": status,
        "stop_geometry_warnings": sorted(warnings),
        "stop_selection_policy": policy,
        "stop_abstained": policy == STOP_SELECTION_ABSTAIN,
        "stop_abstention_reason": reason,
        "review_required": policy in {STOP_SELECTION_ABSTAIN, STOP_SELECTION_PARTIAL_REVIEW},
        "stop_profile_adjustments": adjustments,
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


def apply_stop_geometry_strict_profile_to_candidates(candidates):
    """Return candidate copies annotated by strict OCR geometry policy."""

    adjusted = []
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        item = _copy_candidate(candidate)
        if _is_stop_candidate(item):
            metadata = _metadata(item)
            policy_metadata = classify_stop_geometry_policy(item)
            if policy_metadata:
                metadata.update(policy_metadata)
                if policy_metadata.get("stop_abstained"):
                    item["confidence"] = round(min(float(item.get("confidence") or 0.0), 0.30), 3)
                elif policy_metadata.get("stop_selection_policy") == STOP_SELECTION_PARTIAL_REVIEW:
                    item["confidence"] = round(min(float(item.get("confidence") or 0.0), 0.62), 3)
                item["metadata"] = metadata
        adjusted.append(item)
    return adjusted


def apply_stop_alignment_strict_profile_to_candidates(candidates):
    """Return candidate copies annotated by the OCR stop alignment profile."""

    adjusted = []
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        item = _copy_candidate(candidate)
        if _is_stop_candidate(item):
            metadata = _metadata(item)
            policy_metadata = classify_stop_alignment_policy(item)
            if policy_metadata:
                metadata.update(policy_metadata)
                if policy_metadata.get("stop_abstained"):
                    item["confidence"] = round(min(float(item.get("confidence") or 0.0), 0.32), 3)
                elif policy_metadata.get("stop_selection_policy") == STOP_SELECTION_PARTIAL_REVIEW:
                    item["confidence"] = round(min(float(item.get("confidence") or 0.0), 0.64), 3)
                item["metadata"] = metadata
        adjusted.append(item)
    return adjusted
