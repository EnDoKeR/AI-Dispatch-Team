"""OCR/text stop block assembly for shadow RateCon diagnostics.

This module is intentionally dependency-light and profile-gated. It turns OCR
role blocks into structured stop candidates without changing legacy or
production output.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field as dataclass_field
import re

from app.document_ai.field_candidate_provenance import SOURCE_NATIVE_TEXT, SOURCE_OCR
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
)


STOP_CANDIDATE_PROFILE_BASELINE = "baseline"
STOP_CANDIDATE_PROFILE_OCR_BLOCK_ASSEMBLY_V1 = "ocr_block_assembly_v1"
STOP_CANDIDATE_PROFILES = {
    STOP_CANDIDATE_PROFILE_BASELINE,
    STOP_CANDIDATE_PROFILE_OCR_BLOCK_ASSEMBLY_V1,
}

GENERATOR_OCR_STOP_BLOCK_ASSEMBLER = "ocr_stop_block_assembler"

ROLE_PICKUP = "pickup"
ROLE_DELIVERY = "delivery"
ROLE_UNKNOWN = "unknown"

SECTION_STOP = "stop_section"
SECTION_PAYMENT = "payment"
SECTION_INSTRUCTIONS = "instructions"
SECTION_FOOTER = "footer"
SECTION_UNKNOWN = "unknown"

_PICKUP_ROLE_RE = re.compile(
    r"(^|\b)(?:p\s*/?\s*u|pu\s*\d+|pick[-\s]?up|pickup|load\s+at|shipper|"
    r"origin|pickup\s+location|shipper\s+pickup|stop\s*#?\s*\d+\s*pickup)\b",
    re.IGNORECASE,
)
_DELIVERY_ROLE_RE = re.compile(
    r"(^|\b)(?:s\s*/?\s*o|so\s*\d+|drop|delivery|deliver\s+to|consignee|"
    r"destination|delivery\s+location|consignee\s+delivery|"
    r"stop\s*#?\s*\d+\s*(?:drop|delivery))\b",
    re.IGNORECASE,
)
_PAYMENT_SECTION_RE = re.compile(
    r"\b(?:rate|linehaul|carrier\s+pay|total\s+carrier|charges|accessorial|"
    r"quickpay|fuel\s+advance|comcheck)\b",
    re.IGNORECASE,
)
_INSTRUCTION_SECTION_RE = re.compile(
    r"\b(?:special\s+instructions|instructions|terms|conditions|notes|"
    r"requirements)\b",
    re.IGNORECASE,
)
_FOOTER_SECTION_RE = re.compile(
    r"\b(?:signature|signed\s+by|driver\s+signature|carrier\s+signature)\b",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
    r"\s+\d{1,2},?\s+\d{2,4})\b",
    re.IGNORECASE,
)
_TIME_RE = re.compile(
    r"\b(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{3,4}\s*(?:am|pm)?|"
    r"(?:fcfs|appt|appointment))\b",
    re.IGNORECASE,
)
_CITY_STATE_ZIP_RE = re.compile(
    r"^(?P<city>[A-Za-z][A-Za-z .'-]{1,60}?),?\s+"
    r"(?P<state>[A-Z]{2})(?:\s+(?P<zip>\d{5}(?:-\d{4})?))?$"
)
_ADDRESS_RE = re.compile(
    r"^\d+\s+\S+.*\b(?:st|street|ave|avenue|rd|road|dr|drive|ln|lane|"
    r"blvd|way|hwy|highway|pkwy|parkway|ct|court)\b",
    re.IGNORECASE,
)
_LABEL_VALUE_RE = re.compile(
    r"\b(?P<label>name|facility|address|date|expected\s+date|earliest|latest|"
    r"target\s+window|appt|appointment|time|shipping/receiving\s+hours)"
    r"\s*[:#-]\s*(?P<value>.+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class StopEvidenceBlock:
    role: str = ROLE_UNKNOWN
    stop_index: int = 1
    source: str = SOURCE_OCR
    page: int = 1
    start_line_index: int = 0
    end_line_index: int = 0
    line_count: int = 0
    has_role_label: bool = False
    has_location_like_text: bool = False
    has_date_like_text: bool = False
    has_time_like_text: bool = False
    has_address_like_text: bool = False
    section_context: str = SECTION_UNKNOWN
    lines: list = dataclass_field(default_factory=list)
    provenance: dict = dataclass_field(default_factory=dict)

    def to_dict(self):
        payload = asdict(self)
        payload["raw_text_included"] = False
        return payload


def _text(value) -> str:
    return str(value or "").strip()


def _lower(value) -> str:
    return _text(value).lower()


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _line_source(line, page_source="") -> str:
    if isinstance(line, dict):
        return _text(line.get("source")) or _text(page_source) or SOURCE_NATIVE_TEXT
    return _text(page_source) or SOURCE_NATIVE_TEXT


def _line_rows(artifact, source_filter=None):
    rows = []
    allowed_sources = set(source_filter or [])
    for page in (artifact or {}).get("pages", []) or []:
        page_number = _safe_int(page.get("page_number"), len(rows) + 1) or 1
        page_source = _text(page.get("source")) or _text((artifact or {}).get("source"))
        line_items = page.get("lines", []) or []
        if not line_items:
            line_items = [
                {"text": line.strip(), "line_index": index, "source": page_source}
                for index, line in enumerate(str(page.get("text") or "").splitlines())
                if line.strip()
            ]
        for ordinal, line in enumerate(line_items):
            text = _text(line.get("text") if isinstance(line, dict) else line)
            if not text:
                continue
            source = _line_source(line, page_source=page_source)
            if allowed_sources and source not in allowed_sources:
                continue
            line_index = _safe_int(
                line.get("line_index", ordinal) if isinstance(line, dict) else ordinal,
                ordinal,
            )
            rows.append(
                {
                    "page": page_number,
                    "line_index": line_index,
                    "ordinal": ordinal,
                    "text": text,
                    "source": source,
                }
            )
    return rows


def _role_from_line(text):
    if _PICKUP_ROLE_RE.search(_text(text)):
        return ROLE_PICKUP
    if _DELIVERY_ROLE_RE.search(_text(text)):
        return ROLE_DELIVERY
    return ROLE_UNKNOWN


def _stop_index_from_line(text, default=1):
    match = re.search(r"\b(?:stop|pu|so|drop)\s*#?\s*(\d+)\b", _text(text), re.IGNORECASE)
    if match:
        return _safe_int(match.group(1), default)
    return default


def _section_context(text):
    value = _text(text)
    if _PAYMENT_SECTION_RE.search(value):
        return SECTION_PAYMENT
    if _INSTRUCTION_SECTION_RE.search(value):
        return SECTION_INSTRUCTIONS
    if _FOOTER_SECTION_RE.search(value):
        return SECTION_FOOTER
    if _role_from_line(value) in {ROLE_PICKUP, ROLE_DELIVERY}:
        return SECTION_STOP
    return SECTION_UNKNOWN


def _section_should_end_block(context):
    return context in {SECTION_PAYMENT, SECTION_INSTRUCTIONS, SECTION_FOOTER}


def _has_date(text):
    return bool(_DATE_RE.search(_text(text)))


def _has_time(text):
    return bool(_TIME_RE.search(_text(text)))


def _has_address(text):
    return bool(_ADDRESS_RE.search(_text(text)))


def _has_city_state(text):
    return bool(_CITY_STATE_ZIP_RE.search(_text(text)))


def _line_has_location(text):
    value = _text(text)
    if _has_address(value) or _has_city_state(value):
        return True
    label_match = _LABEL_VALUE_RE.search(value)
    if label_match and _lower(label_match.group("label")) in {"name", "facility", "address"}:
        return bool(_text(label_match.group("value")))
    return False


def detect_stop_evidence_blocks_from_artifact(
    artifact,
    source_filter=(SOURCE_OCR,),
    max_block_lines=9,
):
    """Detect role-scoped OCR/native stop blocks without exposing raw values."""

    rows = _line_rows(artifact, source_filter=source_filter)
    blocks = []
    by_page = {}
    for row in rows:
        by_page.setdefault(row["page"], []).append(row)
    for page, page_rows in sorted(by_page.items()):
        ordered = sorted(page_rows, key=lambda item: item["ordinal"])
        index = 0
        while index < len(ordered):
            row = ordered[index]
            role = _role_from_line(row["text"])
            if role not in {ROLE_PICKUP, ROLE_DELIVERY}:
                index += 1
                continue
            collected = [row]
            end_index = index
            for next_index in range(index + 1, min(len(ordered), index + max_block_lines)):
                next_row = ordered[next_index]
                next_context = _section_context(next_row["text"])
                next_role = _role_from_line(next_row["text"])
                if next_role in {ROLE_PICKUP, ROLE_DELIVERY}:
                    break
                if _section_should_end_block(next_context):
                    break
                collected.append(next_row)
                end_index = next_index
            texts = [item["text"] for item in collected]
            blocks.append(
                StopEvidenceBlock(
                    role=role,
                    stop_index=_stop_index_from_line(row["text"], default=1),
                    source=row["source"],
                    page=page,
                    start_line_index=row["line_index"],
                    end_line_index=collected[-1]["line_index"],
                    line_count=len(collected),
                    has_role_label=True,
                    has_location_like_text=any(_line_has_location(text) for text in texts),
                    has_date_like_text=any(_has_date(text) for text in texts),
                    has_time_like_text=any(_has_time(text) for text in texts),
                    has_address_like_text=any(_has_address(text) for text in texts),
                    section_context=SECTION_STOP,
                    lines=texts,
                    provenance={
                        "block_detector": GENERATOR_OCR_STOP_BLOCK_ASSEMBLER,
                        "source": row["source"],
                        "page": page,
                        "start_line_index": row["line_index"],
                        "end_line_index": collected[-1]["line_index"],
                    },
                ).to_dict()
            )
            index = max(end_index + 1, index + 1)
    return blocks


def _clean_value(value):
    return _text(value).strip(" -:\t")


def _extract_labeled_values(lines):
    values = {}
    for line in lines:
        match = _LABEL_VALUE_RE.search(_text(line))
        if not match:
            continue
        label = re.sub(r"\s+", "_", _lower(match.group("label")))
        value = _clean_value(match.group("value"))
        if value and label not in values:
            values[label] = value
    return values


def _extract_date(lines):
    labeled = _extract_labeled_values(lines)
    for key in ["date", "expected_date", "earliest", "latest"]:
        if key in labeled:
            match = _DATE_RE.search(labeled[key])
            if match:
                return match.group(0)
            return labeled[key]
    for line in lines:
        match = _DATE_RE.search(_text(line))
        if match:
            return match.group(0)
    return ""


def _extract_time(lines):
    labeled = _extract_labeled_values(lines)
    for key in ["time", "appt", "appointment", "target_window", "shipping/receiving_hours"]:
        if key in labeled:
            return labeled[key]
    for line in lines:
        value = _text(line)
        if _has_date(value) and not any(token in _lower(value) for token in ["time", "appt", "window", "hours"]):
            continue
        match = _TIME_RE.search(value)
        if match:
            return match.group(0)
    return ""


def _extract_location(lines):
    labeled = _extract_labeled_values(lines)
    facility = labeled.get("name") or labeled.get("facility") or ""
    address = labeled.get("address") or ""
    city = state = zip_code = ""
    for line in lines:
        value = _text(line)
        if not address and _has_address(value):
            address = value
            continue
        match = _CITY_STATE_ZIP_RE.search(value)
        if match:
            city = _clean_value(match.group("city"))
            state = _clean_value(match.group("state"))
            zip_code = _clean_value(match.group("zip"))
            continue
        if not facility and not _role_from_line(value) and not _has_date(value) and not _has_time(value):
            if not any(token in _lower(value) for token in ["ref", "bol", "po", "phone", "contact"]):
                facility = value
    return facility, address, city, state, zip_code


def _location_string(stop):
    return " ".join(
        _text(stop.get(key))
        for key in ["facility", "address", "city", "state", "zip"]
        if _text(stop.get(key))
    )


def _component_completeness(has_location, has_date, has_time):
    return round((int(has_location) + int(has_date) + int(has_time)) / 3.0, 3)


def _confidence(has_location, has_date, has_time):
    if has_location and has_date and has_time:
        return 0.76
    if has_location and has_date:
        return 0.70
    if has_location or has_date:
        return 0.56
    return 0.30


def _structured_stop_from_block(block):
    lines = list(block.get("lines") or [])
    facility, address, city, state, zip_code = _extract_location(lines)
    date = _extract_date(lines)
    time = _extract_time(lines)
    appointment_window = time if any(token in _lower(time) for token in ["-", "to", "window"]) else ""
    if appointment_window:
        time = ""
    return {
        "role": block.get("role") or ROLE_UNKNOWN,
        "stop_index": block.get("stop_index") or 1,
        "facility": facility or None,
        "address": address or None,
        "city": city or None,
        "state": state or None,
        "zip": zip_code or None,
        "date": date or None,
        "time": time or None,
        "appointment_window": appointment_window or None,
        "source_summary": {
            "source": block.get("source") or SOURCE_OCR,
            "parser_name": GENERATOR_OCR_STOP_BLOCK_ASSEMBLER,
            "pairing_method": "ocr_role_block"
            if block.get("source") == SOURCE_OCR
            else "native_role_block",
            "page": block.get("page"),
            "line_span": [block.get("start_line_index"), block.get("end_line_index")],
        },
    }


def _base_metadata(block, stop):
    has_location = bool(_location_string(stop))
    has_date = bool(_text(stop.get("date")))
    has_time = bool(_text(stop.get("time")) or _text(stop.get("appointment_window")))
    source = block.get("source") or SOURCE_OCR
    return {
        "raw_field": FIELD_PICKUP_STOPS if stop["role"] == ROLE_PICKUP else FIELD_DELIVERY_STOPS,
        "canonical_mapping_strength": MAPPING_STRONG,
        "generator_name": GENERATOR_OCR_STOP_BLOCK_ASSEMBLER,
        "source_generator_name": GENERATOR_OCR_STOP_BLOCK_ASSEMBLER,
        "independent_candidate": True,
        "structured_stop_candidate": True,
        "assembled_from_stop_block": True,
        "ocr_candidate": source == SOURCE_OCR,
        "stop_role": stop["role"],
        "stop_count": 1,
        "stop_index": stop.get("stop_index") or 1,
        "has_location": has_location,
        "has_date": has_date,
        "has_time": has_time,
        "has_facility": bool(_text(stop.get("facility"))),
        "has_address": bool(_text(stop.get("address"))),
        "pairing_method": "ocr_role_block" if source == SOURCE_OCR else "native_role_block",
        "section_context": SECTION_STOP,
        "page_span": [block.get("page")],
        "proximity_cluster_line_span": [
            block.get("start_line_index"),
            block.get("end_line_index"),
        ],
        "component_completeness": _component_completeness(has_location, has_date, has_time),
        "review_required": True,
        "partial_only": not (has_location and (has_date or has_time)),
        "partial_stop_candidate": not (has_location and (has_date or has_time)),
        "diagnostic_fallback": False,
        "raw_text_included": False,
    }


def _field_candidate(field, value, label, block, metadata, confidence, component=False):
    payload_metadata = dict(metadata)
    if component:
        payload_metadata["structured_stop_candidate"] = False
        payload_metadata["stop_block_component_candidate"] = True
        payload_metadata["raw_field"] = field
    return {
        "field": field,
        "value": value,
        "normalized_value": value,
        "label": label,
        "evidence_text": (
            f"{label}: stop block component present"
            if component
            else f"{metadata.get('stop_role')}_stop: OCR role block structured evidence present"
        ),
        "page": block.get("page") or "",
        "bbox": None,
        "source": block.get("source") or SOURCE_OCR,
        "parser_name": GENERATOR_OCR_STOP_BLOCK_ASSEMBLER,
        "confidence": confidence,
        "metadata": payload_metadata,
    }


def candidates_from_stop_evidence_blocks(blocks):
    candidates = []
    diagnostics = {
        "block_count": len(blocks or []),
        "blocks_by_role": {},
        "candidates_by_field": {},
        "structured_stop_candidates": 0,
        "component_candidate_count": 0,
        "partial_structured_stop_candidates": 0,
        "raw_text_printed": False,
        "private_values_printed": False,
    }
    by_role = Counter()
    by_field = Counter()
    for block in blocks or []:
        role = block.get("role") or ROLE_UNKNOWN
        if role not in {ROLE_PICKUP, ROLE_DELIVERY}:
            continue
        stop = _structured_stop_from_block(block)
        metadata = _base_metadata(block, stop)
        has_location = metadata["has_location"]
        has_date = metadata["has_date"]
        has_time = metadata["has_time"]
        confidence = _confidence(has_location, has_date, has_time)
        field = FIELD_PICKUP_STOPS if role == ROLE_PICKUP else FIELD_DELIVERY_STOPS
        structured = _field_candidate(
            field,
            [stop],
            f"{role}_stop_block",
            block,
            metadata,
            confidence,
        )
        candidates.append(structured)
        by_role[role] += 1
        by_field[field] += 1
        diagnostics["structured_stop_candidates"] += 1
        if metadata["partial_only"]:
            diagnostics["partial_structured_stop_candidates"] += 1

        location_value = _location_string(stop)
        component_fields = []
        if role == ROLE_PICKUP:
            component_fields = [
                (FIELD_PICKUP_LOCATION, location_value, "pickup_location"),
                (FIELD_PICKUP_DATE, _text(stop.get("date")), "pickup_date"),
                (
                    FIELD_PICKUP_TIME,
                    _text(stop.get("time") or stop.get("appointment_window")),
                    "pickup_time",
                ),
            ]
        else:
            component_fields = [
                (FIELD_DELIVERY_LOCATION, location_value, "delivery_location"),
                (FIELD_DELIVERY_DATE, _text(stop.get("date")), "delivery_date"),
                (
                    FIELD_DELIVERY_TIME,
                    _text(stop.get("time") or stop.get("appointment_window")),
                    "delivery_time",
                ),
            ]
        for component_field, component_value, label in component_fields:
            if not component_value:
                continue
            component = _field_candidate(
                component_field,
                component_value,
                label,
                block,
                metadata,
                min(confidence, 0.64),
                component=True,
            )
            candidates.append(component)
            by_field[component_field] += 1
            diagnostics["component_candidate_count"] += 1
    diagnostics["blocks_by_role"] = dict(sorted(by_role.items()))
    diagnostics["candidates_by_field"] = dict(sorted(by_field.items()))
    return candidates, diagnostics


def generate_ocr_stop_block_candidates(artifact, source_filter=(SOURCE_OCR,)):
    blocks = detect_stop_evidence_blocks_from_artifact(
        artifact,
        source_filter=source_filter,
    )
    candidates, diagnostics = candidates_from_stop_evidence_blocks(blocks)
    diagnostics["detected_block_count"] = len(blocks)
    diagnostics["source_filter"] = list(source_filter or [])
    return candidates, diagnostics
