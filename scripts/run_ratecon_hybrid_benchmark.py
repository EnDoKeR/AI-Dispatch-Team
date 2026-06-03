"""Local-only benchmark runner for submitted RateCon hybrid result JSON files.

The runner validates manually supplied or future model-supplied JSON results and
compares review-only drafts to local gold labels. It does not call AI models,
cloud APIs, OCR, local model runtimes, or PDF processing.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.ratecon_gold_labels import (  # noqa: E402
    FIELD_DELIVERY_STOPS,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_STOPS,
    FIELD_TOTAL_CARRIER_RATE,
    STATUS_EXACT,
    STATUS_GOLD_UNCERTAIN,
    STATUS_MISSING,
    STATUS_NORMALIZED_MATCH,
    STATUS_PARTIAL_MATCH,
    STATUS_UNLABELED,
    STATUS_WRONG_VALUE,
    compare_field,
    load_gold_labels,
    normalize_date,
    normalize_location_component,
    normalize_money,
)
from app.document_ai.ratecon_hybrid_contract import (  # noqa: E402
    _field_has_value,
    is_under_local_outputs,
    validate_hybrid_result,
)


DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_hybrid_benchmark")
STOP_TIERS = (
    "exact_complete",
    "dispatch_usable",
    "useful_partial",
    "matches_uncertain_gold_review_required",
    "partial_match_uncertain_gold_review_required",
    "gold_uncertain_review_required",
    "not_applicable",
    "unsafe_wrong",
    "missing_review_required",
)
NON_RC_DOCUMENT_TYPES = {
    "bol_pod",
    "non_rate_confirmation",
    "bill_of_lading_or_delivery_receipt",
}
NOT_APPLICABLE_NON_RC_STATUS = "not_applicable_non_rc"
UNCERTAIN_GOLD_REVIEW_TIERS = {
    "matches_uncertain_gold_review_required",
    "partial_match_uncertain_gold_review_required",
    "gold_uncertain_review_required",
}
UNCERTAIN_GOLD_STATUSES = {
    "matches_uncertain_gold_review_required",
    "partial_match_uncertain_gold_review_required",
    "gold_uncertain_not_scored_as_wrong",
    "gold_uncertain_needs_human_review",
}
STABLE_UNCERTAIN_STOP_COMPONENTS = ("facility", "address", "city", "state", "zip", "date")
BASELINE = {
    "load_number": {"correct": 25, "wrong": 1, "missing": 5},
    "total_carrier_rate": {"correct": 26, "wrong": 3, "missing": 2},
    "pickup_stops": {"exact": 0, "partial": 17, "wrong": 5, "missing": 3},
    "delivery_stops": {"exact": 0, "partial": 12, "wrong": 5, "missing": 4},
}


class HybridBenchmarkError(ValueError):
    """Raised when the local-only benchmark would be unsafe or invalid."""


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _file_name_or_label(result: dict[str, Any], fallback: str = "") -> str:
    return (
        _text(result.get("file_name"))
        or _text(result.get("file_name_or_label"))
        or _text(result.get("document_label"))
        or fallback
    )


def _has_evidence_ids(item: dict[str, Any]) -> bool:
    evidence_ids = item.get("evidence_ids") or []
    return isinstance(evidence_ids, list) and any(_text(eid) for eid in evidence_ids)


def _has_stop_evidence(stop: dict[str, Any]) -> bool:
    return isinstance(stop.get("evidence_page"), int) or _has_evidence_ids(stop)


def _has_field_evidence(field: dict[str, Any]) -> bool:
    return _has_evidence_ids(field)


def _read_audit_records(path: Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    resolved = _repo_relative(path)
    if not resolved.exists():
        return []
    records: list[dict[str, Any]] = []
    with resolved.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _audit_indexes(records: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    indexes = {"document_id": {}, "file_name": {}, "file_hash": {}, "file_hash_prefix": {}}
    for record in records:
        for key in indexes:
            value = _text(record.get(key))
            if value and value not in indexes[key]:
                indexes[key][value] = record
    return indexes


def _match_audit(result: dict[str, Any], indexes: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any] | None:
    for key in ("document_id", "file_name", "file_hash"):
        value = _text(result.get(key))
        if value and value in indexes[key]:
            return indexes[key][value]
    file_hash_prefix = _text(result.get("file_hash_prefix"))
    if file_hash_prefix:
        for key, record in indexes["file_hash"].items():
            if key.startswith(file_hash_prefix):
                return record
        for key, record in indexes["file_hash_prefix"].items():
            if key.startswith(file_hash_prefix) or file_hash_prefix.startswith(key):
                return record
    return None


def _is_unfilled_manual_template(result: dict[str, Any]) -> bool:
    if result.get("model_provider") != "manual" or result.get("model_name") not in {
        "manual_pilot_v1",
        "manual_next_batch_v1",
    }:
        return False
    fields = result.get("fields") or {}
    if _field_has_value(fields.get(FIELD_LOAD_NUMBER)) or _field_has_value(fields.get(FIELD_TOTAL_CARRIER_RATE)):
        return False
    for field_name in (FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS):
        stops = fields.get(field_name) or []
        if not isinstance(stops, list):
            continue
        for stop in stops:
            if not isinstance(stop, dict):
                continue
            if any(_text(stop.get(key)) for key in ("facility", "address", "city", "state", "zip", "date", "time", "appointment_window")):
                return False
    return True


def _confidence(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("confidence")
    try:
        if value in [None, ""]:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence_bucket(value: float | None) -> str:
    if value is None:
        return "missing"
    if value >= 0.9:
        return "gte_0_90"
    if value >= 0.8:
        return "0_80_to_0_89"
    if value >= 0.7:
        return "0_70_to_0_79"
    if value >= 0.6:
        return "0_60_to_0_69"
    return "lt_0_60"


def _is_correct_status(status: str) -> bool:
    return status in {STATUS_EXACT, STATUS_NORMALIZED_MATCH}


def _is_missing_status(status: str) -> bool:
    return status in {STATUS_MISSING, STATUS_UNLABELED}


def _gold_document_type(gold: dict[str, Any] | None) -> str:
    if not gold:
        return ""
    return _text((gold.get("gold") or {}).get("document_type"))


def _audit_document_type(record: dict[str, Any] | None) -> str:
    if not record:
        return ""
    direct = _text(record.get("document_type"))
    if direct:
        return direct
    classification = record.get("document_classification")
    if isinstance(classification, dict):
        return _text(classification.get("document_type") or classification.get("classification"))
    validator_results = record.get("validator_results")
    if isinstance(validator_results, dict):
        gate = validator_results.get("document_classification_gate")
        if isinstance(gate, dict):
            return _text(gate.get("document_type") or gate.get("status"))
    return ""


def _is_non_rc_document_type(document_type: str) -> bool:
    return _text(document_type) in NON_RC_DOCUMENT_TYPES


def _is_confirmed_non_rc(
    result: dict[str, Any],
    gold: dict[str, Any] | None,
    audit_record: dict[str, Any] | None,
) -> bool:
    if not _is_non_rc_document_type(_text(result.get("document_type"))):
        return False
    gold_type = _gold_document_type(gold)
    audit_type = _audit_document_type(audit_record)
    return _is_non_rc_document_type(gold_type) or _is_non_rc_document_type(audit_type)


def _is_document_type_mismatch(
    result: dict[str, Any],
    gold: dict[str, Any] | None,
    audit_record: dict[str, Any] | None,
) -> bool:
    if not _is_non_rc_document_type(_text(result.get("document_type"))):
        return False
    if _is_confirmed_non_rc(result, gold, audit_record):
        return False
    gold_type = _gold_document_type(gold) or "rate_confirmation"
    return gold_type == "rate_confirmation"


def _stop_has_ratecon_values(stop: Any) -> bool:
    if not isinstance(stop, dict):
        return False
    return any(
        _text(stop.get(key))
        for key in ("facility", "address", "city", "state", "zip", "date", "time", "appointment_window", "raw_text_local_only")
    )


def _non_rc_ratecon_fields_with_values(result: dict[str, Any]) -> list[str]:
    fields = result.get("fields") or {}
    flagged: list[str] = []
    for field_name in (FIELD_LOAD_NUMBER, FIELD_TOTAL_CARRIER_RATE):
        if _field_has_value(fields.get(field_name)):
            flagged.append(field_name)
    for field_name in (FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS):
        stops = fields.get(field_name) or []
        if isinstance(stops, list) and any(_stop_has_ratecon_values(stop) for stop in stops):
            flagged.append(field_name)
    return flagged


def _non_rc_scalar_row(document_id: str, field_name: str) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "field": field_name,
        "status": NOT_APPLICABLE_NON_RC_STATUS,
        "issues": ["non_rc_filtered"],
        "confidence": None,
        "confidence_bucket": "not_applicable",
        "has_evidence": False,
        "tier": "",
        "requires_human_review": True,
        "auto_accept": False,
        "gold_uncertain_status": "",
    }


def _non_rc_stop_row(document_id: str, field_name: str) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "field": field_name,
        "stop_index": "",
        "status": NOT_APPLICABLE_NON_RC_STATUS,
        "tier": "not_applicable",
        "issues": ["non_rc_filtered"],
        "confidence": None,
        "confidence_bucket": "not_applicable",
        "has_evidence": False,
        "requires_human_review": True,
        "auto_accept": False,
        "gold_uncertain_status": "",
    }


def _normalize_stop_component(stop: dict[str, Any], key: str) -> str:
    value = stop.get(key) if isinstance(stop, dict) else None
    if key == "date":
        return normalize_date(value)
    if key == "zip":
        return "".join(ch for ch in _text(value) if ch.isdigit())
    return normalize_location_component(value)


def _uncertain_gold_stop_result(prediction: dict[str, Any], gold_stops: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify an uncertain-gold stop without treating uncertainty as unsafe by default."""

    pred_values = {
        key: _normalize_stop_component(prediction, key)
        for key in STABLE_UNCERTAIN_STOP_COMPONENTS
    }
    if not any(pred_values.values()):
        return {
            "status": "gold_uncertain_needs_human_review",
            "tier": "gold_uncertain_review_required",
            "issues": ["gold_uncertain", "no_stable_stop_components"],
        }

    best_partial: dict[str, Any] | None = None
    conflict_issues: Counter[str] = Counter()
    for gold_stop in gold_stops or []:
        if not isinstance(gold_stop, dict):
            continue
        gold_values = {
            key: _normalize_stop_component(gold_stop, key)
            for key in STABLE_UNCERTAIN_STOP_COMPONENTS
        }
        labeled_keys = [key for key, value in gold_values.items() if value]
        if not labeled_keys:
            continue
        matches = [key for key in labeled_keys if pred_values.get(key) == gold_values.get(key)]
        missing = [key for key in labeled_keys if not pred_values.get(key)]
        conflicts = [
            key
            for key in labeled_keys
            if pred_values.get(key) and pred_values.get(key) != gold_values.get(key)
        ]
        if conflicts:
            conflict_issues.update(f"wrong_stable_{key}" for key in conflicts)
            continue
        if matches and not missing:
            return {
                "status": "matches_uncertain_gold_review_required",
                "tier": "matches_uncertain_gold_review_required",
                "issues": ["gold_uncertain", "stable_components_match"],
            }
        if matches:
            candidate = {
                "status": "partial_match_uncertain_gold_review_required",
                "tier": "partial_match_uncertain_gold_review_required",
                "issues": ["gold_uncertain", "stable_components_partial_match"]
                + [f"missing_stable_{key}" for key in missing],
                "match_count": len(matches),
            }
            if not best_partial or candidate["match_count"] > best_partial["match_count"]:
                best_partial = candidate

    if best_partial:
        best_partial.pop("match_count", None)
        return best_partial
    if conflict_issues:
        return {
            "status": "wrong_against_uncertain_gold",
            "tier": "unsafe_wrong",
            "issues": ["gold_uncertain"] + sorted(conflict_issues),
        }
    return {
        "status": "gold_uncertain_needs_human_review",
        "tier": "gold_uncertain_review_required",
        "issues": ["gold_uncertain", "stable_components_not_comparable"],
    }


def _stop_tier(compare_result: dict[str, Any], prediction: dict[str, Any], gold_stops: list[dict[str, Any]]) -> str:
    status = compare_result.get("status")
    if _is_correct_status(status):
        return "exact_complete"
    if status == STATUS_GOLD_UNCERTAIN:
        return _uncertain_gold_stop_result(prediction, gold_stops)["tier"]
    if status in UNCERTAIN_GOLD_STATUSES:
        return compare_result.get("tier") or "gold_uncertain_review_required"
    if status == STATUS_PARTIAL_MATCH:
        issues = set(compare_result.get("issues") or [])
        has_location = any(_text(prediction.get(key)) for key in ("city", "state", "address", "facility"))
        has_date = bool(_text(prediction.get("date")))
        has_time = bool(_text(prediction.get("time") or prediction.get("appointment_window")))
        gold_requires_time = any(
            isinstance(stop, dict) and _text(stop.get("time") or stop.get("appointment_window"))
            for stop in gold_stops or []
        )
        wrong_issues = {issue for issue in issues if issue.startswith("wrong_")}
        if wrong_issues:
            return "unsafe_wrong"
        if has_location and has_date and (has_time or not gold_requires_time):
            return "dispatch_usable"
        return "useful_partial"
    if _is_missing_status(status):
        return "missing_review_required"
    if status == STATUS_WRONG_VALUE:
        return "unsafe_wrong"
    return "unsafe_wrong"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HybridBenchmarkError(f"{path.name} must contain a JSON object")
    return payload


def _load_hybrid_results(results_dir: Path, *, allow_missing: bool) -> list[tuple[Path, dict[str, Any]]]:
    resolved = _repo_relative(results_dir)
    if not resolved.exists():
        if allow_missing:
            return []
        raise HybridBenchmarkError(f"Hybrid results directory does not exist: {results_dir}")
    files = sorted(resolved.glob("*.json"))
    if not files and not allow_missing:
        raise HybridBenchmarkError(f"No hybrid JSON files found in {results_dir}")
    return [(path, _load_json(path)) for path in files]


def _gold_indexes(labels: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    indexes = {"document_id": {}, "file_name": {}, "file_hash": {}}
    for label in labels:
        for key in indexes:
            value = _text(label.get(key))
            if value:
                indexes[key][value] = label
    return indexes


def _match_gold(result: dict[str, Any], indexes: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any] | None:
    for key in ("document_id", "file_name", "file_hash"):
        value = _text(result.get(key))
        if value and value in indexes[key]:
            return indexes[key][value]
    file_hash_prefix = _text(result.get("file_hash_prefix"))
    if file_hash_prefix:
        for full_hash, label in indexes["file_hash"].items():
            if full_hash.startswith(file_hash_prefix):
                return label
    return None


def _scalar_value_from_field(field: Any, field_name: str) -> Any:
    if not isinstance(field, dict):
        return field
    value = field.get("value")
    if field_name == FIELD_TOTAL_CARRIER_RATE:
        if isinstance(value, dict):
            for key in ("amount", "value", "numeric_value", "total"):
                if value.get(key) not in [None, ""]:
                    return value.get(key)
        if value in [None, ""]:
            for key in ("amount", "numeric_value", "total"):
                if field.get(key) not in [None, ""]:
                    return field.get(key)
    return value


def _scalar_source_path(field: Any, field_name: str) -> str:
    if not isinstance(field, dict):
        return f"fields.{field_name}"
    value = field.get("value")
    if field_name == FIELD_TOTAL_CARRIER_RATE:
        if isinstance(value, dict):
            for key in ("amount", "value", "numeric_value", "total"):
                if value.get(key) not in [None, ""]:
                    return f"fields.{field_name}.value.{key}"
        if value in [None, ""]:
            for key in ("amount", "numeric_value", "total"):
                if field.get(key) not in [None, ""]:
                    return f"fields.{field_name}.{key}"
    return f"fields.{field_name}.value"


def _prediction_for_scalar(result: dict[str, Any], field_name: str) -> dict[str, Any]:
    field = (result.get("fields") or {}).get(field_name) or {}
    if not isinstance(field, dict):
        field = {"value": field}
    return {"value": _scalar_value_from_field(field, field_name), "confidence": field.get("confidence")}


def _compare_scalar_field(result: dict[str, Any], gold: dict[str, Any], field_name: str) -> dict[str, Any]:
    prediction = _prediction_for_scalar(result, field_name)
    gold_field = (gold.get("gold") or {}).get(field_name)
    compare_result = compare_field(field_name, prediction, gold_field)
    return {
        "field": field_name,
        "status": compare_result.get("status"),
        "issues": compare_result.get("issues") or [],
        "confidence": prediction.get("confidence"),
        "confidence_bucket": _confidence_bucket(_confidence(prediction)),
        "has_evidence": _has_field_evidence((result.get("fields") or {}).get(field_name) or {}),
    }


def _compare_stop_field(result: dict[str, Any], gold: dict[str, Any], field_name: str) -> list[dict[str, Any]]:
    fields = result.get("fields") or {}
    stops = fields.get(field_name) or []
    if not isinstance(stops, list):
        stops = []
    gold_stops = (gold.get("gold") or {}).get(field_name) or []
    if not stops:
        compare_result = compare_field(field_name, {"value": []}, gold_stops)
        return [
            {
                "field": field_name,
                "stop_index": None,
                "status": compare_result.get("status"),
                "tier": "missing_review_required",
                "issues": compare_result.get("issues") or [],
                "confidence": None,
                "confidence_bucket": "missing",
                "has_evidence": False,
                "requires_human_review": True,
                "auto_accept": False,
            }
        ]
    rows = []
    for index, stop in enumerate(stops):
        compare_result = compare_field(field_name, {"value": [stop], "confidence": stop.get("confidence")}, gold_stops)
        rows.append(
            {
                "field": field_name,
                "stop_index": stop.get("stop_index") or index + 1,
                "status": compare_result.get("status"),
                "tier": _stop_tier(compare_result, stop, gold_stops),
                "issues": compare_result.get("issues") or [],
                "confidence": stop.get("confidence"),
                "confidence_bucket": _confidence_bucket(_confidence(stop)),
                "has_evidence": _has_stop_evidence(stop),
                "requires_human_review": stop.get("requires_human_review") is True,
                "auto_accept": stop.get("auto_accept") is True,
            }
        )
        if compare_result.get("status") == STATUS_GOLD_UNCERTAIN:
            uncertain_result = _uncertain_gold_stop_result(stop, gold_stops)
            rows[-1]["status"] = uncertain_result["status"]
            rows[-1]["tier"] = uncertain_result["tier"]
            rows[-1]["issues"] = uncertain_result["issues"]
            rows[-1]["gold_uncertain_status"] = uncertain_result["status"]
    return rows


def _gold_scalar_value(gold_field: Any) -> Any:
    if isinstance(gold_field, dict):
        return gold_field.get("value")
    return gold_field


def _safe_or_private(value: Any, *, include_private_values_local_only: bool) -> Any:
    if include_private_values_local_only:
        return value
    return "<redacted>" if _text(value) else ""


def _money_diagnostic_row(
    *,
    result: dict[str, Any],
    gold: dict[str, Any],
    field_row: dict[str, Any],
    include_private_values_local_only: bool,
) -> dict[str, Any]:
    field = (result.get("fields") or {}).get(FIELD_TOTAL_CARRIER_RATE) or {}
    gold_field = (gold.get("gold") or {}).get(FIELD_TOTAL_CARRIER_RATE)
    hybrid_value = _scalar_value_from_field(field, FIELD_TOTAL_CARRIER_RATE)
    gold_value = _gold_scalar_value(gold_field)
    normalized_hybrid = normalize_money(hybrid_value)
    normalized_gold = normalize_money(gold_value)
    return {
        "document_id": _text(result.get("document_id")),
        "field": FIELD_TOTAL_CARRIER_RATE,
        "status": field_row.get("status"),
        "comparison_reason": ",".join(field_row.get("issues") or []),
        "tolerance_applied": "exact_decimal_cent_normalization",
        "source_field_path": _scalar_source_path(field, FIELD_TOTAL_CARRIER_RATE),
        "currency": _text(field.get("currency")) if isinstance(field, dict) else "",
        "hybrid_value_numeric": _safe_or_private(hybrid_value, include_private_values_local_only=include_private_values_local_only),
        "gold_value_numeric": _safe_or_private(gold_value, include_private_values_local_only=include_private_values_local_only),
        "normalized_hybrid_value": _safe_or_private(normalized_hybrid, include_private_values_local_only=include_private_values_local_only),
        "normalized_gold_value": _safe_or_private(normalized_gold, include_private_values_local_only=include_private_values_local_only),
    }


def _document_type_status(result: dict[str, Any], gold: dict[str, Any] | None) -> str:
    if not gold:
        return "missing_gold"
    predicted = _text(result.get("document_type"))
    gold_type = _text((gold.get("gold") or {}).get("document_type")) or "rate_confirmation"
    if not predicted:
        return "missing"
    if predicted == gold_type:
        return "correct"
    return "wrong"


def _empty_field_metrics() -> dict[str, dict[str, int]]:
    return {
        FIELD_LOAD_NUMBER: {"correct": 0, "wrong": 0, "missing": 0, "high_confidence_wrong": 0},
        FIELD_TOTAL_CARRIER_RATE: {"correct": 0, "wrong": 0, "missing": 0, "high_confidence_wrong": 0},
    }


def _empty_stop_metrics() -> dict[str, dict[str, int]]:
    return {
        FIELD_PICKUP_STOPS: {tier: 0 for tier in STOP_TIERS},
        FIELD_DELIVERY_STOPS: {tier: 0 for tier in STOP_TIERS},
    }


def run_hybrid_benchmark(
    *,
    hybrid_results_dir: Path,
    gold_dir: Path,
    audit: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    include_private_values_local_only: bool = False,
    strict_schema: bool = False,
    allow_missing_hybrid_results: bool = False,
    allow_unfilled_manual_templates: bool = False,
    write_review_packets: bool = False,
) -> dict[str, Any]:
    if not is_under_local_outputs(output_dir, REPO_ROOT):
        raise HybridBenchmarkError("Output directory must be under .local_outputs.")
    resolved_output = _repo_relative(output_dir)
    resolved_output.mkdir(parents=True, exist_ok=True)
    labels = load_gold_labels(_repo_relative(gold_dir))
    indexes = _gold_indexes(labels)
    hybrid_results = _load_hybrid_results(hybrid_results_dir, allow_missing=allow_missing_hybrid_results)
    audit_records = _read_audit_records(audit)
    audit_by_key = _audit_indexes(audit_records)

    schema_errors: list[dict[str, Any]] = []
    document_rows: list[dict[str, Any]] = []
    field_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    money_diagnostic_rows: list[dict[str, Any]] = []
    field_metrics = _empty_field_metrics()
    stop_metrics = _empty_stop_metrics()
    doc_type_counts = Counter()
    review_policy = Counter()
    evidence_metrics = Counter()
    gold_uncertain_metrics = Counter()
    confidence_buckets = Counter()
    unfilled_manual_template_count = 0
    non_rc_handling = Counter()

    for path, result in hybrid_results:
        validation = validate_hybrid_result(
            result,
            strict=False if allow_unfilled_manual_templates else strict_schema,
            include_private_values_local_only=include_private_values_local_only,
        )
        if not validation.valid:
            schema_errors.append(
                {
                    "file": path.name,
                    "document_id": _text(result.get("document_id")),
                    "errors": "; ".join(validation.errors),
                }
            )
            if strict_schema:
                continue
        gold = _match_gold(result, indexes)
        audit_record = _match_audit(result, audit_by_key)
        confirmed_non_rc = _is_confirmed_non_rc(result, gold, audit_record)
        document_type_mismatch = _is_document_type_mismatch(result, gold, audit_record)
        if _is_unfilled_manual_template(result) and not confirmed_non_rc:
            unfilled_manual_template_count += 1
        doc_status = _document_type_status(result, gold)
        if confirmed_non_rc:
            doc_status = "non_rc_filtered_correct"
        elif document_type_mismatch:
            doc_status = "document_type_mismatch"
        doc_type_counts[doc_status] += 1
        document_id = _text(result.get("document_id")) or path.stem
        file_name_or_label = _file_name_or_label(result, path.stem)
        document_type = _text(result.get("document_type"))
        doc_row = {
            "document_id": document_id,
            "file_name_or_label": file_name_or_label,
            "document_type": document_type,
            "schema_valid": validation.valid,
            "document_type_status": doc_status,
            "gold_matched": bool(gold),
            "requires_human_review": result.get("requires_human_review") is True,
            "private_local_only": result.get("private_local_only") is True,
        }
        document_rows.append(doc_row)
        if not gold and not confirmed_non_rc:
            error_rows.append(
                {
                    "document_id": document_id,
                    "field": "document",
                    "status": "missing_gold",
                    "issue": "hybrid_result_not_matched_to_gold",
                    "recommended_action": "needs_human_review",
                }
            )
            continue
        if document_type_mismatch:
            non_rc_handling["document_type_mismatch"] += 1
            error_rows.append(
                {
                    "document_id": document_id,
                    "field": "document_type",
                    "status": "document_type_mismatch",
                    "issue": "hybrid_non_rc_but_gold_rate_confirmation",
                    "recommended_action": "review_document_type",
                }
            )
        if confirmed_non_rc:
            non_rc_handling["non_rc_filtered_correct"] += 1
            flagged_fields = _non_rc_ratecon_fields_with_values(result)
            if flagged_fields:
                non_rc_handling["non_rc_has_ratecon_fields"] += 1
                error_rows.append(
                    {
                        "document_id": document_id,
                        "field": ",".join(flagged_fields),
                        "status": "non_rc_has_ratecon_fields",
                        "issue": "non_rc_has_ratecon_fields",
                        "recommended_action": "review_document_type_or_clear_fields",
                    }
                )
            for field_name in (FIELD_LOAD_NUMBER, FIELD_TOTAL_CARRIER_RATE):
                field_rows.append(_non_rc_scalar_row(document_id, field_name))
                non_rc_handling["non_rc_not_applicable_fields"] += 1
            for field_name in (FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS):
                field_rows.append(_non_rc_stop_row(document_id, field_name))
                stop_metrics[field_name]["not_applicable"] += 1
                non_rc_handling["non_rc_not_applicable_fields"] += 1
                if write_review_packets:
                    review_rows.append(
                        {
                            "document_id": document_id,
                            "file_name_or_label": file_name_or_label,
                            "document_type": document_type,
                            "field": field_name,
                            "stop_role": _stop_role(field_name),
                            "stop_index": "",
                            "status": "not_applicable",
                            "review_reason": "non_rc_filtered",
                            "evidence_status": "not_applicable",
                            "confidence": "",
                            "auto_accept_violation": False,
                            "missing_evidence": False,
                            "recommended_action": "no_action_non_rc",
                        }
                    )
            continue
        for field_name in (FIELD_LOAD_NUMBER, FIELD_TOTAL_CARRIER_RATE):
            row = _compare_scalar_field(result, gold, field_name)
            row["document_id"] = document_id
            field_rows.append(row)
            confidence_buckets[(field_name, row["confidence_bucket"])] += 1
            if _is_correct_status(row["status"]):
                field_metrics[field_name]["correct"] += 1
            elif _is_missing_status(row["status"]):
                field_metrics[field_name]["missing"] += 1
            else:
                field_metrics[field_name]["wrong"] += 1
                if (row.get("confidence") or 0) >= 0.8:
                    field_metrics[field_name]["high_confidence_wrong"] += 1
                if field_name == FIELD_TOTAL_CARRIER_RATE:
                    money_diagnostic_rows.append(
                        _money_diagnostic_row(
                            result=result,
                            gold=gold,
                            field_row=row,
                            include_private_values_local_only=include_private_values_local_only,
                        )
                    )
            if _field_has_value((result.get("fields") or {}).get(field_name)) and not row["has_evidence"]:
                evidence_metrics["field_without_evidence"] += 1
                error_rows.append(
                    {
                        "document_id": document_id,
                        "field": field_name,
                        "status": row["status"],
                        "issue": "missing_evidence",
                        "recommended_action": "missing_evidence",
                    }
                )
        for field_name in (FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS):
            for row in _compare_stop_field(result, gold, field_name):
                row["document_id"] = document_id
                field_rows.append(row)
                stop_metrics[field_name][row["tier"]] += 1
                if row["tier"] in UNCERTAIN_GOLD_REVIEW_TIERS:
                    gold_uncertain_metrics[row["tier"]] += 1
                    gold_uncertain_metrics["review_required"] += 1
                if row.get("gold_uncertain_status") == "matches_uncertain_gold_review_required":
                    gold_uncertain_metrics["matches_uncertain_gold"] += 1
                confidence_buckets[(field_name, row["confidence_bucket"])] += 1
                if row["auto_accept"]:
                    review_policy["stop_auto_accept_violation"] += 1
                    error_rows.append(
                        {
                            "document_id": document_id,
                            "field": field_name,
                            "status": row["status"],
                            "issue": "stop_auto_accept_violation",
                            "recommended_action": "reject_wrong",
                        }
                    )
                if not row["requires_human_review"]:
                    review_policy["missing_review_required_flag"] += 1
                    error_rows.append(
                        {
                            "document_id": document_id,
                            "field": field_name,
                            "status": row["status"],
                            "issue": "missing_review_required",
                            "recommended_action": "needs_human_review",
                        }
                    )
                if row["tier"] != "missing_review_required" and not row["has_evidence"]:
                    evidence_metrics["missing_evidence"] += 1
                    error_rows.append(
                        {
                            "document_id": document_id,
                            "field": field_name,
                            "status": row["status"],
                            "issue": "missing_evidence",
                            "recommended_action": "missing_evidence",
                        }
                    )
                if row["tier"] == "unsafe_wrong":
                    error_rows.append(
                        {
                            "document_id": document_id,
                            "field": field_name,
                            "status": row["status"],
                            "issue": "unsafe_wrong",
                            "recommended_action": "reject_wrong",
                        }
                    )
                if write_review_packets:
                    missing_evidence = row["tier"] != "missing_review_required" and not row["has_evidence"]
                    review_rows.append(
                        {
                            "document_id": document_id,
                            "file_name_or_label": file_name_or_label,
                            "document_type": document_type,
                            "field": field_name,
                            "stop_role": _stop_role(field_name),
                            "stop_index": row.get("stop_index") or "",
                            "status": row["tier"],
                            "review_reason": ",".join(row.get("issues") or []),
                            "evidence_status": "present" if row["has_evidence"] else "missing",
                            "confidence": row.get("confidence"),
                            "auto_accept_violation": bool(row["auto_accept"]),
                            "missing_evidence": bool(missing_evidence),
                            "recommended_action": _recommended_action(row),
                        }
                    )

    summary = {
        "schema_version": "ratecon_hybrid_benchmark_summary_v1",
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ai_model_invocation_attempted": False,
        "hybrid_result_count": len(hybrid_results),
        "gold_label_count": len(labels),
        "audit_path_supplied": bool(audit),
        "schema_error_count": len(schema_errors),
        "allow_unfilled_manual_templates": bool(allow_unfilled_manual_templates),
        "unfilled_manual_template_count": unfilled_manual_template_count,
        "document_classification": {
            "rate_confirmation_correct": doc_type_counts.get("correct", 0),
            "wrong": doc_type_counts.get("wrong", 0),
            "missing": doc_type_counts.get("missing", 0),
            "missing_gold": doc_type_counts.get("missing_gold", 0),
            "non_rc_bol_pod_filtered": non_rc_handling.get("non_rc_filtered_correct", 0),
            "non_rc_filtered_correct": non_rc_handling.get("non_rc_filtered_correct", 0),
            "document_type_mismatch": non_rc_handling.get("document_type_mismatch", 0),
        },
        "non_rc_handling": {
            "non_rc_filtered_correct": non_rc_handling.get("non_rc_filtered_correct", 0),
            "non_rc_not_applicable_fields": non_rc_handling.get("non_rc_not_applicable_fields", 0),
            "non_rc_has_ratecon_fields": non_rc_handling.get("non_rc_has_ratecon_fields", 0),
            "document_type_mismatch": non_rc_handling.get("document_type_mismatch", 0),
        },
        "field_metrics": field_metrics,
        "stop_metrics": stop_metrics,
        "review_policy": dict(review_policy),
        "evidence_metrics": dict(evidence_metrics),
        "gold_uncertain_metrics": dict(gold_uncertain_metrics),
        "money_diagnostic_count": len(money_diagnostic_rows),
        "confidence_buckets": {
            f"{field}:{bucket}": count
            for (field, bucket), count in sorted(confidence_buckets.items())
        },
        "baseline": BASELINE,
    }
    summary["one_screen_summary"] = {
        "results": len(hybrid_results),
        "schema_errors": len(schema_errors),
        "unfilled_manual_templates": unfilled_manual_template_count,
        "error_cases": len(error_rows),
        "stop_auto_accept_violations": review_policy.get("stop_auto_accept_violation", 0),
        "missing_evidence": evidence_metrics.get("missing_evidence", 0)
        + evidence_metrics.get("field_without_evidence", 0),
        "unsafe_wrong_stops": sum(metrics.get("unsafe_wrong", 0) for metrics in stop_metrics.values()),
        "gold_uncertain_review_required": gold_uncertain_metrics.get("review_required", 0),
        "matches_uncertain_gold": gold_uncertain_metrics.get("matches_uncertain_gold", 0),
        "non_rc_bol_pod_filtered": non_rc_handling.get("non_rc_filtered_correct", 0),
        "non_rc_filtered_correct": non_rc_handling.get("non_rc_filtered_correct", 0),
        "non_rc_not_applicable_fields": non_rc_handling.get("non_rc_not_applicable_fields", 0),
        "non_rc_has_ratecon_fields": non_rc_handling.get("non_rc_has_ratecon_fields", 0),
        "document_type_mismatch": non_rc_handling.get("document_type_mismatch", 0),
        "next_action": None,
    }
    summary["safety"] = {
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ai_model_invocation_attempted": False,
        "private_values_included": bool(include_private_values_local_only),
    }
    summary["error_case_examples"] = error_rows[:5]
    summary["next_action"] = _next_action(summary)
    summary["one_screen_summary"]["next_action"] = summary["next_action"]
    _write_outputs(
        resolved_output,
        summary=summary,
        document_rows=document_rows,
        field_rows=field_rows,
        error_rows=error_rows,
        schema_errors=schema_errors,
        review_rows=review_rows,
        money_diagnostic_rows=money_diagnostic_rows,
        include_private_values_local_only=include_private_values_local_only,
        write_review_packets=write_review_packets,
    )
    return summary


def _recommended_action(row: dict[str, Any]) -> str:
    if row.get("auto_accept"):
        return "reject_wrong"
    if not row.get("has_evidence"):
        return "missing_evidence"
    if row.get("tier") in UNCERTAIN_GOLD_REVIEW_TIERS:
        return "needs_human_review"
    if row.get("tier") == "unsafe_wrong":
        return "reject_wrong"
    if row.get("tier") in {"exact_complete", "dispatch_usable", "useful_partial"}:
        return "accept_for_review_draft"
    return "needs_human_review"


def _stop_role(field_name: str) -> str:
    if field_name == FIELD_PICKUP_STOPS:
        return "pickup"
    if field_name == FIELD_DELIVERY_STOPS:
        return "delivery"
    return ""


def _next_action(summary: dict[str, Any]) -> str:
    if summary.get("schema_error_count", 0):
        return "fix_schema_errors"
    if summary.get("review_policy", {}).get("stop_auto_accept_violation", 0):
        return "remove_stop_auto_accept_flags"
    evidence = summary.get("evidence_metrics", {})
    if evidence.get("missing_evidence", 0) or evidence.get("field_without_evidence", 0):
        return "add_missing_evidence"
    unsafe_wrong = sum(
        metrics.get("unsafe_wrong", 0)
        for metrics in (summary.get("stop_metrics") or {}).values()
        if isinstance(metrics, dict)
    )
    if unsafe_wrong:
        return "review_or_reject_unsafe_wrong_stops"
    if summary.get("gold_uncertain_metrics", {}).get("review_required", 0):
        return "review_uncertain_gold_cases"
    return "review_hybrid_drafts"


def _stop_metric_line(field_name: str, metrics: dict[str, int]) -> str:
    return (
        f"- {field_name}: exact {metrics.get('exact_complete', 0)} / "
        f"dispatch {metrics.get('dispatch_usable', 0)} / "
        f"partial {metrics.get('useful_partial', 0)} / "
        f"uncertain-review {sum(metrics.get(tier, 0) for tier in UNCERTAIN_GOLD_REVIEW_TIERS)} / "
        f"unsafe {metrics.get('unsafe_wrong', 0)} / "
        f"missing {metrics.get('missing_review_required', 0)}"
    )


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_outputs(
    output_dir: Path,
    *,
    summary: dict[str, Any],
    document_rows: list[dict[str, Any]],
    field_rows: list[dict[str, Any]],
    error_rows: list[dict[str, Any]],
    schema_errors: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
    money_diagnostic_rows: list[dict[str, Any]],
    include_private_values_local_only: bool,
    write_review_packets: bool,
) -> None:
    _write_json(output_dir / "hybrid_benchmark_summary.json", summary)
    one_screen = summary.get("one_screen_summary", {})
    safety = summary.get("safety", {})
    field_metrics = summary.get("field_metrics", {})
    stop_metrics = summary.get("stop_metrics", {})
    gold_uncertain_metrics = summary.get("gold_uncertain_metrics", {})
    error_examples = summary.get("error_case_examples") or []
    report = [
        "# RateCon Hybrid Benchmark Report",
        "",
        "This local-only benchmark made no AI, cloud, OCR, model, or PDF processing calls.",
        "",
        "## One-Screen Summary",
        "",
        f"- hybrid results: {one_screen.get('results', 0)}",
        f"- schema errors: {one_screen.get('schema_errors', 0)}",
        f"- unfilled manual templates: {one_screen.get('unfilled_manual_templates', 0)}",
        f"- error cases: {one_screen.get('error_cases', 0)}",
        f"- missing evidence: {one_screen.get('missing_evidence', 0)}",
        f"- stop auto-accept violations: {one_screen.get('stop_auto_accept_violations', 0)}",
        f"- unsafe wrong stops: {one_screen.get('unsafe_wrong_stops', 0)}",
        f"- gold uncertain review required: {one_screen.get('gold_uncertain_review_required', 0)}",
        f"- matches uncertain gold: {one_screen.get('matches_uncertain_gold', 0)}",
        f"- non-RC/BOL-POD filtered correctly: {one_screen.get('non_rc_filtered_correct', one_screen.get('non_rc_bol_pod_filtered', 0))}",
        f"- non-RC not-applicable rate-con fields: {one_screen.get('non_rc_not_applicable_fields', 0)}",
        f"- non-RC templates with rate-con fields: {one_screen.get('non_rc_has_ratecon_fields', 0)}",
        f"- document type mismatches: {one_screen.get('document_type_mismatch', 0)}",
        f"- next action: {summary.get('next_action', 'review_hybrid_drafts')}",
        "",
        "## Safety",
        "",
        f"- external API calls attempted: {safety.get('external_api_calls_attempted', False)}",
        f"- PDF processing attempted: {safety.get('pdf_processing_attempted', False)}",
        f"- AI/model invocation attempted: {safety.get('ai_model_invocation_attempted', False)}",
        f"- private values included: {safety.get('private_values_included', bool(include_private_values_local_only))}",
        "",
        "## Baseline Comparison",
        "",
        "- load_number: 25 correct / 1 wrong / 5 missing",
        (
            f"  - hybrid: {field_metrics.get(FIELD_LOAD_NUMBER, {}).get('correct', 0)} correct / "
            f"{field_metrics.get(FIELD_LOAD_NUMBER, {}).get('wrong', 0)} wrong / "
            f"{field_metrics.get(FIELD_LOAD_NUMBER, {}).get('missing', 0)} missing"
        ),
        "- total_carrier_rate: 26 correct / 3 wrong / 2 missing",
        (
            f"  - hybrid: {field_metrics.get(FIELD_TOTAL_CARRIER_RATE, {}).get('correct', 0)} correct / "
            f"{field_metrics.get(FIELD_TOTAL_CARRIER_RATE, {}).get('wrong', 0)} wrong / "
            f"{field_metrics.get(FIELD_TOTAL_CARRIER_RATE, {}).get('missing', 0)} missing"
        ),
        "- pickup stops: 0 exact / 17 partial / 5 wrong / 3 missing",
        _stop_metric_line(FIELD_PICKUP_STOPS, stop_metrics.get(FIELD_PICKUP_STOPS, {})),
        "- delivery stops: 0 exact / 12 partial / 5 wrong / 4 missing",
        _stop_metric_line(FIELD_DELIVERY_STOPS, stop_metrics.get(FIELD_DELIVERY_STOPS, {})),
        "",
        "## Uncertain Gold",
        "",
        f"- review-required uncertain gold stops: {gold_uncertain_metrics.get('review_required', 0)}",
        f"- matching uncertain gold stops: {gold_uncertain_metrics.get('matches_uncertain_gold', 0)}",
        f"- partial-match uncertain gold stops: {gold_uncertain_metrics.get('partial_match_uncertain_gold_review_required', 0)}",
        f"- other uncertain gold review stops: {gold_uncertain_metrics.get('gold_uncertain_review_required', 0)}",
        "",
        "## Money Diagnostics",
        "",
        f"- wrong money diagnostic rows: {summary.get('money_diagnostic_count', 0)}",
        "- diagnostics file: hybrid_money_diagnostics.csv",
        "",
        "## Non-RC Handling",
        "",
        f"- filtered correctly: {summary.get('non_rc_handling', {}).get('non_rc_filtered_correct', 0)}",
        f"- not-applicable rate-con field rows: {summary.get('non_rc_handling', {}).get('non_rc_not_applicable_fields', 0)}",
        f"- non-RC templates with rate-con values: {summary.get('non_rc_handling', {}).get('non_rc_has_ratecon_fields', 0)}",
        f"- document type mismatches: {summary.get('non_rc_handling', {}).get('document_type_mismatch', 0)}",
        "- blank load/rate/stop fields on confirmed non-RC documents are not evidence failures.",
        "",
        "## Error Case Examples",
        "",
    ]
    if error_examples:
        for row in error_examples:
            report.append(
                f"- {row.get('document_id', '')} {row.get('field', '')}: "
                f"{row.get('issue', '')} -> {row.get('recommended_action', '')}"
            )
    else:
        report.append("- none")
    report.extend(
        [
            "",
            "## Next Action",
            "",
            f"- {summary.get('next_action', 'review_hybrid_drafts')}",
        ]
    )
    (output_dir / "hybrid_benchmark_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    _write_csv(
        output_dir / "hybrid_field_metrics.csv",
        field_rows,
        [
            "document_id",
            "field",
            "stop_index",
            "status",
            "tier",
            "issues",
            "confidence",
            "confidence_bucket",
            "has_evidence",
            "requires_human_review",
            "auto_accept",
            "gold_uncertain_status",
        ],
    )
    _write_csv(
        output_dir / "hybrid_document_metrics.csv",
        document_rows,
        [
            "document_id",
            "file_name_or_label",
            "document_type",
            "schema_valid",
            "document_type_status",
            "gold_matched",
            "requires_human_review",
            "private_local_only",
        ],
    )
    _write_csv(
        output_dir / "hybrid_error_cases.csv",
        error_rows,
        ["document_id", "field", "status", "issue", "recommended_action"],
    )
    _write_csv(
        output_dir / "hybrid_money_diagnostics.csv",
        money_diagnostic_rows,
        [
            "document_id",
            "field",
            "status",
            "comparison_reason",
            "tolerance_applied",
            "source_field_path",
            "currency",
            "hybrid_value_numeric",
            "gold_value_numeric",
            "normalized_hybrid_value",
            "normalized_gold_value",
        ],
    )
    _write_csv(output_dir / "hybrid_schema_errors.csv", schema_errors, ["file", "document_id", "errors"])
    if write_review_packets:
        _write_json(output_dir / "hybrid_review_packet.json", {"items": review_rows})
        _write_csv(
            output_dir / "hybrid_review_items.csv",
            review_rows,
            [
                "document_id",
                "file_name_or_label",
                "document_type",
                "field",
                "stop_role",
                "stop_index",
                "status",
                "review_reason",
                "evidence_status",
                "confidence",
                "auto_accept_violation",
                "missing_evidence",
                "recommended_action",
            ],
        )
        lines = ["# Hybrid Review Packet", ""]
        for row in review_rows:
            lines.append(
                f"- {row['document_id']} {row['field']}[{row.get('stop_index', '')}]: "
                f"{row['recommended_action']} ({row['status']})"
            )
        (output_dir / "hybrid_review_packet.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark local-only RateCon hybrid result JSON files.")
    parser.add_argument("--hybrid-results-dir", type=Path, required=True)
    parser.add_argument("--gold-dir", type=Path, required=True)
    parser.add_argument("--audit", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    parser.add_argument("--strict-schema", action="store_true")
    parser.add_argument("--allow-missing-hybrid-results", action="store_true")
    parser.add_argument("--allow-unfilled-manual-templates", action="store_true")
    parser.add_argument("--write-review-packets", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required for local private benchmarks")
    summary = run_hybrid_benchmark(
        hybrid_results_dir=args.hybrid_results_dir,
        gold_dir=args.gold_dir,
        audit=args.audit,
        output_dir=args.output_dir,
        include_private_values_local_only=args.include_private_values_local_only,
        strict_schema=args.strict_schema,
        allow_missing_hybrid_results=args.allow_missing_hybrid_results,
        allow_unfilled_manual_templates=args.allow_unfilled_manual_templates,
        write_review_packets=args.write_review_packets,
    )
    print("RateCon hybrid benchmark summary")
    print(f"hybrid_result_count: {summary['hybrid_result_count']}")
    print(f"schema_error_count: {summary['schema_error_count']}")
    print(f"unfilled_manual_template_count: {summary['unfilled_manual_template_count']}")
    print("external_api_calls_attempted: False")
    print("pdf_processing_attempted: False")
    print("ai_model_invocation_attempted: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
