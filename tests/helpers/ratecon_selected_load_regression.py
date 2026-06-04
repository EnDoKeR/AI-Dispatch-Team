"""Sanitized selected-load regression helper.

The helper builds fake load-number candidates and calls the current public
RateCon field resolver. It does not duplicate resolver selection logic.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

from app.document_ai.load_identifier_candidates import build_load_identifier_candidate
from app.document_ai.ratecon_candidates import FIELD_LOAD_NUMBER
from app.document_ai.ratecon_field_resolution import resolve_ratecon_fields


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "ratecon_selected_load_regression"
    / "selected_load_cases.json"
)


def load_selected_load_cases(path: Path = FIXTURE_PATH) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("cases") or [])


def _candidate_from_spec(spec: dict) -> dict:
    if spec.get("kind", "load_identifier") != "load_identifier":
        raise ValueError(f"unsupported selected-load fixture candidate kind: {spec.get('kind')}")
    candidate = build_load_identifier_candidate(
        candidate_id=spec.get("candidate_id", ""),
        identifier_type=spec.get("identifier_type", ""),
        raw_value=spec.get("value", ""),
        normalized_value=spec.get("normalized_value", spec.get("value", "")),
        confidence=spec.get("confidence", ""),
        confidence_reasons=spec.get("confidence_reasons", []),
        page_number=spec.get("page_number", ""),
        line_number=spec.get("line_number", ""),
        label=spec.get("label", ""),
        context_before=spec.get("context_before", ""),
        context_after=spec.get("context_after", ""),
        source=spec.get("source", "label_pattern"),
        evidence_ref=spec.get("evidence_ref", ""),
        warnings=spec.get("warnings", []),
        section_role=spec.get("section_role", ""),
        page_role=spec.get("page_role", ""),
        primary_load_identifier_candidate=spec.get("primary_load_identifier_candidate"),
    )
    metadata = dict(candidate.get("metadata") or {})
    metadata.update(dict(spec.get("metadata") or {}))
    if metadata:
        candidate["metadata"] = metadata
    return candidate


def run_selected_load_case(case: dict) -> dict:
    candidates = [_candidate_from_spec(spec) for spec in case.get("candidates", [])]
    result = resolve_ratecon_fields(
        {"candidates": deepcopy(candidates)},
        field_names=[FIELD_LOAD_NUMBER],
    )
    resolution = result["resolutions"][0]
    return {
        "case_id": case.get("case_id", ""),
        "selected_value": resolution.get("selected_candidate_value", ""),
        "selected_source": resolution.get("selected_candidate_source", ""),
        "selected_confidence": resolution.get("confidence", ""),
        "selected_label": resolution.get("selected_candidate_label", ""),
        "status": resolution.get("status", ""),
        "reasons": list(resolution.get("reasons", []) or []),
        "warnings": list(resolution.get("warnings", []) or []),
        "warning_codes": list(resolution.get("warning_codes", []) or []),
        "candidate_count": len(candidates),
        "missing": FIELD_LOAD_NUMBER in (result.get("missing_fields") or []),
        "needs_check": FIELD_LOAD_NUMBER in (result.get("needs_check_fields") or []),
        "conflict": FIELD_LOAD_NUMBER in (result.get("conflict_fields") or []),
        "known_debt": bool(case.get("known_debt")),
        "debt_note": case.get("debt_note", ""),
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
    }


def run_selected_load_cases(cases: list[dict] | None = None) -> list[dict]:
    return [run_selected_load_case(case) for case in (cases or load_selected_load_cases())]
