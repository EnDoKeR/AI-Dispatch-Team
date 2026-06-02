"""Dependency-free semantic helpers for shadow table diagnostics.

The functions here classify table cells by generic RateCon business roles.
They intentionally avoid broker templates and do not expose raw cell values in
their summaries.
"""

from collections import Counter
import re


ROLE_LOAD_IDENTITY = "load_identity"
ROLE_STOP_ROLE = "stop_role"
ROLE_LOCATION = "location"
ROLE_DATE = "date"
ROLE_TIME = "time"
ROLE_RATE = "rate"
ROLE_REFERENCE = "reference"
ROLE_UNKNOWN = "unknown"

TABLE_KIND_LOAD = "load"
TABLE_KIND_STOP = "stop"
TABLE_KIND_RATE = "rate"
TABLE_KIND_UNRECOGNIZED = "unrecognized"


LOAD_TERMS = (
    "load",
    "load #",
    "load no",
    "load number",
    "load id",
    "shipment",
    "shipment #",
    "shipment id",
    "order",
    "order #",
    "order no",
    "tender",
    "tender #",
    "confirmation",
    "rate confirmation",
    "dispatch",
    "trip",
)
REFERENCE_TERMS = ("po", "p.o.", "bol", "b.o.l.", "ref", "reference", "customer ref")
STOP_TERMS = (
    "stop",
    "stop #",
    "pickup",
    "pick up",
    "origin",
    "shipper",
    "delivery",
    "deliver",
    "destination",
    "consignee",
)
LOCATION_TERMS = (
    "location",
    "facility",
    "name",
    "address",
    "city",
    "state",
    "zip",
    "city/state/zip",
    "city st zip",
)
DATE_TERMS = (
    "date",
    "pickup date",
    "delivery date",
    "appointment",
    "appt",
    "ready",
    "close",
    "earliest",
    "latest",
)
TIME_TERMS = ("time", "window", "appt", "appointment", "ready", "close", "earliest", "latest")
RATE_TERMS = (
    "rate",
    "carrier pay",
    "total",
    "amount",
    "linehaul",
    "freight",
    "charges",
)


DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b")
TIME_PATTERN = re.compile(r"\b\d{1,2}:\d{2}\s*(?:am|pm)?\b", re.IGNORECASE)
MONEY_PATTERN = re.compile(r"\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")
ADDRESS_PATTERN = re.compile(r"\b\d{1,6}\s+[A-Za-z0-9 .'-]+(?:st|street|rd|road|ave|avenue|blvd|drive|dr|ln|lane)\b", re.IGNORECASE)
CITY_STATE_PATTERN = re.compile(r"\b[A-Z][A-Za-z .'-]+,\s*[A-Z]{2}(?:\s+\d{5})?\b")


def _text(value):
    return str(value or "").strip()


def _lower(value):
    return " ".join(_text(value).lower().replace("_", " ").split())


def _contains_any(text, markers):
    lower = _lower(text)
    return any(marker in lower for marker in markers)


def safe_value_shape(value):
    text = _text(value)
    return {
        "length": len(text),
        "token_count": len(text.split()),
        "has_digits": any(ch.isdigit() for ch in text),
        "has_letters": any(ch.isalpha() for ch in text),
        "has_dash": "-" in text,
        "has_slash": "/" in text,
        "looks_like_date": bool(DATE_PATTERN.search(text)),
        "looks_like_money": bool(MONEY_PATTERN.search(text)),
        "looks_like_phone": bool(PHONE_PATTERN.search(text)),
        "looks_like_address": bool(ADDRESS_PATTERN.search(text)),
        "looks_like_city_state_zip": bool(CITY_STATE_PATTERN.search(text)),
    }


def classify_cell_semantic_role(text):
    lower = _lower(text)
    if not lower:
        return ROLE_UNKNOWN
    if _contains_any(lower, LOAD_TERMS):
        return ROLE_LOAD_IDENTITY
    if _contains_any(lower, STOP_TERMS):
        return ROLE_STOP_ROLE
    if _contains_any(lower, DATE_TERMS):
        return ROLE_DATE
    if _contains_any(lower, TIME_TERMS):
        return ROLE_TIME
    if _contains_any(lower, LOCATION_TERMS):
        return ROLE_LOCATION
    if _contains_any(lower, REFERENCE_TERMS):
        return ROLE_REFERENCE
    if _contains_any(lower, RATE_TERMS):
        return ROLE_RATE
    shape = safe_value_shape(text)
    if shape["looks_like_date"]:
        return ROLE_DATE
    if TIME_PATTERN.search(_text(text)):
        return ROLE_TIME
    if shape["looks_like_address"] or shape["looks_like_city_state_zip"]:
        return ROLE_LOCATION
    if shape["looks_like_money"]:
        return ROLE_RATE
    return ROLE_UNKNOWN


def normalized_header_label(text):
    role = classify_cell_semantic_role(text)
    if role == ROLE_LOAD_IDENTITY:
        lower = _lower(text)
        if "shipment" in lower:
            return "shipment_number"
        if "order" in lower:
            return "order_number"
        if "tender" in lower:
            return "tender_number"
        if "confirmation" in lower:
            return "confirmation_number"
        if "dispatch" in lower:
            return "dispatch_number"
        if "trip" in lower:
            return "trip_number"
        return "load_number"
    if role == ROLE_REFERENCE:
        return "reference_number"
    return role


def _row_cells(row):
    cells = []
    for index, cell in enumerate((row or {}).get("cells", []) or []):
        if not isinstance(cell, dict):
            continue
        cells.append(
            {
                **cell,
                "column_index": int(cell.get("column_index", index) or 0),
                "text": _text(cell.get("text")),
            }
        )
    return cells


def _row_text(row):
    return " ".join(_text(cell.get("text")) for cell in _row_cells(row))


def _candidate_header_rows(rows):
    return [row for row in (rows or [])[:3] if isinstance(row, dict)]


def classify_table_semantics(table, table_index=0, page=1):
    rows = [row for row in (table or {}).get("rows", []) or [] if isinstance(row, dict)]
    best = {
        "table_index": table_index,
        "page": page,
        "row_count": len(rows),
        "column_count": int((table or {}).get("column_count") or 0),
        "header_row_index": "",
        "header_roles": {},
        "header_labels": {},
        "recognized_kind": TABLE_KIND_UNRECOGNIZED,
        "confidence": 0.0,
        "warnings": [],
    }
    best_score = 0
    for row in _candidate_header_rows(rows):
        roles = {}
        labels = {}
        for cell in _row_cells(row):
            role = classify_cell_semantic_role(cell.get("text"))
            if role != ROLE_UNKNOWN:
                col = str(cell.get("column_index", ""))
                roles[col] = role
                labels[col] = normalized_header_label(cell.get("text"))
        score = len(roles)
        if score > best_score:
            best_score = score
            best.update(
                {
                    "header_row_index": row.get("row_index", ""),
                    "header_roles": roles,
                    "header_labels": labels,
                }
            )
    role_values = set(best["header_roles"].values())
    all_text = " ".join(_row_text(row) for row in rows)
    if ROLE_STOP_ROLE in role_values or _contains_any(all_text, STOP_TERMS):
        best["recognized_kind"] = TABLE_KIND_STOP
    elif ROLE_LOAD_IDENTITY in role_values or _contains_any(all_text, LOAD_TERMS):
        best["recognized_kind"] = TABLE_KIND_LOAD
    elif ROLE_RATE in role_values or _contains_any(all_text, RATE_TERMS):
        best["recognized_kind"] = TABLE_KIND_RATE
    else:
        best["warnings"].append("TABLE_HEADERS_UNRECOGNIZED")
    if not best["header_roles"]:
        best["warnings"].append("TABLE_HEADER_ROW_NOT_FOUND")
    best["confidence"] = min(0.95, round(0.2 + (best_score * 0.15), 3)) if best_score else 0.0
    if best["column_count"] <= 0:
        max_col = -1
        for row in rows:
            for cell in _row_cells(row):
                max_col = max(max_col, int(cell.get("column_index", 0) or 0))
        best["column_count"] = max_col + 1 if max_col >= 0 else 0
    return best


def table_semantic_summary(tables_by_page):
    totals = Counter()
    header_roles = Counter()
    row_roles = Counter()
    for page, table_index, table in tables_by_page:
        semantics = classify_table_semantics(table, table_index=table_index, page=page)
        totals["tables_detected"] += 1
        kind = semantics.get("recognized_kind")
        if kind == TABLE_KIND_STOP:
            totals["recognized_stop_tables"] += 1
        elif kind == TABLE_KIND_LOAD:
            totals["recognized_load_tables"] += 1
        elif kind == TABLE_KIND_RATE:
            totals["recognized_rate_tables"] += 1
        else:
            totals["unrecognized_tables"] += 1
        for role in (semantics.get("header_roles") or {}).values():
            header_roles[role] += 1
        for row in (table or {}).get("rows", []) or []:
            row_text = _row_text(row)
            row_role = classify_cell_semantic_role(row_text)
            if row_role != ROLE_UNKNOWN:
                row_roles[row_role] += 1
    return {
        "tables_detected": totals.get("tables_detected", 0),
        "recognized_stop_tables": totals.get("recognized_stop_tables", 0),
        "recognized_load_tables": totals.get("recognized_load_tables", 0),
        "recognized_rate_tables": totals.get("recognized_rate_tables", 0),
        "unrecognized_tables": totals.get("unrecognized_tables", 0),
        "table_header_role_counts": dict(sorted(header_roles.items())),
        "table_row_role_counts": dict(sorted(row_roles.items())),
    }


def row_cells(row):
    return _row_cells(row)


def row_text(row):
    return _row_text(row)
