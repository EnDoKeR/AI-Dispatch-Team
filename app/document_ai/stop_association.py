"""Layout-aware stop association contracts and helpers."""

import re

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
    SOURCE_REGEX,
    normalize_confidence,
    normalize_list,
)
from app.document_ai.stop_group_provenance import (
    STOP_GROUP_SOURCE_TYPE_LINE_CLUSTER,
    STOP_GROUP_SOURCE_TYPE_SECTION_BLOCK,
    STOP_GROUP_SOURCE_TYPE_SINGLE_LINE,
    STOP_GROUP_SOURCE_TYPE_TABLE_ROW,
    TRIGGER_LABEL_DELIVERY,
    TRIGGER_LABEL_PICKUP,
    TRIGGER_LABEL_STOP,
    TRIGGER_LABEL_UNKNOWN,
    build_stop_group_provenance,
)


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

_TEXT_STOP_FIELD_MAP = {
    FIELD_PICKUP_LOCATION: (STOP_TYPE_PICKUP, STOP_FIELD_LOCATION),
    FIELD_PICKUP_DATE: (STOP_TYPE_PICKUP, STOP_FIELD_DATE),
    FIELD_PICKUP_TIME: (STOP_TYPE_PICKUP, STOP_FIELD_TIME),
    FIELD_DELIVERY_LOCATION: (STOP_TYPE_DELIVERY, STOP_FIELD_LOCATION),
    FIELD_DELIVERY_DATE: (STOP_TYPE_DELIVERY, STOP_FIELD_DATE),
    FIELD_DELIVERY_TIME: (STOP_TYPE_DELIVERY, STOP_FIELD_TIME),
}


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
    provenance=None,
):
    safe_fields = [
        candidate for candidate in field_candidates or [] if isinstance(candidate, dict)
    ]
    return {
        "stop_group_id": _text(stop_group_id),
        "stop_sequence": stop_sequence if stop_sequence not in [None, ""] else "",
        "stop_type": _normalize_stop_type(stop_type),
        "source": _normalize_source(source),
        "page_number": page_number if page_number not in [None, ""] else "",
        "section_role": _text(section_role),
        "table_id": _text(table_id),
        "row_index": row_index if row_index not in [None, ""] else "",
        "field_candidates": safe_fields,
        "confidence": float(confidence or 0.0),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
        "provenance": provenance if isinstance(provenance, dict) else {},
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


def _candidate_field_names(field_candidates):
    return [
        _text(candidate.get("field_name"))
        for candidate in field_candidates or []
        if isinstance(candidate, dict) and _text(candidate.get("field_name"))
    ]


def _candidate_field_name_set_from_group(group):
    return {
        _text(candidate.get("field_name"))
        for candidate in (group or {}).get("field_candidates", []) or []
        if isinstance(candidate, dict) and _text(candidate.get("field_name"))
    }


def _trigger_label_for_stop_type(stop_type):
    normalized = _normalize_stop_type(stop_type)
    if normalized == STOP_TYPE_PICKUP:
        return TRIGGER_LABEL_PICKUP
    if normalized == STOP_TYPE_DELIVERY:
        return TRIGGER_LABEL_DELIVERY
    if normalized == STOP_TYPE_STOP:
        return TRIGGER_LABEL_STOP
    return TRIGGER_LABEL_UNKNOWN


def _line_cluster_key(group):
    page_number = _text((group or {}).get("page_number"))
    section_role = _text((group or {}).get("section_role")).upper()
    stop_type = _normalize_stop_type((group or {}).get("stop_type"))
    if not page_number:
        return None
    if section_role:
        return (page_number, section_role, stop_type)
    if stop_type in {STOP_TYPE_PICKUP, STOP_TYPE_DELIVERY}:
        return (page_number, "UNSCOPED_STOP_LINES", stop_type)
    return None


def _line_provenance_value(group, key):
    provenance = (group or {}).get("provenance", {})
    if not isinstance(provenance, dict):
        return ""
    return _text(provenance.get(key))


def _merge_stop_types_for_line_cluster(groups):
    stop_types = {
        _normalize_stop_type(group.get("stop_type"))
        for group in groups or []
        if isinstance(group, dict)
    }
    if len(stop_types) == 1:
        return next(iter(stop_types))
    if STOP_TYPE_PICKUP in stop_types and STOP_TYPE_DELIVERY not in stop_types:
        return STOP_TYPE_PICKUP
    if STOP_TYPE_DELIVERY in stop_types and STOP_TYPE_PICKUP not in stop_types:
        return STOP_TYPE_DELIVERY
    if STOP_TYPE_STOP in stop_types:
        return STOP_TYPE_STOP
    return STOP_TYPE_UNKNOWN


def _build_line_cluster_group(groups, cluster_key):
    safe_groups = [group for group in groups or [] if isinstance(group, dict)]
    if len(safe_groups) <= 1:
        return safe_groups[0] if safe_groups else None

    first = dict(safe_groups[0])
    page_number, section_role, key_stop_type = cluster_key
    stop_type = _merge_stop_types_for_line_cluster(safe_groups) or key_stop_type
    field_candidates = []
    reasons = []
    warning_codes = []
    source_group_ids = []
    line_ids = []
    page_roles = []
    for group in safe_groups:
        field_candidates.extend(
            candidate
            for candidate in group.get("field_candidates", []) or []
            if isinstance(candidate, dict)
        )
        reasons.extend(normalize_list(group.get("reasons")))
        warning_codes.extend(normalize_list(group.get("warning_codes")))
        source_group_ids.append(_text(group.get("stop_group_id")))
        line_id = _line_provenance_value(group, "line_id")
        if line_id:
            line_ids.append(line_id)
        page_role = _line_provenance_value(group, "page_role")
        if page_role:
            page_roles.append(page_role)

    cluster_id = "line_cluster_{}_{}_{}_{}".format(
        page_number,
        section_role.lower() or "unscoped",
        stop_type,
        _text(first.get("stop_sequence")) or "1",
    )
    group_warnings = sorted(set(warning_codes + ["line_cluster_stop_groups_merged"]))
    first.update(
        {
            "stop_group_id": cluster_id,
            "stop_type": stop_type,
            "section_role": "" if section_role == "UNSCOPED_STOP_LINES" else section_role,
            "field_candidates": field_candidates,
            "reasons": sorted(set(reasons + ["line_cluster_preserves_stop_context"])),
            "warning_codes": group_warnings,
            "source_group_ids": [item for item in source_group_ids if item],
            "provenance": build_stop_group_provenance(
                source_type=STOP_GROUP_SOURCE_TYPE_LINE_CLUSTER,
                source_generator="build_stop_groups_from_layout_sections",
                page_number=page_number,
                line_id=",".join(line_ids),
                section_role="" if section_role == "UNSCOPED_STOP_LINES" else section_role,
                page_role=",".join(sorted(set(page_roles))),
                trigger_label_category=_trigger_label_for_stop_type(stop_type),
                candidate_field_names=_candidate_field_names(field_candidates),
                grouping_key="|".join(cluster_key),
                warning_codes=group_warnings,
            ),
        }
    )
    return first


def _cluster_line_stop_groups(line_groups):
    clusters = []
    active = {}
    active_order = []

    def flush_key(key):
        groups = active.pop(key, [])
        if key in active_order:
            active_order.remove(key)
        if not groups:
            return
        merged = _build_line_cluster_group(groups, key)
        if merged:
            clusters.append(merged)

    for group in line_groups or []:
        key = _line_cluster_key(group)
        if not key:
            clusters.append(group)
            continue

        fields = _candidate_field_name_set_from_group(group)
        current = active.get(key, [])
        current_has_location = any(
            STOP_FIELD_LOCATION in _candidate_field_name_set_from_group(item)
            for item in current
        )
        if current and STOP_FIELD_LOCATION in fields and current_has_location:
            flush_key(key)

        if key not in active:
            active[key] = []
            active_order.append(key)
        active[key].append(group)

    for key in list(active_order):
        flush_key(key)

    return clusters


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
    if "date" in text:
        return STOP_FIELD_DATE
    if any(token in text for token in ["time", "appt", "appointment"]):
        return STOP_FIELD_TIME
    if any(token in text for token in ["ref", "reference", "po", "pickup #", "delivery #"]):
        return STOP_FIELD_REFERENCE
    if any(token in text for token in ["stop", "seq", "#", "number"]):
        return "sequence"
    if any(token in text for token in ["type", "activity", "event"]):
        return "type"
    if any(
        token in text
        for token in [
            "location",
            "city",
            "state",
            "address",
            "shipper",
            "consignee",
            "pickup",
            "pick",
            "pu",
            "delivery",
            "deliver",
            "drop",
            "del",
            "so",
            "origin",
            "destination",
        ]
    ):
        return STOP_FIELD_LOCATION
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
    row_text = " ".join(_cell_text(cell) for cell in (row or {}).values())
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
    combined = f"{row_text} {type_text} {location_text}"
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
    seen_fields = set()

    def add_candidate(kind, cell, confidence=0.9, reasons=None):
        field_candidates.append(
            build_stop_field_candidate(
                stop_group_id=stop_group_id,
                stop_sequence=stop_sequence,
                stop_type=stop_type,
                field_name=kind,
                candidate_id=f"{table_id}_{_cell_ref(cell)}_{kind}",
                confidence=confidence,
                evidence_ref={
                    "page_number": page_number,
                    "table_id": table_id,
                    "cell_ref": _cell_ref(cell),
                    "evidence_type": "table_cell",
                },
                source=STOP_ASSOCIATION_SOURCE_TABLE_ROW,
                reasons=reasons or ["same_table_row_stop_association"],
            )
        )
        seen_fields.add(kind)

    for col_index, kind in sorted(columns.items()):
        if kind not in {STOP_FIELD_LOCATION, STOP_FIELD_DATE, STOP_FIELD_TIME, STOP_FIELD_REFERENCE}:
            continue
        cell = row.get(col_index)
        if not cell or not _text(cell.get("text_redacted")):
            continue
        add_candidate(kind, cell)
        signals = detect_stop_date_time_signals(cell.get("text_redacted", ""))
        if signals["has_date"] and kind != STOP_FIELD_DATE and STOP_FIELD_DATE not in seen_fields:
            add_candidate(STOP_FIELD_DATE, cell, confidence=0.82, reasons=["date_signal_in_stop_table_row"])
        if signals["has_time"] and kind != STOP_FIELD_TIME and STOP_FIELD_TIME not in seen_fields:
            add_candidate(STOP_FIELD_TIME, cell, confidence=0.82, reasons=["time_signal_in_stop_table_row"])

    for col_index, cell in sorted((row or {}).items()):
        if col_index in columns or not cell or not _text(cell.get("text_redacted")):
            continue
        signals = detect_stop_date_time_signals(cell.get("text_redacted", ""))
        if signals["has_date"] and STOP_FIELD_DATE not in seen_fields:
            add_candidate(STOP_FIELD_DATE, cell, confidence=0.72, reasons=["date_signal_in_unlabeled_stop_table_cell"])
        if signals["has_time"] and STOP_FIELD_TIME not in seen_fields:
            add_candidate(STOP_FIELD_TIME, cell, confidence=0.72, reasons=["time_signal_in_unlabeled_stop_table_cell"])
    return field_candidates


def build_stop_groups_from_layout_tables(layout_artifact, classification_result=None):
    """Build stop groups from table rows without making final field decisions."""

    del classification_result
    stop_groups = []
    warnings = []
    for page in (layout_artifact or {}).get("pages", []) or []:
        for table in page.get("tables", []) or []:
            columns = detect_stop_table_columns(table)
            rows = _rows_by_index(table)
            header_rows = set(table.get("header_rows") or [0])
            has_row_datetime_signal = any(
                (
                    detect_stop_date_time_signals(cell.get("text_redacted", "")).get("has_date")
                    or detect_stop_date_time_signals(cell.get("text_redacted", "")).get("has_time")
                )
                for row_index, row in rows.items()
                if row_index not in header_rows
                for cell in row.values()
                if isinstance(cell, dict)
            )
            stop_field_kinds = set(columns.values()) & {
                STOP_FIELD_LOCATION,
                STOP_FIELD_DATE,
                STOP_FIELD_TIME,
                STOP_FIELD_REFERENCE,
            }
            if len(stop_field_kinds) < 2 and not (
                STOP_FIELD_LOCATION in stop_field_kinds and has_row_datetime_signal
            ):
                continue

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
                if row_classification["stop_type"] == STOP_TYPE_STOP:
                    group_warnings = list(row_classification["warning_codes"])
                    group_warnings.append("provider_stop_table_row_type_ambiguous")
                else:
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
                        provenance=build_stop_group_provenance(
                            source_type=STOP_GROUP_SOURCE_TYPE_TABLE_ROW,
                            source_generator="build_stop_groups_from_layout_tables",
                            page_number=table.get("page_number", page.get("page_number", "")),
                            table_id=table_id,
                            row_index=row_index,
                            section_role=_text(table.get("section_role")) or "STOP_TABLE",
                            page_role=",".join(page.get("page_roles", []) or []),
                            trigger_label_category=_trigger_label_for_stop_type(
                                row_classification["stop_type"]
                            ),
                            candidate_field_names=_candidate_field_names(field_candidates),
                            grouping_key=f"{table.get('page_number', page.get('page_number', ''))}|{table_id}|{row_index}",
                            warning_codes=group_warnings,
                        ),
                    )
                )

    return build_stop_association_result(
        stop_groups=stop_groups,
        warning_codes=sorted(set(warnings)),
    )


_MONTH_NAMES = (
    "jan|january|feb|february|mar|march|apr|april|may|jun|june|"
    "jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december"
)
_DATE_RE = re.compile(
    rf"\b\d{{4}}[-/]\d{{1,2}}[-/]\d{{1,2}}\b"
    rf"|\b\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}\b"
    rf"|\b(?:{_MONTH_NAMES})\.?\s+\d{{1,2}},?\s+\d{{2,4}}\b",
    re.IGNORECASE,
)
_TIME_RE = re.compile(
    r"\b\d{1,2}:\d{2}(?:\s?(?:a\.?m\.?|p\.?m\.?|am|pm))?\b"
    r"|\b\d{1,2}:\d{2}\s?[-/]\s?\d{1,2}:\d{2}\b",
    re.IGNORECASE,
)
_APPOINTMENT_WINDOW_RE = re.compile(r"\b(?:fcfs|by\s+\d{1,2}:\d{2})\b", re.IGNORECASE)
_DATETIME_ONLY_WORD_RE = re.compile(
    r"\b(?:pickup|delivery|pu|so|date|time|appt|appointment|window|fcfs|by|at|from|to)\b",
    re.IGNORECASE,
)

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


def detect_stop_date_time_signals(section_text):
    text = _text(section_text)
    lowered = text.lower()
    return {
        "has_date": bool(_DATE_RE.search(text)) or "<date>" in lowered,
        "has_time": bool(_TIME_RE.search(text)) or "<time>" in lowered or bool(_APPOINTMENT_WINDOW_RE.search(text)),
        "has_appointment_window": "<time>" in lowered or bool(_APPOINTMENT_WINDOW_RE.search(text)),
    }


def associate_nearby_date_time_to_stop(section_text):
    return {
        key: value
        for key, value in detect_stop_date_time_signals(section_text).items()
        if key in {"has_date", "has_time"}
    }


def _looks_like_datetime_only_section_text(section_text):
    text = _DATE_RE.sub(" ", _text(section_text))
    text = _TIME_RE.sub(" ", text)
    text = text.replace("<DATE>", " ").replace("<TIME>", " ")
    text = _DATETIME_ONLY_WORD_RE.sub(" ", text)
    remaining = re.sub(r"[^A-Za-z]+", " ", text).strip()
    return not remaining


def collect_stop_fields_within_section(block, page, stop_group_id, stop_type, stop_sequence):
    section_text = _block_text(block, page)
    fields = []
    page_number = page.get("page_number", block.get("page_number", ""))
    evidence_base = {
        "page_number": page_number,
        "block_id": block.get("block_id", ""),
        "evidence_type": "section_context",
    }

    nearby = detect_stop_date_time_signals(section_text)
    if section_text and not _looks_like_datetime_only_section_text(section_text):
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
        grouped_line_ids = set()
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

            grouped_line_ids.update(_text(line_id) for line_id in block.get("line_ids", []) or [])
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
                    provenance=build_stop_group_provenance(
                        source_type=STOP_GROUP_SOURCE_TYPE_SECTION_BLOCK,
                        source_generator="build_stop_groups_from_layout_sections",
                        page_number=page.get("page_number", block.get("page_number", "")),
                        block_id=stop_group_id,
                        section_role=section_role,
                        page_role=",".join(page.get("page_roles", []) or []),
                        trigger_label_category=_trigger_label_for_stop_type(
                            section_classification["stop_type"]
                        ),
                        candidate_field_names=_candidate_field_names(fields),
                        grouping_key=f"{page.get('page_number', block.get('page_number', ''))}|{section_role}|{stop_group_id}",
                        warning_codes=group_warnings,
                    ),
                )
            )

        line_stop_groups = []
        for line in page.get("lines", []) or []:
            if not isinstance(line, dict):
                continue
            line_id = _text(line.get("line_id"))
            if line_id and line_id in grouped_line_ids:
                continue
            line_text = _text(line.get("text_redacted"))
            if not line_text:
                continue
            line_section = {
                "section_role": line.get("section_role", ""),
                "text_redacted": line_text,
            }
            section_classification = classify_stop_section(line_section)
            if section_classification["ignored"]:
                if "not_a_stop_section" not in section_classification["warning_codes"]:
                    warnings.extend(section_classification["warning_codes"])
                continue

            stop_sequence = len(stop_groups) + 1
            stop_group_id = line_id or f"line_stop_{stop_sequence}"
            pseudo_block = {
                "block_id": stop_group_id,
                "block_type": "text",
                "section_role": line.get("section_role", ""),
                "line_ids": [line_id] if line_id else [],
                "text_redacted": line_text,
            }
            fields = collect_stop_fields_within_section(
                block=pseudo_block,
                page=page,
                stop_group_id=stop_group_id,
                stop_type=section_classification["stop_type"],
                stop_sequence=stop_sequence,
            )
            if not fields:
                continue
            group_warnings = list(section_classification["warning_codes"])
            warnings.extend(group_warnings)
            line_stop_groups.append(
                build_stop_group_candidate(
                    stop_group_id=stop_group_id,
                    stop_sequence=stop_sequence,
                    stop_type=section_classification["stop_type"],
                    source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
                    page_number=page.get("page_number", line.get("page_number", "")),
                    section_role=_text(line.get("section_role")),
                    field_candidates=fields,
                    confidence=section_classification["confidence"],
                    reasons=["layout_line_preserves_stop_context"],
                    warning_codes=group_warnings,
                    provenance=build_stop_group_provenance(
                        source_type=STOP_GROUP_SOURCE_TYPE_SINGLE_LINE,
                        source_generator="build_stop_groups_from_layout_sections",
                        page_number=page.get("page_number", line.get("page_number", "")),
                        line_id=line_id,
                        section_role=_text(line.get("section_role")),
                        page_role=",".join(page.get("page_roles", []) or []),
                        trigger_label_category=_trigger_label_for_stop_type(
                            section_classification["stop_type"]
                        ),
                        candidate_field_names=_candidate_field_names(fields),
                        grouping_key=f"{page.get('page_number', line.get('page_number', ''))}|{_text(line.get('section_role'))}|{line_id}",
                        warning_codes=group_warnings,
                    ),
                )
            )
        stop_groups.extend(_cluster_line_stop_groups(line_stop_groups))

    return build_stop_association_result(
        stop_groups=stop_groups,
        warning_codes=sorted(set(warnings)),
    )


def _full_stop_field_name(stop_type, field_name):
    stop_type = _normalize_stop_type(stop_type)
    field_name = _normalize_field_name(field_name)
    if stop_type == STOP_TYPE_PICKUP and field_name in {
        STOP_FIELD_LOCATION,
        STOP_FIELD_DATE,
        STOP_FIELD_TIME,
    }:
        return f"pickup_{field_name}"
    if stop_type == STOP_TYPE_DELIVERY and field_name in {
        STOP_FIELD_LOCATION,
        STOP_FIELD_DATE,
        STOP_FIELD_TIME,
    }:
        return f"delivery_{field_name}"
    if field_name == STOP_FIELD_REFERENCE:
        return "stop_reference"
    return f"stop_{field_name}"


def _candidate_confidence_score(candidate):
    confidence = normalize_confidence((candidate or {}).get("confidence"))
    if confidence == CANDIDATE_CONFIDENCE_HIGH:
        return 0.9
    if confidence == CANDIDATE_CONFIDENCE_MEDIUM:
        return 0.65
    if confidence == CANDIDATE_CONFIDENCE_LOW:
        return 0.35
    try:
        return float((candidate or {}).get("confidence") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _candidate_value(candidate):
    return _text((candidate or {}).get("normalized_value") or (candidate or {}).get("raw_value")).lower()


def _baseline_status_map(baseline_resolution_result):
    if not isinstance(baseline_resolution_result, dict):
        return {}
    if isinstance(baseline_resolution_result.get("field_statuses"), dict):
        return {
            _text(field): _text(status)
            for field, status in baseline_resolution_result["field_statuses"].items()
        }
    result = {}
    for item in baseline_resolution_result.get("field_statuses", []) or []:
        if isinstance(item, dict):
            field_name = _text(item.get("field_name"))
            if field_name:
                result[field_name] = _text(item.get("status"))
    return result


def _text_stop_candidates(text_candidate_result):
    candidates = []
    for candidate in (text_candidate_result or {}).get("candidates", []) or []:
        if not isinstance(candidate, dict):
            continue
        field_name = _text(candidate.get("field_name"))
        if field_name not in _TEXT_STOP_FIELD_MAP:
            continue
        stop_type, stop_field = _TEXT_STOP_FIELD_MAP[field_name]
        candidates.append(
            {
                "full_field_name": field_name,
                "candidate_id": _text(candidate.get("candidate_id")) or field_name,
                "confidence": _candidate_confidence_score(candidate),
                "source": STOP_ASSOCIATION_SOURCE_TEXT_REGEX
                if _text(candidate.get("source")) == SOURCE_REGEX
                else STOP_ASSOCIATION_SOURCE_LABEL_VALUE,
                "value": _candidate_value(candidate),
            }
        )
    return candidates


def _layout_stop_candidates(layout_stop_association_result):
    candidates = []
    for group in (layout_stop_association_result or {}).get("stop_groups", []) or []:
        if not isinstance(group, dict):
            continue
        for candidate in group.get("field_candidates", []) or []:
            if not isinstance(candidate, dict):
                continue
            candidates.append(
                {
                    "full_field_name": _full_stop_field_name(
                        candidate.get("stop_type") or group.get("stop_type"),
                        candidate.get("field_name"),
                    ),
                    "candidate_id": _text(candidate.get("candidate_id")),
                    "confidence": float(candidate.get("confidence") or group.get("confidence") or 0.0),
                    "source": candidate.get("source") or group.get("source"),
                    "value": _candidate_value(candidate),
                    "stop_group_id": candidate.get("stop_group_id") or group.get("stop_group_id"),
                }
            )
    return candidates


def fuse_stop_candidates(
    text_candidate_result,
    layout_stop_association_result,
    baseline_resolution_result=None,
):
    """Fuse text and layout stop candidates without final field resolution."""

    baseline_statuses = _baseline_status_map(baseline_resolution_result)
    text_candidates = _text_stop_candidates(text_candidate_result)
    layout_candidates = _layout_stop_candidates(layout_stop_association_result)
    fields = sorted(
        set(candidate["full_field_name"] for candidate in text_candidates)
        | set(candidate["full_field_name"] for candidate in layout_candidates)
        | (set(baseline_statuses) & set(_TEXT_STOP_FIELD_MAP))
    )

    improved = []
    worsened = []
    unchanged = []
    conflicts = []
    unresolved = []
    warnings = list((layout_stop_association_result or {}).get("warning_codes", []) or [])

    for field_name in fields:
        baseline_status = baseline_statuses.get(field_name, "")
        field_text = [candidate for candidate in text_candidates if candidate["full_field_name"] == field_name]
        field_layout = [
            candidate for candidate in layout_candidates if candidate["full_field_name"] == field_name
        ]
        best_text = max(field_text, key=lambda candidate: candidate["confidence"], default=None)
        best_layout = max(field_layout, key=lambda candidate: candidate["confidence"], default=None)

        if best_text and best_layout:
            if (
                best_text.get("value")
                and best_layout.get("value")
                and best_text["value"] != best_layout["value"]
                and best_text["confidence"] >= 0.75
                and best_layout["confidence"] >= 0.75
            ):
                conflicts.append(field_name)
                warnings.append(f"stop_fusion_conflict:{field_name}")
            elif baseline_status in {"", "missing", "needs_review", "low_confidence"} and (
                best_layout["confidence"] > best_text["confidence"]
            ):
                improved.append(field_name)
            else:
                unchanged.append(field_name)
        elif best_layout:
            if baseline_status in {"", "missing", "needs_review", "low_confidence"}:
                improved.append(field_name)
            elif baseline_status == "resolved" and best_layout["confidence"] < 0.6:
                unchanged.append(field_name)
            else:
                unchanged.append(field_name)
        elif best_text:
            unchanged.append(field_name)
        else:
            unresolved.append(field_name)
            if baseline_status == "resolved":
                unchanged.append(field_name)
                warnings.append("layout_candidate_rejected_to_prevent_regression")

    return {
        "stop_groups": (layout_stop_association_result or {}).get("stop_groups", []),
        "improved_fields": sorted(set(improved)),
        "worsened_fields": sorted(set(worsened)),
        "unchanged_fields": sorted(set(unchanged)),
        "conflict_stop_fields": sorted(set(conflicts)),
        "unresolved_stop_fields": sorted(set(unresolved)),
        "warning_codes": sorted(set(_text(warning) for warning in warnings if _text(warning))),
        "association_version": STOP_ASSOCIATION_VERSION,
        "fusion_version": "stop_candidate_fusion_v1",
    }
