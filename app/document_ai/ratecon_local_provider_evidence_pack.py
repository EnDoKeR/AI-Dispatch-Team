"""Evidence-pack helpers for RateCon local-provider readiness review.

The evidence pack bundles sanitized readiness, provider config, fixture smoke,
and benchmark evidence. It never executes models, reads PDFs, performs OCR, or
approves provider implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.document_ai.ratecon_local_provider_readiness import (
    validate_readiness_payload,
)
from app.document_ai.ratecon_model_provider_registry import (
    evaluate_provider_readiness,
    get_provider_descriptor,
    validate_provider_selection,
)


EVIDENCE_PACK_SCHEMA_VERSION = "ratecon_local_provider_evidence_pack_v1"
RECOMMENDATIONS = {
    "reject",
    "fixture_only_continue",
    "ready_for_separate_local_provider_design_pr",
}
SAFETY_SUMMARY_KEYS = (
    "auto_accept_disabled",
    "stops_review_required",
    "production_output_unchanged",
    "gold_labels_unchanged",
    "filled_templates_unchanged",
    "redaction_default",
)
LOCAL_OUTPUT_MARKER = ".local_outputs"
PRIVATE_PATH_MARKERS = (
    ".local_outputs/private_",
    "data/" + "private_" + "ratecons",
    "private_ratecon",
    "private_pdf",
    "gold_labels_private",
)


class RateConLocalProviderEvidencePackError(ValueError):
    """Raised when evidence-pack generation would be unsafe."""


@dataclass(frozen=True)
class EvidencePackValidationResult:
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def _text(value: Any) -> str:
    return str(value or "").strip()


def _bool(value: Any) -> bool:
    return value is True or str(value).strip().lower() == "true"


def _object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _path_text(path: Path | str | None) -> str:
    return str(path or "").replace("\\", "/")


def _looks_private_path(path: Path | str | None) -> bool:
    text = _path_text(path).lower()
    return any(marker in text for marker in PRIVATE_PATH_MARKERS)


def _is_local_output(path: Path | str | None) -> bool:
    return LOCAL_OUTPUT_MARKER in _path_text(path).lower()


def artifact_index_row(
    *,
    artifact_name: str,
    artifact_type: str,
    path: Path | str,
    required_for_review: bool = True,
    notes: str = "",
) -> dict[str, Any]:
    resolved_path = Path(path)
    private_risk = _looks_private_path(path)
    under_local_outputs = _is_local_output(path)
    generated_from_fixtures_only = not private_risk
    return {
        "artifact_name": artifact_name,
        "artifact_type": artifact_type,
        "path": str(path),
        "exists": resolved_path.exists(),
        "safe_to_commit": not under_local_outputs and generated_from_fixtures_only,
        "contains_private_values": private_risk,
        "generated_from_fixtures_only": generated_from_fixtures_only,
        "required_for_review": required_for_review,
        "notes": notes,
    }


def build_artifact_index(
    *,
    readiness_file: Path,
    provider_config: Path,
    smoke_dir: Path,
    readiness_report_dir: Path,
    include_fixture_benchmark: bool = False,
) -> list[dict[str, Any]]:
    rows = [
        artifact_index_row(
            artifact_name="readiness_file",
            artifact_type="input",
            path=readiness_file,
            notes="Readiness checklist source.",
        ),
        artifact_index_row(
            artifact_name="provider_config",
            artifact_type="input",
            path=provider_config,
            notes="Provider config source.",
        ),
        artifact_index_row(
            artifact_name="fixture_smoke_summary",
            artifact_type="smoke_summary",
            path=smoke_dir / "fixture_smoke_summary.json",
            notes="Fixture-only smoke summary.",
        ),
        artifact_index_row(
            artifact_name="readiness_summary",
            artifact_type="readiness_summary",
            path=readiness_report_dir / "readiness_summary.json",
            notes="Readiness dry-run summary.",
        ),
        artifact_index_row(
            artifact_name="readiness_gate_results",
            artifact_type="gate_results",
            path=readiness_report_dir / "readiness_gate_results.csv",
            notes="Readiness and provider config gate results.",
        ),
    ]
    if include_fixture_benchmark:
        rows.append(
            artifact_index_row(
                artifact_name="fixture_model_assisted_benchmark_summary",
                artifact_type="benchmark_summary",
                path=smoke_dir / "model_assisted_benchmark" / "model_assisted_benchmark_summary.json",
                required_for_review=False,
                notes="Optional fixture benchmark summary.",
            )
        )
    return rows


def _safe_summary_from_readiness(readiness_payload: dict[str, Any]) -> dict[str, bool]:
    safety = _object(readiness_payload, "safety_review")
    privacy = _object(readiness_payload, "privacy_review")
    return {
        "auto_accept_disabled": safety.get("auto_accept_disabled") is True,
        "stops_review_required": safety.get("stops_review_required") is True,
        "production_output_unchanged": safety.get("production_output_unchanged") is True,
        "gold_labels_unchanged": safety.get("gold_labels_unchanged") is True,
        "filled_templates_unchanged": safety.get("filled_templates_unchanged") is True,
        "redaction_default": privacy.get("output_redaction_default") is True,
    }


def _flag(smoke_summary: dict[str, Any], *keys: str) -> bool:
    return any(_bool(smoke_summary.get(key)) for key in keys)


def _recommendation(
    *,
    blockers: list[str],
    smoke_present: bool,
    smoke_status: str,
    readiness_valid: bool,
    provider_config_valid: bool,
) -> str:
    if blockers or not readiness_valid or not provider_config_valid:
        return "reject"
    if not smoke_present or smoke_status != "fixture_smoke_passed_no_model_execution":
        return "fixture_only_continue"
    return "ready_for_separate_local_provider_design_pr"


def build_evidence_pack(
    *,
    readiness_payload: dict[str, Any],
    provider_config: dict[str, Any],
    smoke_summary: dict[str, Any] | None = None,
    readiness_report_summary: dict[str, Any] | None = None,
    artifact_index: list[dict[str, Any]] | None = None,
    evidence_pack_id: str | None = None,
    fail_on_warning: bool = False,
) -> dict[str, Any]:
    smoke = smoke_summary or {}
    smoke_present = bool(smoke_summary)
    readiness_validation = validate_readiness_payload(readiness_payload)
    provider_config_validation = validate_provider_selection(provider_config)
    provider_name = _text(provider_config.get("provider_name")) or _text(readiness_payload.get("provider_name"))
    provider_type = _text(readiness_payload.get("provider_type"))
    provider_registry_status = "unknown_provider"
    registry_blockers: list[str] = []
    if provider_name:
        try:
            descriptor = get_provider_descriptor(provider_name)
            provider_type = provider_type or descriptor.provider_type
            evaluation = evaluate_provider_readiness(provider_name, readiness_payload, provider_config)
            provider_registry_status = evaluation.get("provider_readiness_status", descriptor.status)
            registry_blockers = list(evaluation.get("blocking_reasons", []))
        except Exception as exc:  # pragma: no cover - defensive guard
            registry_blockers = [str(exc)]
    safety_summary = _safe_summary_from_readiness(readiness_payload)
    flags = {
        "model_execution_attempted": _flag(smoke, "model_execution_attempted", "ai_model_invocation_attempted"),
        "pdf_processing_attempted": _flag(smoke, "pdf_processing_attempted"),
        "ocr_attempted": _flag(smoke, "ocr_attempted"),
        "external_call_attempted": _flag(smoke, "external_call_attempted", "external_api_calls_attempted"),
        "private_data_used": _flag(smoke, "private_data_used"),
    }
    blockers: list[str] = []
    blockers.extend(readiness_validation.errors)
    blockers.extend(provider_config_validation.errors)
    for key, value in flags.items():
        if value:
            blockers.append(f"{key} must be false")
    for key in SAFETY_SUMMARY_KEYS:
        if safety_summary.get(key) is not True:
            blockers.append(f"safety_summary.{key} must be true")
    approval = _object(readiness_payload, "approval")
    if approval.get("approved_for_cloud") is True:
        blockers.append("cloud provider approval is forbidden in this phase")
    if approval.get("approved_for_private_local_only") is True:
        blockers.append("private local execution approval is forbidden in this phase")
    if _text(readiness_payload.get("provider_type")) == "cloud_model_placeholder":
        blockers.append("cloud provider plans cannot be approved by this pack")
    if provider_config_validation.valid is False:
        blockers.append("provider config validation failed")
    if fail_on_warning:
        blockers.extend(readiness_validation.warnings)
    blockers = list(dict.fromkeys(blockers + registry_blockers))
    smoke_status = _text(smoke.get("status")) or "missing"
    recommendation = _recommendation(
        blockers=blockers,
        smoke_present=smoke_present,
        smoke_status=smoke_status,
        readiness_valid=readiness_validation.valid,
        provider_config_valid=provider_config_validation.valid,
    )
    warnings = list(readiness_validation.warnings)
    if not smoke_present:
        warnings.append("fixture smoke outputs are missing")
    if readiness_report_summary and readiness_report_summary.get("status") != readiness_validation.status:
        warnings.append("readiness report summary differs from readiness file validation")
    next_actions = list(readiness_validation.required_next_actions)
    if recommendation == "fixture_only_continue":
        next_actions.append("run fixture smoke and regenerate the evidence pack")
    if recommendation == "ready_for_separate_local_provider_design_pr":
        next_actions.append("prepare a separate local-provider design PR with no implementation approval implied")
    return {
        "schema_version": EVIDENCE_PACK_SCHEMA_VERSION,
        "evidence_pack_id": evidence_pack_id or f"evidence_pack_{uuid4().hex}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "experiment_id": readiness_payload.get("experiment_id"),
        "provider_name": provider_name,
        "provider_type": provider_type,
        "readiness_status": readiness_validation.status,
        "provider_registry_status": provider_registry_status,
        "provider_config_status": "valid" if provider_config_validation.valid else "invalid",
        "fixture_smoke_status": smoke_status,
        "model_execution_attempted": flags["model_execution_attempted"],
        "pdf_processing_attempted": flags["pdf_processing_attempted"],
        "ocr_attempted": flags["ocr_attempted"],
        "external_call_attempted": flags["external_call_attempted"],
        "private_data_used": flags["private_data_used"],
        "manual_baseline_required": _object(readiness_payload, "benchmark_plan").get("manual_baseline_required") is True,
        "benchmark_required": _object(readiness_payload, "benchmark_plan").get("fixture_smoke_test_required") is True,
        "safety_summary": safety_summary,
        "gate_results": list(readiness_validation.gate_results) + list(provider_config_validation.safety_gates),
        "blockers": blockers,
        "warnings": list(dict.fromkeys(warnings)),
        "required_next_actions": list(dict.fromkeys(next_actions)),
        "recommendation": recommendation,
        "recommendation_note": (
            "This does not approve model implementation; it only supports proposing a separate local-provider design PR."
        ),
        "artifact_index": artifact_index or [],
    }


def validate_evidence_pack(pack: Any) -> EvidencePackValidationResult:
    errors: list[str] = []
    if not isinstance(pack, dict):
        return EvidencePackValidationResult(("evidence pack must be an object",))
    if pack.get("schema_version") != EVIDENCE_PACK_SCHEMA_VERSION:
        errors.append(f"schema_version must be {EVIDENCE_PACK_SCHEMA_VERSION}")
    if pack.get("recommendation") not in RECOMMENDATIONS:
        errors.append("recommendation is invalid")
    for key in ("model_execution_attempted", "pdf_processing_attempted", "ocr_attempted", "external_call_attempted", "private_data_used"):
        if pack.get(key) is True:
            errors.append(f"{key} must be false")
    safety = pack.get("safety_summary") if isinstance(pack.get("safety_summary"), dict) else {}
    for key in SAFETY_SUMMARY_KEYS:
        if safety.get(key) is not True:
            errors.append(f"safety_summary.{key} must be true")
    if pack.get("recommendation") == "ready_for_separate_local_provider_design_pr" and pack.get("blockers"):
        errors.append("ready recommendation cannot have blockers")
    return EvidencePackValidationResult(tuple(errors))
