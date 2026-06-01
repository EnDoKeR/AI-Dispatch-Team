"""Canonical RateCon field taxonomy for shadow candidate diagnostics.

This module is intentionally dependency-light. It maps raw parser/template
field names into stable shadow fields while preserving mapping strength so
weak or ambiguous aliases remain visible without being treated as strong
production evidence.
"""

from dataclasses import dataclass


MAPPING_STRONG = "strong"
MAPPING_MEDIUM = "medium"
MAPPING_WEAK = "weak"
MAPPING_UNMAPPED = "unmapped"

FIELD_LOAD_NUMBER = "load_number"
FIELD_TOTAL_CARRIER_RATE = "total_carrier_rate"
FIELD_BROKER_NAME = "broker_name"
FIELD_CARRIER_NAME = "carrier_name"
FIELD_PICKUP_STOPS = "pickup_stops"
FIELD_DELIVERY_STOPS = "delivery_stops"
FIELD_PICKUP_COUNT = "pickup_count"
FIELD_DELIVERY_COUNT = "delivery_count"
FIELD_PICKUP_LOCATION = "pickup_location"
FIELD_PICKUP_DATE = "pickup_date"
FIELD_PICKUP_TIME = "pickup_time"
FIELD_DELIVERY_LOCATION = "delivery_location"
FIELD_DELIVERY_DATE = "delivery_date"
FIELD_DELIVERY_TIME = "delivery_time"
FIELD_REFERENCE_NUMBERS = "reference_numbers"
FIELD_ACCESSORIAL_TERM = "accessorial_term"
FIELD_EQUIPMENT_TYPE = "equipment_type"
FIELD_COMMODITY = "commodity"
FIELD_WEIGHT = "weight"
FIELD_SPECIAL_REQUIREMENT = "special_requirement"
FIELD_UNKNOWN = "unknown"

CANONICAL_FIELDS = {
    FIELD_LOAD_NUMBER,
    FIELD_TOTAL_CARRIER_RATE,
    FIELD_BROKER_NAME,
    FIELD_CARRIER_NAME,
    FIELD_PICKUP_STOPS,
    FIELD_DELIVERY_STOPS,
    FIELD_PICKUP_COUNT,
    FIELD_DELIVERY_COUNT,
    FIELD_PICKUP_LOCATION,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_TIME,
    FIELD_DELIVERY_LOCATION,
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_TIME,
    FIELD_REFERENCE_NUMBERS,
    FIELD_ACCESSORIAL_TERM,
    FIELD_EQUIPMENT_TYPE,
    FIELD_COMMODITY,
    FIELD_WEIGHT,
    FIELD_SPECIAL_REQUIREMENT,
}


@dataclass(frozen=True)
class CanonicalFieldMapping:
    raw_field: str
    canonical_field: str
    semantic_role: str = ""
    strength: str = MAPPING_UNMAPPED
    notes: str = ""
    id_type_hint: str = ""
    stop_type_hint: str = ""
    party_role_hint: str = ""
    money_context: str = ""

    def to_dict(self):
        return {
            "raw_field": self.raw_field,
            "canonical_field": self.canonical_field,
            "semantic_role": self.semantic_role,
            "strength": self.strength,
            "notes": self.notes,
            "id_type_hint": self.id_type_hint,
            "stop_type_hint": self.stop_type_hint,
            "party_role_hint": self.party_role_hint,
            "money_context": self.money_context,
        }


def normalize_raw_field_name(value):
    token = str(value or "").strip().lower()
    token = token.replace("-", "_").replace(" ", "_")
    token = token.replace("/", "_").replace(".", "")
    while "__" in token:
        token = token.replace("__", "_")
    return token.strip("_")


def _mapping(
    raw,
    canonical,
    semantic_role="",
    strength=MAPPING_STRONG,
    notes="",
    id_type_hint="",
    stop_type_hint="",
    party_role_hint="",
    money_context="",
):
    return CanonicalFieldMapping(
        raw_field=raw,
        canonical_field=canonical,
        semantic_role=semantic_role,
        strength=strength,
        notes=notes,
        id_type_hint=id_type_hint,
        stop_type_hint=stop_type_hint,
        party_role_hint=party_role_hint,
        money_context=money_context,
    )


_ALIASES = {
    # Primary load identity. PO/BOL/stop refs are intentionally not mapped to
    # load_number.
    "load_number": _mapping("load_number", FIELD_LOAD_NUMBER, "load_identity", MAPPING_STRONG, id_type_hint="load"),
    "load_no": _mapping("load_no", FIELD_LOAD_NUMBER, "load_identity", MAPPING_STRONG, id_type_hint="load"),
    "load_num": _mapping("load_num", FIELD_LOAD_NUMBER, "load_identity", MAPPING_STRONG, id_type_hint="load"),
    "load_id": _mapping("load_id", FIELD_LOAD_NUMBER, "load_identity", MAPPING_STRONG, id_type_hint="load"),
    "load_identifier": _mapping("load_identifier", FIELD_LOAD_NUMBER, "load_identity", MAPPING_STRONG, id_type_hint="load"),
    "broker_load_number": _mapping("broker_load_number", FIELD_LOAD_NUMBER, "load_identity", MAPPING_STRONG, id_type_hint="load"),
    "broker_load_id": _mapping("broker_load_id", FIELD_LOAD_NUMBER, "load_identity", MAPPING_STRONG, id_type_hint="load"),
    "primary_load_number": _mapping("primary_load_number", FIELD_LOAD_NUMBER, "load_identity", MAPPING_STRONG, id_type_hint="load"),
    "rate_confirmation_number": _mapping("rate_confirmation_number", FIELD_LOAD_NUMBER, "load_identity", MAPPING_MEDIUM, id_type_hint="confirmation"),
    "ratecon_number": _mapping("ratecon_number", FIELD_LOAD_NUMBER, "load_identity", MAPPING_MEDIUM, id_type_hint="confirmation"),
    "rc_number": _mapping("rc_number", FIELD_LOAD_NUMBER, "load_identity", MAPPING_MEDIUM, id_type_hint="confirmation"),
    "confirmation_number": _mapping("confirmation_number", FIELD_LOAD_NUMBER, "load_identity", MAPPING_MEDIUM, id_type_hint="confirmation"),
    "shipment_number": _mapping("shipment_number", FIELD_LOAD_NUMBER, "shipment_identity", MAPPING_MEDIUM, id_type_hint="shipment"),
    "shipment_no": _mapping("shipment_no", FIELD_LOAD_NUMBER, "shipment_identity", MAPPING_MEDIUM, id_type_hint="shipment"),
    "shipment_id": _mapping("shipment_id", FIELD_LOAD_NUMBER, "shipment_identity", MAPPING_MEDIUM, id_type_hint="shipment"),
    "tender_number": _mapping("tender_number", FIELD_LOAD_NUMBER, "tender_identity", MAPPING_MEDIUM, id_type_hint="tender"),
    "tender_id": _mapping("tender_id", FIELD_LOAD_NUMBER, "tender_identity", MAPPING_MEDIUM, id_type_hint="tender"),
    "order_number": _mapping("order_number", FIELD_LOAD_NUMBER, "order_identity", MAPPING_MEDIUM, id_type_hint="order"),
    "order_no": _mapping("order_no", FIELD_LOAD_NUMBER, "order_identity", MAPPING_MEDIUM, id_type_hint="order"),
    "order_id": _mapping("order_id", FIELD_LOAD_NUMBER, "order_identity", MAPPING_MEDIUM, id_type_hint="order"),
    "dispatch_number": _mapping("dispatch_number", FIELD_LOAD_NUMBER, "dispatch_identity", MAPPING_MEDIUM, id_type_hint="dispatch"),
    "dispatch_id": _mapping("dispatch_id", FIELD_LOAD_NUMBER, "dispatch_identity", MAPPING_MEDIUM, id_type_hint="dispatch"),
    "trip_number": _mapping("trip_number", FIELD_LOAD_NUMBER, "trip_identity", MAPPING_MEDIUM, id_type_hint="trip"),
    "trip_id": _mapping("trip_id", FIELD_LOAD_NUMBER, "trip_identity", MAPPING_MEDIUM, id_type_hint="trip"),
    "pro_number": _mapping("pro_number", FIELD_LOAD_NUMBER, "ambiguous_identity", MAPPING_WEAK, "weak unless document context proves primary identity", id_type_hint="pro"),
    "reference_number": _mapping("reference_number", FIELD_LOAD_NUMBER, "ambiguous_identity", MAPPING_WEAK, "weak unless header/load identity context proves primary", id_type_hint="reference"),
    "reference_id": _mapping("reference_id", FIELD_LOAD_NUMBER, "ambiguous_identity", MAPPING_WEAK, "weak unless header/load identity context proves primary", id_type_hint="reference"),
    "reference": _mapping("reference", FIELD_REFERENCE_NUMBERS, "reference", MAPPING_WEAK, "generic reference is not a strong load number", id_type_hint="reference"),
    "po_number": _mapping("po_number", FIELD_REFERENCE_NUMBERS, "po_reference", MAPPING_STRONG, "non-primary identifier", id_type_hint="po"),
    "bol_number": _mapping("bol_number", FIELD_REFERENCE_NUMBERS, "bol_reference", MAPPING_STRONG, "non-primary identifier", id_type_hint="bol"),
    "pickup_number": _mapping("pickup_number", FIELD_REFERENCE_NUMBERS, "stop_reference", MAPPING_STRONG, "non-primary stop identifier", id_type_hint="pickup"),
    "delivery_number": _mapping("delivery_number", FIELD_REFERENCE_NUMBERS, "stop_reference", MAPPING_STRONG, "non-primary stop identifier", id_type_hint="delivery"),
    "appointment_number": _mapping("appointment_number", FIELD_REFERENCE_NUMBERS, "appointment_reference", MAPPING_STRONG, "non-primary appointment identifier", id_type_hint="appointment"),
    # Money/rate.
    "total_carrier_rate": _mapping("total_carrier_rate", FIELD_TOTAL_CARRIER_RATE, "main_rate", MAPPING_STRONG, money_context="carrier_pay"),
    "rate": _mapping("rate", FIELD_TOTAL_CARRIER_RATE, "main_rate", MAPPING_MEDIUM, money_context="unknown"),
    "carrier_pay": _mapping("carrier_pay", FIELD_TOTAL_CARRIER_RATE, "main_rate", MAPPING_STRONG, money_context="carrier_pay"),
    "total_carrier_pay": _mapping("total_carrier_pay", FIELD_TOTAL_CARRIER_RATE, "main_rate", MAPPING_STRONG, money_context="carrier_pay"),
    "agreed_amount": _mapping("agreed_amount", FIELD_TOTAL_CARRIER_RATE, "main_rate", MAPPING_STRONG, money_context="total_rate"),
    "agreed_rate": _mapping("agreed_rate", FIELD_TOTAL_CARRIER_RATE, "main_rate", MAPPING_STRONG, money_context="total_rate"),
    "total_rate": _mapping("total_rate", FIELD_TOTAL_CARRIER_RATE, "main_rate", MAPPING_STRONG, money_context="total_rate"),
    "linehaul_rate": _mapping("linehaul_rate", FIELD_TOTAL_CARRIER_RATE, "rate_component", MAPPING_MEDIUM, "linehaul can be main only when no total exists", money_context="linehaul"),
    "freight_charge": _mapping("freight_charge", FIELD_TOTAL_CARRIER_RATE, "main_rate", MAPPING_MEDIUM, money_context="total_rate"),
    "amount_due_to_carrier": _mapping("amount_due_to_carrier", FIELD_TOTAL_CARRIER_RATE, "main_rate", MAPPING_STRONG, money_context="carrier_pay"),
    "carrier_total": _mapping("carrier_total", FIELD_TOTAL_CARRIER_RATE, "main_rate", MAPPING_STRONG, money_context="carrier_pay"),
    "fuel_surcharge": _mapping("fuel_surcharge", FIELD_ACCESSORIAL_TERM, "accessorial", MAPPING_STRONG, "not a main total rate", money_context="fuel"),
    "accessorial": _mapping("accessorial", FIELD_ACCESSORIAL_TERM, "accessorial", MAPPING_STRONG, "not a main total rate", money_context="accessorial"),
    "accessorial_term": _mapping("accessorial_term", FIELD_ACCESSORIAL_TERM, "accessorial", MAPPING_STRONG, "not a main total rate", money_context="accessorial"),
    "quickpay_fee": _mapping("quickpay_fee", FIELD_ACCESSORIAL_TERM, "payment_deduction", MAPPING_STRONG, "not a main total rate", money_context="fee"),
    "deduction": _mapping("deduction", FIELD_ACCESSORIAL_TERM, "payment_deduction", MAPPING_STRONG, "not a main total rate", money_context="deduction"),
    # Stops and stop components.
    "pickup_stops": _mapping("pickup_stops", FIELD_PICKUP_STOPS, "pickup_stop", MAPPING_STRONG, stop_type_hint="pickup"),
    "pickups": _mapping("pickups", FIELD_PICKUP_STOPS, "pickup_stop", MAPPING_STRONG, stop_type_hint="pickup"),
    "pickup_stop": _mapping("pickup_stop", FIELD_PICKUP_STOPS, "pickup_stop", MAPPING_STRONG, stop_type_hint="pickup"),
    "pickup_count": _mapping("pickup_count", FIELD_PICKUP_COUNT, "pickup_stop_count", MAPPING_STRONG, stop_type_hint="pickup"),
    "pickup_location": _mapping("pickup_location", FIELD_PICKUP_LOCATION, "pickup_location", MAPPING_STRONG, stop_type_hint="pickup"),
    "pickup_locations": _mapping("pickup_locations", FIELD_PICKUP_LOCATION, "pickup_location", MAPPING_STRONG, stop_type_hint="pickup"),
    "origin": _mapping("origin", FIELD_PICKUP_LOCATION, "pickup_location", MAPPING_MEDIUM, stop_type_hint="pickup"),
    "shipper": _mapping("shipper", FIELD_PICKUP_LOCATION, "pickup_location", MAPPING_MEDIUM, stop_type_hint="pickup"),
    "shipper_location": _mapping("shipper_location", FIELD_PICKUP_LOCATION, "pickup_location", MAPPING_STRONG, stop_type_hint="pickup"),
    "pickup_date": _mapping("pickup_date", FIELD_PICKUP_DATE, "pickup_date", MAPPING_STRONG, stop_type_hint="pickup"),
    "pickup_time": _mapping("pickup_time", FIELD_PICKUP_TIME, "pickup_time", MAPPING_STRONG, stop_type_hint="pickup"),
    "pickup_appointment": _mapping("pickup_appointment", FIELD_PICKUP_TIME, "pickup_appointment", MAPPING_MEDIUM, stop_type_hint="pickup"),
    "delivery_stops": _mapping("delivery_stops", FIELD_DELIVERY_STOPS, "delivery_stop", MAPPING_STRONG, stop_type_hint="delivery"),
    "deliveries": _mapping("deliveries", FIELD_DELIVERY_STOPS, "delivery_stop", MAPPING_STRONG, stop_type_hint="delivery"),
    "delivery_stop": _mapping("delivery_stop", FIELD_DELIVERY_STOPS, "delivery_stop", MAPPING_STRONG, stop_type_hint="delivery"),
    "delivery_count": _mapping("delivery_count", FIELD_DELIVERY_COUNT, "delivery_stop_count", MAPPING_STRONG, stop_type_hint="delivery"),
    "delivery_location": _mapping("delivery_location", FIELD_DELIVERY_LOCATION, "delivery_location", MAPPING_STRONG, stop_type_hint="delivery"),
    "delivery_locations": _mapping("delivery_locations", FIELD_DELIVERY_LOCATION, "delivery_location", MAPPING_STRONG, stop_type_hint="delivery"),
    "destination": _mapping("destination", FIELD_DELIVERY_LOCATION, "delivery_location", MAPPING_MEDIUM, stop_type_hint="delivery"),
    "consignee": _mapping("consignee", FIELD_DELIVERY_LOCATION, "delivery_location", MAPPING_MEDIUM, stop_type_hint="delivery"),
    "consignee_location": _mapping("consignee_location", FIELD_DELIVERY_LOCATION, "delivery_location", MAPPING_STRONG, stop_type_hint="delivery"),
    "delivery_date": _mapping("delivery_date", FIELD_DELIVERY_DATE, "delivery_date", MAPPING_STRONG, stop_type_hint="delivery"),
    "delivery_time": _mapping("delivery_time", FIELD_DELIVERY_TIME, "delivery_time", MAPPING_STRONG, stop_type_hint="delivery"),
    "delivery_appointment": _mapping("delivery_appointment", FIELD_DELIVERY_TIME, "delivery_appointment", MAPPING_MEDIUM, stop_type_hint="delivery"),
    # Parties and supporting fields.
    "broker_name": _mapping("broker_name", FIELD_BROKER_NAME, "broker_party", MAPPING_STRONG, party_role_hint="broker"),
    "brokerage_name": _mapping("brokerage_name", FIELD_BROKER_NAME, "broker_party", MAPPING_STRONG, party_role_hint="broker"),
    "customer_name": _mapping("customer_name", FIELD_BROKER_NAME, "broker_or_customer_party", MAPPING_WEAK, "weak unless existing semantics prove broker role", party_role_hint="customer"),
    "bill_to": _mapping("bill_to", FIELD_BROKER_NAME, "billing_party", MAPPING_WEAK, "weak broker signal", party_role_hint="bill_to"),
    "carrier_name": _mapping("carrier_name", FIELD_CARRIER_NAME, "carrier_party", MAPPING_STRONG, party_role_hint="carrier"),
    "trucking_company": _mapping("trucking_company", FIELD_CARRIER_NAME, "carrier_party", MAPPING_MEDIUM, party_role_hint="carrier"),
    "assigned_carrier": _mapping("assigned_carrier", FIELD_CARRIER_NAME, "carrier_party", MAPPING_STRONG, party_role_hint="carrier"),
    "equipment": _mapping("equipment", FIELD_EQUIPMENT_TYPE, "equipment", MAPPING_STRONG),
    "equipment_type": _mapping("equipment_type", FIELD_EQUIPMENT_TYPE, "equipment", MAPPING_STRONG),
    "commodity": _mapping("commodity", FIELD_COMMODITY, "commodity", MAPPING_STRONG),
    "weight": _mapping("weight", FIELD_WEIGHT, "weight", MAPPING_STRONG),
    "special_requirement": _mapping("special_requirement", FIELD_SPECIAL_REQUIREMENT, "special_requirement", MAPPING_STRONG),
}


def canonical_field_mapping(raw_field, label="", metadata=None):
    raw = normalize_raw_field_name(raw_field)
    mapping = _ALIASES.get(raw)
    if mapping:
        return mapping
    if raw in CANONICAL_FIELDS:
        return _mapping(raw, raw, raw, MAPPING_STRONG)
    return _mapping(
        raw,
        raw or FIELD_UNKNOWN,
        strength=MAPPING_UNMAPPED,
        notes="no canonical mapping configured",
    )


def confidence_after_mapping(confidence, strength):
    try:
        score = max(0.0, min(float(confidence or 0.0), 1.0))
    except (TypeError, ValueError):
        score = 0.0
    if strength == MAPPING_MEDIUM:
        return min(score, 0.75)
    if strength == MAPPING_WEAK:
        return min(score, 0.62)
    return score


def value_shape(value):
    text = str(value or "")
    stripped = text.strip()
    lower = stripped.lower()
    return {
        "length": len(stripped),
        "length_bucket": (
            "empty"
            if not stripped
            else "1_5"
            if len(stripped) <= 5
            else "6_12"
            if len(stripped) <= 12
            else "13_30"
            if len(stripped) <= 30
            else "over_30"
        ),
        "has_digits": any(char.isdigit() for char in stripped),
        "has_letters": any(char.isalpha() for char in stripped),
        "has_currency_symbol": "$" in stripped,
        "looks_like_date": any(token in lower for token in ["/", "-", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]) and any(char.isdigit() for char in stripped),
        "looks_like_money": "$" in stripped or (
            any(char.isdigit() for char in stripped) and "." in stripped and len(stripped) <= 16
        ),
        "is_structured": isinstance(value, (dict, list, tuple)),
    }
