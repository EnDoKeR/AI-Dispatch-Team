"""Contract helpers for local-only RateCon model-assisted submissions.

This module validates wrappers around future model-assisted RateCon hybrid
results. It does not call models, OCR, cloud APIs, local runtimes, or PDF
readers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.document_ai.ratecon_hybrid_contract import (
    build_hybrid_result_template,
    validate_hybrid_result,
)


MODEL_ASSISTED_SCHEMA_VERSION = "ratecon_model_assisted_submission_v1"
ALLOWED_PROVIDER_TYPES = {"stub", "manual_baseline", "local_model", "cloud_model"}
PHASE_ALLOWED_PROVIDER_TYPES = {"stub", "manual_baseline", "local_model"}
REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "submission_id",
    "run_id",
    "created_at",
    "provider",
    "input_policy",
    "result",
    "safety",
)


class ModelAssistedContractError(ValueError):
    """Raised for model-assisted submission validation errors."""


@dataclass(frozen=True)
class ModelAssistedValidationResult:
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def _text(value: Any) -> str:
    return str(value or "").strip()


def _iter_stops(result: dict[str, Any]):
    fields = result.get("fields") if isinstance(result.get("fields"), dict) else {}
    for field_name in ("pickup_stops", "delivery_stops"):
        stops = fields.get(field_name) or []
        if isinstance(stops, list):
            for stop in stops:
                if isinstance(stop, dict):
                    yield field_name, stop


def build_model_assisted_submission(
    result: dict[str, Any] | None = None,
    *,
    submission_id: str | None = None,
    run_id: str = "model_assisted_stub_run_v1",
    provider_type: str = "stub",
    provider_name: str = "local_no_model_stub",
    model_name: str | None = None,
    model_version: str | None = None,
) -> dict[str, Any]:
    hybrid_result = result or build_hybrid_result_template("MODEL_ASSISTED_STUB")
    return {
        "schema_version": MODEL_ASSISTED_SCHEMA_VERSION,
        "submission_id": submission_id or f"mas_{uuid4().hex}",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider": {
            "provider_type": provider_type,
            "provider_name": provider_name,
            "model_name": model_name,
            "model_version": model_version,
            "offline_only": True,
            "external_call_made": False,
        },
        "input_policy": {
            "private_local_only": True,
            "pdf_processed": False,
            "ocr_processed": False,
            "raw_text_included": False,
            "images_included": False,
        },
        "result": hybrid_result,
        "safety": {
            "auto_accept_disabled": True,
            "stops_review_required": True,
            "no_private_values_in_default_logs": True,
        },
    }


def validate_model_assisted_submission(
    submission: Any,
    *,
    strict_hybrid: bool = True,
    include_private_values_local_only: bool = False,
) -> ModelAssistedValidationResult:
    errors: list[str] = []
    if not isinstance(submission, dict):
        return ModelAssistedValidationResult(("model-assisted submission must be an object",))
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in submission:
            errors.append(f"{field} is required")
    if submission.get("schema_version") != MODEL_ASSISTED_SCHEMA_VERSION:
        errors.append(f"schema_version must be {MODEL_ASSISTED_SCHEMA_VERSION}")
    if not _text(submission.get("submission_id")):
        errors.append("submission_id is required")
    if not _text(submission.get("run_id")):
        errors.append("run_id is required")
    if not _text(submission.get("created_at")):
        errors.append("created_at is required")

    provider = submission.get("provider")
    if not isinstance(provider, dict):
        errors.append("provider must be an object")
        provider = {}
    provider_type = provider.get("provider_type")
    if provider_type not in ALLOWED_PROVIDER_TYPES:
        errors.append("provider.provider_type is invalid")
    if provider_type not in PHASE_ALLOWED_PROVIDER_TYPES:
        errors.append("provider.provider_type cloud_model is not allowed in this phase")
    if provider.get("offline_only") is not True:
        errors.append("provider.offline_only must be true in this phase")
    if provider.get("external_call_made") is not False:
        errors.append("provider.external_call_made must be false in this phase")
    if not _text(provider.get("provider_name")):
        errors.append("provider.provider_name is required")

    input_policy = submission.get("input_policy")
    if not isinstance(input_policy, dict):
        errors.append("input_policy must be an object")
        input_policy = {}
    if input_policy.get("private_local_only") is not True:
        errors.append("input_policy.private_local_only must be true")
    for key in ("pdf_processed", "ocr_processed", "raw_text_included", "images_included"):
        if input_policy.get(key) is not False:
            errors.append(f"input_policy.{key} must be false in this phase")

    safety = submission.get("safety")
    if not isinstance(safety, dict):
        errors.append("safety must be an object")
        safety = {}
    if safety.get("auto_accept_disabled") is not True:
        errors.append("safety.auto_accept_disabled must be true")
    if safety.get("stops_review_required") is not True:
        errors.append("safety.stops_review_required must be true")
    if safety.get("no_private_values_in_default_logs") is not True:
        errors.append("safety.no_private_values_in_default_logs must be true")

    result = submission.get("result")
    hybrid_validation = validate_hybrid_result(
        result,
        strict=strict_hybrid,
        include_private_values_local_only=include_private_values_local_only,
    )
    errors.extend(f"result.{error}" for error in hybrid_validation.errors)
    if isinstance(result, dict):
        for field_name, stop in _iter_stops(result):
            if stop.get("auto_accept") is True:
                errors.append(f"result.fields.{field_name}[].auto_accept must be false")
            if stop.get("requires_human_review") is not True:
                errors.append(f"result.fields.{field_name}[].requires_human_review must be true")
    return ModelAssistedValidationResult(tuple(errors))


def require_valid_model_assisted_submission(
    submission: Any,
    *,
    strict_hybrid: bool = True,
    include_private_values_local_only: bool = False,
) -> dict[str, Any]:
    validation = validate_model_assisted_submission(
        submission,
        strict_hybrid=strict_hybrid,
        include_private_values_local_only=include_private_values_local_only,
    )
    if not validation.valid:
        raise ModelAssistedContractError("; ".join(validation.errors))
    return submission


def safe_submission_shape(submission: dict[str, Any]) -> dict[str, Any]:
    provider = submission.get("provider") if isinstance(submission.get("provider"), dict) else {}
    input_policy = submission.get("input_policy") if isinstance(submission.get("input_policy"), dict) else {}
    result = submission.get("result") if isinstance(submission.get("result"), dict) else {}
    return {
        "schema_version": submission.get("schema_version"),
        "submission_id": submission.get("submission_id"),
        "run_id": submission.get("run_id"),
        "provider_type": provider.get("provider_type"),
        "provider_name": provider.get("provider_name"),
        "offline_only": provider.get("offline_only"),
        "external_call_made": provider.get("external_call_made"),
        "private_local_only": input_policy.get("private_local_only"),
        "pdf_processed": input_policy.get("pdf_processed"),
        "ocr_processed": input_policy.get("ocr_processed"),
        "document_id": result.get("document_id"),
        "document_type": result.get("document_type"),
    }
