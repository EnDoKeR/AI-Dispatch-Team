"""Safe root-cause analysis for RateCon shadow pipeline diagnostics."""

from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    _normalize_output_dir,
)


ROOT_CAUSE_ANALYSIS_VERSION = "ratecon_shadow_root_cause_analysis_v1"
ROOT_CAUSE_REPORT_MD = "ratecon_shadow_root_cause_report.md"
ROOT_CAUSE_SUMMARY_JSON = "ratecon_shadow_root_cause_summary.json"
FAILURE_CODES_CSV = "ratecon_shadow_failure_codes.csv"
PRIMARY_LAYERS_CSV = "ratecon_shadow_primary_layers.csv"
FIELD_COMPARISONS_CSV = "ratecon_shadow_field_comparisons.csv"
REVIEW_REASONS_CSV = "ratecon_shadow_review_reasons.csv"
TOP_PROBLEM_DOCUMENTS_CSV = "ratecon_shadow_top_problem_documents.csv"

FIELD_LOAD_NUMBER = "load_number"
FIELD_TOTAL_RATE = "total_carrier_rate"
FIELD_PICKUP_STOPS = "pickup_stops"
FIELD_DELIVERY_STOPS = "delivery_stops"
KEY_INDEPENDENT_COUNTS = "independent_candidates_by_field"
KEY_FALLBACK_COUNTS = "legacy_final_fallback_candidates_by_field"
KEY_ALL_COUNTS = "candidates_by_field"
KEY_TAXONOMY = "candidate_taxonomy"
KEY_MAPPING = "canonical_mapping_summary"
COMPARE_FIELDS = (
    FIELD_LOAD_NUMBER,
    FIELD_TOTAL_RATE,
    "broker_name",
    "carrier_name",
    "pickup_count",
    "delivery_count",
)
COVERAGE_FIELDS = (
    FIELD_LOAD_NUMBER,
    FIELD_TOTAL_RATE,
    FIELD_PICKUP_STOPS,
    FIELD_DELIVERY_STOPS,
    "broker_name",
    "carrier_name",
)

TEXT_OR_DOCUMENT_CODES = {
    "DOC_EMPTY_OR_LOW_TEXT",
    "DOC_SCANNED_OR_OCR_REQUIRED",
    "DOC_IMAGE_HEAVY",
    "TEXT_EXTRACTION_FAILED",
    "ARTIFACT_LOW_TEXT",
}
CANDIDATE_CODES = {
    "NO_CANDIDATES",
    "MISSING_LOAD_NUMBER_CANDIDATE",
    "MISSING_TOTAL_RATE_CANDIDATE",
    "MISSING_PICKUP_CANDIDATE",
    "MISSING_DELIVERY_CANDIDATE",
    "LOW_CANDIDATE_COVERAGE",
    "MISSING_STOP_EVIDENCE",
    "PARTIAL_STOP_EVIDENCE_ONLY",
    "STOP_ASSEMBLY_FAILED",
    "AMBIGUOUS_STOP_ASSEMBLY",
    "MISSING_LOAD_LABEL_HIT",
    "LOAD_LABEL_HIT_NO_VALUE",
    "LOAD_LABEL_HIT_VALUE_REJECTED",
    "LOAD_ID_CANDIDATE_WEAK_ONLY",
    "LOAD_LABEL_HIT_VALUE_NOT_NEARBY",
    "LOAD_LABEL_HIT_VALUE_SHAPE_REJECTED",
    "LOAD_LABEL_HIT_COLUMNAR_PAIRING_NEEDED",
    "LOAD_LABEL_HIT_SECTION_AMBIGUOUS",
    "LOAD_ID_ONLY_WEAK_AMBIGUOUS_CANDIDATES",
    "LOAD_ID_FORENSIC_VALUE_ABSENT",
    "STOP_PROXIMITY_MISSING_LINE_INDEX",
    "STOP_PROXIMITY_NO_LOCATION_DATE_PAIR",
    "STOP_PROXIMITY_MULTI_STOP_AMBIGUOUS",
    "STOP_PROXIMITY_SECTION_AMBIGUOUS",
    "STOP_PROXIMITY_CLUSTER_PARTIAL_ONLY",
    "LINE_SEGMENTATION_INSUFFICIENT",
    "COLUMNAR_LAYOUT_REQUIRES_COORDINATES",
    "TABLE_LAYOUT_REQUIRES_COORDINATES",
    "LAYOUT_PROVIDER_UNAVAILABLE",
    "LAYOUT_PROVIDER_FAILED",
    "LAYOUT_PROVIDER_PARTIAL",
    "LAYOUT_WORDS_UNAVAILABLE",
    "LAYOUT_LINES_UNAVAILABLE",
    "LAYOUT_TABLES_UNAVAILABLE",
    "TABLE_EXTRACTION_EMPTY",
    "TABLE_EXTRACTION_FAILED",
    "TABLE_HEADERS_UNRECOGNIZED",
    "TABLE_HEADER_ROW_NOT_FOUND",
    "TABLE_KEY_VALUE_PATTERN_NOT_FOUND",
    "TABLE_LOAD_LABEL_FOUND_VALUE_MISSING",
    "TABLE_LOAD_VALUE_SHAPE_REJECTED",
    "TABLE_STOP_COLUMNS_NOT_FOUND",
    "TABLE_RATE_COLUMNS_NOT_FOUND",
    "TABLE_STOP_ROLE_COLUMN_NOT_FOUND",
    "TABLE_STOP_LOCATION_COLUMN_NOT_FOUND",
    "TABLE_STOP_DATE_TIME_COLUMN_NOT_FOUND",
    "TABLE_STOP_ROW_AMBIGUOUS",
    "TABLE_STOP_ROW_PARTIAL_ONLY",
    "LAYOUT_LOAD_LABEL_NO_RIGHT_VALUE",
    "LAYOUT_LOAD_LABEL_NO_NEARBY_VALUE",
    "LAYOUT_LOAD_TABLE_PAIRING_FAILED",
    "LAYOUT_LOAD_VALUE_SHAPE_REJECTED",
    "LAYOUT_LOAD_COORDINATES_MISSING",
    "LAYOUT_STOP_TABLE_NOT_FOUND",
    "LAYOUT_STOP_ROW_PAIRING_FAILED",
    "LAYOUT_STOP_ROLE_AMBIGUOUS",
    "LAYOUT_STOP_DATE_LOCATION_NOT_PAIRED",
    "LAYOUT_STOP_COORDINATES_MISSING",
    "ONLY_WEAK_LOAD_ID_CANDIDATES",
    "ONLY_AMBIGUOUS_STOP_CANDIDATES",
    "LAYOUT_CANDIDATES_DUPLICATIVE",
    "LAYOUT_CANDIDATES_NOISY",
    "TABLE_PROFILE_NO_USEFUL_TABLES",
    "TABLE_PROFILE_EXTRACTION_FRAGMENTED",
    "TABLE_PROFILE_CELLS_EMPTY",
    "RESOLVER_ALL_CANDIDATES_WEAK",
    "RESOLVER_ALL_CANDIDATES_AMBIGUOUS",
    "LOAD_ONLY_WEAK_AMBIGUOUS_CANDIDATES",
    "LOAD_MISSING_LAYOUT_LABEL_VALUE",
    "STOP_CANDIDATES_PARTIAL_ONLY",
    "STOP_CANDIDATES_AMBIGUOUS_ONLY",
    "STOP_NO_COMPLETE_CANDIDATE",
    "STOP_STRUCTURED_ONLY_NOISY_PARTIALS",
}
RESOLVER_CODES = {
    "RESOLVER_INPUT_HAS_HIGH_QUALITY_CANDIDATE",
    "RESOLVER_IGNORED_HIGH_QUALITY_CANDIDATE",
    "RESOLVER_CANDIDATE_INELIGIBLE",
    "RESOLVER_UNSUPPORTED_STRUCTURED_VALUE",
    "RESOLVER_FIELD_NOT_SUPPORTED",
    "RESOLVER_SELECTED_LEGACY_FALLBACK_OVER_LAYOUT",
    "LOAD_HIGH_QUALITY_CANDIDATE_NOT_SELECTED",
    "LOAD_NO_ELIGIBLE_CANDIDATES",
    "STOP_STRUCTURED_CANDIDATE_NOT_SELECTED",
    "STOP_STRUCTURED_VALUE_UNSUPPORTED",
    "STOP_STRUCTURED_UNSUPPORTED_VALUE",
    "STOP_STRUCTURED_EMPTY_AFTER_NORMALIZATION",
    "STOP_STRUCTURED_TRUE_CONFLICT",
    "STOP_TABLE_ROW_CANDIDATE_NOT_SELECTED",
    "STOP_CONFLICT_TRUE_DATE",
    "STOP_CONFLICT_TRUE_TIME",
    "STOP_CONFLICT_TRUE_LOCATION",
    "STOP_CONFLICT_TRUE_ROLE",
    "CONFLICTING_LOAD_NUMBER_CANDIDATES",
    "CONFLICTING_TOTAL_RATE_CANDIDATES",
    "LOW_CONFIDENCE_LOAD_NUMBER",
    "LOW_CONFIDENCE_TOTAL_RATE",
    "LOW_CONFIDENCE_STOPS",
    "RESOLVER_NO_DECISION",
}
VALIDATION_CODES = {
    "STOP_STRUCTURED_SELECTED_COMPLETE",
    "STOP_STRUCTURED_SELECTED_PARTIAL_REVIEW",
    "STOP_STRUCTURED_SELECTED_BUT_LOW_CONFIDENCE",
    "STOP_STRUCTURED_DUPLICATES_COLLAPSED",
    "STOP_STRUCTURED_PARTIAL_OVERLAP",
    "STOP_STRUCTURED_REVIEW_GATE_PARTIAL",
    "STOP_CONFLICT_DUPLICATE_ONLY",
    "REVIEW_GATE_STOP_PRESENT_PARTIAL",
    "REVIEW_GATE_STOP_PRESENT_CONFLICT",
    "REVIEW_GATE_STOP_PRESENT_UNSUPPORTED",
    "REVIEW_GATE_RATE_TRACE_MISMATCH",
}


def _text(value):
    return str(value or "").strip()


def _safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]
    return [_text(item) for item in items if _text(item)]


def _percent(count, total):
    total = _safe_int(total)
    if total <= 0:
        return 0.0
    return round((_safe_int(count) / total) * 100, 1)


def _counter_dict(counter):
    return {
        key: count
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    }


def load_shadow_summary(path):
    if not path:
        return {}
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {}


def load_shadow_audit_jsonl(path):
    if not path:
        return []
    records = []
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {line_number}") from exc
        if isinstance(record, dict):
            records.append(record)
    return records


def _record_review_reasons(record):
    shadow = (record or {}).get("shadow", {}) or {}
    return _safe_list(shadow.get("review_reasons"))


def _record_failure(record):
    return (record or {}).get("failure_attribution", {}) or {}


def _record_codes(record):
    return _safe_list(_record_failure(record).get("codes"))


def _record_primary_layer(record):
    return _text(_record_failure(record).get("primary_suspected_layer")) or "unknown"


def _record_candidates_by_field(record):
    summary = (record or {}).get("candidate_summary", {}) or {}
    counts = summary.get("candidates_by_field", {}) or {}
    return counts if isinstance(counts, dict) else {}


def _record_candidate_counts(record, key):
    summary = (record or {}).get("candidate_summary", {}) or {}
    counts = summary.get(key, {}) or {}
    return counts if isinstance(counts, dict) else {}


def _record_compare(record):
    comparison = (record or {}).get("legacy_shadow_comparison", {}) or {}
    return comparison if isinstance(comparison, dict) else {}


def _shadow_success(record):
    return bool(((record or {}).get("shadow", {}) or {}).get("success", False))


def _shadow_needs_review(record):
    return bool(((record or {}).get("shadow", {}) or {}).get("needs_review", False))


def _diagnostic_score(record):
    codes = set(_record_codes(record))
    comparison = _record_compare(record)
    score = 0
    if not _shadow_success(record):
        score += 100
    if "MISSING_LOAD_NUMBER_CANDIDATE" in codes:
        score += 40
    if "MISSING_TOTAL_RATE_CANDIDATE" in codes:
        score += 40
    if any(status == "different" for status in comparison.values()):
        score += 30
    if "CONFLICTING_LOAD_NUMBER_CANDIDATES" in codes:
        score += 25
    if "CONFLICTING_TOTAL_RATE_CANDIDATES" in codes:
        score += 25
    if codes & TEXT_OR_DOCUMENT_CODES:
        score += 15
    if _shadow_needs_review(record):
        score += 10
    return score


def _top_problem_document(record):
    triage = (record or {}).get("triage", {}) or {}
    candidate_counts = _record_candidates_by_field(record)
    return {
        "document_id": _text((record or {}).get("document_id")),
        "file_name": _text((record or {}).get("file_name")),
        "file_hash": _text((record or {}).get("file_hash")),
        "pdf_type": _text(triage.get("pdf_type")) or "unknown",
        "page_count": _safe_int(triage.get("page_count")),
        "quality_flags": _safe_list(triage.get("quality_flags")),
        "primary_suspected_layer": _record_primary_layer(record),
        "failure_codes": _record_codes(record),
        "needs_review": _shadow_needs_review(record),
        "review_reasons": _record_review_reasons(record),
        "candidate_counts": {
            FIELD_LOAD_NUMBER: _safe_int(candidate_counts.get(FIELD_LOAD_NUMBER)),
            FIELD_TOTAL_RATE: _safe_int(candidate_counts.get(FIELD_TOTAL_RATE)),
        },
        "legacy_shadow_comparisons": {
            FIELD_LOAD_NUMBER: _record_compare(record).get(FIELD_LOAD_NUMBER, ""),
            FIELD_TOTAL_RATE: _record_compare(record).get(FIELD_TOTAL_RATE, ""),
        },
        "diagnostic_score": _diagnostic_score(record),
    }


def _field_comparison_counts(records):
    counts = {field_name: Counter() for field_name in COMPARE_FIELDS}
    for record in records or []:
        comparison = _record_compare(record)
        for field_name in COMPARE_FIELDS:
            status = _text(comparison.get(field_name)) or "missing_comparison"
            counts[field_name][status] += 1
    return {field_name: _counter_dict(counter) for field_name, counter in counts.items()}


def _candidate_coverage(records, key=KEY_ALL_COUNTS):
    coverage = {
        field_name: {"candidate_present_count": 0, "candidate_missing_count": 0}
        for field_name in COVERAGE_FIELDS
    }
    for record in records or []:
        counts = _record_candidate_counts(record, key)
        for field_name in coverage:
            if _safe_int(counts.get(field_name)) > 0:
                coverage[field_name]["candidate_present_count"] += 1
            else:
                coverage[field_name]["candidate_missing_count"] += 1
    return coverage


def _generator_candidate_counts(records):
    counts = Counter()
    for record in records or []:
        summary = (record or {}).get("candidate_summary", {}) or {}
        counts.update(summary.get("candidates_by_generator", {}) or {})
    return _counter_dict(counts)


def _aggregate_canonical_mapping(records):
    mapped_by_strength = Counter()
    unmapped_raw = Counter()
    critical_by_strength = defaultdict(Counter)
    independent_critical_by_strength = defaultdict(Counter)
    fallback_critical_by_strength = defaultdict(Counter)
    raw_fields_by_generator = defaultdict(Counter)
    canonical_fields_by_generator = defaultdict(Counter)
    line_diagnostics = Counter()
    for record in records or []:
        summary = (record or {}).get("candidate_summary", {}) or {}
        mapping = summary.get(KEY_MAPPING, {}) or {}
        mapped_by_strength.update(mapping.get("mapped_by_strength", {}) or {})
        unmapped_raw.update(mapping.get("unmapped_raw_fields_top", {}) or {})
        for field_name, strengths in (
            mapping.get("critical_field_candidates_by_mapping_strength", {}) or {}
        ).items():
            critical_by_strength[field_name].update(strengths or {})
        for field_name, strengths in (
            mapping.get(
                "independent_critical_field_candidates_by_mapping_strength",
                {},
            )
            or {}
        ).items():
            independent_critical_by_strength[field_name].update(strengths or {})
        for field_name, strengths in (
            mapping.get(
                "legacy_final_critical_field_candidates_by_mapping_strength",
                {},
            )
            or {}
        ).items():
            fallback_critical_by_strength[field_name].update(strengths or {})
        taxonomy = summary.get(KEY_TAXONOMY, {}) or {}
        for generator_name, counts in (taxonomy.get("raw_fields_by_generator", {}) or {}).items():
            raw_fields_by_generator[generator_name].update(counts or {})
        for generator_name, counts in (
            taxonomy.get("canonical_fields_by_generator", {}) or {}
        ).items():
            canonical_fields_by_generator[generator_name].update(counts or {})
        for generator_summary in taxonomy.get("generator_summaries", []) or []:
            if (
                (generator_summary or {}).get("generator_name")
                == "load_identifier_line_candidate_generator"
            ):
                diagnostics = (generator_summary or {}).get("diagnostics", {}) or {}
                for key in [
                    "lines_scanned_count",
                    "label_hits_count",
                    "candidates_emitted_count",
                ]:
                    line_diagnostics[key] += _safe_int(diagnostics.get(key))
                for reason, count in (
                    diagnostics.get("skipped_reason_counts", {}) or {}
                ).items():
                    line_diagnostics[f"skipped:{reason}"] += _safe_int(count)
                for method, count in (diagnostics.get("emitted_by_method", {}) or {}).items():
                    line_diagnostics[f"emitted:{method}"] += _safe_int(count)
    return {
        "mapped_candidate_count": sum(
            count
            for strength, count in mapped_by_strength.items()
            if strength != "unmapped"
        ),
        "unmapped_candidate_count": mapped_by_strength.get("unmapped", 0),
        "mapped_by_strength": _counter_dict(mapped_by_strength),
        "unmapped_raw_fields_top": dict(unmapped_raw.most_common(25)),
        "critical_field_candidates_by_mapping_strength": {
            field_name: _counter_dict(counter)
            for field_name, counter in sorted(critical_by_strength.items())
        },
        "independent_critical_field_candidates_by_mapping_strength": {
            field_name: _counter_dict(counter)
            for field_name, counter in sorted(independent_critical_by_strength.items())
        },
        "legacy_final_critical_field_candidates_by_mapping_strength": {
            field_name: _counter_dict(counter)
            for field_name, counter in sorted(fallback_critical_by_strength.items())
        },
        "raw_fields_by_generator": {
            generator_name: dict(counter.most_common(25))
            for generator_name, counter in sorted(raw_fields_by_generator.items())
        },
        "canonical_fields_by_generator": {
            generator_name: dict(counter.most_common(25))
            for generator_name, counter in sorted(canonical_fields_by_generator.items())
        },
        "load_identifier_line_generator_diagnostics": dict(sorted(line_diagnostics.items())),
    }


def _aggregate_stop_assembly(records):
    by_role = Counter()
    by_type = Counter()
    counts = Counter()
    for record in records or []:
        summary = (record or {}).get("candidate_summary", {}) or {}
        stop_summary = summary.get("stop_assembly_summary", {}) or {}
        for key in [
            "stop_evidence_count",
            "assembled_pickup_stop_candidate_count",
            "assembled_delivery_stop_candidate_count",
            "docs_with_assembled_pickup_stops",
            "docs_with_assembled_delivery_stops",
            "partial_stop_candidate_count",
            "ambiguous_stop_candidate_count",
        ]:
            counts[key] += _safe_int(stop_summary.get(key))
        by_role.update(stop_summary.get("stop_evidence_by_role", {}) or {})
        by_type.update(stop_summary.get("stop_evidence_by_type", {}) or {})
    return {
        "stop_evidence_count": counts.get("stop_evidence_count", 0),
        "stop_evidence_by_role": _counter_dict(by_role),
        "stop_evidence_by_type": _counter_dict(by_type),
        "assembled_pickup_stop_candidate_count": counts.get(
            "assembled_pickup_stop_candidate_count",
            0,
        ),
        "assembled_delivery_stop_candidate_count": counts.get(
            "assembled_delivery_stop_candidate_count",
            0,
        ),
        "docs_with_assembled_pickup_stops": counts.get(
            "docs_with_assembled_pickup_stops",
            0,
        ),
        "docs_with_assembled_delivery_stops": counts.get(
            "docs_with_assembled_delivery_stops",
            0,
        ),
        "partial_stop_candidate_count": counts.get("partial_stop_candidate_count", 0),
        "ambiguous_stop_candidate_count": counts.get(
            "ambiguous_stop_candidate_count",
            0,
        ),
    }


def _aggregate_load_identity_line_summary(records):
    skipped = Counter()
    emitted = Counter()
    counts = Counter()
    for record in records or []:
        summary = (record or {}).get("candidate_summary", {}) or {}
        load_summary = summary.get("load_identity_line_summary", {}) or {}
        for key in ["lines_scanned", "label_hits", "emitted_candidates"]:
            counts[key] += _safe_int(load_summary.get(key))
        skipped.update(load_summary.get("skipped_by_reason", {}) or {})
        emitted.update(load_summary.get("emitted_by_method", {}) or {})
    return {
        "lines_scanned": counts.get("lines_scanned", 0),
        "label_hits": counts.get("label_hits", 0),
        "emitted_candidates": counts.get("emitted_candidates", 0),
        "skipped_by_reason": _counter_dict(skipped),
        "emitted_by_method": _counter_dict(emitted),
    }


def _aggregate_load_identity_forensics(records):
    counts = Counter()
    hit_types = Counter()
    rejections = Counter()
    attempts = Counter()
    successes = Counter()
    shapes = Counter()
    for record in records or []:
        summary = (record or {}).get("candidate_summary", {}) or {}
        forensics = summary.get("load_identity_forensics", {}) or {}
        for key in [
            "label_hits",
            "emitted_candidates",
            "docs_with_label_hits",
            "docs_with_emitted_load_candidates",
        ]:
            counts[key] += _safe_int(forensics.get(key))
        hit_types.update(forensics.get("hit_type_counts", {}) or {})
        rejections.update(forensics.get("rejection_reason_counts", {}) or {})
        attempts.update(forensics.get("method_attempt_counts", {}) or {})
        successes.update(forensics.get("method_success_counts", {}) or {})
        shapes.update(forensics.get("value_shape_counts", {}) or {})
    return {
        "label_hits": counts.get("label_hits", 0),
        "emitted_candidates": counts.get("emitted_candidates", 0),
        "hit_type_counts": _counter_dict(hit_types),
        "rejection_reason_counts": _counter_dict(rejections),
        "method_attempt_counts": _counter_dict(attempts),
        "method_success_counts": _counter_dict(successes),
        "value_shape_counts": _counter_dict(shapes),
        "docs_with_label_hits": counts.get("docs_with_label_hits", 0),
        "docs_with_emitted_load_candidates": counts.get(
            "docs_with_emitted_load_candidates",
            0,
        ),
    }


def _aggregate_stop_proximity(records):
    counts = Counter()
    reasons = Counter()
    for record in records or []:
        summary = (record or {}).get("candidate_summary", {}) or {}
        proximity = summary.get("stop_proximity_summary", {}) or {}
        for key in [
            "docs_with_proximity_clusters",
            "proximity_cluster_count",
            "ambiguous_cluster_count",
            "clusters_with_location_and_date",
            "clusters_with_location_only",
            "clusters_with_date_only",
        ]:
            counts[key] += _safe_int(proximity.get(key))
        reasons.update(proximity.get("ambiguity_reason_counts", {}) or {})
    return {
        "docs_with_proximity_clusters": counts.get("docs_with_proximity_clusters", 0),
        "proximity_cluster_count": counts.get("proximity_cluster_count", 0),
        "ambiguous_cluster_count": counts.get("ambiguous_cluster_count", 0),
        "clusters_with_location_and_date": counts.get(
            "clusters_with_location_and_date",
            0,
        ),
        "clusters_with_location_only": counts.get("clusters_with_location_only", 0),
        "clusters_with_date_only": counts.get("clusters_with_date_only", 0),
        "ambiguity_reason_counts": _counter_dict(reasons),
    }


def _aggregate_section_context(records):
    counts = Counter()
    sections = Counter()
    for record in records or []:
        summary = (record or {}).get("candidate_summary", {}) or {}
        section_summary = summary.get("section_context_summary", {}) or {}
        counts["lines_with_section_context"] += _safe_int(
            section_summary.get("lines_with_section_context")
        )
        counts["unknown_section_lines"] += _safe_int(
            section_summary.get("unknown_section_lines")
        )
        sections.update(section_summary.get("section_counts", {}) or {})
    return {
        "lines_with_section_context": counts.get("lines_with_section_context", 0),
        "section_counts": _counter_dict(sections),
        "unknown_section_lines": counts.get("unknown_section_lines", 0),
    }


def _aggregate_layout_provider(records):
    status_counts = Counter()
    totals = Counter()
    warnings = Counter()
    errors = Counter()
    for record in records or []:
        artifact = (record or {}).get("artifact_summary", {}) or {}
        summary = artifact.get("layout_provider_summary", {}) or {}
        if not summary:
            continue
        status_counts[
            f"requested:{_text(summary.get('provider_requested')) or 'unknown'}"
        ] += 1
        status_counts[f"used:{_text(summary.get('provider_used')) or 'unknown'}"] += 1
        status_counts[f"status:{_text(summary.get('status')) or 'unknown'}"] += 1
        for key in [
            "pages_with_words",
            "pages_with_lines",
            "pages_with_tables",
            "word_count",
            "line_count",
            "table_count",
            "table_cell_count",
        ]:
            totals[key] += _safe_int(summary.get(key))
        warnings.update(_safe_list(summary.get("warnings")))
        errors.update(_safe_list(summary.get("errors")))
    return {
        "provider_status_counts": _counter_dict(status_counts),
        "pages_with_words": totals.get("pages_with_words", 0),
        "pages_with_lines": totals.get("pages_with_lines", 0),
        "pages_with_tables": totals.get("pages_with_tables", 0),
        "word_count": totals.get("word_count", 0),
        "line_count": totals.get("line_count", 0),
        "table_count": totals.get("table_count", 0),
        "table_cell_count": totals.get("table_cell_count", 0),
        "warnings": _counter_dict(warnings),
        "errors": _counter_dict(errors),
    }


def _aggregate_layout_pairing(records):
    table_totals = Counter()
    table_header_roles = Counter()
    table_row_roles = Counter()
    load_totals = Counter()
    load_rejections = Counter()
    load_methods = Counter()
    stop_totals = Counter()
    stop_rejections = Counter()
    stop_methods = Counter()
    quality_totals = Counter()
    quality_high = Counter()
    quality_weak = Counter()
    quality_legacy = Counter()
    for record in records or []:
        summary = ((record or {}).get("candidate_summary", {}) or {})
        table_summary = summary.get("table_extraction_summary", {}) or {}
        for key, value in table_summary.items():
            if isinstance(value, dict):
                continue
            table_totals[key] += _safe_int(value)
        table_header_roles.update(table_summary.get("table_header_role_counts", {}) or {})
        table_row_roles.update(table_summary.get("table_row_role_counts", {}) or {})
        load_summary = summary.get("layout_load_pairing_summary", {}) or {}
        for key in [
            "layout_label_hits",
            "same_row_pairings",
            "nearby_row_pairings",
            "table_cell_pairings",
            "header_block_pairings",
            "layout_candidates_emitted",
            "table_load_label_hits",
            "docs_with_table_load_candidates",
        ]:
            load_totals[key] += _safe_int(load_summary.get(key))
        load_rejections.update(
            load_summary.get("layout_rejection_reason_counts", {}) or {}
        )
        load_methods.update(load_summary.get("table_pairings_by_method", {}) or {})
        stop_summary = summary.get("layout_stop_pairing_summary", {}) or {}
        for key in [
            "layout_stop_evidence_count",
            "layout_structured_stop_candidates",
            "table_row_stop_candidates",
            "bbox_cluster_stop_candidates",
            "table_stop_candidates_complete",
            "table_stop_candidates_partial",
            "table_stop_candidates_ambiguous",
        ]:
            stop_totals[key] += _safe_int(stop_summary.get(key))
        stop_rejections.update(
            stop_summary.get("layout_ambiguity_reason_counts", {}) or {}
        )
        stop_methods.update(stop_summary.get("table_pairings_by_method", {}) or {})
        quality = summary.get("candidate_quality_summary", {}) or {}
        quality_totals["duplicate_candidates_removed"] += _safe_int(
            quality.get("duplicate_candidates_removed")
        )
        quality_high.update(
            quality.get("critical_fields_with_high_quality_independent_candidates", {}) or {}
        )
        quality_weak.update(quality.get("critical_fields_with_only_weak_candidates", {}) or {})
        quality_legacy.update(quality.get("critical_fields_with_only_legacy_fallback", {}) or {})
    return {
        "table_extraction_summary": {
            **_counter_dict(table_totals),
            "table_header_role_counts": _counter_dict(table_header_roles),
            "table_row_role_counts": _counter_dict(table_row_roles),
        },
        "table_profile_summary": {
            **_counter_dict(table_totals),
            "table_header_role_counts": _counter_dict(table_header_roles),
            "table_row_role_counts": _counter_dict(table_row_roles),
        },
        "layout_load_pairing_summary": {
            **_counter_dict(load_totals),
            "layout_rejection_reason_counts": _counter_dict(load_rejections),
            "table_pairings_by_method": _counter_dict(load_methods),
        },
        "layout_stop_pairing_summary": {
            **_counter_dict(stop_totals),
            "layout_ambiguity_reason_counts": _counter_dict(stop_rejections),
            "table_pairings_by_method": _counter_dict(stop_methods),
        },
        "candidate_quality_summary": {
            **_counter_dict(quality_totals),
            "critical_fields_with_high_quality_independent_candidates": _counter_dict(quality_high),
            "critical_fields_with_only_weak_candidates": _counter_dict(quality_weak),
            "critical_fields_with_only_legacy_fallback": _counter_dict(quality_legacy),
        },
    }


def _aggregate_layout_effectiveness(records):
    load_totals = Counter()
    load_methods = Counter()
    load_hints = Counter()
    load_bands = Counter()
    load_not_selected = Counter()
    stop_totals = Counter()
    stop_methods = Counter()
    stop_ambiguity = Counter()
    for record in records or []:
        summary = ((record or {}).get("candidate_summary", {}) or {})
        effectiveness = summary.get("layout_candidate_effectiveness", {}) or {}
        load = effectiveness.get("layout_load_candidates", {}) or {}
        for key in [
            "emitted",
            "accepted_by_resolver",
            "rejected_or_not_selected",
        ]:
            load_totals[key] += _safe_int(load.get(key))
        load_methods.update(load.get("by_pairing_method", {}) or {})
        load_hints.update(load.get("by_id_type_hint", {}) or {})
        load_bands.update(load.get("by_confidence_band", {}) or {})
        load_not_selected.update(load.get("not_selected_reasons", {}) or {})
        stop = effectiveness.get("layout_stop_candidates", {}) or {}
        for key in [
            "emitted",
            "structured",
            "partial",
            "with_location",
            "with_date",
            "with_time",
            "accepted_by_resolver",
            "rejected_or_not_selected",
        ]:
            stop_totals[key] += _safe_int(stop.get(key))
        stop_methods.update(stop.get("by_pairing_method", {}) or {})
        stop_ambiguity.update(stop.get("ambiguity_reasons", {}) or {})
    return {
        "layout_load_candidates": {
            **_counter_dict(load_totals),
            "by_pairing_method": _counter_dict(load_methods),
            "by_id_type_hint": _counter_dict(load_hints),
            "by_confidence_band": _counter_dict(load_bands),
            "not_selected_reasons": _counter_dict(load_not_selected),
        },
        "layout_stop_candidates": {
            **_counter_dict(stop_totals),
            "by_pairing_method": _counter_dict(stop_methods),
            "ambiguity_reasons": _counter_dict(stop_ambiguity),
        },
    }


def _aggregate_resolver_selection(records):
    field_totals = defaultdict(Counter)
    not_selected = defaultdict(Counter)
    load_totals = Counter()
    load_not_selected = Counter()
    load_sources = Counter()
    load_pairing_methods = Counter()
    stop_totals = {"pickup": Counter(), "delivery": Counter()}
    stop_not_selected = {"pickup": Counter(), "delivery": Counter()}
    structured_stop_totals = {"pickup": Counter(), "delivery": Counter()}
    structured_conflict_totals = defaultdict(Counter)
    structured_conflict_types = defaultdict(Counter)
    rate_sanity_totals = Counter()
    rate_mismatch_reasons = Counter()
    review_status = Counter()
    review_sources = Counter()
    for record in records or []:
        summary = ((record or {}).get("candidate_summary", {}) or {})
        resolver_summary = summary.get("resolver_selection_summary", {}) or {}
        for field_name, details in (resolver_summary.get("fields", {}) or {}).items():
            for key, value in (details or {}).items():
                if isinstance(value, dict):
                    continue
                if key == "selected" and value:
                    field_totals[field_name]["selected_count"] += 1
                    continue
                if key == "decision_status" and _text(value):
                    field_totals[field_name][f"decision:{_text(value)}"] += 1
                    continue
                if key == "selected_quality_band" and _text(value):
                    field_totals[field_name][f"selected_quality:{_text(value)}"] += 1
                    continue
                if key == "selected_source" and _text(value):
                    field_totals[field_name][f"selected_source:{_text(value)}"] += 1
                    continue
                if isinstance(value, bool):
                    continue
                field_totals[field_name][key] += _safe_int(value)
            not_selected[field_name].update(
                details.get("not_selected_reason_counts", {}) or {}
            )
        load = summary.get("load_number_selection_summary", {}) or {}
        for key, value in (load or {}).items():
            if isinstance(value, dict):
                continue
            load_totals[key] += _safe_int(value)
        load_not_selected.update(load.get("not_selected_reason_counts", {}) or {})
        load_sources.update(load.get("selected_source_counts", {}) or {})
        load_pairing_methods.update(load.get("selected_pairing_method_counts", {}) or {})
        stop = summary.get("stop_selection_summary", {}) or {}
        for role in ["pickup", "delivery"]:
            role_summary = stop.get(role, {}) or {}
            for key, value in role_summary.items():
                if isinstance(value, dict):
                    continue
                stop_totals[role][key] += _safe_int(value)
            stop_not_selected[role].update(
                role_summary.get("not_selected_reason_counts", {}) or {}
            )
        structured_resolution = summary.get("structured_stop_resolution_summary", {}) or {}
        for role in ["pickup", "delivery"]:
            role_summary = structured_resolution.get(role, {}) or {}
            for key, value in role_summary.items():
                structured_stop_totals[role][key] += _safe_int(value)
        structured_conflict = summary.get("structured_stop_conflict_summary", {}) or {}
        for field_name in [FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS]:
            field_summary = structured_conflict.get(field_name, {}) or {}
            for key, value in field_summary.items():
                if isinstance(value, dict):
                    continue
                if key in {"selected_status", "selected_source", "selected_pairing_method"}:
                    continue
                structured_conflict_totals[field_name][key] += _safe_int(value)
            structured_conflict_types[field_name].update(
                field_summary.get("conflict_type_counts", {}) or {}
            )
        rate_sanity = summary.get("rate_review_sanity_summary", {}) or {}
        for key, value in rate_sanity.items():
            if isinstance(value, dict):
                continue
            rate_sanity_totals[key] += _safe_int(value)
        rate_mismatch_reasons.update(rate_sanity.get("mismatch_reasons", {}) or {})
        gate = summary.get("review_gate_trace_summary", {}) or {}
        review_status.update(gate.get("critical_field_status_counts", {}) or {})
        review_sources.update(gate.get("review_reason_source_counts", {}) or {})
    return {
        "resolver_selection_summary": {
            "fields": {
                field_name: {
                    **_counter_dict(counter),
                    "not_selected_reason_counts": _counter_dict(
                        not_selected[field_name]
                    ),
                }
                for field_name, counter in sorted(field_totals.items())
            },
        },
        "load_number_selection_summary": {
            **_counter_dict(load_totals),
            "not_selected_reason_counts": _counter_dict(load_not_selected),
            "selected_source_counts": _counter_dict(load_sources),
            "selected_pairing_method_counts": _counter_dict(load_pairing_methods),
        },
        "stop_selection_summary": {
            role: {
                **_counter_dict(counter),
                "not_selected_reason_counts": _counter_dict(stop_not_selected[role]),
            }
            for role, counter in sorted(stop_totals.items())
        },
        "structured_stop_resolution_summary": {
            role: _counter_dict(counter)
            for role, counter in sorted(structured_stop_totals.items())
        },
        "structured_stop_conflict_summary": {
            field_name: {
                **_counter_dict(counter),
                "conflict_type_counts": _counter_dict(
                    structured_conflict_types[field_name]
                ),
            }
            for field_name, counter in sorted(structured_conflict_totals.items())
        },
        "rate_review_sanity_summary": {
            **_counter_dict(rate_sanity_totals),
            "mismatch_reasons": _counter_dict(rate_mismatch_reasons),
        },
        "review_gate_trace_summary": {
            "needs_review_count": sum(1 for record in records or [] if _shadow_needs_review(record)),
            "critical_field_status_counts": _counter_dict(review_status),
            "review_reason_source_counts": _counter_dict(review_sources),
        },
    }


def _stop_candidate_coverage(records):
    structured = {FIELD_PICKUP_STOPS: 0, FIELD_DELIVERY_STOPS: 0}
    partial = {FIELD_PICKUP_STOPS: 0, FIELD_DELIVERY_STOPS: 0}
    for record in records or []:
        summary = (record or {}).get("candidate_summary", {}) or {}
        taxonomy = summary.get(KEY_TAXONOMY, {}) or {}
        structured_counts = taxonomy.get("structured_stop_candidates_by_field", {}) or {}
        partial_counts = taxonomy.get("partial_stop_candidates_by_field", {}) or {}
        if _safe_int(structured_counts.get(FIELD_PICKUP_STOPS)) > 0:
            structured[FIELD_PICKUP_STOPS] += 1
        if _safe_int(structured_counts.get(FIELD_DELIVERY_STOPS)) > 0:
            structured[FIELD_DELIVERY_STOPS] += 1
        if any(
            _safe_int(partial_counts.get(field_name)) > 0
            for field_name in [FIELD_PICKUP_STOPS, "pickup_count", "pickup_date", "pickup_location"]
        ):
            partial[FIELD_PICKUP_STOPS] += 1
        if any(
            _safe_int(partial_counts.get(field_name)) > 0
            for field_name in [
                FIELD_DELIVERY_STOPS,
                "delivery_count",
                "delivery_date",
                "delivery_location",
            ]
        ):
            partial[FIELD_DELIVERY_STOPS] += 1
    return {
        "independent_structured_present_by_field": structured,
        "independent_partial_present_by_field": partial,
    }


def _critical_document_coverage_by_strength(records, mapping_key):
    coverage = {field_name: Counter() for field_name in COVERAGE_FIELDS}
    for record in records or []:
        summary = (record or {}).get("candidate_summary", {}) or {}
        mapping = summary.get(KEY_MAPPING, {}) or {}
        by_field = mapping.get(mapping_key, {}) or {}
        for field_name in COVERAGE_FIELDS:
            strengths = by_field.get(field_name, {}) or {}
            for strength, count in strengths.items():
                if _safe_int(count) > 0:
                    coverage[field_name][strength] += 1
    return {
        field_name: _counter_dict(counter)
        for field_name, counter in coverage.items()
    }


def _fields_still_missing_independent_candidates(coverage):
    return [
        field_name
        for field_name, details in (coverage or {}).items()
        if _safe_int(details.get("candidate_present_count")) == 0
        or _safe_int(details.get("candidate_missing_count")) > 0
    ]


def _pdf_type_breakdown(records):
    grouped = defaultdict(list)
    for record in records or []:
        triage = (record or {}).get("triage", {}) or {}
        grouped[_text(triage.get("pdf_type")) or "unknown"].append(record)

    breakdown = {}
    for pdf_type, group in sorted(grouped.items()):
        code_counter = Counter()
        mismatch_count = 0
        for record in group:
            code_counter.update(_record_codes(record))
            if any(status == "different" for status in _record_compare(record).values()):
                mismatch_count += 1
        coverage = _candidate_coverage(group)
        breakdown[pdf_type] = {
            "document_count": len(group),
            "needs_review_count": sum(1 for record in group if _shadow_needs_review(record)),
            "needs_review_rate_percent": _percent(
                sum(1 for record in group if _shadow_needs_review(record)),
                len(group),
            ),
            "top_failure_codes": dict(list(_counter_dict(code_counter).items())[:10]),
            "missing_load_candidate_rate_percent": _percent(
                coverage[FIELD_LOAD_NUMBER]["candidate_missing_count"],
                len(group),
            ),
            "missing_total_rate_candidate_rate_percent": _percent(
                coverage[FIELD_TOTAL_RATE]["candidate_missing_count"],
                len(group),
            ),
            "legacy_shadow_mismatch_rate_percent": _percent(mismatch_count, len(group)),
        }
    return breakdown


def _candidate_missing_delta(before, after, field_name):
    before_field = ((before or {}).get("candidate_coverage", {}) or {}).get(field_name, {}) or {}
    after_field = ((after or {}).get("candidate_coverage", {}) or {}).get(field_name, {}) or {}
    before_missing = _safe_int(before_field.get("candidate_missing_count"))
    after_missing = _safe_int(after_field.get("candidate_missing_count"))
    return {
        "before_missing": before_missing,
        "after_missing": after_missing,
        "delta_missing": after_missing - before_missing,
    }


def _baseline_deltas(baseline, current):
    if not baseline:
        return {}
    return {
        "documents_processed": {
            "before": _safe_int(baseline.get("documents_processed")),
            "after": _safe_int(current.get("documents_processed")),
        },
        "needs_review": {
            "before": _safe_int(baseline.get("needs_review_count")),
            "after": _safe_int(current.get("needs_review_count")),
            "delta": _safe_int(current.get("needs_review_count"))
            - _safe_int(baseline.get("needs_review_count")),
        },
        "candidate_missing_by_field": {
            field_name: _candidate_missing_delta(baseline, current, field_name)
            for field_name in COVERAGE_FIELDS
        },
        "primary_layer_counts": {
            "before": baseline.get("primary_layer_counts", {}) or {},
            "after": current.get("primary_layer_counts", {}) or {},
        },
    }


def _select_primary_next_move(analysis):
    documents = _safe_int(analysis.get("documents_processed"))
    if documents <= 0:
        return {
            "primary_next_move": "improve audit granularity and add per-field/per-broker/per-PDF-type breakdowns",
            "why": "No shadow records were available to analyze.",
            "do_not_do_next": [
                "do not change extraction behavior without measurement data",
                "do not add OCR, AI, cloud services, or broker regex from an empty report",
            ],
            "secondary_next_moves": ["run private measurement with shadow audit enabled"],
        }

    family_counts = analysis.get("failure_family_document_counts", {}) or {}
    layer_counts = analysis.get("primary_layer_counts", {}) or {}
    review_rate = analysis.get("needs_review_rate_percent", 0.0)

    top_layer = "unknown"
    top_layer_count = 0
    if layer_counts:
        top_layer, top_layer_count = max(
            layer_counts.items(),
            key=lambda item: (_safe_int(item[1]), str(item[0])),
        )
        top_layer_count = _safe_int(top_layer_count)

    text_total = _safe_int(family_counts.get("document_or_text_quality"))
    candidate_total = _safe_int(family_counts.get("candidate_generation"))
    resolver_total = _safe_int(family_counts.get("resolution"))
    mismatch_total = _safe_int(family_counts.get("legacy_shadow_mismatch"))
    legacy_only_total = _safe_int(family_counts.get("legacy_only"))
    shadow_only_total = _safe_int(family_counts.get("shadow_only"))

    threshold = max(3, int(documents * 0.30))

    if top_layer in {"ingestion", "text_extraction"} and top_layer_count >= threshold:
        move = "implement OCR / scanned-PDF route"
        why = (
            f"{top_layer} is the primary suspected layer for "
            f"{top_layer_count} of {documents} documents."
        )
    elif top_layer == "candidate_generation" and top_layer_count >= threshold:
        move = "improve candidate generation and adapt existing legacy/template parsers into FieldCandidate producers"
        why = (
            "Candidate generation is the primary suspected layer for "
            f"{top_layer_count} of {documents} documents."
        )
    elif top_layer == "resolution" and top_layer_count >= threshold:
        move = "improve resolver scoring, conflict handling, confidence calibration, and evidence ranking"
        why = (
            f"Resolution is the primary suspected layer for {top_layer_count} "
            f"of {documents} documents."
        )
    elif top_layer == "validation" and review_rate >= 80.0 and top_layer_count >= threshold:
        move = "confidence threshold calibration using gold labels"
        why = (
            f"Needs-review rate is {review_rate}% and validation is the primary "
            f"suspected layer for {top_layer_count} of {documents} documents."
        )
    else:
        move = None
        why = None

    family_order = [
        ("candidate_generation", candidate_total),
        ("document_or_text_quality", text_total),
        ("resolution", resolver_total),
        ("legacy_shadow_mismatch", mismatch_total),
        ("legacy_only", legacy_only_total),
        ("shadow_only", shadow_only_total),
    ]
    if move is None:
        dominant_family, dominant_count = max(
            enumerate(family_order),
            key=lambda item: (_safe_int(item[1][1]), -item[0]),
        )[1]

        if dominant_family == "document_or_text_quality" and dominant_count >= threshold:
            move = "implement OCR / scanned-PDF route"
            why = f"Document/text quality codes affected {text_total} of {documents} documents."
        elif dominant_family == "candidate_generation" and dominant_count >= threshold:
            move = "improve candidate generation and adapt existing legacy/template parsers into FieldCandidate producers"
            why = f"Candidate-generation codes affected {candidate_total} of {documents} documents."
        elif dominant_family == "resolution" and dominant_count >= threshold:
            move = "improve resolver scoring, conflict handling, confidence calibration, and evidence ranking"
            why = f"Resolver/confidence codes affected {resolver_total} of {documents} documents."
        elif dominant_family == "legacy_shadow_mismatch" and dominant_count >= threshold:
            move = "build adjudication/evaluation harness using manually labeled gold fields before changing production behavior"
            why = f"Legacy/shadow mismatches affected {mismatch_total} of {documents} documents."
        elif dominant_family == "legacy_only" and dominant_count >= threshold:
            move = "wrap more legacy parser modules as candidate generators instead of replacing them"
            why = f"Legacy-only fields affected {legacy_only_total} of {documents} documents."
        elif dominant_family == "shadow_only" and dominant_count >= threshold:
            move = "start migration path where shadow output can be used experimentally for selected fields behind a feature flag"
            why = f"Shadow-only fields affected {shadow_only_total} of {documents} documents."
        else:
            move = "improve audit granularity and add per-field/per-broker/per-PDF-type breakdowns"
            why = "No single measured failure family dominates the shadow diagnostics."

    return {
        "primary_next_move": move,
        "why": why,
        "do_not_do_next": [
            "do not add broker regex without reviewed evidence",
            "do not replace legacy output yet",
            "do not suppress true conflicts",
            "do not claim accuracy improvement from diagnostics alone",
        ],
        "secondary_next_moves": [
            "review top problem documents locally",
            "run analyzer again after any corrected feedback or gold labels are available",
        ],
    }


def analyze_ratecon_shadow_audit(
    summary=None,
    audit_records=None,
    top_n=25,
    baseline_analysis=None,
):
    audit_records = [record for record in audit_records or [] if isinstance(record, dict)]
    documents = len(audit_records) or _safe_int((summary or {}).get("documents_processed"))
    shadow_success = sum(1 for record in audit_records if _shadow_success(record))
    shadow_failed = len(audit_records) - shadow_success if audit_records else _safe_int(
        (summary or {}).get("shadow_failed")
    )
    needs_review = sum(1 for record in audit_records if _shadow_needs_review(record))

    review_reasons = Counter()
    failure_codes = Counter()
    primary_layers = Counter()
    pdf_types = Counter()
    for record in audit_records:
        review_reasons.update(_record_review_reasons(record))
        failure_codes.update(_record_codes(record))
        primary_layers[_record_primary_layer(record)] += 1
        triage = (record or {}).get("triage", {}) or {}
        pdf_types[_text(triage.get("pdf_type")) or "unknown"] += 1

    field_comparisons = _field_comparison_counts(audit_records)
    candidate_coverage = _candidate_coverage(audit_records)
    independent_candidate_coverage = _candidate_coverage(
        audit_records,
        key=KEY_INDEPENDENT_COUNTS,
    )
    legacy_final_fallback_candidate_coverage = _candidate_coverage(
        audit_records,
        key=KEY_FALLBACK_COUNTS,
    )
    generator_candidate_counts = _generator_candidate_counts(audit_records)
    canonical_mapping_summary = _aggregate_canonical_mapping(audit_records)
    stop_candidate_coverage = _stop_candidate_coverage(audit_records)
    stop_assembly_summary = _aggregate_stop_assembly(audit_records)
    load_identity_line_summary = _aggregate_load_identity_line_summary(audit_records)
    load_identity_forensics = _aggregate_load_identity_forensics(audit_records)
    stop_proximity_summary = _aggregate_stop_proximity(audit_records)
    section_context_summary = _aggregate_section_context(audit_records)
    layout_provider_summary = _aggregate_layout_provider(audit_records)
    layout_pairing = _aggregate_layout_pairing(audit_records)
    layout_effectiveness = _aggregate_layout_effectiveness(audit_records)
    resolver_selection = _aggregate_resolver_selection(audit_records)
    independent_strength_document_coverage = _critical_document_coverage_by_strength(
        audit_records,
        "independent_critical_field_candidates_by_mapping_strength",
    )
    fallback_strength_document_coverage = _critical_document_coverage_by_strength(
        audit_records,
        "legacy_final_critical_field_candidates_by_mapping_strength",
    )
    family_document_counts = Counter()
    for record in audit_records:
        codes = set(_record_codes(record))
        comparison = _record_compare(record)
        if codes & TEXT_OR_DOCUMENT_CODES:
            family_document_counts["document_or_text_quality"] += 1
        if codes & CANDIDATE_CODES:
            family_document_counts["candidate_generation"] += 1
        if codes & RESOLVER_CODES:
            family_document_counts["resolution"] += 1
        if codes & VALIDATION_CODES:
            family_document_counts["validation"] += 1
        if "LEGACY_SHADOW_FIELD_MISMATCH" in codes or any(
            status == "different" for status in comparison.values()
        ):
            family_document_counts["legacy_shadow_mismatch"] += 1
        if "LEGACY_ONLY_FIELD" in codes or any(
            status == "legacy_only" for status in comparison.values()
        ):
            family_document_counts["legacy_only"] += 1
        if "SHADOW_ONLY_FIELD" in codes or any(
            status == "shadow_only" for status in comparison.values()
        ):
            family_document_counts["shadow_only"] += 1
    top_problem_documents = sorted(
        [_top_problem_document(record) for record in audit_records],
        key=lambda item: (-item["diagnostic_score"], item.get("document_id", "")),
    )[: int(top_n or 25)]

    layer_percentages = {
        layer: _percent(count, documents)
        for layer, count in _counter_dict(primary_layers).items()
    }
    code_percentages = {
        code: _percent(count, documents)
        for code, count in _counter_dict(failure_codes).items()
    }

    analysis = {
        "analysis_version": ROOT_CAUSE_ANALYSIS_VERSION,
        "documents_processed": documents,
        "shadow_success": shadow_success,
        "shadow_failed": shadow_failed,
        "shadow_success_rate_percent": _percent(shadow_success, documents),
        "shadow_failed_rate_percent": _percent(shadow_failed, documents),
        "needs_review_count": needs_review,
        "needs_review_rate_percent": _percent(needs_review, documents),
        "review_reason_counts": _counter_dict(review_reasons),
        "failure_code_counts": _counter_dict(failure_codes),
        "failure_code_percentages": code_percentages,
        "failure_family_document_counts": _counter_dict(family_document_counts),
        "failure_family_document_percentages": {
            family: _percent(count, documents)
            for family, count in _counter_dict(family_document_counts).items()
        },
        "primary_layer_counts": _counter_dict(primary_layers),
        "primary_layer_percentages": layer_percentages,
        "candidate_coverage": candidate_coverage,
        "independent_candidate_coverage": independent_candidate_coverage,
        "legacy_final_fallback_candidate_coverage": (
            legacy_final_fallback_candidate_coverage
        ),
        "generator_candidate_counts": generator_candidate_counts,
        "canonical_mapping_summary": canonical_mapping_summary,
        "stop_candidate_coverage": stop_candidate_coverage,
        "stop_assembly_summary": stop_assembly_summary,
        "load_identity_line_summary": load_identity_line_summary,
        "load_identity_forensics": load_identity_forensics,
        "stop_proximity_summary": stop_proximity_summary,
        "section_context_summary": section_context_summary,
        "layout_provider_summary": layout_provider_summary,
        "table_extraction_summary": layout_pairing["table_extraction_summary"],
        "table_profile_summary": layout_pairing["table_profile_summary"],
        "layout_load_pairing_summary": layout_pairing["layout_load_pairing_summary"],
        "layout_stop_pairing_summary": layout_pairing["layout_stop_pairing_summary"],
        "layout_candidate_effectiveness": layout_effectiveness,
        "candidate_quality_summary": layout_pairing["candidate_quality_summary"],
        "resolver_selection_summary": resolver_selection["resolver_selection_summary"],
        "load_number_selection_summary": resolver_selection[
            "load_number_selection_summary"
        ],
        "stop_selection_summary": resolver_selection["stop_selection_summary"],
        "structured_stop_resolution_summary": resolver_selection[
            "structured_stop_resolution_summary"
        ],
        "structured_stop_conflict_summary": resolver_selection[
            "structured_stop_conflict_summary"
        ],
        "rate_review_sanity_summary": resolver_selection["rate_review_sanity_summary"],
        "review_gate_trace_summary": resolver_selection["review_gate_trace_summary"],
        "independent_critical_document_coverage_by_strength": (
            independent_strength_document_coverage
        ),
        "legacy_final_critical_document_coverage_by_strength": (
            fallback_strength_document_coverage
        ),
        "fields_still_missing_independent_candidates": (
            _fields_still_missing_independent_candidates(
                independent_candidate_coverage
            )
        ),
        "field_comparison_counts": field_comparisons,
        "pdf_type_counts": _counter_dict(pdf_types),
        "pdf_type_breakdown": _pdf_type_breakdown(audit_records),
        "top_problem_documents": top_problem_documents,
        "private_values_printed": False,
        "raw_text_printed": False,
        "full_text_required": False,
    }
    if baseline_analysis:
        analysis["baseline_deltas"] = _baseline_deltas(baseline_analysis, analysis)
    analysis["recommendation"] = _select_primary_next_move(analysis)
    return analysis


def _format_counts(counts, total=0, limit=25):
    if not counts:
        return ["- none"]
    lines = []
    for key, count in list(counts.items())[:limit]:
        suffix = f" ({_percent(count, total)}%)" if total else ""
        lines.append(f"- {key}: {count}{suffix}")
    return lines


def root_cause_markdown_lines(analysis, top_n=25):
    documents = _safe_int(analysis.get("documents_processed"))
    rec = analysis.get("recommendation", {}) or {}
    lines = [
        "# RateCon Shadow Root-Cause Report",
        "",
        "Safe local analysis. No full document text, private values, or money values are required.",
        "",
        "## Executive Decision",
        f"PRIMARY NEXT MOVE: {rec.get('primary_next_move', '')}",
        f"WHY: {rec.get('why', '')}",
        "EVIDENCE:",
        f"- documents_processed: {documents}",
        f"- shadow_success: {analysis.get('shadow_success', 0)} ({analysis.get('shadow_success_rate_percent', 0.0)}%)",
        f"- shadow_failed: {analysis.get('shadow_failed', 0)} ({analysis.get('shadow_failed_rate_percent', 0.0)}%)",
        f"- needs_review: {analysis.get('needs_review_count', 0)} ({analysis.get('needs_review_rate_percent', 0.0)}%)",
        "",
        "DO NOT DO NEXT:",
    ]
    for item in rec.get("do_not_do_next", []) or []:
        lines.append(f"- {item}")
    lines.extend(["", "SECONDARY NEXT MOVES:"])
    for item in rec.get("secondary_next_moves", []) or []:
        lines.append(f"- {item}")

    lines.extend(["", "## Failure Attribution Codes"])
    lines.extend(_format_counts(analysis.get("failure_code_counts", {}), total=documents, limit=top_n))
    lines.extend(["", "## Primary Suspected Layers"])
    lines.extend(_format_counts(analysis.get("primary_layer_counts", {}), total=documents, limit=top_n))
    lines.extend(["", "## Failure Families"])
    lines.extend(_format_counts(analysis.get("failure_family_document_counts", {}), total=documents, limit=top_n))
    lines.extend(["", "## Review Reasons"])
    lines.extend(_format_counts(analysis.get("review_reason_counts", {}), total=documents, limit=top_n))
    lines.extend(["", "## Candidate Coverage"])
    coverage = analysis.get("candidate_coverage", {}) or {}
    for field_name in COVERAGE_FIELDS:
        field = coverage.get(field_name, {}) or {}
        missing = _safe_int(field.get("candidate_missing_count"))
        present = _safe_int(field.get("candidate_present_count"))
        lines.append(
            f"- {field_name}: present={present} ({_percent(present, documents)}%), "
            f"missing={missing} ({_percent(missing, documents)}%)"
        )

    lines.extend(["", "## Independent Candidate Coverage"])
    independent = analysis.get("independent_candidate_coverage", {}) or {}
    for field_name in COVERAGE_FIELDS:
        field = independent.get(field_name, {}) or {}
        present = _safe_int(field.get("candidate_present_count"))
        missing = _safe_int(field.get("candidate_missing_count"))
        lines.append(
            f"- {field_name}: independent_present={present} ({_percent(present, documents)}%), "
            f"independent_missing={missing} ({_percent(missing, documents)}%)"
        )

    lines.extend(["", "## Legacy-Final Fallback Candidate Coverage"])
    fallback = analysis.get("legacy_final_fallback_candidate_coverage", {}) or {}
    for field_name in COVERAGE_FIELDS:
        field = fallback.get(field_name, {}) or {}
        present = _safe_int(field.get("candidate_present_count"))
        missing = _safe_int(field.get("candidate_missing_count"))
        lines.append(
            f"- {field_name}: fallback_present={present} ({_percent(present, documents)}%), "
            f"fallback_missing={missing} ({_percent(missing, documents)}%)"
        )

    lines.extend(["", "## Candidate Generators"])
    lines.extend(_format_counts(analysis.get("generator_candidate_counts", {}), limit=top_n))

    mapping = analysis.get("canonical_mapping_summary", {}) or {}
    lines.extend(["", "## Canonical Mapping Summary"])
    lines.append(f"- mapped_candidate_count: {mapping.get('mapped_candidate_count', 0)}")
    lines.append(f"- unmapped_candidate_count: {mapping.get('unmapped_candidate_count', 0)}")
    lines.append("- mapped_by_strength:")
    lines.extend(_format_counts(mapping.get("mapped_by_strength", {}), limit=top_n))
    lines.append("- top_unmapped_raw_fields:")
    lines.extend(_format_counts(mapping.get("unmapped_raw_fields_top", {}), limit=top_n))

    lines.extend(["", "## Raw Fields By Generator"])
    for generator_name, counts in (
        mapping.get("raw_fields_by_generator", {}) or {}
    ).items():
        top = ", ".join(f"{field}={count}" for field, count in list(counts.items())[:8])
        lines.append(f"- {generator_name}: {top or 'none'}")

    lines.extend(["", "## Canonical Fields By Generator"])
    for generator_name, counts in (
        mapping.get("canonical_fields_by_generator", {}) or {}
    ).items():
        top = ", ".join(f"{field}={count}" for field, count in list(counts.items())[:8])
        lines.append(f"- {generator_name}: {top or 'none'}")

    lines.extend(["", "## Critical Fields By Mapping Strength"])
    for field_name, counts in (
        mapping.get("independent_critical_field_candidates_by_mapping_strength", {}) or {}
    ).items():
        count_text = ", ".join(f"{strength}={count}" for strength, count in counts.items())
        lines.append(f"- {field_name}: {count_text or 'none'}")

    lines.extend(["", "## Independent Critical Document Coverage By Strength"])
    doc_strength = analysis.get(
        "independent_critical_document_coverage_by_strength",
        {},
    ) or {}
    for field_name in COVERAGE_FIELDS:
        counts = doc_strength.get(field_name, {}) or {}
        count_text = ", ".join(f"{strength}={count}" for strength, count in counts.items())
        lines.append(f"- {field_name}: {count_text or 'none'}")

    line_diag = mapping.get("load_identifier_line_generator_diagnostics", {}) or {}
    lines.extend(["", "## Load Identifier Line Generator Diagnostics"])
    if line_diag:
        lines.extend(_format_counts(line_diag, limit=top_n))
    else:
        lines.append("- none")

    load_line_summary = analysis.get("load_identity_line_summary", {}) or {}
    lines.extend(["", "## Load Identity Line Summary"])
    lines.append(f"- lines_scanned: {load_line_summary.get('lines_scanned', 0)}")
    lines.append(f"- label_hits: {load_line_summary.get('label_hits', 0)}")
    lines.append(f"- emitted_candidates: {load_line_summary.get('emitted_candidates', 0)}")
    lines.append("- skipped_by_reason:")
    lines.extend(_format_counts(load_line_summary.get("skipped_by_reason", {}), limit=top_n))
    lines.append("- emitted_by_method:")
    lines.extend(_format_counts(load_line_summary.get("emitted_by_method", {}), limit=top_n))

    load_forensics = analysis.get("load_identity_forensics", {}) or {}
    lines.extend(["", "## Load Identity Forensics"])
    lines.append(f"- label_hits: {load_forensics.get('label_hits', 0)}")
    lines.append(f"- emitted_candidates: {load_forensics.get('emitted_candidates', 0)}")
    lines.append(
        f"- docs_with_label_hits: {load_forensics.get('docs_with_label_hits', 0)}"
    )
    lines.append(
        "- docs_with_emitted_load_candidates: "
        f"{load_forensics.get('docs_with_emitted_load_candidates', 0)}"
    )
    lines.append("- hit_type_counts:")
    lines.extend(_format_counts(load_forensics.get("hit_type_counts", {}), limit=top_n))
    lines.append("- rejection_reason_counts:")
    lines.extend(_format_counts(load_forensics.get("rejection_reason_counts", {}), limit=top_n))
    lines.append("- method_attempt_counts:")
    lines.extend(_format_counts(load_forensics.get("method_attempt_counts", {}), limit=top_n))
    lines.append("- method_success_counts:")
    lines.extend(_format_counts(load_forensics.get("method_success_counts", {}), limit=top_n))

    stop_summary = analysis.get("stop_assembly_summary", {}) or {}
    lines.extend(["", "## Stop Assembly Summary"])
    lines.append(f"- stop_evidence_count: {stop_summary.get('stop_evidence_count', 0)}")
    lines.append(
        "- assembled_pickup_stop_candidate_count: "
        f"{stop_summary.get('assembled_pickup_stop_candidate_count', 0)}"
    )
    lines.append(
        "- assembled_delivery_stop_candidate_count: "
        f"{stop_summary.get('assembled_delivery_stop_candidate_count', 0)}"
    )
    lines.append(
        "- docs_with_assembled_pickup_stops: "
        f"{stop_summary.get('docs_with_assembled_pickup_stops', 0)}"
    )
    lines.append(
        "- docs_with_assembled_delivery_stops: "
        f"{stop_summary.get('docs_with_assembled_delivery_stops', 0)}"
    )
    lines.append(
        f"- partial_stop_candidate_count: {stop_summary.get('partial_stop_candidate_count', 0)}"
    )
    lines.append(
        "- ambiguous_stop_candidate_count: "
        f"{stop_summary.get('ambiguous_stop_candidate_count', 0)}"
    )
    lines.append("- stop_evidence_by_role:")
    lines.extend(_format_counts(stop_summary.get("stop_evidence_by_role", {}), limit=top_n))
    lines.append("- stop_evidence_by_type:")
    lines.extend(_format_counts(stop_summary.get("stop_evidence_by_type", {}), limit=top_n))

    stop_proximity = analysis.get("stop_proximity_summary", {}) or {}
    lines.extend(["", "## Stop Proximity Summary"])
    for key in [
        "docs_with_proximity_clusters",
        "proximity_cluster_count",
        "ambiguous_cluster_count",
        "clusters_with_location_and_date",
        "clusters_with_location_only",
        "clusters_with_date_only",
    ]:
        lines.append(f"- {key}: {stop_proximity.get(key, 0)}")
    lines.append("- ambiguity_reason_counts:")
    lines.extend(_format_counts(stop_proximity.get("ambiguity_reason_counts", {}), limit=top_n))

    section_summary = analysis.get("section_context_summary", {}) or {}
    lines.extend(["", "## Section Context Summary"])
    lines.append(
        f"- lines_with_section_context: {section_summary.get('lines_with_section_context', 0)}"
    )
    lines.append(f"- unknown_section_lines: {section_summary.get('unknown_section_lines', 0)}")
    lines.append("- section_counts:")
    lines.extend(_format_counts(section_summary.get("section_counts", {}), limit=top_n))

    layout_provider = analysis.get("layout_provider_summary", {}) or {}
    lines.extend(["", "## Layout Provider Summary"])
    for key in [
        "pages_with_words",
        "pages_with_lines",
        "pages_with_tables",
        "word_count",
        "line_count",
        "table_count",
        "table_cell_count",
    ]:
        lines.append(f"- {key}: {layout_provider.get(key, 0)}")
    lines.append("- provider_status_counts:")
    lines.extend(_format_counts(layout_provider.get("provider_status_counts", {}), limit=top_n))
    lines.append("- warnings:")
    lines.extend(_format_counts(layout_provider.get("warnings", {}), limit=top_n))

    table_summary = analysis.get("table_extraction_summary", {}) or {}
    lines.extend(["", "## Table Extraction Summary"])
    lines.extend(_format_counts(table_summary, limit=top_n))

    table_profile = analysis.get("table_profile_summary", {}) or {}
    lines.extend(["", "## Table Profile Summary"])
    for key in [
        "tables_detected",
        "recognized_stop_tables",
        "recognized_load_tables",
        "recognized_rate_tables",
        "unrecognized_tables",
        "tables_with_load_like_headers",
    ]:
        lines.append(f"- {key}: {table_profile.get(key, 0)}")
    lines.append("- table_header_role_counts:")
    lines.extend(_format_counts(table_profile.get("table_header_role_counts", {}), limit=top_n))
    lines.append("- table_row_role_counts:")
    lines.extend(_format_counts(table_profile.get("table_row_role_counts", {}), limit=top_n))

    layout_load = analysis.get("layout_load_pairing_summary", {}) or {}
    lines.extend(["", "## Layout Load Pairing Summary"])
    for key in [
        "layout_label_hits",
        "same_row_pairings",
        "nearby_row_pairings",
        "table_cell_pairings",
        "header_block_pairings",
        "layout_candidates_emitted",
    ]:
        lines.append(f"- {key}: {layout_load.get(key, 0)}")
    lines.append("- layout_rejection_reason_counts:")
    lines.extend(
        _format_counts(layout_load.get("layout_rejection_reason_counts", {}), limit=top_n)
    )
    lines.append("- table_pairings_by_method:")
    lines.extend(_format_counts(layout_load.get("table_pairings_by_method", {}), limit=top_n))

    layout_stop = analysis.get("layout_stop_pairing_summary", {}) or {}
    lines.extend(["", "## Layout Stop Pairing Summary"])
    for key in [
        "layout_stop_evidence_count",
        "layout_structured_stop_candidates",
        "table_row_stop_candidates",
        "bbox_cluster_stop_candidates",
        "table_stop_candidates_complete",
        "table_stop_candidates_partial",
        "table_stop_candidates_ambiguous",
    ]:
        lines.append(f"- {key}: {layout_stop.get(key, 0)}")
    lines.append("- layout_ambiguity_reason_counts:")
    lines.extend(
        _format_counts(layout_stop.get("layout_ambiguity_reason_counts", {}), limit=top_n)
    )
    lines.append("- table_pairings_by_method:")
    lines.extend(_format_counts(layout_stop.get("table_pairings_by_method", {}), limit=top_n))

    effectiveness = analysis.get("layout_candidate_effectiveness", {}) or {}
    lines.extend(["", "## Layout Candidate Effectiveness"])
    load_effectiveness = effectiveness.get("layout_load_candidates", {}) or {}
    lines.append("- load_candidates:")
    for key in ["emitted", "accepted_by_resolver", "rejected_or_not_selected"]:
        lines.append(f"  - {key}: {load_effectiveness.get(key, 0)}")
    lines.append("  - by_pairing_method:")
    lines.extend(_format_counts(load_effectiveness.get("by_pairing_method", {}), limit=top_n))
    lines.append("  - by_id_type_hint:")
    lines.extend(_format_counts(load_effectiveness.get("by_id_type_hint", {}), limit=top_n))
    lines.append("  - by_confidence_band:")
    lines.extend(_format_counts(load_effectiveness.get("by_confidence_band", {}), limit=top_n))
    stop_effectiveness = effectiveness.get("layout_stop_candidates", {}) or {}
    lines.append("- stop_candidates:")
    for key in [
        "emitted",
        "structured",
        "partial",
        "with_location",
        "with_date",
        "with_time",
        "accepted_by_resolver",
        "rejected_or_not_selected",
    ]:
        lines.append(f"  - {key}: {stop_effectiveness.get(key, 0)}")
    lines.append("  - by_pairing_method:")
    lines.extend(_format_counts(stop_effectiveness.get("by_pairing_method", {}), limit=top_n))
    lines.append("  - ambiguity_reasons:")
    lines.extend(_format_counts(stop_effectiveness.get("ambiguity_reasons", {}), limit=top_n))

    resolver_selection = analysis.get("resolver_selection_summary", {}) or {}
    lines.extend(["", "## Resolver Selection Summary"])
    for field_name, details in (
        resolver_selection.get("fields", {}) or {}
    ).items():
        lines.append(
            f"- {field_name}: seen={details.get('candidate_count_seen', 0)}, "
            f"eligible={details.get('eligible_count', 0)}, "
            f"ineligible={details.get('ineligible_count', 0)}, "
            f"selected={details.get('selected_count', 0)}, "
            f"high_quality_not_selected={details.get('high_quality_not_selected_count', 0)}"
        )
        if details.get("not_selected_reason_counts"):
            reason_text = ", ".join(
                f"{reason}={count}"
                for reason, count in details.get("not_selected_reason_counts", {}).items()
            )
            lines.append(f"  - not_selected_reason_counts: {reason_text}")

    load_selection = analysis.get("load_number_selection_summary", {}) or {}
    lines.extend(["", "## Load Number Selection Summary"])
    for key in [
        "docs_with_any_load_candidates",
        "docs_with_high_quality_independent_load_candidates",
        "docs_with_medium_quality_independent_load_candidates",
        "docs_with_only_weak_load_candidates",
        "docs_with_only_legacy_fallback_load_candidates",
        "docs_with_selected_load_number",
        "docs_with_load_candidates_but_no_selection",
    ]:
        lines.append(f"- {key}: {load_selection.get(key, 0)}")
    lines.append("- not_selected_reason_counts:")
    lines.extend(_format_counts(load_selection.get("not_selected_reason_counts", {}), limit=top_n))
    lines.append("- selected_source_counts:")
    lines.extend(_format_counts(load_selection.get("selected_source_counts", {}), limit=top_n))
    lines.append("- selected_pairing_method_counts:")
    lines.extend(_format_counts(load_selection.get("selected_pairing_method_counts", {}), limit=top_n))

    stop_selection = analysis.get("stop_selection_summary", {}) or {}
    lines.extend(["", "## Stop Selection Summary"])
    for role in ["pickup", "delivery"]:
        role_summary = stop_selection.get(role, {}) or {}
        lines.append(f"- {role}:")
        for key in [
            "docs_with_any_candidates",
            "docs_with_complete_structured_candidates",
            "docs_with_partial_structured_candidates",
            "docs_with_ambiguous_candidates",
            "docs_with_table_row_candidates",
            "docs_with_bbox_cluster_candidates",
            "docs_with_selected_candidates",
            "docs_with_candidates_but_no_selection",
        ]:
            lines.append(f"  - {key}: {role_summary.get(key, 0)}")
        lines.append("  - not_selected_reason_counts:")
        lines.extend(_format_counts(role_summary.get("not_selected_reason_counts", {}), limit=top_n))

    structured_stop_resolution = analysis.get("structured_stop_resolution_summary", {}) or {}
    lines.extend(["", "## Structured Stop Resolution Summary"])
    for role in ["pickup", "delivery"]:
        role_summary = structured_stop_resolution.get(role, {}) or {}
        lines.append(f"- {role}:")
        for key in [
            "docs_with_structured_candidates",
            "docs_selected_complete",
            "docs_selected_partial",
            "docs_missing_after_resolution",
            "docs_conflict_review",
            "docs_unsupported",
            "duplicates_collapsed",
            "true_conflicts",
            "partial_overlaps",
        ]:
            lines.append(f"  - {key}: {role_summary.get(key, 0)}")

    structured_conflicts = analysis.get("structured_stop_conflict_summary", {}) or {}
    lines.extend(["", "## Structured Stop Conflict Summary"])
    for field_name in [FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS]:
        field_summary = structured_conflicts.get(field_name, {}) or {}
        lines.append(f"- {field_name}:")
        for key in [
            "candidate_count",
            "normalized_candidate_count",
            "duplicates_collapsed",
            "true_conflict_count",
            "partial_overlap_count",
        ]:
            lines.append(f"  - {key}: {field_summary.get(key, 0)}")
        lines.append("  - conflict_type_counts:")
        lines.extend(_format_counts(field_summary.get("conflict_type_counts", {}), limit=top_n))

    rate_sanity = analysis.get("rate_review_sanity_summary", {}) or {}
    lines.extend(["", "## Rate Review Sanity Summary"])
    for key in [
        "docs_with_rate_candidates",
        "docs_with_selected_rate",
        "docs_marked_rate_missing",
        "docs_marked_rate_low_confidence",
        "docs_with_rate_conflict",
        "rate_review_mismatch_count",
    ]:
        lines.append(f"- {key}: {rate_sanity.get(key, 0)}")
    lines.append("- mismatch_reasons:")
    lines.extend(_format_counts(rate_sanity.get("mismatch_reasons", {}), limit=top_n))

    review_gate_trace = analysis.get("review_gate_trace_summary", {}) or {}
    lines.extend(["", "## Review Gate Trace Summary"])
    lines.append(f"- needs_review_count: {review_gate_trace.get('needs_review_count', 0)}")
    lines.append("- critical_field_status_counts:")
    lines.extend(_format_counts(review_gate_trace.get("critical_field_status_counts", {}), limit=top_n))
    lines.append("- review_reason_source_counts:")
    lines.extend(_format_counts(review_gate_trace.get("review_reason_source_counts", {}), limit=top_n))

    quality = analysis.get("candidate_quality_summary", {}) or {}
    lines.extend(["", "## Candidate Quality Summary"])
    lines.append(f"- duplicate_candidates_removed: {quality.get('duplicate_candidates_removed', 0)}")
    lines.append("- critical_fields_with_high_quality_independent_candidates:")
    lines.extend(
        _format_counts(
            quality.get("critical_fields_with_high_quality_independent_candidates", {}),
            limit=top_n,
        )
    )
    lines.append("- critical_fields_with_only_weak_candidates:")
    lines.extend(
        _format_counts(quality.get("critical_fields_with_only_weak_candidates", {}), limit=top_n)
    )
    lines.append("- critical_fields_with_only_legacy_fallback:")
    lines.extend(
        _format_counts(quality.get("critical_fields_with_only_legacy_fallback", {}), limit=top_n)
    )

    lines.extend(["", "## Stop Candidate Coverage"])
    stop_coverage = analysis.get("stop_candidate_coverage", {}) or {}
    structured = stop_coverage.get("independent_structured_present_by_field", {}) or {}
    partial = stop_coverage.get("independent_partial_present_by_field", {}) or {}
    for field_name in [FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS]:
        lines.append(
            f"- {field_name}: structured_present={structured.get(field_name, 0)}, "
            f"partial_present={partial.get(field_name, 0)}"
        )

    lines.extend(["", "## Fields Still Missing Independent Candidates"])
    missing_independent = analysis.get("fields_still_missing_independent_candidates", []) or []
    if missing_independent:
        for field_name in missing_independent:
            lines.append(f"- {field_name}")
    else:
        lines.append("- none")

    if analysis.get("baseline_deltas"):
        lines.extend(["", "## Baseline Deltas"])
        deltas = analysis.get("baseline_deltas", {}) or {}
        for field_name, delta in (deltas.get("candidate_missing_by_field", {}) or {}).items():
            lines.append(
                f"- {field_name} missing candidates: "
                f"{delta.get('before_missing', 0)} -> {delta.get('after_missing', 0)} "
                f"(delta {delta.get('delta_missing', 0)})"
            )
        needs_review_delta = deltas.get("needs_review", {}) or {}
        lines.append(
            f"- needs_review: {needs_review_delta.get('before', 0)} -> "
            f"{needs_review_delta.get('after', 0)} "
            f"(delta {needs_review_delta.get('delta', 0)})"
        )

    lines.extend(["", "## Legacy vs Shadow Comparisons"])
    for field_name, counts in (analysis.get("field_comparison_counts", {}) or {}).items():
        count_text = ", ".join(f"{status}={count}" for status, count in counts.items())
        lines.append(f"- {field_name}: {count_text or 'none'}")

    lines.extend(["", "## PDF Type Breakdown"])
    for pdf_type, details in (analysis.get("pdf_type_breakdown", {}) or {}).items():
        lines.append(
            f"- {pdf_type}: documents={details.get('document_count', 0)}, "
            f"needs_review_rate={details.get('needs_review_rate_percent', 0.0)}%, "
            f"missing_load_candidate_rate={details.get('missing_load_candidate_rate_percent', 0.0)}%, "
            f"missing_total_rate_candidate_rate={details.get('missing_total_rate_candidate_rate_percent', 0.0)}%, "
            f"legacy_shadow_mismatch_rate={details.get('legacy_shadow_mismatch_rate_percent', 0.0)}%"
        )

    lines.extend(["", "## Top Problem Documents"])
    for item in (analysis.get("top_problem_documents", []) or [])[:top_n]:
        lines.append(
            f"- {item.get('document_id', '')}: pdf_type={item.get('pdf_type', '')}, "
            f"page_count={item.get('page_count', 0)}, layer={item.get('primary_suspected_layer', '')}, "
            f"codes={item.get('failure_codes', [])}, needs_review={item.get('needs_review', False)}, "
            f"load_candidates={item.get('candidate_counts', {}).get(FIELD_LOAD_NUMBER, 0)}, "
            f"rate_candidates={item.get('candidate_counts', {}).get(FIELD_TOTAL_RATE, 0)}"
        )
    if not analysis.get("top_problem_documents"):
        lines.append("- none")

    return lines


def _write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_ratecon_shadow_root_cause_artifacts(
    analysis,
    output_dir=None,
    allow_custom_output_dir=False,
    top_n=25,
):
    output_root = _normalize_output_dir(
        output_dir or DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    md_path = output_root / ROOT_CAUSE_REPORT_MD
    json_path = output_root / ROOT_CAUSE_SUMMARY_JSON
    md_path.write_text(
        "\n".join(root_cause_markdown_lines(analysis, top_n=top_n)) + "\n",
        encoding="utf-8",
    )
    json_path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    failure_rows = [
        {
            "failure_code": code,
            "count": count,
            "percent": (analysis.get("failure_code_percentages", {}) or {}).get(code, 0.0),
        }
        for code, count in (analysis.get("failure_code_counts", {}) or {}).items()
    ]
    layer_rows = [
        {
            "primary_suspected_layer": layer,
            "count": count,
            "percent": (analysis.get("primary_layer_percentages", {}) or {}).get(layer, 0.0),
        }
        for layer, count in (analysis.get("primary_layer_counts", {}) or {}).items()
    ]
    comparison_rows = []
    for field_name, counts in (analysis.get("field_comparison_counts", {}) or {}).items():
        for status, count in counts.items():
            comparison_rows.append(
                {
                    "field_name": field_name,
                    "comparison_status": status,
                    "count": count,
                    "percent": _percent(count, analysis.get("documents_processed", 0)),
                }
            )
    review_rows = [
        {
            "review_reason": reason,
            "count": count,
            "percent": _percent(count, analysis.get("documents_processed", 0)),
        }
        for reason, count in (analysis.get("review_reason_counts", {}) or {}).items()
    ]
    problem_rows = []
    for item in analysis.get("top_problem_documents", []) or []:
        problem_rows.append(
            {
                "document_id": item.get("document_id", ""),
                "file_name": item.get("file_name", ""),
                "file_hash": item.get("file_hash", ""),
                "pdf_type": item.get("pdf_type", ""),
                "page_count": item.get("page_count", 0),
                "quality_flags": ";".join(item.get("quality_flags", []) or []),
                "primary_suspected_layer": item.get("primary_suspected_layer", ""),
                "failure_codes": ";".join(item.get("failure_codes", []) or []),
                "needs_review": item.get("needs_review", False),
                "review_reasons": ";".join(item.get("review_reasons", []) or []),
                "load_number_candidate_count": (
                    item.get("candidate_counts", {}) or {}
                ).get(FIELD_LOAD_NUMBER, 0),
                "total_carrier_rate_candidate_count": (
                    item.get("candidate_counts", {}) or {}
                ).get(FIELD_TOTAL_RATE, 0),
                "load_number_comparison": (
                    item.get("legacy_shadow_comparisons", {}) or {}
                ).get(FIELD_LOAD_NUMBER, ""),
                "total_carrier_rate_comparison": (
                    item.get("legacy_shadow_comparisons", {}) or {}
                ).get(FIELD_TOTAL_RATE, ""),
                "diagnostic_score": item.get("diagnostic_score", 0),
            }
        )

    paths = {
        "root_cause_report_md": md_path.name,
        "root_cause_summary_json": json_path.name,
    }
    csv_specs = [
        (
            FAILURE_CODES_CSV,
            ["failure_code", "count", "percent"],
            failure_rows,
            "failure_codes_csv",
        ),
        (
            PRIMARY_LAYERS_CSV,
            ["primary_suspected_layer", "count", "percent"],
            layer_rows,
            "primary_layers_csv",
        ),
        (
            FIELD_COMPARISONS_CSV,
            ["field_name", "comparison_status", "count", "percent"],
            comparison_rows,
            "field_comparisons_csv",
        ),
        (
            REVIEW_REASONS_CSV,
            ["review_reason", "count", "percent"],
            review_rows,
            "review_reasons_csv",
        ),
        (
            TOP_PROBLEM_DOCUMENTS_CSV,
            [
                "document_id",
                "file_name",
                "file_hash",
                "pdf_type",
                "page_count",
                "quality_flags",
                "primary_suspected_layer",
                "failure_codes",
                "needs_review",
                "review_reasons",
                "load_number_candidate_count",
                "total_carrier_rate_candidate_count",
                "load_number_comparison",
                "total_carrier_rate_comparison",
                "diagnostic_score",
            ],
            problem_rows,
            "top_problem_documents_csv",
        ),
    ]
    for file_name, fieldnames, rows, key in csv_specs:
        csv_path = output_root / file_name
        _write_csv(csv_path, fieldnames, rows)
        paths[key] = csv_path.name

    return {
        "files": paths,
        "aggregate": analysis,
        "private_values_printed": False,
        "raw_text_printed": False,
        "money_values_printed": False,
    }
