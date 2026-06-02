"""Vertical-slice RateCon document extraction pipeline.

This module packages existing pieces into an explicit path:
triage -> document artifact -> candidates with provenance -> resolver/gate ->
backward-compatible final output. It does not replace existing broker/template
or private measurement paths.
"""

from app.document_ai.document_extraction_artifact import (
    artifact_summary,
    extract_document_artifact_from_pdf,
)
from app.document_ai.field_candidate_generators import (
    LOAD_CANDIDATE_PROFILE_BASELINE,
    generate_field_candidates,
)
from app.document_ai.field_candidate_resolver import (
    FIELD_BROKER_NAME,
    FIELD_CARRIER_NAME,
    FIELD_DELIVERY_STOPS,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_STOPS,
    FIELD_TOTAL_CARRIER_RATE,
    RANKING_PROFILE_BASELINE,
    resolve_candidates,
)
from app.document_ai.pdf_triage import triage_document
from app.document_ai.section_context import section_context_summary


RATECON_DOCUMENT_PIPELINE_VERSION = "ratecon_document_pipeline_v1"


def _text(value):
    return str(value or "").strip()


def _field_value(resolution_result, field_name):
    return (
        (resolution_result.get("resolved_fields", {}) or {})
        .get(field_name, {})
        .get("value", "")
    )


def _legacy_output_from_resolution(resolution_result, document_id=""):
    pickup_value = _field_value(resolution_result, FIELD_PICKUP_STOPS)
    delivery_value = _field_value(resolution_result, FIELD_DELIVERY_STOPS)
    return {
        "document_id": _text(document_id),
        "broker_name": _field_value(resolution_result, FIELD_BROKER_NAME),
        "carrier_name": _field_value(resolution_result, FIELD_CARRIER_NAME),
        "load_number": _field_value(resolution_result, FIELD_LOAD_NUMBER),
        "rate": _field_value(resolution_result, FIELD_TOTAL_CARRIER_RATE),
        "total_carrier_rate": _field_value(resolution_result, FIELD_TOTAL_CARRIER_RATE),
        "pickup_stops": [pickup_value] if pickup_value else [],
        "delivery_stops": [delivery_value] if delivery_value else [],
        "needs_review": bool(resolution_result.get("needs_review", True)),
        "review_reasons": list(resolution_result.get("review_reasons", [])),
        "field_confidence": {
            field_name: resolution.get("confidence", 0.0)
            for field_name, resolution in (resolution_result.get("resolved_fields", {}) or {}).items()
        },
        "parser_version": RATECON_DOCUMENT_PIPELINE_VERSION,
        "raw_text_included": False,
        "cases_created": False,
        "events_written": False,
    }


def extract_ratecon_document(
    file_path,
    document_id="",
    include_debug=False,
    legacy_context=None,
    include_legacy_final_candidates=True,
    strict_candidate_generators=False,
    shadow_layout_provider="native_text",
    shadow_table_profile="default",
    strict_layout_provider=False,
    shadow_ranking_profile=RANKING_PROFILE_BASELINE,
    shadow_load_candidate_profile=LOAD_CANDIDATE_PROFILE_BASELINE,
    include_private_eval_artifact=False,
):
    triage = triage_document(file_path, document_id=document_id)
    artifact = extract_document_artifact_from_pdf(
        file_path,
        document_id=triage.get("document_id", document_id),
        triage_result=triage,
        layout_provider_name=shadow_layout_provider,
        table_settings_profile=shadow_table_profile,
        strict_layout_provider=strict_layout_provider,
    )
    generation_result = generate_field_candidates(
        artifact,
        triage=triage,
        legacy_context=legacy_context or {},
        include_legacy_final_candidates=include_legacy_final_candidates,
        strict=strict_candidate_generators,
        load_candidate_profile=shadow_load_candidate_profile,
    )
    candidates = generation_result.get("candidates", [])

    resolved = resolve_candidates(
        candidates,
        artifact=artifact,
        triage=triage,
        ranking_profile=shadow_ranking_profile,
    )
    final_output = _legacy_output_from_resolution(
        resolved,
        document_id=triage.get("document_id", document_id),
    )
    result = {
        "final_output": final_output,
        "needs_review": final_output["needs_review"],
        "review_reasons": final_output["review_reasons"],
        "pipeline_version": RATECON_DOCUMENT_PIPELINE_VERSION,
        "raw_text_printed": False,
        "raw_text_saved": False,
    }
    if include_debug:
        result["debug"] = {
            "triage": triage,
            "artifact_summary": artifact_summary(artifact),
            "candidates": candidates,
            "candidate_generation": {
                "generator_summaries": generation_result.get("generator_summaries", []),
                "errors": generation_result.get("errors", []),
                "section_context_summary": section_context_summary(artifact),
            },
            "resolved_fields": resolved.get("resolved_fields", {}),
            "resolver_decision_traces": resolved.get("resolver_decision_traces", {}),
            "review_gate_trace": resolved.get("review_gate_trace", {}),
            "ranking_profile": resolved.get("ranking_profile", shadow_ranking_profile),
            "load_candidate_profile": shadow_load_candidate_profile,
            "needs_review": resolved.get("needs_review", True),
            "review_reasons": resolved.get("review_reasons", []),
            "candidate_warnings": [
                warning
                for summary in generation_result.get("generator_summaries", [])
                for warning in summary.get("warnings", [])
            ],
            "missing_candidate_fields": [],
        }
        if include_private_eval_artifact:
            result["debug"]["private_eval_artifact"] = artifact
    return result
