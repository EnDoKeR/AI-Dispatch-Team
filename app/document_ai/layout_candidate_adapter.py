"""Adapters from layout evidence to existing RateCon field candidates."""

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_LOW,
    SOURCE_TABLE_PATTERN_FUTURE,
    build_field_candidate,
    normalize_confidence,
    normalize_list,
)


def _evidence_ref_id(evidence_ref):
    if not isinstance(evidence_ref, dict):
        return str(evidence_ref or "").strip()

    parts = [
        f"p{evidence_ref.get('page_number', '')}",
        evidence_ref.get("line_id", ""),
        evidence_ref.get("block_id", ""),
        evidence_ref.get("table_id", ""),
        evidence_ref.get("cell_ref", ""),
        evidence_ref.get("evidence_type", ""),
    ]
    return ":".join(str(part).strip() for part in parts if str(part).strip())


def attach_layout_evidence_to_candidate(
    candidate,
    layout_evidence_ref=None,
    section_role="",
    page_role="",
    proximity_type="",
    layout_confidence_reason="",
):
    enriched = dict(candidate or {})
    evidence_ref = layout_evidence_ref if isinstance(layout_evidence_ref, dict) else {}
    bbox = evidence_ref.get("bbox") if isinstance(evidence_ref, dict) else None

    enriched["layout_evidence_ref"] = evidence_ref
    enriched["layout_page_number"] = evidence_ref.get("page_number", "")
    enriched["layout_bbox"] = bbox or {}
    enriched["layout_line_id"] = evidence_ref.get("line_id", "")
    enriched["layout_block_id"] = evidence_ref.get("block_id", "")
    enriched["layout_table_id"] = evidence_ref.get("table_id", "")
    enriched["layout_cell_ref"] = evidence_ref.get("cell_ref", "")
    enriched["layout_section_role"] = str(section_role or "").strip()
    enriched["layout_page_role"] = str(page_role or "").strip()
    enriched["layout_proximity_type"] = str(proximity_type or "").strip()
    enriched["layout_confidence_reason"] = str(layout_confidence_reason or "").strip()

    return enriched


def build_field_candidate_from_layout_value(
    field_name,
    label_value_candidate,
    raw_value=None,
    normalized_value=None,
    confidence=None,
    confidence_reasons=None,
    source=SOURCE_TABLE_PATTERN_FUTURE,
    value_type="",
    warnings=None,
    section_role="",
    page_role="",
):
    label_value_candidate = label_value_candidate or {}
    candidate_raw_value = (
        str(raw_value).strip()
        if raw_value not in [None, ""]
        else str(label_value_candidate.get("value_text_redacted", "")).strip()
    )
    candidate_confidence = normalize_confidence(
        confidence or label_value_candidate.get("confidence") or CANDIDATE_CONFIDENCE_LOW
    )
    reasons = normalize_list(confidence_reasons)
    if not reasons:
        reasons = normalize_list(label_value_candidate.get("reasons"))
    if label_value_candidate.get("proximity_type"):
        reasons.append(f"layout_proximity:{label_value_candidate['proximity_type']}")

    evidence_ref = label_value_candidate.get("evidence_ref", {})
    candidate = build_field_candidate(
        field_name=field_name,
        raw_value=candidate_raw_value,
        normalized_value=normalized_value if normalized_value not in [None, ""] else candidate_raw_value,
        confidence=candidate_confidence,
        confidence_reasons=reasons,
        page_number=label_value_candidate.get("page_number", ""),
        label=label_value_candidate.get("label", ""),
        source=source,
        evidence_ref=_evidence_ref_id(evidence_ref),
        warnings=warnings,
        value_type=value_type,
    )

    return attach_layout_evidence_to_candidate(
        candidate,
        layout_evidence_ref=evidence_ref,
        section_role=section_role,
        page_role=page_role,
        proximity_type=label_value_candidate.get("proximity_type", ""),
        layout_confidence_reason="; ".join(reasons),
    )


def convert_label_value_candidates_to_field_candidates(
    field_name,
    label_value_candidates,
    value_type="",
    source=SOURCE_TABLE_PATTERN_FUTURE,
    warnings=None,
    section_role="",
    page_role="",
):
    return [
        build_field_candidate_from_layout_value(
            field_name=field_name,
            label_value_candidate=label_value_candidate,
            source=source,
            value_type=value_type,
            warnings=warnings,
            section_role=section_role,
            page_role=page_role,
        )
        for label_value_candidate in (label_value_candidates or [])
        if isinstance(label_value_candidate, dict)
    ]
