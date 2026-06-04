"""Disabled-by-default provider adapter contract for RateCon model assistance.

The contract defines provider descriptors, safe config validation, and dry-run
planning. It does not execute models, call networks, read PDFs, OCR, or modify
gold/template files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.document_ai.ratecon_hybrid_contract import build_hybrid_result_template
from app.document_ai.ratecon_model_assisted_contract import (
    build_model_assisted_submission,
    validate_model_assisted_submission,
)


PROVIDER_CONFIG_SCHEMA_VERSION = "ratecon_model_provider_config_v1"
PROVIDER_TYPES = {"stub", "manual_baseline", "local_model_placeholder", "cloud_model_placeholder"}
PROVIDER_STATUSES = {
    "available_disabled",
    "blocked_requires_explicit_opt_in",
    "blocked_requires_api_key",
    "blocked_network_provider_not_allowed",
    "blocked_real_model_execution_not_implemented",
    "ready_stub_only",
}
SECRET_KEY_TOKENS = ("api_key", "token", "secret", "password")
UNSAFE_FALSE_FLAGS = (
    "allow_external_calls",
    "allow_pdf_processing",
    "allow_ocr_processing",
    "allow_raw_text_input",
    "allow_image_input",
    "allow_private_value_copy",
)


class RateConModelProviderError(ValueError):
    """Raised when a provider config or operation is unsafe."""


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_type: str
    provider_name: str
    supports_pdf_input: bool
    supports_text_input: bool
    supports_image_input: bool
    requires_network: bool
    requires_api_key: bool
    offline_only: bool
    can_execute: bool
    status: str
    blocking_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_type": self.provider_type,
            "provider_name": self.provider_name,
            "supports_pdf_input": self.supports_pdf_input,
            "supports_text_input": self.supports_text_input,
            "supports_image_input": self.supports_image_input,
            "requires_network": self.requires_network,
            "requires_api_key": self.requires_api_key,
            "offline_only": self.offline_only,
            "can_execute": self.can_execute,
            "status": self.status,
            "blocking_reasons": list(self.blocking_reasons),
        }


@dataclass(frozen=True)
class ProviderConfigValidationResult:
    errors: tuple[str, ...]
    safety_gates: tuple[dict[str, str], ...]

    @property
    def valid(self) -> bool:
        return not self.errors


class RateConModelProviderAdapter:
    """Interface for future provider adapters.

    Real provider execution is intentionally not implemented in this phase.
    """

    descriptor: ProviderDescriptor

    def __init__(self, descriptor: ProviderDescriptor):
        self.descriptor = descriptor

    def validate_config(self, config: dict[str, Any]) -> ProviderConfigValidationResult:
        return validate_provider_config(config, self.descriptor)

    def dry_run_plan(
        self,
        config: dict[str, Any],
        *,
        template_count: int = 0,
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        validation = self.validate_config(config)
        return {
            "schema_version": "ratecon_model_provider_dry_run_plan_v1",
            "provider": self.descriptor.to_dict(),
            "config_valid": validation.valid,
            "errors": list(validation.errors),
            "template_count": template_count,
            "output_dir": str(output_dir) if output_dir else "",
            "execution_planned": False,
            "external_api_calls_attempted": False,
            "pdf_processing_attempted": False,
            "ocr_attempted": False,
            "ai_model_invocation_attempted": False,
            "safety_gate_results": list(validation.safety_gates),
        }

    def build_submission(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RateConModelProviderError("Provider execution is disabled in this phase.")


class StubEmptyProviderAdapter(RateConModelProviderAdapter):
    """Stub-only adapter that can create empty local submissions."""

    def build_submission(self, document_id: str = "MODEL_PROVIDER_STUB") -> dict[str, Any]:
        if not self.descriptor.can_execute:
            raise RateConModelProviderError("Stub provider is not executable with this descriptor.")
        result = build_hybrid_result_template(document_id)
        result["fields"]["pickup_stops"] = []
        result["fields"]["delivery_stops"] = []
        result["model_provider"] = "local_stub"
        result["model_name"] = "provider_stub_empty_v1"
        submission = build_model_assisted_submission(
            result,
            provider_type="stub",
            provider_name=self.descriptor.provider_name,
        )
        validation = validate_model_assisted_submission(submission, strict_hybrid=False)
        if not validation.valid:
            raise RateConModelProviderError("; ".join(validation.errors))
        return submission


def _text(value: Any) -> str:
    return str(value or "").strip()


def _secret_key_paths(value: Any, path: str = "config") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).lower()
            child_path = f"{path}.{key}"
            if any(token in key_text for token in SECRET_KEY_TOKENS):
                paths.append(child_path)
            paths.extend(_secret_key_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_secret_key_paths(child, f"{path}[{index}]"))
    return paths


def _gate(name: str, passed: bool, reason: str) -> dict[str, str]:
    return {
        "gate": name,
        "status": "passed" if passed else "failed",
        "reason": reason,
    }


def default_provider_config(provider_name: str = "stub_empty_v1", run_id: str = "local_stub_run") -> dict[str, Any]:
    return {
        "schema_version": PROVIDER_CONFIG_SCHEMA_VERSION,
        "provider_name": provider_name,
        "run_id": run_id,
        "private_local_only": True,
        "allow_external_calls": False,
        "allow_pdf_processing": False,
        "allow_ocr_processing": False,
        "allow_raw_text_input": False,
        "allow_image_input": False,
        "allow_private_value_copy": False,
        "output_redaction_default": True,
    }


def validate_provider_config(
    config: Any,
    descriptor: ProviderDescriptor | None = None,
) -> ProviderConfigValidationResult:
    errors: list[str] = []
    gates: list[dict[str, str]] = []
    if not isinstance(config, dict):
        return ProviderConfigValidationResult(("config must be an object",), (_gate("config_object", False, "config must be an object"),))
    if config.get("schema_version") != PROVIDER_CONFIG_SCHEMA_VERSION:
        errors.append(f"schema_version must be {PROVIDER_CONFIG_SCHEMA_VERSION}")
    provider_name = _text(config.get("provider_name"))
    if not provider_name:
        errors.append("provider_name is required")
    if not _text(config.get("run_id")):
        errors.append("run_id is required")
    if config.get("private_local_only") is not True:
        errors.append("private_local_only must be true")
    for flag in UNSAFE_FALSE_FLAGS:
        if config.get(flag) is not False:
            errors.append(f"{flag} must be false in this phase")
    if config.get("output_redaction_default") is not True:
        errors.append("output_redaction_default must be true")
    secret_paths = _secret_key_paths(config)
    for path in secret_paths:
        errors.append(f"secret-like config key is not allowed: {path}")
    gates.extend(
        [
            _gate("private_local_only", config.get("private_local_only") is True, "private_local_only must be true"),
            _gate("external_calls_disabled", config.get("allow_external_calls") is False, "external calls are disabled"),
            _gate("pdf_processing_disabled", config.get("allow_pdf_processing") is False, "PDF processing is disabled"),
            _gate("ocr_processing_disabled", config.get("allow_ocr_processing") is False, "OCR processing is disabled"),
            _gate("raw_text_input_disabled", config.get("allow_raw_text_input") is False, "raw text input is disabled"),
            _gate("image_input_disabled", config.get("allow_image_input") is False, "image input is disabled"),
            _gate("private_value_copy_disabled", config.get("allow_private_value_copy") is False, "private value copy is disabled"),
            _gate("output_redaction_default", config.get("output_redaction_default") is True, "default output redaction is required"),
            _gate("no_secret_keys", not secret_paths, "secret-like keys are not allowed"),
        ]
    )
    if descriptor:
        if descriptor.provider_type == "cloud_model_placeholder":
            errors.append("cloud_model_placeholder is blocked in this phase")
        if descriptor.provider_type == "local_model_placeholder":
            errors.append("local_model_placeholder is blocked in this phase")
        if descriptor.requires_network:
            errors.append("network providers are not allowed in this phase")
        if descriptor.requires_api_key:
            errors.append("providers requiring API keys are not allowed in this phase")
        if descriptor.provider_type == "manual_baseline":
            errors.append("manual_baseline is reference-only and cannot execute")
        if descriptor.provider_type != "stub":
            errors.append("only stub providers can execute in this phase")
        if descriptor.provider_type == "stub" and not descriptor.can_execute:
            errors.append("stub provider is not marked executable")
        gates.append(
            _gate(
                "provider_execution_allowed",
                descriptor.provider_type == "stub" and descriptor.can_execute,
                descriptor.status,
            )
        )
    return ProviderConfigValidationResult(tuple(errors), tuple(gates))
