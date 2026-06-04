"""Provider registry for disabled-by-default RateCon model assistance."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.document_ai.ratecon_model_provider_contract import (
    ProviderConfigValidationResult,
    ProviderDescriptor,
    RateConModelProviderAdapter,
    RateConModelProviderError,
    StubEmptyProviderAdapter,
    validate_provider_config,
)


PROVIDERS: dict[str, ProviderDescriptor] = {
    "stub_empty_v1": ProviderDescriptor(
        provider_type="stub",
        provider_name="stub_empty_v1",
        supports_pdf_input=False,
        supports_text_input=False,
        supports_image_input=False,
        requires_network=False,
        requires_api_key=False,
        offline_only=True,
        can_execute=True,
        status="ready_stub_only",
        blocking_reasons=(),
    ),
    "manual_baseline_reference_v1": ProviderDescriptor(
        provider_type="manual_baseline",
        provider_name="manual_baseline_reference_v1",
        supports_pdf_input=False,
        supports_text_input=False,
        supports_image_input=False,
        requires_network=False,
        requires_api_key=False,
        offline_only=True,
        can_execute=False,
        status="available_disabled",
        blocking_reasons=("manual baseline is reference-only and cannot copy private values by default",),
    ),
    "local_model_placeholder_v1": ProviderDescriptor(
        provider_type="local_model_placeholder",
        provider_name="local_model_placeholder_v1",
        supports_pdf_input=False,
        supports_text_input=False,
        supports_image_input=False,
        requires_network=False,
        requires_api_key=False,
        offline_only=True,
        can_execute=False,
        status="blocked_real_model_execution_not_implemented",
        blocking_reasons=("local model execution is not implemented in this phase",),
    ),
    "cloud_model_placeholder_v1": ProviderDescriptor(
        provider_type="cloud_model_placeholder",
        provider_name="cloud_model_placeholder_v1",
        supports_pdf_input=False,
        supports_text_input=False,
        supports_image_input=False,
        requires_network=True,
        requires_api_key=True,
        offline_only=False,
        can_execute=False,
        status="blocked_network_provider_not_allowed",
        blocking_reasons=("cloud/network providers are not allowed in this phase", "API-key providers are blocked"),
    ),
}


def list_available_providers() -> list[dict[str, Any]]:
    return [PROVIDERS[name].to_dict() for name in sorted(PROVIDERS)]


def get_provider_descriptor(provider_name: str) -> ProviderDescriptor:
    if provider_name not in PROVIDERS:
        raise RateConModelProviderError(f"Unknown provider: {provider_name}")
    return PROVIDERS[provider_name]


def get_provider_adapter(provider_name: str) -> RateConModelProviderAdapter:
    descriptor = get_provider_descriptor(provider_name)
    if descriptor.provider_type == "stub":
        return StubEmptyProviderAdapter(descriptor)
    return RateConModelProviderAdapter(descriptor)


def validate_provider_selection(config: dict[str, Any]) -> ProviderConfigValidationResult:
    provider_name = str(config.get("provider_name") or "").strip()
    if provider_name not in PROVIDERS:
        base = validate_provider_config(config)
        errors = list(base.errors)
        errors.append(f"Unknown provider: {provider_name or '<missing>'}")
        return ProviderConfigValidationResult(tuple(errors), base.safety_gates)
    return validate_provider_config(config, PROVIDERS[provider_name])


def provider_blocking_reasons(provider_name: str) -> list[str]:
    descriptor = get_provider_descriptor(provider_name)
    reasons = list(descriptor.blocking_reasons)
    if not descriptor.can_execute:
        reasons.append(descriptor.status)
    return reasons


def dry_run_provider_plan(
    config: dict[str, Any],
    *,
    template_count: int = 0,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    provider_name = str(config.get("provider_name") or "").strip()
    adapter = get_provider_adapter(provider_name)
    return adapter.dry_run_plan(config, template_count=template_count, output_dir=output_dir)
