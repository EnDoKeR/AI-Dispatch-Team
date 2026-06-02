"""Local gold-label schema and evaluation helpers for RateCon diagnostics.

This module is intentionally dependency-light and local-only. It defines the
truth layer needed to compare legacy output and shadow resolver output without
changing either extraction path.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
import re
from pathlib import Path


GOLD_LABEL_SCHEMA_VERSION = "ratecon_gold_label_v1"

LABEL_UNLABELED = "unlabeled"
LABEL_PARTIAL = "partial"
LABEL_LABELED = "labeled"
LABEL_ADJUDICATED = "adjudicated"
LABEL_SKIPPED = "skipped"

LABEL_STATUSES = {
    LABEL_UNLABELED,
    LABEL_PARTIAL,
    LABEL_LABELED,
    LABEL_ADJUDICATED,
    LABEL_SKIPPED,
}

FIELD_LOAD_NUMBER = "load_number"
FIELD_TOTAL_CARRIER_RATE = "total_carrier_rate"
FIELD_BROKER_NAME = "broker_name"
FIELD_CARRIER_NAME = "carrier_name"
FIELD_PICKUP_STOPS = "pickup_stops"
FIELD_DELIVERY_STOPS = "delivery_stops"
FIELD_EQUIPMENT_TYPE = "equipment_type"
FIELD_COMMODITY = "commodity"
FIELD_WEIGHT = "weight"
FIELD_REFERENCE_NUMBERS = "reference_numbers"
FIELD_PICKUP_LOCATION = "pickup_location"
FIELD_PICKUP_DATE = "pickup_date"
FIELD_PICKUP_TIME = "pickup_time"
FIELD_DELIVERY_LOCATION = "delivery_location"
FIELD_DELIVERY_DATE = "delivery_date"
FIELD_DELIVERY_TIME = "delivery_time"

CRITICAL_FIELDS = (
    FIELD_LOAD_NUMBER,
    FIELD_TOTAL_CARRIER_RATE,
    FIELD_PICKUP_STOPS,
    FIELD_DELIVERY_STOPS,
    FIELD_BROKER_NAME,
    FIELD_CARRIER_NAME,
)

STOP_COMPONENT_FIELDS = (
    FIELD_PICKUP_LOCATION,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_TIME,
    FIELD_DELIVERY_LOCATION,
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_TIME,
)

EVALUATION_FIELDS = CRITICAL_FIELDS + STOP_COMPONENT_FIELDS

SCALAR_FIELDS = (
    FIELD_BROKER_NAME,
    FIELD_CARRIER_NAME,
    FIELD_LOAD_NUMBER,
    FIELD_EQUIPMENT_TYPE,
    FIELD_COMMODITY,
)

REFERENCE_TYPES = {
    "po",
    "bol",
    "customer_ref",
    "pickup_ref",
    "delivery_ref",
    "reference",
    "broker_reference",
    "freight_bill",
    "pickup_delivery_number",
    "alternate_load_header",
    "load_code",
    "shipment_id",
    "pro",
    "el",
    "iel_po",
    "unknown",
}

SYSTEM_LEGACY = "legacy"
SYSTEM_SHADOW = "shadow"
SYSTEM_SHADOW_CANDIDATE_BEST = "shadow_candidate_best"
SYSTEM_SHADOW_BEST_INDEPENDENT = "shadow_best_independent_candidate"
SYSTEM_SHADOW_BEST_LAYOUT = "shadow_best_layout_candidate"
SYSTEM_LEGACY_FALLBACK_CANDIDATE = "legacy_fallback_candidate"

EVALUATION_SYSTEMS = (
    SYSTEM_LEGACY,
    SYSTEM_SHADOW,
    SYSTEM_SHADOW_CANDIDATE_BEST,
    SYSTEM_SHADOW_BEST_INDEPENDENT,
    SYSTEM_SHADOW_BEST_LAYOUT,
    SYSTEM_LEGACY_FALLBACK_CANDIDATE,
)

STATUS_EXACT = "correct_exact"
STATUS_NORMALIZED_MATCH = "correct_normalized"
STATUS_PARTIAL_MATCH = "partial_match"
STATUS_MISSING = "extractor_missing"
STATUS_WRONG_VALUE = "wrong"
STATUS_CONFLICT = "conflict"
STATUS_UNLABELED = "unlabeled"
STATUS_GOLD_UNCERTAIN = "gold_uncertain"
STATUS_SOURCE_NOT_AVAILABLE = "source_not_available"
STATUS_REDACTED_NOT_COMPARABLE = "redacted_not_comparable"
STATUS_UNSUPPORTED_VALUE_TYPE = "unsupported_value_type"
STATUS_LEGACY_SOURCE_NOT_AVAILABLE = "legacy_source_not_available"
STATUS_LEGACY_FIELD_NOT_SERIALIZED = "legacy_field_not_serialized"
STATUS_LEGACY_EXTRACTOR_MISSING = "legacy_extractor_missing"
STATUS_SHADOW_COMPONENT_NOT_SERIALIZED = "shadow_component_not_serialized"
STATUS_SHADOW_REDACTED_NOT_COMPARABLE = "shadow_redacted_not_comparable"
STATUS_SHADOW_EXTRACTOR_MISSING = "shadow_extractor_missing"
STATUS_PREDICTION_UNAVAILABLE = STATUS_SOURCE_NOT_AVAILABLE

SOURCE_AVAILABILITY_STATUSES = {
    STATUS_SOURCE_NOT_AVAILABLE,
    STATUS_REDACTED_NOT_COMPARABLE,
    STATUS_UNSUPPORTED_VALUE_TYPE,
    STATUS_LEGACY_SOURCE_NOT_AVAILABLE,
    STATUS_LEGACY_FIELD_NOT_SERIALIZED,
    STATUS_LEGACY_EXTRACTOR_MISSING,
    STATUS_SHADOW_COMPONENT_NOT_SERIALIZED,
    STATUS_SHADOW_REDACTED_NOT_COMPARABLE,
    STATUS_SHADOW_EXTRACTOR_MISSING,
}

EXTRACTOR_MISSING_STATUSES = {
    STATUS_MISSING,
    STATUS_LEGACY_EXTRACTOR_MISSING,
    STATUS_SHADOW_EXTRACTOR_MISSING,
}

ADJ_LEGACY_CORRECT_SHADOW_WRONG = "legacy_correct_shadow_wrong"
ADJ_SHADOW_CORRECT_LEGACY_WRONG = "shadow_correct_legacy_wrong"
ADJ_BOTH_CORRECT = "both_correct"
ADJ_BOTH_WRONG = "both_wrong"
ADJ_LEGACY_MISSING_SHADOW_CORRECT = "legacy_missing_shadow_correct"
ADJ_LEGACY_CORRECT_SHADOW_MISSING = "legacy_correct_shadow_missing"
ADJ_BOTH_MISSING = "both_missing"
ADJ_GOLD_UNCERTAIN = "gold_uncertain"
ADJ_UNLABELED = "unlabeled"

WINNER_LEGACY = "legacy"
WINNER_SHADOW = "shadow"
WINNER_BOTH = "both"
WINNER_NEITHER = "neither"
WINNER_UNKNOWN = "unknown"

ACTION_KEEP_LEGACY = "keep_legacy"
ACTION_SHADOW_EXPERIMENT = "candidate_shadow_field_experiment"
ACTION_IMPROVE_CANDIDATES = "improve_candidates"
ACTION_RESOLVER_TUNING = "resolver_tuning"
ACTION_REVIEW_REQUIRED = "review_required"
ACTION_OCR_ROUTE = "OCR_route"
ACTION_MORE_GOLD = "more_gold_labels_needed"

CONFIDENCE_BANDS = (
    ("gte_0_90", 0.90, 1.01),
    ("0_80_to_0_89", 0.80, 0.90),
    ("0_70_to_0_79", 0.70, 0.80),
    ("0_60_to_0_69", 0.60, 0.70),
    ("lt_0_60", 0.0, 0.60),
)


def _text(value) -> str:
    return str(value or "").strip()


def _lower(value) -> str:
    return _text(value).lower()


def _safe_money_amount(value):
    text = _text(value).upper().replace("USD", "").replace("$", "").replace(",", "").strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _safe_bool(value) -> bool:
    return bool(value)


def _safe_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value):
    if value in ["", None]:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_value_shape(value) -> dict:
    if isinstance(value, list):
        return {
            "type": "list",
            "length": len(value),
            "has_digits": False,
            "has_letters": False,
            "looks_like_date": False,
            "looks_like_money": False,
            "looks_like_phone": False,
            "looks_like_address": False,
            "token_count": len(value),
        }
    if isinstance(value, dict):
        return {
            "type": "dict",
            "length": len(value),
            "has_digits": False,
            "has_letters": False,
            "looks_like_date": False,
            "looks_like_money": False,
            "looks_like_phone": False,
            "looks_like_address": False,
            "token_count": len(value),
        }
    text = _text(value)
    digits = sum(1 for char in text if char.isdigit())
    letters = sum(1 for char in text if char.isalpha())
    lowered = text.lower()
    amount = _safe_money_amount(text)
    if amount is None:
        magnitude = "unknown"
    elif amount < 500:
        magnitude = "small"
    elif amount < 5000:
        magnitude = "medium"
    else:
        magnitude = "large"
    return {
        "type": "string",
        "length": len(text),
        "has_digits": bool(digits),
        "has_letters": bool(letters),
        "has_currency_symbol": "$" in text,
        "amount_magnitude_band": magnitude,
        "looks_like_date": bool(digits and ("/" in text or "-" in text) and len(text) <= 16),
        "looks_like_money": "$" in text or bool(digits and "." in text),
        "looks_like_phone": digits >= 10 and any(char in text for char in ["(", ")", "-"]),
        "looks_like_address": any(
            token in lowered
            for token in [" st", " ave", " rd", " road", " drive", " blvd", " lane"]
        ),
        "token_count": len(text.split()) if text else 0,
    }


def scalar_gold_field(value=None, uncertain=False, notes="") -> dict:
    return {"value": value, "uncertain": bool(uncertain), "notes": _text(notes)}


def money_gold_field(value=None, currency="USD", uncertain=False, notes="") -> dict:
    return {
        "value": value,
        "currency": _text(currency) or "USD",
        "uncertain": bool(uncertain),
        "notes": _text(notes),
    }


def weight_gold_field(value=None, unit="lb", uncertain=False, notes="") -> dict:
    return {
        "value": value,
        "unit": _text(unit) or "lb",
        "uncertain": bool(uncertain),
        "notes": _text(notes),
    }


def stop_gold_item(stop_index=1, uncertain=False, notes="") -> dict:
    return {
        "stop_index": stop_index,
        "facility": None,
        "address": None,
        "city": None,
        "state": None,
        "zip": None,
        "date": None,
        "time": None,
        "appointment_window": None,
        "uncertain": bool(uncertain),
        "notes": _text(notes),
    }


def reference_gold_item(value="", ref_type="unknown", uncertain=False, notes="") -> dict:
    return {
        "type": ref_type if ref_type in REFERENCE_TYPES else "unknown",
        "value": value,
        "uncertain": bool(uncertain),
        "notes": _text(notes),
    }


def build_gold_label_template(document_id="", file_hash="", file_name="") -> dict:
    return {
        "schema_version": GOLD_LABEL_SCHEMA_VERSION,
        "document_id": _text(document_id),
        "file_hash": _text(file_hash),
        "file_name": _text(file_name),
        "label_status": LABEL_UNLABELED,
        "skip_reason": None,
        "gold": {
            "document_type": "rate_confirmation",
            FIELD_BROKER_NAME: scalar_gold_field(),
            FIELD_CARRIER_NAME: scalar_gold_field(),
            FIELD_LOAD_NUMBER: {
                "value": None,
                "alternate_acceptable_values": [],
                "uncertain": False,
                "notes": "",
            },
            FIELD_TOTAL_CARRIER_RATE: money_gold_field(),
            FIELD_PICKUP_STOPS: [],
            FIELD_DELIVERY_STOPS: [],
            FIELD_EQUIPMENT_TYPE: scalar_gold_field(),
            FIELD_COMMODITY: scalar_gold_field(),
            FIELD_WEIGHT: weight_gold_field(),
            FIELD_REFERENCE_NUMBERS: [],
        },
        "labeler": {
            "name": None,
            "labeled_at": None,
            "review_notes": "",
        },
    }


def _field_has_value(field_value) -> bool:
    if isinstance(field_value, dict):
        if _text(field_value.get("value")):
            return True
        if isinstance(field_value.get("alternate_acceptable_values"), list) and any(
            _text(item) for item in field_value.get("alternate_acceptable_values")
        ):
            return True
        return False
    if isinstance(field_value, list):
        return bool(field_value)
    return bool(_text(field_value))


def _validate_scalar_field(path, value, errors):
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return
    if "uncertain" in value and not isinstance(value.get("uncertain"), bool):
        errors.append(f"{path}.uncertain must be boolean")
    if "notes" in value and not isinstance(value.get("notes"), str):
        errors.append(f"{path}.notes must be string")


def _validate_money_field(path, value, errors):
    _validate_scalar_field(path, value, errors)
    if not isinstance(value, dict):
        return
    if value.get("value") not in [None, ""]:
        try:
            Decimal(str(value.get("value")).replace(",", ""))
        except (InvalidOperation, ValueError):
            errors.append(f"{path}.value must be numeric or null")
    if "currency" in value and not isinstance(value.get("currency"), str):
        errors.append(f"{path}.currency must be string")


def _validate_stop(path, stop, errors):
    if not isinstance(stop, dict):
        errors.append(f"{path} must be an object")
        return
    if "stop_index" in stop and not isinstance(stop.get("stop_index"), int):
        errors.append(f"{path}.stop_index must be integer")
    for key in [
        "facility",
        "address",
        "city",
        "state",
        "zip",
        "date",
        "time",
        "appointment_window",
        "notes",
    ]:
        if stop.get(key) is not None and not isinstance(stop.get(key), str):
            errors.append(f"{path}.{key} must be string or null")
    if "uncertain" in stop and not isinstance(stop.get("uncertain"), bool):
        errors.append(f"{path}.uncertain must be boolean")


def validate_gold_label(label) -> list[str]:
    errors: list[str] = []
    if not isinstance(label, dict):
        return ["gold label must be an object"]
    if label.get("schema_version") != GOLD_LABEL_SCHEMA_VERSION:
        errors.append(f"schema_version must be {GOLD_LABEL_SCHEMA_VERSION}")
    status = _text(label.get("label_status")) or LABEL_UNLABELED
    if status not in LABEL_STATUSES:
        errors.append("label_status is invalid")
    gold = label.get("gold")
    if not isinstance(gold, dict):
        errors.append("gold must be an object")
        return errors
    for field_name in SCALAR_FIELDS:
        if field_name in gold:
            _validate_scalar_field(f"gold.{field_name}", gold.get(field_name), errors)
    if FIELD_TOTAL_CARRIER_RATE in gold:
        _validate_money_field(f"gold.{FIELD_TOTAL_CARRIER_RATE}", gold.get(FIELD_TOTAL_CARRIER_RATE), errors)
    if FIELD_WEIGHT in gold:
        _validate_money_field(f"gold.{FIELD_WEIGHT}", gold.get(FIELD_WEIGHT), errors)
    for stop_field in [FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS]:
        stops = gold.get(stop_field, [])
        if stops in [None, ""]:
            stops = []
        if not isinstance(stops, list):
            errors.append(f"gold.{stop_field} must be a list")
            continue
        for index, stop in enumerate(stops):
            _validate_stop(f"gold.{stop_field}[{index}]", stop, errors)
    refs = gold.get(FIELD_REFERENCE_NUMBERS, [])
    if refs in [None, ""]:
        refs = []
    if not isinstance(refs, list):
        errors.append("gold.reference_numbers must be a list")
    else:
        for index, ref in enumerate(refs):
            if not isinstance(ref, dict):
                errors.append(f"gold.reference_numbers[{index}] must be an object")
                continue
            if ref.get("type", "unknown") not in REFERENCE_TYPES:
                errors.append(f"gold.reference_numbers[{index}].type is invalid")
    if status in {LABEL_LABELED, LABEL_ADJUDICATED}:
        for field_name in CRITICAL_FIELDS:
            if not _field_has_value(gold.get(field_name)):
                errors.append(
                    f"gold.{field_name} is required when label_status={status}; use label_status=partial for partial labels"
                )
    if status == LABEL_SKIPPED and not _text(label.get("skip_reason")):
        errors.append("skip_reason is required when label_status=skipped")
    return errors


def require_valid_gold_label(label) -> dict:
    errors = validate_gold_label(label)
    if errors:
        raise ValueError("; ".join(errors))
    return label


def read_json(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path) -> list[dict]:
    records = []
    path = Path(path)
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def load_gold_labels(path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    if path.is_dir():
        labels = []
        for item in sorted(path.glob("*.json")):
            if item.name.endswith("_manifest.json"):
                continue
            payload = read_json(item)
            if payload.get("gold_label_template"):
                payload = payload.get("gold_label_template")
            labels.append(require_valid_gold_label(payload))
        return labels
    if path.suffix.lower() == ".jsonl":
        return [require_valid_gold_label(record) for record in read_jsonl(path)]
    payload = read_json(path)
    if isinstance(payload, list):
        return [require_valid_gold_label(record) for record in payload]
    if payload.get("gold_label_template"):
        payload = payload.get("gold_label_template")
    return [require_valid_gold_label(payload)]


def normalize_load_number(value) -> str:
    text = _lower(value)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[-_/]+", "", text)
    return text


def normalize_money(value) -> str:
    text = _text(value).replace("$", "").replace(",", "").strip()
    if not text:
        return ""
    try:
        return str(Decimal(text).quantize(Decimal("0.01")))
    except (InvalidOperation, ValueError):
        return ""


LEGAL_SUFFIXES = {
    "llc",
    "inc",
    "inc.",
    "corp",
    "corp.",
    "co",
    "co.",
    "company",
    "ltd",
    "ltd.",
}


def normalize_name(value) -> str:
    text = re.sub(r"[^a-z0-9 ]+", " ", _lower(value))
    tokens = [token for token in text.split() if token not in LEGAL_SUFFIXES]
    return " ".join(tokens)


def normalize_date(value) -> str:
    text = _text(value)
    if not text:
        return ""
    match = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", text)
    if match:
        month, day, year = match.groups()
        if len(year) == 2:
            year = f"20{year}"
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return _lower(text)


def normalize_time(value) -> str:
    text = _lower(value)
    text = re.sub(r"\s+", "", text)
    return text


def normalize_location_component(value) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", _lower(value)).strip()


def _gold_scalar_value(gold_field):
    if isinstance(gold_field, dict):
        return gold_field.get("value")
    return gold_field


def _location_value(stop):
    if not isinstance(stop, dict):
        return ""
    return " ".join(
        part
        for part in [
            _text(stop.get("facility")),
            _text(stop.get("address")),
            _text(stop.get("city")),
            _text(stop.get("state")),
            _text(stop.get("zip")),
        ]
        if part
    )


def _first_labeled_stop_component(stops, component):
    for stop in stops or []:
        if not isinstance(stop, dict):
            continue
        if component == "location":
            value = _location_value(stop)
        elif component == "time":
            value = _text(stop.get("time") or stop.get("appointment_window"))
        else:
            value = _text(stop.get(component))
        if value:
            return value
    return ""


def gold_field_for_evaluation(gold, field_name):
    gold = gold if isinstance(gold, dict) else {}
    if field_name in CRITICAL_FIELDS:
        return gold.get(field_name)
    if field_name.startswith("pickup_"):
        stops = gold.get(FIELD_PICKUP_STOPS, []) or []
    elif field_name.startswith("delivery_"):
        stops = gold.get(FIELD_DELIVERY_STOPS, []) or []
    else:
        return None
    if field_name.endswith("_location"):
        value = _first_labeled_stop_component(stops, "location")
    elif field_name.endswith("_date"):
        value = _first_labeled_stop_component(stops, "date")
    elif field_name.endswith("_time"):
        value = _first_labeled_stop_component(stops, "time")
    else:
        value = ""
    uncertain = any(isinstance(stop, dict) and stop.get("uncertain") for stop in stops)
    return {"value": value or None, "uncertain": uncertain, "notes": ""}


def _gold_uncertain(gold_field) -> bool:
    if isinstance(gold_field, dict):
        return bool(gold_field.get("uncertain"))
    if isinstance(gold_field, list):
        return any(isinstance(item, dict) and item.get("uncertain") for item in gold_field)
    return False


def _prediction_value(prediction):
    if isinstance(prediction, dict):
        return prediction.get("value")
    return prediction


def _prediction_source_status(prediction):
    if isinstance(prediction, dict):
        status = _text(prediction.get("source_status"))
        if status:
            return status
    return ""


def _confidence(prediction):
    if isinstance(prediction, dict):
        value = _safe_float(prediction.get("confidence"))
        return value
    return None


def _availability_result(field_name, prediction, status):
    return {
        "field": field_name,
        "status": status,
        "issues": [status],
        "confidence": _confidence(prediction),
        "predicted": False,
        "gold_labeled": True,
    }


def _compare_text(prediction, gold_value, normalizer=None) -> dict:
    predicted_value = _prediction_value(prediction)
    if not _text(gold_value):
        return {"status": STATUS_UNLABELED, "issues": ["unlabeled"]}
    if not _text(predicted_value):
        return {"status": STATUS_MISSING, "issues": ["missing"]}
    if _text(predicted_value) == _text(gold_value):
        return {"status": STATUS_EXACT, "issues": []}
    if normalizer and normalizer(predicted_value) and normalizer(predicted_value) == normalizer(gold_value):
        return {"status": STATUS_NORMALIZED_MATCH, "issues": []}
    return {"status": STATUS_WRONG_VALUE, "issues": ["wrong_value"]}


def compare_load_number(prediction, gold_field) -> dict:
    gold_value = _gold_scalar_value(gold_field)
    result = _compare_text(prediction, gold_value, normalizer=normalize_load_number)
    if result["status"] in {STATUS_EXACT, STATUS_NORMALIZED_MATCH}:
        return result
    predicted_value = _prediction_value(prediction)
    alternates = []
    if isinstance(gold_field, dict):
        alternates = gold_field.get("alternate_acceptable_values") or []
    for alternate in alternates:
        alt_result = _compare_text(prediction, alternate, normalizer=normalize_load_number)
        if alt_result["status"] in {STATUS_EXACT, STATUS_NORMALIZED_MATCH}:
            alt_result["status"] = STATUS_NORMALIZED_MATCH
            alt_result["issues"] = ["matched_alternate"]
            return alt_result
    if _text(predicted_value) and not _text(gold_value) and alternates:
        return {"status": STATUS_WRONG_VALUE, "issues": ["alternate_mismatch"]}
    return result


def compare_money(prediction, gold_field) -> dict:
    gold_value = _gold_scalar_value(gold_field)
    predicted_value = _prediction_value(prediction)
    if not _text(gold_value):
        return {"status": STATUS_UNLABELED, "issues": ["unlabeled"]}
    if not _text(predicted_value):
        return {"status": STATUS_MISSING, "issues": ["missing"]}
    gold_norm = normalize_money(gold_value)
    pred_norm = normalize_money(predicted_value)
    if pred_norm and gold_norm and pred_norm == gold_norm:
        raw_status = STATUS_EXACT if _text(predicted_value) == _text(gold_value) else STATUS_NORMALIZED_MATCH
        return {"status": raw_status, "issues": []}
    return {"status": STATUS_WRONG_VALUE, "issues": ["wrong_money"]}


def _stop_component(stop, key):
    if isinstance(stop, dict):
        return stop.get(key)
    return None


def _stop_has_any_label(stop) -> bool:
    return any(
        _text(_stop_component(stop, key))
        for key in [
            "facility",
            "address",
            "city",
            "state",
            "zip",
            "date",
            "time",
            "appointment_window",
        ]
    )


def _normalize_stop_for_compare(stop) -> dict:
    return {
        "facility": normalize_location_component(_stop_component(stop, "facility")),
        "address": normalize_location_component(_stop_component(stop, "address")),
        "city": normalize_location_component(_stop_component(stop, "city")),
        "state": normalize_location_component(_stop_component(stop, "state")),
        "zip": re.sub(r"\D+", "", _text(_stop_component(stop, "zip"))),
        "date": normalize_date(_stop_component(stop, "date")),
        "time": normalize_time(
            _stop_component(stop, "time") or _stop_component(stop, "appointment_window")
        ),
    }


def _coerce_prediction_stops(prediction) -> list[dict]:
    value = _prediction_value(prediction)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        if isinstance(value.get("stops"), list):
            return [item for item in value.get("stops") if isinstance(item, dict)]
        return [value]
    if isinstance(prediction, dict):
        selected = prediction.get("selected_candidate") or {}
        metadata = selected.get("metadata") if isinstance(selected, dict) else {}
        if isinstance(metadata, dict) and metadata.get("structured_stop_summary"):
            summary = metadata.get("structured_stop_summary") or {}
            return [
                {
                    "facility": "__present__" if summary.get("has_facility") else None,
                    "address": "__present__" if summary.get("has_address") else None,
                    "city": "__present__" if summary.get("has_location") else None,
                    "date": "__present__" if summary.get("has_date") else None,
                    "time": "__present__" if summary.get("has_time") else None,
                }
            ]
    return []


def _prediction_stop_component(prediction, component):
    stops = _coerce_prediction_stops(prediction)
    if not stops:
        return ""
    if component == "location":
        return _location_value(stops[0])
    if component == "time":
        return _text(stops[0].get("time") or stops[0].get("appointment_window"))
    return _text(stops[0].get(component))


def compare_stops(prediction, gold_stops) -> dict:
    gold_items = [stop for stop in gold_stops or [] if isinstance(stop, dict) and _stop_has_any_label(stop)]
    if not gold_items:
        return {"status": STATUS_UNLABELED, "issues": ["unlabeled"]}
    predicted_stops = _coerce_prediction_stops(prediction)
    if not predicted_stops:
        return {"status": STATUS_MISSING, "issues": ["missing_stop"]}
    pred_norms = [_normalize_stop_for_compare(stop) for stop in predicted_stops]
    gold_norms = [_normalize_stop_for_compare(stop) for stop in gold_items]
    exact_matches = 0
    partial_matches = 0
    issues = Counter()
    for gold in gold_norms:
        best_score = 0
        best_issues = []
        labeled_keys = [key for key, value in gold.items() if value]
        for pred in pred_norms:
            score = 0
            local_issues = []
            for key in labeled_keys:
                if pred.get(key) and pred.get(key) == gold.get(key):
                    score += 1
                elif not pred.get(key):
                    local_issues.append(f"missing_{key}")
                else:
                    local_issues.append(f"wrong_{key}")
            if score > best_score:
                best_score = score
                best_issues = local_issues
        if labeled_keys and best_score == len(labeled_keys):
            exact_matches += 1
        elif best_score > 0:
            partial_matches += 1
            issues.update(best_issues)
        else:
            issues["missing_stop"] += 1
    if exact_matches == len(gold_norms):
        return {"status": STATUS_NORMALIZED_MATCH, "issues": []}
    if partial_matches or exact_matches:
        return {"status": STATUS_PARTIAL_MATCH, "issues": sorted(issues) or ["partial_stop"]}
    return {"status": STATUS_WRONG_VALUE, "issues": sorted(issues) or ["wrong_stop"]}


def _gold_field_has_label(field_name, gold_field) -> bool:
    if field_name in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}:
        return any(
            isinstance(stop, dict) and _stop_has_any_label(stop)
            for stop in gold_field or []
        )
    return bool(_text(_gold_scalar_value(gold_field)))


def compare_field(field_name, prediction, gold_field) -> dict:
    if _gold_uncertain(gold_field):
        return {
            "field": field_name,
            "status": STATUS_GOLD_UNCERTAIN,
            "issues": ["gold_uncertain"],
            "confidence": _confidence(prediction),
        }
    source_status = _prediction_source_status(prediction)
    if source_status in SOURCE_AVAILABILITY_STATUSES:
        if not _gold_field_has_label(field_name, gold_field):
            return {
                "field": field_name,
                "status": STATUS_UNLABELED,
                "issues": ["unlabeled"],
                "confidence": _confidence(prediction),
                "predicted": False,
                "gold_labeled": False,
            }
        return _availability_result(field_name, prediction, source_status)
    if field_name == FIELD_LOAD_NUMBER:
        result = compare_load_number(prediction, gold_field)
    elif field_name == FIELD_TOTAL_CARRIER_RATE:
        result = compare_money(prediction, gold_field)
    elif field_name in {FIELD_BROKER_NAME, FIELD_CARRIER_NAME}:
        result = _compare_text(prediction, _gold_scalar_value(gold_field), normalizer=normalize_name)
    elif field_name in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}:
        result = compare_stops(prediction, gold_field)
    elif field_name.endswith("_location"):
        result = _compare_text(
            prediction,
            _gold_scalar_value(gold_field),
            normalizer=normalize_location_component,
        )
    elif field_name.endswith("_date"):
        result = _compare_text(
            prediction,
            _gold_scalar_value(gold_field),
            normalizer=normalize_date,
        )
    elif field_name.endswith("_time"):
        result = _compare_text(
            prediction,
            _gold_scalar_value(gold_field),
            normalizer=normalize_time,
        )
    else:
        result = _compare_text(prediction, _gold_scalar_value(gold_field), normalizer=_lower)
    result = dict(result)
    result["field"] = field_name
    result["confidence"] = _confidence(prediction)
    result["predicted"] = bool(_text(_prediction_value(prediction)) or _coerce_prediction_stops(prediction))
    result["gold_labeled"] = result["status"] not in {STATUS_UNLABELED, STATUS_GOLD_UNCERTAIN}
    return result


def _record_key(record) -> tuple[str, str]:
    return (_text(record.get("document_id")), _text(record.get("file_hash")))


def _label_key(label) -> tuple[str, str]:
    return (_text(label.get("document_id")), _text(label.get("file_hash")))


def _audit_by_key(records) -> dict:
    indexed = {}
    for record in records or []:
        document_id, file_hash = _record_key(record)
        file_name = _text(record.get("file_name"))
        if document_id:
            indexed[(document_id, "")] = record
        if file_hash:
            indexed[("", file_hash)] = record
            indexed[("", file_hash[:16])] = record
        if file_name:
            indexed[(file_name, "")] = record
            indexed[(Path(file_name).stem, "")] = record
        if document_id or file_hash:
            indexed[(document_id, file_hash)] = record
            indexed[(document_id, file_hash[:16])] = record
    return indexed


def _find_record(label, indexed):
    document_id, file_hash = _label_key(label)
    file_name = _text(label.get("file_name"))
    return (
        indexed.get((document_id, file_hash))
        or indexed.get((document_id, file_hash[:16]))
        or indexed.get((document_id, ""))
        or indexed.get(("", file_hash))
        or indexed.get(("", file_hash[:16]))
        or indexed.get((file_name, ""))
        or indexed.get((Path(file_name).stem, ""))
        or {}
    )


def _private_eval_values(record):
    if not isinstance(record, dict):
        return {}
    values = record.get("private_eval_values", {})
    return values if isinstance(values, dict) else {}


def _private_group_prediction(record, group_name, field_name):
    payload = _private_eval_values(record)
    group = payload.get(group_name, {}) if isinstance(payload, dict) else {}
    if isinstance(group, dict) and field_name in group and isinstance(group.get(field_name), dict):
        return group[field_name]
    if isinstance(group, dict) and field_name in group:
        return {"value": group.get(field_name)}
    return None


def _prediction_with_status(status, confidence=None):
    return {"value": "", "confidence": confidence, "source_status": status}


def _legacy_field_status_from_audit(record, field_name):
    legacy = record.get("legacy", {}) if isinstance(record, dict) else {}
    if not legacy:
        return STATUS_LEGACY_SOURCE_NOT_AVAILABLE
    fields_present = set(legacy.get("fields_present", []) or [])
    if field_name in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}:
        count_field = "pickup_count" if field_name == FIELD_PICKUP_STOPS else "delivery_count"
        count = _safe_int(legacy.get(count_field))
        if count > 0:
            return STATUS_LEGACY_FIELD_NOT_SERIALIZED
        return STATUS_LEGACY_EXTRACTOR_MISSING
    if _text(legacy.get(field_name)):
        return ""
    if field_name in fields_present:
        return STATUS_LEGACY_FIELD_NOT_SERIALIZED
    if field_name in legacy:
        return STATUS_LEGACY_EXTRACTOR_MISSING
    return STATUS_LEGACY_FIELD_NOT_SERIALIZED


def _legacy_prediction(record, field_name):
    private_prediction = _private_group_prediction(record, "legacy_selected", field_name)
    if private_prediction is not None:
        return private_prediction
    legacy = record.get("legacy", {}) if isinstance(record, dict) else {}
    if field_name in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}:
        status = _legacy_field_status_from_audit(record, field_name)
        if status:
            return _prediction_with_status(status)
        return {"value": legacy.get(field_name, ""), "confidence": None}
    status = _legacy_field_status_from_audit(record, field_name)
    if status:
        return _prediction_with_status(status)
    return {"value": legacy.get(field_name, ""), "confidence": None}


def _shadow_prediction(record, field_name):
    private_prediction = _private_group_prediction(record, "shadow_selected", field_name)
    if private_prediction is not None:
        return private_prediction
    shadow = record.get("shadow", {}) if isinstance(record, dict) else {}
    fields = shadow.get("resolved_fields", {}) if isinstance(shadow, dict) else {}
    value = fields.get(field_name, {}) if isinstance(fields, dict) else {}
    if field_name in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS} and isinstance(value, dict):
        if value.get("structured_stop_summary") and not _coerce_prediction_stops(value):
            return {
                **value,
                "source_status": STATUS_SHADOW_COMPONENT_NOT_SERIALIZED,
            }
    return value if isinstance(value, dict) else {"value": value}


def _candidate_group_prediction(record, field_name, group_name):
    private_prediction = _private_group_prediction(record, group_name, field_name)
    if private_prediction is not None:
        return private_prediction
    return _prediction_with_status(STATUS_SOURCE_NOT_AVAILABLE)


def _component_prediction(record, field_name, system_name):
    stop_field = FIELD_PICKUP_STOPS if field_name.startswith("pickup_") else FIELD_DELIVERY_STOPS
    if system_name == SYSTEM_LEGACY:
        base = _legacy_prediction(record, stop_field)
    elif system_name == SYSTEM_SHADOW:
        base = _shadow_prediction(record, stop_field)
    else:
        base = _candidate_group_prediction(record, stop_field, system_name)
    source_status = _prediction_source_status(base)
    if source_status in SOURCE_AVAILABILITY_STATUSES:
        return {
            "value": "",
            "confidence": _confidence(base),
            "source_status": source_status,
        }
    if field_name.endswith("_location"):
        value = _prediction_stop_component(base, "location")
    elif field_name.endswith("_date"):
        value = _prediction_stop_component(base, "date")
    elif field_name.endswith("_time"):
        value = _prediction_stop_component(base, "time")
    else:
        value = ""
    if not _text(value) and _coerce_prediction_stops(base):
        status = (
            STATUS_LEGACY_FIELD_NOT_SERIALIZED
            if system_name == SYSTEM_LEGACY
            else STATUS_SHADOW_COMPONENT_NOT_SERIALIZED
        )
        return {"value": "", "confidence": _confidence(base), "source_status": status}
    return {"value": value, "confidence": _confidence(base)}


def _prediction_for_system(record, field_name, system_name):
    if field_name in STOP_COMPONENT_FIELDS:
        return _component_prediction(record, field_name, system_name)
    if system_name == SYSTEM_LEGACY:
        return _legacy_prediction(record, field_name)
    if system_name == SYSTEM_SHADOW:
        return _shadow_prediction(record, field_name)
    return _candidate_group_prediction(record, field_name, system_name)


def _status_correct(status) -> bool:
    return status in {STATUS_EXACT, STATUS_NORMALIZED_MATCH}


def _status_partial(status) -> bool:
    return status == STATUS_PARTIAL_MATCH


def _status_missing(status) -> bool:
    return status in EXTRACTOR_MISSING_STATUSES


def _status_unavailable(status) -> bool:
    return status in SOURCE_AVAILABILITY_STATUSES and not _status_missing(status)


def _empty_metric():
    return {
        "labeled_count": 0,
        "uncertain_count": 0,
        "predicted_count": 0,
        "exact_match_count": 0,
        "normalized_match_count": 0,
        "partial_match_count": 0,
        "missing_count": 0,
        "extractor_missing_count": 0,
        "source_not_available_count": 0,
        "field_not_serialized_count": 0,
        "redacted_not_comparable_count": 0,
        "unsupported_value_type_count": 0,
        "wrong_value_count": 0,
        "conflict_count": 0,
        "low_confidence_but_correct_count": 0,
        "high_confidence_but_wrong_count": 0,
    }


def _update_metric(metric, comparison):
    status = comparison.get("status")
    confidence = comparison.get("confidence")
    if status == STATUS_GOLD_UNCERTAIN:
        metric["uncertain_count"] += 1
        return
    if status == STATUS_UNLABELED:
        return
    metric["labeled_count"] += 1
    if comparison.get("predicted"):
        metric["predicted_count"] += 1
    if status == STATUS_EXACT:
        metric["exact_match_count"] += 1
    elif status == STATUS_NORMALIZED_MATCH:
        metric["normalized_match_count"] += 1
    elif status == STATUS_PARTIAL_MATCH:
        metric["partial_match_count"] += 1
    elif status in EXTRACTOR_MISSING_STATUSES:
        metric["missing_count"] += 1
        metric["extractor_missing_count"] += 1
    elif status == STATUS_CONFLICT:
        metric["conflict_count"] += 1
    elif status == STATUS_WRONG_VALUE:
        metric["wrong_value_count"] += 1
    elif status in {STATUS_SOURCE_NOT_AVAILABLE, STATUS_LEGACY_SOURCE_NOT_AVAILABLE}:
        metric["source_not_available_count"] += 1
    elif status in {STATUS_LEGACY_FIELD_NOT_SERIALIZED, STATUS_SHADOW_COMPONENT_NOT_SERIALIZED}:
        metric["field_not_serialized_count"] += 1
    elif status in {STATUS_REDACTED_NOT_COMPARABLE, STATUS_SHADOW_REDACTED_NOT_COMPARABLE}:
        metric["redacted_not_comparable_count"] += 1
    elif status == STATUS_UNSUPPORTED_VALUE_TYPE:
        metric["unsupported_value_type_count"] += 1
    if confidence is not None:
        if confidence < 0.70 and _status_correct(status):
            metric["low_confidence_but_correct_count"] += 1
        if confidence >= 0.80 and status == STATUS_WRONG_VALUE:
            metric["high_confidence_but_wrong_count"] += 1


def _finalize_metric(metric):
    metric = dict(metric)
    labeled = metric.get("labeled_count", 0)
    predicted = metric.get("predicted_count", 0)
    correct = metric.get("exact_match_count", 0) + metric.get("normalized_match_count", 0)
    metric["precision"] = round(correct / predicted, 4) if predicted else 0.0
    metric["recall"] = round(correct / labeled, 4) if labeled else 0.0
    metric["exact_match_rate"] = round(metric.get("exact_match_count", 0) / labeled, 4) if labeled else 0.0
    metric["normalized_match_rate"] = round(correct / labeled, 4) if labeled else 0.0
    metric["partial_match_rate"] = round(metric.get("partial_match_count", 0) / labeled, 4) if labeled else 0.0
    metric["missing_rate"] = round(metric.get("missing_count", 0) / labeled, 4) if labeled else 0.0
    metric["source_not_available_rate"] = round(metric.get("source_not_available_count", 0) / labeled, 4) if labeled else 0.0
    metric["field_not_serialized_rate"] = round(metric.get("field_not_serialized_count", 0) / labeled, 4) if labeled else 0.0
    metric["redacted_not_comparable_rate"] = round(metric.get("redacted_not_comparable_count", 0) / labeled, 4) if labeled else 0.0
    metric["wrong_value_rate"] = round(metric.get("wrong_value_count", 0) / labeled, 4) if labeled else 0.0
    return metric


def _confidence_band(confidence):
    if confidence is None:
        return "unavailable"
    for name, low, high in CONFIDENCE_BANDS:
        if low <= confidence < high:
            return name
    return "unavailable"


def _build_confidence_calibration(comparison_rows):
    by_field = {}
    for field_name in CRITICAL_FIELDS:
        labeled_rows = [
            row
            for row in comparison_rows
            if row["field"] == field_name
            and row["system"] == SYSTEM_SHADOW
            and row["status"] not in {STATUS_UNLABELED, STATUS_GOLD_UNCERTAIN}
        ]
        rows = [row for row in labeled_rows if row.get("predicted")]
        band_counts = defaultdict(lambda: {"total": 0, "correct": 0, "wrong": 0, "partial": 0})
        for row in rows:
            band = _confidence_band(row.get("confidence"))
            band_counts[band]["total"] += 1
            if _status_correct(row["status"]):
                band_counts[band]["correct"] += 1
            elif _status_partial(row["status"]):
                band_counts[band]["partial"] += 1
            elif row["status"] == STATUS_WRONG_VALUE:
                band_counts[band]["wrong"] += 1
        threshold_rows = []
        for threshold in [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90]:
            selected = [
                row
                for row in rows
                if row.get("confidence") is not None and row.get("confidence") >= threshold
            ]
            correct = sum(1 for row in selected if _status_correct(row["status"]))
            precision = round(correct / len(selected), 4) if selected else 0.0
            recall = round(correct / len(labeled_rows), 4) if labeled_rows else 0.0
            review_rate = round(1.0 - (len(selected) / len(labeled_rows)), 4) if labeled_rows else 1.0
            f1 = round((2 * precision * recall / (precision + recall)), 4) if precision + recall else 0.0
            threshold_rows.append(
                {
                    "threshold": threshold,
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                    "review_rate": review_rate,
                }
            )
        by_field[field_name] = {
            "labeled_count": len(labeled_rows),
            "predicted_count": len(rows),
            "bands": {key: dict(value) for key, value in sorted(band_counts.items())},
            "recommended_threshold_candidates": threshold_rows,
            "do_not_apply_automatically": True,
            "small_sample_warning": len(labeled_rows) < 30,
        }
    return by_field


def _winner(legacy_status, shadow_status):
    legacy_correct = _status_correct(legacy_status)
    shadow_correct = _status_correct(shadow_status)
    if legacy_correct and shadow_correct:
        return WINNER_BOTH
    if legacy_correct:
        return WINNER_LEGACY
    if shadow_correct:
        return WINNER_SHADOW
    if (
        legacy_status == STATUS_UNLABELED
        or shadow_status == STATUS_UNLABELED
        or _status_unavailable(legacy_status)
        or _status_unavailable(shadow_status)
    ):
        return WINNER_UNKNOWN
    return WINNER_NEITHER


def _adjudication_category(legacy_status, shadow_status):
    if legacy_status == STATUS_GOLD_UNCERTAIN or shadow_status == STATUS_GOLD_UNCERTAIN:
        return ADJ_GOLD_UNCERTAIN
    if legacy_status == STATUS_UNLABELED or shadow_status == STATUS_UNLABELED:
        return ADJ_UNLABELED
    legacy_correct = _status_correct(legacy_status)
    shadow_correct = _status_correct(shadow_status)
    if legacy_correct and shadow_correct:
        return ADJ_BOTH_CORRECT
    if legacy_correct and _status_missing(shadow_status):
        return ADJ_LEGACY_CORRECT_SHADOW_MISSING
    if shadow_correct and _status_missing(legacy_status):
        return ADJ_LEGACY_MISSING_SHADOW_CORRECT
    if legacy_correct:
        return ADJ_LEGACY_CORRECT_SHADOW_WRONG
    if shadow_correct:
        return ADJ_SHADOW_CORRECT_LEGACY_WRONG
    if _status_missing(legacy_status) and _status_missing(shadow_status):
        return ADJ_BOTH_MISSING
    return ADJ_BOTH_WRONG


def _recommended_action(winner, legacy_status, shadow_status):
    if winner == WINNER_SHADOW:
        return ACTION_SHADOW_EXPERIMENT
    if winner == WINNER_LEGACY:
        return ACTION_KEEP_LEGACY
    if winner == WINNER_BOTH:
        return ACTION_KEEP_LEGACY
    if _status_unavailable(legacy_status) or _status_unavailable(shadow_status):
        return ACTION_MORE_GOLD
    if _status_missing(legacy_status) and _status_missing(shadow_status):
        return ACTION_IMPROVE_CANDIDATES
    if shadow_status == STATUS_PARTIAL_MATCH:
        return ACTION_RESOLVER_TUNING
    if winner == WINNER_UNKNOWN:
        return ACTION_MORE_GOLD
    return ACTION_REVIEW_REQUIRED


def _prediction_metadata(prediction):
    if not isinstance(prediction, dict):
        return {}
    metadata = prediction.get("metadata_summary")
    if isinstance(metadata, dict):
        return metadata
    selected = prediction.get("selected_candidate")
    if isinstance(selected, dict):
        metadata = selected.get("metadata") or selected.get("metadata_summary")
        if isinstance(metadata, dict):
            return metadata
    metadata = prediction.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _prediction_source_name(prediction):
    if isinstance(prediction, dict):
        return _text(prediction.get("source"))
    return ""


def _candidate_group_correct(comparisons, group_name):
    comparison = comparisons.get(group_name, {}) or {}
    return _status_correct(comparison.get("status"))


def _classify_error_reason(field_name, system_name, prediction, comparisons):
    if system_name != SYSTEM_SHADOW:
        return ""
    metadata = _prediction_metadata(prediction)
    if field_name == FIELD_LOAD_NUMBER:
        if _candidate_group_correct(comparisons, SYSTEM_SHADOW_CANDIDATE_BEST):
            return "gold_primary_id_in_candidates_not_selected"
        if metadata.get("is_pickup_delivery_reference"):
            return "selected_pickup_number_instead_of_primary_load"
        if metadata.get("is_stop_level_reference"):
            hint = _text(metadata.get("id_type_hint")).lower()
            if hint == "bol":
                return "selected_bol_instead_of_primary_load"
            if hint == "po":
                return "selected_po_reference_instead_of_primary_load"
            return "selected_stop_reference_instead_of_primary_load"
        if metadata.get("is_driver_truck_trailer_noise"):
            return "selected_driver_truck_trailer_noise"
        hint = _text(metadata.get("id_type_hint")).lower()
        if hint == "po":
            return "selected_po_reference_instead_of_primary_load"
        if hint == "bol":
            return "selected_bol_instead_of_primary_load"
        if hint in {"reference", "customer_ref", "pickup_ref", "delivery_ref"}:
            if hint == "customer_ref":
                return "selected_customer_reference_instead_of_primary_load"
            if hint == "pickup_ref":
                return "selected_pickup_number_instead_of_primary_load"
            if hint == "delivery_ref":
                return "selected_delivery_number_instead_of_primary_load"
            return "selected_customer_reference_instead_of_primary_load"
        method = _text(metadata.get("pairing_method"))
        if method.startswith("table_"):
            return "selected_table_neighbor_wrong_cell"
        if "layout" in _prediction_source_name(prediction).lower() or method:
            if method == "same_row_right":
                return "selected_layout_same_row_wrong_pair"
            if method == "nearby_row":
                return "selected_nearby_row_wrong_pair"
            return "selected_layout_same_row_wrong_pair"
        return "unknown"
    if field_name == FIELD_TOTAL_CARRIER_RATE:
        if _candidate_group_correct(comparisons, SYSTEM_SHADOW_CANDIDATE_BEST):
            return "gold_total_in_candidates_not_selected"
        context = _text(metadata.get("money_context")).lower()
        if context == "per_unit_rate" or metadata.get("is_per_unit_rate"):
            return "selected_per_unit_rate_instead_of_total"
        if context in {"linehaul", "linehaul_total", "line_item_rate"}:
            return "selected_linehaul_instead_of_total"
        if context == "accessorial":
            return "selected_accessorial_instead_of_total"
        if context in {"deduction", "fee"}:
            return "selected_deduction_or_fee"
        if context == "quickpay":
            return "selected_quickpay_fee"
        if context in {"fuel_advance"}:
            return "selected_fuel_advance_or_comcheck"
        if context == "penalty":
            return "selected_tracking_hold_or_penalty"
        if context == "payment_terms_amount":
            return "selected_payment_terms_amount"
        if context in {"total_rate", "total_cost", "total_carrier_pay", "estimated_rate_to_truck", "agreed_rate_total"}:
            method = _text(metadata.get("pairing_method"))
            if method.startswith("table_"):
                return "selected_wrong_table_cell"
            return "selected_wrong_money_context"
        if context and context != "carrier_pay":
            return "selected_wrong_money_context"
        return "unknown"
    return ""


def _candidate_group_has_correct(comparison_index, document_id, field_name):
    for system_name in [
        SYSTEM_SHADOW_CANDIDATE_BEST,
        SYSTEM_SHADOW_BEST_INDEPENDENT,
        SYSTEM_SHADOW_BEST_LAYOUT,
        SYSTEM_LEGACY_FALLBACK_CANDIDATE,
    ]:
        row = comparison_index.get((document_id, field_name, system_name), {}) or {}
        if _status_correct(row.get("status")) or _status_partial(row.get("status")):
            return True
    return False


def _candidate_group_correct_with_metadata(comparison_index, document_id, field_name, predicate):
    for system_name in [
        SYSTEM_SHADOW_CANDIDATE_BEST,
        SYSTEM_SHADOW_BEST_INDEPENDENT,
        SYSTEM_SHADOW_BEST_LAYOUT,
        SYSTEM_LEGACY_FALLBACK_CANDIDATE,
    ]:
        row = comparison_index.get((document_id, field_name, system_name), {}) or {}
        if not (_status_correct(row.get("status")) or _status_partial(row.get("status"))):
            continue
        if predicate(row):
            return True
    return False


def _gold_load_values(gold_field):
    values = []
    primary = _gold_scalar_value(gold_field)
    if _text(primary):
        values.append(primary)
    if isinstance(gold_field, dict):
        values.extend(
            value
            for value in gold_field.get("alternate_acceptable_values", []) or []
            if _text(value)
        )
    return values


def _load_value_matches(candidate_value, gold_values):
    candidate_normalized = normalize_load_number(candidate_value)
    return bool(
        candidate_normalized
        and any(candidate_normalized == normalize_load_number(value) for value in gold_values)
    )


def _load_value_hashes(gold_values):
    import hashlib

    hashes = set()
    for value in gold_values or []:
        normalized = normalize_load_number(value)
        if normalized:
            hashes.add(hashlib.sha256(normalized.encode("utf-8")).hexdigest())
    return hashes


def _money_value_matches(candidate_value, gold_value) -> bool:
    candidate_normalized = normalize_money(candidate_value)
    gold_normalized = normalize_money(gold_value)
    return bool(candidate_normalized and gold_normalized and candidate_normalized == gold_normalized)


def _money_value_hashes(gold_value):
    import hashlib

    normalized = normalize_money(gold_value)
    if not normalized:
        return set()
    return {hashlib.sha256(normalized.encode("utf-8")).hexdigest()}


def _load_inventory(record):
    payload = _private_eval_values(record)
    inventory = payload.get("load_identity_candidate_inventory", [])
    return inventory if isinstance(inventory, list) else []


def _rate_inventory(record):
    payload = _private_eval_values(record)
    inventory = payload.get("rate_money_candidate_inventory", [])
    return inventory if isinstance(inventory, list) else []


def _load_visibility_probe(record):
    payload = _private_eval_values(record)
    probe = payload.get("load_visibility_probe", {})
    return probe if isinstance(probe, dict) else {}


def _rate_visibility_probe(record):
    payload = _private_eval_values(record)
    probe = payload.get("rate_visibility_probe", {})
    return probe if isinstance(probe, dict) else {}


def _hash_set(probe, key):
    return set(_text(value) for value in (probe.get(key, []) or []) if _text(value))


def _load_visibility_status(record, gold_hashes):
    probe = _load_visibility_probe(record)
    if not probe:
        return {
            "visible_in_full_text": False,
            "visible_in_lines": False,
            "visible_in_layout_words": False,
            "visible_in_layout_tables": False,
            "visibility_available": False,
        }
    return {
        "visible_in_full_text": bool(gold_hashes & _hash_set(probe, "full_text_token_hashes")),
        "visible_in_lines": bool(gold_hashes & _hash_set(probe, "line_token_hashes")),
        "visible_in_layout_words": bool(gold_hashes & _hash_set(probe, "layout_word_token_hashes")),
        "visible_in_layout_tables": bool(gold_hashes & _hash_set(probe, "layout_table_token_hashes")),
        "visibility_available": True,
    }


def _rate_visibility_status(record, gold_hashes):
    probe = _rate_visibility_probe(record)
    if not probe:
        return {
            "visible_in_full_text": False,
            "visible_in_lines": False,
            "visible_in_layout_words": False,
            "visible_in_layout_tables": False,
            "visibility_available": False,
        }
    return {
        "visible_in_full_text": bool(gold_hashes & _hash_set(probe, "full_text_money_hashes")),
        "visible_in_lines": bool(gold_hashes & _hash_set(probe, "line_money_hashes")),
        "visible_in_layout_words": bool(gold_hashes & _hash_set(probe, "layout_word_money_hashes")),
        "visible_in_layout_tables": bool(gold_hashes & _hash_set(probe, "layout_table_money_hashes")),
        "visibility_available": True,
    }


def _rate_inventory_matching_gold(record, gold_value):
    return [
        item
        for item in _rate_inventory(record)
        if isinstance(item, dict) and _money_value_matches(item.get("value"), gold_value)
    ]


def _rate_inventory_context(item):
    metadata = item.get("metadata_summary", {}) if isinstance(item, dict) else {}
    return _text(metadata.get("money_context")) or "unknown"


def _rate_inventory_safety(item):
    metadata = item.get("metadata_summary", {}) if isinstance(item, dict) else {}
    return _text(metadata.get("rate_safety")) or "unknown"


def _rate_inventory_metadata(item):
    metadata = item.get("metadata_summary", {}) if isinstance(item, dict) else {}
    return metadata if isinstance(metadata, dict) else {}


def _rate_context_group(money_context):
    context = _text(money_context)
    if context == "total_carrier_pay":
        return "total_carrier_pay"
    if context == "carrier_freight_pay":
        return "carrier_freight_pay"
    if context in {"linehaul", "linehaul_total", "line_item_rate"}:
        return "linehaul"
    if context in {"total_rate", "total_cost", "agreed_rate_total"}:
        return "grand_total"
    if context == "estimated_rate_to_truck":
        return "estimated_rate_to_truck"
    return "other"


def _empty_rate_context_value_summary():
    return {
        "present": False,
        "nonblank": False,
        "matches_gold": False,
        "matches_shadow": False,
        "value_count": 0,
        "nonblank_value_count": 0,
    }


def _rate_context_value_summary(record, gold_value="", selected_value=""):
    groups = {
        "total_carrier_pay": _empty_rate_context_value_summary(),
        "carrier_freight_pay": _empty_rate_context_value_summary(),
        "linehaul": _empty_rate_context_value_summary(),
        "grand_total": _empty_rate_context_value_summary(),
        "estimated_rate_to_truck": _empty_rate_context_value_summary(),
    }
    for item in _rate_inventory(record):
        if not isinstance(item, dict):
            continue
        group = _rate_context_group(_rate_inventory_context(item))
        if group not in groups:
            continue
        value = item.get("value")
        normalized = normalize_money(value)
        bucket = groups[group]
        bucket["present"] = True
        bucket["value_count"] += 1
        if normalized:
            bucket["nonblank"] = True
            bucket["nonblank_value_count"] += 1
        if _money_value_matches(value, gold_value):
            bucket["matches_gold"] = True
        if _money_value_matches(value, selected_value):
            bucket["matches_shadow"] = True
    return groups


def _rate_candidate_summary(record):
    inventory = [item for item in _rate_inventory(record) if isinstance(item, dict)]
    context_counts = Counter()
    safe = risky = unsafe = unknown = 0
    amount_count = 0
    for item in inventory:
        amount_count += 1
        context = _rate_inventory_context(item)
        safety = _rate_inventory_safety(item)
        context_counts[context] += 1
        if safety == "safe":
            safe += 1
        elif safety == "risky":
            risky += 1
        elif safety == "unsafe":
            unsafe += 1
        else:
            unknown += 1
    return {
        "safe_total_candidates": safe,
        "risky_total_candidates": risky,
        "unsafe_money_candidates": unsafe,
        "unknown_money_candidates": unknown,
        "candidate_amount_count": amount_count,
        "candidate_context_counts": dict(context_counts.most_common()),
    }


def _gold_rate_visible_in_artifact(record, gold_value):
    visibility = _rate_visibility_status(record, _money_value_hashes(gold_value))
    return {
        "visible_in_text": visibility["visible_in_full_text"] or visibility["visible_in_lines"],
        "visible_in_layout": visibility["visible_in_layout_words"] or visibility["visible_in_layout_tables"],
        "visible_in_table": visibility["visible_in_layout_tables"],
        "visibility_available": visibility["visibility_available"],
    }


def _build_load_candidate_recall_summary(gold_labels, audit_index):
    summary = {
        "evaluated_docs": 0,
        "gold_load_in_any_candidate": 0,
        "gold_load_in_independent_candidate": 0,
        "gold_load_in_layout_candidate": 0,
        "gold_load_in_header_candidate": 0,
        "gold_load_in_table_candidate": 0,
        "gold_load_in_legacy_fallback_candidate": 0,
        "gold_load_not_in_candidates": 0,
        "gold_load_visible_in_text_but_not_candidate": 0,
        "gold_load_visible_in_layout_but_not_candidate": 0,
        "gold_load_requires_ocr_or_vision": 0,
        "candidate_missing_reason_counts": {},
        "documents": [],
        "private_values_printed": False,
        "raw_text_printed": False,
    }
    missing_reasons = Counter()
    for label in gold_labels or []:
        status = _text(label.get("label_status")) or LABEL_UNLABELED
        if status in {LABEL_UNLABELED, LABEL_SKIPPED}:
            continue
        gold = label.get("gold", {}) or {}
        gold_field = gold.get(FIELD_LOAD_NUMBER, {})
        gold_values = _gold_load_values(gold_field)
        if not gold_values:
            continue
        summary["evaluated_docs"] += 1
        record = _find_record(label, audit_index)
        inventory = _load_inventory(record)
        matching = [
            candidate
            for candidate in inventory
            if isinstance(candidate, dict)
            and _load_value_matches(candidate.get("value"), gold_values)
        ]
        flags = {
            "any": bool(matching),
            "independent": any(candidate.get("independent") for candidate in matching),
            "layout": any(candidate.get("layout_based") for candidate in matching),
            "header": any(candidate.get("header_candidate") for candidate in matching),
            "table": any(candidate.get("table_based") for candidate in matching),
            "legacy_fallback": any(candidate.get("legacy_fallback") for candidate in matching),
        }
        if flags["any"]:
            summary["gold_load_in_any_candidate"] += 1
        if flags["independent"]:
            summary["gold_load_in_independent_candidate"] += 1
        if flags["layout"]:
            summary["gold_load_in_layout_candidate"] += 1
        if flags["header"]:
            summary["gold_load_in_header_candidate"] += 1
        if flags["table"]:
            summary["gold_load_in_table_candidate"] += 1
        if flags["legacy_fallback"]:
            summary["gold_load_in_legacy_fallback_candidate"] += 1
        visibility = _load_visibility_status(record, _load_value_hashes(gold_values))
        visible_text = visibility["visible_in_full_text"] or visibility["visible_in_lines"]
        visible_layout = visibility["visible_in_layout_words"] or visibility["visible_in_layout_tables"]
        if not flags["any"]:
            summary["gold_load_not_in_candidates"] += 1
            triage = record.get("triage", {}) if isinstance(record, dict) else {}
            artifact = record.get("artifact_summary", {}) if isinstance(record, dict) else {}
            if visible_text:
                missing_reason = "gold_load_visible_in_text_but_not_candidate"
                summary["gold_load_visible_in_text_but_not_candidate"] += 1
            elif visible_layout:
                missing_reason = "gold_load_visible_in_layout_but_not_candidate"
                summary["gold_load_visible_in_layout_but_not_candidate"] += 1
            elif triage.get("ocr_required") or not artifact.get("full_text_present"):
                missing_reason = "gold_load_requires_ocr_or_vision"
                summary["gold_load_requires_ocr_or_vision"] += 1
            elif inventory:
                missing_reason = "gold_load_not_visible_in_current_artifact"
            elif not visibility["visibility_available"]:
                missing_reason = "private_visibility_probe_not_available"
            else:
                missing_reason = "candidate_inventory_empty"
            missing_reasons[missing_reason] += 1
        else:
            missing_reason = ""
        summary["documents"].append(
            {
                "document_id": _text(label.get("document_id")),
                "file_hash_prefix_present": bool(_text(label.get("file_hash"))),
                "gold_load_in_any_candidate": flags["any"],
                "gold_load_in_independent_candidate": flags["independent"],
                "gold_load_in_layout_candidate": flags["layout"],
                "gold_load_in_header_candidate": flags["header"],
                "gold_load_in_table_candidate": flags["table"],
                "gold_load_in_legacy_fallback_candidate": flags["legacy_fallback"],
                "visible_in_text": visible_text,
                "visible_in_layout": visible_layout,
                "missing_reason": missing_reason,
                "raw_value_printed": False,
            }
        )
    summary["candidate_missing_reason_counts"] = dict(missing_reasons.most_common())
    return summary


def _build_load_number_error_analysis(comparison_rows):
    index = {
        (row.get("document_id", ""), row.get("field", ""), row.get("system", "")): row
        for row in comparison_rows
    }
    wrong_rows = [
        row
        for row in comparison_rows
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") == FIELD_LOAD_NUMBER
        and row.get("status") == STATUS_WRONG_VALUE
    ]
    missing_rows = [
        row
        for row in comparison_rows
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") == FIELD_LOAD_NUMBER
        and row.get("status") in EXTRACTOR_MISSING_STATUSES
    ]
    gold_in_candidates = sum(
        1
        for row in wrong_rows + missing_rows
        if _candidate_group_has_correct(index, row.get("document_id", ""), FIELD_LOAD_NUMBER)
    )
    return {
        "wrong_selected_count": len(wrong_rows),
        "missing_count": len(missing_rows),
        "gold_in_candidates_not_selected": gold_in_candidates,
        "gold_not_in_candidates": len(wrong_rows) + len(missing_rows) - gold_in_candidates,
        "wrong_reason_counts": dict(
            Counter(row.get("error_reason") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_candidate_source": dict(
            Counter(row.get("source") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_pairing_method": dict(
            Counter(row.get("pairing_method") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_section_context": dict(
            Counter(row.get("section_context") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_id_type_hint": dict(
            Counter(row.get("id_type_hint") or "unknown" for row in wrong_rows).most_common()
        ),
    }


def _build_rate_error_analysis(comparison_rows):
    index = {
        (row.get("document_id", ""), row.get("field", ""), row.get("system", "")): row
        for row in comparison_rows
    }
    wrong_rows = [
        row
        for row in comparison_rows
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") == FIELD_TOTAL_CARRIER_RATE
        and row.get("status") == STATUS_WRONG_VALUE
    ]
    missing_rows = [
        row
        for row in comparison_rows
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") == FIELD_TOTAL_CARRIER_RATE
        and row.get("status") in EXTRACTOR_MISSING_STATUSES
    ]
    gold_in_candidates = sum(
        1
        for row in wrong_rows + missing_rows
        if _candidate_group_has_correct(index, row.get("document_id", ""), FIELD_TOTAL_CARRIER_RATE)
    )
    return {
        "wrong_selected_count": len(wrong_rows),
        "missing_count": len(missing_rows),
        "gold_total_in_candidates_not_selected": gold_in_candidates,
        "gold_total_not_in_candidates": len(wrong_rows) + len(missing_rows) - gold_in_candidates,
        "high_confidence_wrong_count": sum(
            1 for row in wrong_rows if _safe_float(row.get("confidence")) >= 0.90
        ),
        "wrong_reason_counts": dict(
            Counter(row.get("error_reason") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_candidate_source": dict(
            Counter(row.get("source") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_pairing_method": dict(
            Counter(row.get("pairing_method") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_money_context": dict(
            Counter(row.get("money_context") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_rate_safety": dict(
            Counter(row.get("rate_safety") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_section_context": dict(
            Counter(row.get("section_context") or "unknown" for row in wrong_rows).most_common()
        ),
    }


def _build_rate_wrong_case_summary(comparison_rows):
    index = {
        (row.get("document_id", ""), row.get("field", ""), row.get("system", "")): row
        for row in comparison_rows
    }
    wrong_rows = [
        row
        for row in comparison_rows
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") == FIELD_TOTAL_CARRIER_RATE
        and row.get("status") == STATUS_WRONG_VALUE
    ]
    cases = []
    for row in wrong_rows:
        document_id = _text(row.get("document_id"))
        same_table = _candidate_group_correct_with_metadata(
            index,
            document_id,
            FIELD_TOTAL_CARRIER_RATE,
            lambda candidate_row: _text(candidate_row.get("table_index"))
            == _text(row.get("table_index"))
            and bool(_text(row.get("table_index"))),
        )
        same_page = _candidate_group_correct_with_metadata(
            index,
            document_id,
            FIELD_TOTAL_CARRIER_RATE,
            lambda candidate_row: _text(candidate_row.get("page"))
            == _text(row.get("page"))
            and bool(_text(row.get("page"))),
        )
        cases.append(
            {
                "file_name": _text(row.get("file_name")),
                "document_id": document_id,
                "field": FIELD_TOTAL_CARRIER_RATE,
                "selected_candidate": {
                    "source": _text(row.get("source")),
                    "parser_name": _text(row.get("parser_name")),
                    "pairing_method": _text(row.get("pairing_method")),
                    "confidence": _safe_float(row.get("confidence")),
                    "quality_band": _quality_band_from_confidence(row.get("confidence")),
                    "money_context": _text(row.get("money_context")),
                    "document_region": _text(row.get("document_region")),
                    "section_context": _text(row.get("section_context")),
                    "rate_safety": _text(row.get("rate_safety")),
                    "rate_safety_reason": _text(row.get("rate_safety_reason")),
                    "is_total_pay_candidate": bool(row.get("is_total_pay_candidate")),
                    "is_line_item_only": bool(row.get("is_line_item_only")),
                    "is_per_unit_rate": bool(row.get("is_per_unit_rate")),
                    "is_deduction_or_penalty": bool(row.get("is_deduction_or_penalty")),
                    "is_payment_terms_amount": bool(row.get("is_payment_terms_amount")),
                    "value_shape": dict(row.get("value_shape") or {}),
                },
                "gold_candidate_visibility": {
                    "gold_total_in_any_candidate": _candidate_group_has_correct(
                        index,
                        document_id,
                        FIELD_TOTAL_CARRIER_RATE,
                    ),
                    "gold_total_in_same_table": same_table,
                    "gold_total_in_same_page": same_page,
                    "gold_total_requires_ocr": False,
                },
                "diagnosis": row.get("error_reason") or "unknown",
            }
        )
    return {
        "wrong_selected_count": len(wrong_rows),
        "reason_counts": dict(
            Counter(row.get("error_reason") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_money_context": dict(
            Counter(row.get("money_context") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_section_context": dict(
            Counter(row.get("section_context") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_pairing_method": dict(
            Counter(row.get("pairing_method") or "unknown" for row in wrong_rows).most_common()
        ),
        "gold_total_in_candidates_not_selected": sum(
            1
            for row in wrong_rows
            if _candidate_group_has_correct(
                index,
                row.get("document_id", ""),
                FIELD_TOTAL_CARRIER_RATE,
            )
        ),
        "gold_total_not_in_candidates": sum(
            1
            for row in wrong_rows
            if not _candidate_group_has_correct(
                index,
                row.get("document_id", ""),
                FIELD_TOTAL_CARRIER_RATE,
            )
        ),
        "high_confidence_wrong_count": sum(
            1 for row in wrong_rows if _safe_float(row.get("confidence")) >= 0.90
        ),
        "cases": cases,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _comparison_index(comparison_rows):
    return {
        (row.get("document_id", ""), row.get("field", ""), row.get("system", "")): row
        for row in comparison_rows
    }


def _rate_gold_in_selected_group(index, document_id, selected_row):
    selected_source = _text(selected_row.get("source"))
    selected_parser = _text(selected_row.get("parser_name"))
    return _candidate_group_correct_with_metadata(
        index,
        document_id,
        FIELD_TOTAL_CARRIER_RATE,
        lambda candidate_row: (
            bool(selected_source)
            and _text(candidate_row.get("source")) == selected_source
        )
        or (
            bool(selected_parser)
            and _text(candidate_row.get("parser_name")) == selected_parser
        ),
    )


def _rate_matching_contexts(record, gold_value):
    return {
        _rate_inventory_context(item)
        for item in _rate_inventory_matching_gold(record, gold_value)
        if isinstance(item, dict)
    }


def _rate_context_summary_for_wrong_case(record, gold_value, selected_value):
    summary = _rate_context_value_summary(record, gold_value, selected_value)
    return {
        "total_carrier_pay_value_present": summary["total_carrier_pay"]["nonblank"],
        "total_carrier_pay_value_blank": (
            summary["total_carrier_pay"]["present"]
            and not summary["total_carrier_pay"]["nonblank"]
        ),
        "carrier_freight_pay_value_present": summary["carrier_freight_pay"]["nonblank"],
        "total_carrier_pay_matches_gold": summary["total_carrier_pay"]["matches_gold"],
        "carrier_freight_pay_matches_gold": summary["carrier_freight_pay"]["matches_gold"],
        "candidate_values_summary": summary,
    }


def _classify_residual_wrong_rate(row, record, gold_field, index):
    document_id = _text(row.get("document_id"))
    gold_value = _gold_scalar_value(gold_field)
    selected = _shadow_prediction(record, FIELD_TOTAL_CARRIER_RATE)
    selected_value = _prediction_value(selected)
    selected_context = _text(row.get("money_context")) or "unknown"
    matching_contexts = _rate_matching_contexts(record, gold_value)
    context_summary = _rate_context_value_summary(record, gold_value, selected_value)
    summary = _rate_candidate_summary(record)
    triage = record.get("triage", {}) if isinstance(record, dict) else {}
    visibility = _gold_rate_visible_in_artifact(record, gold_value)
    if _money_value_matches(selected_value, gold_value):
        return "selected_same_amount_but_normalization_failed"
    if _gold_uncertain(gold_field):
        return "selected_amount_correct_but_gold_uncertain"
    if selected_context == "carrier_freight_pay" and "total_carrier_pay" in matching_contexts:
        return "selected_carrier_freight_pay_but_gold_uses_total_carrier_pay"
    if (
        selected_context == "total_carrier_pay"
        and "carrier_freight_pay" in matching_contexts
        and context_summary["total_carrier_pay"]["nonblank"]
    ):
        return "selected_total_carrier_pay_but_gold_uses_carrier_freight_pay"
    if selected_context in {"linehaul", "linehaul_total", "line_item_rate"} and matching_contexts:
        return "selected_linehaul_but_gold_uses_grand_total"
    if selected_context in {
        "total_carrier_pay",
        "total_rate",
        "total_cost",
        "estimated_rate_to_truck",
        "agreed_rate_total",
    } and matching_contexts & {"linehaul", "linehaul_total", "line_item_rate"}:
        return "selected_grand_total_but_gold_uses_linehaul"
    if _candidate_group_has_correct(index, document_id, FIELD_TOTAL_CARRIER_RATE):
        return "gold_total_in_candidates_not_selected"
    if summary.get("safe_total_candidates", 0) > 1 and selected_context in {
        "total_carrier_pay",
        "total_rate",
        "total_cost",
        "estimated_rate_to_truck",
        "agreed_rate_total",
        "carrier_freight_pay",
    }:
        return "multiple_valid_totals_ambiguous"
    if triage.get("ocr_required") and not matching_contexts and not (
        visibility["visible_in_text"] or visibility["visible_in_layout"]
    ):
        return "gold_total_requires_ocr"
    if selected_context in {
        "total_carrier_pay",
        "total_rate",
        "total_cost",
        "estimated_rate_to_truck",
        "agreed_rate_total",
    }:
        return "selected_safe_total_but_gold_differs"
    if not matching_contexts:
        return "gold_total_not_in_candidates"
    return "unknown"


def _rate_wrong_case_payload(row, record, gold_field, index):
    document_id = _text(row.get("document_id"))
    gold_value = _gold_scalar_value(gold_field)
    selected = _shadow_prediction(record, FIELD_TOTAL_CARRIER_RATE)
    selected_value = _prediction_value(selected)
    same_table = _candidate_group_correct_with_metadata(
        index,
        document_id,
        FIELD_TOTAL_CARRIER_RATE,
        lambda candidate_row: _text(candidate_row.get("table_index"))
        == _text(row.get("table_index"))
        and bool(_text(row.get("table_index"))),
    )
    same_page = _candidate_group_correct_with_metadata(
        index,
        document_id,
        FIELD_TOTAL_CARRIER_RATE,
        lambda candidate_row: _text(candidate_row.get("page"))
        == _text(row.get("page"))
        and bool(_text(row.get("page"))),
    )
    return {
        "file_name": _text(row.get("file_name")),
        "document_id": document_id,
        "gold_label_status": _text(row.get("label_status")) or LABEL_LABELED,
        "selected_rate": {
            "source": _text(row.get("source")),
            "parser_name": _text(row.get("parser_name")),
            "confidence": _safe_float(row.get("confidence")),
            "quality_band": _quality_band_from_confidence(row.get("confidence")),
            "money_context": _text(row.get("money_context")),
            "rate_safety": _text(row.get("rate_safety")),
            "document_region": _text(row.get("document_region")),
            "section_context": _text(row.get("section_context")),
            "pairing_method": _text(row.get("pairing_method")),
            "value_shape": {
                "looks_like_money": bool((row.get("value_shape") or {}).get("looks_like_money")),
                "has_currency_symbol": bool(
                    (row.get("value_shape") or {}).get("has_currency_symbol")
                ),
                "amount_magnitude_band": _text(
                    (row.get("value_shape") or {}).get("amount_magnitude_band")
                )
                or "unknown",
            },
        },
        "gold_visibility": {
            "gold_total_in_any_candidate": _candidate_group_has_correct(
                index,
                document_id,
                FIELD_TOTAL_CARRIER_RATE,
            ),
            "gold_total_in_selected_candidate_group": _rate_gold_in_selected_group(
                index,
                document_id,
                row,
            ),
            "gold_total_in_same_table": same_table,
            "gold_total_in_same_page": same_page,
            "gold_total_requires_ocr": bool(
                (record.get("triage", {}) if isinstance(record, dict) else {}).get(
                    "ocr_required"
                )
            )
            and not _rate_inventory_matching_gold(record, gold_value),
        },
        "all_plausible_rate_candidate_summary": _rate_candidate_summary(record),
        "rate_context_value_summary": _rate_context_summary_for_wrong_case(
            record,
            gold_value,
            selected_value,
        ),
        "diagnosis": _classify_residual_wrong_rate(row, record, gold_field, index),
    }


def _build_residual_wrong_rate_forensics(comparison_rows, gold_labels, audit_index):
    index = _comparison_index(comparison_rows)
    label_by_document = {
        _text(label.get("document_id")): label
        for label in gold_labels or []
        if _text(label.get("document_id"))
    }
    wrong_rows = [
        row
        for row in comparison_rows
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") == FIELD_TOTAL_CARRIER_RATE
        and row.get("status") == STATUS_WRONG_VALUE
    ]
    cases = []
    diagnoses = Counter()
    for row in wrong_rows:
        label = label_by_document.get(_text(row.get("document_id")), {}) or {}
        gold = label.get("gold", {}) or {}
        gold_field = gold.get(FIELD_TOTAL_CARRIER_RATE, {})
        record = _find_record(label, audit_index)
        case = _rate_wrong_case_payload(row, record, gold_field, index)
        diagnoses[case["diagnosis"]] += 1
        cases.append(case)
    return {
        "wrong_selected_count": len(wrong_rows),
        "diagnosis_counts": dict(diagnoses.most_common()),
        "wrong_by_money_context": dict(
            Counter(row.get("money_context") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_rate_safety": dict(
            Counter(row.get("rate_safety") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_section_context": dict(
            Counter(row.get("section_context") or "unknown" for row in wrong_rows).most_common()
        ),
        "wrong_by_pairing_method": dict(
            Counter(row.get("pairing_method") or "unknown" for row in wrong_rows).most_common()
        ),
        "high_confidence_wrong_count": sum(
            1 for row in wrong_rows if _safe_float(row.get("confidence")) >= 0.90
        ),
        "cases": cases,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _gold_consistency_reason(case):
    diagnosis = _text(case.get("diagnosis"))
    selected = case.get("selected_rate", {}) or {}
    plausible = case.get("all_plausible_rate_candidate_summary", {}) or {}
    value_summary = (case.get("rate_context_value_summary", {}) or {}).get(
        "candidate_values_summary",
        {},
    ) or {}
    total_pay = value_summary.get("total_carrier_pay", {}) or {}
    carrier_freight = value_summary.get("carrier_freight_pay", {}) or {}
    if diagnosis == "selected_same_amount_but_normalization_failed":
        return "selected_and_gold_are_same_after_normalization"
    if diagnosis == "selected_total_carrier_pay_but_gold_uses_carrier_freight_pay":
        if total_pay.get("nonblank") and not total_pay.get("matches_gold"):
            return "gold_uses_carrier_freight_pay_but_total_carrier_pay_present"
        return "unknown"
    if diagnosis == "selected_carrier_freight_pay_but_gold_uses_total_carrier_pay":
        if not total_pay.get("nonblank") and carrier_freight.get("nonblank"):
            return "gold_uses_total_carrier_pay_but_total_blank_and_carrier_freight_pay_present"
        return "unknown"
    if diagnosis == "selected_grand_total_but_gold_uses_linehaul":
        return "gold_uses_linehaul_but_document_has_explicit_total"
    if diagnosis == "multiple_valid_totals_ambiguous" or plausible.get("safe_total_candidates", 0) > 1:
        return "ambiguous_multiple_totals"
    if diagnosis == "selected_safe_total_but_gold_differs" and selected.get("money_context") in {
        "total_carrier_pay",
        "total_rate",
        "total_cost",
        "estimated_rate_to_truck",
        "agreed_rate_total",
    }:
        return "gold_uses_rate_table_amount_but_document_total_differs"
    if diagnosis == "gold_total_not_in_candidates":
        return "gold_total_not_visible_in_document_artifact"
    return "unknown"


def _build_gold_rate_consistency_audit(residual_wrong_summary):
    cases = list((residual_wrong_summary or {}).get("cases", []) or [])
    reasons = Counter()
    suspect_count = 0
    uncertain_count = 0
    matches_selected = 0
    not_visible = 0
    recommend_review = 0
    review_cases = []
    for case in cases:
        reason = _gold_consistency_reason(case)
        reasons[reason] += 1
        if case.get("gold_label_status") == "uncertain":
            uncertain_count += 1
        if reason == "selected_and_gold_are_same_after_normalization":
            matches_selected += 1
        if reason == "gold_total_not_visible_in_document_artifact":
            not_visible += 1
        if reason != "unknown":
            suspect_count += 1
            recommend_review += 1
            review_cases.append(
                {
                    "file_name": _text(case.get("file_name")),
                    "document_id": _text(case.get("document_id")),
                    "suspect_reason": reason,
                    "diagnosis": _text(case.get("diagnosis")),
                    "private_values_printed": False,
                }
            )
    return {
        "cases_checked": len(cases),
        "gold_label_suspect_count": suspect_count,
        "gold_label_uncertain_count": uncertain_count,
        "gold_rate_matches_selected_but_marked_wrong_count": matches_selected,
        "gold_rate_not_visible_in_artifact_count": not_visible,
        "recommend_human_review_count": recommend_review,
        "suspect_reasons": dict(reasons.most_common()),
        "review_cases": review_cases,
        "gold_files_modified": False,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _classify_missing_rate(label, record, row):
    gold = label.get("gold", {}) if isinstance(label, dict) else {}
    gold_field = gold.get(FIELD_TOTAL_CARRIER_RATE, {})
    gold_value = _gold_scalar_value(gold_field)
    if _gold_uncertain(gold_field):
        return "gold_label_uncertain"
    triage = record.get("triage", {}) if isinstance(record, dict) else {}
    matching = _rate_inventory_matching_gold(record, gold_value)
    if matching:
        if any(
            (_rate_inventory_metadata(item).get("rate_abstained"))
            or (_rate_inventory_metadata(item).get("rate_demoted_from_total_carrier_rate"))
            for item in matching
        ):
            return "rate_in_candidate_but_abstained"
        return "unknown"
    visibility = _gold_rate_visible_in_artifact(record, gold_value)
    if visibility["visible_in_text"]:
        return "rate_visible_in_text_but_no_candidate"
    if visibility["visible_in_layout"]:
        return "rate_visible_in_layout_but_no_candidate"
    if triage.get("ocr_required"):
        return "rate_requires_ocr"
    inventory = [item for item in _rate_inventory(record) if isinstance(item, dict)]
    if inventory:
        safeties = {_rate_inventory_safety(item) for item in inventory}
        if safeties <= {"unsafe"}:
            return "only_unsafe_money_candidates"
        if safeties <= {"unknown"}:
            return "only_unknown_money_context_candidates"
    if row.get("label_status") == LABEL_SKIPPED:
        return "skipped_non_rc"
    return "rate_not_in_artifact_text"


def _build_missing_rate_forensics(comparison_rows, gold_labels, audit_index):
    row_by_document = {
        _text(row.get("document_id")): row
        for row in comparison_rows
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") == FIELD_TOTAL_CARRIER_RATE
        and row.get("status") in EXTRACTOR_MISSING_STATUSES
    }
    cases = []
    reasons = Counter()
    for label in gold_labels or []:
        status = _text(label.get("label_status")) or LABEL_UNLABELED
        if status in {LABEL_UNLABELED, LABEL_SKIPPED}:
            continue
        document_id = _text(label.get("document_id"))
        row = row_by_document.get(document_id)
        if not row:
            continue
        record = _find_record(label, audit_index)
        reason = _classify_missing_rate(label, record, row)
        reasons[reason] += 1
        gold_value = _gold_scalar_value((label.get("gold", {}) or {}).get(FIELD_TOTAL_CARRIER_RATE, {}))
        visibility = _gold_rate_visible_in_artifact(record, gold_value)
        cases.append(
            {
                "file_name": _text(row.get("file_name")),
                "document_id": document_id,
                "reason": reason,
                "gold_rate_visible_in_text": visibility["visible_in_text"],
                "gold_rate_visible_in_layout": visibility["visible_in_layout"],
                "candidate_amount_count": _rate_candidate_summary(record).get("candidate_amount_count", 0),
                "private_values_printed": False,
            }
        )
    return {
        "missing_count": len(cases),
        "reason_counts": dict(reasons.most_common()),
        "gold_rate_visible_in_text_but_not_candidate": reasons.get(
            "rate_visible_in_text_but_no_candidate",
            0,
        ),
        "gold_rate_visible_in_layout_but_not_candidate": reasons.get(
            "rate_visible_in_layout_but_no_candidate",
            0,
        ),
        "gold_rate_in_candidate_but_abstained": reasons.get(
            "rate_in_candidate_but_abstained",
            0,
        ),
        "rate_requires_ocr": reasons.get("rate_requires_ocr", 0),
        "cases": cases,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _classify_table_neighbor_error(row, comparison_index):
    table_context = _text(row.get("table_context_role"))
    table_row = _text(row.get("table_row_role"))
    id_hint = _text(row.get("id_type_hint")).lower()
    penalty = _text(row.get("table_neighbor_penalty_reason"))
    document_id = _text(row.get("document_id"))
    if _candidate_group_has_correct(comparison_index, document_id, FIELD_LOAD_NUMBER):
        return "gold_value_elsewhere_in_header_candidate"
    if table_row == "pickup_delivery_ref_row" or penalty == "pickup_delivery_reference_row":
        return "table_neighbor_from_pickup_delivery_ref_row"
    if table_row == "stop_reference_row" or penalty == "stop_reference_row":
        return "table_neighbor_from_stop_reference_row"
    if id_hint in {"bol", "po", "reference", "customer_ref"} or penalty in {
        "reference_label",
        "po_outside_header_load_info",
        "reference_table",
    }:
        return "table_neighbor_from_bol_or_po_row"
    if table_context == "rate_table" or table_row == "rate_row" or penalty == "rate_or_money_table":
        return "table_neighbor_from_rate_or_money_table"
    if table_context == "carrier_contact_table" or table_row == "carrier_contact_row":
        return "table_neighbor_from_carrier_contact_table"
    if table_context == "signature_footer" or table_row == "footer_row":
        return "table_neighbor_from_signature_or_footer_table"
    if penalty == "multi_value_row":
        return "table_neighbor_from_multi_value_row"
    if penalty == "table_neighbor_missing_header_context":
        return "table_neighbor_missing_header_context"
    if row.get("status") in EXTRACTOR_MISSING_STATUSES:
        return "gold_value_not_in_candidates"
    return "unknown"


def _build_load_table_neighbor_error_summary(comparison_rows):
    index = {
        (row.get("document_id", ""), row.get("field", ""), row.get("system", "")): row
        for row in comparison_rows
    }
    rows = [
        row
        for row in comparison_rows
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") == FIELD_LOAD_NUMBER
        and row.get("status") == STATUS_WRONG_VALUE
        and row.get("error_reason") == "selected_table_neighbor_wrong_cell"
    ]
    reasons = Counter()
    gold_elsewhere = 0
    gold_absent = 0
    for row in rows:
        reason = _classify_table_neighbor_error(row, index)
        reasons[reason] += 1
        if _candidate_group_has_correct(index, row.get("document_id", ""), FIELD_LOAD_NUMBER):
            gold_elsewhere += 1
        else:
            gold_absent += 1
    return {
        "wrong_table_neighbor_count": len(rows),
        "reason_counts": dict(reasons.most_common()),
        "by_table_role": dict(
            Counter(row.get("table_context_role") or "unknown" for row in rows).most_common()
        ),
        "by_table_row_role": dict(
            Counter(row.get("table_row_role") or "unknown" for row in rows).most_common()
        ),
        "by_section_context": dict(
            Counter(row.get("section_context") or "unknown" for row in rows).most_common()
        ),
        "by_pairing_method": dict(
            Counter(row.get("pairing_method") or "unknown" for row in rows).most_common()
        ),
        "by_table_neighbor_safety": dict(
            Counter(row.get("table_neighbor_safety") or "unknown" for row in rows).most_common()
        ),
        "gold_value_available_elsewhere_count": gold_elsewhere,
        "gold_value_not_in_candidates_count": gold_absent,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _classify_remaining_table_neighbor_wrong(row, comparison_index):
    safety = _text(row.get("table_neighbor_safety"))
    table_context = _text(row.get("table_context_role"))
    table_row = _text(row.get("table_row_role"))
    penalty = _text(row.get("table_neighbor_penalty_reason"))
    document_id = _text(row.get("document_id"))
    if _candidate_group_has_correct(comparison_index, document_id, FIELD_LOAD_NUMBER):
        return "table_neighbor_safe_but_gold_elsewhere"
    if row.get("status") in EXTRACTOR_MISSING_STATUSES:
        return "table_neighbor_gold_not_in_candidates"
    if safety == "unknown":
        return "table_neighbor_unknown_context_selected"
    if table_row in {"stop_reference_row", "pickup_delivery_ref_row"} or penalty in {
        "stop_reference_row",
        "pickup_delivery_reference_row",
        "reference_label",
        "reference_table",
        "po_outside_header_load_info",
    }:
        return "table_neighbor_should_be_reference_not_load"
    if penalty == "multi_value_row":
        return "table_neighbor_needs_row_geometry"
    if penalty == "table_neighbor_missing_header_context" or table_context == "unknown":
        return "table_neighbor_needs_column_header_geometry"
    if table_context in {"rate_table", "carrier_contact_table", "signature_footer"}:
        return "table_neighbor_needs_table_boundary_refinement"
    if safety == "safe":
        if table_context and table_context not in {"header_load_info", "unknown"}:
            return "table_neighbor_safe_but_wrong_header_context"
        return "table_neighbor_safe_but_wrong_value_cell"
    return "unknown"


def _quality_band_from_confidence(confidence):
    value = _safe_float(confidence)
    if value is None:
        return "unknown"
    if value >= 0.80:
        return "high"
    if value >= 0.60:
        return "medium"
    return "weak"


def _row_value_shape_summary(row):
    return {
        "neighbor_cell_count": _safe_int(row.get("neighbor_cell_count")),
        "id_like_cell_count_in_row": _safe_int(row.get("id_like_cell_count_in_row")),
        "load_label_cell_count_in_row": _safe_int(row.get("load_label_cell_count_in_row")),
        "reference_label_cell_count_in_row": _safe_int(
            row.get("reference_label_cell_count_in_row")
        ),
        "stop_label_cell_count_in_row": _safe_int(row.get("stop_label_cell_count_in_row")),
        "money_like_cell_count_in_row": _safe_int(row.get("money_like_cell_count_in_row")),
    }


def _classify_table_neighbor_value_cell_diagnosis(row, comparison_index):
    document_id = _text(row.get("document_id"))
    if _candidate_group_has_correct(comparison_index, document_id, FIELD_LOAD_NUMBER):
        return "gold_value_elsewhere_in_text_candidate"
    summary = _row_value_shape_summary(row)
    reference_labels = summary["reference_label_cell_count_in_row"]
    stop_labels = summary["stop_label_cell_count_in_row"]
    load_labels = summary["load_label_cell_count_in_row"]
    id_like = summary["id_like_cell_count_in_row"]
    penalty = _text(row.get("table_neighbor_penalty_reason"))
    pairing_method = _text(row.get("pairing_method"))
    table_row = _text(row.get("table_row_role"))
    if row.get("status") in EXTRACTOR_MISSING_STATUSES:
        return "no_gold_candidate"
    if table_row == "header" and pairing_method == "table_key_value_row":
        return "label_value_alignment_unclear"
    if reference_labels or stop_labels:
        return "ambiguous_multi_id_row" if load_labels else "wrong_value_cell"
    if id_like >= 2:
        return "ambiguous_multi_id_row"
    if penalty in {"table_neighbor_missing_header_context", "multi_value_row"}:
        return "label_value_alignment_unclear"
    if _text(row.get("table_context_role")) == "unknown":
        return "table_fragmentation"
    return "wrong_value_cell"


def _build_load_table_neighbor_value_cell_forensics(comparison_rows):
    index = {
        (row.get("document_id", ""), row.get("field", ""), row.get("system", "")): row
        for row in comparison_rows
    }
    rows = [
        row
        for row in comparison_rows
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") == FIELD_LOAD_NUMBER
        and row.get("status") == STATUS_WRONG_VALUE
        and row.get("error_reason") == "selected_table_neighbor_wrong_cell"
    ]
    diagnoses = Counter()
    cases = []
    for row in rows:
        document_id = _text(row.get("document_id"))
        diagnosis = _classify_table_neighbor_value_cell_diagnosis(row, index)
        diagnoses[diagnosis] += 1
        same_table = _candidate_group_correct_with_metadata(
            index,
            document_id,
            FIELD_LOAD_NUMBER,
            lambda candidate_row: _text(candidate_row.get("table_index"))
            == _text(row.get("table_index"))
            and bool(_text(row.get("table_index"))),
        )
        same_row = _candidate_group_correct_with_metadata(
            index,
            document_id,
            FIELD_LOAD_NUMBER,
            lambda candidate_row: _text(candidate_row.get("table_index"))
            == _text(row.get("table_index"))
            and _text(candidate_row.get("row_index")) == _text(row.get("row_index"))
            and bool(_text(row.get("row_index"))),
        )
        cases.append(
            {
                "file_name": _text(row.get("file_name")),
                "document_id": document_id,
                "field": FIELD_LOAD_NUMBER,
                "selected_candidate": {
                    "source": _text(row.get("source")),
                    "parser_name": _text(row.get("parser_name")),
                    "pairing_method": _text(row.get("pairing_method")),
                    "confidence": _safe_float(row.get("confidence")),
                    "quality_band": _quality_band_from_confidence(row.get("confidence")),
                    "value_shape": dict(row.get("value_shape") or {}),
                    "table_context_role": _text(row.get("table_context_role")),
                    "table_row_role": _text(row.get("table_row_role")),
                    "table_neighbor_safety": _text(row.get("table_neighbor_safety")),
                    "row_value_shape_summary": _row_value_shape_summary(row),
                    "neighbor_cell_count": _safe_int(row.get("neighbor_cell_count")),
                    "id_like_cell_count_in_row": _safe_int(row.get("id_like_cell_count_in_row")),
                    "load_label_cell_count_in_row": _safe_int(
                        row.get("load_label_cell_count_in_row")
                    ),
                    "reference_label_cell_count_in_row": _safe_int(
                        row.get("reference_label_cell_count_in_row")
                    ),
                    "stop_label_cell_count_in_row": _safe_int(
                        row.get("stop_label_cell_count_in_row")
                    ),
                    "money_like_cell_count_in_row": _safe_int(
                        row.get("money_like_cell_count_in_row")
                    ),
                },
                "gold_candidate_visibility": {
                    "gold_in_any_candidate": _candidate_group_has_correct(
                        index,
                        document_id,
                        FIELD_LOAD_NUMBER,
                    ),
                    "gold_in_same_table": same_table,
                    "gold_in_same_row": same_row,
                    "gold_in_same_page": _candidate_group_correct_with_metadata(
                        index,
                        document_id,
                        FIELD_LOAD_NUMBER,
                        lambda candidate_row: _text(candidate_row.get("page"))
                        == _text(row.get("page"))
                        and bool(_text(row.get("page"))),
                    ),
                    "gold_requires_ocr": False,
                },
                "diagnosis": diagnosis,
            }
        )
    return {
        "wrong_table_neighbor_count": len(rows),
        "diagnosis_counts": dict(diagnoses.most_common()),
        "cases": cases,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _build_remaining_table_neighbor_wrong_summary(comparison_rows):
    index = {
        (row.get("document_id", ""), row.get("field", ""), row.get("system", "")): row
        for row in comparison_rows
    }
    rows = [
        row
        for row in comparison_rows
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") == FIELD_LOAD_NUMBER
        and row.get("status") == STATUS_WRONG_VALUE
        and row.get("error_reason") == "selected_table_neighbor_wrong_cell"
    ]
    reasons = Counter()
    safety_counts = Counter()
    for row in rows:
        reasons[_classify_remaining_table_neighbor_wrong(row, index)] += 1
        safety_counts[_text(row.get("table_neighbor_safety")) or "unknown"] += 1
    needs_geometry = sum(
        count
        for reason, count in reasons.items()
        if reason
        in {
            "table_neighbor_needs_row_geometry",
            "table_neighbor_needs_column_header_geometry",
            "table_neighbor_needs_table_boundary_refinement",
        }
    )
    return {
        "count": len(rows),
        "reason_counts": dict(reasons.most_common()),
        "safe_count": safety_counts.get("safe", 0),
        "risky_count": safety_counts.get("risky", 0),
        "unknown_count": safety_counts.get("unknown", 0),
        "gold_elsewhere_count": reasons.get("table_neighbor_safe_but_gold_elsewhere", 0),
        "needs_geometry_count": needs_geometry,
        "should_be_reference_count": reasons.get(
            "table_neighbor_should_be_reference_not_load",
            0,
        ),
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _unique_audit_records(indexed):
    seen = set()
    records = []
    for record in (indexed or {}).values():
        marker = id(record)
        if marker in seen:
            continue
        seen.add(marker)
        records.append(record)
    return records


def _load_inventory_abstention_rows(audit_records):
    rows = []
    for record in audit_records or []:
        payload = _private_eval_values(record)
        inventory = (
            payload.get("load_identity_candidate_inventory", [])
            if isinstance(payload, dict)
            else []
        )
        for item in inventory or []:
            if not isinstance(item, dict):
                continue
            metadata = (
                item.get("metadata_summary", {})
                if isinstance(item.get("metadata_summary"), dict)
                else {}
            )
            abstained = bool(metadata.get("table_neighbor_abstained"))
            demoted = bool(metadata.get("table_neighbor_demoted_from_load_number"))
            if not (abstained or demoted):
                continue
            rows.append(
                {
                    "system": "load_identity_candidate_inventory",
                    "field": _text(item.get("field")),
                    "table_neighbor_abstained": abstained,
                    "table_neighbor_demoted_from_load_number": demoted,
                    "table_neighbor_abstention_reason": _text(
                        metadata.get("table_neighbor_abstention_reason")
                        or metadata.get("table_neighbor_penalty_reason")
                    ),
                    "selection_policy": _text(metadata.get("selection_policy")),
                }
            )
    return rows


def _build_table_neighbor_abstention_summary(comparison_rows, audit_records=None):
    rows = [
        row
        for row in comparison_rows
        if row.get("field") == FIELD_LOAD_NUMBER
        and row.get("table_neighbor_abstained")
        and row.get("system")
        in {
            SYSTEM_SHADOW,
            SYSTEM_SHADOW_CANDIDATE_BEST,
            SYSTEM_SHADOW_BEST_INDEPENDENT,
            SYSTEM_SHADOW_BEST_LAYOUT,
        }
    ]
    inventory_rows = _load_inventory_abstention_rows(audit_records)
    rows = rows + inventory_rows
    return {
        "abstained_candidate_count": len(rows),
        "demoted_from_load_number_count": sum(
            1 for row in rows if row.get("table_neighbor_demoted_from_load_number")
        ),
        "reason_counts": dict(
            Counter(row.get("table_neighbor_abstention_reason") or "unknown" for row in rows).most_common()
        ),
        "selection_policy_counts": dict(
            Counter(row.get("selection_policy") or "unknown" for row in rows).most_common()
        ),
        "by_system": dict(Counter(row.get("system") or "unknown" for row in rows).most_common()),
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _rate_inventory_abstention_rows(audit_records):
    rows = []
    for record in audit_records or []:
        payload = _private_eval_values(record)
        inventory = (
            payload.get("rate_money_candidate_inventory", [])
            if isinstance(payload, dict)
            else []
        )
        for item in inventory or []:
            if not isinstance(item, dict):
                continue
            metadata = (
                item.get("metadata_summary", {})
                if isinstance(item.get("metadata_summary"), dict)
                else {}
            )
            abstained = bool(metadata.get("rate_abstained"))
            demoted = bool(metadata.get("rate_demoted_from_total_carrier_rate"))
            if not (abstained or demoted):
                continue
            rows.append(
                {
                    "system": "rate_money_candidate_inventory",
                    "field": _text(item.get("field")),
                    "rate_abstained": abstained,
                    "rate_demoted_from_total_carrier_rate": demoted,
                    "rate_abstention_reason": _text(
                        metadata.get("rate_abstention_reason")
                        or metadata.get("rate_safety_reason")
                    ),
                    "selection_policy": _text(metadata.get("selection_policy")),
                    "money_context": _text(metadata.get("money_context")),
                    "rate_safety": _text(metadata.get("rate_safety")),
                }
            )
    return rows


def _build_rate_abstention_summary(comparison_rows, audit_records=None):
    rows = [
        row
        for row in comparison_rows
        if row.get("field") == FIELD_TOTAL_CARRIER_RATE
        and row.get("rate_abstained")
        and row.get("system")
        in {
            SYSTEM_SHADOW,
            SYSTEM_SHADOW_CANDIDATE_BEST,
            SYSTEM_SHADOW_BEST_INDEPENDENT,
            SYSTEM_SHADOW_BEST_LAYOUT,
        }
    ]
    inventory_rows = _rate_inventory_abstention_rows(audit_records)
    rows = rows + inventory_rows
    return {
        "abstained_candidate_count": len(rows),
        "demoted_from_total_carrier_rate_count": sum(
            1 for row in rows if row.get("rate_demoted_from_total_carrier_rate")
        ),
        "reason_counts": dict(
            Counter(row.get("rate_abstention_reason") or "unknown" for row in rows).most_common()
        ),
        "selection_policy_counts": dict(
            Counter(row.get("selection_policy") or "unknown" for row in rows).most_common()
        ),
        "money_context_counts": dict(
            Counter(row.get("money_context") or "unknown" for row in rows).most_common()
        ),
        "rate_safety_counts": dict(
            Counter(row.get("rate_safety") or "unknown" for row in rows).most_common()
        ),
        "by_system": dict(Counter(row.get("system") or "unknown" for row in rows).most_common()),
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _ocr_backlog_doc_type(triage, artifact):
    if triage.get("ocr_required"):
        return "scanned"
    if triage.get("pdf_type") in {"scanned", "image_heavy"}:
        return _text(triage.get("pdf_type"))
    if not artifact.get("full_text_present") or _safe_int(triage.get("native_text_token_count")) <= 10:
        return "low_text"
    if _safe_int(artifact.get("word_count")) <= 0 and _safe_int(artifact.get("table_count")) <= 0:
        return "image_heavy"
    return "unknown"


def _build_ocr_vision_backlog_summary(gold_labels, audit_index):
    docs = []
    for label in gold_labels or []:
        status = _text(label.get("label_status")) or LABEL_UNLABELED
        if status == LABEL_UNLABELED:
            continue
        record = _find_record(label, audit_index)
        if not isinstance(record, dict):
            continue
        triage = record.get("triage", {}) or {}
        artifact = record.get("artifact_summary", {}) or {}
        text_blocked = bool(triage.get("ocr_required")) or (
            not artifact.get("full_text_present")
            and _safe_int(artifact.get("word_count")) <= 0
        )
        gold = label.get("gold", {}) or {}
        skipped_non_rc = status == LABEL_SKIPPED
        gold_load_known = bool(_gold_load_values(gold.get(FIELD_LOAD_NUMBER, {})))
        gold_rate_known = bool(_gold_scalar_value(gold.get(FIELD_TOTAL_CARRIER_RATE, {})))
        gold_stop_known = bool(gold.get(FIELD_PICKUP_STOPS)) or bool(
            gold.get(FIELD_DELIVERY_STOPS)
        )
        if not skipped_non_rc and not text_blocked and not triage.get("ocr_required"):
            continue
        fields = []
        if gold_load_known:
            fields.append(FIELD_LOAD_NUMBER)
        if gold_rate_known:
            fields.append(FIELD_TOTAL_CARRIER_RATE)
        if gold_stop_known:
            fields.append("stops")
        if skipped_non_rc:
            route = "document_classification"
        elif triage.get("ocr_required"):
            route = "ocr"
        else:
            route = "manual_review"
        docs.append(
            {
                "document_id": _text(label.get("document_id")),
                "file_name": _text(record.get("file_name")),
                "pdf_type": _ocr_backlog_doc_type(triage, artifact),
                "page_count": _safe_int(triage.get("page_count") or artifact.get("page_count")),
                "native_text_token_count": _safe_int(triage.get("native_text_token_count")),
                "layout_provider_status": _text(
                    (artifact.get("layout_provider_summary", {}) or {}).get("status")
                ),
                "gold_load_known": gold_load_known,
                "gold_rate_known": gold_rate_known,
                "gold_stop_known": gold_stop_known,
                "evaluated_rate_confirmation": not skipped_non_rc,
                "skipped_non_rate_confirmation": skipped_non_rc,
                "fields_missing_due_to_text_extraction": fields,
                "recommended_route": route,
                "raw_value_printed": False,
            }
        )
    route_counts = dict(Counter(doc["recommended_route"] for doc in docs).most_common())
    return {
        "overall_docs": len(docs),
        "evaluated_rc_docs": sum(1 for doc in docs if doc.get("evaluated_rate_confirmation")),
        "skipped_non_rc_docs": sum(1 for doc in docs if doc.get("skipped_non_rate_confirmation")),
        "load_blocked_docs": sum(
            1
            for doc in docs
            if FIELD_LOAD_NUMBER in set(doc.get("fields_missing_due_to_text_extraction") or [])
        ),
        "rate_blocked_docs": sum(
            1
            for doc in docs
            if FIELD_TOTAL_CARRIER_RATE
            in set(doc.get("fields_missing_due_to_text_extraction") or [])
        ),
        "stop_blocked_docs": sum(
            1
            for doc in docs
            if "stops" in set(doc.get("fields_missing_due_to_text_extraction") or [])
        ),
        "recommended_next_route_counts": {
            "ocr": route_counts.get("ocr", 0),
            "vision_model": route_counts.get("vision_model", 0),
            "manual_review": route_counts.get("manual_review", 0),
            "document_classification": route_counts.get("document_classification", 0),
        },
        "ocr_or_vision_required_doc_count": len(docs),
        "pdf_type_counts": dict(Counter(doc["pdf_type"] for doc in docs).most_common()),
        "recommended_route_counts": route_counts,
        "documents": docs,
        "ocr_run": False,
        "ai_cloud_used": False,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _candidate_source_is_ocr(item):
    if not isinstance(item, dict):
        return False
    metadata = item.get("metadata_summary", {}) if isinstance(item.get("metadata_summary"), dict) else {}
    return _text(item.get("source")) == "ocr" or bool(metadata.get("ocr_candidate"))


def _gold_load_matches_candidate(item, gold):
    values = _gold_load_values(gold.get(FIELD_LOAD_NUMBER, {}) if isinstance(gold, dict) else {})
    if not values or not isinstance(item, dict):
        return False
    return _load_value_matches(item.get("value"), values)


def _gold_rate_matches_candidate(item, gold):
    value = _gold_scalar_value(gold.get(FIELD_TOTAL_CARRIER_RATE, {}) if isinstance(gold, dict) else {})
    if not value or not isinstance(item, dict):
        return False
    return _money_value_matches(item.get("value"), value)


def _build_ocr_gold_eval_summary(gold_labels, audit_index, comparison_rows):
    records = _unique_audit_records(audit_index)
    provider_status_counts = Counter()
    document_type_counts = Counter()
    skip_reason_counts = Counter()
    candidate_total = 0
    candidates_by_field = Counter()
    candidates_by_generator = Counter()
    for record in records:
        artifact = record.get("artifact_summary", {}) if isinstance(record, dict) else {}
        ocr_summary = artifact.get("ocr_provider_summary", {}) or {}
        if ocr_summary:
            provider_status_counts[
                f"requested:{_text(ocr_summary.get('provider_requested')) or 'none'}"
            ] += 1
            provider_status_counts[
                f"used:{_text(ocr_summary.get('provider_used')) or 'none'}"
            ] += 1
            provider_status_counts[
                f"status:{_text(ocr_summary.get('status')) or 'skipped'}"
            ] += 1
        classification = artifact.get("ocr_document_classification", {}) or {}
        if classification:
            document_type_counts[
                _text(classification.get("document_type")) or "unknown"
            ] += 1
            skip_reason = _text(classification.get("skip_reason"))
            if skip_reason:
                skip_reason_counts[skip_reason] += 1
        candidate_summary = (record.get("candidate_summary", {}) or {}).get(
            "ocr_candidate_summary",
            {},
        )
        candidate_total += _safe_int(candidate_summary.get("ocr_candidates_total"))
        candidates_by_field.update(candidate_summary.get("ocr_candidates_by_field", {}) or {})
        candidates_by_generator.update(
            candidate_summary.get("ocr_candidates_by_generator", {}) or {}
        )

    load_matches = 0
    rate_matches = 0
    stop_evidence_docs = set()
    for label in gold_labels or []:
        status = _text(label.get("label_status")) or LABEL_UNLABELED
        if status in {LABEL_UNLABELED, LABEL_SKIPPED}:
            continue
        record = _find_record(label, audit_index)
        if not isinstance(record, dict) or not record:
            continue
        gold = label.get("gold", {}) or {}
        if any(
            _candidate_source_is_ocr(item) and _gold_load_matches_candidate(item, gold)
            for item in _load_inventory(record)
        ):
            load_matches += 1
        if any(
            _candidate_source_is_ocr(item) and _gold_rate_matches_candidate(item, gold)
            for item in _rate_inventory(record)
        ):
            rate_matches += 1
        for stop_field in [FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS]:
            prediction = _shadow_prediction(record, stop_field)
            if isinstance(prediction, dict) and _prediction_source_name(prediction) == "ocr":
                stop_evidence_docs.add(_text(label.get("document_id")))

    shadow_rows = [
        row
        for row in comparison_rows
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") in CRITICAL_FIELDS
        and row.get("status") not in {STATUS_UNLABELED, STATUS_GOLD_UNCERTAIN}
    ]
    ocr_selected_rows = [
        row for row in shadow_rows if _text(row.get("source")) == "ocr" and row.get("predicted")
    ]
    ocr_correct_rows = [row for row in ocr_selected_rows if _status_correct(row.get("status"))]
    ocr_partial_rows = [row for row in ocr_selected_rows if _status_partial(row.get("status"))]
    ocr_wrong_rows = [
        row for row in ocr_selected_rows if row.get("status") == STATUS_WRONG_VALUE
    ]
    missing_by_field = Counter(
        row.get("field")
        for row in shadow_rows
        if row.get("status") in EXTRACTOR_MISSING_STATUSES
    )
    return {
        "provider_status_counts": dict(provider_status_counts.most_common()),
        "ocr_candidates_total": candidate_total,
        "ocr_candidates_by_field": dict(candidates_by_field.most_common()),
        "ocr_candidates_by_generator": dict(candidates_by_generator.most_common()),
        "ocr_gold_load_in_candidates": load_matches,
        "ocr_gold_rate_in_candidates": rate_matches,
        "ocr_gold_stop_evidence_docs": len(stop_evidence_docs),
        "ocr_selected_predictions": len(ocr_selected_rows),
        "ocr_resolved_docs": len(
            {
                _text(row.get("document_id"))
                for row in ocr_correct_rows + ocr_partial_rows
                if _text(row.get("document_id"))
            }
        ),
        "ocr_still_missing_docs": len(
            {
                _text(row.get("document_id"))
                for row in shadow_rows
                if row.get("status") in EXTRACTOR_MISSING_STATUSES
                and _text(row.get("document_id"))
            }
        ),
        "ocr_wrong_predictions": len(ocr_wrong_rows),
        "load_missing_current": missing_by_field.get(FIELD_LOAD_NUMBER, 0),
        "rate_missing_current": missing_by_field.get(FIELD_TOTAL_CARRIER_RATE, 0),
        "stop_missing_current": missing_by_field.get(FIELD_PICKUP_STOPS, 0)
        + missing_by_field.get(FIELD_DELIVERY_STOPS, 0),
        "document_type_counts": dict(document_type_counts.most_common()),
        "skip_reason_counts": dict(skip_reason_counts.most_common()),
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _record_ocr_status(record):
    artifact = record.get("artifact_summary", {}) if isinstance(record, dict) else {}
    summary = artifact.get("ocr_provider_summary", {}) or {}
    return _text(summary.get("status")) or "skipped"


def _record_has_ocr_text(record):
    artifact = record.get("artifact_summary", {}) if isinstance(record, dict) else {}
    summary = artifact.get("ocr_provider_summary", {}) or {}
    return _safe_int(summary.get("ocr_text_page_count")) > 0


def _ocr_load_inventory(record):
    return [
        item
        for item in _load_inventory(record)
        if isinstance(item, dict) and _candidate_source_is_ocr(item)
    ]


def _ocr_rate_inventory(record):
    return [
        item
        for item in _rate_inventory(record)
        if isinstance(item, dict) and _candidate_source_is_ocr(item)
    ]


def _ocr_load_gap_diagnosis(record, gold, gold_hashes):
    if not isinstance(record, dict) or not record:
        return "unknown"
    artifact = record.get("artifact_summary", {}) or {}
    classification = artifact.get("ocr_document_classification", {}) or {}
    if _text(classification.get("document_type")) == "non_rate_confirmation":
        return "skipped_non_rc"
    if not _record_has_ocr_text(record):
        return "ocr_text_missing"
    visibility = _load_visibility_status(record, gold_hashes)
    gold_in_ocr = visibility["visible_in_full_text"] or visibility["visible_in_lines"]
    if not gold_in_ocr:
        return "gold_not_in_ocr_text"
    selected = _shadow_prediction(record, FIELD_LOAD_NUMBER)
    if (
        isinstance(selected, dict)
        and _prediction_source_name(selected) == "ocr"
        and _load_value_matches(
            selected.get("value"),
            _gold_load_values(gold.get(FIELD_LOAD_NUMBER, {})),
        )
    ):
        return "ocr_load_candidate_selected"
    inventory = _ocr_load_inventory(record)
    if any(_gold_load_matches_candidate(item, gold) for item in inventory):
        return "resolver_excluded_ocr"
    if inventory:
        return "value_shape_rejected"
    candidate_summary = (record.get("candidate_summary", {}) or {}).get(
        "ocr_candidate_summary",
        {},
    )
    if _safe_int(candidate_summary.get("ocr_candidates_total")) > 0:
        return "label_hit_no_candidate"
    return "ocr_text_present_not_scanned"


def _build_ocr_load_candidate_gap_summary(gold_labels, audit_index):
    docs = []
    reasons = Counter()
    totals = Counter()
    for label in gold_labels or []:
        status = _text(label.get("label_status")) or LABEL_UNLABELED
        if status in {LABEL_UNLABELED, LABEL_SKIPPED}:
            continue
        record = _find_record(label, audit_index)
        if not isinstance(record, dict) or not record:
            continue
        ocr_status = _record_ocr_status(record)
        if ocr_status not in {"success", "partial"} and not _record_has_ocr_text(record):
            continue
        gold = label.get("gold", {}) or {}
        gold_values = _gold_load_values(gold.get(FIELD_LOAD_NUMBER, {}))
        gold_hashes = _load_value_hashes(gold_values)
        visibility = _load_visibility_status(record, gold_hashes)
        inventory = _ocr_load_inventory(record)
        matching = [item for item in inventory if _gold_load_matches_candidate(item, gold)]
        candidate_summary = (record.get("candidate_summary", {}) or {}).get(
            "ocr_candidate_summary",
            {},
        )
        by_field = candidate_summary.get("ocr_candidates_by_field", {}) or {}
        by_generator = candidate_summary.get("ocr_candidates_by_generator", {}) or {}
        diagnosis = _ocr_load_gap_diagnosis(record, gold, gold_hashes)
        reasons[diagnosis] += 1
        totals["ocr_docs"] += 1
        totals["evaluated_rc_ocr_docs"] += 1
        totals["gold_load_in_ocr_text"] += int(
            visibility["visible_in_full_text"] or visibility["visible_in_lines"]
        )
        totals["ocr_load_label_hits"] += sum(
            1
            for item in inventory
            if (_rate_inventory_metadata(item) or {}).get("header_load_identity_candidate")
        )
        totals["ocr_load_candidates_emitted"] += _safe_int(by_field.get(FIELD_LOAD_NUMBER))
        selected = _shadow_prediction(record, FIELD_LOAD_NUMBER)
        totals["ocr_load_candidates_selected"] += int(
            isinstance(selected, dict)
            and _prediction_source_name(selected) == "ocr"
            and bool(_text(selected.get("value")))
        )
        docs.append(
            {
                "file_name": _text(label.get("file_name")),
                "document_id": _text(label.get("document_id")),
                "ocr_status": ocr_status,
                "gold_load_status": "uncertain"
                if _gold_uncertain(gold.get(FIELD_LOAD_NUMBER, {}))
                else "labeled",
                "gold_load_in_ocr_text": bool(
                    visibility["visible_in_full_text"] or visibility["visible_in_lines"]
                ),
                "gold_load_in_ocr_lines": bool(visibility["visible_in_lines"]),
                "gold_load_in_ocr_candidates": bool(matching),
                "ocr_load_label_hits": sum(
                    1
                    for item in inventory
                    if (_rate_inventory_metadata(item) or {}).get(
                        "header_load_identity_candidate"
                    )
                ),
                "ocr_header_load_label_hits": _safe_int(
                    by_generator.get("header_load_identity_candidate_generator")
                ),
                "ocr_order_label_hits": sum(
                    1
                    for item in inventory
                    if (_rate_inventory_metadata(item) or {}).get("id_type_hint")
                    == "order"
                ),
                "ocr_po_label_hits": sum(
                    1
                    for item in inventory
                    if (_rate_inventory_metadata(item) or {}).get("id_type_hint") == "po"
                ),
                "ocr_candidate_rejection_reasons": {},
                "ocr_artifact_merge_status": {
                    "ocr_text_attached": _record_has_ocr_text(record),
                    "ocr_lines_attached": _record_has_ocr_text(record),
                    "candidate_generators_scanned_ocr": bool(
                        _safe_int(candidate_summary.get("ocr_candidates_total"))
                    ),
                },
                "diagnosis": diagnosis,
                "private_values_printed": False,
                "raw_text_printed": False,
            }
        )
    return {
        "ocr_docs": totals.get("ocr_docs", 0),
        "evaluated_rc_ocr_docs": totals.get("evaluated_rc_ocr_docs", 0),
        "gold_load_in_ocr_text": totals.get("gold_load_in_ocr_text", 0),
        "ocr_load_label_hits": totals.get("ocr_load_label_hits", 0),
        "ocr_load_candidates_emitted": totals.get("ocr_load_candidates_emitted", 0),
        "ocr_load_candidates_selected": totals.get("ocr_load_candidates_selected", 0),
        "gap_reason_counts": dict(reasons.most_common()),
        "documents": docs,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _ocr_rate_diagnosis(row, record, gold):
    if _status_correct(row.get("status")):
        return "ocr_correct_total"
    context = _text(row.get("money_context")) or "unknown"
    safety = _text(row.get("rate_safety")) or "unknown"
    if row.get("status") != STATUS_WRONG_VALUE:
        return "unknown"
    if context in {"accessorial", "deduction", "fee", "quickpay", "fuel_advance", "tracking_hold", "penalty"}:
        return "ocr_accessorial_or_penalty"
    if context == "payment_terms_amount":
        return "ocr_terms_amount"
    if safety in {"risky", "unknown"}:
        return "ocr_ambiguous_total" if safety == "risky" else "ocr_wrong_money_context"
    if not any(_gold_rate_matches_candidate(item, gold) for item in _ocr_rate_inventory(record)):
        return "ocr_gold_not_in_text"
    return "ocr_wrong_money_context"


def _build_ocr_rate_selection_summary(gold_labels, audit_index, comparison_rows):
    labels_by_doc = {
        _text(label.get("document_id")): label
        for label in gold_labels or []
        if _text(label.get("document_id"))
    }
    rows = [
        row
        for row in comparison_rows
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") == FIELD_TOTAL_CARRIER_RATE
        and row.get("predicted")
        and _text(row.get("source")) == "ocr"
    ]
    diagnoses = Counter()
    safety = Counter()
    contexts = Counter()
    cases = []
    for row in rows:
        label = labels_by_doc.get(_text(row.get("document_id")), {}) or {}
        record = _find_record(label, audit_index)
        gold = label.get("gold", {}) or {}
        diagnosis = _ocr_rate_diagnosis(row, record, gold)
        diagnoses[diagnosis] += 1
        contexts[_text(row.get("money_context")) or "unknown"] += 1
        safety[_text(row.get("rate_safety")) or "unknown"] += 1
        cases.append(
            {
                "file_name": _text(row.get("file_name")),
                "document_id": _text(row.get("document_id")),
                "selected_from_ocr": True,
                "ocr_rate_candidate_context": _text(row.get("money_context")) or "unknown",
                "ocr_rate_safety": _text(row.get("rate_safety")) or "unknown",
                "gold_rate_in_ocr_candidates": any(
                    _gold_rate_matches_candidate(item, gold)
                    for item in _ocr_rate_inventory(record)
                ),
                "diagnosis": diagnosis,
                "private_values_printed": False,
            }
        )
    wrong_rows = [row for row in rows if row.get("status") == STATUS_WRONG_VALUE]
    return {
        "ocr_selected_rate_count": len(rows),
        "ocr_wrong_rate_count": len(wrong_rows),
        "diagnosis_counts": dict(diagnoses.most_common()),
        "ocr_rate_safety_counts": dict(safety.most_common()),
        "ocr_rate_context_counts": dict(contexts.most_common()),
        "high_confidence_wrong_count": sum(
            1 for row in wrong_rows if _safe_float(row.get("confidence")) >= 0.90
        ),
        "cases": cases,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _build_ocr_accessorial_noise_summary(audit_index, comparison_rows):
    records = _unique_audit_records(audit_index)
    by_section = Counter()
    candidate_count = 0
    demoted = 0
    for record in records:
        candidate_summary = (record.get("candidate_summary", {}) or {}).get(
            "ocr_candidate_summary",
            {},
        )
        candidate_count += _safe_int(
            candidate_summary.get("ocr_accessorial_candidate_count")
        )
        demoted += _safe_int(candidate_summary.get("ocr_accessorial_deduped_or_demoted"))
        by_section.update(candidate_summary.get("ocr_accessorial_by_section", {}) or {})
    used_in_rate = sum(
        1
        for row in comparison_rows
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") == FIELD_TOTAL_CARRIER_RATE
        and _text(row.get("source")) == "ocr"
        and _text(row.get("money_context")) in {"accessorial", "deduction", "quickpay", "penalty", "fee"}
    )
    return {
        "ocr_accessorial_candidate_count": candidate_count,
        "ocr_accessorial_by_section": dict(by_section.most_common()),
        "ocr_accessorial_used_in_rate_selection": used_in_rate,
        "ocr_accessorial_deduped_or_demoted": demoted,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _stop_component_keys():
    return [
        "facility",
        "address",
        "city",
        "state",
        "zip",
        "date",
        "time",
        "appointment_window",
    ]


def _component_field_for_stop(field_name):
    if field_name == FIELD_PICKUP_STOPS:
        return {
            "location": FIELD_PICKUP_LOCATION,
            "date": FIELD_PICKUP_DATE,
            "time": FIELD_PICKUP_TIME,
        }
    return {
        "location": FIELD_DELIVERY_LOCATION,
        "date": FIELD_DELIVERY_DATE,
        "time": FIELD_DELIVERY_TIME,
    }


def _stop_source_bucket(row):
    source = _text(row.get("source")) or "unknown"
    parser = _text(row.get("parser_name")).lower()
    if source == "ocr":
        return "ocr"
    if source == "native_layout" and "table" in parser:
        return "pdfplumber_table"
    if source == "native_layout":
        return "native_layout"
    if source in {"native_text", "regex"}:
        return "native_text"
    if "legacy" in parser or source == "legacy_parser":
        return "legacy_fallback"
    return source or "unknown"


def _stop_wrong_reason(row):
    issues = set(row.get("issues") or [])
    if row.get("stop_role") and row.get("field") == FIELD_PICKUP_STOPS and row.get("stop_role") == "delivery":
        return "pickup_delivery_swapped"
    if row.get("stop_role") and row.get("field") == FIELD_DELIVERY_STOPS and row.get("stop_role") == "pickup":
        return "pickup_delivery_swapped"
    if "wrong_role" in issues:
        return "wrong_role"
    if "wrong_stop_count" in issues:
        return "wrong_stop_count"
    if "wrong_date" in issues:
        return "wrong_date"
    if "wrong_time" in issues:
        return "wrong_time"
    if any(issue in issues for issue in ["wrong_city", "wrong_state", "wrong_zip"]):
        return "wrong_city_state"
    if any(issue in issues for issue in ["wrong_facility", "wrong_address", "wrong_location"]):
        return "wrong_location"
    if row.get("source") == "ocr":
        return "ocr_line_misaligned"
    if _text(row.get("pairing_method")).startswith("table_"):
        return "table_row_misaligned"
    if row.get("status") == STATUS_PARTIAL_MATCH:
        return "partial_selected_as_complete"
    return "unknown"


def _stop_missing_reason(row):
    status = _text(row.get("status"))
    source_status = _text(row.get("source_status"))
    if status == STATUS_SHADOW_COMPONENT_NOT_SERIALIZED or source_status == STATUS_SHADOW_COMPONENT_NOT_SERIALIZED:
        return "serialized_gap"
    if source_status == STATUS_UNSUPPORTED_VALUE_TYPE:
        return "unsupported_structured_value"
    if row.get("stop_abstained"):
        return "candidate_abstained"
    if row.get("source") == "ocr":
        return "ocr_text_present_not_scanned"
    if status in EXTRACTOR_MISSING_STATUSES:
        return "no_stop_candidate"
    return "unknown"


def _empty_stop_forensics(field_name):
    return {
        "field": field_name,
        "evaluated_docs": 0,
        "exact_match": 0,
        "partial_match": 0,
        "wrong": 0,
        "missing": 0,
        "serialized_gap": 0,
        "role_swapped_count": 0,
        "order_ambiguous_count": 0,
        "component_status_counts": {key: {} for key in _stop_component_keys()},
        "source_counts": {
            "native_text": 0,
            "native_layout": 0,
            "pdfplumber_table": 0,
            "ocr": 0,
            "legacy_fallback": 0,
        },
        "wrong_reason_counts": {},
        "missing_reason_counts": {},
    }


def _build_stop_component_forensics_summary(comparison_rows, audit_index=None):
    summary = {
        FIELD_PICKUP_STOPS: _empty_stop_forensics(FIELD_PICKUP_STOPS),
        FIELD_DELIVERY_STOPS: _empty_stop_forensics(FIELD_DELIVERY_STOPS),
        "private_values_printed": False,
        "raw_text_printed": False,
    }
    rows_by_field = defaultdict(list)
    for row in comparison_rows or []:
        if row.get("system") == SYSTEM_SHADOW:
            rows_by_field[row.get("field")].append(row)

    for stop_field in [FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS]:
        payload = summary[stop_field]
        wrong_reasons = Counter()
        missing_reasons = Counter()
        source_counts = Counter()
        for row in rows_by_field.get(stop_field, []):
            status = row.get("status")
            if status in {STATUS_UNLABELED, STATUS_GOLD_UNCERTAIN}:
                continue
            payload["evaluated_docs"] += 1
            if status in {STATUS_EXACT, STATUS_NORMALIZED_MATCH}:
                payload["exact_match"] += 1
            elif status == STATUS_PARTIAL_MATCH:
                payload["partial_match"] += 1
                wrong_reasons[_stop_wrong_reason(row)] += 1
            elif status == STATUS_WRONG_VALUE:
                payload["wrong"] += 1
                reason = _stop_wrong_reason(row)
                wrong_reasons[reason] += 1
                if reason == "pickup_delivery_swapped":
                    payload["role_swapped_count"] += 1
            elif status in EXTRACTOR_MISSING_STATUSES or status in SOURCE_AVAILABILITY_STATUSES:
                payload["missing"] += 1
                reason = _stop_missing_reason(row)
                missing_reasons[reason] += 1
                if reason == "serialized_gap":
                    payload["serialized_gap"] += 1
            if row.get("predicted"):
                source_counts[_stop_source_bucket(row)] += 1
            if "wrong_stop_count" in set(row.get("issues") or []):
                payload["order_ambiguous_count"] += 1

        component_fields = _component_field_for_stop(stop_field)
        component_map = {
            "facility": "location",
            "address": "location",
            "city": "location",
            "state": "location",
            "zip": "location",
            "date": "date",
            "time": "time",
            "appointment_window": "time",
        }
        for component, derived_name in component_map.items():
            field = component_fields[derived_name]
            counts = Counter(
                row.get("status") or "unknown"
                for row in rows_by_field.get(field, [])
                if row.get("status") not in {STATUS_UNLABELED, STATUS_GOLD_UNCERTAIN}
            )
            payload["component_status_counts"][component] = dict(counts.most_common())

        for key in payload["source_counts"]:
            payload["source_counts"][key] = source_counts.get(key, 0)
        for key, value in source_counts.items():
            if key not in payload["source_counts"]:
                payload["source_counts"][key] = value
        payload["wrong_reason_counts"] = dict(wrong_reasons.most_common())
        payload["missing_reason_counts"] = dict(missing_reasons.most_common())
    return summary


def _stop_inventory(record):
    payload = _private_eval_values(record)
    return (
        payload.get("stop_component_candidate_inventory", [])
        if isinstance(payload, dict)
        else []
    )


def _is_ocr_stop_inventory_item(item):
    metadata = item.get("metadata_summary", {}) if isinstance(item.get("metadata_summary"), dict) else {}
    return _text(item.get("source")) == "ocr" or bool(metadata.get("ocr_candidate"))


def _ocr_stop_not_selected_reason(item):
    metadata = item.get("metadata_summary", {}) if isinstance(item.get("metadata_summary"), dict) else {}
    if metadata.get("stop_abstained"):
        return _text(metadata.get("stop_abstention_reason")) or "candidate_abstained"
    if _text(metadata.get("stop_selection_policy")) == "partial_review":
        return _text(metadata.get("stop_abstention_reason")) or "partial_review"
    if not metadata.get("structured_stop_candidate"):
        return "not_assembled_structured_stop"
    if metadata.get("ambiguous_stop_candidate"):
        return "ambiguous_stop_candidate"
    return "resolver_excluded_ocr"


def _build_ocr_stop_evidence_gap_summary(audit_index, comparison_rows):
    records = _unique_audit_records(audit_index)
    docs_with_ocr = [
        record
        for record in records
        if _record_ocr_status(record) in {"success", "partial"} or _record_has_ocr_text(record)
    ]
    ocr_items = []
    for record in docs_with_ocr:
        for item in _stop_inventory(record):
            if isinstance(item, dict) and _is_ocr_stop_inventory_item(item):
                ocr_items.append(item)
    selected_rows = [
        row
        for row in comparison_rows or []
        if row.get("system") == SYSTEM_SHADOW
        and row.get("field") in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}
        and row.get("predicted")
        and _text(row.get("source")) == "ocr"
    ]
    rejected = [
        item
        for item in ocr_items
        if _text(item.get("field")) not in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}
    ]
    rejection_reasons = Counter(_ocr_stop_not_selected_reason(item) for item in rejected)
    candidates_by_field = Counter(_text(item.get("field")) for item in ocr_items)
    structured = [
        item
        for item in ocr_items
        if _text(item.get("field")) in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}
    ]
    return {
        "ocr_docs": len(docs_with_ocr),
        "ocr_pickup_location_candidates": candidates_by_field.get(FIELD_PICKUP_LOCATION, 0),
        "ocr_pickup_date_candidates": candidates_by_field.get(FIELD_PICKUP_DATE, 0),
        "ocr_pickup_time_candidates": candidates_by_field.get(FIELD_PICKUP_TIME, 0),
        "ocr_delivery_location_candidates": candidates_by_field.get(FIELD_DELIVERY_LOCATION, 0),
        "ocr_delivery_date_candidates": candidates_by_field.get(FIELD_DELIVERY_DATE, 0),
        "ocr_delivery_time_candidates": candidates_by_field.get(FIELD_DELIVERY_TIME, 0),
        "ocr_structured_stop_candidates": len(structured),
        "ocr_stop_candidates_selected": len(selected_rows),
        "ocr_stop_candidates_rejected": max(0, len(ocr_items) - len(selected_rows)),
        "rejection_reason_counts": dict(rejection_reasons.most_common()),
        "candidate_field_counts": dict(candidates_by_field.most_common()),
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def evaluate_ratecon_against_gold(gold_labels, audit_records) -> dict:
    indexed = _audit_by_key(audit_records)
    metrics = defaultdict(lambda: defaultdict(_empty_metric))
    comparison_rows = []
    document_rows = []
    adjudication = []
    valid_labels = 0
    skipped = 0
    matched_labels = 0
    unmatched_labels = []
    for label in gold_labels or []:
        status = _text(label.get("label_status")) or LABEL_UNLABELED
        if status in {LABEL_UNLABELED, LABEL_SKIPPED}:
            skipped += 1
            continue
        valid_labels += 1
        record = _find_record(label, indexed)
        if record:
            matched_labels += 1
        else:
            unmatched_labels.append(
                {
                    "document_id": _text(label.get("document_id")),
                    "file_name": _text(label.get("file_name")),
                    "file_hash_prefix_present": bool(_text(label.get("file_hash"))),
                }
            )
        gold = label.get("gold", {}) or {}
        doc_result = {
            "document_id": _text(label.get("document_id")),
            "file_hash": _text(label.get("file_hash")),
            "field_results": {},
        }
        for field_name in EVALUATION_FIELDS:
            gold_field = gold_field_for_evaluation(gold, field_name)
            predictions = {
                system_name: _prediction_for_system(record, field_name, system_name)
                for system_name in EVALUATION_SYSTEMS
            }
            field_statuses = {}
            comparisons = {
                system_name: compare_field(field_name, prediction, gold_field)
                for system_name, prediction in predictions.items()
            }
            for system_name, prediction in predictions.items():
                comparison = comparisons[system_name]
                _update_metric(metrics[system_name][field_name], comparison)
                source_status = _prediction_source_status(prediction)
                metadata = _prediction_metadata(prediction)
                row = {
                    "document_id": _text(label.get("document_id")),
                    "file_name": _text(label.get("file_name")),
                    "file_hash": _text(label.get("file_hash")),
                    "label_status": status,
                    "system": system_name,
                    "field": field_name,
                    "status": comparison["status"],
                    "issues": list(comparison.get("issues", [])),
                    "confidence": comparison.get("confidence"),
                    "predicted": comparison.get("predicted", False),
                    "source_status": source_status,
                    "source": _prediction_source_name(prediction),
                    "parser_name": _text((prediction or {}).get("parser_name"))
                    if isinstance(prediction, dict)
                    else "",
                    "page": _text((prediction or {}).get("page"))
                    if isinstance(prediction, dict)
                    else "",
                    "value_shape": dict((prediction or {}).get("value_shape") or {})
                    if isinstance(prediction, dict)
                    else safe_value_shape(_prediction_value(prediction)),
                    "pairing_method": _text(metadata.get("pairing_method")),
                    "section_context": _text(metadata.get("section_context")),
                    "document_region": _text(metadata.get("document_region")),
                    "id_type_hint": _text(metadata.get("id_type_hint")),
                    "money_context": _text(metadata.get("money_context")),
                    "rate_safety": _text(metadata.get("rate_safety")),
                    "rate_safety_reason": _text(metadata.get("rate_safety_reason")),
                    "rate_abstained": bool(metadata.get("rate_abstained")),
                    "rate_abstention_reason": _text(
                        metadata.get("rate_abstention_reason")
                    ),
                    "rate_demoted_from_total_carrier_rate": bool(
                        metadata.get("rate_demoted_from_total_carrier_rate")
                    ),
                    "stop_role": _text(metadata.get("stop_role")),
                    "has_location": bool(metadata.get("has_location")),
                    "has_date": bool(metadata.get("has_date")),
                    "has_time": bool(metadata.get("has_time")),
                    "has_facility": bool(metadata.get("has_facility")),
                    "has_address": bool(metadata.get("has_address")),
                    "stop_structure_status": _text(metadata.get("stop_structure_status")),
                    "stop_selection_policy": _text(metadata.get("stop_selection_policy")),
                    "stop_abstained": bool(metadata.get("stop_abstained")),
                    "stop_abstention_reason": _text(metadata.get("stop_abstention_reason")),
                    "role_confidence": _safe_float(metadata.get("role_confidence")),
                    "component_completeness": _safe_float(
                        metadata.get("component_completeness")
                    ),
                    "table_context_role": _text(metadata.get("table_context_role")),
                    "table_row_role": _text(metadata.get("table_row_role")),
                    "table_neighbor_safety": _text(metadata.get("table_neighbor_safety")),
                    "table_neighbor_penalty_reason": _text(
                        metadata.get("table_neighbor_penalty_reason")
                    ),
                    "table_neighbor_abstained": bool(
                        metadata.get("table_neighbor_abstained")
                    ),
                    "table_neighbor_abstention_reason": _text(
                        metadata.get("table_neighbor_abstention_reason")
                    ),
                    "selection_policy": _text(metadata.get("selection_policy")),
                    "table_index": _text(metadata.get("table_index")),
                    "row_index": _text(metadata.get("row_index")),
                    "label_cell_index": _text(metadata.get("label_cell_index")),
                    "value_cell_index": _text(metadata.get("value_cell_index")),
                    "neighbor_cell_count": _safe_int(metadata.get("neighbor_cell_count")),
                    "id_like_cell_count_in_row": _safe_int(
                        metadata.get("id_like_cell_count_in_row")
                        or metadata.get("table_row_identifier_like_cell_count")
                    ),
                    "load_label_cell_count_in_row": _safe_int(
                        metadata.get("load_label_cell_count_in_row")
                    ),
                    "reference_label_cell_count_in_row": _safe_int(
                        metadata.get("reference_label_cell_count_in_row")
                    ),
                    "stop_label_cell_count_in_row": _safe_int(
                        metadata.get("stop_label_cell_count_in_row")
                    ),
                    "money_like_cell_count_in_row": _safe_int(
                        metadata.get("money_like_cell_count_in_row")
                    ),
                    "is_total_pay_candidate": bool(metadata.get("is_total_pay_candidate")),
                    "is_line_item_only": bool(metadata.get("is_line_item_only")),
                    "is_per_unit_rate": bool(metadata.get("is_per_unit_rate")),
                    "is_deduction_or_penalty": bool(
                        metadata.get("is_deduction_or_penalty")
                    ),
                    "is_payment_terms_amount": bool(
                        metadata.get("is_payment_terms_amount")
                    ),
                    "is_accessorial_only": bool(metadata.get("is_accessorial_only")),
                    "error_reason": _classify_error_reason(
                        field_name,
                        system_name,
                        prediction,
                        comparisons,
                    )
                    if comparison["status"] == STATUS_WRONG_VALUE
                    else "",
                }
                comparison_rows.append(row)
                field_statuses[system_name] = comparison["status"]
            winner = _winner(field_statuses[SYSTEM_LEGACY], field_statuses[SYSTEM_SHADOW])
            action = _recommended_action(
                winner,
                field_statuses[SYSTEM_LEGACY],
                field_statuses[SYSTEM_SHADOW],
            )
            category = _adjudication_category(
                field_statuses[SYSTEM_LEGACY],
                field_statuses[SYSTEM_SHADOW],
            )
            doc_result["field_results"][field_name] = {
                "legacy_vs_gold": field_statuses[SYSTEM_LEGACY],
                "shadow_vs_gold": field_statuses[SYSTEM_SHADOW],
                "winner": winner,
                "adjudication_category": category,
                "recommended_action": action,
            }
            adjudication.append(
                {
                    "document_id": _text(label.get("document_id")),
                    "file_hash": _text(label.get("file_hash")),
                    "field": field_name,
                    "legacy_vs_gold": field_statuses[SYSTEM_LEGACY],
                    "shadow_vs_gold": field_statuses[SYSTEM_SHADOW],
                    "winner": winner,
                    "adjudication_category": category,
                    "recommended_action": action,
                }
            )
        action_counts = Counter(
            result["recommended_action"] for result in doc_result["field_results"].values()
        )
        doc_result["recommended_action"] = action_counts.most_common(1)[0][0] if action_counts else ACTION_MORE_GOLD
        document_rows.append(doc_result)
    finalized = {
        system_name: {
            field_name: _finalize_metric(metric)
            for field_name, metric in field_metrics.items()
        }
        for system_name, field_metrics in metrics.items()
    }
    adjudication_counts = Counter(row["winner"] for row in adjudication)
    category_counts = Counter(row["adjudication_category"] for row in adjudication)
    action_counts = Counter(row["recommended_action"] for row in adjudication)
    error_case_breakdown = {
        field_name: dict(
            Counter(
                row.get("error_reason") or "unknown"
                for row in comparison_rows
                if row.get("system") == SYSTEM_SHADOW
                and row.get("field") == field_name
                and row.get("status") == STATUS_WRONG_VALUE
            ).most_common()
        )
        for field_name in [FIELD_LOAD_NUMBER, FIELD_TOTAL_CARRIER_RATE]
    }
    residual_wrong_rate_forensics = _build_residual_wrong_rate_forensics(
        comparison_rows,
        gold_labels,
        indexed,
    )
    return {
        "schema_version": "ratecon_gold_evaluation_v1",
        "labels_loaded": len(gold_labels or []),
        "labels_evaluated": valid_labels,
        "labels_skipped": skipped,
        "labels_matched_to_audit": matched_labels,
        "labels_unmatched_to_audit": len(unmatched_labels),
        "unmatched_labels": unmatched_labels,
        "field_metrics": finalized,
        "confidence_calibration": _build_confidence_calibration(comparison_rows),
        "adjudication": {
            "winner_counts": dict(adjudication_counts.most_common()),
            "category_counts": dict(category_counts.most_common()),
            "recommended_action_counts": dict(action_counts.most_common()),
            "rows": adjudication,
        },
        "error_case_breakdown": error_case_breakdown,
        "load_number_error_analysis": _build_load_number_error_analysis(comparison_rows),
        "load_table_neighbor_error_summary": _build_load_table_neighbor_error_summary(
            comparison_rows,
        ),
        "load_table_neighbor_value_cell_forensics": (
            _build_load_table_neighbor_value_cell_forensics(comparison_rows)
        ),
        "remaining_table_neighbor_wrong_summary": _build_remaining_table_neighbor_wrong_summary(
            comparison_rows,
        ),
        "table_neighbor_abstention_summary": _build_table_neighbor_abstention_summary(
            comparison_rows,
            _unique_audit_records(indexed),
        ),
        "rate_error_analysis": _build_rate_error_analysis(comparison_rows),
        "rate_wrong_case_summary": _build_rate_wrong_case_summary(comparison_rows),
        "residual_wrong_rate_forensics": residual_wrong_rate_forensics,
        "gold_rate_consistency_audit": _build_gold_rate_consistency_audit(
            residual_wrong_rate_forensics,
        ),
        "missing_rate_forensics": _build_missing_rate_forensics(
            comparison_rows,
            gold_labels,
            indexed,
        ),
        "rate_abstention_summary": _build_rate_abstention_summary(
            comparison_rows,
            _unique_audit_records(indexed),
        ),
        "load_candidate_recall_summary": _build_load_candidate_recall_summary(
            gold_labels,
            indexed,
        ),
        "ocr_vision_backlog_summary": _build_ocr_vision_backlog_summary(
            gold_labels,
            indexed,
        ),
        "ocr_gold_eval_summary": _build_ocr_gold_eval_summary(
            gold_labels,
            indexed,
            comparison_rows,
        ),
        "ocr_load_candidate_gap_summary": _build_ocr_load_candidate_gap_summary(
            gold_labels,
            indexed,
        ),
        "ocr_rate_selection_summary": _build_ocr_rate_selection_summary(
            gold_labels,
            indexed,
            comparison_rows,
        ),
        "ocr_accessorial_noise_summary": _build_ocr_accessorial_noise_summary(
            indexed,
            comparison_rows,
        ),
        "stop_component_forensics_summary": _build_stop_component_forensics_summary(
            comparison_rows,
            indexed,
        ),
        "ocr_stop_evidence_gap_summary": _build_ocr_stop_evidence_gap_summary(
            indexed,
            comparison_rows,
        ),
        "document_metrics": document_rows,
        "comparison_rows": comparison_rows,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


@dataclass(frozen=True)
class PacketBuildOptions:
    include_private_values: bool = False
    include_private_evidence: bool = False


def _safe_prediction_block(resolution, include_private_values=False, include_private_evidence=False):
    resolution = resolution if isinstance(resolution, dict) else {}
    value = resolution.get("value", "")
    return {
        "value": value if include_private_values else "",
        "value_shape": safe_value_shape(value),
        "confidence": _safe_float(resolution.get("confidence")),
        "source": _text(resolution.get("source")),
        "candidate_count": _safe_int(resolution.get("candidate_count")),
        "needs_review": _safe_bool(resolution.get("needs_review")),
        "review_reasons": list(resolution.get("review_reasons", []) or []),
        "evidence_text": _text(resolution.get("evidence_text")) if include_private_evidence else "",
        "structure_status": _text(resolution.get("structure_status")),
        "selected_status": _text(resolution.get("selected_status")),
        "structured_stop_summary": dict(resolution.get("structured_stop_summary") or {}),
    }


def build_gold_label_packet(record, summary=None, options=None) -> dict:
    options = options or PacketBuildOptions()
    record = record or {}
    shadow = record.get("shadow", {}) if isinstance(record.get("shadow"), dict) else {}
    resolved_fields = shadow.get("resolved_fields", {}) if isinstance(shadow, dict) else {}
    legacy = record.get("legacy", {}) if isinstance(record.get("legacy"), dict) else {}
    legacy_values = {}
    for field_name in CRITICAL_FIELDS:
        value = legacy.get(field_name, "")
        legacy_values[field_name] = {
            "value": value if options.include_private_values else "",
            "value_shape": safe_value_shape(value),
            "present": bool(_text(value)) or (
                field_name == FIELD_PICKUP_STOPS and _safe_int(legacy.get("pickup_count")) > 0
            )
            or (
                field_name == FIELD_DELIVERY_STOPS and _safe_int(legacy.get("delivery_count")) > 0
            ),
        }
    shadow_values = {
        field_name: _safe_prediction_block(
            resolved_fields.get(field_name, {}),
            include_private_values=options.include_private_values,
            include_private_evidence=options.include_private_evidence,
        )
        for field_name in CRITICAL_FIELDS
    }
    return {
        "schema_version": "ratecon_gold_label_packet_v1",
        "document_id": _text(record.get("document_id")),
        "file_hash": _text(record.get("file_hash")),
        "file_name": _text(record.get("file_name")) if options.include_private_values else "",
        "triage": deepcopy(record.get("triage", {}) or {}),
        "legacy_values": legacy_values,
        "shadow_values": shadow_values,
        "resolver_trace_summary": deepcopy((record.get("candidate_summary", {}) or {}).get("resolver_selection_summary", {})),
        "review_gate_trace": deepcopy(shadow.get("review_gate_trace", {}) or {}),
        "candidate_quality_summary": deepcopy((record.get("candidate_summary", {}) or {}).get("candidate_quality_summary", {})),
        "failure_attribution": deepcopy(record.get("failure_attribution", {}) or {}),
        "gold_label_template": build_gold_label_template(
            document_id=record.get("document_id", ""),
            file_hash=record.get("file_hash", ""),
            file_name=record.get("file_name", "") if options.include_private_values else "",
        ),
        "private_values_included": bool(options.include_private_values),
        "private_evidence_included": bool(options.include_private_evidence),
        "raw_text_included": False,
    }
