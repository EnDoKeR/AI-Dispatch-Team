"""Generic candidate context features for shadow RateCon ranking diagnostics.

The features in this module are intentionally semantic and broker-agnostic.
They only add safe metadata booleans/enums; they do not expose private values
in default audit output and do not change production or legacy extraction.
"""

from __future__ import annotations

import re

from app.document_ai.ratecon_load_table_safety import enrich_table_neighbor_safety
from app.document_ai.ratecon_rate_money_safety import enrich_rate_money_safety


FIELD_LOAD_NUMBER = "load_number"
FIELD_TOTAL_CARRIER_RATE = "total_carrier_rate"
FIELD_REFERENCE_NUMBERS = "reference_numbers"

DOCUMENT_REGION_HEADER = "header"
DOCUMENT_REGION_LOAD_INFO = "load_info"
DOCUMENT_REGION_PAYMENT = "payment_summary"
DOCUMENT_REGION_RATE_LINE_ITEM = "rate_line_item"
DOCUMENT_REGION_ACCESSORIAL = "accessorial_section"
DOCUMENT_REGION_STOP = "stop_section"
DOCUMENT_REGION_REFERENCE = "reference_section"
DOCUMENT_REGION_INSTRUCTIONS = "instructions"
DOCUMENT_REGION_FOOTER = "footer_signature"
DOCUMENT_REGION_UNKNOWN = "unknown"

MONEY_CONTEXT_TOTAL_CARRIER_PAY = "total_carrier_pay"
MONEY_CONTEXT_CARRIER_FREIGHT_PAY = "carrier_freight_pay"
MONEY_CONTEXT_TOTAL_RATE = "total_rate"
MONEY_CONTEXT_LINEHAUL_TOTAL = "linehaul_total"
MONEY_CONTEXT_LINE_ITEM_RATE = "line_item_rate"
MONEY_CONTEXT_ACCESSORIAL = "accessorial"
MONEY_CONTEXT_DEDUCTION = "deduction"
MONEY_CONTEXT_FEE = "fee"
MONEY_CONTEXT_QUICKPAY = "quickpay"
MONEY_CONTEXT_FUEL_ADVANCE = "fuel_advance"
MONEY_CONTEXT_PENALTY = "penalty"
MONEY_CONTEXT_PAYMENT_TERMS = "payment_terms_amount"
MONEY_CONTEXT_UNKNOWN = "unknown"


def _text(value) -> str:
    return str(value or "").strip()


def _lower(value) -> str:
    return _text(value).lower()


def _metadata(candidate) -> dict:
    metadata = (candidate or {}).get("metadata")
    return dict(metadata) if isinstance(metadata, dict) else {}


def _context_text(candidate, metadata) -> str:
    return " ".join(
        _lower(value)
        for value in [
            (candidate or {}).get("label"),
            (candidate or {}).get("evidence_text"),
            metadata.get("raw_field"),
            metadata.get("section_context"),
            metadata.get("id_type_hint"),
            metadata.get("money_context"),
            metadata.get("pairing_method"),
            metadata.get("semantic_role"),
        ]
        if _text(value)
    )


def _has_word(text: str, token: str) -> bool:
    return bool(re.search(rf"\b{re.escape(token)}\b", text))


def _has_any(text: str, tokens) -> bool:
    return any(token in text for token in tokens)


def _section_context(metadata) -> str:
    return _lower(metadata.get("section_context")) or "unknown"


def _document_region(candidate, metadata, context: str) -> str:
    section = _section_context(metadata)
    field = _lower((candidate or {}).get("field"))
    if section in {"pickup", "delivery", "stop"} or _has_any(
        context,
        [" pickup ", " delivery ", " consignee", " shipper", " origin", " destination"],
    ):
        return DOCUMENT_REGION_STOP
    if section in {"rate", "charges"}:
        return DOCUMENT_REGION_PAYMENT
    if section == "instructions" or _has_any(context, [" instructions", " terms", " signature"]):
        return DOCUMENT_REGION_INSTRUCTIONS
    if section == "references" or _has_any(context, ["reference", " customer ref"]):
        return DOCUMENT_REGION_REFERENCE
    if section == "load_info" or _has_any(
        context,
        ["rate confirmation", "load confirmation", "load information", "shipment information"],
    ):
        return DOCUMENT_REGION_LOAD_INFO
    if field == FIELD_TOTAL_CARRIER_RATE:
        return DOCUMENT_REGION_PAYMENT
    return DOCUMENT_REGION_UNKNOWN


def _id_type_from_context(metadata, context: str) -> str:
    existing = _lower(metadata.get("id_type_hint"))
    if existing and existing != "unknown":
        if _has_word(context, "po") or "p.o" in context:
            return "po"
        if _has_word(context, "bol") or "b.o.l" in context:
            return "bol"
        return existing
    if _has_word(context, "bol") or "b.o.l" in context:
        return "bol"
    if _has_word(context, "po") or "p.o" in context:
        return "po"
    if "customer ref" in context or "customer reference" in context:
        return "customer_ref"
    if "pickup #" in context or "pu #" in context or "pickup number" in context:
        return "pickup_ref"
    if "delivery #" in context or "del #" in context or "delivery number" in context:
        return "delivery_ref"
    for token in ["load", "shipment", "order", "tender", "confirmation", "dispatch", "trip"]:
        if _has_word(context, token):
            return token
    if _has_word(context, "reference") or _has_word(context, "ref"):
        return "reference"
    return "unknown"


def _enrich_identifier_candidate(candidate, metadata, context: str) -> None:
    region = _document_region(candidate, metadata, context)
    id_hint = _id_type_from_context(metadata, context)
    is_stop = region == DOCUMENT_REGION_STOP
    is_pickup_delivery_ref = id_hint in {"pickup_ref", "delivery_ref"} or _has_any(
        context,
        ["pickup #", "pu #", "delivery #", "del #"],
    )
    is_bol_po_customer = id_hint in {"bol", "po", "customer_ref"}
    is_noise = _has_any(context, ["driver", "truck", "tractor", "trailer", "seal #", "seal number"])
    is_footer = region == DOCUMENT_REGION_FOOTER or _has_any(context, ["signature", "signed by", "footer"])
    header_context = region in {DOCUMENT_REGION_HEADER, DOCUMENT_REGION_LOAD_INFO, DOCUMENT_REGION_UNKNOWN}
    title_or_header = bool(
        header_context
        and (
            _has_any(context, ["rate confirmation", "load confirmation"])
            or id_hint in {"load", "shipment", "order", "tender", "confirmation", "dispatch", "trip"}
        )
        and not is_stop
        and not is_noise
    )
    # A PO in the rate-confirmation title/header may be the primary document
    # identity, but the same label in a stop/reference block stays weak.
    header_po_primary = bool(
        id_hint == "po"
        and header_context
        and _has_any(context, ["rate confirmation", "load confirmation", "load information"])
        and not is_stop
    )
    if header_po_primary:
        title_or_header = True
    if is_noise:
        role_confidence = 0.05
        penalty = "driver_truck_trailer_noise"
    elif is_pickup_delivery_ref:
        role_confidence = 0.20
        penalty = "pickup_delivery_reference"
    elif is_stop and is_bol_po_customer:
        role_confidence = 0.25
        penalty = "stop_level_reference"
    elif is_footer:
        role_confidence = 0.15
        penalty = "footer_signature_id"
    elif header_po_primary:
        role_confidence = 0.72
        penalty = None
    elif title_or_header:
        role_confidence = 0.80 if id_hint == "load" else 0.68
        penalty = None
    elif region == DOCUMENT_REGION_REFERENCE and is_bol_po_customer:
        role_confidence = 0.30
        penalty = "reference_section_id"
    elif is_bol_po_customer:
        role_confidence = 0.40
        penalty = "bol_po_customer_reference"
    else:
        role_confidence = 0.55 if id_hint != "unknown" else 0.35
        penalty = None
    metadata["document_region"] = region
    metadata["section_context"] = _section_context(metadata) or metadata.get("section_context", "")
    metadata["id_type_hint"] = id_hint
    metadata["is_document_title_or_header_id"] = bool(title_or_header)
    metadata["is_stop_level_reference"] = bool(is_stop and (is_bol_po_customer or is_pickup_delivery_ref))
    metadata["is_pickup_delivery_reference"] = bool(is_pickup_delivery_ref)
    metadata["is_bol_or_po_or_customer_ref"] = bool(is_bol_po_customer)
    metadata["is_driver_truck_trailer_noise"] = bool(is_noise)
    metadata["id_role_confidence"] = round(role_confidence, 3)
    metadata["context_penalty_reason"] = penalty or ""
    metadata["context_feature_load_identity_candidate"] = bool(
        title_or_header and role_confidence >= 0.65
    )


def _money_context_from_context(metadata, context: str) -> str:
    existing = _lower(metadata.get("money_context"))
    if "quickpay" in context or "quick pay" in context:
        return MONEY_CONTEXT_QUICKPAY
    if _has_any(context, ["deduction", "deduct", "chargeback"]):
        return MONEY_CONTEXT_DEDUCTION
    if _has_any(context, ["tracking hold", "penalty", "tonu", "late fee"]):
        return MONEY_CONTEXT_PENALTY
    if _has_any(context, ["fuel advance", "advance", "comcheck"]):
        return MONEY_CONTEXT_FUEL_ADVANCE
    if _has_any(context, ["detention", "layover", "lumper", "accessorial"]):
        return MONEY_CONTEXT_ACCESSORIAL
    if re.search(r"\bfee\b", context):
        return MONEY_CONTEXT_FEE
    if _has_any(context, ["payment terms", "net 30", "net30", "days to pay"]):
        return MONEY_CONTEXT_PAYMENT_TERMS
    if _has_any(context, ["total carrier pay", "amount due to carrier", "carrier total", "to truck"]):
        return MONEY_CONTEXT_TOTAL_CARRIER_PAY
    if _has_any(context, ["carrier freight pay", "freight pay"]):
        return MONEY_CONTEXT_CARRIER_FREIGHT_PAY
    if _has_any(context, ["total cost", "total rate", "agreed rate total", "estimated rate"]):
        return MONEY_CONTEXT_TOTAL_RATE
    if _has_any(context, ["linehaul total", "line haul total", "freight charge total"]):
        return MONEY_CONTEXT_LINEHAUL_TOTAL
    if _has_any(context, ["linehaul", "line haul", "per mile", "per unit"]):
        return MONEY_CONTEXT_LINE_ITEM_RATE
    if existing:
        return existing
    return MONEY_CONTEXT_UNKNOWN


def _enrich_money_candidate(candidate, metadata, context: str) -> None:
    money_context = _money_context_from_context(metadata, context)
    negative_contexts = {
        MONEY_CONTEXT_ACCESSORIAL,
        MONEY_CONTEXT_DEDUCTION,
        MONEY_CONTEXT_FEE,
        MONEY_CONTEXT_QUICKPAY,
        MONEY_CONTEXT_FUEL_ADVANCE,
        MONEY_CONTEXT_PENALTY,
        MONEY_CONTEXT_PAYMENT_TERMS,
    }
    total_contexts = {
        MONEY_CONTEXT_TOTAL_CARRIER_PAY,
        MONEY_CONTEXT_CARRIER_FREIGHT_PAY,
        MONEY_CONTEXT_TOTAL_RATE,
        MONEY_CONTEXT_LINEHAUL_TOTAL,
    }
    if money_context in {
        MONEY_CONTEXT_TOTAL_CARRIER_PAY,
        MONEY_CONTEXT_TOTAL_RATE,
        MONEY_CONTEXT_CARRIER_FREIGHT_PAY,
    }:
        region = DOCUMENT_REGION_PAYMENT
    elif money_context == MONEY_CONTEXT_LINEHAUL_TOTAL:
        region = DOCUMENT_REGION_RATE_LINE_ITEM
    elif money_context in negative_contexts:
        region = (
            DOCUMENT_REGION_ACCESSORIAL
            if money_context in {MONEY_CONTEXT_ACCESSORIAL, MONEY_CONTEXT_DEDUCTION, MONEY_CONTEXT_FEE}
            else DOCUMENT_REGION_INSTRUCTIONS
        )
    else:
        region = _document_region(candidate, metadata, context)
    penalty = ""
    if money_context in negative_contexts:
        penalty = money_context
    elif money_context == MONEY_CONTEXT_LINE_ITEM_RATE:
        penalty = "line_item_only"
    elif region in {DOCUMENT_REGION_INSTRUCTIONS, DOCUMENT_REGION_FOOTER}:
        penalty = "instructions_or_footer_money"
    metadata["document_region"] = region
    metadata["money_context"] = money_context
    metadata["is_total_pay_candidate"] = money_context in total_contexts
    metadata["is_total_rate_candidate"] = money_context in total_contexts
    metadata["is_line_item_only"] = money_context == MONEY_CONTEXT_LINE_ITEM_RATE
    metadata["is_deduction_or_penalty"] = money_context in {
        MONEY_CONTEXT_DEDUCTION,
        MONEY_CONTEXT_FEE,
        MONEY_CONTEXT_QUICKPAY,
        MONEY_CONTEXT_FUEL_ADVANCE,
        MONEY_CONTEXT_PENALTY,
    }
    metadata["is_payment_terms_amount"] = money_context == MONEY_CONTEXT_PAYMENT_TERMS
    metadata["context_penalty_reason"] = penalty


def enrich_candidate_context(candidate):
    """Return a candidate copy with safe context metadata added."""
    if not isinstance(candidate, dict):
        return candidate
    item = dict(candidate)
    metadata = _metadata(item)
    context = _context_text(item, metadata)
    field = _lower(item.get("field"))
    if field in {FIELD_LOAD_NUMBER, FIELD_REFERENCE_NUMBERS}:
        _enrich_identifier_candidate(item, metadata, context)
        item["metadata"] = metadata
        item = enrich_table_neighbor_safety(item)
        metadata = _metadata(item)
    if field == FIELD_TOTAL_CARRIER_RATE:
        _enrich_money_candidate(item, metadata, context)
        item["metadata"] = metadata
        item = enrich_rate_money_safety(item)
        metadata = _metadata(item)
    if metadata:
        metadata["context_feature_version"] = "ratecon_candidate_context_features_v1"
        item["metadata"] = metadata
    return item


def enrich_candidates_context(candidates):
    return [enrich_candidate_context(candidate) for candidate in candidates or []]
