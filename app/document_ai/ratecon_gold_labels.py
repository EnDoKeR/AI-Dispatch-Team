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

STATUS_EXACT = "exact"
STATUS_NORMALIZED_MATCH = "normalized_match"
STATUS_PARTIAL_MATCH = "partial_match"
STATUS_MISSING = "missing"
STATUS_WRONG_VALUE = "wrong_value"
STATUS_CONFLICT = "conflict"
STATUS_UNLABELED = "unlabeled"
STATUS_GOLD_UNCERTAIN = "gold_uncertain"
STATUS_PREDICTION_UNAVAILABLE = "prediction_unavailable"

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
    return {
        "type": "string",
        "length": len(text),
        "has_digits": bool(digits),
        "has_letters": bool(letters),
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


def _confidence(prediction):
    if isinstance(prediction, dict):
        value = _safe_float(prediction.get("confidence"))
        return value
    return None


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


def compare_field(field_name, prediction, gold_field) -> dict:
    if _gold_uncertain(gold_field):
        return {
            "field": field_name,
            "status": STATUS_GOLD_UNCERTAIN,
            "issues": ["gold_uncertain"],
            "confidence": _confidence(prediction),
        }
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


def _legacy_prediction(record, field_name):
    legacy = record.get("legacy", {}) if isinstance(record, dict) else {}
    if field_name in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}:
        count_field = "pickup_count" if field_name == FIELD_PICKUP_STOPS else "delivery_count"
        count = _safe_int(legacy.get(count_field))
        return {"value": [{"stop_index": index + 1} for index in range(count)] if count else ""}
    return {"value": legacy.get(field_name, ""), "confidence": None}


def _shadow_prediction(record, field_name):
    shadow = record.get("shadow", {}) if isinstance(record, dict) else {}
    fields = shadow.get("resolved_fields", {}) if isinstance(shadow, dict) else {}
    value = fields.get(field_name, {}) if isinstance(fields, dict) else {}
    return value if isinstance(value, dict) else {"value": value}


def _candidate_best_prediction(record, field_name):
    shadow = record.get("shadow", {}) if isinstance(record, dict) else {}
    traces = shadow.get("resolver_decision_traces", {}) if isinstance(shadow, dict) else {}
    trace = traces.get(field_name, {}) if isinstance(traces, dict) else {}
    selected = trace.get("selected_candidate", {}) if isinstance(trace, dict) else {}
    return selected if isinstance(selected, dict) else {"value": ""}


def _component_prediction(record, field_name, system_name):
    stop_field = FIELD_PICKUP_STOPS if field_name.startswith("pickup_") else FIELD_DELIVERY_STOPS
    if system_name == SYSTEM_LEGACY:
        base = _legacy_prediction(record, stop_field)
    elif system_name == SYSTEM_SHADOW:
        base = _shadow_prediction(record, stop_field)
    else:
        base = _candidate_best_prediction(record, stop_field)
    if field_name.endswith("_location"):
        value = _prediction_stop_component(base, "location")
    elif field_name.endswith("_date"):
        value = _prediction_stop_component(base, "date")
    elif field_name.endswith("_time"):
        value = _prediction_stop_component(base, "time")
    else:
        value = ""
    return {"value": value, "confidence": _confidence(base)}


def _prediction_for_system(record, field_name, system_name):
    if field_name in STOP_COMPONENT_FIELDS:
        return _component_prediction(record, field_name, system_name)
    if system_name == SYSTEM_LEGACY:
        return _legacy_prediction(record, field_name)
    if system_name == SYSTEM_SHADOW:
        return _shadow_prediction(record, field_name)
    return _candidate_best_prediction(record, field_name)


def _status_correct(status) -> bool:
    return status in {STATUS_EXACT, STATUS_NORMALIZED_MATCH}


def _status_partial(status) -> bool:
    return status == STATUS_PARTIAL_MATCH


def _empty_metric():
    return {
        "labeled_count": 0,
        "uncertain_count": 0,
        "predicted_count": 0,
        "exact_match_count": 0,
        "normalized_match_count": 0,
        "partial_match_count": 0,
        "missing_count": 0,
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
    elif status == STATUS_MISSING:
        metric["missing_count"] += 1
    elif status == STATUS_CONFLICT:
        metric["conflict_count"] += 1
    elif status == STATUS_WRONG_VALUE:
        metric["wrong_value_count"] += 1
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
        rows = [
            row
            for row in comparison_rows
            if row["field"] == field_name
            and row["system"] == SYSTEM_SHADOW
            and row["status"] not in {STATUS_UNLABELED, STATUS_GOLD_UNCERTAIN}
        ]
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
            recall = round(correct / len(rows), 4) if rows else 0.0
            review_rate = round(1.0 - (len(selected) / len(rows)), 4) if rows else 1.0
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
            "labeled_count": len(rows),
            "bands": {key: dict(value) for key, value in sorted(band_counts.items())},
            "recommended_threshold_candidates": threshold_rows,
            "do_not_apply_automatically": True,
            "small_sample_warning": len(rows) < 30,
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
    if legacy_status == STATUS_UNLABELED or shadow_status == STATUS_UNLABELED:
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
    if legacy_correct and shadow_status == STATUS_MISSING:
        return ADJ_LEGACY_CORRECT_SHADOW_MISSING
    if shadow_correct and legacy_status == STATUS_MISSING:
        return ADJ_LEGACY_MISSING_SHADOW_CORRECT
    if legacy_correct:
        return ADJ_LEGACY_CORRECT_SHADOW_WRONG
    if shadow_correct:
        return ADJ_SHADOW_CORRECT_LEGACY_WRONG
    if legacy_status == STATUS_MISSING and shadow_status == STATUS_MISSING:
        return ADJ_BOTH_MISSING
    return ADJ_BOTH_WRONG


def _recommended_action(winner, legacy_status, shadow_status):
    if winner == WINNER_SHADOW:
        return ACTION_SHADOW_EXPERIMENT
    if winner == WINNER_LEGACY:
        return ACTION_KEEP_LEGACY
    if winner == WINNER_BOTH:
        return ACTION_KEEP_LEGACY
    if legacy_status == STATUS_MISSING and shadow_status == STATUS_MISSING:
        return ACTION_IMPROVE_CANDIDATES
    if shadow_status == STATUS_PARTIAL_MATCH:
        return ACTION_RESOLVER_TUNING
    if winner == WINNER_UNKNOWN:
        return ACTION_MORE_GOLD
    return ACTION_REVIEW_REQUIRED


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
                for system_name in [
                    SYSTEM_LEGACY,
                    SYSTEM_SHADOW,
                    SYSTEM_SHADOW_CANDIDATE_BEST,
                ]
            }
            field_statuses = {}
            for system_name, prediction in predictions.items():
                comparison = compare_field(field_name, prediction, gold_field)
                _update_metric(metrics[system_name][field_name], comparison)
                row = {
                    "document_id": _text(label.get("document_id")),
                    "file_hash": _text(label.get("file_hash")),
                    "system": system_name,
                    "field": field_name,
                    "status": comparison["status"],
                    "issues": list(comparison.get("issues", [])),
                    "confidence": comparison.get("confidence"),
                    "predicted": comparison.get("predicted", False),
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
