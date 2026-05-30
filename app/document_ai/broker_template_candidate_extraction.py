"""Template-aware RateCon candidate extraction orchestration."""

from app.document_ai.broker_template_matcher import (
    TEMPLATE_SELECTION_STATUS_CONFLICT,
    TEMPLATE_SELECTION_STATUS_MATCHED,
    select_broker_template,
)
from app.document_ai.broker_template_scoring import apply_template_candidate_scoring
from app.document_ai.ratecon_candidate_extraction import extract_ratecon_candidates
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_MEDIUM,
    FIELD_BROKER_NAME,
    SOURCE_BROKER_TEMPLATE_FUTURE,
    build_candidate_extraction_result,
    build_field_candidate,
)


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


def _artifact_text(artifact):
    if isinstance(artifact, dict):
        full_text = artifact.get("full_text", "")
        if full_text:
            return str(full_text or "")

        return "\n".join(
            str(page.get("text", "") or "")
            for page in artifact.get("pages", [])
            if isinstance(page, dict)
        )

    return str(getattr(artifact, "full_text", "") or "")


def _has_field_candidate(candidates, field_name):
    return any(candidate.get("field_name") == field_name for candidate in candidates)


def _append_template_identity_candidates(candidates, template, template_selection, artifact):
    if _has_field_candidate(candidates, FIELD_BROKER_NAME):
        return candidates

    display_name = str(template.get("display_name") or "").strip()
    template_id = str(template.get("template_id") or "").strip()
    if not display_name or not template_id:
        return candidates

    if display_name.lower() not in _artifact_text(artifact).lower():
        return candidates

    selected_confidence = float(template_selection.get("selected_confidence", 0.0) or 0.0)
    confidence = (
        CANDIDATE_CONFIDENCE_HIGH
        if selected_confidence >= 0.7
        else CANDIDATE_CONFIDENCE_MEDIUM
    )
    enriched = list(candidates)
    enriched.append(
        build_field_candidate(
            candidate_id=f"template-broker-name-{template_id}",
            field_name=FIELD_BROKER_NAME,
            raw_value=display_name,
            normalized_value=display_name,
            confidence=confidence,
            confidence_reasons=[
                "matched_template_identity_keyword",
                "broker_name_from_template_header",
            ],
            label="template_display_name",
            source=SOURCE_BROKER_TEMPLATE_FUTURE,
            value_type="name",
        )
    )
    return enriched


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
        adjusted_candidates = _append_template_identity_candidates(
            scoring_result["adjusted_candidates"],
            selected_template,
            template_selection,
            artifact,
        )
        adjusted_candidate_result = _safe_adjusted_candidate_result(
            base_candidate_result,
            adjusted_candidates,
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
