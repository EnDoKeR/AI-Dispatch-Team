"""Collect redacted template patterns from private text in memory only."""

from app.document_ai.private_measurement import EXTRACTION_STATUS_EMPTY_TEXT
from app.document_ai.private_measurement_pipeline import _extract_text_in_memory
from app.document_ai.private_template_patterns import (
    TOKEN_CITY_STATE,
    TOKEN_COMPANY_LIKE,
    TOKEN_DATE,
    TOKEN_MC_NUMBER,
    TOKEN_MONEY,
    TOKEN_REFERENCE,
    TOKEN_TIME,
    TOKEN_WEIGHT,
    build_redacted_line_pattern,
    build_redacted_template_pattern_summary,
)
from app.document_ai.private_template_redaction import redact_line_for_pattern_collection


RATE_MARKERS = ["rate", "pay", "linehaul", "amount", "charge"]
STOP_MARKERS = ["pickup", "delivery", "shipper", "consignee", "origin", "destination", "stop"]
REFERENCE_MARKERS = ["load", "order", "shipment", "po", "bol", "reference", "pickup #", "delivery #"]
EQUIPMENT_WEIGHT_MARKERS = ["equipment", "trailer", "weight", "commodity", "product"]
TERMS_MARKERS = ["detention", "layover", "tonu", "quick pay", "fee", "terms", "accessorial"]
HEADER_MARKERS = ["rate confirmation", "confirmation", "broker", "carrier"]


def _line_bucket(index, total):
    if total <= 3:
        return "beginning"
    ratio = index / max(total, 1)
    if ratio <= 0.25:
        return "beginning"
    if ratio >= 0.75:
        return "end"
    return "middle"


def _contains_any(text, markers):
    normalized = str(text or "").lower()
    return any(marker in normalized for marker in markers)


def _token_types(redacted_line):
    tokens = []
    mapping = {
        "<MONEY>": TOKEN_MONEY,
        "<DATE>": TOKEN_DATE,
        "<TIME>": TOKEN_TIME,
        "<MC>": TOKEN_MC_NUMBER,
        "<REF>": TOKEN_REFERENCE,
        "<CITY_STATE_OR_LOCATION>": TOKEN_CITY_STATE,
        "<COMPANY>": TOKEN_COMPANY_LIKE,
        "<WEIGHT>": TOKEN_WEIGHT,
    }
    for placeholder, token_type in mapping.items():
        if placeholder in redacted_line:
            tokens.append(token_type)
    return tokens


def _redacted_patterns_from_text(text, page_number=1):
    raw_lines = [
        line.strip()
        for line in str(text or "").splitlines()
        if line.strip()
    ]
    patterns = []
    for index, line in enumerate(raw_lines, start=1):
        redacted_line = redact_line_for_pattern_collection(line)
        patterns.append(
            build_redacted_line_pattern(
                page_number=page_number,
                line_index_bucket=_line_bucket(index, len(raw_lines)),
                redacted_line=redacted_line,
                token_types=_token_types(redacted_line),
                looks_like_header=_contains_any(redacted_line, HEADER_MARKERS),
                looks_like_rate_section=_contains_any(redacted_line, RATE_MARKERS),
                looks_like_stop_section=_contains_any(redacted_line, STOP_MARKERS),
                looks_like_terms_section=_contains_any(redacted_line, TERMS_MARKERS),
            )
        )
    return patterns


def _section_markers(patterns):
    markers = []
    for pattern in patterns:
        if pattern.get("looks_like_rate_section"):
            markers.append("rate")
        if pattern.get("looks_like_stop_section"):
            markers.append("stop")
        if pattern.get("looks_like_terms_section"):
            markers.append("terms")
        redacted = pattern.get("redacted_line", "").lower()
        if _contains_any(redacted, REFERENCE_MARKERS):
            markers.append("reference")
        if _contains_any(redacted, EQUIPMENT_WEIGHT_MARKERS):
            markers.append("equipment_weight")
    return sorted(set(markers))


def collect_redacted_template_patterns_from_text(
    text,
    document_alias,
    page_count=1,
    char_count=None,
    warning_codes=None,
):
    patterns = _redacted_patterns_from_text(text, page_number=1)
    warnings = list(warning_codes or [])
    if not str(text or "").strip():
        warnings.append("OCR_NEEDED")
        warnings.append("no_extractable_text")

    return build_redacted_template_pattern_summary(
        document_alias=document_alias,
        page_count=page_count,
        char_count=len(str(text or "")) if char_count is None else char_count,
        section_markers=_section_markers(patterns),
        redacted_header_patterns=[
            pattern for pattern in patterns if pattern.get("looks_like_header")
        ],
        redacted_rate_label_patterns=[
            pattern for pattern in patterns if pattern.get("looks_like_rate_section")
        ],
        redacted_stop_label_patterns=[
            pattern for pattern in patterns if pattern.get("looks_like_stop_section")
        ],
        redacted_reference_label_patterns=[
            pattern
            for pattern in patterns
            if _contains_any(pattern.get("redacted_line", ""), REFERENCE_MARKERS)
        ],
        redacted_equipment_weight_patterns=[
            pattern
            for pattern in patterns
            if _contains_any(pattern.get("redacted_line", ""), EQUIPMENT_WEIGHT_MARKERS)
        ],
        warning_codes=warnings,
    )


def collect_redacted_template_patterns_from_text_artifact(artifact, document_alias=""):
    if isinstance(artifact, dict):
        full_text = artifact.get("full_text", "")
        if not full_text:
            full_text = "\n".join(
                str(page.get("text", "") or "")
                for page in artifact.get("pages", [])
                if isinstance(page, dict)
            )
        return collect_redacted_template_patterns_from_text(
            full_text,
            document_alias=document_alias or artifact.get("document_id", ""),
            page_count=artifact.get("page_count", 1),
            char_count=artifact.get("char_count", len(full_text)),
            warning_codes=artifact.get("warnings", []),
        )

    full_text = str(getattr(artifact, "full_text", "") or "")
    return collect_redacted_template_patterns_from_text(
        full_text,
        document_alias=document_alias or str(getattr(artifact, "document_id", "") or ""),
        page_count=getattr(artifact, "page_count", 1),
        char_count=getattr(artifact, "char_count", len(full_text)),
        warning_codes=getattr(artifact, "warnings", []),
    )


def collect_redacted_template_patterns_from_pdf(pdf_path, document_alias):
    extraction = _extract_text_in_memory(pdf_path)
    text = extraction.get("text", "")
    warnings = list(extraction.get("warnings", []))
    if extraction.get("extraction_status") == EXTRACTION_STATUS_EMPTY_TEXT:
        warnings.append("OCR_NEEDED")

    return collect_redacted_template_patterns_from_text(
        text,
        document_alias=document_alias,
        page_count=extraction.get("page_count", 0),
        char_count=extraction.get("char_count", 0),
        warning_codes=warnings,
    )
