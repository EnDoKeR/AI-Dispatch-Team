"""Layout-aware stop association contracts and helpers."""

import re

from app.document_ai.ratecon_candidates import normalize_list


STOP_ASSOCIATION_SOURCE_TABLE_ROW = "table_row"
STOP_ASSOCIATION_SOURCE_SECTION_BLOCK = "section_block"
STOP_ASSOCIATION_SOURCE_LABEL_VALUE = "label_value"
STOP_ASSOCIATION_SOURCE_TEXT_REGEX = "text_regex"
STOP_ASSOCIATION_SOURCE_TEMPLATE_RULE = "template_rule"
STOP_ASSOCIATION_SOURCE_UNKNOWN = "unknown"

STOP_ASSOCIATION_SOURCES = {
    STOP_ASSOCIATION_SOURCE_TABLE_ROW,
    STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
    STOP_ASSOCIATION_SOURCE_LABEL_VALUE,
    STOP_ASSOCIATION_SOURCE_TEXT_REGEX,
    STOP_ASSOCIATION_SOURCE_TEMPLATE_RULE,
    STOP_ASSOCIATION_SOURCE_UNKNOWN,
}

STOP_TYPE_PICKUP = "pickup"
STOP_TYPE_DELIVERY = "delivery"
STOP_TYPE_STOP = "stop"
STOP_TYPE_UNKNOWN = "unknown"

STOP_TYPES = {
    STOP_TYPE_PICKUP,
    STOP_TYPE_DELIVERY,
    STOP_TYPE_STOP,
    STOP_TYPE_UNKNOWN,
}

STOP_FIELD_LOCATION = "location"
STOP_FIELD_DATE = "date"
STOP_FIELD_TIME = "time"
STOP_FIELD_REFERENCE = "reference"
STOP_FIELD_NOTES = "notes"
STOP_FIELD_FACILITY_NAME = "facility_name"
STOP_FIELD_ADDRESS = "address"
STOP_FIELD_CONTACT = "contact"

STOP_FIELD_NAMES = {
    STOP_FIELD_LOCATION,
    STOP_FIELD_DATE,
    STOP_FIELD_TIME,
    STOP_FIELD_REFERENCE,
    STOP_FIELD_NOTES,
    STOP_FIELD_FACILITY_NAME,
    STOP_FIELD_ADDRESS,
    STOP_FIELD_CONTACT,
}

STOP_ASSOCIATION_VERSION = "stop_association_v1"


def _text(value):
    return str(value or "").strip()


def _normalize_source(value):
    text = _text(value).lower().replace(" ", "_").replace("-", "_")
    return text if text in STOP_ASSOCIATION_SOURCES else STOP_ASSOCIATION_SOURCE_UNKNOWN


def _normalize_stop_type(value):
    text = _text(value).lower().replace(" ", "_").replace("-", "_")
    return text if text in STOP_TYPES else STOP_TYPE_UNKNOWN


def _normalize_field_name(value):
    text = _text(value).lower().replace(" ", "_").replace("-", "_")
    return text if text in STOP_FIELD_NAMES else STOP_FIELD_NOTES


def build_stop_field_candidate(
    stop_group_id="",
    stop_sequence=None,
    stop_type=STOP_TYPE_UNKNOWN,
    field_name=STOP_FIELD_NOTES,
    candidate_id="",
    confidence=0.0,
    evidence_ref=None,
    source=STOP_ASSOCIATION_SOURCE_UNKNOWN,
    reasons=None,
    warning_codes=None,
):
    return {
        "stop_group_id": _text(stop_group_id),
        "stop_sequence": stop_sequence if stop_sequence not in [None, ""] else "",
        "stop_type": _normalize_stop_type(stop_type),
        "field_name": _normalize_field_name(field_name),
        "candidate_id": _text(candidate_id),
        "confidence": float(confidence or 0.0),
        "evidence_ref": evidence_ref if isinstance(evidence_ref, dict) else {},
        "source": _normalize_source(source),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
    }


def build_stop_group_candidate(
    stop_group_id="",
    stop_sequence=None,
    stop_type=STOP_TYPE_UNKNOWN,
    source=STOP_ASSOCIATION_SOURCE_UNKNOWN,
    page_number="",
    section_role="",
    table_id="",
    row_index=None,
    field_candidates=None,
    confidence=0.0,
    reasons=None,
    warning_codes=None,
):
    return {
        "stop_group_id": _text(stop_group_id),
        "stop_sequence": stop_sequence if stop_sequence not in [None, ""] else "",
        "stop_type": _normalize_stop_type(stop_type),
        "source": _normalize_source(source),
        "page_number": page_number if page_number not in [None, ""] else "",
        "section_role": _text(section_role),
        "table_id": _text(table_id),
        "row_index": row_index if row_index not in [None, ""] else "",
        "field_candidates": [
            candidate for candidate in field_candidates or [] if isinstance(candidate, dict)
        ],
        "confidence": float(confidence or 0.0),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
    }


def build_stop_association_result(
    stop_groups=None,
    unresolved_stop_fields=None,
    conflict_stop_fields=None,
    warning_codes=None,
):
    return {
        "stop_groups": [group for group in stop_groups or [] if isinstance(group, dict)],
        "unresolved_stop_fields": normalize_list(unresolved_stop_fields),
        "conflict_stop_fields": normalize_list(conflict_stop_fields),
        "warning_codes": normalize_list(warning_codes),
        "association_version": STOP_ASSOCIATION_VERSION,
    }


def _cell_text(cell):
    return _text((cell or {}).get("text_redacted")).lower()


def _cell_ref(cell):
    return f"r{int((cell or {}).get('row_index', 0))}c{int((cell or {}).get('col_index', 0))}"


def _rows_by_index(table):
    rows = {}
    for cell in (table or {}).get("cells", []) or []:
        if not isinstance(cell, dict):
            continue
        rows.setdefault(int(cell.get("row_index", 0) or 0), {})[
            int(cell.get("col_index", 0) or 0)
        ] = cell
    return rows


def _sequence_from_text(value):
    digits = "".join(char for char in _text(value) if char.isdigit())
    return int(digits) if digits else ""


def _column_kind(header_text):
    text = _text(header_text).lower()
    if any(token in text for token in ["stop", "seq", "#", "number"]):
        return "sequence"
    if any(token in text for token in ["type", "activity", "event"]):
        return "type"
    if any(token in text for token in ["location", "city", "state", "address", "shipper", "consignee"]):
        return STOP_FIELD_LOCATION
    if "date" in text:
        return STOP_FIELD_DATE
    if any(token in text for token in ["time", "appt", "appointment"]):
        return STOP_FIELD_TIME
    if any(token in text for token in ["ref", "reference", "po", "pickup #", "delivery #"]):
        return STOP_FIELD_REFERENCE
    return ""


def detect_stop_table_columns(table):
    """Return a column index -> semantic kind map for a likely stop table."""

    rows = _rows_by_index(table)
    header_rows = set((table or {}).get("header_rows") or [0])
    header_index = min(header_rows) if header_rows else 0
    header = rows.get(header_index, {})
    columns = {
        col_index: _column_kind(cell.get("text_redacted", ""))
        for col_index, cell in header.items()
    }
    return {col_index: kind for col_index, kind in columns.items() if kind}


def classify_stop_row(row, columns):
    type_text = " ".join(
        _cell_text(row.get(col_index))
        for col_index, kind in columns.items()
        if kind == "type"
    )
    location_text = " ".join(
        _cell_text(row.get(col_index))
        for col_index, kind in columns.items()
        if kind == STOP_FIELD_LOCATION
    )
    combined = f"{type_text} {location_text}"
    warnings = []

    if any(token in combined for token in ["pickup", "pick", "pu", "shipper", "origin"]):
        stop_type = STOP_TYPE_PICKUP
        confidence = 0.9
    elif any(token in combined for token in ["delivery", "deliver", "drop", "del", "so", "consignee", "destination"]):
        stop_type = STOP_TYPE_DELIVERY
        confidence = 0.9
    else:
        stop_type = STOP_TYPE_STOP
        confidence = 0.55
        warnings.append("ambiguous_stop_type")

    sequence = ""
    for col_index, kind in columns.items():
        if kind == "sequence" and row.get(col_index):
            sequence = _sequence_from_text(row[col_index].get("text_redacted", ""))
            break

    return {
        "stop_type": stop_type,
        "stop_sequence": sequence,
        "confidence": confidence,
        "warning_codes": warnings,
    }


def build_stop_field_candidates_from_row(row, columns, table, stop_group_id, stop_type, stop_sequence):
    field_candidates = []
    table_id = _text((table or {}).get("table_id"))
    page_number = int((table or {}).get("page_number", 0) or 0)
    for col_index, kind in sorted(columns.items()):
        if kind not in {STOP_FIELD_LOCATION, STOP_FIELD_DATE, STOP_FIELD_TIME, STOP_FIELD_REFERENCE}:
            continue
        cell = row.get(col_index)
        if not cell or not _text(cell.get("text_redacted")):
            continue
        field_candidates.append(
            build_stop_field_candidate(
                stop_group_id=stop_group_id,
                stop_sequence=stop_sequence,
                stop_type=stop_type,
                field_name=kind,
                candidate_id=f"{table_id}_{_cell_ref(cell)}_{kind}",
                confidence=0.9,
                evidence_ref={
                    "page_number": page_number,
                    "table_id": table_id,
                    "cell_ref": _cell_ref(cell),
                    "evidence_type": "table_cell",
                },
                source=STOP_ASSOCIATION_SOURCE_TABLE_ROW,
                reasons=["same_table_row_stop_association"],
            )
        )
    return field_candidates


def build_stop_groups_from_layout_tables(layout_artifact, classification_result=None):
    """Build stop groups from table rows without making final field decisions."""

    del classification_result
    stop_groups = []
    warnings = []
    for page in (layout_artifact or {}).get("pages", []) or []:
        for table in page.get("tables", []) or []:
            columns = detect_stop_table_columns(table)
            if len(set(columns.values()) & {STOP_FIELD_LOCATION, STOP_FIELD_DATE, STOP_FIELD_TIME}) < 1:
                continue
            if "type" not in set(columns.values()) and "sequence" not in set(columns.values()):
                continue

            rows = _rows_by_index(table)
            header_rows = set(table.get("header_rows") or [0])
            for row_index in sorted(rows):
                if row_index in header_rows:
                    continue
                row = rows[row_index]
                row_classification = classify_stop_row(row, columns)
                table_id = _text(table.get("table_id"))
                sequence = row_classification["stop_sequence"] or len(stop_groups) + 1
                stop_group_id = f"{table_id}_row_{row_index}"
                field_candidates = build_stop_field_candidates_from_row(
                    row=row,
                    columns=columns,
                    table=table,
                    stop_group_id=stop_group_id,
                    stop_type=row_classification["stop_type"],
                    stop_sequence=sequence,
                )
                if not field_candidates:
                    continue
                group_warnings = list(row_classification["warning_codes"])
                warnings.extend(group_warnings)
                stop_groups.append(
                    build_stop_group_candidate(
                        stop_group_id=stop_group_id,
                        stop_sequence=sequence,
                        stop_type=row_classification["stop_type"],
                        source=STOP_ASSOCIATION_SOURCE_TABLE_ROW,
                        page_number=table.get("page_number", page.get("page_number", "")),
                        table_id=table_id,
                        row_index=row_index,
                        field_candidates=field_candidates,
                        confidence=row_classification["confidence"],
                        reasons=["layout_table_row_preserves_stop_field_association"],
                        warning_codes=group_warnings,
                    )
                )

    return build_stop_association_result(
        stop_groups=stop_groups,
        warning_codes=sorted(set(warnings)),
    )


_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_TIME_RE = re.compile(r"\b\d{1,2}:\d{2}(?:\s?(?:am|pm))?\b", re.IGNORECASE)

_STOP_SECTION_ROLES = {
    "PICKUP_SECTION",
    "DELIVERY_SECTION",
    "MULTI_STOP_SECTION",
    "STOP_TABLE",
}

_IGNORED_STOP_SECTION_ROLES = {
    "LEGAL_TERMS",
    "PAYMENT_TERMS",
    "BILLING_INSTRUCTIONS",
    "QUICK_PAY",
    "SIGNATURE_BLOCK",
    "CERTIFICATE_SIGNATURE_BLOCK",
}


def _line_lookup(page):
    return {
        _text(line.get("line_id")): line
        for line in page.get("lines", []) or []
        if isinstance(line, dict) and _text(line.get("line_id"))
    }


def _block_text(block, page):
    lines = _line_lookup(page)
    texts = [_text(block.get("text_redacted"))]
    for line_id in block.get("line_ids", []) or []:
        if line_id in lines:
            texts.append(_text(lines[line_id].get("text_redacted")))
    return " ".join(text for text in texts if text)


def classify_stop_section(block_or_section):
    section_role = _text((block_or_section or {}).get("section_role")).upper()
    text = _text((block_or_section or {}).get("text_redacted")).lower()
    combined = f"{section_role.lower()} {text}"
    warnings = []

    if section_role in _IGNORED_STOP_SECTION_ROLES:
        return {
            "stop_type": STOP_TYPE_UNKNOWN,
            "confidence": 0.0,
            "warning_codes": ["ignored_non_core_stop_section"],
            "ignored": True,
        }
    if section_role == "PICKUP_SECTION" or any(
        token in combined for token in ["pickup", "pick up", " pu ", "shipper", "origin"]
    ):
        return {
            "stop_type": STOP_TYPE_PICKUP,
            "confidence": 0.85,
            "warning_codes": [],
            "ignored": False,
        }
    if section_role == "DELIVERY_SECTION" or any(
        token in combined
        for token in ["delivery", "deliver", " drop ", " so ", "consignee", "destination"]
    ):
        return {
            "stop_type": STOP_TYPE_DELIVERY,
            "confidence": 0.85,
            "warning_codes": [],
            "ignored": False,
        }
    if section_role in {"MULTI_STOP_SECTION", "STOP_TABLE"} or "stop" in combined:
        return {
            "stop_type": STOP_TYPE_STOP,
            "confidence": 0.55,
            "warning_codes": ["ambiguous_stop_type"],
            "ignored": False,
        }
    return {
        "stop_type": STOP_TYPE_UNKNOWN,
        "confidence": 0.0,
        "warning_codes": ["not_a_stop_section"],
        "ignored": True,
    }


def associate_nearby_date_time_to_stop(section_text):
    text = _text(section_text)
    return {
        "has_date": bool(_DATE_RE.search(text)),
        "has_time": bool(_TIME_RE.search(text)),
    }


def collect_stop_fields_within_section(block, page, stop_group_id, stop_type, stop_sequence):
    section_text = _block_text(block, page)
    fields = []
    page_number = page.get("page_number", block.get("page_number", ""))
    evidence_base = {
        "page_number": page_number,
        "block_id": block.get("block_id", ""),
        "evidence_type": "section_context",
    }

    if section_text:
        fields.append(
            build_stop_field_candidate(
                stop_group_id=stop_group_id,
                stop_sequence=stop_sequence,
                stop_type=stop_type,
                field_name=STOP_FIELD_LOCATION,
                candidate_id=f"{stop_group_id}_location",
                confidence=0.75,
                evidence_ref=evidence_base,
                source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
                reasons=["stop_section_context_location_candidate"],
            )
        )

    nearby = associate_nearby_date_time_to_stop(section_text)
    if nearby["has_date"]:
        fields.append(
            build_stop_field_candidate(
                stop_group_id=stop_group_id,
                stop_sequence=stop_sequence,
                stop_type=stop_type,
                field_name=STOP_FIELD_DATE,
                candidate_id=f"{stop_group_id}_date",
                confidence=0.8,
                evidence_ref=evidence_base,
                source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
                reasons=["date_within_stop_section"],
            )
        )
    if nearby["has_time"]:
        fields.append(
            build_stop_field_candidate(
                stop_group_id=stop_group_id,
                stop_sequence=stop_sequence,
                stop_type=stop_type,
                field_name=STOP_FIELD_TIME,
                candidate_id=f"{stop_group_id}_time",
                confidence=0.8,
                evidence_ref=evidence_base,
                source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
                reasons=["time_within_stop_section"],
            )
        )
    if "ref" in section_text.lower() or "reference" in section_text.lower():
        fields.append(
            build_stop_field_candidate(
                stop_group_id=stop_group_id,
                stop_sequence=stop_sequence,
                stop_type=stop_type,
                field_name=STOP_FIELD_REFERENCE,
                candidate_id=f"{stop_group_id}_reference",
                confidence=0.65,
                evidence_ref=evidence_base,
                source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
                reasons=["reference_within_stop_section"],
            )
        )
    return fields


def build_stop_groups_from_layout_sections(layout_artifact, classification_result=None):
    """Build stop groups from pickup/delivery/multi-stop text sections."""

    del classification_result
    stop_groups = []
    warnings = []
    for page in (layout_artifact or {}).get("pages", []) or []:
        for block in page.get("blocks", []) or []:
            if not isinstance(block, dict):
                continue
            if _text(block.get("block_type")).lower() == "table":
                continue
            section_role = _text(block.get("section_role")).upper()
            if section_role not in _STOP_SECTION_ROLES and section_role not in _IGNORED_STOP_SECTION_ROLES:
                continue

            block_with_text = dict(block)
            block_with_text["text_redacted"] = _block_text(block, page)
            section_classification = classify_stop_section(block_with_text)
            if section_classification["ignored"]:
                warnings.extend(section_classification["warning_codes"])
                continue

            stop_sequence = len(stop_groups) + 1
            stop_group_id = _text(block.get("block_id")) or f"section_stop_{stop_sequence}"
            fields = collect_stop_fields_within_section(
                block=block,
                page=page,
                stop_group_id=stop_group_id,
                stop_type=section_classification["stop_type"],
                stop_sequence=stop_sequence,
            )
            if not fields:
                continue
            group_warnings = list(section_classification["warning_codes"])
            warnings.extend(group_warnings)
            stop_groups.append(
                build_stop_group_candidate(
                    stop_group_id=stop_group_id,
                    stop_sequence=stop_sequence,
                    stop_type=section_classification["stop_type"],
                    source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
                    page_number=page.get("page_number", block.get("page_number", "")),
                    section_role=section_role,
                    field_candidates=fields,
                    confidence=section_classification["confidence"],
                    reasons=["layout_section_preserves_stop_context"],
                    warning_codes=group_warnings,
                )
            )

    return build_stop_association_result(
        stop_groups=stop_groups,
        warning_codes=sorted(set(warnings)),
    )
