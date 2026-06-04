"""Readiness gates for future local RateCon model-provider experiments.

This module defines approval-gate validation only. It does not execute models,
read PDFs, perform OCR, call networks, or approve real provider execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


READINESS_SCHEMA_VERSION = "ratecon_local_provider_readiness_v1"
READINESS_STATUSES = {
    "readiness_blocked",
    "fixture_only_plan_valid",
    "private_local_execution_not_approved",
    "cloud_execution_forbidden",
}
REQUESTED_CAPABILITY_KEYS = (
    "pdf_input",
    "image_input",
    "raw_text_input",
    "ocr_input",
    "private_value_copy",
    "external_calls",
)
PRIVACY_REVIEW_KEYS = (
    "private_data_stays_local",
    "no_external_calls",
    "no_model_weight_download_in_task",
    "no_private_prompt_logging",
    "no_private_response_logging",
    "output_redaction_default",
)
SAFETY_REVIEW_KEYS = (
    "auto_accept_disabled",
    "stops_review_required",
    "production_output_unchanged",
    "gold_labels_unchanged",
    "filled_templates_unchanged",
)
REQUIRED_REPORTS = (
    "schema_errors",
    "missing_evidence",
    "auto_accept_violations",
    "unsafe_wrong_stops",
    "manual_baseline_delta",
)


class RateConLocalProviderReadinessError(ValueError):
    """Raised when a readiness operation would be unsafe."""


@dataclass(frozen=True)
class ReadinessValidationResult:
    status: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    required_next_actions: tuple[str, ...]
    gate_results: tuple[dict[str, str], ...]

    @property
    def valid(self) -> bool:
        return self.status == "fixture_only_plan_valid" and not self.errors


def _text(value: Any) -> str:
    return str(value or "").strip()


def _gate(name: str, passed: bool, reason: str) -> dict[str, str]:
    return {
        "gate": name,
        "status": "passed" if passed else "failed",
        "reason": reason,
    }


def default_readiness_template(
    *,
    experiment_id: str = "local_provider_readiness_fixture_plan",
    provider_name: str = "local_model_placeholder_v1",
    provider_type: str = "local_model_placeholder",
) -> dict[str, Any]:
    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "provider_name": provider_name,
        "provider_type": provider_type,
        "requested_capabilities": {
            "pdf_input": False,
            "image_input": False,
            "raw_text_input": False,
            "ocr_input": False,
            "private_value_copy": False,
            "external_calls": False,
        },
        "privacy_review": {
            "private_data_stays_local": True,
            "no_external_calls": True,
            "no_model_weight_download_in_task": True,
            "no_private_prompt_logging": True,
            "no_private_response_logging": True,
            "output_redaction_default": True,
        },
        "safety_review": {
            "auto_accept_disabled": True,
            "stops_review_required": True,
            "production_output_unchanged": True,
            "gold_labels_unchanged": True,
            "filled_templates_unchanged": True,
        },
        "benchmark_plan": {
            "manual_baseline_required": True,
            "fixture_smoke_test_required": True,
            "private_pilot_requires_explicit_confirmation": True,
            "minimum_required_reports": list(REQUIRED_REPORTS),
        },
        "approval": {
            "approved_for_fixture_only": False,
            "approved_for_private_local_only": False,
            "approved_for_cloud": False,
            "reviewer": None,
            "review_notes": "",
        },
    }


def _object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def validate_readiness_payload(payload: Any) -> ReadinessValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    gates: list[dict[str, str]] = []
    actions: list[str] = [
        "keep provider execution disabled",
        "run fixture-only smoke tests before any implementation PR",
        "open a separate PR for any local provider implementation",
    ]
    if not isinstance(payload, dict):
        return ReadinessValidationResult(
            status="readiness_blocked",
            errors=("readiness payload must be an object",),
            warnings=(),
            required_next_actions=tuple(actions),
            gate_results=(_gate("readiness_object", False, "readiness payload must be an object"),),
        )
    if payload.get("schema_version") != READINESS_SCHEMA_VERSION:
        errors.append(f"schema_version must be {READINESS_SCHEMA_VERSION}")
    if not _text(payload.get("experiment_id")):
        errors.append("experiment_id is required")
    if not _text(payload.get("provider_name")):
        errors.append("provider_name is required")
    provider_type = _text(payload.get("provider_type"))
    if provider_type not in {"stub", "manual_baseline", "local_model_placeholder", "cloud_model_placeholder"}:
        errors.append("provider_type is invalid")

    requested = _object(payload, "requested_capabilities")
    for key in REQUESTED_CAPABILITY_KEYS:
        if requested.get(key) is not False:
            errors.append(f"requested_capabilities.{key} must be false for execution in this phase")
        gates.append(_gate(f"requested_{key}_disabled", requested.get(key) is False, f"{key} must be false"))

    privacy = _object(payload, "privacy_review")
    for key in PRIVACY_REVIEW_KEYS:
        if privacy.get(key) is not True:
            errors.append(f"privacy_review.{key} must be true")
        gates.append(_gate(f"privacy_{key}", privacy.get(key) is True, f"{key} must be true"))

    safety = _object(payload, "safety_review")
    for key in SAFETY_REVIEW_KEYS:
        if safety.get(key) is not True:
            errors.append(f"safety_review.{key} must be true")
        gates.append(_gate(f"safety_{key}", safety.get(key) is True, f"{key} must be true"))

    benchmark = _object(payload, "benchmark_plan")
    if benchmark.get("manual_baseline_required") is not True:
        errors.append("benchmark_plan.manual_baseline_required must be true")
    if benchmark.get("fixture_smoke_test_required") is not True:
        errors.append("benchmark_plan.fixture_smoke_test_required must be true")
    if benchmark.get("private_pilot_requires_explicit_confirmation") is not True:
        errors.append("benchmark_plan.private_pilot_requires_explicit_confirmation must be true")
    reports = benchmark.get("minimum_required_reports")
    report_set = {str(item) for item in reports} if isinstance(reports, list) else set()
    for report in REQUIRED_REPORTS:
        if report not in report_set:
            errors.append(f"benchmark_plan.minimum_required_reports missing {report}")
    gates.extend(
        [
            _gate("manual_baseline_required", benchmark.get("manual_baseline_required") is True, "manual baseline is required"),
            _gate("fixture_smoke_test_required", benchmark.get("fixture_smoke_test_required") is True, "fixture smoke test is required"),
            _gate(
                "private_pilot_confirmation_required",
                benchmark.get("private_pilot_requires_explicit_confirmation") is True,
                "private pilot requires explicit confirmation",
            ),
            _gate("minimum_reports_complete", set(REQUIRED_REPORTS).issubset(report_set), "minimum benchmark reports are required"),
        ]
    )

    approval = _object(payload, "approval")
    if approval.get("approved_for_private_local_only") is True:
        errors.append("approval.approved_for_private_local_only cannot be true in this pre-implementation phase")
        actions.append("remove private-local execution approval until a separate implementation PR is reviewed")
    if approval.get("approved_for_cloud") is True:
        errors.append("approval.approved_for_cloud is forbidden in this phase")
        actions.append("use a separate privacy and business approval path for cloud providers")
    if provider_type == "cloud_model_placeholder":
        warnings.append("cloud provider plans require a separate privacy and business approval")
    if provider_type == "local_model_placeholder":
        warnings.append("local model placeholder remains non-executable in this branch")
    gates.extend(
        [
            _gate(
                "private_local_execution_not_approved",
                approval.get("approved_for_private_local_only") is not True,
                "private local execution is not approved in this phase",
            ),
            _gate("cloud_execution_forbidden", approval.get("approved_for_cloud") is not True, "cloud execution is forbidden"),
        ]
    )

    if approval.get("approved_for_cloud") is True or provider_type == "cloud_model_placeholder":
        status = "cloud_execution_forbidden" if errors else "fixture_only_plan_valid"
    elif approval.get("approved_for_private_local_only") is True:
        status = "private_local_execution_not_approved"
    elif errors:
        status = "readiness_blocked"
    else:
        status = "fixture_only_plan_valid"
    return ReadinessValidationResult(
        status=status,
        errors=tuple(errors),
        warnings=tuple(warnings),
        required_next_actions=tuple(dict.fromkeys(actions)),
        gate_results=tuple(gates),
    )


def readiness_summary(payload: dict[str, Any]) -> dict[str, Any]:
    validation = validate_readiness_payload(payload)
    return {
        "schema_version": "ratecon_local_provider_readiness_summary_v1",
        "experiment_id": payload.get("experiment_id") if isinstance(payload, dict) else "",
        "provider_name": payload.get("provider_name") if isinstance(payload, dict) else "",
        "provider_type": payload.get("provider_type") if isinstance(payload, dict) else "",
        "status": validation.status,
        "valid": validation.valid,
        "blocking_reasons": list(validation.errors),
        "warnings": list(validation.warnings),
        "required_next_actions": list(validation.required_next_actions),
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "ai_model_invocation_attempted": False,
    }
