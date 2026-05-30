"""Orchestrator for dependency-free layout-aware RateCon candidates."""

from app.document_ai.extraction_scope import (
    select_pages_for_rate_candidates,
    select_pages_for_requirements_candidates,
    select_pages_for_stop_candidates,
    should_skip_ratecon_extraction,
)
from app.document_ai.layout_operational_candidates import generate_layout_operational_candidates
from app.document_ai.layout_rate_candidates import generate_layout_rate_candidates
from app.document_ai.layout_stop_candidates import generate_layout_stop_candidates
from app.document_ai.ratecon_candidates import build_candidate_extraction_result

LAYOUT_CANDIDATE_EXTRACTOR_VERSION = "layout_candidate_extraction_v1"


def _page_subset_artifact(layout_artifact, pages):
    selected_pages = [page for page in pages or [] if isinstance(page, dict)]
    return {
        "artifact_id": layout_artifact.get("artifact_id", ""),
        "document_id": layout_artifact.get("document_id", ""),
        "source_method": layout_artifact.get("source_method", "synthetic_fixture"),
        "provider": layout_artifact.get("provider", "synthetic"),
        "layout_version": layout_artifact.get("layout_version", ""),
        "pages": selected_pages,
        "page_count": len(selected_pages),
        "warning_codes": list(layout_artifact.get("warning_codes", [])),
        "raw_text_included": bool(layout_artifact.get("raw_text_included", False)),
        "private_values_redacted": bool(layout_artifact.get("private_values_redacted", True)),
    }


def _all_pages(layout_artifact):
    return [page for page in layout_artifact.get("pages", []) if isinstance(page, dict)]


def _selected_or_all(layout_artifact, classification_result, selector):
    if not classification_result:
        return _all_pages(layout_artifact)
    return selector(classification_result, layout_artifact)


def _candidate_field_counts(candidates):
    counts = {}
    for candidate in candidates or []:
        field_name = candidate.get("field_name", "")
        if field_name:
            counts[field_name] = counts.get(field_name, 0) + 1
    return dict(sorted(counts.items()))


def extract_ratecon_layout_candidates(layout_artifact, classification_result=None):
    warnings = ["layout_candidate_extraction_only"]

    if classification_result and should_skip_ratecon_extraction(classification_result):
        warnings.append("layout_extraction_skipped_by_classification")
        return build_candidate_extraction_result(
            document_id=layout_artifact.get("document_id", ""),
            artifact_id=layout_artifact.get("artifact_id", ""),
            candidates=[],
            missing_candidate_fields=[],
            warnings=warnings,
            extractor_version=LAYOUT_CANDIDATE_EXTRACTOR_VERSION,
        )

    rate_pages = _selected_or_all(layout_artifact, classification_result, select_pages_for_rate_candidates)
    stop_pages = _selected_or_all(layout_artifact, classification_result, select_pages_for_stop_candidates)
    requirement_pages = _selected_or_all(
        layout_artifact,
        classification_result,
        select_pages_for_requirements_candidates,
    )

    rate_candidates = generate_layout_rate_candidates(_page_subset_artifact(layout_artifact, rate_pages))
    stop_candidates = generate_layout_stop_candidates(_page_subset_artifact(layout_artifact, stop_pages))
    operational_candidates = generate_layout_operational_candidates(
        _page_subset_artifact(layout_artifact, requirement_pages)
    )

    candidates = rate_candidates + stop_candidates + operational_candidates
    result = build_candidate_extraction_result(
        document_id=layout_artifact.get("document_id", ""),
        artifact_id=layout_artifact.get("artifact_id", ""),
        candidates=candidates,
        missing_candidate_fields=[],
        warnings=warnings,
        extractor_version=LAYOUT_CANDIDATE_EXTRACTOR_VERSION,
    )
    result["candidate_counts_by_field"] = _candidate_field_counts(candidates)
    result["layout_pages_considered"] = sorted(
        {
            int(candidate.get("page_number") or 0)
            for candidate in candidates
            if candidate.get("page_number") not in [None, ""]
        }
    )
    return result
