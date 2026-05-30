"""Template-aware RateCon candidate extraction orchestration."""

from app.document_ai.broker_template_matcher import (
    TEMPLATE_SELECTION_STATUS_CONFLICT,
    TEMPLATE_SELECTION_STATUS_MATCHED,
    select_broker_template,
)
from app.document_ai.broker_template_scoring import apply_template_candidate_scoring
from app.document_ai.ratecon_candidate_extraction import extract_ratecon_candidates
from app.document_ai.ratecon_candidates import build_candidate_extraction_result


TEMPLATE_AWARE_CANDIDATE_EXTRACTOR_VERSION = "template_aware_candidate_extractor_v1"


def _templates_from_registry(registry_or_templates):
    if hasattr(registry_or_templates, "list_templates"):
        return registry_or_templates.list_templates(active_only=True)

    return list(registry_or_templates or [])


def _template_by_id(templates, template_id):
    for template in templates:
        if template.get("template_id") == template_id:
            return template

    return {}


def _safe_adjusted_candidate_result(base_result, adjusted_candidates, extractor_version):
    return build_candidate_extraction_result(
        document_id=base_result.get("document_id", ""),
        artifact_id=base_result.get("artifact_id", ""),
        candidates=adjusted_candidates,
        missing_candidate_fields=base_result.get("missing_candidate_fields", []),
        warnings=base_result.get("warnings", []),
        extractor_version=extractor_version,
    )


def extract_ratecon_candidates_with_template_context(artifact, registry_or_templates):
    templates = _templates_from_registry(registry_or_templates)
    base_candidate_result = extract_ratecon_candidates(artifact)
    template_selection = select_broker_template(
        artifact,
        templates,
        candidate_result=base_candidate_result,
    )
    warnings = list(template_selection.get("warnings", []))
    scoring_result = {
        "template_id": "",
        "broker_key": "",
        "adjusted_candidates": base_candidate_result.get("candidates", []),
        "adjustments": [],
        "warnings": [],
        "scorer_version": "",
    }
    adjusted_candidate_result = base_candidate_result

    if template_selection["status"] == TEMPLATE_SELECTION_STATUS_MATCHED:
        selected_template = _template_by_id(
            templates,
            template_selection.get("selected_template_id", ""),
        )
        scoring_result = apply_template_candidate_scoring(
            base_candidate_result,
            selected_template,
        )
        adjusted_candidate_result = _safe_adjusted_candidate_result(
            base_candidate_result,
            scoring_result["adjusted_candidates"],
            TEMPLATE_AWARE_CANDIDATE_EXTRACTOR_VERSION,
        )
        warnings.extend(scoring_result.get("warnings", []))
    elif template_selection["status"] == TEMPLATE_SELECTION_STATUS_CONFLICT:
        warnings.append("template_conflict_no_scoring_applied")
    else:
        warnings.append("template_not_matched_generic_candidates_used")

    return {
        "base_candidate_result": base_candidate_result,
        "template_selection_result": template_selection,
        "adjusted_candidate_result": adjusted_candidate_result,
        "scoring_adjustments": scoring_result.get("adjustments", []),
        "warnings": sorted(set(warnings)),
        "extractor_version": TEMPLATE_AWARE_CANDIDATE_EXTRACTOR_VERSION,
    }
