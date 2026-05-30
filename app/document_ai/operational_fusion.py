"""Operational detail candidate fusion guardrails."""

from collections import defaultdict

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_MEDIUM,
    FIELD_COMMODITY,
    FIELD_EQUIPMENT,
    FIELD_SPECIAL_REQUIREMENT,
    FIELD_WEIGHT,
    normalize_confidence,
)


OPERATIONAL_FUSION_VERSION = "operational_fusion_v1"

OPERATIONAL_FIELDS = {
    FIELD_EQUIPMENT,
    FIELD_WEIGHT,
    FIELD_COMMODITY,
    FIELD_SPECIAL_REQUIREMENT,
}

_HIGH_CONTEXT_SECTIONS = {
    "EQUIPMENT_SUMMARY",
    "COMMODITY_WEIGHT",
    "SPECIAL_INSTRUCTIONS",
}

_LOW_CONTEXT_SECTIONS = {
    "LEGAL_TERMS",
    "PAYMENT_TERMS",
    "BILLING_INSTRUCTIONS",
}

_UNRESOLVED_STATUSES = {
    "",
    "missing",
    "needs_review",
    "low_confidence",
    "conflict",
    "unknown",
}


def _text(value):
    return str(value or "").strip()


def _candidate_id(candidate, index):
    return _text((candidate or {}).get("candidate_id")) or f"operational_candidate_{index + 1}"


def _value(candidate):
    return _text((candidate or {}).get("normalized_value") or (candidate or {}).get("raw_value")).lower()


def _confidence_score(candidate):
    confidence = normalize_confidence((candidate or {}).get("confidence"))
    if confidence == CANDIDATE_CONFIDENCE_HIGH:
        base = 0.85
    elif confidence == CANDIDATE_CONFIDENCE_MEDIUM:
        base = 0.6
    elif confidence == CANDIDATE_CONFIDENCE_LOW:
        base = 0.3
    else:
        base = 0.2

    section = _text((candidate or {}).get("layout_section_role")).upper()
    if section in _HIGH_CONTEXT_SECTIONS:
        base += 0.1
    if section in _LOW_CONTEXT_SECTIONS:
        base -= 0.15
    if "requirement_from_supplemental_terms" in (candidate or {}).get("warnings", []):
        base -= 0.15
    return max(0.0, min(base, 1.0))


def _group_candidates(candidates):
    grouped = defaultdict(list)
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        field_name = _text(candidate.get("field_name"))
        if field_name in OPERATIONAL_FIELDS:
            grouped[field_name].append(candidate)
    return grouped


def fuse_operational_detail_candidates(
    text_candidates=None,
    layout_candidates=None,
    baseline_statuses=None,
):
    baseline_statuses = baseline_statuses or {}
    grouped = _group_candidates((text_candidates or []) + (layout_candidates or []))
    decisions = []
    improved = []
    worsened = []
    unchanged = []
    conflicts = []
    warnings = []

    for field_name in sorted(grouped):
        candidates = grouped[field_name]
        ranked = sorted(
            enumerate(candidates),
            key=lambda item: (_confidence_score(item[1]), -item[0]),
            reverse=True,
        )
        selected_index, selected = ranked[0]
        selected_id = _candidate_id(selected, selected_index)
        baseline_status = _text(baseline_statuses.get(field_name))
        selected_value = _value(selected)

        conflict_ids = []
        for index, candidate in ranked[1:]:
            if _confidence_score(candidate) < 0.75 or _confidence_score(selected) < 0.75:
                continue
            if _value(candidate) and _value(candidate) != selected_value:
                conflict_ids.extend([selected_id, _candidate_id(candidate, index)])

        if conflict_ids:
            status = "conflict"
            conflicts.append(field_name)
            warnings.append(f"operational_fusion_conflict:{field_name}")
            did_improve = False
            did_worsen = baseline_status == "resolved"
        else:
            status = "resolved"
            did_improve = baseline_status in _UNRESOLVED_STATUSES
            did_worsen = False
            if did_improve:
                improved.append(field_name)
            else:
                unchanged.append(field_name)

        if did_worsen:
            worsened.append(field_name)

        decisions.append(
            {
                "field_name": field_name,
                "fused_status": status,
                "selected_candidate_id": "" if conflict_ids else selected_id,
                "conflict_candidate_ids": sorted(set(conflict_ids)),
                "did_improve_baseline": did_improve,
                "did_worsen_baseline": did_worsen,
                "review_required": bool(conflict_ids),
                "warning_codes": sorted(set(warnings)),
            }
        )

    return {
        "decisions": decisions,
        "improved_fields": sorted(set(improved)),
        "worsened_fields": sorted(set(worsened)),
        "unchanged_fields": sorted(set(unchanged)),
        "conflict_fields": sorted(set(conflicts)),
        "warning_codes": sorted(set(warnings)),
        "fusion_version": OPERATIONAL_FUSION_VERSION,
    }
