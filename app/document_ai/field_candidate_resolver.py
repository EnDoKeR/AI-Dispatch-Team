"""Generic field candidate resolver with confidence and review gating."""

from collections import defaultdict

from app.document_ai.structured_stop_values import (
    CONFLICT_DATE,
    CONFLICT_DUPLICATE_PARTIAL_OVERLAP,
    CONFLICT_DUPLICATE_SAME_STOP,
    CONFLICT_LOCATION,
    CONFLICT_ROLE,
    CONFLICT_STOP_COUNT,
    CONFLICT_TIME,
    FIELD_DELIVERY_STOPS as STRUCTURED_FIELD_DELIVERY_STOPS,
    FIELD_PICKUP_STOPS as STRUCTURED_FIELD_PICKUP_STOPS,
    STOP_STATUS_AMBIGUOUS,
    STOP_STATUS_COMPLETE,
    STOP_STATUS_EMPTY,
    STOP_STATUS_PARTIAL_ONLY,
    STOP_STATUS_UNSUPPORTED,
    STOP_STATUS_USEFUL_PARTIAL,
    normalize_stop_candidate_value,
    safe_stop_normalization_summary,
    stop_conflict_types,
    stop_equivalence_key,
)
from app.document_ai.ratecon_rate_money_safety import (
    RATE_SELECTION_ABSTAIN,
    RATE_SELECTION_WEAK_ONLY,
    apply_rate_money_abstention_profile_to_candidates,
)


REVIEW_NEEDS_REVIEW = "NEEDS_REVIEW"
REVIEW_LOW_CONFIDENCE_CRITICAL_FIELD = "LOW_CONFIDENCE_CRITICAL_FIELD"
REVIEW_MISSING_CRITICAL_FIELD = "MISSING_CRITICAL_FIELD"
REVIEW_CONFLICTING_CANDIDATES = "CONFLICTING_CANDIDATES"
REVIEW_TRIAGE_OCR_REQUIRED = "TRIAGE_OCR_REQUIRED"
REVIEW_TRIAGE_NATIVE_TEXT_SUSPICIOUS = "TRIAGE_NATIVE_TEXT_SUSPICIOUS"
REVIEW_STRUCTURED_STOP_PARTIAL = "STRUCTURED_STOP_PARTIAL_REVIEW_REQUIRED"
REVIEW_STRUCTURED_STOP_UNSUPPORTED = "STRUCTURED_STOP_UNSUPPORTED"

FIELD_LOAD_NUMBER = "load_number"
FIELD_TOTAL_CARRIER_RATE = "total_carrier_rate"
FIELD_PICKUP_STOPS = "pickup_stops"
FIELD_DELIVERY_STOPS = "delivery_stops"
FIELD_BROKER_NAME = "broker_name"
FIELD_CARRIER_NAME = "carrier_name"

QUALITY_HIGH = "high"
QUALITY_MEDIUM = "medium"
QUALITY_WEAK = "weak"
QUALITY_FALLBACK = "fallback"

ELIGIBLE_CANONICAL_FIELD_MATCH = "canonical_field_match"
ELIGIBLE_WEAK_ALIAS = "weak_alias"
ELIGIBLE_FALLBACK_ALLOWED = "fallback_allowed"
INELIGIBLE_UNSUPPORTED_VALUE_TYPE = "unsupported_value_type"
INELIGIBLE_MISSING_VALUE = "missing_value"
INELIGIBLE_LOW_CONFIDENCE = "low_confidence"
INELIGIBLE_DIAGNOSTIC_ONLY = "diagnostic_only"
INELIGIBLE_WRONG_FIELD = "wrong_field"
INELIGIBLE_AMBIGUOUS_ROLE = "ambiguous_role"
INELIGIBLE_UNKNOWN = "unknown"

DECISION_SELECTED = "selected"
DECISION_NO_CANDIDATES = "no_candidates"
DECISION_NO_ELIGIBLE_CANDIDATES = "no_eligible_candidates"
DECISION_CONFLICT = "conflict"
DECISION_LOW_CONFIDENCE = "low_confidence"
DECISION_UNSUPPORTED_FIELD = "unsupported_field"
DECISION_UNSUPPORTED_VALUE_TYPE = "unsupported_value_type"
DECISION_REVIEW_REQUIRED = "review_required"
DECISION_SELECTED_COMPLETE = "selected_complete"
DECISION_SELECTED_USEFUL_PARTIAL = "selected_useful_partial"
DECISION_UNSUPPORTED_STRUCTURED_VALUE = "unsupported_value_type"

REJECT_LOWER_CONFIDENCE = "lower_confidence"
REJECT_WEAK_MAPPING = "weak_mapping"
REJECT_FALLBACK_PENALTY = "fallback_penalty"
REJECT_VALUE_SHAPE_REJECTED = "value_shape_rejected"
REJECT_CONFLICT = "conflict"
REJECT_UNSUPPORTED_VALUE_TYPE = "unsupported_value_type"
REJECT_MISSING_EVIDENCE = "missing_evidence"
REJECT_DUPLICATE = "duplicate"
REJECT_FIELD_NOT_RESOLVED = "field_not_resolved"
REJECT_PARTIAL_ONLY = "partial_only"
REJECT_AMBIGUOUS_ROLE = "ambiguous_role"
REJECT_TRUE_CONFLICT = "true_conflict"
REJECT_UNSUPPORTED_STOP_VALUE = "unsupported_stop_value"
REJECT_EMPTY_STOP_VALUE = "empty_stop_value"
REJECT_LOW_QUALITY = "low_quality"
REJECT_UNKNOWN = "unknown"

FIELD_THRESHOLDS = {
    FIELD_LOAD_NUMBER: 0.75,
    FIELD_TOTAL_CARRIER_RATE: 0.80,
    FIELD_PICKUP_STOPS: 0.70,
    FIELD_DELIVERY_STOPS: 0.70,
    FIELD_BROKER_NAME: 0.70,
    FIELD_CARRIER_NAME: 0.70,
}

RANKING_PROFILE_BASELINE = "baseline"
RANKING_PROFILE_GOLD_DIAGNOSTIC_V1 = "gold_diagnostic_v1"
RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1 = "money_abstain_v1"
RANKING_PROFILES = {
    RANKING_PROFILE_BASELINE,
    RANKING_PROFILE_GOLD_DIAGNOSTIC_V1,
}
LOAD_RANKING_PROFILE_HEADER_RECALL_V1 = "header_recall_v1"
LOAD_RANKING_PROFILE_HEADER_RECALL_TABLE_SAFETY_V1 = "header_recall_table_safety_v1"
LOAD_RANKING_PROFILE_HEADER_RECALL_TABLE_ABSTAIN_V1 = "header_recall_table_abstain_v1"
LOAD_RANKING_PROFILES = {
    RANKING_PROFILE_BASELINE,
    LOAD_RANKING_PROFILE_HEADER_RECALL_V1,
    LOAD_RANKING_PROFILE_HEADER_RECALL_TABLE_SAFETY_V1,
    LOAD_RANKING_PROFILE_HEADER_RECALL_TABLE_ABSTAIN_V1,
}
RATE_RANKING_PROFILES = {
    RANKING_PROFILE_BASELINE,
    RANKING_PROFILE_GOLD_DIAGNOSTIC_V1,
    RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
}

SOURCE_RANK = {
    "native_layout": 0.12,
    "native_text": 0.08,
    "broker_parser": 0.06,
    "legacy_parser": 0.04,
    "ocr": 0.02,
    "regex": 0.0,
    "unknown": 0.0,
}

RATE_STRONG_LABELS = (
    "total carrier pay",
    "total carrier rate",
    "carrier pay",
    "total rate",
    "agreed amount",
)
RATE_COMPONENT_LABELS = (
    "linehaul",
    "line haul",
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

LOAD_STRONG_LABELS = (
    "load #",
    "load number",
    "load no",
    "order #",
    "order number",
    "tender #",
    "tender id",
    "shipment #",
    "shipment number",
)
LOAD_NEGATIVE_LABELS = (
    "po #",
    "po number",
    "bol #",
    "bol number",
    "pickup #",
    "delivery #",
    "appointment #",
    "customer ref",
    "carrier ref",
)

STOP_FIELDS = {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}


def _text(value):
    return str(value or "").strip()


def _raw_value(candidate):
    return (candidate or {}).get("value")


def _value_shape(value):
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        return {
            "length": len(items),
            "has_digits": False,
            "has_letters": False,
            "looks_like_money": False,
            "looks_like_date": False,
            "looks_like_phone": False,
            "looks_like_address": False,
            "structured": True,
            "list": True,
            "dict": False,
            "token_count": len(items),
        }
    if isinstance(value, dict):
        return {
            "length": len(value),
            "has_digits": False,
            "has_letters": False,
            "looks_like_money": False,
            "looks_like_date": False,
            "looks_like_phone": False,
            "looks_like_address": False,
            "structured": True,
            "list": False,
            "dict": True,
            "token_count": len(value),
        }
    text = _text(value)
    digits = sum(1 for char in text if char.isdigit())
    letters = sum(1 for char in text if char.isalpha())
    lowered = text.lower()
    return {
        "length": len(text),
        "has_digits": digits > 0,
        "has_letters": letters > 0,
        "looks_like_money": "$" in text or bool(digits and "." in text and any(word in lowered for word in ["usd", "rate", "pay"])),
        "looks_like_date": bool(digits and ("/" in text or "-" in text) and len(text) <= 12),
        "looks_like_phone": digits >= 10 and any(char in text for char in ["(", ")", "-"]),
        "looks_like_address": any(word in lowered for word in [" st", " ave", " rd", " road", " drive", " blvd", " lane"]),
        "structured": False,
        "list": False,
        "dict": False,
        "token_count": len(text.split()) if text else 0,
    }


def _lower_join(candidate):
    return " ".join(
        _text(value).lower()
        for value in [
            candidate.get("label"),
            candidate.get("evidence_text"),
            (candidate.get("metadata") or {}).get("value_type"),
            (candidate.get("metadata") or {}).get("identifier_type"),
        ]
        if _text(value)
    )


def _canonical_field(field_name):
    token = _text(field_name).lower().replace(" ", "_").replace("-", "_")
    if token == "rate":
        return FIELD_TOTAL_CARRIER_RATE
    if token == "equipment":
        return "equipment_type"
    if token == "reference":
        return "reference_numbers"
    if token in {"pickup_location", "pickup_date", "pickup_time"}:
        return FIELD_PICKUP_STOPS
    if token in {"delivery_location", "delivery_date", "delivery_time"}:
        return FIELD_DELIVERY_STOPS
    return token


def _metadata(candidate):
    return dict((candidate or {}).get("metadata") or {})


def _quality_band(candidate):
    metadata = _metadata(candidate)
    if metadata.get("diagnostic_fallback") or metadata.get("not_independent_candidate"):
        return QUALITY_FALLBACK
    confidence = float((candidate or {}).get("confidence") or 0.0)
    if confidence >= 0.80:
        return QUALITY_HIGH
    if confidence >= 0.60:
        return QUALITY_MEDIUM
    return QUALITY_WEAK


def _candidate_id(field_name, index):
    return f"{field_name}:candidate:{index + 1}"


def _metadata_summary(candidate):
    metadata = _metadata(candidate)
    safe_keys = [
        "canonical_mapping_strength",
        "semantic_role",
        "id_type_hint",
        "stop_role",
        "party_role_hint",
        "money_context",
        "pairing_method",
        "layout_provider",
        "structured_stop_candidate",
        "partial_stop_candidate",
        "ambiguous_stop_candidate",
        "diagnostic_fallback",
        "not_independent_candidate",
        "independent_candidate",
        "table_cell_candidate",
        "table_context_role",
        "table_row_role",
        "table_neighbor_safety",
        "table_neighbor_penalty_reason",
        "table_neighbor_demoted_from_load_number",
        "table_neighbor_abstained",
        "table_neighbor_abstention_reason",
        "selection_policy",
        "review_required",
        "table_semantic_kind",
        "table_row_identifier_like_cell_count",
        "neighbor_cell_count",
        "id_like_cell_count_in_row",
        "load_label_cell_count_in_row",
        "reference_label_cell_count_in_row",
        "stop_label_cell_count_in_row",
        "money_like_cell_count_in_row",
        "has_location",
        "has_date",
        "has_time",
        "has_facility",
        "has_address",
        "stop_structure_status",
        "stop_completeness_score",
        "stop_selected_status",
        "stop_conflict_type",
        "generator_name",
        "document_region",
        "is_document_title_or_header_id",
        "is_stop_level_reference",
        "is_pickup_delivery_reference",
        "is_bol_or_po_or_customer_ref",
        "is_driver_truck_trailer_noise",
        "id_role_confidence",
        "context_penalty_reason",
        "context_feature_load_identity_candidate",
        "is_total_pay_candidate",
        "is_total_rate_candidate",
        "is_line_item_only",
        "is_per_unit_rate",
        "is_deduction_or_penalty",
        "is_payment_terms_amount",
        "is_accessorial_only",
        "rate_safety",
        "rate_safety_reason",
        "rate_abstained",
        "rate_abstention_reason",
        "rate_demoted_from_total_carrier_rate",
        "rate_candidate_profile_adjustments",
        "ranking_profile",
        "ranking_adjustment_total",
        "ranking_adjustments",
        "load_candidate_profile",
        "load_candidate_profile_adjustments",
    ]
    return {key: metadata.get(key) for key in safe_keys if key in metadata}


def _safe_candidate_trace(candidate, field_name, index, score=None):
    metadata = _metadata(candidate)
    payload = {
        "candidate_id": _text(metadata.get("candidate_id")) or _candidate_id(field_name, index),
        "source": _text((candidate or {}).get("source")),
        "parser_name": _text((candidate or {}).get("parser_name")),
        "confidence": round(float((candidate or {}).get("confidence") or 0.0), 3),
        "score": round(float(score), 3) if score is not None else "",
        "mapping_strength": _text(metadata.get("canonical_mapping_strength")),
        "quality_band": _quality_band(candidate),
        "value_shape": _value_shape(_raw_value(candidate)),
        "evidence_available": bool(_text((candidate or {}).get("evidence_text"))),
        "has_bbox": bool((candidate or {}).get("bbox")),
        "metadata_summary": _metadata_summary(candidate),
    }
    if _is_stop_field(field_name):
        normalized = _stop_normalization(candidate, field_name)
        payload["structured_stop_summary"] = safe_stop_normalization_summary(normalized)
        payload["metadata_summary"].update(
            {
                "stop_structure_status": normalized.get("structure_status"),
                "stop_completeness_score": round(
                    float(normalized.get("completeness_score") or 0.0),
                    3,
                ),
                "has_location": bool(normalized.get("has_location")),
                "has_date": bool(normalized.get("has_date")),
                "has_time": bool(normalized.get("has_time")),
                "has_facility": bool(normalized.get("has_facility")),
                "has_address": bool(normalized.get("has_address")),
            }
        )
    return payload


def _value(candidate):
    return _text(candidate.get("normalized_value") or candidate.get("value"))


def _is_stop_field(field_name):
    return field_name in STOP_FIELDS


def _stop_normalization(candidate, field_name):
    return normalize_stop_candidate_value(
        _raw_value(candidate),
        field_name,
        candidate_metadata=_metadata(candidate),
    )


def _stop_value_label(normalized):
    role = _text(normalized.get("role")) or "stop"
    status = _text(normalized.get("structure_status")) or STOP_STATUS_EMPTY
    return f"{role}_stop_{status}"


def _stop_is_selectable(normalized):
    return normalized.get("structure_status") in {
        STOP_STATUS_COMPLETE,
        STOP_STATUS_USEFUL_PARTIAL,
    }


def _stop_status_from_resolution(resolution):
    return _text((resolution or {}).get("structure_status"))


def _with_stop_metadata(candidate, normalized, selected_status=""):
    item = dict(candidate or {})
    metadata = dict(item.get("metadata") or {})
    summary = safe_stop_normalization_summary(normalized)
    metadata["stop_structure_status"] = summary.get("structure_status")
    metadata["stop_completeness_score"] = summary.get("completeness_score")
    if selected_status:
        metadata["stop_selected_status"] = selected_status
    metadata["has_location"] = summary.get("has_location")
    metadata["has_date"] = summary.get("has_date")
    metadata["has_time"] = summary.get("has_time")
    metadata["has_facility"] = summary.get("has_facility")
    metadata["has_address"] = summary.get("has_address")
    item["metadata"] = metadata
    return item


def _has_any(text, markers):
    return any(marker in text for marker in markers)


def _triage_penalty(triage):
    flags = set((triage or {}).get("quality_flags", []) or [])
    penalty = 0.0
    if (triage or {}).get("ocr_required") or "OCR_REQUIRED" in flags:
        penalty += 0.15
    if "NATIVE_TEXT_SUSPICIOUS" in flags:
        penalty += 0.10
    return penalty


def _label_adjustment(field_name, candidate):
    context = _lower_join(candidate)
    if field_name == FIELD_TOTAL_CARRIER_RATE:
        if _has_any(context, RATE_NEGATIVE_LABELS):
            return -0.55
        if _has_any(context, RATE_STRONG_LABELS):
            return 0.18
        if _has_any(context, RATE_COMPONENT_LABELS):
            return 0.03
        return -0.05
    if field_name == FIELD_LOAD_NUMBER:
        if _has_any(context, LOAD_NEGATIVE_LABELS):
            return -0.55
        if _has_any(context, LOAD_STRONG_LABELS):
            return 0.18
    return 0.0


def _profile_adjustments(field_name, candidate, ranking_profile):
    if ranking_profile not in {
        RANKING_PROFILE_GOLD_DIAGNOSTIC_V1,
        RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
    }:
        return []
    metadata = _metadata(candidate)
    adjustments = []
    if field_name == FIELD_LOAD_NUMBER:
        if metadata.get("is_document_title_or_header_id") and float(metadata.get("id_role_confidence") or 0.0) >= 0.65:
            adjustments.append(("document_title_or_header_id", 0.10))
        elif _text(metadata.get("document_region")) == "load_info":
            adjustments.append(("load_info_section_id", 0.05))
        if _text(metadata.get("pairing_method")) in {"same_row_right", "table_key_value_row", "table_same_cell"} and not metadata.get("is_stop_level_reference"):
            adjustments.append(("strong_layout_pairing_context", 0.03))
        if metadata.get("is_pickup_delivery_reference"):
            adjustments.append(("pickup_delivery_reference_penalty", -0.45))
        if metadata.get("is_stop_level_reference"):
            adjustments.append(("stop_level_reference_penalty", -0.38))
        if metadata.get("is_driver_truck_trailer_noise"):
            adjustments.append(("driver_truck_trailer_noise_penalty", -0.60))
        if metadata.get("is_bol_or_po_or_customer_ref") and not metadata.get("context_feature_load_identity_candidate"):
            adjustments.append(("bol_po_customer_reference_penalty", -0.30))
        if _text(metadata.get("document_region")) in {"instructions", "footer_signature"}:
            adjustments.append(("instructions_or_footer_id_penalty", -0.35))
        if _text(metadata.get("document_region")) == "reference_section" and not metadata.get("context_feature_load_identity_candidate"):
            adjustments.append(("reference_section_id_penalty", -0.25))
    elif field_name == FIELD_TOTAL_CARRIER_RATE:
        money_context = _text(metadata.get("money_context"))
        if money_context == "total_carrier_pay":
            adjustments.append(("total_carrier_pay_context", 0.08))
        elif money_context in {
            "total_rate",
            "total_cost",
            "estimated_rate_to_truck",
            "agreed_rate_total",
        }:
            adjustments.append(("total_rate_context", 0.06))
        elif money_context == "carrier_freight_pay":
            adjustments.append(("carrier_freight_pay_context", 0.04))
        elif money_context == "linehaul_total":
            adjustments.append(("linehaul_total_context", 0.02))
        if metadata.get("is_line_item_only"):
            adjustments.append(("line_item_only_penalty", -0.25))
        if metadata.get("is_deduction_or_penalty"):
            adjustments.append(("deduction_fee_penalty_context", -0.45))
        if metadata.get("is_payment_terms_amount"):
            adjustments.append(("payment_terms_amount_penalty", -0.40))
        if metadata.get("is_per_unit_rate"):
            adjustments.append(("per_unit_rate_penalty", -0.45))
        if metadata.get("is_accessorial_only"):
            adjustments.append(("accessorial_only_penalty", -0.42))
        if money_context in {
            "accessorial",
            "quickpay",
            "fuel_advance",
            "comcheck_fee",
            "tracking_hold",
            "penalty",
            "fee",
            "deduction",
        }:
            adjustments.append((f"{money_context}_money_context_penalty", -0.42))
        if metadata.get("rate_abstained"):
            adjustments.append(
                (
                    metadata.get("rate_abstention_reason")
                    or "rate_money_abstained",
                    -0.60,
                )
            )
        elif metadata.get("selection_policy") == RATE_SELECTION_WEAK_ONLY:
            adjustments.append(
                (
                    metadata.get("rate_abstention_reason")
                    or "rate_money_weak_only",
                    -0.18,
                )
            )
        if _text(metadata.get("document_region")) in {"instructions", "footer_signature"}:
            adjustments.append(("instructions_or_footer_money_penalty", -0.25))
    return adjustments


def _effective_ranking_profile(
    field_name,
    ranking_profile=RANKING_PROFILE_BASELINE,
    load_ranking_profile=None,
    rate_ranking_profile=None,
):
    if field_name == FIELD_LOAD_NUMBER and load_ranking_profile is not None:
        return load_ranking_profile
    if field_name == FIELD_TOTAL_CARRIER_RATE and rate_ranking_profile is not None:
        return rate_ranking_profile
    return ranking_profile


def _effective_field_ranking_profiles(
    ranking_profile=RANKING_PROFILE_BASELINE,
    load_ranking_profile=None,
    rate_ranking_profile=None,
):
    return {
        FIELD_LOAD_NUMBER: _effective_ranking_profile(
            FIELD_LOAD_NUMBER,
            ranking_profile=ranking_profile,
            load_ranking_profile=load_ranking_profile,
            rate_ranking_profile=rate_ranking_profile,
        ),
        FIELD_TOTAL_CARRIER_RATE: _effective_ranking_profile(
            FIELD_TOTAL_CARRIER_RATE,
            ranking_profile=ranking_profile,
            load_ranking_profile=load_ranking_profile,
            rate_ranking_profile=rate_ranking_profile,
        ),
    }


def _apply_field_scoped_candidate_profiles(
    candidates,
    ranking_profile=RANKING_PROFILE_BASELINE,
    load_ranking_profile=None,
    rate_ranking_profile=None,
):
    effective_rate_profile = _effective_ranking_profile(
        FIELD_TOTAL_CARRIER_RATE,
        ranking_profile=ranking_profile,
        load_ranking_profile=load_ranking_profile,
        rate_ranking_profile=rate_ranking_profile,
    )
    if effective_rate_profile == RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1:
        return apply_rate_money_abstention_profile_to_candidates(candidates)
    return candidates


def _validate_ranking_profiles(
    ranking_profile=RANKING_PROFILE_BASELINE,
    load_ranking_profile=None,
    rate_ranking_profile=None,
):
    if ranking_profile not in RANKING_PROFILES:
        raise ValueError(f"unknown ranking profile: {ranking_profile}")
    if load_ranking_profile is not None and load_ranking_profile not in LOAD_RANKING_PROFILES:
        raise ValueError(f"unknown load ranking profile: {load_ranking_profile}")
    if rate_ranking_profile is not None and rate_ranking_profile not in RATE_RANKING_PROFILES:
        raise ValueError(f"unknown rate ranking profile: {rate_ranking_profile}")


def _apply_score_trace(candidate, ranking_profile, adjustments):
    if ranking_profile == RANKING_PROFILE_BASELINE:
        return
    metadata = dict((candidate or {}).get("metadata") or {})
    total = round(sum(amount for _reason, amount in adjustments), 3)
    metadata["ranking_profile"] = ranking_profile
    metadata["ranking_adjustment_total"] = total
    metadata["ranking_adjustments"] = [
        {"reason": reason, "amount": round(float(amount), 3)}
        for reason, amount in adjustments
    ]
    candidate["metadata"] = metadata


def _score(field_name, candidate, triage, ranking_profile=RANKING_PROFILE_BASELINE):
    base = float(candidate.get("confidence") or 0.0)
    source_boost = SOURCE_RANK.get(_text(candidate.get("source")), 0.0)
    profile_adjustments = _profile_adjustments(field_name, candidate, ranking_profile)
    _apply_score_trace(candidate, ranking_profile, profile_adjustments)
    score = (
        base
        + source_boost
        + _label_adjustment(field_name, candidate)
        + sum(amount for _reason, amount in profile_adjustments)
        - _triage_penalty(triage)
    )
    return max(0.0, min(round(score, 3), 1.0))


def _public_candidate(candidate, score):
    return {
        "value": _value(candidate),
        "normalized_value": _value(candidate),
        "label": _text(candidate.get("label")),
        "evidence_text": _text(candidate.get("evidence_text")),
        "page": candidate.get("page", ""),
        "source": _text(candidate.get("source")),
        "parser_name": _text(candidate.get("parser_name")),
        "confidence": round(float(candidate.get("confidence") or 0.0), 3),
        "score": score,
        "metadata": dict(candidate.get("metadata") or {}),
    }


def _field_candidates(candidates, field_name, ranking_profile=RANKING_PROFILE_BASELINE):
    direct = []
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        candidate_field = _canonical_field(candidate.get("field"))
        metadata = _metadata(candidate)
        if candidate_field == field_name:
            direct.append(candidate)
        elif field_name == FIELD_TOTAL_CARRIER_RATE and _canonical_field(candidate.get("field")) == "total_carrier_rate":
            direct.append(candidate)
        elif (
            ranking_profile == RANKING_PROFILE_GOLD_DIAGNOSTIC_V1
            and field_name == FIELD_LOAD_NUMBER
            and candidate_field == "reference_numbers"
            and metadata.get("context_feature_load_identity_candidate")
        ):
            direct.append(candidate)
    return direct


def classify_candidate_eligibility(candidate, field_name, index=0):
    metadata = _metadata(candidate)
    candidate_field = _canonical_field((candidate or {}).get("field"))
    diagnostic_fallback = bool(metadata.get("diagnostic_fallback")) or bool(
        metadata.get("not_independent_candidate")
    )
    value = _value(candidate)
    raw_value = _raw_value(candidate)
    mapping_strength = _text(metadata.get("canonical_mapping_strength"))
    reason = ELIGIBLE_CANONICAL_FIELD_MATCH
    eligible = True
    if (
        field_name == FIELD_LOAD_NUMBER
        and candidate_field == "reference_numbers"
        and metadata.get("context_feature_load_identity_candidate")
    ):
        reason = ELIGIBLE_WEAK_ALIAS
    elif candidate_field != field_name:
        eligible = False
        reason = INELIGIBLE_WRONG_FIELD
    elif _is_stop_field(field_name):
        normalized = _stop_normalization(candidate, field_name)
        status = normalized.get("structure_status")
        if status == STOP_STATUS_EMPTY:
            eligible = False
            reason = INELIGIBLE_MISSING_VALUE
        elif status == STOP_STATUS_UNSUPPORTED:
            eligible = False
            reason = INELIGIBLE_UNSUPPORTED_VALUE_TYPE
        elif status == STOP_STATUS_AMBIGUOUS:
            eligible = False
            reason = INELIGIBLE_AMBIGUOUS_ROLE
        elif status == STOP_STATUS_PARTIAL_ONLY:
            eligible = False
            reason = REJECT_PARTIAL_ONLY
        elif diagnostic_fallback:
            reason = ELIGIBLE_FALLBACK_ALLOWED
        elif mapping_strength == "weak":
            reason = ELIGIBLE_WEAK_ALIAS
    elif not value:
        eligible = False
        reason = INELIGIBLE_MISSING_VALUE
    elif isinstance(raw_value, (list, dict)) and not _text((candidate or {}).get("normalized_value")):
        eligible = False
        reason = INELIGIBLE_UNSUPPORTED_VALUE_TYPE
    elif diagnostic_fallback:
        reason = ELIGIBLE_FALLBACK_ALLOWED
    elif mapping_strength == "weak":
        reason = ELIGIBLE_WEAK_ALIAS
    elif metadata.get("ambiguous_stop_candidate"):
        reason = INELIGIBLE_AMBIGUOUS_ROLE
        eligible = False
    return {
        "candidate_id": _text(metadata.get("candidate_id")) or _candidate_id(field_name, index),
        "field": field_name,
        "eligible": bool(eligible),
        "eligibility_reason": reason or INELIGIBLE_UNKNOWN,
        "quality_band": _quality_band(candidate),
        "independent": not diagnostic_fallback,
        "layout_based": _text((candidate or {}).get("source")) == "native_layout"
        or "layout" in _text((candidate or {}).get("parser_name")),
        "table_based": bool(metadata.get("table_cell_candidate"))
        or _text(metadata.get("pairing_method")).startswith("table_")
        or "table" in _text((candidate or {}).get("parser_name")),
        "legacy_fallback": diagnostic_fallback,
    }


def _selected_candidate_identity(resolution):
    selected = (resolution or {}).get("selected_candidate") or {}
    return (
        _text(selected.get("parser_name")),
        _text(selected.get("source")),
        _text(selected.get("normalized_value") or selected.get("value")),
        _text(selected.get("label")),
    )


def _candidate_identity(candidate):
    return (
        _text((candidate or {}).get("parser_name")),
        _text((candidate or {}).get("source")),
        _value(candidate),
        _text((candidate or {}).get("label")),
    )


def _not_selected_reason(field_name, candidate, selected_score=None, candidate_score=None, resolution=None):
    metadata = _metadata(candidate)
    reasons = set((resolution or {}).get("review_reasons", []) or [])
    if REVIEW_CONFLICTING_CANDIDATES in reasons:
        return REJECT_CONFLICT
    if _is_stop_field(field_name):
        normalized = _stop_normalization(candidate, field_name)
        status = normalized.get("structure_status")
        if status == STOP_STATUS_UNSUPPORTED:
            return REJECT_UNSUPPORTED_STOP_VALUE
        if status == STOP_STATUS_EMPTY:
            return REJECT_EMPTY_STOP_VALUE
        if status == STOP_STATUS_AMBIGUOUS:
            return REJECT_AMBIGUOUS_ROLE
        if status == STOP_STATUS_PARTIAL_ONLY:
            return REJECT_PARTIAL_ONLY
    if metadata.get("ambiguous_stop_candidate"):
        return REJECT_AMBIGUOUS_ROLE
    if metadata.get("partial_stop_candidate"):
        return REJECT_PARTIAL_ONLY
    if metadata.get("diagnostic_fallback") or metadata.get("not_independent_candidate"):
        return REJECT_FALLBACK_PENALTY
    if _text(metadata.get("canonical_mapping_strength")) == "weak":
        return REJECT_WEAK_MAPPING
    if not _text((candidate or {}).get("evidence_text")):
        return REJECT_MISSING_EVIDENCE
    if selected_score is not None and candidate_score is not None and candidate_score < selected_score:
        return REJECT_LOWER_CONFIDENCE
    if not _text((resolution or {}).get("value")):
        return REJECT_FIELD_NOT_RESOLVED
    return REJECT_UNKNOWN


def build_resolver_decision_traces(
    candidates,
    resolved_fields=None,
    triage=None,
    field_names=None,
    ranking_profile=RANKING_PROFILE_BASELINE,
    load_ranking_profile=None,
    rate_ranking_profile=None,
):
    candidates = _apply_field_scoped_candidate_profiles(
        candidates,
        ranking_profile=ranking_profile,
        load_ranking_profile=load_ranking_profile,
        rate_ranking_profile=rate_ranking_profile,
    )
    resolved_fields = resolved_fields if isinstance(resolved_fields, dict) else {}
    target_fields = tuple(field_names or FIELD_THRESHOLDS.keys())
    traces = {}
    for field_name in target_fields:
        field_ranking_profile = _effective_ranking_profile(
            field_name,
            ranking_profile=ranking_profile,
            load_ranking_profile=load_ranking_profile,
            rate_ranking_profile=rate_ranking_profile,
        )
        field_candidates = _field_candidates(
            candidates,
            field_name,
            ranking_profile=field_ranking_profile,
        )
        resolution = resolved_fields.get(field_name, {}) or {}
        selected_identity = _selected_candidate_identity(resolution)
        selected_score = None
        if (resolution.get("selected_candidate") or {}).get("score") not in ["", None]:
            selected_score = float((resolution.get("selected_candidate") or {}).get("score") or 0.0)
        selected_candidate = None
        eligibility_rows = []
        candidates_by_quality = defaultdict(int)
        candidates_by_source = defaultdict(int)
        candidates_by_parser = defaultdict(int)
        rejected = []
        eligible_count = 0
        ineligible_count = 0
        for index, candidate in enumerate(field_candidates):
            eligibility = classify_candidate_eligibility(candidate, field_name, index=index)
            eligibility_rows.append(eligibility)
            candidates_by_quality[eligibility["quality_band"]] += 1
            candidates_by_source[_text(candidate.get("source")) or "unknown"] += 1
            candidates_by_parser[_text(candidate.get("parser_name")) or "unknown"] += 1
            if eligibility["eligible"]:
                eligible_count += 1
            else:
                ineligible_count += 1
            score = (
                _score(
                    field_name,
                    candidate,
                    triage or {},
                    ranking_profile=field_ranking_profile,
                )
                if eligibility["eligible"]
                else None
            )
            if selected_identity and _candidate_identity(candidate) == selected_identity:
                selected_candidate = _safe_candidate_trace(candidate, field_name, index, score=score)
                continue
            if not eligibility["eligible"]:
                reason = eligibility["eligibility_reason"]
            else:
                reason = _not_selected_reason(
                    field_name,
                    candidate,
                    selected_score=selected_score,
                    candidate_score=score,
                    resolution=resolution,
                )
            rejected.append(
                {
                    **_safe_candidate_trace(candidate, field_name, index, score=score),
                    "reason": reason,
                }
            )

        reasons = set(resolution.get("review_reasons", []) or [])
        if not field_candidates:
            decision_status = DECISION_NO_CANDIDATES
        elif eligible_count <= 0:
            decision_status = DECISION_NO_ELIGIBLE_CANDIDATES
        elif REVIEW_CONFLICTING_CANDIDATES in reasons:
            decision_status = DECISION_CONFLICT
        elif _is_stop_field(field_name) and resolution.get("selected_status"):
            decision_status = _text(resolution.get("selected_status"))
        elif REVIEW_LOW_CONFIDENCE_CRITICAL_FIELD in reasons:
            decision_status = DECISION_LOW_CONFIDENCE
        elif _text(resolution.get("value")):
            decision_status = DECISION_SELECTED
        else:
            decision_status = DECISION_REVIEW_REQUIRED

        traces[field_name] = {
            "field": field_name,
            "ranking_profile": field_ranking_profile,
            "selected_candidate": selected_candidate or {},
            "candidate_count_seen": len(field_candidates),
            "candidate_count_eligible": eligible_count,
            "candidate_count_ineligible": ineligible_count,
            "candidates_by_quality_band": dict(sorted(candidates_by_quality.items())),
            "candidates_by_source": dict(sorted(candidates_by_source.items())),
            "candidates_by_parser_name": dict(sorted(candidates_by_parser.items())),
            "candidate_eligibility": eligibility_rows[:50],
            "top_rejected_or_not_selected": sorted(
                rejected,
                key=lambda item: (
                    -float(item.get("score") or item.get("confidence") or 0.0),
                    item.get("parser_name", ""),
                ),
            )[:10],
            "decision_status": decision_status,
            "review_reasons": sorted(reasons),
        }
    return traces


def build_review_gate_trace(resolved_fields=None, review_reasons=None, triage=None):
    resolved_fields = resolved_fields if isinstance(resolved_fields, dict) else {}
    reasons = list(review_reasons or [])
    status_by_field = {}
    for field_name, threshold in FIELD_THRESHOLDS.items():
        resolution = resolved_fields.get(field_name, {}) or {}
        field_reasons = set(resolution.get("review_reasons", []) or [])
        present = bool(_text(resolution.get("value")))
        confidence = round(float(resolution.get("confidence") or 0.0), 3)
        structure_status = _stop_status_from_resolution(resolution)
        if _is_stop_field(field_name) and structure_status:
            present = present or structure_status in {
                STOP_STATUS_COMPLETE,
                STOP_STATUS_USEFUL_PARTIAL,
                STOP_STATUS_PARTIAL_ONLY,
                STOP_STATUS_AMBIGUOUS,
                STOP_STATUS_UNSUPPORTED,
            }
            if REVIEW_CONFLICTING_CANDIDATES in field_reasons:
                status = "conflict_review_required"
                reason = "structured stop conflict"
            elif structure_status == STOP_STATUS_UNSUPPORTED:
                status = "unsupported"
                reason = "structured stop value unsupported"
            elif structure_status == STOP_STATUS_USEFUL_PARTIAL:
                status = "partial_review_required"
                reason = "structured stop candidate is partial"
            elif structure_status in {STOP_STATUS_PARTIAL_ONLY, STOP_STATUS_AMBIGUOUS}:
                status = "partial_review_required"
                reason = "structured stop candidate is incomplete or ambiguous"
            elif not present or structure_status == STOP_STATUS_EMPTY:
                status = "missing"
                reason = "missing selected value"
            elif confidence < threshold:
                status = "low_confidence"
                reason = "below field threshold"
            else:
                status = "passed"
                reason = "field passed threshold"
        elif REVIEW_CONFLICTING_CANDIDATES in field_reasons:
            status = "conflict"
            reason = "conflicting candidates"
        elif not present:
            status = "missing"
            reason = "missing selected value"
        elif confidence < threshold:
            status = "low_confidence"
            reason = "below field threshold"
        else:
            status = "passed"
            reason = "field passed threshold"
        status_by_field[field_name] = {
            "present": present,
            "confidence": confidence,
            "threshold": threshold,
            "status": status,
            "reason": reason,
            "structure_status": structure_status,
            "selected": bool((resolution or {}).get("selected_candidate")),
        }
    sources = {
        "missing_field": [],
        "low_confidence": [],
        "conflict": [],
        "triage": [],
        "validation": [],
        "layout": [],
    }
    for reason in reasons:
        if ":" in reason:
            reason_name, field_name = reason.split(":", 1)
        else:
            reason_name, field_name = reason, ""
        if reason_name == REVIEW_MISSING_CRITICAL_FIELD:
            sources["missing_field"].append(field_name)
        elif reason_name == REVIEW_LOW_CONFIDENCE_CRITICAL_FIELD:
            sources["low_confidence"].append(field_name)
        elif reason_name == REVIEW_CONFLICTING_CANDIDATES:
            sources["conflict"].append(field_name)
        elif reason_name in {REVIEW_TRIAGE_OCR_REQUIRED, REVIEW_TRIAGE_NATIVE_TEXT_SUSPICIOUS}:
            sources["triage"].append(reason_name)
        else:
            sources["validation"].append(reason_name)
    return {
        "needs_review": bool(reasons),
        "critical_field_status": status_by_field,
        "review_reason_sources": {
            key: sorted(set(value))
            for key, value in sources.items()
            if value
        },
    }


def _stop_row(field_name, candidate, triage, ranking_profile=RANKING_PROFILE_BASELINE):
    normalized = _stop_normalization(candidate, field_name)
    score = _score(field_name, candidate, triage, ranking_profile=ranking_profile)
    # Keep thresholds unchanged; completeness is only a stop-specific
    # tie-breaker so richer structured candidates sort ahead of thin evidence.
    rank_score = min(1.0, round(score + (0.03 * float(normalized.get("completeness_score") or 0.0)), 3))
    return {
        "candidate": candidate,
        "normalized": normalized,
        "score": score,
        "rank_score": rank_score,
        "status": normalized.get("structure_status"),
        "key": stop_equivalence_key(normalized),
    }


def _stop_conflict_summary(field_name, rows, selected_row=None, duplicates_collapsed=0, true_conflicts=None, partial_overlaps=0, selected_status="none"):
    true_conflicts = list(true_conflicts or [])
    conflict_counts = defaultdict(int)
    for conflict in true_conflicts:
        for conflict_type in conflict.get("conflict_types", []) or []:
            conflict_counts[conflict_type] += 1
    return {
        "field": field_name,
        "candidate_count": len(rows or []),
        "normalized_candidate_count": len(
            [
                row
                for row in rows or []
                if row.get("status") not in {STOP_STATUS_EMPTY, STOP_STATUS_UNSUPPORTED}
            ]
        ),
        "duplicates_collapsed": int(duplicates_collapsed or 0),
        "true_conflict_count": len(true_conflicts),
        "partial_overlap_count": int(partial_overlaps or 0),
        "selected_status": selected_status,
        "conflict_type_counts": dict(sorted(conflict_counts.items())),
        "selected_source": _text(((selected_row or {}).get("candidate") or {}).get("source")),
        "selected_pairing_method": _text(
            _metadata(((selected_row or {}).get("candidate") or {})).get("pairing_method")
        ),
        "selected_completeness_score": round(
            float(((selected_row or {}).get("normalized") or {}).get("completeness_score") or 0.0),
            3,
        ),
    }


def _stop_resolution_empty(field_name, field_candidates, reason):
    return {
        "value": "",
        "confidence": 0.0,
        "evidence_text": "",
        "page": "",
        "source": "",
        "candidate_count": len(field_candidates or []),
        "competing_candidates": [],
        "needs_review": True,
        "review_reasons": [reason],
        "structure_status": STOP_STATUS_EMPTY,
        "structured_stop_summary": {
            "field": field_name,
            "role": "pickup" if field_name == FIELD_PICKUP_STOPS else "delivery",
            "stop_count": 0,
            "has_location": False,
            "has_date": False,
            "has_time": False,
            "has_facility": False,
            "has_address": False,
            "completeness_score": 0.0,
            "structure_status": STOP_STATUS_EMPTY,
            "normalization_warnings": [],
        },
        "structured_stop_conflict_summary": _stop_conflict_summary(
            field_name,
            [],
            selected_status="none",
        ),
    }


def _resolve_stop_field(
    field_name,
    candidates,
    triage,
    ranking_profile=RANKING_PROFILE_BASELINE,
):
    field_candidates = _field_candidates(
        candidates,
        field_name,
        ranking_profile=ranking_profile,
    )
    threshold = FIELD_THRESHOLDS.get(field_name, 0.70)
    if not field_candidates:
        return _stop_resolution_empty(
            field_name,
            field_candidates,
            REVIEW_MISSING_CRITICAL_FIELD,
        )

    rows = [
        _stop_row(
            field_name,
            candidate,
            triage,
            ranking_profile=ranking_profile,
        )
        for candidate in field_candidates
    ]
    unsupported = [row for row in rows if row["status"] == STOP_STATUS_UNSUPPORTED]
    nonempty = [row for row in rows if row["status"] != STOP_STATUS_EMPTY]
    selectable = [row for row in rows if _stop_is_selectable(row["normalized"])]
    if not selectable:
        reason = (
            REVIEW_STRUCTURED_STOP_UNSUPPORTED
            if unsupported and not any(row["status"] != STOP_STATUS_UNSUPPORTED for row in nonempty)
            else REVIEW_MISSING_CRITICAL_FIELD
        )
        summary = _stop_conflict_summary(
            field_name,
            rows,
            duplicates_collapsed=0,
            selected_status="unsupported" if reason == REVIEW_STRUCTURED_STOP_UNSUPPORTED else "none",
        )
        empty = _stop_resolution_empty(field_name, field_candidates, reason)
        empty["structure_status"] = (
            STOP_STATUS_UNSUPPORTED if reason == REVIEW_STRUCTURED_STOP_UNSUPPORTED else STOP_STATUS_EMPTY
        )
        empty["structured_stop_conflict_summary"] = summary
        return empty

    unique_rows = []
    seen = {}
    duplicates_collapsed = 0
    partial_overlaps = 0
    for row in sorted(selectable, key=lambda item: (item["rank_score"], item["score"]), reverse=True):
        key = row["key"]
        if key in seen:
            duplicates_collapsed += 1
            continue
        # Treat same-role partials without material values as overlaps, not true
        # conflicts. This avoids turning repeated location-only/date-only hints
        # into resolver conflicts.
        if row["status"] == STOP_STATUS_USEFUL_PARTIAL:
            partial_overlaps += sum(
                1
                for existing in unique_rows
                if not stop_conflict_types(existing["normalized"], row["normalized"])
            )
        seen[key] = row
        unique_rows.append(row)

    best = unique_rows[0]
    true_conflicts = []
    for row in unique_rows[1:]:
        conflicts = stop_conflict_types(best["normalized"], row["normalized"])
        if conflicts and row["score"] >= threshold and best["score"] >= threshold:
            true_conflicts.append(
                {
                    "conflict_types": conflicts,
                    "left_status": best["status"],
                    "right_status": row["status"],
                }
            )

    best_status = best["status"]
    if true_conflicts:
        selected_status = "conflict"
    elif best_status == STOP_STATUS_COMPLETE:
        selected_status = DECISION_SELECTED_COMPLETE
    else:
        selected_status = DECISION_SELECTED_USEFUL_PARTIAL

    reasons = []
    needs_review = False
    if true_conflicts:
        needs_review = True
        reasons.append(REVIEW_CONFLICTING_CANDIDATES)
    if best_status == STOP_STATUS_USEFUL_PARTIAL:
        needs_review = True
        reasons.append(REVIEW_STRUCTURED_STOP_PARTIAL)
    if best["score"] < threshold:
        needs_review = True
        reasons.append(REVIEW_LOW_CONFIDENCE_CRITICAL_FIELD)

    selected_candidate = _with_stop_metadata(best["candidate"], best["normalized"], selected_status)
    competing = []
    for row in unique_rows[1:6]:
        candidate = _with_stop_metadata(row["candidate"], row["normalized"])
        competing.append(_public_candidate(candidate, row["score"]))
    summary = _stop_conflict_summary(
        field_name,
        rows,
        selected_row=best,
        duplicates_collapsed=duplicates_collapsed,
        true_conflicts=true_conflicts,
        partial_overlaps=partial_overlaps,
        selected_status=selected_status,
    )
    return {
        "value": _stop_value_label(best["normalized"]),
        "confidence": best["score"],
        "evidence_text": _text(best["candidate"].get("evidence_text")),
        "page": best["candidate"].get("page", ""),
        "source": _text(best["candidate"].get("source")),
        "candidate_count": len(field_candidates),
        "competing_candidates": competing,
        "needs_review": needs_review,
        "review_reasons": reasons,
        "selected_candidate": _public_candidate(selected_candidate, best["score"]),
        "structure_status": best_status,
        "selected_status": selected_status,
        "structured_stop_summary": safe_stop_normalization_summary(best["normalized"]),
        "structured_stop_conflict_summary": summary,
    }


def _resolve_one_field(
    field_name,
    candidates,
    triage,
    ranking_profile=RANKING_PROFILE_BASELINE,
):
    if _is_stop_field(field_name):
        return _resolve_stop_field(
            field_name,
            candidates,
            triage,
            ranking_profile=ranking_profile,
        )
    field_candidates = _field_candidates(
        candidates,
        field_name,
        ranking_profile=ranking_profile,
    )
    threshold = FIELD_THRESHOLDS.get(field_name, 0.65)
    if not field_candidates:
        return {
            "value": "",
            "confidence": 0.0,
            "evidence_text": "",
            "page": "",
            "source": "",
            "candidate_count": 0,
            "competing_candidates": [],
            "needs_review": True,
            "review_reasons": [REVIEW_MISSING_CRITICAL_FIELD],
        }

    scored = sorted(
        [
            (
                _score(
                    field_name,
                    candidate,
                    triage,
                    ranking_profile=ranking_profile,
                ),
                candidate,
            )
            for candidate in field_candidates
            if _value(candidate)
        ],
        key=lambda item: (item[0], _value(item[1])),
        reverse=True,
    )
    if not scored:
        return {
            "value": "",
            "confidence": 0.0,
            "evidence_text": "",
            "page": "",
            "source": "",
            "candidate_count": len(field_candidates),
            "competing_candidates": [],
            "needs_review": True,
            "review_reasons": [REVIEW_MISSING_CRITICAL_FIELD],
        }

    best_score, best = scored[0]
    best_value = _value(best)
    strong_different = [
        (score, candidate)
        for score, candidate in scored[1:]
        if score >= threshold and _value(candidate) and _value(candidate) != best_value
    ]
    reasons = []
    needs_review = False
    if strong_different and best_score >= threshold:
        needs_review = True
        reasons.append(REVIEW_CONFLICTING_CANDIDATES)
    if best_score < threshold:
        needs_review = True
        reasons.append(REVIEW_LOW_CONFIDENCE_CRITICAL_FIELD)

    return {
        "value": "" if REVIEW_CONFLICTING_CANDIDATES in reasons else best_value,
        "confidence": best_score,
        "evidence_text": _text(best.get("evidence_text")),
        "page": best.get("page", ""),
        "source": _text(best.get("source")),
        "candidate_count": len(field_candidates),
        "competing_candidates": [
            _public_candidate(candidate, score)
            for score, candidate in scored[1:6]
        ],
        "needs_review": needs_review,
        "review_reasons": reasons,
        "selected_candidate": _public_candidate(best, best_score),
    }


def resolve_candidates(
    candidates,
    artifact=None,
    triage=None,
    field_names=None,
    ranking_profile=RANKING_PROFILE_BASELINE,
    load_ranking_profile=None,
    rate_ranking_profile=None,
):
    artifact = artifact or {}
    triage = triage if isinstance(triage, dict) else artifact.get("triage", {})
    _validate_ranking_profiles(
        ranking_profile=ranking_profile,
        load_ranking_profile=load_ranking_profile,
        rate_ranking_profile=rate_ranking_profile,
    )
    candidates = _apply_field_scoped_candidate_profiles(
        candidates,
        ranking_profile=ranking_profile,
        load_ranking_profile=load_ranking_profile,
        rate_ranking_profile=rate_ranking_profile,
    )
    target_fields = tuple(field_names or FIELD_THRESHOLDS.keys())
    resolved_fields = {
        field_name: _resolve_one_field(
            field_name,
            candidates,
            triage,
            ranking_profile=_effective_ranking_profile(
                field_name,
                ranking_profile=ranking_profile,
                load_ranking_profile=load_ranking_profile,
                rate_ranking_profile=rate_ranking_profile,
            ),
        )
        for field_name in target_fields
    }
    review_reasons = []
    for field_name, resolution in resolved_fields.items():
        for reason in resolution.get("review_reasons", []):
            review_reasons.append(f"{reason}:{field_name}")
    if (triage or {}).get("ocr_required"):
        review_reasons.append(REVIEW_TRIAGE_OCR_REQUIRED)
    if "NATIVE_TEXT_SUSPICIOUS" in set((triage or {}).get("quality_flags", []) or []):
        review_reasons.append(REVIEW_TRIAGE_NATIVE_TEXT_SUSPICIOUS)

    result = {
        "resolved_fields": resolved_fields,
        "final_values": {
            field_name: resolution.get("value", "")
            for field_name, resolution in resolved_fields.items()
        },
        "needs_review": bool(review_reasons),
        "review_reasons": sorted(set(review_reasons)),
        "candidate_count": len([candidate for candidate in candidates or [] if isinstance(candidate, dict)]),
        "candidate_count_by_field": dict(
            sorted(
                defaultdict(
                    int,
                    {
                        field_name: len(
                            _field_candidates(
                                candidates,
                                field_name,
                                ranking_profile=_effective_ranking_profile(
                                    field_name,
                                    ranking_profile=ranking_profile,
                                    load_ranking_profile=load_ranking_profile,
                                    rate_ranking_profile=rate_ranking_profile,
                                ),
                            )
                        )
                        for field_name in target_fields
                    },
                ).items()
            )
        ),
        "resolver_version": "field_candidate_resolver_v1",
        "ranking_profile": ranking_profile,
        "load_ranking_profile": load_ranking_profile or RANKING_PROFILE_BASELINE,
        "rate_ranking_profile": rate_ranking_profile or RANKING_PROFILE_BASELINE,
        "field_ranking_profiles": _effective_field_ranking_profiles(
            ranking_profile=ranking_profile,
            load_ranking_profile=load_ranking_profile,
            rate_ranking_profile=rate_ranking_profile,
        ),
        "field_scoped_ranking_enabled": bool(
            load_ranking_profile is not None or rate_ranking_profile is not None
        ),
    }
    result["resolver_decision_traces"] = build_resolver_decision_traces(
        candidates,
        resolved_fields=resolved_fields,
        triage=triage,
        field_names=target_fields,
        ranking_profile=ranking_profile,
        load_ranking_profile=load_ranking_profile,
        rate_ranking_profile=rate_ranking_profile,
    )
    result["review_gate_trace"] = build_review_gate_trace(
        resolved_fields=resolved_fields,
        review_reasons=result["review_reasons"],
        triage=triage,
    )
    return result
