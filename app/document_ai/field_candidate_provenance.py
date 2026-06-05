"""Field candidate provenance model and adapters."""

from dataclasses import asdict, dataclass, field as dataclass_field

from app.document_ai.ratecon_canonical_fields import (
    canonical_field_mapping,
    confidence_after_mapping,
    normalize_raw_field_name,
)
from app.document_ai.load_identifier_candidate_adapter_provenance import (
    preserve_load_candidate_provenance,
)


SOURCE_NATIVE_TEXT = "native_text"
SOURCE_NATIVE_LAYOUT = "native_layout"
SOURCE_OCR = "ocr"
SOURCE_REGEX = "regex"
SOURCE_BROKER_PARSER = "broker_parser"
SOURCE_LEGACY_PARSER = "legacy_parser"
SOURCE_UNKNOWN = "unknown"

CONFIDENCE_SCORE_BY_LEVEL = {
    "HIGH": 0.9,
    "MEDIUM": 0.65,
    "LOW": 0.35,
    "UNKNOWN": 0.0,
}

@dataclass(frozen=True)
class FieldCandidate:
    field: str
    value: str
    normalized_value: str = ""
    label: str = ""
    evidence_text: str = ""
    page: int | None = None
    bbox: list | None = None
    source: str = SOURCE_UNKNOWN
    parser_name: str = ""
    confidence: float = 0.0
    metadata: dict = dataclass_field(default_factory=dict)

    def to_dict(self):
        payload = asdict(self)
        if payload["page"] is None:
            payload["page"] = ""
        return payload


def _text(value):
    return str(value or "").strip()


def _canonical_field(field_name):
    return canonical_field_mapping(field_name).canonical_field


def _confidence_score(value):
    if isinstance(value, (int, float)):
        return max(0.0, min(float(value), 1.0))
    token = _text(value).upper().replace(" ", "_").replace("-", "_")
    return CONFIDENCE_SCORE_BY_LEVEL.get(token, 0.0)


def _source_from_candidate(candidate):
    source = _text((candidate or {}).get("source")).lower()
    evidence_ref = _text((candidate or {}).get("evidence_ref")).lower()
    if "ocr" in source:
        return SOURCE_OCR
    if "layout" in source or "layout" in evidence_ref or (candidate or {}).get("bbox"):
        return SOURCE_NATIVE_LAYOUT
    if source in {"regex", "label_pattern", "section_pattern"}:
        return SOURCE_NATIVE_TEXT
    if "broker" in source or "template" in source:
        return SOURCE_BROKER_PARSER
    return source or SOURCE_UNKNOWN


def _page(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed or None


def _evidence_from_parts(label="", value="", context_before="", context_after=""):
    parts = [_text(label), _text(value)]
    if not parts[0]:
        parts = [_text(context_before), _text(value), _text(context_after)]
    return " ".join(part for part in parts if part).strip()


def _find_evidence_line(full_text, value):
    needle = _text(value)
    if not needle:
        return ""
    for line in str(full_text or "").splitlines():
        if needle and needle in line:
            return line.strip()
    return ""


def build_field_candidate(
    field,
    value,
    normalized_value="",
    label="",
    evidence_text="",
    page=None,
    bbox=None,
    source=SOURCE_UNKNOWN,
    parser_name="",
    confidence=0.0,
    metadata=None,
):
    metadata_payload = dict(metadata or {})
    raw_field = normalize_raw_field_name(metadata_payload.get("raw_field") or field)
    mapping = canonical_field_mapping(raw_field, label=label, metadata=metadata_payload)
    metadata_payload.setdefault("raw_field", raw_field)
    metadata_payload["canonical_field"] = mapping.canonical_field
    metadata_payload["canonical_mapping_strength"] = mapping.strength
    metadata_payload["semantic_role"] = mapping.semantic_role
    if mapping.notes:
        metadata_payload["canonical_mapping_notes"] = mapping.notes
    for key, mapping_value in [
        ("id_type_hint", mapping.id_type_hint),
        ("stop_type_hint", mapping.stop_type_hint),
        ("party_role_hint", mapping.party_role_hint),
        ("money_context", mapping.money_context),
    ]:
        if mapping_value and not metadata_payload.get(key):
            metadata_payload[key] = mapping_value
    confidence_score = confidence_after_mapping(
        _confidence_score(confidence),
        mapping.strength,
    )
    return FieldCandidate(
        field=mapping.canonical_field,
        value=_text(value),
        normalized_value=_text(normalized_value) or _text(value),
        label=_text(label),
        evidence_text=_text(evidence_text),
        page=_page(page),
        bbox=bbox if isinstance(bbox, list) or bbox is None else None,
        source=_text(source) or SOURCE_UNKNOWN,
        parser_name=_text(parser_name),
        confidence=confidence_score,
        metadata=metadata_payload,
    ).to_dict()


def adapt_ratecon_candidate_to_field_candidate(
    candidate,
    parser_name="ratecon_candidate_extraction",
):
    candidate = candidate or {}
    value = _text(candidate.get("normalized_value") or candidate.get("raw_value"))
    evidence = _evidence_from_parts(
        label=candidate.get("label", ""),
        value=candidate.get("raw_value") or value,
        context_before=candidate.get("context_before", ""),
        context_after=candidate.get("context_after", ""),
    )
    metadata = preserve_load_candidate_provenance(
        candidate,
        parser_name=parser_name,
        metadata={
            "candidate_id": _text(candidate.get("candidate_id")),
            "value_type": _text(candidate.get("value_type")),
            "identifier_type": _text(candidate.get("identifier_type")),
            "confidence_reasons": list(candidate.get("confidence_reasons", []) or []),
            "warnings": list(candidate.get("warnings", []) or []),
            "original_source": _text(candidate.get("source")),
        },
    )
    return build_field_candidate(
        field=candidate.get("field_name", ""),
        value=candidate.get("raw_value") or value,
        normalized_value=value,
        label=candidate.get("label", ""),
        evidence_text=evidence,
        page=candidate.get("page_number", ""),
        bbox=(candidate.get("bbox") or {}).get("bbox") if isinstance(candidate.get("bbox"), dict) else candidate.get("bbox"),
        source=_source_from_candidate(candidate),
        parser_name=parser_name,
        confidence=candidate.get("confidence", ""),
        metadata=metadata,
    )


def adapt_candidate_result_to_field_candidates(
    candidate_result,
    parser_name="ratecon_candidate_extraction",
):
    return [
        adapt_ratecon_candidate_to_field_candidate(candidate, parser_name=parser_name)
        for candidate in (candidate_result or {}).get("candidates", []) or []
        if isinstance(candidate, dict)
    ]


def adapt_legacy_parser_output_to_field_candidates(
    parser_output,
    full_text="",
    parser_name="pasted_text_parser_adapter",
):
    parser_output = parser_output or {}
    confidence_by_field = parser_output.get("field_confidence", {}) or {}
    candidates = []
    for field_name, value in parser_output.items():
        if field_name in {"field_confidence", "special_requirements", "source_type", "source_file_name"}:
            continue
        if value in ["", None, {}, []]:
            continue
        canonical = _canonical_field(field_name)
        evidence = _find_evidence_line(full_text, value) or _evidence_from_parts(
            label=field_name,
            value=value,
        )
        candidates.append(
            build_field_candidate(
                field=canonical,
                value=value,
                normalized_value=value,
                label=field_name,
                evidence_text=evidence,
                source=SOURCE_LEGACY_PARSER,
                parser_name=parser_name,
                confidence=confidence_by_field.get(field_name, "UNKNOWN"),
                metadata={"legacy_field": field_name},
            )
        )
    return candidates
