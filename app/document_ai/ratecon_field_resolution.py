"""RateCon field resolution contracts.

Resolution is still extraction-layer output. It records selected candidates,
missing fields, conflicts, and low-confidence fields without creating cases or
making dispatch recommendations.
"""

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
CANDIDATE_CONFIDENCE_MEDIUM,
    FIELD_BROKER_MC,
    FIELD_BROKER_NAME,
    FIELD_COMMODITY,
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_LOCATION,
    FIELD_EQUIPMENT,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    FIELD_RATE,
    FIELD_WEIGHT,
)

FIELD_RESOLUTION_STATUS_RESOLVED = "resolved"
FIELD_RESOLUTION_STATUS_MISSING = "missing"
FIELD_RESOLUTION_STATUS_NEEDS_REVIEW = "needs_review"
FIELD_RESOLUTION_STATUS_CONFLICT = "conflict"
FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE = "low_confidence"

FIELD_RESOLUTION_STATUSES = (
    FIELD_RESOLUTION_STATUS_RESOLVED,
    FIELD_RESOLUTION_STATUS_MISSING,
    FIELD_RESOLUTION_STATUS_NEEDS_REVIEW,
    FIELD_RESOLUTION_STATUS_CONFLICT,
    FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE,
)

RATECON_FIELD_RESOLVER_VERSION = "ratecon_field_resolver_contract_v1"
RATECON_GENERIC_RESOLVER_VERSION = "ratecon_generic_resolver_v1"

DEFAULT_RATECON_RESOLUTION_FIELDS = (
    FIELD_BROKER_NAME,
    FIELD_BROKER_MC,
    FIELD_LOAD_NUMBER,
    FIELD_RATE,
    FIELD_PICKUP_LOCATION,
    FIELD_PICKUP_DATE,
    FIELD_DELIVERY_LOCATION,
    FIELD_DELIVERY_DATE,
    FIELD_EQUIPMENT,
    FIELD_WEIGHT,
    FIELD_COMMODITY,
)

CONFIDENCE_RANKS = {
    CANDIDATE_CONFIDENCE_HIGH: 3,
    CANDIDATE_CONFIDENCE_MEDIUM: 2,
    CANDIDATE_CONFIDENCE_LOW: 1,
}
MIN_RESOLVE_CONFIDENCE_RANK = CONFIDENCE_RANKS[CANDIDATE_CONFIDENCE_MEDIUM]
REVIEW_WARNING_MARKERS = {
    "template_negative_label_seen",
    "accessorial_label_not_main_rate",
}


def _normalize_list(value):
    if value is None:
        return []

    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]

    return [
        str(item).strip()
        for item in values
        if str(item).strip()
    ]


def normalize_resolution_status(value):
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")

    if text in FIELD_RESOLUTION_STATUSES:
        return text

    return FIELD_RESOLUTION_STATUS_NEEDS_REVIEW


def build_field_resolution(
    field_name,
    status,
    selected_candidate=None,
    rejected_candidates=None,
    confidence="",
    reasons=None,
    evidence_refs=None,
    warnings=None,
):
    safe_selected = selected_candidate if isinstance(selected_candidate, dict) else {}
    safe_rejected = [
        candidate
        for candidate in rejected_candidates or []
        if isinstance(candidate, dict)
    ]

    return {
        "field_name": str(field_name or "").strip(),
        "status": normalize_resolution_status(status),
        "selected_candidate": safe_selected,
        "rejected_candidates": safe_rejected,
        "confidence": str(confidence or "").strip(),
        "reasons": _normalize_list(reasons),
        "evidence_refs": _normalize_list(evidence_refs),
        "warnings": _normalize_list(warnings),
    }


def build_ratecon_field_resolution_result(
    document_id="",
    artifact_id="",
    resolutions=None,
    missing_fields=None,
    needs_check_fields=None,
    conflict_fields=None,
    warnings=None,
    resolver_version=RATECON_FIELD_RESOLVER_VERSION,
):
    safe_resolutions = [
        resolution
        for resolution in resolutions or []
        if isinstance(resolution, dict)
    ]

    return {
        "document_id": str(document_id or "").strip(),
        "artifact_id": str(artifact_id or "").strip(),
        "resolutions": safe_resolutions,
        "missing_fields": _normalize_list(missing_fields),
        "needs_check_fields": _normalize_list(needs_check_fields),
        "conflict_fields": _normalize_list(conflict_fields),
        "warnings": _normalize_list(warnings),
        "resolver_version": str(resolver_version or RATECON_FIELD_RESOLVER_VERSION).strip(),
    }


def _candidate_confidence_rank(candidate):
    return CONFIDENCE_RANKS.get(str(candidate.get("confidence", "")).upper(), 0)


def _candidate_value(candidate):
    return str(candidate.get("normalized_value") or candidate.get("raw_value") or "").strip()


def _candidate_evidence_ref(candidate):
    candidate_id = str(candidate.get("candidate_id") or "").strip()
    if candidate_id:
        return candidate_id

    page_number = candidate.get("page_number", "")
    line_number = candidate.get("line_number", "")
    if page_number or line_number:
        return f"p{page_number}-l{line_number}"

    return ""


def _group_candidates(candidate_result):
    grouped = {}

    for candidate in candidate_result.get("candidates", []):
        if not isinstance(candidate, dict):
            continue

        field_name = str(candidate.get("field_name") or "").strip()
        if not field_name:
            continue

        grouped.setdefault(field_name, []).append(candidate)

    return grouped


def _resolution_for_field(field_name, candidates):
    if not candidates:
        return build_field_resolution(
            field_name=field_name,
            status=FIELD_RESOLUTION_STATUS_MISSING,
            reasons=["no_candidate"],
        )

    sorted_candidates = sorted(
        candidates,
        key=lambda candidate: (_candidate_confidence_rank(candidate), _candidate_value(candidate)),
        reverse=True,
    )
    best = sorted_candidates[0]
    best_rank = _candidate_confidence_rank(best)
    best_value = _candidate_value(best)
    best_warnings = set(best.get("warnings", []))
    evidence_refs = [
        evidence_ref
        for evidence_ref in [_candidate_evidence_ref(best)]
        if evidence_ref
    ]

    if best_warnings.intersection(REVIEW_WARNING_MARKERS):
        return build_field_resolution(
            field_name=field_name,
            status=FIELD_RESOLUTION_STATUS_NEEDS_REVIEW,
            selected_candidate=best,
            rejected_candidates=sorted_candidates[1:],
            confidence=best.get("confidence", ""),
            reasons=["candidate_warning_requires_review"],
            evidence_refs=evidence_refs,
            warnings=best.get("warnings", []),
        )

    if best_rank < MIN_RESOLVE_CONFIDENCE_RANK:
        return build_field_resolution(
            field_name=field_name,
            status=FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE,
            selected_candidate=best,
            rejected_candidates=sorted_candidates[1:],
            confidence=best.get("confidence", ""),
            reasons=["best_candidate_below_threshold"],
            evidence_refs=evidence_refs,
            warnings=["field_requires_review"],
        )

    strong_candidates = [
        candidate
        for candidate in sorted_candidates
        if _candidate_confidence_rank(candidate) >= MIN_RESOLVE_CONFIDENCE_RANK
    ]
    strong_values = {
        _candidate_value(candidate)
        for candidate in strong_candidates
        if _candidate_value(candidate)
    }

    if len(strong_values) > 1:
        return build_field_resolution(
            field_name=field_name,
            status=FIELD_RESOLUTION_STATUS_CONFLICT,
            selected_candidate=best,
            rejected_candidates=sorted_candidates[1:],
            confidence=best.get("confidence", ""),
            reasons=["multiple_strong_candidate_values"],
            evidence_refs=[
                ref
                for ref in [_candidate_evidence_ref(candidate) for candidate in strong_candidates]
                if ref
            ],
            warnings=["field_conflict_requires_review"],
        )

    return build_field_resolution(
        field_name=field_name,
        status=FIELD_RESOLUTION_STATUS_RESOLVED,
        selected_candidate=best,
        rejected_candidates=sorted_candidates[1:],
        confidence=best.get("confidence", ""),
        reasons=["selected_highest_confidence_candidate"],
        evidence_refs=evidence_refs,
        warnings=best.get("warnings", []),
    )


def resolve_ratecon_fields(candidate_result, field_names=None):
    grouped = _group_candidates(candidate_result)
    target_fields = tuple(field_names or DEFAULT_RATECON_RESOLUTION_FIELDS)
    resolutions = []
    missing_fields = []
    needs_check_fields = []
    conflict_fields = []

    for field_name in target_fields:
        resolution = _resolution_for_field(field_name, grouped.get(field_name, []))
        resolutions.append(resolution)

        status = resolution["status"]
        if status == FIELD_RESOLUTION_STATUS_MISSING:
            missing_fields.append(field_name)
        elif status == FIELD_RESOLUTION_STATUS_CONFLICT:
            conflict_fields.append(field_name)
            needs_check_fields.append(field_name)
        elif status in [
            FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE,
            FIELD_RESOLUTION_STATUS_NEEDS_REVIEW,
        ]:
            needs_check_fields.append(field_name)

    return build_ratecon_field_resolution_result(
        document_id=candidate_result.get("document_id", ""),
        artifact_id=candidate_result.get("artifact_id", ""),
        resolutions=resolutions,
        missing_fields=missing_fields,
        needs_check_fields=needs_check_fields,
        conflict_fields=conflict_fields,
        warnings=candidate_result.get("warnings", []),
        resolver_version=RATECON_GENERIC_RESOLVER_VERSION,
    )


def resolve_ratecon_fields_with_template_context(template_aware_result, field_names=None):
    template_selection = template_aware_result.get("template_selection_result", {})
    template_status = template_selection.get("status", "")
    trusted_template = template_status == "matched"
    candidate_result = (
        template_aware_result.get("adjusted_candidate_result", {})
        if trusted_template
        else template_aware_result.get("base_candidate_result", {})
    )
    result = resolve_ratecon_fields(candidate_result, field_names=field_names)
    warnings = list(result.get("warnings", []))
    needs_check_fields = list(result.get("needs_check_fields", []))

    if template_status in ["conflict", "low_confidence"]:
        if "template_match" not in needs_check_fields:
            needs_check_fields.append("template_match")
        warnings.append(f"template_match_{template_status}")
    elif not trusted_template:
        warnings.append("generic_resolution_without_template")

    result["needs_check_fields"] = needs_check_fields
    result["warnings"] = sorted(set(warnings))
    result["template_match_status"] = template_status
    result["selected_template_id"] = (
        template_selection.get("selected_template_id", "") if trusted_template else ""
    )
    result["selected_broker_key"] = (
        template_selection.get("selected_broker_key", "") if trusted_template else ""
    )
    result["template_match_confidence"] = template_selection.get("selected_confidence", 0.0)
    result["template_context_used"] = trusted_template

    return result
