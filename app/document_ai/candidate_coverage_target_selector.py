"""Safe target selection for candidate coverage hardening.

The selector consumes candidate coverage analysis output and returns counts,
statuses, and target names only. It must not require private values or raw text.
"""

from collections import Counter, defaultdict
import json
from pathlib import Path

from app.document_ai.candidate_coverage_analysis import (
    CANDIDATE_COVERAGE_ANALYSIS_JSON,
    CANDIDATE_COVERAGE_JSON,
    COVERAGE_GAP_CANDIDATE_GENERATED_BUT_NOT_NORMALIZED,
    COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
    COVERAGE_GAP_IDENTIFIER_CANDIDATE_NOT_GENERATED,
    COVERAGE_GAP_IDENTIFIER_LABEL_MISSING,
    COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED,
    COVERAGE_GAP_OCR_NEEDED,
    COVERAGE_GAP_ONLY_NON_PRIMARY_REFERENCE_FOUND,
    COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
    normalize_coverage_gap_reason,
    normalize_coverage_stage,
)
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    _normalize_output_dir,
)
from app.document_ai.target_disposition import (
    is_target_selectable,
    load_target_dispositions,
    skipped_targets_for_registry,
)


TARGET_STOP_SPAN_DATE_CANDIDATE_GENERATION = "stop_span_date_candidate_generation"
TARGET_STOP_SPAN_LOCATION_CANDIDATE_GENERATION = "stop_span_location_candidate_generation"
TARGET_LOAD_IDENTIFIER_CANDIDATE_GENERATION = "load_identifier_candidate_generation"
TARGET_BROKER_IDENTITY_CANDIDATE_GENERATION = "broker_identity_candidate_generation"
TARGET_RATE_CANDIDATE_GENERATION_OR_RESOLUTION = "rate_candidate_generation_or_resolution"
TARGET_NORMALIZED_STOP_FIELD_MAPPING = "normalized_stop_field_mapping"
TARGET_NORMALIZED_TO_CORE_FIELD_MAPPING = "normalized_to_core_field_mapping"
TARGET_HUMAN_REVIEW_REQUIRED = "human_review_required"
TARGET_OCR_DESIGN_LATER = "ocr_design_later"
TARGET_UNKNOWN = "unknown"

CANDIDATE_COVERAGE_TARGET_SELECTION_VERSION = "candidate_coverage_target_selection_v1"
CANDIDATE_COVERAGE_TARGET_SELECTION_JSON = "candidate_coverage_target_selection.json"
CANDIDATE_COVERAGE_TARGET_SELECTION_MD = "candidate_coverage_target_selection.md"

DATE_FIELDS = {"pickup_date", "delivery_date"}
LOCATION_FIELDS = {"pickup_location", "delivery_location"}
LOAD_IDENTIFIER_GAP_REASONS = {
    COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
    COVERAGE_GAP_IDENTIFIER_CANDIDATE_NOT_GENERATED,
    COVERAGE_GAP_IDENTIFIER_LABEL_MISSING,
    COVERAGE_GAP_ONLY_NON_PRIMARY_REFERENCE_FOUND,
}


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _records(analysis):
    return [
        record
        for record in (analysis or {}).get("records", []) or []
        if isinstance(record, dict)
    ]


def _field(record):
    return _token((record or {}).get("field_name"))


def _reason(record):
    return normalize_coverage_gap_reason((record or {}).get("gap_reason"))


def _stage(record):
    return normalize_coverage_stage((record or {}).get("stage"))


def _status(record):
    return _token((record or {}).get("status"))


def _alias(record):
    return _text((record or {}).get("measurement_alias"))


def _count(records, predicate):
    return sum(1 for record in records if predicate(record))


def _aliases(records, predicate):
    return sorted(
        {
            _alias(record)
            for record in records
            if predicate(record) and _alias(record)
        }
    )


def _supporting_counts(records):
    return {
        "date_span_candidate_not_generated": _count(
            records,
            lambda record: _field(record) in DATE_FIELDS
            and _reason(record) == COVERAGE_GAP_CANDIDATE_NOT_GENERATED
            and _stage(record) == COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
        ),
        "location_span_candidate_not_generated": _count(
            records,
            lambda record: _field(record) in LOCATION_FIELDS
            and _reason(record) == COVERAGE_GAP_CANDIDATE_NOT_GENERATED
            and _stage(record) == COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
        ),
        "load_number_candidate_not_generated": _count(
            records,
            lambda record: _field(record) == "load_number"
            and _reason(record) in LOAD_IDENTIFIER_GAP_REASONS,
        ),
        "broker_name_candidate_not_generated": _count(
            records,
            lambda record: _field(record) == "broker_name"
            and _reason(record) == COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
        ),
        "rate_candidate_or_conflict": _count(
            records,
            lambda record: _field(record) == "rate"
            and (
                _reason(record) == COVERAGE_GAP_CANDIDATE_NOT_GENERATED
                or _status(record) == "conflict"
            ),
        ),
        "candidate_generated_but_not_normalized": _count(
            records,
            lambda record: _reason(record)
            == COVERAGE_GAP_CANDIDATE_GENERATED_BUT_NOT_NORMALIZED,
        ),
        "normalized_but_not_core_mapped": _count(
            records,
            lambda record: _reason(record)
            == COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED,
        ),
        "ocr_needed": _count(
            records,
            lambda record: _reason(record) == COVERAGE_GAP_OCR_NEEDED,
        ),
    }


def _gap_reason_counts(records):
    counts = Counter(_reason(record) for record in records)
    return {
        key: count
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    }


def _field_counts(records):
    counts = Counter(_field(record) for record in records if _field(record))
    return {
        key: count
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    }


def _target_scores_from_scores(scores):
    target_scores = {
        TARGET_STOP_SPAN_DATE_CANDIDATE_GENERATION: scores[
            "date_span_candidate_not_generated"
        ],
        TARGET_STOP_SPAN_LOCATION_CANDIDATE_GENERATION: scores[
            "location_span_candidate_not_generated"
        ],
        TARGET_LOAD_IDENTIFIER_CANDIDATE_GENERATION: scores[
            "load_number_candidate_not_generated"
        ],
        TARGET_RATE_CANDIDATE_GENERATION_OR_RESOLUTION: scores[
            "rate_candidate_or_conflict"
        ],
        TARGET_BROKER_IDENTITY_CANDIDATE_GENERATION: scores[
            "broker_name_candidate_not_generated"
        ],
        TARGET_NORMALIZED_STOP_FIELD_MAPPING: scores[
            "candidate_generated_but_not_normalized"
        ],
        TARGET_NORMALIZED_TO_CORE_FIELD_MAPPING: scores[
            "normalized_but_not_core_mapped"
        ],
        TARGET_OCR_DESIGN_LATER: scores["ocr_needed"],
    }
    return target_scores


def _best_target_from_scores(
    scores,
    target_disposition_registry=None,
    allow_deferred_targets=False,
):
    target_scores = _target_scores_from_scores(scores)
    nonzero = {
        target: score
        for target, score in target_scores.items()
        if score > 0
        and is_target_selectable(
            target,
            target_disposition_registry,
            allow_deferred_targets=allow_deferred_targets,
        )
    }
    if not nonzero:
        return TARGET_HUMAN_REVIEW_REQUIRED
    priority = {
        TARGET_NORMALIZED_TO_CORE_FIELD_MAPPING: 0,
        TARGET_NORMALIZED_STOP_FIELD_MAPPING: 1,
        TARGET_STOP_SPAN_DATE_CANDIDATE_GENERATION: 2,
        TARGET_STOP_SPAN_LOCATION_CANDIDATE_GENERATION: 3,
        TARGET_LOAD_IDENTIFIER_CANDIDATE_GENERATION: 4,
        TARGET_RATE_CANDIDATE_GENERATION_OR_RESOLUTION: 5,
        TARGET_BROKER_IDENTITY_CANDIDATE_GENERATION: 6,
        TARGET_OCR_DESIGN_LATER: 9,
    }
    return sorted(
        nonzero.items(),
        key=lambda item: (-item[1], priority.get(item[0], 99), item[0]),
    )[0][0]


def _supporting_fields_for_target(target, records):
    if target == TARGET_STOP_SPAN_DATE_CANDIDATE_GENERATION:
        return sorted(
            {
                _field(record)
                for record in records
                if _field(record) in DATE_FIELDS
                and _reason(record) == COVERAGE_GAP_CANDIDATE_NOT_GENERATED
                and _stage(record) == COVERAGE_STAGE_SPAN_FIELD_CANDIDATE
            }
        )
    if target == TARGET_STOP_SPAN_LOCATION_CANDIDATE_GENERATION:
        return sorted(
            {
                _field(record)
                for record in records
                if _field(record) in LOCATION_FIELDS
                and _reason(record) == COVERAGE_GAP_CANDIDATE_NOT_GENERATED
                and _stage(record) == COVERAGE_STAGE_SPAN_FIELD_CANDIDATE
            }
        )
    if target == TARGET_LOAD_IDENTIFIER_CANDIDATE_GENERATION:
        return ["load_number"]
    if target == TARGET_RATE_CANDIDATE_GENERATION_OR_RESOLUTION:
        return ["rate"]
    if target == TARGET_BROKER_IDENTITY_CANDIDATE_GENERATION:
        return ["broker_name"]
    return []


def _aliases_for_target(target, records):
    if target == TARGET_STOP_SPAN_DATE_CANDIDATE_GENERATION:
        return _aliases(
            records,
            lambda record: _field(record) in DATE_FIELDS
            and _reason(record) == COVERAGE_GAP_CANDIDATE_NOT_GENERATED
            and _stage(record) == COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
        )
    if target == TARGET_STOP_SPAN_LOCATION_CANDIDATE_GENERATION:
        return _aliases(
            records,
            lambda record: _field(record) in LOCATION_FIELDS
            and _reason(record) == COVERAGE_GAP_CANDIDATE_NOT_GENERATED
            and _stage(record) == COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
        )
    fields = set(_supporting_fields_for_target(target, records))
    if fields:
        return _aliases(
            records,
            lambda record: _field(record) in fields
            and (
                _reason(record) == COVERAGE_GAP_CANDIDATE_NOT_GENERATED
                or (
                    _field(record) == "load_number"
                    and _reason(record) in LOAD_IDENTIFIER_GAP_REASONS
                )
            ),
        )
    if target == TARGET_NORMALIZED_STOP_FIELD_MAPPING:
        return _aliases(
            records,
            lambda record: _reason(record)
            == COVERAGE_GAP_CANDIDATE_GENERATED_BUT_NOT_NORMALIZED,
        )
    if target == TARGET_NORMALIZED_TO_CORE_FIELD_MAPPING:
        return _aliases(
            records,
            lambda record: _reason(record)
            == COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED,
        )
    return []


def _reason_lines(target, scores):
    if target == TARGET_STOP_SPAN_DATE_CANDIDATE_GENERATION:
        return [
            "pickup/delivery date gaps are present at span_field_candidate",
            "line/span evidence exists, but date candidates are not emitted",
            "broad datetime work remains out of scope",
        ]
    if target == TARGET_LOAD_IDENTIFIER_CANDIDATE_GENERATION:
        return ["load_number identifier candidate gap is the strongest count"]
    if target == TARGET_STOP_SPAN_LOCATION_CANDIDATE_GENERATION:
        return ["pickup/delivery location gaps reach spans without candidates"]
    if target == TARGET_RATE_CANDIDATE_GENERATION_OR_RESOLUTION:
        return ["rate candidate/conflict records dominate the actionable counts"]
    if target == TARGET_BROKER_IDENTITY_CANDIDATE_GENERATION:
        return ["broker_name candidate_not_generated remains the strongest count"]
    if target == TARGET_NORMALIZED_STOP_FIELD_MAPPING:
        return ["span candidates exist but normalized stop fields are missing"]
    if target == TARGET_NORMALIZED_TO_CORE_FIELD_MAPPING:
        return ["normalized stop fields exist but core field mapping is missing"]
    if target == TARGET_OCR_DESIGN_LATER:
        return ["ocr_needed dominates, but OCR remains deferred"]
    if not any(scores.values()):
        return ["no high-count deterministic target is visible"]
    return ["target selected from coverage scores"]


def select_candidate_coverage_target(
    candidate_coverage_analysis,
    core_gap_analysis=None,
    target_disposition_registry=None,
    allow_deferred_targets=False,
):
    del core_gap_analysis
    records = _records(candidate_coverage_analysis)
    scores = _supporting_counts(records)
    target = _best_target_from_scores(
        scores,
        target_disposition_registry=target_disposition_registry,
        allow_deferred_targets=allow_deferred_targets,
    )
    aliases = _aliases_for_target(target, records)
    fields = _supporting_fields_for_target(target, records)
    skipped_deferred_targets = skipped_targets_for_registry(
        target_disposition_registry or {},
        allow_deferred_targets=allow_deferred_targets,
    )
    confidence = "high" if aliases and fields else "medium" if aliases else "low"
    if target in {TARGET_HUMAN_REVIEW_REQUIRED, TARGET_OCR_DESIGN_LATER}:
        confidence = "medium"
    return {
        "selected_target": target,
        "supporting_fields": fields,
        "supporting_gap_reasons": _gap_reason_counts(records),
        "affected_alias_count": len(aliases),
        "affected_field_count": sum(
            scores.values()
        )
        if target == TARGET_UNKNOWN
        else scores.get(
            {
                TARGET_STOP_SPAN_DATE_CANDIDATE_GENERATION: (
                    "date_span_candidate_not_generated"
                ),
                TARGET_STOP_SPAN_LOCATION_CANDIDATE_GENERATION: (
                    "location_span_candidate_not_generated"
                ),
                TARGET_LOAD_IDENTIFIER_CANDIDATE_GENERATION: (
                    "load_number_candidate_not_generated"
                ),
                TARGET_BROKER_IDENTITY_CANDIDATE_GENERATION: (
                    "broker_name_candidate_not_generated"
                ),
                TARGET_RATE_CANDIDATE_GENERATION_OR_RESOLUTION: (
                    "rate_candidate_or_conflict"
                ),
                TARGET_NORMALIZED_STOP_FIELD_MAPPING: (
                    "candidate_generated_but_not_normalized"
                ),
                TARGET_NORMALIZED_TO_CORE_FIELD_MAPPING: (
                    "normalized_but_not_core_mapped"
                ),
                TARGET_OCR_DESIGN_LATER: "ocr_needed",
            }.get(target, ""),
            0,
        ),
        "evidence_summary_counts": scores,
        "field_counts": _field_counts(records),
        "skipped_deferred_targets": skipped_deferred_targets,
        "next_selectable_target": target,
        "confidence": confidence,
        "reasons": _reason_lines(target, scores),
        "warning_codes": [],
        "non_goals": [
            "no_google_sync",
            "no_ocr_or_vision_implementation",
            "no_dispatch_case",
            "no_production_automation_claim",
        ],
        "analysis_version": CANDIDATE_COVERAGE_TARGET_SELECTION_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
    }


def _read_json(path, default=None):
    file_path = Path(path)
    if not file_path.exists():
        return default
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_candidate_coverage_target_inputs(
    input_dir=DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
):
    root = Path(input_dir)
    coverage = _read_json(root / CANDIDATE_COVERAGE_JSON)
    if not isinstance(coverage, dict):
        coverage = _read_json(root / CANDIDATE_COVERAGE_ANALYSIS_JSON, default={})
    core_gap = _read_json(root / "core_field_gap_analysis.json", default={})
    return {"candidate_coverage_analysis": coverage or {}, "core_gap_analysis": core_gap or {}}


def select_candidate_coverage_target_from_dir(
    input_dir=DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    allow_deferred_targets=False,
):
    inputs = load_candidate_coverage_target_inputs(input_dir)
    registry = load_target_dispositions(input_dir)
    return select_candidate_coverage_target(
        **inputs,
        target_disposition_registry=registry,
        allow_deferred_targets=allow_deferred_targets,
    )


def candidate_coverage_target_markdown_lines(decision):
    lines = [
        "# Candidate Coverage Target Selection",
        "",
        "Local-only target selection. Safe to share: target names, field names, aliases counts, gap reasons, and statuses.",
        "Do not share private values, raw text, filenames, local paths, rates, addresses, references, or broker identifiers.",
        "",
        f"Selected target: {decision.get('selected_target', TARGET_UNKNOWN)}",
        f"Confidence: {decision.get('confidence', 'unknown')}",
        f"Affected aliases: {decision.get('affected_alias_count', 0)}",
        f"Affected field records: {decision.get('affected_field_count', 0)}",
        f"Skipped deferred targets: {', '.join(decision.get('skipped_deferred_targets', []) or [])}",
        f"Next selectable target: {decision.get('next_selectable_target', TARGET_UNKNOWN)}",
        "",
        "## Supporting Fields",
    ]
    for field_name in decision.get("supporting_fields", []) or []:
        lines.append(f"- {field_name}")
    lines.extend(["", "## Evidence Summary Counts"])
    for key, count in (decision.get("evidence_summary_counts", {}) or {}).items():
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## Reasons"])
    for reason in decision.get("reasons", []) or []:
        lines.append(f"- {reason}")
    lines.extend(["", "## Non-Goals"])
    for non_goal in decision.get("non_goals", []) or []:
        lines.append(f"- {non_goal}")
    return lines


def write_candidate_coverage_target_json(decision, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "json": path.name,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def write_candidate_coverage_target_md(decision, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(candidate_coverage_target_markdown_lines(decision)) + "\n", encoding="utf-8")
    return {
        "md": path.name,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def write_candidate_coverage_target_artifacts(
    decision,
    output_dir=None,
    allow_custom_output_dir=False,
):
    output_root = _normalize_output_dir(
        output_dir or DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    json_result = write_candidate_coverage_target_json(
        decision,
        output_root / CANDIDATE_COVERAGE_TARGET_SELECTION_JSON,
    )
    md_result = write_candidate_coverage_target_md(
        decision,
        output_root / CANDIDATE_COVERAGE_TARGET_SELECTION_MD,
    )
    return {
        "json": json_result["json"],
        "md": md_result["md"],
        "private_values_printed": False,
        "raw_text_printed": False,
    }
