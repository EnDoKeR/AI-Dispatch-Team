"""Typed load identifier candidate helpers for RateCon extraction."""

from app.document_ai.ratecon_candidates import (
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


def normalize_identifier_type(value):
    token = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return token if token in LOAD_IDENTIFIER_TYPES else LOAD_IDENTIFIER_TYPE_UNKNOWN_REFERENCE


def is_primary_load_identifier_type(value):
    return normalize_identifier_type(value) in PRIMARY_LOAD_IDENTIFIER_TYPES


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
