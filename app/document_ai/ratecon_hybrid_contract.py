"""Contract helpers for local-only RateCon hybrid extraction evaluation.

The contract is intentionally dependency-light. It validates JSON submitted by a
future human or model pipeline, but it does not call models, OCR, PDF readers, or
production extraction code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


HYBRID_SCHEMA_VERSION = "ratecon_hybrid_extraction_result_v1"
STOP_SCHEMA_VERSION = "ratecon_hybrid_stop_v1"

ALLOWED_DOCUMENT_TYPES = {
    "rate_confirmation",
    "bol_pod",
    "non_rate_confirmation",
    "bill_of_lading_or_delivery_receipt",
    "unknown",
}
ALLOWED_MODEL_PROVIDERS = {
    "local_stub",
    "local_vlm",
    "commercial_doc_ai",
    "manual",
}
ALLOWED_STOP_ROLES = {"pickup", "delivery"}
ALLOWED_EVIDENCE_SOURCES = {"native_text", "OCR", "image", "model"}

REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "document_id",
    "document_type",
    "model_provider",
    "model_name",
    "private_local_only",
    "fields",
    "evidence",
    "confidence",
    "requires_human_review",
    "review_reasons",
    "validator_results",
)

REQUIRED_FIELD_GROUPS = (
    "load_number",
    "total_carrier_rate",
    "pickup_stops",
    "delivery_stops",
)

STOP_COMPONENT_KEYS = (
    "facility",
    "address",
    "city",
    "state",
    "zip",
    "date",
    "time",
    "appointment_window",
    "raw_text_local_only",
)

PRIVATE_VALUE_KEYS = {
    "raw_text_local_only",
    "raw_location_text_local_only",
    "unparsed_location_text_local_only",
}


class HybridContractError(ValueError):
    """Raised for contract validation errors."""


@dataclass(frozen=True)
class HybridValidationResult:
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def _text(value: Any) -> str:
    return str(value or "").strip()


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _path_text(path: str, suffix: str) -> str:
    return f"{path}.{suffix}" if path else suffix


def is_under_local_outputs(path: Path, repo_root: Path | None = None) -> bool:
    root = (repo_root or Path.cwd()).resolve()
    resolved = (root / path).resolve() if not path.is_absolute() else path.resolve()
    local_outputs = (root / ".local_outputs").resolve()
    return resolved == local_outputs or local_outputs in resolved.parents


def build_stop_template(role: str = "pickup", stop_index: int = 1) -> dict[str, Any]:
    return {
        "schema_version": STOP_SCHEMA_VERSION,
        "role": role,
        "stop_index": stop_index,
        "facility": None,
        "address": None,
        "city": None,
        "state": None,
        "zip": None,
        "date": None,
        "time": None,
        "appointment_window": None,
        "raw_text_local_only": None,
        "evidence_page": None,
        "evidence_bbox": None,
        "confidence": 0.0,
        "requires_human_review": True,
        "auto_accept": False,
        "evidence_ids": [],
    }


def build_hybrid_result_template(document_id: str = "RATECON_001") -> dict[str, Any]:
    return {
        "schema_version": HYBRID_SCHEMA_VERSION,
        "document_id": document_id,
        "document_type": "rate_confirmation",
        "model_provider": "local_stub",
        "model_name": "no_model_stub",
        "private_local_only": True,
        "fields": {
            "load_number": {
                "value": None,
                "confidence": 0.0,
                "requires_human_review": True,
                "evidence_ids": [],
            },
            "total_carrier_rate": {
                "value": None,
                "currency": "USD",
                "confidence": 0.0,
                "requires_human_review": True,
                "evidence_ids": [],
            },
            "pickup_stops": [build_stop_template("pickup", 1)],
            "delivery_stops": [build_stop_template("delivery", 1)],
        },
        "evidence": [],
        "confidence": {
            "overall": 0.0,
            "load_number": 0.0,
            "total_carrier_rate": 0.0,
            "pickup_stops": 0.0,
            "delivery_stops": 0.0,
        },
        "requires_human_review": True,
        "review_reasons": ["phase_1_no_auto_accept", "local_stub_no_model_output"],
        "validator_results": {
            "document_classification_gate": {"status": "not_evaluated"},
            "critical_field_gate": {"status": "not_evaluated"},
            "stop_consistency_gate": {"status": "review_required"},
            "evidence_gate": {"status": "not_evaluated"},
            "confidence_review_gate": {"status": "review_required"},
            "no_auto_accept_gate": {"status": "passed"},
        },
    }


def _evidence_map(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    evidence_rows = result.get("evidence") or []
    if not isinstance(evidence_rows, list):
        return {}
    mapping = {}
    for item in evidence_rows:
        if isinstance(item, dict) and _text(item.get("evidence_id")):
            mapping[_text(item.get("evidence_id"))] = item
    return mapping


def _validate_evidence_item(path: str, item: Any, errors: list[str]) -> None:
    if not isinstance(item, dict):
        errors.append(f"{path} must be an object")
        return
    if not _text(item.get("evidence_id")):
        errors.append(f"{path}.evidence_id is required")
    if not _text(item.get("field")):
        errors.append(f"{path}.field is required")
    if item.get("page") is not None and not isinstance(item.get("page"), int):
        errors.append(f"{path}.page must be integer or null")
    source = item.get("source")
    if source not in ALLOWED_EVIDENCE_SOURCES:
        errors.append(f"{path}.source must be one of {sorted(ALLOWED_EVIDENCE_SOURCES)}")


def _stop_has_component_value(stop: dict[str, Any]) -> bool:
    return any(_has_value(stop.get(key)) for key in STOP_COMPONENT_KEYS)


def _field_has_value(field: Any) -> bool:
    if isinstance(field, dict):
        return _has_value(field.get("value"))
    return _has_value(field)


def _has_stop_evidence(stop: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> bool:
    if isinstance(stop.get("evidence_page"), int):
        return True
    evidence_ids = stop.get("evidence_ids") or []
    if isinstance(evidence_ids, list) and any(_text(eid) in evidence for eid in evidence_ids):
        return True
    return False


def _has_field_evidence(field: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> bool:
    evidence_ids = field.get("evidence_ids") or []
    return isinstance(evidence_ids, list) and any(_text(eid) in evidence for eid in evidence_ids)


def _contains_private_value_keys(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in PRIVATE_VALUE_KEYS and _has_value(child):
                return True
            if _contains_private_value_keys(child):
                return True
    if isinstance(value, list):
        return any(_contains_private_value_keys(child) for child in value)
    return False


def validate_stop(
    stop: Any,
    *,
    path: str = "stop",
    evidence: dict[str, dict[str, Any]] | None = None,
    require_evidence_for_values: bool = True,
) -> list[str]:
    errors: list[str] = []
    evidence = evidence or {}
    if not isinstance(stop, dict):
        return [f"{path} must be an object"]
    if stop.get("role") not in ALLOWED_STOP_ROLES:
        errors.append(f"{path}.role must be pickup or delivery")
    stop_index = stop.get("stop_index")
    if not isinstance(stop_index, int) or stop_index < 1:
        errors.append(f"{path}.stop_index must be a positive integer")
    if stop.get("requires_human_review") is not True:
        errors.append(f"{path}.requires_human_review must be true in phase 1")
    if stop.get("auto_accept") is True:
        errors.append(f"{path}.auto_accept must be false in phase 1")
    if require_evidence_for_values and _stop_has_component_value(stop) and not _has_stop_evidence(stop, evidence):
        errors.append(f"{path} has values but no evidence")
    return errors


def validate_hybrid_result(
    result: Any,
    *,
    private_benchmark: bool = True,
    strict: bool = True,
    include_private_values_local_only: bool = False,
) -> HybridValidationResult:
    errors: list[str] = []
    if not isinstance(result, dict):
        return HybridValidationResult(("hybrid result must be an object",))
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in result:
            errors.append(f"{field} is required")
    if result.get("schema_version") != HYBRID_SCHEMA_VERSION:
        errors.append(f"schema_version must be {HYBRID_SCHEMA_VERSION}")
    if result.get("document_type") not in ALLOWED_DOCUMENT_TYPES:
        errors.append("document_type is invalid")
    if result.get("model_provider") not in ALLOWED_MODEL_PROVIDERS:
        errors.append("model_provider is invalid")
    if private_benchmark and result.get("private_local_only") is not True:
        errors.append("private_local_only must be true for private benchmarks")
    if result.get("requires_human_review") is not True:
        errors.append("requires_human_review must be true")
    if not isinstance(result.get("review_reasons"), list):
        errors.append("review_reasons must be a list")
    if not isinstance(result.get("validator_results"), dict):
        errors.append("validator_results must be an object")
    fields = result.get("fields")
    if not isinstance(fields, dict):
        errors.append("fields must be an object")
        fields = {}
    for field_group in REQUIRED_FIELD_GROUPS:
        if field_group not in fields:
            errors.append(f"fields.{field_group} is required")
    evidence_rows = result.get("evidence")
    if not isinstance(evidence_rows, list):
        errors.append("evidence must be a list")
        evidence_rows = []
    for index, item in enumerate(evidence_rows):
        _validate_evidence_item(f"evidence[{index}]", item, errors)
    evidence = _evidence_map(result)
    for field_name in ("load_number", "total_carrier_rate"):
        field = fields.get(field_name)
        if isinstance(field, dict) and _field_has_value(field) and strict and not _has_field_evidence(field, evidence):
            errors.append(f"fields.{field_name} has value but no evidence")
    for stop_field in ("pickup_stops", "delivery_stops"):
        stops = fields.get(stop_field, [])
        if stops is None:
            stops = []
        if not isinstance(stops, list):
            errors.append(f"fields.{stop_field} must be a list")
            continue
        for index, stop in enumerate(stops):
            errors.extend(
                validate_stop(
                    stop,
                    path=f"fields.{stop_field}[{index}]",
                    evidence=evidence,
                    require_evidence_for_values=strict,
                )
            )
    if not include_private_values_local_only and _contains_private_value_keys(result):
        errors.append("private local-only values present without explicit private flag")
    return HybridValidationResult(tuple(errors))


def require_valid_hybrid_result(
    result: Any,
    *,
    private_benchmark: bool = True,
    strict: bool = True,
    include_private_values_local_only: bool = False,
) -> dict[str, Any]:
    validation = validate_hybrid_result(
        result,
        private_benchmark=private_benchmark,
        strict=strict,
        include_private_values_local_only=include_private_values_local_only,
    )
    if not validation.valid:
        raise HybridContractError("; ".join(validation.errors))
    return result


def safe_output_shape(result: dict[str, Any]) -> dict[str, Any]:
    fields = result.get("fields") if isinstance(result.get("fields"), dict) else {}
    return {
        "schema_version": result.get("schema_version"),
        "document_id": result.get("document_id"),
        "document_type": result.get("document_type"),
        "model_provider": result.get("model_provider"),
        "model_name": result.get("model_name"),
        "private_local_only": result.get("private_local_only"),
        "requires_human_review": result.get("requires_human_review"),
        "review_reasons": result.get("review_reasons") if isinstance(result.get("review_reasons"), list) else [],
        "field_presence": {
            "load_number": _field_has_value(fields.get("load_number")),
            "total_carrier_rate": _field_has_value(fields.get("total_carrier_rate")),
            "pickup_stop_count": len(fields.get("pickup_stops") or []) if isinstance(fields.get("pickup_stops"), list) else 0,
            "delivery_stop_count": len(fields.get("delivery_stops") or []) if isinstance(fields.get("delivery_stops"), list) else 0,
        },
        "evidence_count": len(result.get("evidence") or []) if isinstance(result.get("evidence"), list) else 0,
    }
