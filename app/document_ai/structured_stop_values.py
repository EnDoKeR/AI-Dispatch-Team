"""Structured stop value normalization for shadow RateCon resolution.

This module is intentionally dependency-light and diagnostic-only. It preserves
stop structure for resolver decisions without making partial stop evidence look
production-ready.
"""

ROLE_PICKUP = "pickup"
ROLE_DELIVERY = "delivery"
ROLE_UNKNOWN = "unknown"

FIELD_PICKUP_STOPS = "pickup_stops"
FIELD_DELIVERY_STOPS = "delivery_stops"

STOP_STATUS_COMPLETE = "complete"
STOP_STATUS_USEFUL_PARTIAL = "useful_partial"
STOP_STATUS_PARTIAL_ONLY = "partial_only"
STOP_STATUS_AMBIGUOUS = "ambiguous"
STOP_STATUS_UNSUPPORTED = "unsupported"
STOP_STATUS_EMPTY = "empty"

CONFLICT_DUPLICATE_SAME_STOP = "duplicate_same_stop"
CONFLICT_DUPLICATE_PARTIAL_OVERLAP = "duplicate_partial_overlap"
CONFLICT_DATE = "date_conflict"
CONFLICT_TIME = "time_conflict"
CONFLICT_LOCATION = "location_conflict"
CONFLICT_ROLE = "role_conflict"
CONFLICT_STOP_COUNT = "stop_count_conflict"
CONFLICT_UNKNOWN = "unknown_conflict"


def _text(value):
    return str(value or "").strip()


def _lower(value):
    return _text(value).lower()


def _bool(value):
    return bool(value)


def role_from_field(field):
    token = _lower(field)
    if token == FIELD_PICKUP_STOPS or "pickup" in token:
        return ROLE_PICKUP
    if token == FIELD_DELIVERY_STOPS or "delivery" in token:
        return ROLE_DELIVERY
    return ROLE_UNKNOWN


def _metadata_role(metadata, field):
    role = _lower((metadata or {}).get("stop_role")) or _lower(
        (metadata or {}).get("role")
    )
    if role in {ROLE_PICKUP, ROLE_DELIVERY}:
        return role
    return role_from_field(field)


def _safe_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return [value]
    if _text(value):
        return [value]
    return []


def _stop_from_mapping(item, default_role, metadata):
    item = item if isinstance(item, dict) else {}
    item_metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    role = _lower(item.get("role")) or _lower(item.get("stop_role")) or default_role
    if role not in {ROLE_PICKUP, ROLE_DELIVERY}:
        role = default_role
    facility = _text(item.get("facility") or item.get("name"))
    address = _text(item.get("address"))
    city = _text(item.get("city"))
    state = _text(item.get("state"))
    zip_code = _text(item.get("zip") or item.get("postal_code"))
    date = _text(item.get("date"))
    time = _text(item.get("time"))
    appointment_window = _text(item.get("appointment_window"))
    evidence_items = item.get("evidence_items") if isinstance(item.get("evidence_items"), list) else []
    page_span = item_metadata.get("page_span") or metadata.get("page_span") or []
    table_refs = []
    if metadata.get("table_index") not in ["", None]:
        table_refs.append(
            {
                "table_index": metadata.get("table_index", ""),
                "row_index": metadata.get("row_index", ""),
                "cell_indices": list(metadata.get("cell_indices", []) or []),
            }
        )
    return {
        "role": role or ROLE_UNKNOWN,
        "stop_index": item.get("stop_index") or metadata.get("stop_index") or 1,
        "facility": facility,
        "address": address,
        "city": city,
        "state": state,
        "zip": zip_code,
        "date": date,
        "time": time,
        "appointment_window": appointment_window,
        "source_summary": {
            "source": _text(metadata.get("generator_name") or metadata.get("source")),
            "pairing_method": _text(metadata.get("pairing_method")),
        },
        "evidence_count": int(metadata.get("evidence_count") or len(evidence_items) or 0),
        "page_span": list(page_span or []),
        "table_refs": table_refs,
        "bbox_refs": [],
    }


def _synthetic_stop_from_metadata(metadata, field):
    role = _metadata_role(metadata, field)
    return {
        "role": role,
        "stop_index": metadata.get("stop_index") or 1,
        "facility": "__present__" if metadata.get("has_facility") else "",
        "address": "__present__" if metadata.get("has_address") else "",
        "city": "__present__" if metadata.get("has_location") else "",
        "state": "",
        "zip": "",
        "date": "__present__" if metadata.get("has_date") else "",
        "time": "__present__" if metadata.get("has_time") else "",
        "appointment_window": "",
        "source_summary": {
            "source": _text(metadata.get("generator_name") or metadata.get("source")),
            "pairing_method": _text(metadata.get("pairing_method")),
        },
        "evidence_count": int(metadata.get("evidence_count") or 0),
        "page_span": list(metadata.get("page_span") or []),
        "table_refs": [
            {
                "table_index": metadata.get("table_index", ""),
                "row_index": metadata.get("row_index", ""),
                "cell_indices": list(metadata.get("cell_indices", []) or []),
            }
        ]
        if metadata.get("table_index") not in ["", None]
        else [],
        "bbox_refs": [],
    }


def _has_location(stop):
    return any(
        _text(stop.get(key))
        for key in ["facility", "address", "city", "state", "zip"]
    )


def _has_date(stop):
    return bool(_text(stop.get("date")))


def _has_time(stop):
    return bool(_text(stop.get("time")) or _text(stop.get("appointment_window")))


def _status(role, stops, metadata, warnings):
    if "unsupported" in warnings:
        return STOP_STATUS_UNSUPPORTED
    if not stops:
        return STOP_STATUS_EMPTY
    if role not in {ROLE_PICKUP, ROLE_DELIVERY} or metadata.get("ambiguous_stop_candidate"):
        return STOP_STATUS_AMBIGUOUS
    has_location = any(_has_location(stop) for stop in stops) or _bool(metadata.get("has_location"))
    has_date = any(_has_date(stop) for stop in stops) or _bool(metadata.get("has_date"))
    has_time = any(_has_time(stop) for stop in stops) or _bool(metadata.get("has_time"))
    if has_location and (has_date or has_time):
        return STOP_STATUS_COMPLETE
    if has_location or has_date or has_time:
        return STOP_STATUS_USEFUL_PARTIAL
    return STOP_STATUS_PARTIAL_ONLY


def _completeness_score(status, has_location, has_date, has_time):
    if status == STOP_STATUS_COMPLETE:
        if has_location and has_date and has_time:
            return 1.0
        return 0.85
    if status == STOP_STATUS_USEFUL_PARTIAL:
        return 0.62
    if status == STOP_STATUS_PARTIAL_ONLY:
        return 0.25
    if status == STOP_STATUS_AMBIGUOUS:
        return 0.2
    return 0.0


def normalize_stop_candidate_value(value, field, candidate_metadata=None):
    """Return a safe normalized stop decision object.

    The returned object may preserve private stop values internally for resolver
    comparison. Audit/reporting code must use ``safe_stop_normalization_summary``
    rather than serializing this object wholesale.
    """
    metadata = dict(candidate_metadata or {})
    role = _metadata_role(metadata, field)
    warnings = []
    stops = []
    raw_items = _safe_list(value)
    if not raw_items and not (
        metadata.get("structured_stop_candidate")
        or metadata.get("stop_candidate_kind")
        or metadata.get("stop_count")
    ):
        status = STOP_STATUS_EMPTY
    else:
        for item in raw_items:
            if isinstance(item, dict):
                stops.append(_stop_from_mapping(item, role, metadata))
            elif isinstance(item, str):
                if metadata.get("structured_stop_candidate") or metadata.get("stop_count"):
                    stops.append(_synthetic_stop_from_metadata(metadata, field))
                elif item.strip():
                    stops.append(_synthetic_stop_from_metadata(metadata, field))
                else:
                    warnings.append("empty_string")
            else:
                warnings.append("unsupported")
        if not stops and (
            metadata.get("structured_stop_candidate")
            or metadata.get("stop_candidate_kind")
            or metadata.get("stop_count")
        ):
            stops.append(_synthetic_stop_from_metadata(metadata, field))
        status = _status(role, stops, metadata, warnings)

    has_location = any(_has_location(stop) for stop in stops) or _bool(metadata.get("has_location"))
    has_date = any(_has_date(stop) for stop in stops) or _bool(metadata.get("has_date"))
    has_time = any(_has_time(stop) for stop in stops) or _bool(metadata.get("has_time"))
    has_facility = any(_text(stop.get("facility")) for stop in stops) or _bool(
        metadata.get("has_facility")
    )
    has_address = any(_text(stop.get("address")) for stop in stops) or _bool(
        metadata.get("has_address")
    )
    if status == STOP_STATUS_EMPTY:
        stops = []
    return {
        "field": field,
        "role": role,
        "stops": stops,
        "stop_count": len(stops) or int(metadata.get("stop_count") or 0),
        "has_location": bool(has_location),
        "has_date": bool(has_date),
        "has_time": bool(has_time),
        "has_facility": bool(has_facility),
        "has_address": bool(has_address),
        "completeness_score": _completeness_score(status, has_location, has_date, has_time),
        "structure_status": status,
        "normalization_warnings": sorted(set(warnings)),
    }


def _norm(value):
    text = _lower(value)
    if text == "__present__":
        return ""
    return " ".join(text.split())


def _material_values(normalized):
    stops = normalized.get("stops") or []
    if not stops:
        return {}
    first = stops[0]
    location = " ".join(
        _norm(first.get(key))
        for key in ["facility", "address", "city", "state", "zip"]
        if _norm(first.get(key))
    )
    return {
        "role": _lower(normalized.get("role")),
        "location": location,
        "date": _norm(first.get("date")),
        "time": _norm(first.get("time") or first.get("appointment_window")),
        "stop_count": str(normalized.get("stop_count") or ""),
    }


def stop_equivalence_key(normalized):
    values = _material_values(normalized)
    if not any(values.get(key) for key in ["location", "date", "time"]):
        return (
            values.get("role", ""),
            normalized.get("structure_status", ""),
            bool(normalized.get("has_location")),
            bool(normalized.get("has_date")),
            bool(normalized.get("has_time")),
        )
    return (
        values.get("role", ""),
        values.get("location", ""),
        values.get("date", ""),
        values.get("time", ""),
        values.get("stop_count", ""),
    )


def stop_conflict_types(left, right):
    left_values = _material_values(left)
    right_values = _material_values(right)
    conflicts = []
    if left_values.get("role") and right_values.get("role") and left_values["role"] != right_values["role"]:
        conflicts.append(CONFLICT_ROLE)
    if (
        left_values.get("stop_count")
        and right_values.get("stop_count")
        and left_values["stop_count"] != right_values["stop_count"]
    ):
        conflicts.append(CONFLICT_STOP_COUNT)
    for key, conflict_name in [
        ("date", CONFLICT_DATE),
        ("time", CONFLICT_TIME),
        ("location", CONFLICT_LOCATION),
    ]:
        if left_values.get(key) and right_values.get(key) and left_values[key] != right_values[key]:
            conflicts.append(conflict_name)
    return conflicts


def safe_stop_normalization_summary(normalized):
    normalized = normalized if isinstance(normalized, dict) else {}
    return {
        "field": _text(normalized.get("field")),
        "role": _text(normalized.get("role")),
        "stop_count": int(normalized.get("stop_count") or 0),
        "has_location": bool(normalized.get("has_location")),
        "has_date": bool(normalized.get("has_date")),
        "has_time": bool(normalized.get("has_time")),
        "has_facility": bool(normalized.get("has_facility")),
        "has_address": bool(normalized.get("has_address")),
        "completeness_score": round(float(normalized.get("completeness_score") or 0.0), 3),
        "structure_status": _text(normalized.get("structure_status")),
        "normalization_warnings": list(normalized.get("normalization_warnings") or []),
    }
