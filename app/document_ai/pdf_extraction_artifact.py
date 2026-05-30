"""Build safe extraction artifacts from PDF triage results."""

from app.document_ai.extraction_artifacts import build_extraction_artifact
from app.document_ai.pdf_triage_contract import (
    DIGITAL_TEXT,
    MANUAL_REVIEW,
    OCR_NEEDED,
    UNSUPPORTED,
    VISION_REVIEW_CANDIDATE,
)


NEXT_STEPS_BY_ROUTE = {
    DIGITAL_TEXT: "candidate_extraction_ready",
    OCR_NEEDED: "ocr_needed_not_implemented",
    VISION_REVIEW_CANDIDATE: "vision_review_future_only",
    UNSUPPORTED: "unsupported_or_broken_pdf",
    MANUAL_REVIEW: "manual_review_required",
}


def value_from(source, key, default=""):
    if isinstance(source, dict):
        return source.get(key, default)

    return getattr(source, key, default)


def build_pdf_extraction_artifact(
    triage_result,
    method,
    provider,
    extractor_version,
):
    route = str(value_from(triage_result, "recommended_route", MANUAL_REVIEW) or MANUAL_REVIEW)
    page_count = value_from(triage_result, "page_count", 0)
    char_count = value_from(triage_result, "char_count", 0)
    text_summary = (
        f"route={route}; pages={page_count}; chars={char_count}; "
        f"text_layer={bool(value_from(triage_result, 'has_text_layer', False))}"
    )

    return build_extraction_artifact(
        document_id=value_from(triage_result, "document_id", ""),
        method=method,
        provider=provider,
        extractor_version=extractor_version,
        page_count=page_count,
        char_count=char_count,
        text_summary=text_summary,
        page_profiles=value_from(triage_result, "page_profiles", []),
        warnings=value_from(triage_result, "warnings", []),
        recommended_route=route,
        recommended_next_step=NEXT_STEPS_BY_ROUTE.get(route, "manual_review_required"),
        triage_version=value_from(triage_result, "triage_version", ""),
    )
