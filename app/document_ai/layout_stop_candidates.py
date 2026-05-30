"""Layout-aware stop candidate generation from synthetic layout artifacts."""

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
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_LOCATION,
    FIELD_DELIVERY_TIME,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    FIELD_PICKUP_TIME,
    FIELD_REFERENCE,
    FIELD_UNKNOWN,
    SOURCE_TABLE_PATTERN_FUTURE,
)

LAYOUT_STOP_EXTRACTOR_VERSION = "layout_stop_candidates_v1"

DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b")
TIME_PATTERN = re.compile(r"\b\d{1,2}:\d{2}(?:\s?[AP]M)?\b", re.IGNORECASE)

PICKUP_MARKERS = ("pickup", "pick", "pu", "shipper", "origin")
DELIVERY_MARKERS = ("delivery", "drop", "del", "so", "consignee", "destination")


def _text(value):
    return str(value or "").strip()


def _lower(value):
    return _text(value).lower()


def _page_role_text(page):
    return ",".join(str(role) for role in page.get("page_roles", []))


def _stop_type_from_text(text):
    lower = _lower(text)
    if any(marker == lower or f" {marker} " in f" {lower} " for marker in PICKUP_MARKERS):
        return "pickup"
    if any(marker == lower or f" {marker} " in f" {lower} " for marker in DELIVERY_MARKERS):
        return "delivery"
    if lower.startswith("pu"):
        return "pickup"
    if lower.startswith("so"):
        return "delivery"
    return ""


def _stop_type_from_section(section_role):
    if section_role == "PICKUP_SECTION":
        return "pickup"
    if section_role == "DELIVERY_SECTION":
        return "delivery"
    return ""


def _field_for_stop(stop_type, value_kind):
    fields = {
        ("pickup", "location"): FIELD_PICKUP_LOCATION,
        ("pickup", "date"): FIELD_PICKUP_DATE,
        ("pickup", "time"): FIELD_PICKUP_TIME,
        ("delivery", "location"): FIELD_DELIVERY_LOCATION,
        ("delivery", "date"): FIELD_DELIVERY_DATE,
        ("delivery", "time"): FIELD_DELIVERY_TIME,
    }
    return fields.get((stop_type, value_kind), "")


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
    confidence=CANDIDATE_CONFIDENCE_HIGH,
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
        reasons=[f"layout_stop_{value_type}"],
        evidence_ref=evidence_ref,
        source_field=field_name,
    )
    return build_field_candidate_from_layout_value(
        field_name=field_name,
        label_value_candidate=label_value,
        confidence=confidence,
        confidence_reasons=[f"layout_stop_{value_type}"],
        source=SOURCE_TABLE_PATTERN_FUTURE,
        value_type=value_type,
        warnings=warnings,
        section_role=section_role,
        page_role=page_role,
    )


def _headers_for_table(table):
    header_rows = set(table.get("header_rows") or [0])
    headers = {}
    for cell in table.get("cells", []):
        if int(cell.get("row_index") or 0) in header_rows:
            headers[int(cell.get("col_index") or 0)] = _lower(cell.get("text_redacted"))
    return headers


def _rows_for_table(table):
    rows = {}
    for cell in table.get("cells", []):
        row_index = int(cell.get("row_index") or 0)
        rows.setdefault(row_index, []).append(cell)
    return {row: sorted(cells, key=lambda cell: int(cell.get("col_index") or 0)) for row, cells in rows.items()}


def _kind_for_header(header):
    if any(text in header for text in ["type", "action"]):
        return "type"
    if any(text in header for text in ["location", "city", "state"]):
        return "location"
    if "date" in header or "appt" in header:
        return "date_time"
    if "time" in header or "appt" in header:
        return "time"
    if any(text in header for text in ["ref", "reference"]):
        return "reference"
    if any(text in header for text in ["seq", "stop"]):
        return "sequence"
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
    return "STOP_TABLE"


def _extract_date_time(value):
    date_match = DATE_PATTERN.search(value)
    time_match = TIME_PATTERN.search(value)
    return (
        date_match.group(0) if date_match else "",
        time_match.group(0) if time_match else "",
    )


def _table_stop_candidates(page, table):
    candidates = []
    page_number = int(page.get("page_number") or 0)
    page_role = _page_role_text(page)
    section_role = _table_section_role(page, table)
    headers = _headers_for_table(table)
    rows = _rows_for_table(table)

    for row_index, cells in rows.items():
        if row_index in set(table.get("header_rows") or [0]):
            continue

        by_kind = {}
        for cell in cells:
            kind = _kind_for_header(headers.get(int(cell.get("col_index") or 0), ""))
            if kind:
                by_kind[kind] = cell

        stop_type = _stop_type_from_text((by_kind.get("type") or {}).get("text_redacted", ""))
        confidence = CANDIDATE_CONFIDENCE_HIGH if stop_type else CANDIDATE_CONFIDENCE_LOW
        warnings = [] if stop_type else ["stop_type_ambiguous"]

        location_cell = by_kind.get("location")
        if location_cell:
            field = _field_for_stop(stop_type, "location") if stop_type else FIELD_UNKNOWN
            candidates.append(
                _candidate(
                    field,
                    location_cell.get("text_redacted", ""),
                    f"{stop_type or 'ambiguous'}_location",
                    location_cell.get("bbox", {}),
                    page_number,
                    build_layout_evidence_ref(
                        page_number=page_number,
                        bbox=location_cell.get("bbox", {}),
                        table_id=table.get("table_id", ""),
                        cell_ref=f"r{location_cell.get('row_index')}c{location_cell.get('col_index')}",
                        label=f"{stop_type or 'ambiguous'}_location",
                        evidence_type=EVIDENCE_TABLE_CELL,
                    ),
                    section_role,
                    page_role,
                    f"{stop_type or 'ambiguous'}_location",
                    confidence=confidence,
                    warnings=warnings,
                )
            )

        date_time_cell = by_kind.get("date_time") or by_kind.get("time")
        if date_time_cell and stop_type:
            date_value, time_value = _extract_date_time(date_time_cell.get("text_redacted", ""))
            if date_value:
                candidates.append(
                    _candidate(
                        _field_for_stop(stop_type, "date"),
                        date_value,
                        f"{stop_type}_date",
                        date_time_cell.get("bbox", {}),
                        page_number,
                        build_layout_evidence_ref(
                            page_number=page_number,
                            bbox=date_time_cell.get("bbox", {}),
                            table_id=table.get("table_id", ""),
                            cell_ref=f"r{date_time_cell.get('row_index')}c{date_time_cell.get('col_index')}",
                            label=f"{stop_type}_date",
                            evidence_type=EVIDENCE_TABLE_CELL,
                        ),
                        section_role,
                        page_role,
                        f"{stop_type}_date",
                        confidence=confidence,
                        warnings=warnings,
                    )
                )
            if time_value:
                candidates.append(
                    _candidate(
                        _field_for_stop(stop_type, "time"),
                        time_value,
                        f"{stop_type}_time",
                        date_time_cell.get("bbox", {}),
                        page_number,
                        build_layout_evidence_ref(
                            page_number=page_number,
                            bbox=date_time_cell.get("bbox", {}),
                            table_id=table.get("table_id", ""),
                            cell_ref=f"r{date_time_cell.get('row_index')}c{date_time_cell.get('col_index')}",
                            label=f"{stop_type}_time",
                            evidence_type=EVIDENCE_TABLE_CELL,
                        ),
                        section_role,
                        page_role,
                        f"{stop_type}_time",
                        confidence=confidence,
                        warnings=warnings,
                    )
                )

        reference_cell = by_kind.get("reference")
        if reference_cell:
            candidates.append(
                _candidate(
                    FIELD_REFERENCE,
                    reference_cell.get("text_redacted", ""),
                    "stop_reference",
                    reference_cell.get("bbox", {}),
                    page_number,
                    build_layout_evidence_ref(
                        page_number=page_number,
                        bbox=reference_cell.get("bbox", {}),
                        table_id=table.get("table_id", ""),
                        cell_ref=f"r{reference_cell.get('row_index')}c{reference_cell.get('col_index')}",
                        label="stop_reference",
                        evidence_type=EVIDENCE_TABLE_CELL,
                    ),
                    section_role,
                    page_role,
                    "stop_reference",
                    confidence=CANDIDATE_CONFIDENCE_MEDIUM,
                    warnings=[],
                )
            )

    return candidates


def _line_stop_candidates(page, line):
    section_role = line.get("section_role", "")
    stop_type = _stop_type_from_section(section_role)
    if not stop_type:
        return []

    text = _text(line.get("text_redacted"))
    lower = _lower(text)
    page_number = int(page.get("page_number") or 0)
    page_role = _page_role_text(page)
    candidates = []

    if "location:" in lower:
        value = text.split("Location:", 1)[1].strip()
        field = _field_for_stop(stop_type, "location")
        candidates.append(
            _candidate(
                field,
                value,
                f"{stop_type}_location",
                line.get("bbox", {}),
                page_number,
                build_layout_evidence_ref(
                    page_number=page_number,
                    bbox=line.get("bbox", {}),
                    line_id=line.get("line_id", ""),
                    label=f"{stop_type}_location",
                    evidence_type=EVIDENCE_LABEL_VALUE,
                ),
                section_role,
                page_role,
                f"{stop_type}_location",
            )
        )

    date_value, time_value = _extract_date_time(text)
    if date_value:
        candidates.append(
            _candidate(
                _field_for_stop(stop_type, "date"),
                date_value,
                f"{stop_type}_date",
                line.get("bbox", {}),
                page_number,
                build_layout_evidence_ref(
                    page_number=page_number,
                    bbox=line.get("bbox", {}),
                    line_id=line.get("line_id", ""),
                    label=f"{stop_type}_date",
                    evidence_type=EVIDENCE_LABEL_VALUE,
                ),
                section_role,
                page_role,
                f"{stop_type}_date",
            )
        )
    if time_value:
        candidates.append(
            _candidate(
                _field_for_stop(stop_type, "time"),
                time_value,
                f"{stop_type}_time",
                line.get("bbox", {}),
                page_number,
                build_layout_evidence_ref(
                    page_number=page_number,
                    bbox=line.get("bbox", {}),
                    line_id=line.get("line_id", ""),
                    label=f"{stop_type}_time",
                    evidence_type=EVIDENCE_LABEL_VALUE,
                ),
                section_role,
                page_role,
                f"{stop_type}_time",
            )
        )

    return candidates


def generate_layout_stop_candidates(layout_artifact):
    candidates = []

    for page in layout_artifact.get("pages", []):
        for table in page.get("tables", []):
            candidates.extend(_table_stop_candidates(page, table))

        for line in page.get("lines", []):
            candidates.extend(_line_stop_candidates(page, line))

    return candidates
