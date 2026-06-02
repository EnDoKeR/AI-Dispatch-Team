"""Generic shadow-only safety features for table-neighbor load IDs.

The helpers here classify table-neighbor load candidates using structural
context only. They do not depend on broker templates, do not expose raw private
values, and do not affect legacy/production output.
"""

from __future__ import annotations

import re


LOAD_CANDIDATE_PROFILE_HEADER_RECALL_TABLE_SAFETY_V1 = "header_recall_table_safety_v1"

TABLE_CONTEXT_HEADER_LOAD_INFO = "header_load_info"
TABLE_CONTEXT_RATE = "rate_table"
TABLE_CONTEXT_STOP = "stop_table"
TABLE_CONTEXT_REFERENCE = "reference_table"
TABLE_CONTEXT_CARRIER_CONTACT = "carrier_contact_table"
TABLE_CONTEXT_SIGNATURE_FOOTER = "signature_footer"
TABLE_CONTEXT_UNKNOWN = "unknown"

TABLE_ROW_HEADER = "header"
TABLE_ROW_LOAD_ID = "load_id_row"
TABLE_ROW_STOP_REFERENCE = "stop_reference_row"
TABLE_ROW_PICKUP_DELIVERY_REF = "pickup_delivery_ref_row"
TABLE_ROW_RATE = "rate_row"
TABLE_ROW_CARRIER_CONTACT = "carrier_contact_row"
TABLE_ROW_FOOTER = "footer_row"
TABLE_ROW_UNKNOWN = "unknown"

TABLE_NEIGHBOR_SAFE = "safe"
TABLE_NEIGHBOR_RISKY = "risky"
TABLE_NEIGHBOR_UNSAFE = "unsafe"
TABLE_NEIGHBOR_UNKNOWN = "unknown"

TABLE_METHOD_PREFIX = "table_"

_STOP_TERMS = (
    "pickup",
    "pick up",
    "pu #",
    "pu#",
    "delivery",
    "del #",
    "del#",
    "shipper",
    "consignee",
    "origin",
    "destination",
    "stop",
)
_REFERENCE_TERMS = ("bol", "b.o.l", "customer ref", "customer reference", "reference", " ref ", "po #", "po#")
_RATE_TERMS = ("rate", "amount", "charge", "carrier pay", "total pay", "linehaul", "fuel", "accessorial")
_CONTACT_TERMS = ("phone", "email", "contact", "mc #", "mc#", "dot #", "dot#", "carrier contact")
_FOOTER_TERMS = ("signature", "signed", "footer", "driver signature", "carrier signature")
_LOAD_TERMS = (
    "load",
    "order",
    "shipment",
    "tender",
    "confirmation",
    "freight bill",
    "pro #",
    "pro#",
)


def _text(value) -> str:
    return str(value or "").strip()


def _lower(value) -> str:
    return _text(value).lower()


def _has_any(text: str, terms) -> bool:
    return any(term in text for term in terms)


def _metadata(candidate) -> dict:
    metadata = (candidate or {}).get("metadata")
    return dict(metadata) if isinstance(metadata, dict) else {}


def is_table_load_candidate(candidate) -> bool:
    metadata = _metadata(candidate)
    method = _lower(metadata.get("pairing_method"))
    return bool(metadata.get("table_cell_candidate") or method.startswith(TABLE_METHOD_PREFIX))


def row_role_from_safe_context(row_text="", row_role_counts=None, header_row=False) -> str:
    """Classify a table row role without returning any private row text."""

    text = _lower(row_text)
    counts = row_role_counts if isinstance(row_role_counts, dict) else {}
    if header_row:
        return TABLE_ROW_HEADER
    if _has_any(text, _FOOTER_TERMS):
        return TABLE_ROW_FOOTER
    if _has_any(text, _CONTACT_TERMS):
        return TABLE_ROW_CARRIER_CONTACT
    if _has_any(text, _RATE_TERMS) or counts.get("rate"):
        return TABLE_ROW_RATE
    if _has_any(text, ("pickup #", "pu#", "pu #", "delivery #", "del#", "del #")):
        return TABLE_ROW_PICKUP_DELIVERY_REF
    if _has_any(text, _STOP_TERMS) and _has_any(text, _REFERENCE_TERMS):
        return TABLE_ROW_PICKUP_DELIVERY_REF
    if _has_any(text, _STOP_TERMS) or counts.get("stop_role"):
        return TABLE_ROW_STOP_REFERENCE
    if _has_any(text, _REFERENCE_TERMS) or counts.get("reference"):
        return TABLE_ROW_STOP_REFERENCE
    if _has_any(text, _LOAD_TERMS) or counts.get("load_identity"):
        return TABLE_ROW_LOAD_ID
    return TABLE_ROW_UNKNOWN


def context_role_from_safe_context(table_kind="", row_role="", candidate_context="") -> str:
    text = _lower(candidate_context)
    kind = _lower(table_kind)
    row_role = _text(row_role)
    if row_role in {TABLE_ROW_FOOTER} or _has_any(text, _FOOTER_TERMS):
        return TABLE_CONTEXT_SIGNATURE_FOOTER
    if row_role in {TABLE_ROW_CARRIER_CONTACT} or _has_any(text, _CONTACT_TERMS):
        return TABLE_CONTEXT_CARRIER_CONTACT
    if row_role in {TABLE_ROW_RATE} or kind == "rate" or _has_any(text, _RATE_TERMS):
        return TABLE_CONTEXT_RATE
    if row_role in {TABLE_ROW_STOP_REFERENCE, TABLE_ROW_PICKUP_DELIVERY_REF} or kind == "stop":
        return TABLE_CONTEXT_STOP
    if kind == "load" or _has_any(text, _LOAD_TERMS):
        return TABLE_CONTEXT_HEADER_LOAD_INFO
    if _has_any(text, _REFERENCE_TERMS):
        return TABLE_CONTEXT_REFERENCE
    return TABLE_CONTEXT_UNKNOWN


def _identifier_like_count(text: str) -> int:
    count = 0
    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_./-]{2,}", _text(text)):
        normalized = re.sub(r"[-_/.\s]+", "", token)
        if 3 <= len(normalized) <= 40 and any(char.isdigit() for char in normalized):
            count += 1
    return count


def safe_table_context_metadata(
    *,
    table_kind="",
    row_text="",
    row_role_counts=None,
    header_row=False,
) -> dict:
    """Return safe metadata derived from table/row semantics."""

    row_role_counts = row_role_counts if isinstance(row_role_counts, dict) else {}
    row_role = row_role_from_safe_context(
        row_text=row_text,
        row_role_counts=row_role_counts,
        header_row=header_row,
    )
    context_role = context_role_from_safe_context(
        table_kind=table_kind,
        row_role=row_role,
        candidate_context=row_text,
    )
    return {
        "table_context_role": context_role,
        "table_row_role": row_role,
        "table_semantic_kind": _text(table_kind) or TABLE_CONTEXT_UNKNOWN,
        "table_row_role_counts": {
            _text(key): int(value or 0)
            for key, value in (row_role_counts or {}).items()
            if _text(key) and int(value or 0) > 0
        },
        "table_row_identifier_like_cell_count": _identifier_like_count(row_text),
    }


def classify_table_neighbor_safety(candidate) -> dict:
    """Classify a table-neighbor load candidate as safe/risky/unsafe."""

    metadata = _metadata(candidate)
    if not is_table_load_candidate(candidate):
        return {}

    context = " ".join(
        _lower(value)
        for value in [
            (candidate or {}).get("label"),
            (candidate or {}).get("evidence_text"),
            metadata.get("section_context"),
            metadata.get("document_region"),
            metadata.get("id_type_hint"),
            metadata.get("table_context_role"),
            metadata.get("table_row_role"),
        ]
        if _text(value)
    )
    row_role = _text(metadata.get("table_row_role")) or row_role_from_safe_context(
        row_role_counts=metadata.get("table_row_role_counts"),
    )
    context_role = _text(metadata.get("table_context_role")) or context_role_from_safe_context(
        table_kind=metadata.get("table_semantic_kind"),
        row_role=row_role,
        candidate_context=context,
    )
    id_hint = _lower(metadata.get("id_type_hint"))
    label_strength = _lower(metadata.get("label_strength"))
    multi_value_row = int(metadata.get("table_row_identifier_like_cell_count") or 0) >= 3

    penalty = ""
    safety = TABLE_NEIGHBOR_UNKNOWN
    if context_role == TABLE_CONTEXT_RATE or row_role == TABLE_ROW_RATE:
        safety = TABLE_NEIGHBOR_UNSAFE
        penalty = "rate_or_money_table"
    elif context_role == TABLE_CONTEXT_CARRIER_CONTACT or row_role == TABLE_ROW_CARRIER_CONTACT:
        safety = TABLE_NEIGHBOR_UNSAFE
        penalty = "carrier_contact_table"
    elif context_role == TABLE_CONTEXT_SIGNATURE_FOOTER or row_role == TABLE_ROW_FOOTER:
        safety = TABLE_NEIGHBOR_UNSAFE
        penalty = "signature_footer_table"
    elif row_role == TABLE_ROW_PICKUP_DELIVERY_REF:
        safety = TABLE_NEIGHBOR_UNSAFE
        penalty = "pickup_delivery_reference_row"
    elif row_role == TABLE_ROW_STOP_REFERENCE or context_role == TABLE_CONTEXT_STOP:
        safety = TABLE_NEIGHBOR_UNSAFE
        penalty = "stop_reference_row"
    elif metadata.get("is_driver_truck_trailer_noise"):
        safety = TABLE_NEIGHBOR_UNSAFE
        penalty = "driver_truck_trailer_table"
    elif multi_value_row:
        safety = TABLE_NEIGHBOR_RISKY
        penalty = "multi_value_row"
    elif id_hint in {"bol", "reference", "customer_ref"}:
        safety = TABLE_NEIGHBOR_RISKY
        penalty = "reference_label"
    elif id_hint == "po" and context_role not in {TABLE_CONTEXT_HEADER_LOAD_INFO}:
        safety = TABLE_NEIGHBOR_RISKY
        penalty = "po_outside_header_load_info"
    elif context_role == TABLE_CONTEXT_REFERENCE:
        safety = TABLE_NEIGHBOR_RISKY
        penalty = "reference_table"
    elif context_role == TABLE_CONTEXT_HEADER_LOAD_INFO and id_hint in {
        "load",
        "order",
        "shipment",
        "tender",
        "confirmation",
        "freight_bill",
        "pro",
        "po",
    }:
        safety = TABLE_NEIGHBOR_SAFE
    elif label_strength == "strong" and id_hint in {"load", "order", "shipment"}:
        safety = TABLE_NEIGHBOR_SAFE
    else:
        safety = TABLE_NEIGHBOR_RISKY
        penalty = "table_neighbor_missing_header_context"

    return {
        "table_context_role": context_role or TABLE_CONTEXT_UNKNOWN,
        "table_row_role": row_role or TABLE_ROW_UNKNOWN,
        "table_neighbor_safety": safety,
        "table_neighbor_penalty_reason": penalty,
        "gold_debug_available_elsewhere": False,
    }


def enrich_table_neighbor_safety(candidate):
    if not isinstance(candidate, dict):
        return candidate
    item = dict(candidate)
    metadata = _metadata(item)
    safety = classify_table_neighbor_safety(item)
    if safety:
        metadata.update(safety)
        item["metadata"] = metadata
    return item


def apply_table_safety_profile(candidate):
    """Return a candidate copy adjusted for header_recall_table_safety_v1."""

    if not isinstance(candidate, dict):
        return candidate
    item = enrich_table_neighbor_safety(candidate)
    metadata = _metadata(item)
    if not is_table_load_candidate(item):
        return item
    safety = _text(metadata.get("table_neighbor_safety"))
    if not safety:
        return item

    original_confidence = float(item.get("confidence") or 0.0)
    adjustments = []
    if safety == TABLE_NEIGHBOR_SAFE:
        adjustments.append({"reason": "table_neighbor_safe_context", "amount": 0.0})
    elif safety == TABLE_NEIGHBOR_RISKY:
        capped = min(original_confidence, 0.55)
        item["confidence"] = capped
        metadata["label_strength"] = "weak" if capped < 0.60 else metadata.get("label_strength", "medium")
        adjustments.append(
            {
                "reason": metadata.get("table_neighbor_penalty_reason") or "table_neighbor_risky",
                "amount": round(capped - original_confidence, 3),
            }
        )
    elif safety == TABLE_NEIGHBOR_UNSAFE:
        capped = min(original_confidence, 0.35)
        item["confidence"] = capped
        metadata["label_strength"] = "weak"
        # Demote unsafe table-neighbor IDs out of the load_number field while
        # preserving them as diagnostic/reference candidates.
        if _text(item.get("field")) == "load_number":
            item["field"] = "reference_numbers"
            metadata["table_neighbor_demoted_from_load_number"] = True
        adjustments.append(
            {
                "reason": metadata.get("table_neighbor_penalty_reason") or "table_neighbor_unsafe",
                "amount": round(capped - original_confidence, 3),
            }
        )
    metadata["load_candidate_profile"] = LOAD_CANDIDATE_PROFILE_HEADER_RECALL_TABLE_SAFETY_V1
    metadata["load_candidate_profile_adjustments"] = adjustments
    item["metadata"] = metadata
    return item


def apply_table_safety_profile_to_candidates(candidates):
    return [apply_table_safety_profile(candidate) for candidate in candidates or []]
