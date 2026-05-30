"""Pipeline boundary from PDF layout providers to layout-aware candidates."""

from copy import deepcopy

from app.document_ai.layout_candidate_extraction import extract_ratecon_layout_candidates
from app.document_ai.layout_provider import (
    PROVIDER_PDFPLUMBER,
    STATUS_SUCCESS,
    extract_layout_artifact,
)


LAYOUT_CANDIDATE_PIPELINE_VERSION = "layout_candidate_pipeline_v1"


def _candidate_field_counts(candidate_result):
    counts = {}
    for candidate in (candidate_result or {}).get("candidates", []):
        field_name = candidate.get("field_name", "")
        if field_name:
            counts[field_name] = counts.get(field_name, 0) + 1
    return dict(sorted(counts.items()))


def _classification_page_map(classification_result):
    pages = (classification_result or {}).get("page_results", [])
    return {
        int(page.get("page_number", index) or index): page
        for index, page in enumerate(pages or [], start=1)
        if isinstance(page, dict)
    }


def _section_roles(page_result):
    roles = []
    for section in page_result.get("section_summaries", []) or []:
        if not isinstance(section, dict):
            continue
        role = str(section.get("section_role") or "").strip()
        if role and role not in roles:
            roles.append(role)
    return roles


def _apply_classification_context(layout_artifact, classification_result):
    if not classification_result:
        return layout_artifact

    artifact = deepcopy(layout_artifact)
    classification_pages = _classification_page_map(classification_result)

    for page in artifact.get("pages", []):
        page_number = int(page.get("page_number") or 0)
        page_result = classification_pages.get(page_number)
        if not page_result:
            continue

        page["page_roles"] = list(page_result.get("page_roles", []) or [])
        section_roles = _section_roles(page_result)
        page["section_roles"] = section_roles

        if len(section_roles) == 1:
            section_role = section_roles[0]
            for line in page.get("lines", []):
                if not line.get("section_role"):
                    line["section_role"] = section_role
            for block in page.get("blocks", []):
                if not block.get("section_role"):
                    block["section_role"] = section_role

    return artifact


def build_layout_candidate_pipeline_result(
    provider_result,
    candidate_result=None,
    warnings=None,
    layout_artifact=None,
    include_artifact=False,
):
    provider_warning_codes = list((provider_result or {}).get("warning_codes", []))
    candidate_warnings = list((candidate_result or {}).get("warnings", [])) if candidate_result else []
    combined_warnings = []
    for warning in provider_warning_codes + candidate_warnings + list(warnings or []):
        if warning and warning not in combined_warnings:
            combined_warnings.append(warning)

    result = {
        "pipeline_version": LAYOUT_CANDIDATE_PIPELINE_VERSION,
        "provider_name": (provider_result or {}).get("provider_name", ""),
        "provider_status": (provider_result or {}).get("status", ""),
        "provider_page_count": int((provider_result or {}).get("page_count", 0) or 0),
        "provider_warning_codes": provider_warning_codes,
        "candidate_result": candidate_result,
        "candidate_counts_by_field": _candidate_field_counts(candidate_result),
        "warning_codes": combined_warnings,
        "raw_text_saved": False,
        "private_values_redacted": True,
    }
    if include_artifact:
        result["layout_artifact"] = layout_artifact or {}
    return result


def extract_layout_candidates_from_pdf(
    pdf_path,
    provider_name=PROVIDER_PDFPLUMBER,
    classification_result=None,
    document_id=None,
    include_artifact=False,
):
    provider_result = extract_layout_artifact(
        pdf_path,
        provider_name=provider_name,
        document_id=document_id,
    )

    if provider_result.get("status") != STATUS_SUCCESS:
        return build_layout_candidate_pipeline_result(
            provider_result,
            candidate_result=None,
            warnings=["layout_provider_no_candidates"],
            include_artifact=include_artifact,
        )

    layout_artifact = provider_result.get("artifact") or {}
    contextual_artifact = _apply_classification_context(layout_artifact, classification_result)
    candidate_result = extract_ratecon_layout_candidates(
        contextual_artifact,
        classification_result=classification_result,
    )

    return build_layout_candidate_pipeline_result(
        provider_result,
        candidate_result=candidate_result,
        layout_artifact=contextual_artifact,
        include_artifact=include_artifact,
    )
