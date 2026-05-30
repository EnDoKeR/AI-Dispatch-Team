import re

from app.market_intelligence.intake.parser_confidence import (
    HIGH,
    MEDIUM,
    LOW,
    UNKNOWN,
)


PARSER_OUTPUT_FIELDS = [
    "source_type",
    "source_file_name",
    "broker_name",
    "broker_mc",
    "rate",
    "pickup_location",
    "pickup_date",
    "pickup_time",
    "delivery_location",
    "delivery_date",
    "delivery_time",
    "commodity",
    "weight",
    "reference_id",
    "equipment",
    "special_requirements",
    "field_confidence",
]

LABEL_MAPPINGS = {
    "broker": ("broker_name", HIGH),
    "broker name": ("broker_name", HIGH),
    "bill to": ("broker_name", MEDIUM),
    "customer": ("broker_name", MEDIUM),
    "broker mc": ("broker_mc", HIGH),
    "mc#": ("broker_mc", MEDIUM),
    "mc #": ("broker_mc", MEDIUM),
    "mc": ("broker_mc", MEDIUM),
    "mc number": ("broker_mc", MEDIUM),
    "rate": ("rate", HIGH),
    "total": ("rate", HIGH),
    "total rate": ("rate", HIGH),
    "total carrier pay": ("rate", HIGH),
    "carrier pay": ("rate", MEDIUM),
    "linehaul total": ("rate", MEDIUM),
    "pickup": ("pickup_location", HIGH),
    "pickup location": ("pickup_location", HIGH),
    "pickup date": ("pickup_date", HIGH),
    "pickup time": ("pickup_time", HIGH),
    "pickup window": ("pickup_time", MEDIUM),
    "delivery": ("delivery_location", HIGH),
    "delivery location": ("delivery_location", HIGH),
    "delivery date": ("delivery_date", HIGH),
    "delivery time": ("delivery_time", HIGH),
    "delivery window": ("delivery_time", MEDIUM),
    "commodity": ("commodity", HIGH),
    "weight": ("weight", HIGH),
    "reference": ("reference_id", HIGH),
    "reference #": ("reference_id", HIGH),
    "reference id": ("reference_id", HIGH),
    "ref #": ("reference_id", MEDIUM),
    "load #": ("reference_id", MEDIUM),
    "load number": ("reference_id", MEDIUM),
    "order #": ("reference_id", MEDIUM),
    "shipment #": ("reference_id", MEDIUM),
    "shipment id": ("reference_id", MEDIUM),
    "equipment": ("equipment", HIGH),
}

SPECIAL_REQUIREMENT_LABELS = {
    "special requirements",
    "requirements",
}

RATE_REVIEW_LABELS = {
    "linehaul",
    "fuel",
    "accessorial",
    "accessorials",
    "detention",
    "layover",
    "lumper",
    "tonu",
}


def empty_parser_output():
    return {
        field_name: [] if field_name == "special_requirements" else {}
        if field_name == "field_confidence"
        else ""
        for field_name in PARSER_OUTPUT_FIELDS
    }


def normalize_label(label):
    return re.sub(r"\s+", " ", str(label or "").strip().lower())


def split_label_value(line):
    if ":" not in line:
        return "", ""

    label, value = line.split(":", 1)

    return normalize_label(label), value.strip()


def numeric_value(value):
    text = str(value or "").strip()
    cleaned = re.sub(r"\busd\b", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"[$,\s]", "", cleaned)

    if not cleaned:
        return ""

    if not re.fullmatch(r"\d+(\.\d+)?", cleaned):
        return text

    number = float(cleaned)

    if number.is_integer():
        return int(number)

    return number


def append_special_requirement(output, requirement):
    text = str(requirement or "").strip()

    if text and text not in output["special_requirements"]:
        output["special_requirements"].append(text)


def parse_special_requirements(value):
    return [
        item.strip()
        for item in re.split(r"[,;]", str(value or ""))
        if item.strip()
    ]


def set_field(output, field_name, value, confidence):
    if value in ["", None]:
        return

    if field_name in {"rate", "weight"}:
        normalized_value = numeric_value(value)
    else:
        normalized_value = str(value).strip()

    existing_value = output.get(field_name, "")

    if existing_value not in ["", None] and str(existing_value) != str(normalized_value):
        if field_name == "rate":
            output[field_name] = ""
            append_special_requirement(output, "RATE_NEEDS_REVIEW")
        elif field_name == "reference_id":
            append_special_requirement(output, "REFERENCE_NEEDS_REVIEW")
        elif field_name in {"broker_name", "broker_mc"}:
            append_special_requirement(output, "BROKER_IDENTITY_NEEDS_REVIEW")
        else:
            append_special_requirement(output, f"{field_name.upper()}_NEEDS_REVIEW")

        output["field_confidence"][field_name] = LOW
        output["field_confidence"]["special_requirements"] = LOW
        return

    output[field_name] = normalized_value

    output["field_confidence"][field_name] = confidence


def apply_label_value(output, label, value):
    if label in SPECIAL_REQUIREMENT_LABELS:
        for requirement in parse_special_requirements(value):
            append_special_requirement(output, requirement)

        if output["special_requirements"]:
            output["field_confidence"]["special_requirements"] = HIGH
        return

    if label in RATE_REVIEW_LABELS:
        append_special_requirement(output, "ACCESSORIALS_PRESENT")
        output["field_confidence"].setdefault("rate", UNKNOWN)
        output["field_confidence"].setdefault("special_requirements", MEDIUM)
        return

    mapping = LABEL_MAPPINGS.get(label)

    if not mapping:
        return

    field_name, confidence = mapping
    set_field(output, field_name, value, confidence)


def apply_missing_confidence(output):
    if not output["broker_mc"]:
        output["field_confidence"].setdefault("broker_mc", UNKNOWN)

    if not output["broker_name"]:
        output["field_confidence"].setdefault("broker_name", UNKNOWN)

    if not output["rate"]:
        output["field_confidence"].setdefault("rate", UNKNOWN)

    if not output["commodity"]:
        output["field_confidence"].setdefault("commodity", UNKNOWN)

    if not output["weight"]:
        output["field_confidence"].setdefault("weight", UNKNOWN)


def apply_ambiguous_context(output, text):
    normalized_text = str(text or "").lower()

    if not output["broker_name"] and "company header:" in normalized_text:
        output["field_confidence"]["broker_name"] = LOW
        append_special_requirement(output, "BROKER_IDENTITY_NEEDS_REVIEW")
        output["field_confidence"]["special_requirements"] = LOW

    if any(
        requirement in output["special_requirements"]
        for requirement in ["MULTI_STOP_NEEDS_REVIEW", "STOP_DETAILS_NEED_REVIEW"]
    ):
        if output["pickup_location"]:
            output["field_confidence"]["pickup_location"] = MEDIUM

        if output["delivery_location"]:
            output["field_confidence"]["delivery_location"] = MEDIUM


def parse_pasted_text_to_parser_output(text):
    output = empty_parser_output()
    output["source_type"] = "manual_pasted_text"

    for raw_line in str(text or "").splitlines():
        label, value = split_label_value(raw_line)

        if not label:
            continue

        apply_label_value(output, label, value)

    apply_ambiguous_context(output, text)
    apply_missing_confidence(output)

    return output
