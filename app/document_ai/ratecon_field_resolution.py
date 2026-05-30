"""RateCon field resolution contracts.

Resolution is still extraction-layer output. It records selected candidates,
missing fields, conflicts, and low-confidence fields without creating cases or
making dispatch recommendations.
"""

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
