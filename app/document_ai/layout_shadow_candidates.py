"""Shadow-only layout-aware candidate generation diagnostics."""

from collections import Counter, defaultdict
import re

from app.document_ai.field_candidate_provenance import (
    SOURCE_NATIVE_LAYOUT,
    build_field_candidate,
)
from app.document_ai.field_candidate_resolver import (
    FIELD_DELIVERY_STOPS,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_STOPS,
)
from app.document_ai.load_identifier_candidates import classify_identifier_label
from app.document_ai.load_identity_forensics import (
    candidate_value_shape,
    identifier_value_rejection_reason,
)
from app.document_ai.section_context import classify_line_section_context
from app.document_ai.stop_evidence_assembler import (
    EVIDENCE_ADDRESS,
    EVIDENCE_APPOINTMENT_WINDOW,
    EVIDENCE_CITY_STATE_ZIP,
    EVIDENCE_DATE,
    EVIDENCE_FACILITY,
    EVIDENCE_TIME,
    ROLE_DELIVERY,
    ROLE_PICKUP,
    classify_stop_value_shape,
)
from app.document_ai.ratecon_table_semantics import (
    ROLE_DATE,
    ROLE_LOAD_IDENTITY,
    ROLE_LOCATION,
    ROLE_RATE,
    ROLE_REFERENCE,
    ROLE_STOP_ROLE,
    ROLE_TIME,
    ROLE_UNKNOWN,
    classify_cell_semantic_role,
    classify_table_semantics,
    normalized_header_label,
    row_cells,
    safe_value_shape,
    table_semantic_summary,
)


GENERATOR_LAYOUT_LOAD_PAIRING = "layout_load_identity_pairing_generator"
GENERATOR_LAYOUT_STOP_TABLE = "layout_stop_table_candidate_generator"

PAIR_SAME_ROW_RIGHT = "same_row_right"
PAIR_NEARBY_ROW = "nearby_row"
PAIR_TABLE_CELL = "table_cell"
PAIR_HEADER_BLOCK = "header_block"
PAIR_TABLE_KEY_VALUE_ROW = "table_key_value_row"
PAIR_TABLE_HEADER_VALUE_COLUMN = "table_header_value_column"
PAIR_TABLE_SAME_CELL = "table_same_cell"
PAIR_TABLE_NEAREST_CELL = "table_nearest_cell"

STOP_PAIR_TABLE_ROW_SEMANTIC = "table_row_semantic"
STOP_PAIR_SPLIT_COLUMNS = "table_split_pickup_delivery_columns"
STOP_PAIR_ROLE_FIRST_CELL = "table_role_first_cell"
STOP_PAIR_HEADER_VALUE = "table_header_value"


LOAD_LABEL_PATTERN = re.compile(
    r"\b(?P<label>(?:rate\s+confirmation|load|shipment|order|tender|confirmation|dispatch|trip)"
    r"(?:\s*(?:#|no\.?|number|id))?)\b",
    re.IGNORECASE,
)
REFERENCE_ONLY_PATTERN = re.compile(r"\b(?:po|p\.o\.|bol|b\.o\.l\.|ref|reference)\b", re.IGNORECASE)

PICKUP_MARKERS = ("pickup", "pick up", "pu", "shipper", "origin")
DELIVERY_MARKERS = ("delivery", "deliver", "drop", "consignee", "destination", "receiver")
DATE_MARKERS = ("date", "appt", "appointment")
TIME_MARKERS = ("time", "appt", "appointment", "window")
LOCATION_MARKERS = ("location", "address", "city", "state", "zip", "facility", "name")
RATE_MARKERS = ("rate", "carrier pay", "total", "amount", "linehaul", "freight")


def _text(value):
    return str(value or "").strip()


def _safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bbox(value):
    if isinstance(value, list):
        return value
    return None


def _line_rows(artifact):
    rows = []
    for page in (artifact or {}).get("pages", []) or []:
        page_number = _safe_int(page.get("page_number"))
        context = "unknown"
        for line in page.get("lines", []) or []:
            if not isinstance(line, dict):
                continue
            text = _text(line.get("text"))
            if not text:
                continue
            context = classify_line_section_context(text, previous_context=context)
            rows.append(
                {
                    "page": page_number,
                    "line_index": _safe_int(line.get("line_index")),
                    "line_id": _text(line.get("line_id")),
                    "text": text,
                    "bbox": _bbox(line.get("bbox")),
                    "section_context": context,
                    "source": _text(line.get("source")) or SOURCE_NATIVE_LAYOUT,
                }
            )
    return rows


def _table_rows(artifact):
    for page in (artifact or {}).get("pages", []) or []:
        page_number = _safe_int(page.get("page_number"))
        for table_index, table in enumerate(page.get("tables", []) or []):
            if not isinstance(table, dict):
                continue
            for row in table.get("rows", []) or []:
                if not isinstance(row, dict):
                    continue
                yield page_number, table_index, table, row


def _right_value_from_text(text, match):
    suffix = _text(text[match.end() :]).lstrip(" :#.-\t")
    if not suffix:
        return ""
    return suffix.split()[0].strip(" ,;")


def _id_hint(label):
    lower = _text(label).lower()
    for token in ["load", "shipment", "order", "tender", "confirmation", "dispatch", "trip"]:
        if token in lower:
            return token
    if REFERENCE_ONLY_PATTERN.search(lower):
        return "reference"
    return "unknown"


def _confidence(label, method):
    hint = _id_hint(label)
    table_methods = {
        PAIR_TABLE_CELL,
        PAIR_TABLE_KEY_VALUE_ROW,
        PAIR_TABLE_HEADER_VALUE_COLUMN,
        PAIR_TABLE_SAME_CELL,
        PAIR_TABLE_NEAREST_CELL,
    }
    if hint == "load" and method in {PAIR_SAME_ROW_RIGHT, *table_methods}:
        return 0.86
    if hint in {"shipment", "order", "tender", "confirmation", "dispatch", "trip"} and method in {
        PAIR_SAME_ROW_RIGHT,
        *table_methods,
    }:
        return 0.74
    if method == PAIR_NEARBY_ROW:
        return 0.62
    if method == PAIR_HEADER_BLOCK:
        return 0.58
    return 0.45


def _load_candidate(label, value, page, bbox, label_bbox, method, section_context, diagnostics):
    rejection = identifier_value_rejection_reason(value)
    diagnostics["method_attempt_counts"][method] += 1
    if rejection:
        diagnostics["layout_rejection_reason_counts"][rejection] += 1
        return None
    diagnostics["method_success_counts"][method] += 1
    diagnostics["layout_candidates_emitted"] += 1
    if method == PAIR_SAME_ROW_RIGHT:
        diagnostics["same_row_pairings"] += 1
    elif method == PAIR_NEARBY_ROW:
        diagnostics["nearby_row_pairings"] += 1
    elif method == PAIR_TABLE_CELL:
        diagnostics["table_cell_pairings"] += 1
    elif method in {
        PAIR_TABLE_KEY_VALUE_ROW,
        PAIR_TABLE_HEADER_VALUE_COLUMN,
        PAIR_TABLE_SAME_CELL,
        PAIR_TABLE_NEAREST_CELL,
    }:
        diagnostics["table_cell_pairings"] += 1
        diagnostics["table_pairings_by_method"][method] += 1
    elif method == PAIR_HEADER_BLOCK:
        diagnostics["header_block_pairings"] += 1

    classification = classify_identifier_label(label, {"window": section_context})
    hint = _id_hint(label)
    primary = bool(classification.get("primary_load_identifier_candidate")) or hint == "load"
    if REFERENCE_ONLY_PATTERN.search(label):
        primary = False
    field_name = FIELD_LOAD_NUMBER if primary else "reference_numbers"
    confidence = _confidence(label, method)
    return build_field_candidate(
        field=field_name,
        value=value,
        normalized_value=value,
        label=label,
        evidence_text=f"{label} [{method}-layout-value-present]",
        page=page,
        bbox=bbox,
        source=SOURCE_NATIVE_LAYOUT,
        parser_name=GENERATOR_LAYOUT_LOAD_PAIRING,
        confidence=confidence,
        metadata={
            "layout_provider": "document_layout_artifact",
            "has_bbox": bool(bbox or label_bbox),
            "label_bbox": label_bbox,
            "value_bbox": bbox,
            "pairing_method": method,
            "layout_table_pairing_method": method if method.startswith("table_") else "",
            "section_context": section_context,
            "id_type_hint": hint,
            "label_strength": (
                "strong"
                if hint == "load"
                else "medium"
                if hint in {"shipment", "order", "tender", "confirmation", "dispatch", "trip"}
                else "weak"
            ),
            "candidate_value_shape": candidate_value_shape(value),
            "label_confidence": confidence,
            "layout_pairing": True,
            "table_cell_candidate": method.startswith("table_"),
        },
    )


def _empty_load_diagnostics():
    return {
        "layout_label_hits": 0,
        "same_row_pairings": 0,
        "nearby_row_pairings": 0,
        "table_cell_pairings": 0,
        "header_block_pairings": 0,
        "layout_candidates_emitted": 0,
        "layout_rejection_reason_counts": Counter(),
        "method_attempt_counts": Counter(),
        "method_success_counts": Counter(),
        "table_pairings_by_method": Counter(),
        "table_load_label_hits": 0,
        "docs_with_table_load_candidates": 0,
    }


def _first_safe_token(text):
    return _text(text).split()[0].strip(" ,;") if _text(text) else ""


def _table_cell_value(cell):
    return _first_safe_token((cell or {}).get("text"))


def _same_cell_value(text, match):
    return _right_value_from_text(text, match)


def _nearest_non_empty_cell(cells, start_index):
    for candidate_cell in cells[start_index + 1 :]:
        if _text(candidate_cell.get("text")):
            return candidate_cell
    return None


def _cell_below(table, row_index, column_index):
    target = _safe_int(row_index) + 1
    for row in (table or {}).get("rows", []) or []:
        if _safe_int(row.get("row_index")) != target:
            continue
        for cell in row_cells(row):
            if _safe_int(cell.get("column_index")) == _safe_int(column_index) and _text(cell.get("text")):
                return cell
    return None


def _table_load_candidates(page, table_index, table, diagnostics):
    candidates = []
    semantics = classify_table_semantics(table, table_index=table_index, page=page)
    header_roles = semantics.get("header_roles", {}) or {}
    header_labels = semantics.get("header_labels", {}) or {}
    header_row_index = _safe_int(semantics.get("header_row_index"))

    for row in (table or {}).get("rows", []) or []:
        cells = row_cells(row)
        for cell_index, cell in enumerate(cells):
            text = _text(cell.get("text"))
            match = LOAD_LABEL_PATTERN.search(text)
            role = classify_cell_semantic_role(text)
            if not match and role not in {ROLE_LOAD_IDENTITY, ROLE_REFERENCE}:
                continue
            diagnostics["layout_label_hits"] += 1
            diagnostics["table_load_label_hits"] += 1
            label = match.group("label") if match else normalized_header_label(text)

            same_cell = _same_cell_value(text, match) if match else ""
            if same_cell:
                candidate = _load_candidate(
                    label,
                    same_cell,
                    page,
                    _bbox(cell.get("bbox")),
                    _bbox(cell.get("bbox")),
                    PAIR_TABLE_SAME_CELL,
                    "load_info",
                    diagnostics,
                )
                if candidate:
                    metadata = dict(candidate.get("metadata") or {})
                    metadata.update(
                        {
                            "table_index": table_index,
                            "row_index": row.get("row_index", ""),
                            "label_cell_index": cell.get("column_index", ""),
                            "value_cell_index": cell.get("column_index", ""),
                        }
                    )
                    candidate["metadata"] = metadata
                    candidates.append(candidate)
                    continue

            value_cell = _nearest_non_empty_cell(cells, cell_index)
            if value_cell:
                candidate = _load_candidate(
                    label,
                    _table_cell_value(value_cell),
                    page,
                    _bbox(value_cell.get("bbox")),
                    _bbox(cell.get("bbox")),
                    PAIR_TABLE_KEY_VALUE_ROW,
                    "load_info",
                    diagnostics,
                )
                if candidate:
                    metadata = dict(candidate.get("metadata") or {})
                    metadata.update(
                        {
                            "table_index": table_index,
                            "row_index": row.get("row_index", ""),
                            "label_cell_index": cell.get("column_index", ""),
                            "value_cell_index": value_cell.get("column_index", ""),
                        }
                    )
                    candidate["metadata"] = metadata
                    candidates.append(candidate)
                    continue
                else:
                    diagnostics["layout_rejection_reason_counts"]["TABLE_LOAD_VALUE_SHAPE_REJECTED"] += 1

            below_cell = _cell_below(table, row.get("row_index", 0), cell.get("column_index", 0))
            if below_cell:
                candidate = _load_candidate(
                    label,
                    _table_cell_value(below_cell),
                    page,
                    _bbox(below_cell.get("bbox")),
                    _bbox(cell.get("bbox")),
                    PAIR_TABLE_NEAREST_CELL,
                    "load_info",
                    diagnostics,
                )
                if candidate:
                    metadata = dict(candidate.get("metadata") or {})
                    metadata.update(
                        {
                            "table_index": table_index,
                            "row_index": row.get("row_index", ""),
                            "label_cell_index": cell.get("column_index", ""),
                            "value_cell_index": below_cell.get("column_index", ""),
                        }
                    )
                    candidate["metadata"] = metadata
                    candidates.append(candidate)
                    continue

            diagnostics["layout_rejection_reason_counts"]["TABLE_LOAD_LABEL_FOUND_VALUE_MISSING"] += 1

    for col, role in header_roles.items():
        if role not in {ROLE_LOAD_IDENTITY, ROLE_REFERENCE}:
            continue
        label = header_labels.get(str(col), "load_number")
        for row in (table or {}).get("rows", []) or []:
            if _safe_int(row.get("row_index")) <= header_row_index:
                continue
            for cell in row_cells(row):
                if str(cell.get("column_index")) != str(col) or not _text(cell.get("text")):
                    continue
                diagnostics["layout_label_hits"] += 1
                diagnostics["table_load_label_hits"] += 1
                candidate = _load_candidate(
                    label,
                    _table_cell_value(cell),
                    page,
                    _bbox(cell.get("bbox")),
                    None,
                    PAIR_TABLE_HEADER_VALUE_COLUMN,
                    "load_info",
                    diagnostics,
                )
                if candidate:
                    metadata = dict(candidate.get("metadata") or {})
                    metadata.update(
                        {
                            "table_index": table_index,
                            "row_index": row.get("row_index", ""),
                            "label_cell_index": str(col),
                            "value_cell_index": cell.get("column_index", ""),
                            "header_row_index": semantics.get("header_row_index", ""),
                        }
                    )
                    candidate["metadata"] = metadata
                    candidates.append(candidate)
                else:
                    diagnostics["layout_rejection_reason_counts"]["TABLE_LOAD_VALUE_SHAPE_REJECTED"] += 1
    return candidates


def generate_layout_load_identity_candidates(artifact):
    diagnostics = _empty_load_diagnostics()
    candidates = []
    rows = _line_rows(artifact)
    by_page = defaultdict(list)
    for row in rows:
        by_page[row["page"]].append(row)

    for page_rows in by_page.values():
        for index, row in enumerate(page_rows):
            for match in LOAD_LABEL_PATTERN.finditer(row["text"]):
                diagnostics["layout_label_hits"] += 1
                label = match.group("label")
                value = _right_value_from_text(row["text"], match)
                if value:
                    candidate = _load_candidate(
                        label,
                        value,
                        row["page"],
                        row["bbox"],
                        row["bbox"],
                        PAIR_SAME_ROW_RIGHT,
                        row["section_context"],
                        diagnostics,
                    )
                    if candidate:
                        candidates.append(candidate)
                        continue
                else:
                    diagnostics["layout_rejection_reason_counts"]["LAYOUT_LOAD_LABEL_NO_RIGHT_VALUE"] += 1
                for offset in [1, -1, 2, -2]:
                    nearby_index = index + offset
                    if nearby_index < 0 or nearby_index >= len(page_rows):
                        continue
                    nearby = page_rows[nearby_index]
                    nearby_value = _text(nearby["text"]).split()[0] if _text(nearby["text"]) else ""
                    candidate = _load_candidate(
                        label,
                        nearby_value,
                        nearby["page"],
                        nearby["bbox"],
                        row["bbox"],
                        PAIR_NEARBY_ROW,
                        row["section_context"],
                        diagnostics,
                    )
                    if candidate:
                        candidates.append(candidate)
                        break
                else:
                    diagnostics["layout_rejection_reason_counts"]["LAYOUT_LOAD_LABEL_NO_NEARBY_VALUE"] += 1

    seen_tables = set()
    for page, table_index, table, _row in _table_rows(artifact):
        identity = (page, table_index)
        if identity in seen_tables:
            continue
        seen_tables.add(identity)
        candidates.extend(_table_load_candidates(page, table_index, table, diagnostics))

    if candidates:
        diagnostics["docs_with_table_load_candidates"] = 1 if any(
            (candidate.get("metadata") or {}).get("table_cell_candidate")
            for candidate in candidates
        ) else 0

    diagnostics = {
        key: dict(value.most_common()) if isinstance(value, Counter) else value
        for key, value in diagnostics.items()
    }
    return candidates, diagnostics


def _contains_any(text, markers):
    lower = _text(text).lower()
    return any(marker in lower for marker in markers)


def _role_from_row(row_text):
    if _contains_any(row_text, PICKUP_MARKERS):
        return ROLE_PICKUP
    if _contains_any(row_text, DELIVERY_MARKERS):
        return ROLE_DELIVERY
    return "unknown"


def _kind_from_header_or_value(header, value):
    combined = f"{header} {value}".lower()
    if _contains_any(combined, DATE_MARKERS) or classify_stop_value_shape(value) == EVIDENCE_DATE:
        return EVIDENCE_DATE
    if _contains_any(combined, TIME_MARKERS) or classify_stop_value_shape(value) in {EVIDENCE_TIME, EVIDENCE_APPOINTMENT_WINDOW}:
        return EVIDENCE_TIME
    if _contains_any(combined, LOCATION_MARKERS):
        shape = classify_stop_value_shape(value)
        if shape in {EVIDENCE_ADDRESS, EVIDENCE_CITY_STATE_ZIP, EVIDENCE_FACILITY}:
            return shape
        return EVIDENCE_FACILITY
    shape = classify_stop_value_shape(value)
    if shape in {EVIDENCE_ADDRESS, EVIDENCE_CITY_STATE_ZIP, EVIDENCE_FACILITY}:
        return shape
    return "unknown"


def _headers(row):
    return {
        _safe_int(cell.get("column_index")): _text(cell.get("text")).lower()
        for cell in row.get("cells", []) or []
        if isinstance(cell, dict)
    }


def _role_from_text(text):
    return _role_from_row(text)


def _kind_from_semantic_role(role, value):
    if role == ROLE_LOCATION:
        shape = classify_stop_value_shape(value)
        if shape in {EVIDENCE_ADDRESS, EVIDENCE_CITY_STATE_ZIP, EVIDENCE_FACILITY}:
            return shape
        return EVIDENCE_FACILITY
    if role == ROLE_DATE:
        return EVIDENCE_DATE
    if role == ROLE_TIME:
        return EVIDENCE_TIME
    return "unknown"


def _row_stop_cells_from_headers(row, header_roles):
    cells = []
    for cell in row_cells(row):
        role = header_roles.get(str(cell.get("column_index")), ROLE_UNKNOWN)
        kind = _kind_from_semantic_role(role, cell.get("text"))
        if kind == "unknown":
            continue
        cells.append(
            {
                "kind": kind,
                "column_index": cell.get("column_index", ""),
                "bbox": _bbox(cell.get("bbox")),
                "text": _text(cell.get("text")),
            }
        )
    return cells


def _split_pickup_delivery_candidates(page, table_index, table, semantics):
    candidates = []
    header_roles = semantics.get("header_roles", {}) or {}
    header_row_index = _safe_int(semantics.get("header_row_index"))
    header_cells = []
    for header_row in (table or {}).get("rows", []) or []:
        if _safe_int(header_row.get("row_index")) == header_row_index:
            header_cells = row_cells(header_row)
            break
    pickup_cols = []
    delivery_cols = []
    for cell in header_cells:
        col = str(cell.get("column_index"))
        lower = _text(cell.get("text")).lower()
        role = header_roles.get(col)
        if any(token in lower for token in ["location", "address", "city", "state", "zip", "facility"]):
            role = ROLE_LOCATION
        elif "date" in lower or "appt" in lower or "appointment" in lower:
            role = ROLE_DATE
        elif "time" in lower or "window" in lower:
            role = ROLE_TIME
        if "pickup" in lower or "shipper" in lower or "origin" in lower:
            pickup_cols.append((col, role))
        if "delivery" in lower or "consignee" in lower or "destination" in lower:
            delivery_cols.append((col, role))
    for row in (table or {}).get("rows", []) or []:
        if _is_semantic_header_row(row, semantics):
            continue
        for role_name, columns in [(ROLE_PICKUP, pickup_cols), (ROLE_DELIVERY, delivery_cols)]:
            row_cells_payload = []
            for col, semantic_role in columns:
                for cell in row_cells(row):
                    if str(cell.get("column_index")) != col:
                        continue
                    kind = _kind_from_semantic_role(semantic_role, cell.get("text"))
                    if kind != "unknown":
                        row_cells_payload.append(
                            {
                                "kind": kind,
                                "column_index": cell.get("column_index", ""),
                                "bbox": _bbox(cell.get("bbox")),
                                "text": _text(cell.get("text")),
                            }
                        )
            if row_cells_payload:
                candidates.append(
                    _stop_candidate(
                        role_name,
                        row_cells_payload,
                        page,
                        table_index,
                        row.get("row_index", ""),
                        STOP_PAIR_SPLIT_COLUMNS,
                        "table_split_pickup_delivery_columns",
                    )
                )
    return candidates


def _is_semantic_header_row(row, semantics):
    if _safe_int(row.get("row_index")) != _safe_int(semantics.get("header_row_index")):
        return False
    text = " ".join(_text(cell.get("text")) for cell in row_cells(row))
    shape = safe_value_shape(text)
    if shape["looks_like_date"] or shape["looks_like_address"] or shape["looks_like_city_state_zip"]:
        return False
    return bool(semantics.get("header_roles"))


def _private_stop_components_from_cells(role, cells, confidence, source):
    if role not in {ROLE_PICKUP, ROLE_DELIVERY}:
        return {}
    stop = {
        "role": role,
        "stop_index": 1,
        "facility": "",
        "address": "",
        "city": "",
        "state": "",
        "zip": "",
        "date": "",
        "time": "",
        "appointment_window": "",
        "confidence": round(float(confidence or 0.0), 3),
        "source": source,
        "structure_status": "",
    }
    for cell in cells or []:
        value = _text(cell.get("text"))
        if not value:
            continue
        kind = cell.get("kind")
        if kind == EVIDENCE_FACILITY and not stop["facility"]:
            stop["facility"] = value
        elif kind == EVIDENCE_ADDRESS and not stop["address"]:
            stop["address"] = value
        elif kind == EVIDENCE_CITY_STATE_ZIP and not stop["city"]:
            stop["city"] = value
        elif kind == EVIDENCE_DATE and not stop["date"]:
            stop["date"] = value
        elif kind == EVIDENCE_TIME and not stop["time"]:
            stop["time"] = value
        elif kind == EVIDENCE_APPOINTMENT_WINDOW and not stop["appointment_window"]:
            stop["appointment_window"] = value
    if any(
        _text(stop.get(key))
        for key in [
            "facility",
            "address",
            "city",
            "state",
            "zip",
            "date",
            "time",
            "appointment_window",
        ]
    ):
        return stop
    return {}


def _stop_candidate(role, row_cells, page, table_index, row_index, method, confidence_reason):
    location_types = {EVIDENCE_ADDRESS, EVIDENCE_CITY_STATE_ZIP, EVIDENCE_FACILITY}
    has_location = any(cell["kind"] in location_types for cell in row_cells)
    has_date = any(cell["kind"] == EVIDENCE_DATE for cell in row_cells)
    has_time = any(cell["kind"] in {EVIDENCE_TIME, EVIDENCE_APPOINTMENT_WINDOW} for cell in row_cells)
    confidence = 0.78 if has_location and has_date else 0.55 if has_location or has_date else 0.4
    field = FIELD_PICKUP_STOPS if role == ROLE_PICKUP else FIELD_DELIVERY_STOPS
    candidate = build_field_candidate(
        field=field,
        value=f"{role}_layout_stop_present",
        normalized_value=f"{role}_layout_stop_present",
        label=f"{role}_layout_stop",
        evidence_text=(
            f"{role}_layout_stop; has_location={has_location}; has_date={has_date}; "
            f"has_time={has_time}"
        ),
        page=page,
        bbox=row_cells[0].get("bbox") if row_cells else None,
        source=SOURCE_NATIVE_LAYOUT,
        parser_name=GENERATOR_LAYOUT_STOP_TABLE,
        confidence=confidence,
        metadata={
            "layout_provider": "document_layout_artifact",
            "table_index": table_index,
            "row_index": row_index,
            "cell_indices": [cell.get("column_index", "") for cell in row_cells],
            "stop_role": role,
            "evidence_count": len(row_cells),
            "structured_stop_candidate": True,
            "has_location": has_location,
            "has_date": has_date,
            "has_time": has_time,
            "pairing_method": method,
            "confidence_reason": confidence_reason,
            "partial_stop_candidate": bool((has_location or has_date or has_time) and not (has_location and has_date)),
            "ambiguous_stop_candidate": role == "unknown",
            "diagnostic_fallback": False,
            "independent_candidate": True,
        },
    )
    private_stop = _private_stop_components_from_cells(role, row_cells, confidence, SOURCE_NATIVE_LAYOUT)
    if private_stop:
        candidate["_private_eval_stop_components"] = [private_stop]
    return candidate


def generate_layout_stop_table_candidates(artifact):
    candidates = []
    diagnostics = {
        "layout_stop_evidence_count": 0,
        "layout_structured_stop_candidates": 0,
        "table_row_stop_candidates": 0,
        "bbox_cluster_stop_candidates": 0,
        "table_stop_candidates_complete": 0,
        "table_stop_candidates_partial": 0,
        "table_stop_candidates_ambiguous": 0,
        "table_pairings_by_method": Counter(),
        "layout_ambiguity_reason_counts": Counter(),
    }
    seen_tables = set()
    for page, table_index, table, _row in _table_rows(artifact):
        identity = (page, table_index)
        if identity in seen_tables:
            continue
        seen_tables.add(identity)
        semantics = classify_table_semantics(table, table_index=table_index, page=page)
        header_roles = semantics.get("header_roles", {}) or {}

        split_candidates = _split_pickup_delivery_candidates(page, table_index, table, semantics)
        for candidate in split_candidates:
            candidates.append(candidate)
            metadata = candidate.get("metadata") or {}
            diagnostics["layout_stop_evidence_count"] += _safe_int(metadata.get("evidence_count", 0)) or len(metadata.get("cell_indices", []) or [])
            diagnostics["layout_structured_stop_candidates"] += 1
            diagnostics["table_row_stop_candidates"] += 1
            diagnostics["table_pairings_by_method"][STOP_PAIR_SPLIT_COLUMNS] += 1
            if metadata.get("has_location") and (metadata.get("has_date") or metadata.get("has_time")):
                diagnostics["table_stop_candidates_complete"] += 1
            elif metadata.get("has_location") or metadata.get("has_date") or metadata.get("has_time"):
                diagnostics["table_stop_candidates_partial"] += 1

        for row in (table or {}).get("rows", []) or []:
            if _is_semantic_header_row(row, semantics):
                continue
            cells = row_cells(row)
            row_text = " ".join(_text(cell.get("text")) for cell in cells)
            role = _role_from_text(row_text)
            if role == "unknown":
                if _contains_any(row_text, DATE_MARKERS + TIME_MARKERS + LOCATION_MARKERS):
                    diagnostics["layout_ambiguity_reason_counts"]["LAYOUT_STOP_ROLE_AMBIGUOUS"] += 1
                    diagnostics["table_stop_candidates_ambiguous"] += 1
                continue
            semantic_cells = _row_stop_cells_from_headers(row, header_roles)
            if not semantic_cells:
                semantic_cells = []
                for cell in cells:
                    kind = _kind_from_header_or_value("", cell.get("text"))
                    if kind == "unknown":
                        continue
                    semantic_cells.append(
                        {
                            "kind": kind,
                            "column_index": cell.get("column_index", ""),
                            "bbox": _bbox(cell.get("bbox")),
                            "text": _text(cell.get("text")),
                        }
                    )
            diagnostics["layout_stop_evidence_count"] += len(semantic_cells)
            if not semantic_cells:
                diagnostics["layout_ambiguity_reason_counts"]["LAYOUT_STOP_ROW_PAIRING_FAILED"] += 1
                continue
            method = STOP_PAIR_ROLE_FIRST_CELL if classify_cell_semantic_role(_text(cells[0].get("text")) if cells else "") == ROLE_STOP_ROLE else STOP_PAIR_TABLE_ROW_SEMANTIC
            candidate = _stop_candidate(
                role,
                semantic_cells,
                page,
                table_index,
                row.get("row_index", ""),
                method,
                "layout_stop_table_row",
            )
            candidates.append(candidate)
            metadata = candidate.get("metadata") or {}
            complete = bool(metadata.get("has_location") and (metadata.get("has_date") or metadata.get("has_time")))
            if complete:
                diagnostics["table_stop_candidates_complete"] += 1
            else:
                diagnostics["table_stop_candidates_partial"] += 1
            diagnostics["layout_structured_stop_candidates"] += 1
            diagnostics["table_row_stop_candidates"] += 1
            diagnostics["table_pairings_by_method"][method] += 1

    diagnostics["layout_ambiguity_reason_counts"] = dict(
        diagnostics["layout_ambiguity_reason_counts"].most_common()
    )
    diagnostics["table_pairings_by_method"] = dict(
        diagnostics["table_pairings_by_method"].most_common()
    )
    return candidates, diagnostics


def summarize_tables_for_shadow(artifact):
    seen_tables = set()
    docs_with_tables = 0
    stop_headers = 0
    rate_headers = 0
    load_headers = 0
    stop_role_rows = 0
    date_time_location_rows = 0
    table_payloads = []
    table_payload_seen = set()
    for page, table_index, _table, row in _table_rows(artifact):
        seen_tables.add((page, table_index))
        table_identity = (page, table_index, id(_table))
        if table_identity not in table_payload_seen:
            table_payload_seen.add(table_identity)
            table_payloads.append((page, table_index, _table))
        row_text = " ".join(
            _text(cell.get("text"))
            for cell in row.get("cells", []) or []
            if isinstance(cell, dict)
        )
        if _contains_any(row_text, PICKUP_MARKERS + DELIVERY_MARKERS):
            stop_role_rows += 1
        if _contains_any(row_text, DATE_MARKERS + TIME_MARKERS) and _contains_any(row_text, LOCATION_MARKERS):
            date_time_location_rows += 1
        if _contains_any(row_text, PICKUP_MARKERS + DELIVERY_MARKERS + LOCATION_MARKERS):
            stop_headers += 1
        if _contains_any(row_text, RATE_MARKERS):
            rate_headers += 1
        if LOAD_LABEL_PATTERN.search(row_text):
            load_headers += 1
    table_count = len(seen_tables)
    docs_with_tables = 1 if table_count else 0
    semantic_summary = table_semantic_summary(table_payloads)
    return {
        "docs_with_tables": docs_with_tables,
        "tables_detected": table_count,
        "tables_with_stop_like_headers": stop_headers,
        "tables_with_rate_like_headers": rate_headers,
        "tables_with_load_like_headers": load_headers,
        "table_rows_with_stop_role": stop_role_rows,
        "table_rows_with_date_time_location": date_time_location_rows,
        **semantic_summary,
    }
