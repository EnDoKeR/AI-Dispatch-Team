"""Typed load identifier candidate helpers for RateCon extraction."""

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_MEDIUM,
    CANDIDATE_CONFIDENCE_UNKNOWN,
    FIELD_LOAD_NUMBER,
    FIELD_REFERENCE,
    SOURCE_LABEL_PATTERN,
    build_field_candidate,
    normalize_confidence,
    normalize_list,
)


LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER = "broker_load_number"
LOAD_IDENTIFIER_TYPE_ORDER_NUMBER = "order_number"
LOAD_IDENTIFIER_TYPE_TENDER_ID = "tender_id"
LOAD_IDENTIFIER_TYPE_PRO_NUMBER = "pro_number"
LOAD_IDENTIFIER_TYPE_SHIPMENT_NUMBER = "shipment_number"
LOAD_IDENTIFIER_TYPE_FREIGHT_BILL_NUMBER = "freight_bill_number"
LOAD_IDENTIFIER_TYPE_TRIP_NUMBER = "trip_number"
LOAD_IDENTIFIER_TYPE_DISPATCH_NUMBER = "dispatch_number"
LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE = "primary_reference"
LOAD_IDENTIFIER_TYPE_PO_NUMBER = "po_number"
LOAD_IDENTIFIER_TYPE_BOL_NUMBER = "bol_number"
LOAD_IDENTIFIER_TYPE_PICKUP_NUMBER = "pickup_number"
LOAD_IDENTIFIER_TYPE_DELIVERY_NUMBER = "delivery_number"
LOAD_IDENTIFIER_TYPE_PICKUP_CONFIRMATION = "pickup_confirmation"
LOAD_IDENTIFIER_TYPE_DELIVERY_CONFIRMATION = "delivery_confirmation"
LOAD_IDENTIFIER_TYPE_APPOINTMENT_NUMBER = "appointment_number"
LOAD_IDENTIFIER_TYPE_CUSTOMER_REFERENCE = "customer_reference"
LOAD_IDENTIFIER_TYPE_CARRIER_REFERENCE = "carrier_reference"
LOAD_IDENTIFIER_TYPE_UNKNOWN_REFERENCE = "unknown_reference"

LOAD_IDENTIFIER_TYPES = {
    LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
    LOAD_IDENTIFIER_TYPE_ORDER_NUMBER,
    LOAD_IDENTIFIER_TYPE_TENDER_ID,
    LOAD_IDENTIFIER_TYPE_PRO_NUMBER,
    LOAD_IDENTIFIER_TYPE_SHIPMENT_NUMBER,
    LOAD_IDENTIFIER_TYPE_FREIGHT_BILL_NUMBER,
    LOAD_IDENTIFIER_TYPE_TRIP_NUMBER,
    LOAD_IDENTIFIER_TYPE_DISPATCH_NUMBER,
    LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
    LOAD_IDENTIFIER_TYPE_PO_NUMBER,
    LOAD_IDENTIFIER_TYPE_BOL_NUMBER,
    LOAD_IDENTIFIER_TYPE_PICKUP_NUMBER,
    LOAD_IDENTIFIER_TYPE_DELIVERY_NUMBER,
    LOAD_IDENTIFIER_TYPE_PICKUP_CONFIRMATION,
    LOAD_IDENTIFIER_TYPE_DELIVERY_CONFIRMATION,
    LOAD_IDENTIFIER_TYPE_APPOINTMENT_NUMBER,
    LOAD_IDENTIFIER_TYPE_CUSTOMER_REFERENCE,
    LOAD_IDENTIFIER_TYPE_CARRIER_REFERENCE,
    LOAD_IDENTIFIER_TYPE_UNKNOWN_REFERENCE,
}

PRIMARY_LOAD_IDENTIFIER_TYPES = {
    LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
    LOAD_IDENTIFIER_TYPE_ORDER_NUMBER,
    LOAD_IDENTIFIER_TYPE_TENDER_ID,
    LOAD_IDENTIFIER_TYPE_PRO_NUMBER,
    LOAD_IDENTIFIER_TYPE_SHIPMENT_NUMBER,
    LOAD_IDENTIFIER_TYPE_FREIGHT_BILL_NUMBER,
    LOAD_IDENTIFIER_TYPE_TRIP_NUMBER,
    LOAD_IDENTIFIER_TYPE_DISPATCH_NUMBER,
    LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
}

NON_PRIMARY_REFERENCE_TYPES = LOAD_IDENTIFIER_TYPES - PRIMARY_LOAD_IDENTIFIER_TYPES

STRONG_PRIMARY_IDENTIFIER_LABELS = {
    "load #": LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
    "load number": LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
    "load id": LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
    "load no": LOAD_IDENTIFIER_TYPE_BROKER_LOAD_NUMBER,
    "order #": LOAD_IDENTIFIER_TYPE_ORDER_NUMBER,
    "order number": LOAD_IDENTIFIER_TYPE_ORDER_NUMBER,
    "order no": LOAD_IDENTIFIER_TYPE_ORDER_NUMBER,
    "tender #": LOAD_IDENTIFIER_TYPE_TENDER_ID,
    "tender id": LOAD_IDENTIFIER_TYPE_TENDER_ID,
    "tender number": LOAD_IDENTIFIER_TYPE_TENDER_ID,
    "freight bill #": LOAD_IDENTIFIER_TYPE_FREIGHT_BILL_NUMBER,
    "freight bill number": LOAD_IDENTIFIER_TYPE_FREIGHT_BILL_NUMBER,
    "freight bill no": LOAD_IDENTIFIER_TYPE_FREIGHT_BILL_NUMBER,
    "pro #": LOAD_IDENTIFIER_TYPE_PRO_NUMBER,
    "pro number": LOAD_IDENTIFIER_TYPE_PRO_NUMBER,
    "pro no": LOAD_IDENTIFIER_TYPE_PRO_NUMBER,
    "shipment #": LOAD_IDENTIFIER_TYPE_SHIPMENT_NUMBER,
    "shipment number": LOAD_IDENTIFIER_TYPE_SHIPMENT_NUMBER,
    "shipment no": LOAD_IDENTIFIER_TYPE_SHIPMENT_NUMBER,
}

MEDIUM_CONTEXTUAL_IDENTIFIER_LABELS = {
    "trip #": LOAD_IDENTIFIER_TYPE_TRIP_NUMBER,
    "trip number": LOAD_IDENTIFIER_TYPE_TRIP_NUMBER,
    "trip no": LOAD_IDENTIFIER_TYPE_TRIP_NUMBER,
    "dispatch #": LOAD_IDENTIFIER_TYPE_DISPATCH_NUMBER,
    "dispatch number": LOAD_IDENTIFIER_TYPE_DISPATCH_NUMBER,
    "dispatch no": LOAD_IDENTIFIER_TYPE_DISPATCH_NUMBER,
    "ref #": LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
    "reference #": LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
    "reference number": LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
    "confirmation #": LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
    "confirmation number": LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
    "booking #": LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
    "booking number": LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE,
}

NEGATIVE_PRIMARY_IDENTIFIER_LABELS = {
    "po #": LOAD_IDENTIFIER_TYPE_PO_NUMBER,
    "po number": LOAD_IDENTIFIER_TYPE_PO_NUMBER,
    "po no": LOAD_IDENTIFIER_TYPE_PO_NUMBER,
    "bol #": LOAD_IDENTIFIER_TYPE_BOL_NUMBER,
    "bol number": LOAD_IDENTIFIER_TYPE_BOL_NUMBER,
    "bol no": LOAD_IDENTIFIER_TYPE_BOL_NUMBER,
    "pickup #": LOAD_IDENTIFIER_TYPE_PICKUP_NUMBER,
    "pickup number": LOAD_IDENTIFIER_TYPE_PICKUP_NUMBER,
    "pickup no": LOAD_IDENTIFIER_TYPE_PICKUP_NUMBER,
    "pickup confirmation": LOAD_IDENTIFIER_TYPE_PICKUP_CONFIRMATION,
    "delivery #": LOAD_IDENTIFIER_TYPE_DELIVERY_NUMBER,
    "delivery number": LOAD_IDENTIFIER_TYPE_DELIVERY_NUMBER,
    "delivery no": LOAD_IDENTIFIER_TYPE_DELIVERY_NUMBER,
    "delivery confirmation": LOAD_IDENTIFIER_TYPE_DELIVERY_CONFIRMATION,
    "appointment #": LOAD_IDENTIFIER_TYPE_APPOINTMENT_NUMBER,
    "appointment number": LOAD_IDENTIFIER_TYPE_APPOINTMENT_NUMBER,
    "appointment no": LOAD_IDENTIFIER_TYPE_APPOINTMENT_NUMBER,
    "customer ref": LOAD_IDENTIFIER_TYPE_CUSTOMER_REFERENCE,
    "customer reference": LOAD_IDENTIFIER_TYPE_CUSTOMER_REFERENCE,
    "customer reference #": LOAD_IDENTIFIER_TYPE_CUSTOMER_REFERENCE,
    "carrier ref": LOAD_IDENTIFIER_TYPE_CARRIER_REFERENCE,
    "carrier reference": LOAD_IDENTIFIER_TYPE_CARRIER_REFERENCE,
    "carrier reference #": LOAD_IDENTIFIER_TYPE_CARRIER_REFERENCE,
}

LOAD_IDENTITY_CONTEXT_MARKERS = {
    "header",
    "load identity",
    "load confirmation",
    "rate confirmation",
    "carrier tender",
    "load tender",
    "main tender",
    "main rateconf",
    "route details",
    "order confirmation",
    "confirmation title",
}

NON_PRIMARY_CONTEXT_MARKERS = {
    "pickup section",
    "pickup stop",
    "delivery section",
    "delivery stop",
    "stop table",
    "billing",
    "terms",
    "signature",
    "bol body",
}


def normalize_identifier_type(value):
    token = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return token if token in LOAD_IDENTIFIER_TYPES else LOAD_IDENTIFIER_TYPE_UNKNOWN_REFERENCE


def is_primary_load_identifier_type(value):
    return normalize_identifier_type(value) in PRIMARY_LOAD_IDENTIFIER_TYPES


def normalize_identifier_label(label_text):
    text = str(label_text or "").strip().lower()
    text = text.replace(":", " ")
    text = text.replace("no.", "no")
    text = text.replace(" id.", " id")
    text = " ".join(text.split())
    return text


def _context_text(context):
    if context is None:
        return ""
    if isinstance(context, str):
        return context.lower()
    if isinstance(context, dict):
        return " ".join(
            str(value or "").strip().lower()
            for value in context.values()
            if str(value or "").strip()
        )
    if isinstance(context, (list, tuple, set)):
        return " ".join(str(value or "").strip().lower() for value in context)
    return str(context or "").strip().lower()


def _has_marker(context, markers):
    text = _context_text(context)
    return any(marker in text for marker in markers)


def classify_identifier_label(label_text, context=None):
    label = normalize_identifier_label(label_text)
    in_load_context = _has_marker(context, LOAD_IDENTITY_CONTEXT_MARKERS)
    in_non_primary_context = _has_marker(context, NON_PRIMARY_CONTEXT_MARKERS)

    if label in STRONG_PRIMARY_IDENTIFIER_LABELS and not in_non_primary_context:
        identifier_type = STRONG_PRIMARY_IDENTIFIER_LABELS[label]
        return {
            "identifier_type": identifier_type,
            "primary_load_identifier_candidate": True,
            "confidence": CANDIDATE_CONFIDENCE_HIGH,
            "confidence_reasons": ["strong_primary_identifier_label"],
            "warning_codes": [],
        }

    if label in MEDIUM_CONTEXTUAL_IDENTIFIER_LABELS:
        identifier_type = MEDIUM_CONTEXTUAL_IDENTIFIER_LABELS[label]
        if in_load_context and not in_non_primary_context:
            return {
                "identifier_type": identifier_type,
                "primary_load_identifier_candidate": True,
                "confidence": CANDIDATE_CONFIDENCE_MEDIUM,
                "confidence_reasons": ["contextual_primary_identifier_label"],
                "warning_codes": ["generic_identifier_requires_review"]
                if identifier_type == LOAD_IDENTIFIER_TYPE_PRIMARY_REFERENCE
                else [],
            }
        return {
            "identifier_type": LOAD_IDENTIFIER_TYPE_UNKNOWN_REFERENCE,
            "primary_load_identifier_candidate": False,
            "confidence": CANDIDATE_CONFIDENCE_LOW,
            "confidence_reasons": ["ambiguous_reference_label"],
            "warning_codes": ["ambiguous_reference_label"],
        }

    if label in NEGATIVE_PRIMARY_IDENTIFIER_LABELS:
        return {
            "identifier_type": NEGATIVE_PRIMARY_IDENTIFIER_LABELS[label],
            "primary_load_identifier_candidate": False,
            "confidence": CANDIDATE_CONFIDENCE_HIGH,
            "confidence_reasons": ["typed_non_primary_reference_label"],
            "warning_codes": ["not_primary_load_identifier"],
        }

    if "reference" in label or label in {"ref", "ref #"}:
        return {
            "identifier_type": LOAD_IDENTIFIER_TYPE_UNKNOWN_REFERENCE,
            "primary_load_identifier_candidate": False,
            "confidence": CANDIDATE_CONFIDENCE_LOW,
            "confidence_reasons": ["ambiguous_reference_label"],
            "warning_codes": ["ambiguous_reference_label"],
        }

    return {
        "identifier_type": LOAD_IDENTIFIER_TYPE_UNKNOWN_REFERENCE,
        "primary_load_identifier_candidate": False,
        "confidence": CANDIDATE_CONFIDENCE_UNKNOWN,
        "confidence_reasons": ["unknown_identifier_label"],
        "warning_codes": [],
    }


def is_primary_load_identifier_label(label_text, context=None):
    return bool(classify_identifier_label(label_text, context).get("primary_load_identifier_candidate"))


def is_negative_primary_identifier_label(label_text, context=None):
    classification = classify_identifier_label(label_text, context)
    return (
        normalize_identifier_type(classification.get("identifier_type"))
        in NON_PRIMARY_REFERENCE_TYPES
        and "not_primary_load_identifier" in classification.get("warning_codes", [])
    )


def score_identifier_label(label_type, context=None):
    classification = classify_identifier_label(label_type, context)
    if classification["primary_load_identifier_candidate"]:
        if classification["confidence"] == CANDIDATE_CONFIDENCE_HIGH:
            return 90
        if classification["confidence"] == CANDIDATE_CONFIDENCE_MEDIUM:
            return 60
    if is_negative_primary_identifier_label(label_type, context):
        return 20
    if classification["confidence"] == CANDIDATE_CONFIDENCE_LOW:
        return 30
    return 0


def build_load_identifier_candidate(
    candidate_id="",
    identifier_type=LOAD_IDENTIFIER_TYPE_UNKNOWN_REFERENCE,
    raw_value="",
    normalized_value="",
    confidence=CANDIDATE_CONFIDENCE_UNKNOWN,
    confidence_reasons=None,
    page_number="",
    line_number="",
    label="",
    context_before="",
    context_after="",
    source=SOURCE_LABEL_PATTERN,
    evidence_ref="",
    warnings=None,
    section_role="",
    page_role="",
    primary_load_identifier_candidate=None,
):
    normalized_type = normalize_identifier_type(identifier_type)
    primary = (
        is_primary_load_identifier_type(normalized_type)
        if primary_load_identifier_candidate is None
        else bool(primary_load_identifier_candidate)
    )
    candidate = build_field_candidate(
        candidate_id=candidate_id,
        field_name=FIELD_LOAD_NUMBER if primary else FIELD_REFERENCE,
        raw_value=raw_value,
        normalized_value=normalized_value,
        confidence=normalize_confidence(confidence),
        confidence_reasons=confidence_reasons,
        page_number=page_number,
        line_number=line_number,
        label=label,
        context_before=context_before,
        context_after=context_after,
        source=source,
        evidence_ref=evidence_ref,
        warnings=warnings,
        value_type=normalized_type,
    )
    candidate.update(
        {
            "identifier_type": normalized_type,
            "primary_load_identifier_candidate": primary,
            "section_role": str(section_role or "").strip(),
            "page_role": str(page_role or "").strip(),
            "confidence_reasons": normalize_list(confidence_reasons),
            "warnings": normalize_list(warnings),
        }
    )
    return candidate
