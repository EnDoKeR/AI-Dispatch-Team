"""Layout-aware operational detail candidate generation."""

import re

from app.document_ai.layout_artifacts import (
    EVIDENCE_LABEL_VALUE,
    EVIDENCE_TABLE_CELL,
    build_layout_evidence_ref,
)
from app.document_ai.layout_candidate_adapter import build_field_candidate_from_layout_value
from app.document_ai.layout_proximity import (
    PROXIMITY_SAME_ROW_RIGHT,
    PROXIMITY_TABLE_ROW,
    build_label_value_candidate,
)
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_MEDIUM,
    FIELD_COMMODITY,
    FIELD_EQUIPMENT,
    FIELD_SPECIAL_REQUIREMENT,
    FIELD_WEIGHT,
    SOURCE_TABLE_PATTERN_FUTURE,
)

LAYOUT_OPERATIONAL_EXTRACTOR_VERSION = "layout_operational_candidates_v1"

EQUIPMENT_PATTERN = re.compile(
    r"\b(?P<equipment>reefer|dry\s+van|van\s+53\s*ft|53\s*ft\s+van|flatbed|conestoga|step\s*deck|power only)\b",
    re.IGNORECASE,
)
WEIGHT_PATTERN = re.compile(r"\b(?P<weight>\d{4,6}|(?:\d{1,3},)+\d{3})\s*(?P<unit>lbs?|pounds)?\b", re.IGNORECASE)
DIMENSION_PATTERN = re.compile(r"\b(?P<dimensions>\d{1,3}\s*(?:ft|feet|in|inch|x)\s*[xX]?\s*\d{0,3}\s*(?:ft|feet|in|inch)?)\b")

REQUIREMENT_PATTERNS = (
    ("tarp required", "tarp_required"),
    ("straps required", "straps_required"),
    ("chains required", "chains_required"),
    ("conestoga required", "conestoga_required"),
    ("tracking required", "tracking_required"),
    ("driver assist", "driver_assist"),
    ("no touch", "no_touch"),
    ("appointment required", "appointment_required"),
)

HIGH_CONTEXT_SECTIONS = {"EQUIPMENT_SUMMARY", "COMMODITY_WEIGHT", "SPECIAL_INSTRUCTIONS"}
LOW_CONTEXT_SECTIONS = {"LEGAL_TERMS", "PAYMENT_TERMS", "BILLING_INSTRUCTIONS"}


def _text(value):
    return str(value or "").strip()


def _lower(value):
    return _text(value).lower()


def _page_role_text(page):
    return ",".join(str(role) for role in page.get("page_roles", []))


def _confidence_for_section(section_role):
    if section_role in HIGH_CONTEXT_SECTIONS:
        return CANDIDATE_CONFIDENCE_HIGH
    if section_role in LOW_CONTEXT_SECTIONS:
        return CANDIDATE_CONFIDENCE_LOW
    return CANDIDATE_CONFIDENCE_MEDIUM


def _warnings_for_section(section_role):
    if section_role in LOW_CONTEXT_SECTIONS:
        return ["requirement_from_supplemental_terms"]
    return []


def _normalize_weight(value):
    return _text(value).replace(",", "")


def _candidate(
    field_name,
    value,
    label,
    bbox,
    page_number,
    evidence_ref,
    section_role,
    page_role,
    value_type,
    confidence,
    warnings=None,
):
    label_value = build_label_value_candidate(
        label=label,
        value_text_redacted=value,
        label_bbox=bbox,
        value_bbox=bbox,
        page_number=page_number,
        proximity_type=PROXIMITY_TABLE_ROW if evidence_ref.get("table_id") else PROXIMITY_SAME_ROW_RIGHT,
        distance_score=0.88 if confidence == CANDIDATE_CONFIDENCE_HIGH else 0.55,
        confidence=confidence,
        reasons=[f"layout_operational_{value_type}"],
        evidence_ref=evidence_ref,
        source_field=field_name,
    )
    normalized = _normalize_weight(value) if field_name == FIELD_WEIGHT else value
    return build_field_candidate_from_layout_value(
        field_name=field_name,
        label_value_candidate=label_value,
        normalized_value=normalized,
        confidence=confidence,
        confidence_reasons=[f"layout_operational_{value_type}"],
        source=SOURCE_TABLE_PATTERN_FUTURE,
        value_type=value_type,
        warnings=warnings,
        section_role=section_role,
        page_role=page_role,
    )


def _line_label_value(text, label):
    lower = _lower(text)
    lower_label = label.lower()
    index = lower.find(lower_label)
    if index < 0:
        return ""
    value = text[index + len(label):].strip()
    if value.startswith(":"):
        value = value[1:].strip()
    return value


def _line_candidates(page, line):
    text = _text(line.get("text_redacted"))
    lower = _lower(text)
    section_role = line.get("section_role", "")
    page_number = int(page.get("page_number") or 0)
    page_role = _page_role_text(page)
    confidence = _confidence_for_section(section_role)
    warnings = _warnings_for_section(section_role)
    evidence_ref = build_layout_evidence_ref(
        page_number=page_number,
        bbox=line.get("bbox", {}),
        line_id=line.get("line_id", ""),
        evidence_type=EVIDENCE_LABEL_VALUE,
    )
    candidates = []

    if "equipment" in lower:
        equipment_match = EQUIPMENT_PATTERN.search(text)
        if equipment_match:
            candidates.append(
                _candidate(
                    FIELD_EQUIPMENT,
                    equipment_match.group("equipment"),
                    "equipment",
                    line.get("bbox", {}),
                    page_number,
                    evidence_ref,
                    section_role,
                    page_role,
                    "equipment",
                    confidence,
                    warnings=warnings,
                )
            )

    if "weight" in lower:
        after_label = _line_label_value(text, "Weight")
        weight_match = WEIGHT_PATTERN.search(after_label or text)
        if weight_match:
            candidates.append(
                _candidate(
                    FIELD_WEIGHT,
                    weight_match.group("weight"),
                    "weight",
                    line.get("bbox", {}),
                    page_number,
                    evidence_ref,
                    section_role,
                    page_role,
                    "weight",
                    confidence,
                    warnings=warnings,
                )
            )

    if "commodity" in lower:
        value = _line_label_value(text, "Commodity")
        if value:
            value = value.split("Weight:", 1)[0].strip()
            candidates.append(
                _candidate(
                    FIELD_COMMODITY,
                    value,
                    "commodity",
                    line.get("bbox", {}),
                    page_number,
                    evidence_ref,
                    section_role,
                    page_role,
                    "commodity",
                    confidence,
                    warnings=warnings,
                )
            )

    dimension_match = DIMENSION_PATTERN.search(text)
    if dimension_match and "dimension" in lower:
        candidates.append(
            _candidate(
                FIELD_SPECIAL_REQUIREMENT,
                dimension_match.group("dimensions"),
                "dimensions",
                line.get("bbox", {}),
                page_number,
                evidence_ref,
                section_role,
                page_role,
                "dimensions",
                confidence,
                warnings=warnings,
            )
        )

    for phrase, value_type in REQUIREMENT_PATTERNS:
        if phrase in lower:
            candidates.append(
                _candidate(
                    FIELD_SPECIAL_REQUIREMENT,
                    phrase,
                    phrase,
                    line.get("bbox", {}),
                    page_number,
                    evidence_ref,
                    section_role,
                    page_role,
                    value_type,
                    confidence,
                    warnings=warnings,
                )
            )

    return candidates


def _headers_for_table(table):
    headers = {}
    for cell in table.get("cells", []):
        if int(cell.get("row_index") or 0) in set(table.get("header_rows") or [0]):
            headers[int(cell.get("col_index") or 0)] = _lower(cell.get("text_redacted"))
    return headers


def _kind_for_header(header):
    if "equipment" in header or "trailer" in header:
        return FIELD_EQUIPMENT
    if "weight" in header:
        return FIELD_WEIGHT
    if "commodity" in header or "product" in header:
        return FIELD_COMMODITY
    return ""


def _table_section_role(page, table):
    table_box = table.get("bbox", {})
    for block in page.get("blocks", []):
        block_box = block.get("bbox", {})
        if (
            abs(float(block_box.get("x0", 0)) - float(table_box.get("x0", 0))) <= 1
            and abs(float(block_box.get("y0", 0)) - float(table_box.get("y0", 0))) <= 1
            and block.get("section_role")
        ):
            return block["section_role"]
    return ""


def _table_candidates(page, table):
    page_number = int(page.get("page_number") or 0)
    page_role = _page_role_text(page)
    section_role = _table_section_role(page, table) or "COMMODITY_WEIGHT"
    confidence = _confidence_for_section(section_role)
    warnings = _warnings_for_section(section_role)
    headers = _headers_for_table(table)
    candidates = []

    for cell in table.get("cells", []):
        row_index = int(cell.get("row_index") or 0)
        if row_index in set(table.get("header_rows") or [0]):
            continue
        field_name = _kind_for_header(headers.get(int(cell.get("col_index") or 0), ""))
        if not field_name:
            continue
        value = _text(cell.get("text_redacted"))
        if not value:
            continue
        candidates.append(
            _candidate(
                field_name,
                value,
                field_name,
                cell.get("bbox", {}),
                page_number,
                build_layout_evidence_ref(
                    page_number=page_number,
                    bbox=cell.get("bbox", {}),
                    table_id=table.get("table_id", ""),
                    cell_ref=f"r{cell.get('row_index')}c{cell.get('col_index')}",
                    label=field_name,
                    evidence_type=EVIDENCE_TABLE_CELL,
                ),
                section_role,
                page_role,
                field_name,
                confidence,
                warnings=warnings,
            )
        )

    return candidates


def generate_layout_operational_candidates(layout_artifact):
    candidates = []

    for page in layout_artifact.get("pages", []):
        for line in page.get("lines", []):
            candidates.extend(_line_candidates(page, line))
        for table in page.get("tables", []):
            candidates.extend(_table_candidates(page, table))

    return candidates
