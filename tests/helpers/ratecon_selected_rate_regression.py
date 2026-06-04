"""Sanitized selected-rate regression helpers for RateCon resolver tests."""

from __future__ import annotations

import json
from pathlib import Path

from app.document_ai.field_candidate_resolver import (
    FIELD_TOTAL_CARRIER_RATE,
    RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
    resolve_candidates,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "ratecon_selected_rate_regression"
    / "selected_rate_cases.json"
)

FORBIDDEN_PRIVATE_MARKERS = (
    ".local_outputs",
    "data/private_ratecons",
    ".pdf",
    ".gold.json",
    "api_key",
    "secret",
    "token",
    "spreadsheet",
    "service account",
    "raw text",
    "private_ratecon",
)


def load_selected_rate_cases(path: Path | None = None) -> list[dict]:
    """Load sanitized selected-rate fixture cases."""
    fixture_path = Path(path or FIXTURE_PATH)
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def build_candidate(raw: dict) -> dict:
    """Build the current resolver candidate shape from sanitized fixture data."""
    label = str(raw.get("label") or "")
    value = str(raw.get("value") or "")
    return {
        "field": raw.get("field") or FIELD_TOTAL_CARRIER_RATE,
        "value": value,
        "normalized_value": str(raw.get("normalized_value") or value),
        "label": label,
        "evidence_text": str(raw.get("evidence_text") or label),
        "source": str(raw.get("source") or "native_layout"),
        "parser_name": str(raw.get("parser_name") or "sanitized_selected_rate_fixture"),
        "confidence": float(raw.get("confidence") or 0.0),
        "metadata": dict(raw.get("metadata") or {}),
    }


def build_candidates(raw_candidates: list[dict]) -> list[dict]:
    """Build all candidates for a selected-rate fixture case."""
    return [build_candidate(candidate) for candidate in raw_candidates]


def _float_or_none(value):
    if value in ("", None):
        return None
    return float(value)


def normalize_selected_rate_result(case: dict, result: dict) -> dict:
    """Normalize resolver output to a stable selected-rate snapshot."""
    resolution = (result.get("resolved_fields") or {}).get(FIELD_TOTAL_CARRIER_RATE, {})
    selected = resolution.get("selected_candidate") or {}
    metadata = selected.get("metadata") or {}
    return {
        "case_id": case["id"],
        "known_debt": bool(case.get("known_debt")),
        "selected_value": str(resolution.get("value") or ""),
        "selected_label": str(selected.get("label") or ""),
        "selected_source": str(selected.get("source") or ""),
        "selected_confidence": _float_or_none(selected.get("confidence")),
        "selected_score": float(resolution.get("confidence") or 0.0),
        "selected_money_context": str(metadata.get("money_context") or ""),
        "selected_rate_safety": str(metadata.get("rate_safety") or ""),
        "selected_rate_safety_reason": str(metadata.get("rate_safety_reason") or ""),
        "resolved_candidate_count": int(resolution.get("candidate_count") or 0),
        "input_candidate_count": len(case.get("candidates") or []),
        "needs_review": bool(resolution.get("needs_review")),
        "review_reasons": sorted(resolution.get("review_reasons") or []),
        "global_needs_review": bool(result.get("needs_review")),
        "global_review_reasons": sorted(result.get("review_reasons") or []),
    }


def run_selected_rate_case(case: dict) -> dict:
    """Run one sanitized fixture case through the current resolver path."""
    result = resolve_candidates(
        build_candidates(case.get("candidates") or []),
        field_names=[FIELD_TOTAL_CARRIER_RATE],
        rate_ranking_profile=RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
    )
    return normalize_selected_rate_result(case, result)


def run_selected_rate_cases(cases: list[dict] | None = None) -> list[dict]:
    """Run all selected-rate fixture cases through the current resolver path."""
    return [run_selected_rate_case(case) for case in (cases or load_selected_rate_cases())]


def assert_no_private_fixture_values(cases: list[dict]) -> None:
    """Raise AssertionError if a fixture contains private/local markers."""
    payload = json.dumps(cases, sort_keys=True).lower()
    hits = [marker for marker in FORBIDDEN_PRIVATE_MARKERS if marker in payload]
    if hits:
        raise AssertionError(f"selected-rate fixture contains private markers: {hits}")
