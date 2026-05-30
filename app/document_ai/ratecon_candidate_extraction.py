"""Orchestrate candidate extraction from fake/anonymized RateCon text artifacts."""

from app.document_ai.ratecon_candidate_generators import (
    build_identity_reference_candidate_result,
    build_money_rate_candidate_result,
    build_operational_detail_candidate_result,
    build_stop_candidate_result,
)
from app.document_ai.ratecon_candidates import build_candidate_extraction_result


RATECON_CANDIDATE_EXTRACTOR_VERSION = "ratecon_candidate_extractor_v1"


def _artifact_value(artifact, key):
    if isinstance(artifact, dict):
        return artifact.get(key, "")

    return getattr(artifact, key, "")


def _unique(values):
    seen = set()
    result = []

    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue

        seen.add(text)
        result.append(text)

    return result


def extract_ratecon_candidates(artifact):
    """Run all dependency-free RateCon candidate generators.

    This returns evidence candidates only. Final field assignment, review gating,
    and DispatchCase creation are separate downstream steps.
    """

    generator_results = [
        build_money_rate_candidate_result(artifact),
        build_identity_reference_candidate_result(artifact),
        build_stop_candidate_result(artifact),
        build_operational_detail_candidate_result(artifact),
    ]
    candidates = []
    missing_fields = []
    warnings = []

    for result in generator_results:
        candidates.extend(result.get("candidates", []))
        missing_fields.extend(result.get("missing_candidate_fields", []))
        warnings.extend(result.get("warnings", []))

    return build_candidate_extraction_result(
        document_id=_artifact_value(artifact, "document_id"),
        artifact_id=_artifact_value(artifact, "artifact_id"),
        candidates=candidates,
        missing_candidate_fields=_unique(missing_fields),
        warnings=_unique(warnings),
        extractor_version=RATECON_CANDIDATE_EXTRACTOR_VERSION,
    )
