"""RateCon field candidate contracts."""

CANDIDATE_CONFIDENCE_HIGH = "HIGH"
CANDIDATE_CONFIDENCE_MEDIUM = "MEDIUM"
CANDIDATE_CONFIDENCE_LOW = "LOW"
CANDIDATE_CONFIDENCE_UNKNOWN = "UNKNOWN"

CONFIDENCE_LEVELS = (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_MEDIUM,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_UNKNOWN,
)

FIELD_BROKER_NAME = "broker_name"
FIELD_BROKER_MC = "broker_mc"
FIELD_BROKER_CONTACT = "broker_contact"
FIELD_CARRIER_NAME = "carrier_name"
FIELD_LOAD_NUMBER = "load_number"
FIELD_REFERENCE = "reference"
FIELD_RATE = "rate"
FIELD_PICKUP_LOCATION = "pickup_location"
FIELD_PICKUP_DATE = "pickup_date"
FIELD_PICKUP_TIME = "pickup_time"
FIELD_DELIVERY_LOCATION = "delivery_location"
FIELD_DELIVERY_DATE = "delivery_date"
FIELD_DELIVERY_TIME = "delivery_time"
FIELD_EQUIPMENT = "equipment"
FIELD_WEIGHT = "weight"
FIELD_COMMODITY = "commodity"
FIELD_SPECIAL_REQUIREMENT = "special_requirement"
FIELD_ACCESSORIAL_TERM = "accessorial_term"
FIELD_UNKNOWN = "unknown"

CANDIDATE_FIELD_NAMES = (
    FIELD_BROKER_NAME,
    FIELD_BROKER_MC,
    FIELD_BROKER_CONTACT,
    FIELD_CARRIER_NAME,
    FIELD_LOAD_NUMBER,
    FIELD_REFERENCE,
    FIELD_RATE,
    FIELD_PICKUP_LOCATION,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_TIME,
    FIELD_DELIVERY_LOCATION,
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_TIME,
    FIELD_EQUIPMENT,
    FIELD_WEIGHT,
    FIELD_COMMODITY,
    FIELD_SPECIAL_REQUIREMENT,
    FIELD_ACCESSORIAL_TERM,
    FIELD_UNKNOWN,
)

SOURCE_REGEX = "regex"
SOURCE_LABEL_PATTERN = "label_pattern"
SOURCE_SECTION_PATTERN = "section_pattern"
SOURCE_TABLE_PATTERN_FUTURE = "table_pattern_future"
SOURCE_BROKER_TEMPLATE_FUTURE = "broker_template_future"
SOURCE_OCR_FUTURE = "ocr_future"
SOURCE_VISION_FUTURE = "vision_future"
SOURCE_MANUAL_REVIEW = "manual_review"
SOURCE_SYNTHETIC_FIXTURE = "synthetic_fixture"

CANDIDATE_SOURCES = (
    SOURCE_REGEX,
    SOURCE_LABEL_PATTERN,
    SOURCE_SECTION_PATTERN,
    SOURCE_TABLE_PATTERN_FUTURE,
    SOURCE_BROKER_TEMPLATE_FUTURE,
    SOURCE_OCR_FUTURE,
    SOURCE_VISION_FUTURE,
    SOURCE_MANUAL_REVIEW,
    SOURCE_SYNTHETIC_FIXTURE,
)

CANDIDATE_EXTRACTOR_VERSION = "ratecon_candidate_contract_v1"


def normalize_confidence(value):
    text = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")

    if text in CONFIDENCE_LEVELS:
        return text

    return CANDIDATE_CONFIDENCE_UNKNOWN


def normalize_field_name(value):
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")

    if text in CANDIDATE_FIELD_NAMES:
        return text

    return FIELD_UNKNOWN


def normalize_source(value):
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")

    if text in CANDIDATE_SOURCES:
        return text

    return SOURCE_REGEX if not text else text


def normalize_list(value):
    if value is None:
        return []

    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]

    return [
        str(item).strip()
        for item in values
        if str(item).strip()
    ]


def build_field_candidate(
    field_name,
    raw_value="",
    normalized_value="",
    confidence=CANDIDATE_CONFIDENCE_UNKNOWN,
    confidence_reasons=None,
    page_number="",
    line_number="",
    label="",
    context_before="",
    context_after="",
    source=SOURCE_REGEX,
    evidence_ref="",
    warnings=None,
    candidate_id="",
    value_type="",
):
    safe_raw_value = str(raw_value or "").strip()
    safe_normalized = (
        str(normalized_value).strip()
        if normalized_value not in [None, ""]
        else safe_raw_value
    )

    return {
        "candidate_id": str(candidate_id or "").strip(),
        "field_name": normalize_field_name(field_name),
        "raw_value": safe_raw_value,
        "normalized_value": safe_normalized,
        "value_type": str(value_type or "").strip(),
        "confidence": normalize_confidence(confidence),
        "confidence_reasons": normalize_list(confidence_reasons),
        "page_number": page_number if page_number not in [None, ""] else "",
        "line_number": line_number if line_number not in [None, ""] else "",
        "label": str(label or "").strip(),
        "context_before": str(context_before or "").strip(),
        "context_after": str(context_after or "").strip(),
        "source": normalize_source(source),
        "evidence_ref": str(evidence_ref or "").strip(),
        "warnings": normalize_list(warnings),
    }


def build_candidate_extraction_result(
    document_id="",
    artifact_id="",
    candidates=None,
    missing_candidate_fields=None,
    warnings=None,
    extractor_version=CANDIDATE_EXTRACTOR_VERSION,
):
    safe_candidates = [
        candidate
        for candidate in candidates or []
        if isinstance(candidate, dict)
    ]

    return {
        "document_id": str(document_id or "").strip(),
        "artifact_id": str(artifact_id or "").strip(),
        "candidates": safe_candidates,
        "missing_candidate_fields": normalize_list(missing_candidate_fields),
        "warnings": normalize_list(warnings),
        "extractor_version": str(extractor_version or CANDIDATE_EXTRACTOR_VERSION).strip(),
    }
