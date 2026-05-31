"""Provider-line stop span extraction contracts.

The span extractor consumes layout lines/tables before the older raw stop group
path fragments provider evidence into many stop candidates.
"""

import re
from collections import Counter

from app.document_ai.layout_artifacts import normalize_bbox
from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_FIELD_ADDRESS,
    NORMALIZED_STOP_FIELD_APPOINTMENT_WINDOW,
    NORMALIZED_STOP_FIELD_CITY_STATE,
    NORMALIZED_STOP_FIELD_DATE,
    NORMALIZED_STOP_FIELD_FACILITY_NAME,
    NORMALIZED_STOP_FIELD_LOCATION,
    NORMALIZED_STOP_FIELD_NOTES,
    NORMALIZED_STOP_FIELD_REFERENCE,
    NORMALIZED_STOP_FIELD_TIME,
    NORMALIZED_STOP_FIELD_STATUS_CONFLICT,
    NORMALIZED_STOP_FIELD_STATUS_MISSING,
    NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
    build_normalized_stop,
    build_normalized_stop_field,
    build_normalized_stop_set,
    NORMALIZED_STOP_TYPE_DELIVERY,
    NORMALIZED_STOP_TYPE_PICKUP,
    NORMALIZED_STOP_TYPE_STOP,
    NORMALIZED_STOP_TYPE_UNKNOWN,
    NORMALIZED_STOP_TYPES,
)
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_MEDIUM,
    CANDIDATE_CONFIDENCE_UNKNOWN,
    normalize_confidence,
    normalize_list,
)


STOP_SPAN_ANCHOR_TYPE_PICKUP = "pickup"
STOP_SPAN_ANCHOR_TYPE_DELIVERY = "delivery"
STOP_SPAN_ANCHOR_TYPE_STOP = "stop"
STOP_SPAN_ANCHOR_TYPE_SHIPPER = "shipper"
STOP_SPAN_ANCHOR_TYPE_CONSIGNEE = "consignee"
STOP_SPAN_ANCHOR_TYPE_ORIGIN = "origin"
STOP_SPAN_ANCHOR_TYPE_DESTINATION = "destination"
STOP_SPAN_ANCHOR_TYPE_LOAD_AT = "load_at"
STOP_SPAN_ANCHOR_TYPE_DELIVER_TO = "deliver_to"
STOP_SPAN_ANCHOR_TYPE_PU = "pu"
STOP_SPAN_ANCHOR_TYPE_SO = "so"
STOP_SPAN_ANCHOR_TYPE_UNKNOWN = "unknown"

STOP_SPAN_ANCHOR_TYPES = {
    STOP_SPAN_ANCHOR_TYPE_PICKUP,
    STOP_SPAN_ANCHOR_TYPE_DELIVERY,
    STOP_SPAN_ANCHOR_TYPE_STOP,
    STOP_SPAN_ANCHOR_TYPE_SHIPPER,
    STOP_SPAN_ANCHOR_TYPE_CONSIGNEE,
    STOP_SPAN_ANCHOR_TYPE_ORIGIN,
    STOP_SPAN_ANCHOR_TYPE_DESTINATION,
    STOP_SPAN_ANCHOR_TYPE_LOAD_AT,
    STOP_SPAN_ANCHOR_TYPE_DELIVER_TO,
    STOP_SPAN_ANCHOR_TYPE_PU,
    STOP_SPAN_ANCHOR_TYPE_SO,
    STOP_SPAN_ANCHOR_TYPE_UNKNOWN,
}

STOP_SPAN_SOURCE_LAYOUT_LINE = "layout_line"
STOP_SPAN_SOURCE_LAYOUT_TABLE_ROW = "layout_table_row"
STOP_SPAN_SOURCE_LAYOUT_BLOCK = "layout_block"
STOP_SPAN_SOURCE_SYNTHETIC_FIXTURE = "synthetic_fixture"
STOP_SPAN_SOURCE_UNKNOWN = "unknown"

STOP_SPAN_SOURCES = {
    STOP_SPAN_SOURCE_LAYOUT_LINE,
    STOP_SPAN_SOURCE_LAYOUT_TABLE_ROW,
    STOP_SPAN_SOURCE_LAYOUT_BLOCK,
    STOP_SPAN_SOURCE_SYNTHETIC_FIXTURE,
    STOP_SPAN_SOURCE_UNKNOWN,
}

STOP_SPAN_FIELD_FACILITY_NAME = NORMALIZED_STOP_FIELD_FACILITY_NAME
STOP_SPAN_FIELD_ADDRESS = NORMALIZED_STOP_FIELD_ADDRESS
STOP_SPAN_FIELD_CITY_STATE = NORMALIZED_STOP_FIELD_CITY_STATE
STOP_SPAN_FIELD_LOCATION = NORMALIZED_STOP_FIELD_LOCATION
STOP_SPAN_FIELD_DATE = NORMALIZED_STOP_FIELD_DATE
STOP_SPAN_FIELD_TIME = NORMALIZED_STOP_FIELD_TIME
STOP_SPAN_FIELD_APPOINTMENT_WINDOW = NORMALIZED_STOP_FIELD_APPOINTMENT_WINDOW
STOP_SPAN_FIELD_REFERENCE = NORMALIZED_STOP_FIELD_REFERENCE
STOP_SPAN_FIELD_NOTES = NORMALIZED_STOP_FIELD_NOTES

STOP_SPAN_FIELDS = {
    STOP_SPAN_FIELD_FACILITY_NAME,
    STOP_SPAN_FIELD_ADDRESS,
    STOP_SPAN_FIELD_CITY_STATE,
    STOP_SPAN_FIELD_LOCATION,
    STOP_SPAN_FIELD_DATE,
    STOP_SPAN_FIELD_TIME,
    STOP_SPAN_FIELD_APPOINTMENT_WINDOW,
    STOP_SPAN_FIELD_REFERENCE,
    STOP_SPAN_FIELD_NOTES,
}

STOP_SPAN_EXTRACTOR_VERSION = "stop_span_extractor_v1"

LINE_LABEL_PICKUP = "pickup"
LINE_LABEL_DELIVERY = "delivery"
LINE_LABEL_STOP = "stop"
LINE_LABEL_DATE = "date"
LINE_LABEL_TIME = "time"
LINE_LABEL_LOCATION = "location"
LINE_LABEL_REFERENCE = "reference"
LINE_LABEL_RATE = "rate"
LINE_LABEL_NOISE = "noise"
LINE_LABEL_UNKNOWN = "unknown"

NOISE_SECTION_ROLE_TOKENS = {
    "billing",
    "certificate",
    "footer",
    "header",
    "legal",
    "quick_pay",
    "signature",
    "terms",
}

NOISE_TEXT_RE = re.compile(
    r"\b(signature|sign and return|terms|billing|quick\s*pay|page \d+ of \d+|"
    r"agreement|carrier requirements|please sign)\b",
    re.IGNORECASE,
)
DATE_RE = re.compile(
    r"\b(?:\d{4}[/-]\d{1,2}[/-]\d{1,2}|"
    r"\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
    r"\s+\d{1,2},?\s+\d{2,4})\b",
    re.IGNORECASE,
)
TIME_RE = re.compile(
    r"\b(?:\d{1,2}:\d{2}\s*(?:am|pm)?|"
    r"\d{1,2}\s*(?:am|pm)|"
    r"(?:[01]?\d|2[0-3])[0-5]\d|"
    r"fcfs)\b",
    re.IGNORECASE,
)
TIME_WINDOW_LABEL_RE = re.compile(
    r"\b(fcfs|target window|earliest|latest|shipping|receiving|hours|appt|"
    r"appointment|window|by)\b|-|\bto\b",
    re.IGNORECASE,
)
NUMERIC_TIME_RE = re.compile(
    r"\b(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm)|"
    r"(?:[01]?\d|2[0-3])[0-5]\d)\b",
    re.IGNORECASE,
)
REFERENCE_RE = re.compile(r"\b(ref|reference|appt|appointment|po|pickup #|delivery #)\b", re.IGNORECASE)
LOCATION_RE = re.compile(
    r"\b(location|facility|warehouse|shipper|consignee|origin|destination|"
    r"load at|deliver to|pickup site|delivery site)\b",
    re.IGNORECASE,
)
MONEY_RE = re.compile(r"(?:\$|usd|rate|pay|total|amount)", re.IGNORECASE)
BOUNDARY_RE = re.compile(
    r"\b(payment|rate|carrier freight pay|total carrier pay|instructions|remarks|"
    r"comments|billing|signature|please sign|terms|agreement|carrier requirements)\b",
    re.IGNORECASE,
)

PICKUP_LABEL_RE = re.compile(
    r"\b(?:pu(?:\s*#?\s*\d+)?|pickup|pick[- ]?up|load at|shipper|origin|"
    r"shipper pickup|pick ups)\b",
    re.IGNORECASE,
)
DELIVERY_LABEL_RE = re.compile(
    r"\b(?:so(?:\s*#?\s*\d+)?|delivery|deliver to|drop(?:\s*\d+)?|"
    r"consignee|receiver|destination|consignee delivery|deliveries)\b",
    re.IGNORECASE,
)
STOP_LABEL_RE = re.compile(r"\b(?:stop\s*#?\s*\d+|route details|shipment stop)\b", re.IGNORECASE)
EXPLICIT_PICKUP_ANCHOR_RE = re.compile(
    r"^\s*(?:pu(?:\s*#?\s*\d+)?|pickup\b|pick[- ]?up\s+location|"
    r"load at\b|shipper\b|origin\b|shipper pickup\b|pick ups\b)",
    re.IGNORECASE,
)
EXPLICIT_DELIVERY_ANCHOR_RE = re.compile(
    r"^\s*(?:so(?:\s*#?\s*\d+)?|delivery\b(?!\s+(?:date|time))|"
    r"deliver to\b|drop(?:\s*\d+)?\b|consignee\b|receiver\b|destination\b|"
    r"consignee delivery\b|deliveries\b)",
    re.IGNORECASE,
)


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _int_or_empty(value):
    if value in [None, ""]:
        return ""
    try:
        return int(value)
    except (TypeError, ValueError):
        return ""


def _normalize_anchor_type(value):
    token = _token(value)
    return token if token in STOP_SPAN_ANCHOR_TYPES else STOP_SPAN_ANCHOR_TYPE_UNKNOWN


def _normalize_source(value):
    token = _token(value)
    return token if token in STOP_SPAN_SOURCES else STOP_SPAN_SOURCE_UNKNOWN


def _normalize_stop_type(value):
    token = _token(value)
    return token if token in NORMALIZED_STOP_TYPES else NORMALIZED_STOP_TYPE_UNKNOWN


def _normalize_field_name(value):
    token = _token(value)
    return token if token in STOP_SPAN_FIELDS else STOP_SPAN_FIELD_NOTES


def _sorted_counts(counter):
    return {
        key: count
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        if key
    }


def normalize_line_text_for_features(text):
    return re.sub(r"\s+", " ", _text(text)).strip()


def _line_text(line):
    return normalize_line_text_for_features((line or {}).get("text_redacted", ""))


def _line_section_role(line):
    return _token((line or {}).get("section_role", ""))


def detect_line_is_noise(line):
    text = _line_text(line)
    section_role = _line_section_role(line)
    if any(token in section_role for token in NOISE_SECTION_ROLE_TOKENS):
        return True
    return bool(NOISE_TEXT_RE.search(text))


def _line_is_boundary(line):
    text = _line_text(line)
    section_role = _line_section_role(line)
    if any(token in section_role for token in NOISE_SECTION_ROLE_TOKENS):
        return True
    return bool(BOUNDARY_RE.search(text))


def detect_line_has_date(line):
    return bool(DATE_RE.search(_line_text(line)))


def detect_line_has_time(line):
    return bool(TIME_RE.search(_line_text(line)))


def detect_line_has_location_like(line):
    text = _line_text(line)
    if not text:
        return False
    if LOCATION_RE.search(text):
        return True
    return bool(
        len(text.split()) >= 2
        and not detect_line_has_date(line)
        and not detect_line_has_time(line)
        and not MONEY_RE.search(text)
        and not detect_line_is_noise(line)
    )


def detect_line_has_reference_like(line):
    return bool(REFERENCE_RE.search(_line_text(line)))


def classify_line_label_category(line):
    text = _line_text(line)
    categories = []
    if detect_line_is_noise(line):
        categories.append(LINE_LABEL_NOISE)
    if PICKUP_LABEL_RE.search(text):
        categories.append(LINE_LABEL_PICKUP)
    if DELIVERY_LABEL_RE.search(text):
        categories.append(LINE_LABEL_DELIVERY)
    if STOP_LABEL_RE.search(text):
        categories.append(LINE_LABEL_STOP)
    if detect_line_has_date(line):
        categories.append(LINE_LABEL_DATE)
    if detect_line_has_time(line):
        categories.append(LINE_LABEL_TIME)
    if detect_line_has_location_like(line):
        categories.append(LINE_LABEL_LOCATION)
    if detect_line_has_reference_like(line):
        categories.append(LINE_LABEL_REFERENCE)
    if MONEY_RE.search(text):
        categories.append(LINE_LABEL_RATE)
    return categories or [LINE_LABEL_UNKNOWN]


def build_layout_line_features(layout_artifact, classification_result=None, include_safe_text=False):
    features = []
    del classification_result
    for page in (layout_artifact or {}).get("pages", []) or []:
        page_number = int(page.get("page_number") or 0)
        page_roles = normalize_list(page.get("page_roles"))
        for line in page.get("lines", []) or []:
            if not isinstance(line, dict):
                continue
            text = _line_text(line)
            if not text:
                continue
            label_categories = classify_line_label_category(line)
            feature = {
                "page_number": page_number,
                "line_id": _text(line.get("line_id")),
                "reading_order_index": int(line.get("reading_order_index") or 0),
                "bbox": normalize_bbox(line.get("bbox"), page_number=page_number)
                if line.get("bbox")
                else None,
                "section_role": _text(line.get("section_role")),
                "page_role": page_roles[0] if page_roles else "",
                "label_categories": label_categories,
                "has_date": LINE_LABEL_DATE in label_categories,
                "has_time": LINE_LABEL_TIME in label_categories,
                "has_location_like": LINE_LABEL_LOCATION in label_categories,
                "has_reference_like": LINE_LABEL_REFERENCE in label_categories,
                "has_money": LINE_LABEL_RATE in label_categories,
                "is_noise_candidate": LINE_LABEL_NOISE in label_categories,
                "is_boundary_candidate": _line_is_boundary(line),
                "warning_codes": normalize_list(line.get("warning_codes")),
            }
            if include_safe_text:
                feature["safe_text_redacted"] = text
            features.append(feature)
    return sorted(
        features,
        key=lambda item: (
            int(item.get("page_number") or 0),
            int(item.get("reading_order_index") or 0),
            item.get("line_id", ""),
        ),
    )


def classify_anchor_type(line_feature):
    categories = set(normalize_list((line_feature or {}).get("label_categories")))
    if LINE_LABEL_NOISE in categories:
        return STOP_SPAN_ANCHOR_TYPE_UNKNOWN
    text = _text((line_feature or {}).get("safe_text_redacted", ""))
    lower_text = text.lower()

    explicit_pickup = bool(EXPLICIT_PICKUP_ANCHOR_RE.search(text))
    explicit_delivery = bool(EXPLICIT_DELIVERY_ANCHOR_RE.search(text))
    date_time_label_only = bool(
        re.match(
            r"^\s*(?:(?:pu|pickup|pick[- ]?up|delivery|so)\s+)?"
            r"(?:date|time|appt|appointment)\b",
            text,
            re.IGNORECASE,
        )
    )
    reference_label_only = bool(
        re.match(
            r"^\s*(?:(?:pu|pickup|delivery|so)\s+)?"
            r"(?:ref|reference|pickup #|delivery #|appt(?:ointment)?\s+ref)\b",
            text,
            re.IGNORECASE,
        )
    )
    if (date_time_label_only or reference_label_only) and LINE_LABEL_STOP not in categories:
        return STOP_SPAN_ANCHOR_TYPE_UNKNOWN
    if (
        (LINE_LABEL_DATE in categories or LINE_LABEL_TIME in categories)
        and LINE_LABEL_STOP not in categories
        and not explicit_pickup
        and not explicit_delivery
        and "location" not in lower_text
    ):
        return STOP_SPAN_ANCHOR_TYPE_UNKNOWN

    if LINE_LABEL_STOP in categories and "pickup" in lower_text:
        return STOP_SPAN_ANCHOR_TYPE_PICKUP
    if LINE_LABEL_STOP in categories and (
        "drop" in lower_text or "delivery" in lower_text
    ):
        return STOP_SPAN_ANCHOR_TYPE_DELIVERY
    if LINE_LABEL_PICKUP in categories and (explicit_pickup or not text):
        if re.search(r"\bpu\b", lower_text):
            return STOP_SPAN_ANCHOR_TYPE_PU
        if "load at" in lower_text:
            return STOP_SPAN_ANCHOR_TYPE_LOAD_AT
        if "shipper" in lower_text:
            return STOP_SPAN_ANCHOR_TYPE_SHIPPER
        if "origin" in lower_text:
            return STOP_SPAN_ANCHOR_TYPE_ORIGIN
        return STOP_SPAN_ANCHOR_TYPE_PICKUP
    if LINE_LABEL_DELIVERY in categories and (explicit_delivery or not text):
        if re.search(r"\bso\b", lower_text):
            return STOP_SPAN_ANCHOR_TYPE_SO
        if "deliver to" in lower_text:
            return STOP_SPAN_ANCHOR_TYPE_DELIVER_TO
        if "consignee" in lower_text:
            return STOP_SPAN_ANCHOR_TYPE_CONSIGNEE
        if "destination" in lower_text:
            return STOP_SPAN_ANCHOR_TYPE_DESTINATION
        return STOP_SPAN_ANCHOR_TYPE_DELIVERY
    if LINE_LABEL_STOP in categories and "route details" not in lower_text:
        return STOP_SPAN_ANCHOR_TYPE_STOP
    return STOP_SPAN_ANCHOR_TYPE_UNKNOWN


def score_stop_anchor(line_feature):
    categories = set(normalize_list((line_feature or {}).get("label_categories")))
    if LINE_LABEL_NOISE in categories:
        return 0.0
    if LINE_LABEL_PICKUP in categories or LINE_LABEL_DELIVERY in categories:
        return CANDIDATE_CONFIDENCE_HIGH
    if LINE_LABEL_STOP in categories:
        return CANDIDATE_CONFIDENCE_MEDIUM
    return CANDIDATE_CONFIDENCE_LOW if categories else 0.0


def _anchor_stop_type(anchor_type):
    if anchor_type in {
        STOP_SPAN_ANCHOR_TYPE_PICKUP,
        STOP_SPAN_ANCHOR_TYPE_SHIPPER,
        STOP_SPAN_ANCHOR_TYPE_ORIGIN,
        STOP_SPAN_ANCHOR_TYPE_LOAD_AT,
        STOP_SPAN_ANCHOR_TYPE_PU,
    }:
        return NORMALIZED_STOP_TYPE_PICKUP
    if anchor_type in {
        STOP_SPAN_ANCHOR_TYPE_DELIVERY,
        STOP_SPAN_ANCHOR_TYPE_CONSIGNEE,
        STOP_SPAN_ANCHOR_TYPE_DESTINATION,
        STOP_SPAN_ANCHOR_TYPE_DELIVER_TO,
        STOP_SPAN_ANCHOR_TYPE_SO,
    }:
        return NORMALIZED_STOP_TYPE_DELIVERY
    if anchor_type == STOP_SPAN_ANCHOR_TYPE_STOP:
        return NORMALIZED_STOP_TYPE_STOP
    return NORMALIZED_STOP_TYPE_UNKNOWN


def detect_stop_span_anchors(line_features, classification_result=None):
    del classification_result
    anchors = []
    for index, feature in enumerate(line_features or [], start=1):
        if not isinstance(feature, dict) or feature.get("is_noise_candidate"):
            continue
        anchor_type = classify_anchor_type(feature)
        if anchor_type == STOP_SPAN_ANCHOR_TYPE_UNKNOWN:
            continue
        confidence = score_stop_anchor(feature)
        if confidence == CANDIDATE_CONFIDENCE_UNKNOWN:
            continue
        anchor = build_stop_span_anchor(
            anchor_id=f"anchor_{index:03d}",
            anchor_type=anchor_type,
            page_number=feature.get("page_number", 0),
            line_id=feature.get("line_id", ""),
            bbox=feature.get("bbox"),
            label_category=anchor_type,
            confidence=confidence,
            reasons=["line_label_anchor"],
            warning_codes=["ambiguous_generic_stop_anchor"]
            if anchor_type == STOP_SPAN_ANCHOR_TYPE_STOP
            else [],
        )
        anchor["stop_type"] = _anchor_stop_type(anchor_type)
        anchors.append(anchor)
    return anchors


def detect_stop_span_boundaries(line_features):
    return [
        feature
        for feature in line_features or []
        if isinstance(feature, dict) and feature.get("is_boundary_candidate")
    ]


def _feature_sort_key(feature):
    return (
        int((feature or {}).get("page_number") or 0),
        int((feature or {}).get("reading_order_index") or 0),
        (feature or {}).get("line_id", ""),
    )


def _feature_by_line_id(line_features):
    return {
        feature.get("line_id", ""): feature
        for feature in line_features or []
        if isinstance(feature, dict) and feature.get("line_id")
    }


def _sequence_from_anchor_feature(feature):
    text = _text((feature or {}).get("safe_text_redacted", ""))
    match = re.search(r"\b(?:stop\s*#?|pu|so|drop)\s*(\d+)\b", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return ""


def _span_id(anchor, index):
    anchor_id = (anchor or {}).get("anchor_id", "")
    return f"span_{anchor_id}" if anchor_id else f"span_{index:03d}"


def find_span_end(anchor, next_anchor, boundaries, line_features):
    features_by_id = _feature_by_line_id(line_features)
    anchor_feature = features_by_id.get((anchor or {}).get("line_id", ""))
    if not anchor_feature:
        return None

    anchor_key = _feature_sort_key(anchor_feature)
    candidate_end_key = None
    if next_anchor and next_anchor.get("page_number") == anchor.get("page_number"):
        next_feature = features_by_id.get(next_anchor.get("line_id", ""))
        if next_feature:
            candidate_end_key = _feature_sort_key(next_feature)

    for boundary in sorted(boundaries or [], key=_feature_sort_key):
        if boundary.get("page_number") != anchor.get("page_number"):
            continue
        boundary_key = _feature_sort_key(boundary)
        if boundary_key <= anchor_key:
            continue
        if candidate_end_key is None or boundary_key < candidate_end_key:
            candidate_end_key = boundary_key

    if candidate_end_key is None:
        page_features = [
            feature
            for feature in line_features or []
            if feature.get("page_number") == anchor.get("page_number")
        ]
        return max(page_features, key=_feature_sort_key, default=anchor_feature)

    span_features = [
        feature
        for feature in line_features or []
        if feature.get("page_number") == anchor.get("page_number")
        and anchor_key <= _feature_sort_key(feature) < candidate_end_key
    ]
    return max(span_features, key=_feature_sort_key, default=anchor_feature)


def build_stop_spans_from_anchors(line_features, anchors, classification_result=None):
    del classification_result
    ordered_features = sorted(line_features or [], key=_feature_sort_key)
    features_by_id = _feature_by_line_id(ordered_features)
    boundaries = detect_stop_span_boundaries(ordered_features)
    spans = []

    for index, anchor in enumerate(anchors or [], start=1):
        if not isinstance(anchor, dict):
            continue
        anchor_feature = features_by_id.get(anchor.get("line_id", ""))
        if not anchor_feature:
            continue
        next_anchor = None
        for later_anchor in anchors[index:]:
            if later_anchor.get("page_number") == anchor.get("page_number"):
                next_anchor = later_anchor
                break
        end_feature = find_span_end(anchor, next_anchor, boundaries, ordered_features)
        start_key = _feature_sort_key(anchor_feature)
        end_key = _feature_sort_key(end_feature or anchor_feature)
        included = [
            feature
            for feature in ordered_features
            if feature.get("page_number") == anchor.get("page_number")
            and start_key <= _feature_sort_key(feature) <= end_key
            and not feature.get("is_noise_candidate")
            and not (
                feature.get("is_boundary_candidate")
                and feature.get("line_id") != anchor.get("line_id")
            )
        ]
        if not included:
            continue
        line_ids = [feature.get("line_id", "") for feature in included if feature.get("line_id")]
        span = build_stop_span(
            span_id=_span_id(anchor, index),
            anchor=anchor,
            page_number=anchor.get("page_number", 0),
            start_line_id=line_ids[0] if line_ids else "",
            end_line_id=line_ids[-1] if line_ids else "",
            line_ids=line_ids,
            section_role=anchor_feature.get("section_role", ""),
            stop_type=anchor.get("stop_type", NORMALIZED_STOP_TYPE_UNKNOWN),
            sequence=_sequence_from_anchor_feature(anchor_feature),
            confidence=anchor.get("confidence", CANDIDATE_CONFIDENCE_UNKNOWN),
            reasons=["bounded_by_next_anchor_or_section_boundary"],
            warning_codes=anchor.get("warning_codes"),
        )
        spans.append(span)
    return spans


def _layout_lines_by_id(layout_artifact):
    lines = {}
    for page in (layout_artifact or {}).get("pages", []) or []:
        for line in page.get("lines", []) or []:
            if isinstance(line, dict) and line.get("line_id"):
                lines[line.get("line_id")] = line
    return lines


def _feature_map(line_features):
    return {
        feature.get("line_id"): feature
        for feature in line_features or []
        if isinstance(feature, dict) and feature.get("line_id")
    }


def _line_evidence_ref(line, evidence_type="layout_line"):
    return {
        "page_number": int((line or {}).get("page_number") or 0),
        "line_id": _text((line or {}).get("line_id")),
        "evidence_type": evidence_type,
    }


def _table_cell_evidence_ref(cell, row):
    return {
        "page_number": int((row or {}).get("page_number") or 0),
        "table_id": _text((row or {}).get("table_id")),
        "row_index": int((cell or {}).get("row_index") or 0),
        "col_index": int((cell or {}).get("col_index") or 0),
        "evidence_type": "table_cell",
    }


def _candidate(
    span,
    field_name,
    line,
    index,
    confidence=CANDIDATE_CONFIDENCE_MEDIUM,
    reasons=None,
    warning_codes=None,
):
    return build_stop_span_field_candidate(
        span_id=(span or {}).get("span_id", ""),
        field_name=field_name,
        candidate_id=f"{(span or {}).get('span_id', 'span')}_{field_name}_{index:03d}",
        confidence=confidence,
        evidence_ref=_line_evidence_ref(line),
        source=STOP_SPAN_SOURCE_LAYOUT_LINE,
        reasons=reasons or ["inside_stop_span"],
        warning_codes=warning_codes,
    )


def _table_date_candidate(span, row, cell, index):
    return build_stop_span_field_candidate(
        span_id=(span or {}).get("span_id", ""),
        field_name=STOP_SPAN_FIELD_DATE,
        candidate_id=(
            f"{(span or {}).get('span_id', 'span')}_"
            f"{STOP_SPAN_FIELD_DATE}_table_{index:03d}"
        ),
        confidence=CANDIDATE_CONFIDENCE_MEDIUM,
        evidence_ref=_table_cell_evidence_ref(cell, row),
        source=STOP_SPAN_SOURCE_LAYOUT_TABLE_ROW,
        reasons=["date_inside_stop_table_row"],
        warning_codes=["table_row_date_requires_review"],
    )


def _layout_table_rows(layout_artifact):
    rows = []
    for page in (layout_artifact or {}).get("pages", []) or []:
        page_number = int((page or {}).get("page_number") or 0)
        for table in (page or {}).get("tables", []) or []:
            if not isinstance(table, dict):
                continue
            header_rows = {
                int(item)
                for item in (table.get("header_rows") or [])
                if str(item).strip().isdigit()
            }
            grouped = {}
            for cell in table.get("cells", []) or []:
                if not isinstance(cell, dict):
                    continue
                row_index = int(cell.get("row_index") or 0)
                grouped.setdefault(row_index, []).append(cell)
            for row_index, cells in grouped.items():
                rows.append(
                    {
                        "page_number": page_number,
                        "table_id": _text(table.get("table_id")),
                        "row_index": row_index,
                        "is_header_row": row_index in header_rows,
                        "cells": sorted(
                            cells,
                            key=lambda item: int(item.get("col_index") or 0),
                        ),
                    }
                )
    return sorted(
        rows,
        key=lambda item: (
            int(item.get("page_number") or 0),
            item.get("table_id", ""),
            int(item.get("row_index") or 0),
        ),
    )


def _cell_text(cell):
    return normalize_line_text_for_features((cell or {}).get("text_redacted", ""))


def _table_row_text(row):
    return " ".join(_cell_text(cell) for cell in (row or {}).get("cells", []) if _cell_text(cell))


def _table_row_is_stop_date_noise(row_text):
    text = _text(row_text)
    if not text:
        return True
    return bool(
        re.search(
            r"\b(payment|billing|terms|rate confirmation date|invoice|quick\s*pay|"
            r"signature|agreement|carrier requirements)\b",
            text,
            re.IGNORECASE,
        )
    )


def _table_row_matches_span_stop_type(row_text, span):
    stop_type = _normalize_stop_type((span or {}).get("stop_type"))
    text = _text(row_text)
    if stop_type == NORMALIZED_STOP_TYPE_PICKUP:
        return bool(PICKUP_LABEL_RE.search(text))
    if stop_type == NORMALIZED_STOP_TYPE_DELIVERY:
        return bool(DELIVERY_LABEL_RE.search(text))
    if stop_type == NORMALIZED_STOP_TYPE_STOP:
        return bool(STOP_LABEL_RE.search(text))
    return False


def extract_table_date_candidates_for_span(span, layout_artifact, start_index=1):
    candidates = []
    for row in _layout_table_rows(layout_artifact):
        if row.get("is_header_row"):
            continue
        row_text = _table_row_text(row)
        if _table_row_is_stop_date_noise(row_text):
            continue
        if not _table_row_matches_span_stop_type(row_text, span):
            continue
        date_cells = [
            cell
            for cell in (row.get("cells") or [])
            if DATE_RE.search(_cell_text(cell))
        ]
        for offset, cell in enumerate(date_cells, start=len(candidates) + start_index):
            candidates.append(_table_date_candidate(span, row, cell, offset))
    return candidates


def extract_date_candidates_from_span(span, line_features, layout_artifact):
    lines = _layout_lines_by_id(layout_artifact)
    features = _feature_map(line_features)
    candidates = []
    for index, line_id in enumerate((span or {}).get("line_ids", []) or [], start=1):
        line = lines.get(line_id, {})
        feature = features.get(line_id, {})
        if feature.get("is_noise_candidate") or feature.get("is_boundary_candidate"):
            continue
        text = _line_text(line)
        if DATE_RE.search(text):
            candidates.append(
                _candidate(
                    span,
                    STOP_SPAN_FIELD_DATE,
                    line,
                    index,
                    CANDIDATE_CONFIDENCE_HIGH,
                    ["date_inside_stop_span"],
                )
            )
    if candidates:
        return candidates
    candidates.extend(
        extract_table_date_candidates_for_span(
            span,
            layout_artifact,
            start_index=len(candidates) + 1,
        )
    )
    return candidates


def extract_time_candidates_from_span(span, line_features, layout_artifact):
    lines = _layout_lines_by_id(layout_artifact)
    features = _feature_map(line_features)
    candidates = []
    for index, line_id in enumerate((span or {}).get("line_ids", []) or [], start=1):
        line = lines.get(line_id, {})
        feature = features.get(line_id, {})
        if feature.get("is_noise_candidate") or feature.get("is_boundary_candidate"):
            continue
        text = _line_text(line)
        if TIME_RE.search(text):
            field_names = [STOP_SPAN_FIELD_TIME]
            if TIME_WINDOW_LABEL_RE.search(text):
                field_names.append(STOP_SPAN_FIELD_APPOINTMENT_WINDOW)
            if re.search(r"\bfcfs\b", text, re.IGNORECASE) and not NUMERIC_TIME_RE.search(text):
                field_names = [STOP_SPAN_FIELD_APPOINTMENT_WINDOW]
            for field_name in dict.fromkeys(field_names):
                candidates.append(
                    _candidate(
                        span,
                        field_name,
                        line,
                        index,
                        CANDIDATE_CONFIDENCE_HIGH,
                        ["time_inside_stop_span"],
                    )
                )
    return candidates


def extract_reference_candidates_from_span(span, line_features, layout_artifact):
    lines = _layout_lines_by_id(layout_artifact)
    features = _feature_map(line_features)
    candidates = []
    for index, line_id in enumerate((span or {}).get("line_ids", []) or [], start=1):
        line = lines.get(line_id, {})
        feature = features.get(line_id, {})
        if feature.get("is_noise_candidate") or feature.get("is_boundary_candidate"):
            continue
        if detect_line_has_reference_like(line):
            candidates.append(
                _candidate(
                    span,
                    STOP_SPAN_FIELD_REFERENCE,
                    line,
                    index,
                    CANDIDATE_CONFIDENCE_MEDIUM,
                    ["reference_inside_stop_span"],
                )
            )
    return candidates


def extract_location_candidates_from_span(span, line_features, layout_artifact):
    lines = _layout_lines_by_id(layout_artifact)
    features = _feature_map(line_features)
    candidates = []
    for index, line_id in enumerate((span or {}).get("line_ids", []) or [], start=1):
        line = lines.get(line_id, {})
        feature = features.get(line_id, {})
        if feature.get("is_noise_candidate") or feature.get("is_boundary_candidate"):
            continue
        if line_id == ((span or {}).get("anchor") or {}).get("line_id") and len(span.get("line_ids", [])) > 1:
            continue
        text = _line_text(line)
        if not text or DATE_RE.search(text) or TIME_RE.search(text) or MONEY_RE.search(text):
            continue
        if detect_line_has_location_like(line):
            candidates.append(
                _candidate(
                    span,
                    STOP_SPAN_FIELD_LOCATION,
                    line,
                    index,
                    CANDIDATE_CONFIDENCE_HIGH,
                    ["location_inside_stop_span"],
                )
            )
    return candidates


def extract_notes_candidates_from_span(span, line_features, layout_artifact):
    lines = _layout_lines_by_id(layout_artifact)
    features = _feature_map(line_features)
    candidates = []
    for index, line_id in enumerate((span or {}).get("line_ids", []) or [], start=1):
        line = lines.get(line_id, {})
        feature = features.get(line_id, {})
        if feature.get("is_noise_candidate") or feature.get("is_boundary_candidate"):
            continue
        text = _line_text(line)
        if re.search(r"\b(note|notes|hours|receiving|shipping)\b", text, re.IGNORECASE):
            candidates.append(
                _candidate(
                    span,
                    STOP_SPAN_FIELD_NOTES,
                    line,
                    index,
                    CANDIDATE_CONFIDENCE_LOW,
                    ["notes_inside_stop_span"],
                )
            )
    return candidates


def extract_stop_span_field_candidates(span, line_features, layout_artifact):
    candidates = []
    candidates.extend(extract_location_candidates_from_span(span, line_features, layout_artifact))
    candidates.extend(extract_date_candidates_from_span(span, line_features, layout_artifact))
    candidates.extend(extract_time_candidates_from_span(span, line_features, layout_artifact))
    candidates.extend(extract_reference_candidates_from_span(span, line_features, layout_artifact))
    candidates.extend(extract_notes_candidates_from_span(span, line_features, layout_artifact))
    return candidates


def _field_status_for_candidates(candidates):
    if not candidates:
        return NORMALIZED_STOP_FIELD_STATUS_MISSING
    if len(candidates) > 1:
        return NORMALIZED_STOP_FIELD_STATUS_CONFLICT
    return NORMALIZED_STOP_FIELD_STATUS_RESOLVED


def _build_stop_field_from_span_candidates(field_name, candidates):
    status = _field_status_for_candidates(candidates)
    selected_candidate_id = candidates[0].get("candidate_id", "") if candidates else ""
    evidence_refs = [
        candidate.get("evidence_ref", {})
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("evidence_ref"), dict)
    ]
    warning_codes = []
    if status == NORMALIZED_STOP_FIELD_STATUS_CONFLICT:
        warning_codes.append(f"conflicting_span_{field_name}")
    return build_normalized_stop_field(
        field_name=field_name,
        status=status,
        selected_candidate_id=selected_candidate_id,
        confidence=candidates[0].get("confidence", CANDIDATE_CONFIDENCE_UNKNOWN)
        if candidates
        else CANDIDATE_CONFIDENCE_UNKNOWN,
        evidence_refs=evidence_refs,
        reasons=["built_from_stop_span"],
        warning_codes=warning_codes,
    )


def _candidate_map_for_span(field_candidates, span_id):
    mapped = {}
    for candidate in field_candidates or []:
        if not isinstance(candidate, dict) or candidate.get("span_id") != span_id:
            continue
        mapped.setdefault(candidate.get("field_name", STOP_SPAN_FIELD_NOTES), []).append(candidate)
    return mapped


def _span_review_required(stop_type, fields, span):
    if stop_type == NORMALIZED_STOP_TYPE_UNKNOWN:
        return True
    if (span or {}).get("warning_codes"):
        return True
    return any(
        field.get("status")
        in {
            NORMALIZED_STOP_FIELD_STATUS_MISSING,
            NORMALIZED_STOP_FIELD_STATUS_CONFLICT,
        }
        for field in fields
    )


def build_normalized_stop_set_from_spans(span_result, classification_result=None):
    del classification_result
    field_candidates = (span_result or {}).get("field_candidates", []) or []
    normalized_stops = []
    required_fields = [
        STOP_SPAN_FIELD_LOCATION,
        STOP_SPAN_FIELD_DATE,
        STOP_SPAN_FIELD_TIME,
        STOP_SPAN_FIELD_APPOINTMENT_WINDOW,
        STOP_SPAN_FIELD_REFERENCE,
        STOP_SPAN_FIELD_NOTES,
    ]
    for index, span in enumerate((span_result or {}).get("spans", []) or [], start=1):
        if not isinstance(span, dict):
            continue
        by_field = _candidate_map_for_span(field_candidates, span.get("span_id", ""))
        fields = [
            _build_stop_field_from_span_candidates(field_name, by_field.get(field_name, []))
            for field_name in required_fields
        ]
        stop_type = span.get("stop_type", NORMALIZED_STOP_TYPE_UNKNOWN)
        stop = build_normalized_stop(
            stop_id=f"span_stop_{index:03d}",
            sequence=span.get("sequence"),
            stop_type=stop_type,
            source_group_ids=[span.get("span_id", "")],
            page_numbers=[span.get("page_number", 0)],
            section_roles=[span.get("section_role", "")],
            table_ids=[span.get("table_id", "")],
            row_indices=span.get("row_indices", []),
            fields=fields,
            confidence=span.get("confidence", CANDIDATE_CONFIDENCE_UNKNOWN),
            reasons=["normalized_from_stop_span"],
            warning_codes=span.get("warning_codes", []),
            review_required=_span_review_required(stop_type, fields, span),
        )
        normalized_stops.append(stop)
    return build_normalized_stop_set(
        document_alias=(span_result or {}).get("document_alias", ""),
        stops=normalized_stops,
        warning_codes=(span_result or {}).get("warning_codes", []),
    )


def build_stop_span_coverage_metrics(
    line_features=None,
    anchors=None,
    spans=None,
    field_candidates=None,
    normalized_stop_set=None,
    core_field_statuses=None,
    review_rows_by_field=None,
):
    label_counts = Counter()
    for feature in line_features or []:
        for label in normalize_list((feature or {}).get("label_categories")):
            label_counts[_token(label)] += 1

    anchor_counts = Counter(
        _normalize_anchor_type((anchor or {}).get("anchor_type"))
        for anchor in anchors or []
        if isinstance(anchor, dict)
    )
    span_counts = Counter(
        _normalize_stop_type((span or {}).get("stop_type"))
        for span in spans or []
        if isinstance(span, dict)
    )
    candidate_counts = Counter(
        _normalize_field_name((candidate or {}).get("field_name"))
        for candidate in field_candidates or []
        if isinstance(candidate, dict)
    )
    normalized_counts = Counter()
    normalized_status_counts = {}
    for stop in (normalized_stop_set or {}).get("stops", []) or []:
        if not isinstance(stop, dict):
            continue
        for field in stop.get("fields", []) or []:
            if not isinstance(field, dict):
                continue
            field_name = _token(field.get("field_name"))
            status = _token(field.get("status"))
            if not field_name:
                continue
            normalized_status_counts.setdefault(field_name, Counter())[status] += 1
            if status and status != NORMALIZED_STOP_FIELD_STATUS_MISSING:
                normalized_counts[field_name] += 1

    core_counts = Counter()
    for field in core_field_statuses or []:
        if not isinstance(field, dict):
            continue
        field_name = _token(field.get("field_name"))
        status = _token(field.get("status"))
        if field_name and status and status != NORMALIZED_STOP_FIELD_STATUS_MISSING:
            core_counts[field_name] += 1

    return {
        "line_feature_count_by_label_category": _sorted_counts(label_counts),
        "anchor_count_by_type": _sorted_counts(anchor_counts),
        "span_count_by_type": _sorted_counts(span_counts),
        "span_field_candidate_count_by_field": _sorted_counts(candidate_counts),
        "normalized_stop_field_count_by_field": _sorted_counts(normalized_counts),
        "normalized_stop_field_status_count_by_field": {
            field_name: _sorted_counts(counts)
            for field_name, counts in sorted(normalized_status_counts.items())
        },
        "core_field_mapping_count_by_field": _sorted_counts(core_counts),
        "review_row_count_by_field": _sorted_counts(Counter(review_rows_by_field or {})),
        "private_values_included": False,
        "raw_text_included": False,
    }


def extract_stop_spans_from_layout_artifact(
    layout_artifact,
    classification_result=None,
    document_alias="",
):
    line_features = build_layout_line_features(
        layout_artifact,
        classification_result=classification_result,
        include_safe_text=True,
    )
    anchors = detect_stop_span_anchors(
        line_features,
        classification_result=classification_result,
    )
    spans = build_stop_spans_from_anchors(
        line_features,
        anchors,
        classification_result=classification_result,
    )
    field_candidates = []
    for span in spans:
        field_candidates.extend(
            extract_stop_span_field_candidates(span, line_features, layout_artifact)
        )
    return build_stop_span_extraction_result(
        document_alias=document_alias,
        anchors=anchors,
        spans=spans,
        field_candidates=field_candidates,
        raw_line_count=len(line_features),
        coverage_metrics=build_stop_span_coverage_metrics(
            line_features=line_features,
            anchors=anchors,
            spans=spans,
            field_candidates=field_candidates,
        ),
    )


def build_stop_span_anchor(
    anchor_id="",
    anchor_type=STOP_SPAN_ANCHOR_TYPE_UNKNOWN,
    page_number=0,
    line_id="",
    block_id="",
    table_id="",
    row_index=None,
    bbox=None,
    label_category="unknown",
    confidence=CANDIDATE_CONFIDENCE_UNKNOWN,
    reasons=None,
    warning_codes=None,
):
    return {
        "anchor_id": _text(anchor_id),
        "anchor_type": _normalize_anchor_type(anchor_type),
        "page_number": int(page_number or 0),
        "line_id": _text(line_id),
        "block_id": _text(block_id),
        "table_id": _text(table_id),
        "row_index": _int_or_empty(row_index),
        "bbox": normalize_bbox(bbox, page_number=page_number) if bbox else None,
        "label_category": _text(label_category) or STOP_SPAN_ANCHOR_TYPE_UNKNOWN,
        "confidence": normalize_confidence(confidence),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
    }


def build_stop_span(
    span_id="",
    anchor=None,
    page_number=0,
    start_line_id="",
    end_line_id="",
    line_ids=None,
    table_id="",
    row_indices=None,
    section_role="",
    stop_type=NORMALIZED_STOP_TYPE_UNKNOWN,
    sequence=None,
    confidence=CANDIDATE_CONFIDENCE_UNKNOWN,
    reasons=None,
    warning_codes=None,
):
    return {
        "span_id": _text(span_id),
        "anchor": anchor if isinstance(anchor, dict) else {},
        "page_number": int(page_number or 0),
        "start_line_id": _text(start_line_id),
        "end_line_id": _text(end_line_id),
        "line_ids": normalize_list(line_ids),
        "table_id": _text(table_id),
        "row_indices": [
            int(row)
            for row in row_indices or []
            if str(row).strip() and str(row).strip().lstrip("-").isdigit()
        ],
        "section_role": _text(section_role),
        "stop_type": _normalize_stop_type(stop_type),
        "sequence": sequence if sequence not in [None, ""] else "",
        "confidence": normalize_confidence(confidence),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
    }


def build_stop_span_field_candidate(
    span_id="",
    field_name=STOP_SPAN_FIELD_NOTES,
    candidate_id="",
    confidence=CANDIDATE_CONFIDENCE_UNKNOWN,
    evidence_ref=None,
    source=STOP_SPAN_SOURCE_UNKNOWN,
    reasons=None,
    warning_codes=None,
):
    return {
        "span_id": _text(span_id),
        "field_name": _normalize_field_name(field_name),
        "candidate_id": _text(candidate_id),
        "confidence": normalize_confidence(confidence),
        "evidence_ref": evidence_ref if isinstance(evidence_ref, dict) else {},
        "source": _normalize_source(source),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
    }


def build_stop_span_extraction_result(
    document_alias="",
    anchors=None,
    spans=None,
    field_candidates=None,
    raw_line_count=0,
    coverage_metrics=None,
    warning_codes=None,
):
    safe_anchors = [anchor for anchor in anchors or [] if isinstance(anchor, dict)]
    safe_spans = [span for span in spans or [] if isinstance(span, dict)]
    safe_fields = [
        candidate
        for candidate in field_candidates or []
        if isinstance(candidate, dict)
    ]
    raw_count = int(raw_line_count or 0)
    span_count = len(safe_spans)

    return {
        "document_alias": _text(document_alias),
        "anchors": safe_anchors,
        "spans": safe_spans,
        "field_candidates": safe_fields,
        "raw_line_count": raw_count,
        "anchor_count": len(safe_anchors),
        "span_count": span_count,
        "passthrough_detected": bool(span_count and raw_count and span_count >= raw_count),
        "coverage_metrics": coverage_metrics if isinstance(coverage_metrics, dict) else {},
        "warning_codes": normalize_list(warning_codes),
        "extractor_version": STOP_SPAN_EXTRACTOR_VERSION,
        "raw_text_included": False,
        "private_values_redacted": True,
    }
