"""JSON-ready Rate Confirmation intake contract helpers."""

from copy import deepcopy


CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"
CONFIDENCE_UNKNOWN = "UNKNOWN"

CONFIDENCE_LEVELS = {
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    CONFIDENCE_UNKNOWN,
}

STATUS_READY_FOR_REVIEW = "READY_FOR_REVIEW"
STATUS_REVIEW_REQUIRED = "REVIEW_REQUIRED"
STATUS_MISSING_FIELDS = "MISSING_FIELDS"

CRITICAL_FIELDS = [
    "document_id",
    "broker_name",
    "load_number",
    "rate",
    "pickup_location",
    "pickup_date",
    "delivery_location",
    "delivery_date",
    "commodity",
    "weight",
]


def value_from(source, key, default=None):
    if isinstance(source, dict):
        return source.get(key, default)

    return getattr(source, key, default)


def text(value):
    return str(value or "").strip()


def json_safe(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    return str(value)


def normalize_confidence(value):
    confidence = text(value).upper().replace(" ", "_").replace("-", "_")
    if confidence in CONFIDENCE_LEVELS:
        return confidence
    return CONFIDENCE_UNKNOWN


def normalize_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        items = deepcopy(value)
    elif isinstance(value, (tuple, set)):
        items = list(value)
    elif isinstance(value, str):
        items = [item.strip() for item in value.split(",")]
    else:
        items = [value]

    normalized = []
    for item in items:
        safe_item = json_safe(item)
        if safe_item not in ["", None]:
            normalized.append(safe_item)

    return normalized


def normalize_dict(value):
    if isinstance(value, dict):
        return json_safe(deepcopy(value))
    return {}


def has_value(value):
    if value is None:
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, dict):
        return any(has_value(item) for item in value.values())

    if isinstance(value, (list, tuple, set)):
        return any(has_value(item) for item in value)

    if isinstance(value, str):
        return bool(value.strip())

    return value != ""


def append_once(values, value):
    if value and value not in values:
        values.append(value)


def build_stop(
    stop_type="",
    sequence=0,
    location="",
    date="",
    time="",
    appointment_window="",
    evidence_refs=None,
):
    return {
        "stop_type": text(stop_type).upper(),
        "sequence": int(sequence or 0),
        "location": text(location),
        "date": text(date),
        "time": text(time),
        "appointment_window": text(appointment_window),
        "evidence_refs": normalize_list(evidence_refs),
    }


def build_reference(
    reference_type="",
    value="",
    source="",
    confidence=CONFIDENCE_UNKNOWN,
    evidence_refs=None,
):
    return {
        "reference_type": text(reference_type).upper(),
        "value": text(value),
        "source": text(source),
        "confidence": normalize_confidence(confidence),
        "evidence_refs": normalize_list(evidence_refs),
    }


def build_money_amount(
    amount="",
    currency="USD",
    amount_type="RATE",
    confidence=CONFIDENCE_UNKNOWN,
    evidence_refs=None,
):
    return {
        "amount": json_safe(amount if amount is not None else ""),
        "currency": text(currency or "USD").upper(),
        "amount_type": text(amount_type or "RATE").upper(),
        "confidence": normalize_confidence(confidence),
        "evidence_refs": normalize_list(evidence_refs),
    }


def build_broker_contact(
    name="",
    phone="",
    email="",
    role="",
    source="",
    confidence=CONFIDENCE_UNKNOWN,
):
    return {
        "name": text(name),
        "phone": text(phone),
        "email": text(email),
        "role": text(role),
        "source": text(source),
        "confidence": normalize_confidence(confidence),
    }


def build_extracted_field_evidence(
    evidence_id="",
    document_id="",
    page="",
    source_method="",
    redacted_context="",
    confidence=CONFIDENCE_UNKNOWN,
):
    return {
        "evidence_id": text(evidence_id),
        "document_id": text(document_id),
        "page": json_safe(page if page is not None else ""),
        "source_method": text(source_method),
        "redacted_context": text(redacted_context),
        "confidence": normalize_confidence(confidence),
    }


def build_field_candidate(
    field_name="",
    candidate_value="",
    normalized_value="",
    confidence=CONFIDENCE_UNKNOWN,
    source_method="",
    evidence_ref="",
    warnings=None,
):
    return {
        "field_name": text(field_name),
        "candidate_value": json_safe(candidate_value),
        "normalized_value": json_safe(
            normalized_value if normalized_value not in [None, ""] else candidate_value
        ),
        "confidence": normalize_confidence(confidence),
        "source_method": text(source_method),
        "evidence_ref": text(evidence_ref),
        "warnings": normalize_list(warnings),
    }


def normalize_stops(source):
    stops = normalize_list(value_from(source, "stops", []))
    if stops:
        return stops

    built_stops = []
    pickup = build_stop(
        stop_type="PICKUP",
        sequence=1,
        location=value_from(source, "pickup_location", ""),
        date=value_from(source, "pickup_date", ""),
        time=value_from(source, "pickup_time", ""),
        appointment_window=value_from(source, "pickup_appointment_window", ""),
        evidence_refs=value_from(source, "pickup_evidence_refs", []),
    )
    delivery = build_stop(
        stop_type="DELIVERY",
        sequence=2,
        location=value_from(source, "delivery_location", ""),
        date=value_from(source, "delivery_date", ""),
        time=value_from(source, "delivery_time", ""),
        appointment_window=value_from(source, "delivery_appointment_window", ""),
        evidence_refs=value_from(source, "delivery_evidence_refs", []),
    )

    if has_value(pickup["location"]) or has_value(pickup["date"]):
        built_stops.append(pickup)

    if has_value(delivery["location"]) or has_value(delivery["date"]):
        built_stops.append(delivery)

    return built_stops


def normalize_references(source):
    references = normalize_list(value_from(source, "references", []))
    if references:
        return references

    built_references = []
    load_number = text(value_from(source, "load_number", ""))
    reference_id = text(value_from(source, "reference_id", ""))

    if load_number:
        built_references.append(
            build_reference(
                reference_type="LOAD_NUMBER",
                value=load_number,
                source="rate_confirmation",
                confidence=value_from(source, "load_number_confidence", CONFIDENCE_UNKNOWN),
            )
        )

    if reference_id and reference_id != load_number:
        built_references.append(
            build_reference(
                reference_type="REFERENCE_ID",
                value=reference_id,
                source="rate_confirmation",
                confidence=value_from(source, "reference_id_confidence", CONFIDENCE_UNKNOWN),
            )
        )

    return built_references


def normalize_rate(source):
    rate = value_from(source, "rate", "")

    if isinstance(rate, dict):
        return {
            "amount": json_safe(rate.get("amount", "")),
            "currency": text(rate.get("currency", "USD") or "USD").upper(),
            "amount_type": text(rate.get("amount_type", "RATE") or "RATE").upper(),
            "confidence": normalize_confidence(rate.get("confidence", CONFIDENCE_UNKNOWN)),
            "evidence_refs": normalize_list(rate.get("evidence_refs", [])),
        }

    return build_money_amount(
        amount=rate,
        currency=value_from(source, "rate_currency", "USD"),
        amount_type="RATE",
        confidence=value_from(source, "rate_confidence", CONFIDENCE_UNKNOWN),
        evidence_refs=value_from(source, "rate_evidence_refs", []),
    )


def field_confidences(source):
    return normalize_dict(value_from(source, "field_confidences", value_from(source, "field_confidence", {})))


def low_confidence_fields(confidences):
    return [
        field_name
        for field_name, confidence in confidences.items()
        if normalize_confidence(confidence) == CONFIDENCE_LOW
    ]


def stops_have(stop_list, stop_type, field_name):
    for stop in stop_list:
        if text(stop.get("stop_type", "")).upper() == stop_type:
            return has_value(stop.get(field_name, ""))
    return False


def computed_field_values(intake):
    return {
        "document_id": intake["document_id"],
        "broker_name": intake["broker_name"],
        "load_number": intake["load_number"],
        "rate": intake["rate"].get("amount", ""),
        "pickup_location": stops_have(intake["stops"], "PICKUP", "location"),
        "pickup_date": stops_have(intake["stops"], "PICKUP", "date"),
        "delivery_location": stops_have(intake["stops"], "DELIVERY", "location"),
        "delivery_date": stops_have(intake["stops"], "DELIVERY", "date"),
        "commodity": intake["commodity"],
        "weight": intake["weight"],
    }


def computed_missing_fields(intake):
    field_values = computed_field_values(intake)
    missing = []

    for field_name in CRITICAL_FIELDS:
        if not has_value(field_values.get(field_name, "")):
            missing.append(field_name)

    return missing


def candidate_conflicts(field_candidates):
    values_by_field = {}

    for candidate in field_candidates:
        field_name = text(candidate.get("field_name", ""))
        normalized_value = json_safe(candidate.get("normalized_value", ""))

        if not field_name or normalized_value in ["", None]:
            continue

        values_by_field.setdefault(field_name, set()).add(str(normalized_value))

    return sorted(
        field_name
        for field_name, values in values_by_field.items()
        if len(values) > 1
    )


def computed_needs_check_fields(intake):
    needs_check = []

    for field_name in low_confidence_fields(intake["field_confidences"]):
        append_once(needs_check, field_name)

    for field_name in candidate_conflicts(intake["field_candidates"]):
        append_once(needs_check, field_name)

    for field_name in normalize_list(intake.get("needs_check_fields", [])):
        append_once(needs_check, field_name)

    return needs_check


def status_from_fields(missing_fields, needs_check_fields):
    if missing_fields:
        return STATUS_MISSING_FIELDS

    if needs_check_fields:
        return STATUS_REVIEW_REQUIRED

    return STATUS_READY_FOR_REVIEW


def build_rate_confirmation_intake(
    source=None,
    document_id="",
    extractor_version="",
    source_method="",
):
    source = source or {}
    resolved_document_id = text(document_id or value_from(source, "document_id", ""))
    references = normalize_references(source)
    load_number = text(
        value_from(source, "load_number", "")
        or value_from(source, "reference_id", "")
    )
    stops = normalize_stops(source)
    confidences = field_confidences(source)

    intake = {
        "document_id": resolved_document_id,
        "broker_name": text(value_from(source, "broker_name", value_from(source, "customer_name", ""))),
        "broker_mc": text(value_from(source, "broker_mc", "")),
        "broker_contacts": normalize_list(value_from(source, "broker_contacts", [])),
        "carrier_info": normalize_dict(value_from(source, "carrier_info", {})),
        "load_number": load_number,
        "references": references,
        "rate": normalize_rate(source),
        "stops": stops,
        "commodity": text(value_from(source, "commodity", "")),
        "weight": json_safe(value_from(source, "weight", "")),
        "equipment": text(value_from(source, "equipment", "")),
        "dimensions": normalize_dict(value_from(source, "dimensions", {})),
        "special_requirements": normalize_list(value_from(source, "special_requirements", [])),
        "accessorial_terms": normalize_list(value_from(source, "accessorial_terms", [])),
        "missing_fields": normalize_list(value_from(source, "missing_fields", [])),
        "needs_check_fields": normalize_list(value_from(source, "needs_check_fields", [])),
        "field_confidences": confidences,
        "evidence_refs": normalize_dict(value_from(source, "evidence_refs", {})),
        "field_candidates": normalize_list(value_from(source, "field_candidates", [])),
        "field_evidence": normalize_list(value_from(source, "field_evidence", [])),
        "parser_version": text(value_from(source, "parser_version", "")),
        "extractor_version": text(extractor_version or value_from(source, "extractor_version", "")),
        "source_method": text(source_method or value_from(source, "source_method", "")),
        "status": "",
        "review_required": False,
        "raw_text_included": False,
        "cases_created": False,
        "cases_linked": False,
    }

    missing_fields = computed_missing_fields(intake)
    for field_name in intake["missing_fields"]:
        append_once(missing_fields, field_name)

    needs_check_fields = computed_needs_check_fields(intake)
    intake["missing_fields"] = missing_fields
    intake["needs_check_fields"] = needs_check_fields
    intake["status"] = status_from_fields(missing_fields, needs_check_fields)
    intake["review_required"] = intake["status"] != STATUS_READY_FOR_REVIEW

    return intake
