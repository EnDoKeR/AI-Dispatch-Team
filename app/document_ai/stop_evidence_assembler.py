"""Stop evidence assembly for RateCon shadow diagnostics.

This module turns existing partial pickup/delivery FieldCandidate objects into
structured stop candidates for the shadow document pipeline. It is diagnostic
only: it does not replace normalized legacy stops and does not invent missing
location/date/time values.
"""

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field as dataclass_field
import re

from app.document_ai.field_candidate_provenance import SOURCE_NATIVE_TEXT
from app.document_ai.ratecon_canonical_fields import (
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_LOCATION,
    FIELD_DELIVERY_STOPS,
    FIELD_DELIVERY_TIME,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    FIELD_PICKUP_STOPS,
    FIELD_PICKUP_TIME,
    MAPPING_STRONG,
    value_shape,
)
from app.document_ai.section_context import (
    SECTION_UNKNOWN,
    artifact_page_lines_with_context,
)


GENERATOR_STOP_EVIDENCE_ASSEMBLER = "stop_evidence_assembler"

ROLE_PICKUP = "pickup"
ROLE_DELIVERY = "delivery"
ROLE_UNKNOWN = "unknown"

EVIDENCE_FACILITY = "facility"
EVIDENCE_ADDRESS = "address"
EVIDENCE_CITY_STATE_ZIP = "city_state_zip"
EVIDENCE_DATE = "date"
EVIDENCE_TIME = "time"
EVIDENCE_APPOINTMENT_WINDOW = "appointment_window"
EVIDENCE_CONTACT = "contact"
EVIDENCE_PHONE = "phone"
EVIDENCE_REFERENCE = "reference"
EVIDENCE_NOTE = "note"
EVIDENCE_UNKNOWN = "unknown"


@dataclass(frozen=True)
class StopEvidence:
    role: str = ROLE_UNKNOWN
    evidence_type: str = EVIDENCE_UNKNOWN
    value: str = ""
    normalized_value: str = ""
    page: int | None = None
    line_index: int | None = None
    bbox: list | None = None
    label: str = ""
    evidence_text: str = ""
    source: str = SOURCE_NATIVE_TEXT
    parser_name: str = ""
    confidence: float = 0.0
    metadata: dict = dataclass_field(default_factory=dict)

    def to_dict(self):
        payload = asdict(self)
        if payload["page"] is None:
            payload["page"] = ""
        if payload["line_index"] is None:
            payload["line_index"] = ""
        return payload


@dataclass(frozen=True)
class StopCandidate:
    role: str
    stop_index: int = 1
    facility: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    date: str = ""
    time: str = ""
    appointment_window: str = ""
    evidence_items: list = dataclass_field(default_factory=list)
    confidence: float = 0.0
    metadata: dict = dataclass_field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def _text(value):
    return str(value or "").strip()


def _safe_float(value):
    try:
        return max(0.0, min(float(value or 0.0), 1.0))
    except (TypeError, ValueError):
        return 0.0


def _safe_int_or_none(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _artifact_line_rows(artifact):
    rows = []
    for page_number, page_rows in artifact_page_lines_with_context(artifact or {}):
        for row in page_rows:
            rows.append(
                {
                    "page_number": page_number,
                    "line_index": row.get("line_index"),
                    "section_context": row.get("section_context", SECTION_UNKNOWN),
                    "text": row.get("text", ""),
                }
            )
    return rows


def _infer_line_context(candidate, artifact):
    page = _safe_int_or_none((candidate or {}).get("page"))
    evidence = _text((candidate or {}).get("evidence_text"))
    value = _candidate_value(candidate)
    needles = [needle for needle in [evidence, value] if needle]
    if not needles:
        return None, SECTION_UNKNOWN
    for row in _artifact_line_rows(artifact):
        if page is not None and row.get("page_number") != page:
            continue
        line = _text(row.get("text"))
        if any(needle and needle in line for needle in needles):
            return _safe_int_or_none(row.get("line_index")), row.get("section_context", SECTION_UNKNOWN)
    return None, SECTION_UNKNOWN


def _candidate_value(candidate):
    return _text((candidate or {}).get("normalized_value") or (candidate or {}).get("value"))


def _role_from_candidate(candidate):
    candidate = candidate or {}
    field_name = _text(candidate.get("field")).lower()
    metadata = candidate.get("metadata") or {}
    raw_field = _text(metadata.get("raw_field")).lower()
    hint = _text(metadata.get("stop_type_hint")).lower()
    combined = " ".join([field_name, raw_field, hint, _text(candidate.get("label")).lower()])
    if hint in {ROLE_PICKUP, ROLE_DELIVERY}:
        return hint
    if any(token in combined for token in ["pickup", "pick_up", "shipper", "origin", "pu_"]):
        return ROLE_PICKUP
    if any(token in combined for token in ["delivery", "deliver", "consignee", "destination", "drop", "del_"]):
        return ROLE_DELIVERY
    return ROLE_UNKNOWN


def _looks_like_phone(text):
    digits = [char for char in _text(text) if char.isdigit()]
    return len(digits) >= 10 and bool(re.search(r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}", _text(text)))


def _looks_like_time(text):
    value = _text(text).lower()
    return bool(
        re.search(r"\b\d{1,2}:\d{2}\s*(?:am|pm)?\b", value)
        or re.search(r"\b(?:am|pm)\b", value)
        or re.search(r"\b\d{3,4}\b", value)
    )


def _looks_like_window(text):
    value = _text(text).lower()
    return _looks_like_time(value) and any(token in value for token in ["-", " to ", "window", "appt", "appointment"])


def _looks_like_city_state_zip(text):
    value = _text(text)
    return bool(
        re.search(r"\b[A-Z]{2}\s+\d{5}(?:-\d{4})?\b", value)
        or re.search(r",\s*[A-Z]{2}\b", value)
    )


def _looks_like_street_address(text):
    value = _text(text).lower()
    return bool(
        re.match(r"^\d+\s+\S+", value)
        and any(
            suffix in value
            for suffix in [
                " st",
                " street",
                " ave",
                " avenue",
                " rd",
                " road",
                " dr",
                " drive",
                " ln",
                " lane",
                " blvd",
                " way",
                " hwy",
                " highway",
            ]
        )
    )


def classify_stop_value_shape(value):
    text = _text(value)
    shape = value_shape(text)
    if not text:
        return EVIDENCE_UNKNOWN
    if _looks_like_phone(text):
        return EVIDENCE_PHONE
    if shape.get("looks_like_date"):
        return EVIDENCE_DATE
    if _looks_like_street_address(text):
        return EVIDENCE_ADDRESS
    if _looks_like_city_state_zip(text):
        return EVIDENCE_CITY_STATE_ZIP
    if _looks_like_window(text):
        return EVIDENCE_APPOINTMENT_WINDOW
    if _looks_like_time(text):
        return EVIDENCE_TIME
    if len(text) > 3:
        return EVIDENCE_FACILITY
    return EVIDENCE_UNKNOWN


def _evidence_type_from_candidate(candidate):
    candidate = candidate or {}
    field_name = _text(candidate.get("field")).lower()
    metadata = candidate.get("metadata") or {}
    raw_field = _text(metadata.get("raw_field")).lower()
    label = _text(candidate.get("label")).lower()
    combined = " ".join([field_name, raw_field, label])
    if field_name in {FIELD_PICKUP_DATE, FIELD_DELIVERY_DATE} or "date" in combined:
        return EVIDENCE_DATE
    if "appointment" in combined or "appt" in combined or "window" in combined:
        return EVIDENCE_APPOINTMENT_WINDOW
    if field_name in {FIELD_PICKUP_TIME, FIELD_DELIVERY_TIME} or "time" in combined:
        return EVIDENCE_TIME
    if "address" in combined:
        return EVIDENCE_ADDRESS
    if "city" in combined or "state" in combined or "zip" in combined:
        return EVIDENCE_CITY_STATE_ZIP
    if field_name in {FIELD_PICKUP_LOCATION, FIELD_DELIVERY_LOCATION} or any(
        token in combined
        for token in ["location", "shipper", "origin", "consignee", "destination"]
    ):
        return classify_stop_value_shape(_candidate_value(candidate))
    return EVIDENCE_UNKNOWN


def _is_stop_evidence_candidate(candidate):
    candidate = candidate if isinstance(candidate, dict) else {}
    metadata = candidate.get("metadata") or {}
    if metadata.get("diagnostic_fallback") or metadata.get("not_independent_candidate"):
        return False
    field_name = _text(candidate.get("field"))
    if field_name in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}:
        return False
    if metadata.get("structured_stop_candidate") or metadata.get("stop_candidate_kind") in {
        "count",
        "partial_count",
    }:
        return False
    raw_field = _text(metadata.get("raw_field"))
    tokens = " ".join([field_name, raw_field, _text(candidate.get("label"))]).lower()
    if field_name in {
        FIELD_PICKUP_LOCATION,
        FIELD_PICKUP_DATE,
        FIELD_PICKUP_TIME,
        FIELD_DELIVERY_LOCATION,
        FIELD_DELIVERY_DATE,
        FIELD_DELIVERY_TIME,
    }:
        return True
    return any(
        token in tokens
        for token in [
            "pickup",
            "delivery",
            "shipper",
            "origin",
            "consignee",
            "destination",
            "appointment",
            "appt",
        ]
    )


def extract_stop_evidence_from_candidates(candidates, artifact=None, triage=None):
    evidence_items = []
    for candidate in candidates or []:
        if not _is_stop_evidence_candidate(candidate):
            continue
        value = _candidate_value(candidate)
        if not value:
            continue
        role = _role_from_candidate(candidate)
        evidence_type = _evidence_type_from_candidate(candidate)
        metadata = dict(candidate.get("metadata") or {})
        line_index = _safe_int_or_none(metadata.get("line_index"))
        section_context = _text(metadata.get("section_context")) or SECTION_UNKNOWN
        if line_index is None or section_context == SECTION_UNKNOWN:
            inferred_index, inferred_context = _infer_line_context(candidate, artifact)
            if line_index is None:
                line_index = inferred_index
            if section_context == SECTION_UNKNOWN and inferred_context:
                section_context = inferred_context
        metadata["source_field"] = _text(candidate.get("field"))
        metadata["source_generator_name"] = _text(metadata.get("generator_name"))
        metadata["section_context"] = section_context
        evidence_items.append(
            StopEvidence(
                role=role,
                evidence_type=evidence_type,
                value=value,
                normalized_value=value,
                page=_safe_int_or_none(candidate.get("page")),
                line_index=line_index,
                bbox=candidate.get("bbox") if isinstance(candidate.get("bbox"), list) else None,
                label=_text(candidate.get("label")),
                evidence_text=_text(candidate.get("evidence_text")),
                source=_text(candidate.get("source")) or SOURCE_NATIVE_TEXT,
                parser_name=_text(candidate.get("parser_name")),
                confidence=_safe_float(candidate.get("confidence")),
                metadata=metadata,
            ).to_dict()
        )
    return evidence_items


def _first_value(evidence_items, evidence_types):
    for evidence_type in evidence_types:
        for item in evidence_items:
            if item.get("evidence_type") == evidence_type and _text(item.get("value")):
                return _text(item.get("value"))
    return ""


def _page_span(evidence_items):
    pages = sorted(
        {
            int(item.get("page"))
            for item in evidence_items
            if _text(item.get("page")).isdigit()
        }
    )
    return pages


def _source_ref_from_evidence(item, component_type=""):
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    page = item.get("page", "")
    line_index = item.get("line_index", "")
    return {
        "candidate_id": _text(metadata.get("candidate_id")),
        "source": _text(item.get("source")),
        "parser_name": _text(item.get("parser_name")),
        "generator_name": _text(metadata.get("source_generator_name") or metadata.get("generator_name")),
        "page": page,
        "line_index": line_index,
        "bbox": item.get("bbox"),
        "role": item.get("role", ""),
        "stop_index": metadata.get("stop_index") or 1,
        "component_type": component_type or item.get("evidence_type", ""),
        "safety_status": "safe",
        "provenance_status": (
            "complete"
            if page not in {None, ""} and line_index not in {None, ""}
            else "page_line_unavailable_from_source"
        ),
    }


def _component_sources_from_evidence(evidence_items):
    component_sources = defaultdict(list)
    mapping = {
        EVIDENCE_FACILITY: "facility",
        EVIDENCE_ADDRESS: "address",
        EVIDENCE_CITY_STATE_ZIP: "city_state_zip",
        EVIDENCE_DATE: "date",
        EVIDENCE_TIME: "time",
        EVIDENCE_APPOINTMENT_WINDOW: "appointment_window",
    }
    for item in evidence_items or []:
        component = mapping.get(item.get("evidence_type"))
        if component:
            component_sources[component].append(_source_ref_from_evidence(item, component))
    return {key: value for key, value in component_sources.items() if value}


def _is_ambiguous(evidence_items):
    by_type = defaultdict(set)
    for item in evidence_items:
        evidence_type = _text(item.get("evidence_type")) or EVIDENCE_UNKNOWN
        value = _text(item.get("normalized_value") or item.get("value")).lower()
        if value:
            by_type[evidence_type].add(value)
    location_types = {EVIDENCE_FACILITY, EVIDENCE_ADDRESS, EVIDENCE_CITY_STATE_ZIP}
    location_values = set()
    for evidence_type in location_types:
        location_values.update(by_type.get(evidence_type, set()))
    return len(location_values) > 1 or len(by_type.get(EVIDENCE_DATE, set())) > 1


def _confidence(has_location, has_date, has_time, ambiguous):
    if has_location and has_date and has_time:
        score = 0.80
    elif has_location and has_date:
        score = 0.70
    elif has_location or has_date:
        score = 0.50
    else:
        score = 0.40
    if ambiguous:
        score = min(score, 0.60)
    return score


def _stop_candidate_from_evidence(role, evidence_items, proximity_metadata=None):
    location_types = [EVIDENCE_ADDRESS, EVIDENCE_CITY_STATE_ZIP, EVIDENCE_FACILITY]
    time_types = [EVIDENCE_APPOINTMENT_WINDOW, EVIDENCE_TIME]
    has_location = any(item.get("evidence_type") in location_types for item in evidence_items)
    has_date = any(item.get("evidence_type") == EVIDENCE_DATE for item in evidence_items)
    has_time = any(item.get("evidence_type") in time_types for item in evidence_items)
    ambiguous = _is_ambiguous(evidence_items)
    return StopCandidate(
        role=role,
        stop_index=1,
        facility=_first_value(evidence_items, [EVIDENCE_FACILITY]),
        address=_first_value(evidence_items, [EVIDENCE_ADDRESS]),
        city="",
        state="",
        zip="",
        date=_first_value(evidence_items, [EVIDENCE_DATE]),
        time=_first_value(evidence_items, [EVIDENCE_TIME]),
        appointment_window=_first_value(evidence_items, [EVIDENCE_APPOINTMENT_WINDOW]),
        evidence_items=[
            {
                "candidate_id": (item.get("metadata") or {}).get("candidate_id", ""),
                "role": item.get("role", ""),
                "evidence_type": item.get("evidence_type", ""),
                "page": item.get("page", ""),
                "line_index": item.get("line_index", ""),
                "bbox": item.get("bbox"),
                "source": item.get("source", ""),
                "parser_name": item.get("parser_name", ""),
                "confidence": item.get("confidence", 0.0),
                "metadata": {
                    "candidate_id": (item.get("metadata") or {}).get("candidate_id", ""),
                    "generator_name": (item.get("metadata") or {}).get("generator_name", ""),
                    "source_generator_name": (item.get("metadata") or {}).get("source_generator_name", ""),
                    "stop_index": (item.get("metadata") or {}).get("stop_index", 1),
                },
            }
            for item in evidence_items
        ],
        confidence=_confidence(has_location, has_date, has_time, ambiguous),
        metadata={
            "assembled_from_partial_evidence": True,
            "evidence_count": len(evidence_items),
            "has_location": has_location,
            "has_date": has_date,
            "has_time": has_time,
            "page_span": _page_span(evidence_items),
            "component_sources": _component_sources_from_evidence(evidence_items),
            "source_lineage": [
                _source_ref_from_evidence(item, item.get("evidence_type", ""))
                for item in evidence_items
            ],
            "partial_only": not (has_location and has_date),
            "ambiguous_stop_candidate": ambiguous,
            **dict(proximity_metadata or {}),
        },
    ).to_dict()


def _field_candidate_for_stop(role, stop_candidate):
    field_name = FIELD_PICKUP_STOPS if role == ROLE_PICKUP else FIELD_DELIVERY_STOPS
    metadata = dict(stop_candidate.get("metadata") or {})
    metadata.update(
        {
            "raw_field": field_name,
            "canonical_field": field_name,
            "canonical_mapping_strength": MAPPING_STRONG,
            "generator_name": GENERATOR_STOP_EVIDENCE_ASSEMBLER,
            "independent_candidate": True,
            "assembled_from_partial_evidence": True,
            "stop_role": role,
            "stop_count": 1,
            "evidence_count": metadata.get("evidence_count", 0),
            "has_location": metadata.get("has_location", False),
            "has_date": metadata.get("has_date", False),
            "has_time": metadata.get("has_time", False),
            "structured_stop_candidate": True,
            "diagnostic_fallback": False,
        }
    )
    summary_bits = [
        f"{role}_stop",
        f"evidence_count={metadata.get('evidence_count', 0)}",
        f"has_location={bool(metadata.get('has_location'))}",
        f"has_date={bool(metadata.get('has_date'))}",
        f"has_time={bool(metadata.get('has_time'))}",
    ]
    return {
        "field": field_name,
        "value": [stop_candidate],
        "normalized_value": f"{role}_stop_assembled",
        "label": f"{role}_stop_assembled",
        "evidence_text": "; ".join(summary_bits),
        "page": (metadata.get("page_span") or [""])[0] if metadata.get("page_span") else "",
        "bbox": None,
        "source": GENERATOR_STOP_EVIDENCE_ASSEMBLER,
        "parser_name": GENERATOR_STOP_EVIDENCE_ASSEMBLER,
        "confidence": stop_candidate.get("confidence", 0.0),
        "metadata": metadata,
    }


def _has_line_index(item):
    return _text((item or {}).get("line_index")).isdigit()


def _cluster_by_proximity(evidence_items, max_line_distance=6):
    if not any(_has_line_index(item) for item in evidence_items):
        return [evidence_items], {"STOP_PROXIMITY_MISSING_LINE_INDEX": 1}
    reason_counts = Counter()
    with_line = [item for item in evidence_items if _has_line_index(item)]
    without_line = [item for item in evidence_items if not _has_line_index(item)]
    if without_line:
        reason_counts["STOP_PROXIMITY_MISSING_LINE_INDEX"] += len(without_line)
    by_page = defaultdict(list)
    for item in with_line:
        by_page[_text(item.get("page")) or "unknown"].append(item)
    clusters = []
    for _page, items in sorted(by_page.items()):
        current = []
        previous_index = None
        for item in sorted(items, key=lambda value: int(value.get("line_index"))):
            line_index = int(item.get("line_index"))
            if previous_index is None or line_index - previous_index <= max_line_distance:
                current.append(item)
            else:
                clusters.append(current)
                current = [item]
            previous_index = line_index
        if current:
            clusters.append(current)
    if without_line and not clusters:
        clusters.append(without_line)
    elif without_line:
        clusters.extend([[item] for item in without_line])
    return clusters, dict(reason_counts)


def _cluster_metadata(cluster, ambiguity_reasons):
    location_types = {EVIDENCE_ADDRESS, EVIDENCE_CITY_STATE_ZIP, EVIDENCE_FACILITY}
    has_location = any(item.get("evidence_type") in location_types for item in cluster)
    has_date = any(item.get("evidence_type") == EVIDENCE_DATE for item in cluster)
    if not has_location or not has_date:
        ambiguity_reasons["STOP_PROXIMITY_CLUSTER_PARTIAL_ONLY"] += 1
    if has_location and not has_date:
        ambiguity_reasons["STOP_PROXIMITY_NO_LOCATION_DATE_PAIR"] += 1
    if has_date and not has_location:
        ambiguity_reasons["STOP_PROXIMITY_NO_LOCATION_DATE_PAIR"] += 1
    return {
        "proximity_cluster": True,
        "proximity_cluster_line_span": [
            min(int(item.get("line_index")) for item in cluster if _has_line_index(item))
            if any(_has_line_index(item) for item in cluster)
            else "",
            max(int(item.get("line_index")) for item in cluster if _has_line_index(item))
            if any(_has_line_index(item) for item in cluster)
            else "",
        ],
    }


def associate_stop_evidence_by_proximity(stop_evidence, artifact=None, triage=None):
    by_role = defaultdict(list)
    for item in stop_evidence or []:
        role = _text((item or {}).get("role")) or ROLE_UNKNOWN
        if role in {ROLE_PICKUP, ROLE_DELIVERY}:
            by_role[role].append(item)

    stop_candidates = []
    summary = {
        "docs_with_proximity_clusters": 0,
        "proximity_cluster_count": 0,
        "ambiguous_cluster_count": 0,
        "clusters_with_location_and_date": 0,
        "clusters_with_location_only": 0,
        "clusters_with_date_only": 0,
        "ambiguity_reason_counts": {},
    }
    ambiguity_reasons = Counter()
    for role in [ROLE_PICKUP, ROLE_DELIVERY]:
        role_items = by_role.get(role, [])
        if not role_items:
            continue
        clusters, cluster_reasons = _cluster_by_proximity(role_items)
        ambiguity_reasons.update(cluster_reasons)
        if len(clusters) > 1:
            ambiguity_reasons["STOP_PROXIMITY_MULTI_STOP_AMBIGUOUS"] += 1
        for cluster in clusters:
            metadata = _cluster_metadata(cluster, ambiguity_reasons)
            candidate = _stop_candidate_from_evidence(
                role,
                cluster,
                proximity_metadata=metadata,
            )
            stop_candidates.append(candidate)
            summary["proximity_cluster_count"] += 1
            if candidate["metadata"].get("ambiguous_stop_candidate"):
                summary["ambiguous_cluster_count"] += 1
            has_location = bool(candidate["metadata"].get("has_location"))
            has_date = bool(candidate["metadata"].get("has_date"))
            if has_location and has_date:
                summary["clusters_with_location_and_date"] += 1
            elif has_location:
                summary["clusters_with_location_only"] += 1
            elif has_date:
                summary["clusters_with_date_only"] += 1
    summary["docs_with_proximity_clusters"] = 1 if summary["proximity_cluster_count"] else 0
    summary["ambiguity_reason_counts"] = dict(ambiguity_reasons.most_common())
    return stop_candidates, summary


def assemble_stop_candidates(stop_evidence, artifact=None, triage=None):
    stop_candidates, proximity_summary = associate_stop_evidence_by_proximity(
        stop_evidence,
        artifact=artifact,
        triage=triage,
    )
    if not stop_candidates:
        by_role = defaultdict(list)
        for item in stop_evidence or []:
            role = _text((item or {}).get("role")) or ROLE_UNKNOWN
            if role in {ROLE_PICKUP, ROLE_DELIVERY}:
                by_role[role].append(item)
        stop_candidates = []
        for role in [ROLE_PICKUP, ROLE_DELIVERY]:
            evidence_items = by_role.get(role, [])
            if not evidence_items:
                continue
            stop_candidates.append(_stop_candidate_from_evidence(role, evidence_items))
    candidates = []
    for stop_candidate in stop_candidates:
        role = stop_candidate.get("role")
        candidates.append(_field_candidate_for_stop(role, stop_candidate))
    for candidate in candidates:
        metadata = candidate.get("metadata") or {}
        metadata["stop_proximity_summary"] = proximity_summary
        candidate["metadata"] = metadata
    return candidates


def summarize_stop_assembly(stop_evidence, assembled_candidates):
    by_role = Counter()
    by_type = Counter()
    for item in stop_evidence or []:
        by_role[_text((item or {}).get("role")) or ROLE_UNKNOWN] += 1
        by_type[_text((item or {}).get("evidence_type")) or EVIDENCE_UNKNOWN] += 1
    assembled_pickup = 0
    assembled_delivery = 0
    partial = 0
    ambiguous = 0
    proximity_summary = {
        "docs_with_proximity_clusters": 0,
        "proximity_cluster_count": 0,
        "ambiguous_cluster_count": 0,
        "clusters_with_location_and_date": 0,
        "clusters_with_location_only": 0,
        "clusters_with_date_only": 0,
        "ambiguity_reason_counts": {},
    }
    for candidate in assembled_candidates or []:
        metadata = (candidate or {}).get("metadata") or {}
        if candidate.get("field") == FIELD_PICKUP_STOPS:
            assembled_pickup += 1
        if candidate.get("field") == FIELD_DELIVERY_STOPS:
            assembled_delivery += 1
        if metadata.get("partial_only"):
            partial += 1
        if metadata.get("ambiguous_stop_candidate"):
            ambiguous += 1
        candidate_proximity = metadata.get("stop_proximity_summary", {}) or {}
        if candidate_proximity and not proximity_summary["proximity_cluster_count"]:
            proximity_summary = candidate_proximity
    return {
        "stop_evidence_count": len(stop_evidence or []),
        "stop_evidence_by_role": dict(sorted(by_role.items())),
        "stop_evidence_by_type": dict(sorted(by_type.items())),
        "assembled_pickup_stop_candidate_count": assembled_pickup,
        "assembled_delivery_stop_candidate_count": assembled_delivery,
        "partial_stop_candidate_count": partial,
        "ambiguous_stop_candidate_count": ambiguous,
        "stop_proximity_summary": proximity_summary,
    }
