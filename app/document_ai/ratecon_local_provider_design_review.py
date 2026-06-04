"""Design-review contract for future RateCon local-provider PRs.

This module consumes a fixture-only evidence-pack summary and creates a
copyable design-review checklist. It does not execute providers, call models,
read PDFs, perform OCR, or approve implementation work.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.document_ai.ratecon_local_provider_evidence_pack import validate_evidence_pack


DESIGN_REVIEW_SCHEMA_VERSION = "ratecon_local_provider_design_review_v1"
READY_EVIDENCE_RECOMMENDATION = "ready_for_separate_local_provider_design_pr"
DESIGN_RECOMMENDATIONS = {"reject", "design_review_incomplete", "design_pr_ready"}

PROPOSED_SCOPE_REQUIRED = {
    "implementation_pr_requested": False,
    "design_only": True,
    "runtime_execution_allowed": False,
    "private_execution_allowed": False,
    "pdf_processing_allowed": False,
    "ocr_allowed": False,
    "external_calls_allowed": False,
    "model_weight_download_allowed": False,
    "provider_registry_unblock_allowed": False,
}
INPUT_POLICY_REQUIRED = {
    "private_pdf_input": False,
    "private_text_input": False,
    "private_image_input": False,
    "fixture_only_inputs": True,
    "private_values_in_prompts": False,
    "private_values_in_logs": False,
}
OUTPUT_POLICY_REQUIRED = {
    "must_emit_model_assisted_submission_v1": True,
    "must_validate_hybrid_contract": True,
    "stops_review_required": True,
    "auto_accept_forbidden": True,
    "raw_model_response_private_local_only": True,
    "default_redaction_required": True,
}
BENCHMARK_POLICY_REQUIRED = {
    "manual_baseline_required": True,
    "full_corpus_private_benchmark_required_before_private_execution": True,
    "fixture_smoke_required_before_implementation": True,
    "safety_failure_blocks_progress": True,
}


class RateConLocalProviderDesignReviewError(ValueError):
    """Raised when design-review generation would be unsafe."""


@dataclass(frozen=True)
class DesignReviewValidationResult:
    recommendation: str
    blockers: tuple[str, ...]
    required_next_actions: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return self.recommendation == "design_pr_ready" and not self.blockers


def _text(value: Any) -> str:
    return str(value or "").strip()


def _object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def default_acceptance_criteria() -> list[dict[str, Any]]:
    """Return sanitized acceptance criteria for a future design PR."""

    return [
        {
            "id": "scope_design_only",
            "section": "scope",
            "criterion": "The PR is design-only and does not request implementation approval.",
            "required": True,
            "status": "required",
        },
        {
            "id": "scope_no_runtime_execution",
            "section": "scope",
            "criterion": "No runtime model, provider, private execution, PDF, OCR, external-call, or model-weight-download execution is allowed.",
            "required": True,
            "status": "required",
        },
        {
            "id": "scope_no_registry_unblock",
            "section": "scope",
            "criterion": "The design review cannot unblock provider registry blockers or make local/cloud placeholders executable.",
            "required": True,
            "status": "required",
        },
        {
            "id": "input_fixture_only",
            "section": "input_policy",
            "criterion": "Design inputs are fixture-only with no private PDFs, raw private text, or private images.",
            "required": True,
            "status": "required",
        },
        {
            "id": "output_model_assisted_contract",
            "section": "output_contract",
            "criterion": "Future generated submissions must use ratecon_model_assisted_submission_v1.",
            "required": True,
            "status": "required",
        },
        {
            "id": "output_hybrid_contract",
            "section": "output_contract",
            "criterion": "Embedded hybrid results must validate ratecon_hybrid_extraction_result_v1.",
            "required": True,
            "status": "required",
        },
        {
            "id": "safety_stops_review_required",
            "section": "safety",
            "criterion": "Stops remain review-required and cannot be auto-accepted.",
            "required": True,
            "status": "required",
        },
        {
            "id": "safety_no_production_changes",
            "section": "safety",
            "criterion": "Production extraction, legacy output, selected stop output, gold labels, and hybrid templates remain unchanged.",
            "required": True,
            "status": "required",
        },
        {
            "id": "benchmark_fixture_smoke_first",
            "section": "benchmark",
            "criterion": "Fixture smoke validation must pass before any implementation PR.",
            "required": True,
            "status": "required",
        },
        {
            "id": "benchmark_manual_baseline",
            "section": "benchmark",
            "criterion": "A future private benchmark must compare against the manual baseline before private execution is approved.",
            "required": True,
            "status": "required",
        },
        {
            "id": "privacy_no_committed_sensitive_outputs",
            "section": "privacy",
            "criterion": "No secrets, prompt logs, response logs, private outputs, local model weights, embeddings, or vector stores may be committed.",
            "required": True,
            "status": "required",
        },
        {
            "id": "privacy_redaction_default",
            "section": "privacy",
            "criterion": "Default reporting remains redacted and safe to copy into a PR.",
            "required": True,
            "status": "required",
        },
        {
            "id": "blocked_actions_explicit",
            "section": "blocked_actions",
            "criterion": "The checklist explicitly states that design approval is not implementation or model-execution approval.",
            "required": True,
            "status": "required",
        },
    ]


def default_design_review_template(
    *,
    design_review_id: str | None = None,
    provider_name: str = "local_model_placeholder_v1",
    created_at: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": DESIGN_REVIEW_SCHEMA_VERSION,
        "design_review_id": design_review_id or f"local_provider_design_{uuid4().hex}",
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "provider_name": provider_name,
        "provider_type": "local_model_design",
        "evidence_pack_reference": {
            "evidence_pack_id": "",
            "recommendation": "",
            "source_path": None,
            "validated": False,
        },
        "proposed_provider_scope": dict(PROPOSED_SCOPE_REQUIRED),
        "input_policy": dict(INPUT_POLICY_REQUIRED),
        "output_policy": dict(OUTPUT_POLICY_REQUIRED),
        "benchmark_policy": dict(BENCHMARK_POLICY_REQUIRED),
        "acceptance_criteria": default_acceptance_criteria(),
        "blockers": [],
        "required_next_actions": [],
        "recommendation": "design_review_incomplete",
    }


def _evidence_reference(evidence_pack_summary: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(evidence_pack_summary, dict) or not evidence_pack_summary:
        return {
            "evidence_pack_id": "",
            "recommendation": "",
            "source_path": None,
            "validated": False,
        }
    validation = validate_evidence_pack(evidence_pack_summary)
    return {
        "evidence_pack_id": _text(evidence_pack_summary.get("evidence_pack_id")),
        "recommendation": _text(evidence_pack_summary.get("recommendation")),
        "source_path": None,
        "validated": validation.valid,
    }


def _require_section_values(
    payload: dict[str, Any],
    section_name: str,
    required_values: dict[str, bool],
    blockers: list[str],
) -> None:
    section = _object(payload, section_name)
    for key, required in required_values.items():
        if section.get(key) is not required:
            blockers.append(f"{section_name}.{key} must be {str(required).lower()}")


def validate_design_review(payload: Any) -> DesignReviewValidationResult:
    if not isinstance(payload, dict):
        return DesignReviewValidationResult(
            recommendation="reject",
            blockers=("design review must be an object",),
            required_next_actions=("regenerate the design review from a ready evidence-pack summary",),
        )
    blockers: list[str] = []
    incomplete: list[str] = []
    if payload.get("schema_version") != DESIGN_REVIEW_SCHEMA_VERSION:
        blockers.append(f"schema_version must be {DESIGN_REVIEW_SCHEMA_VERSION}")
    if not _text(payload.get("design_review_id")):
        incomplete.append("design_review_id is required")
    if not _text(payload.get("provider_name")):
        incomplete.append("provider_name is required")
    if payload.get("provider_type") != "local_model_design":
        blockers.append("provider_type must be local_model_design")

    evidence = _object(payload, "evidence_pack_reference")
    evidence_id = _text(evidence.get("evidence_pack_id"))
    evidence_recommendation = _text(evidence.get("recommendation"))
    if not evidence_id or not evidence_recommendation:
        incomplete.append("evidence pack reference is required")
    elif evidence_recommendation != READY_EVIDENCE_RECOMMENDATION:
        blockers.append(f"evidence_pack_reference.recommendation must be {READY_EVIDENCE_RECOMMENDATION}")
    elif evidence.get("validated") is not True:
        blockers.append("evidence_pack_reference.validated must be true for design PR readiness")

    _require_section_values(payload, "proposed_provider_scope", PROPOSED_SCOPE_REQUIRED, blockers)
    _require_section_values(payload, "input_policy", INPUT_POLICY_REQUIRED, blockers)
    _require_section_values(payload, "output_policy", OUTPUT_POLICY_REQUIRED, blockers)
    _require_section_values(payload, "benchmark_policy", BENCHMARK_POLICY_REQUIRED, blockers)

    criteria = payload.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria:
        incomplete.append("acceptance_criteria are required")

    if blockers:
        recommendation = "reject"
        actions = [
            "fix unsafe design-review permissions before opening a design PR",
            "keep local and cloud model providers blocked",
            "do not execute models, process PDFs, run OCR, unblock providers, approve private execution, or edit gold/template files",
        ]
    elif incomplete:
        recommendation = "design_review_incomplete"
        actions = [
            "attach a ready fixture-only evidence-pack summary",
            "regenerate the design review checklist",
            "keep provider execution disabled",
        ]
        blockers = incomplete
    else:
        recommendation = "design_pr_ready"
        actions = [
            "copy the design PR checklist into a future GitHub PR body",
            "request separate approval before any implementation PR",
            "keep model execution, private execution, PDF processing, OCR, external calls, model downloads, and registry unblocking disabled",
        ]
    return DesignReviewValidationResult(
        recommendation=recommendation,
        blockers=tuple(_unique(blockers)),
        required_next_actions=tuple(_unique(actions)),
    )


def build_design_review(
    *,
    evidence_pack_summary: dict[str, Any] | None,
    provider_name: str = "local_model_placeholder_v1",
    design_review_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    review = default_design_review_template(
        design_review_id=design_review_id,
        provider_name=provider_name,
        created_at=created_at,
    )
    review["evidence_pack_reference"] = _evidence_reference(evidence_pack_summary)
    validation = validate_design_review(review)
    review["blockers"] = list(validation.blockers)
    review["required_next_actions"] = list(validation.required_next_actions)
    review["recommendation"] = validation.recommendation
    return review


def checklist_markdown(review: dict[str, Any]) -> str:
    """Build a sanitized, copyable PR checklist for a future design PR."""

    recommendation = _text(review.get("recommendation")) or "design_review_incomplete"
    criteria_count = len(review.get("acceptance_criteria", [])) if isinstance(review.get("acceptance_criteria"), list) else 0
    lines = [
        "# RateCon Local Provider Design PR Checklist",
        "",
        "**This checklist is not implementation approval and does not approve model execution, private execution, external calls, OCR, PDF processing, model-weight downloads, or provider-registry unblocking.**",
        "",
        f"- design review recommendation: {recommendation}",
        f"- acceptance criteria count: {criteria_count}",
        "",
        "## 1. Scope Confirmation",
        "",
        "- [ ] Design only; no provider implementation is included.",
        "- [ ] No runtime model execution is approved.",
        "- [ ] No private execution or provider-registry unblock is approved.",
        "- [ ] No PDF, OCR, or private document processing is approved.",
        "- [ ] No external calls or model-weight downloads are approved.",
        "- [ ] Implementation requires a separate PR and separate approval.",
        "",
        "## 2. Provider Input Policy",
        "",
        "- [ ] Fixture-only inputs are used for design validation.",
        "- [ ] No private PDFs are read, attached, processed, or committed.",
        "- [ ] No private raw text is copied into prompts, fixtures, logs, or reports.",
        "- [ ] No private images are used, processed, attached, or committed.",
        "",
        "## 3. Provider Output Contract",
        "",
        "- [ ] Future provider output must produce `ratecon_model_assisted_submission_v1`.",
        "- [ ] Embedded hybrid results must validate `ratecon_hybrid_extraction_result_v1`.",
        "- [ ] Raw model responses remain private-local-only and are redacted from review artifacts by default.",
        "",
        "## 4. Safety",
        "",
        "- [ ] Stops remain review-required.",
        "- [ ] `auto_accept` remains false.",
        "- [ ] Production and legacy output remain unchanged.",
        "- [ ] Selected stop output remains unchanged.",
        "- [ ] Gold labels and filled hybrid templates are not edited.",
        "- [ ] Local and cloud model placeholders remain blocked.",
        "",
        "## 5. Benchmark",
        "",
        "- [ ] Fixture smoke test is required before implementation.",
        "- [ ] Model-assisted benchmark wrapper is required for implementation evidence.",
        "- [ ] Benchmark reports compare against the manual baseline.",
        "- [ ] Any safety failure blocks progression.",
        "",
        "## 6. Privacy",
        "",
        "- [ ] No secrets or provider configs containing secrets are committed.",
        "- [ ] No prompt or response logs containing private values are committed.",
        "- [ ] No local model files, model weights, embeddings, or vector stores are committed.",
        "- [ ] Generated reports default to redaction and contain no private values.",
        "",
        "## 7. Required Tests",
        "",
        "- [ ] Contract validation tests cover ready, incomplete, rejected, and unsafe permission states.",
        "- [ ] CLI tests prove confirmation and `.local_outputs` restrictions.",
        "- [ ] Fixture-only smoke tests run before any implementation work.",
        "- [ ] Provider registry tests continue to prove local/cloud placeholders are blocked.",
        "",
        "## 8. Required Reports",
        "",
        "- [ ] Design review summary JSON.",
        "- [ ] Design review report markdown.",
        "- [ ] Acceptance criteria CSV.",
        "- [ ] Blockers CSV.",
        "- [ ] Next actions CSV.",
        "- [ ] Copyable PR checklist markdown.",
        "",
        "## 9. Explicit Blocked Actions",
        "",
        "- [ ] Do not implement a provider in the design PR.",
        "- [ ] Do not call AI, cloud APIs, local models, OCR, or PDF-processing tools.",
        "- [ ] Do not unblock local/cloud provider placeholders or approve private execution.",
        "- [ ] Do not download model weights.",
        "- [ ] Do not process private documents.",
        "- [ ] Do not edit gold labels or filled hybrid templates.",
        "- [ ] Do not claim production extraction improvement.",
    ]
    return "\n".join(lines) + "\n"


def report_markdown(review: dict[str, Any]) -> str:
    blockers = review.get("blockers", []) if isinstance(review.get("blockers"), list) else []
    actions = review.get("required_next_actions", []) if isinstance(review.get("required_next_actions"), list) else []
    return "\n".join(
        [
            "# RateCon Local Provider Design Review",
            "",
            "No model, cloud API, local model, PDF processing, OCR, gold-label edit, or hybrid-template edit occurred.",
            "",
            f"- recommendation: {review.get('recommendation')}",
            f"- provider name: {review.get('provider_name')}",
            f"- provider type: {review.get('provider_type')}",
            f"- evidence recommendation: {_object(review, 'evidence_pack_reference').get('recommendation')}",
            f"- evidence reference validated: {_object(review, 'evidence_pack_reference').get('validated')}",
            f"- acceptance criteria: {len(review.get('acceptance_criteria', []))}",
            f"- blockers: {len(blockers)}",
            f"- next actions: {len(actions)}",
            "",
            "This review can only support a future design PR. It cannot unblock provider execution or approve implementation.",
        ]
    ) + "\n"
