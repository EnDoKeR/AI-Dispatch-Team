"""Evaluate legacy and shadow RateCon diagnostics against local gold labels."""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.document_ai.ratecon_gold_labels import (  # noqa: E402
    EVALUATION_FIELDS,
    EVALUATION_SYSTEMS,
    STATUS_GOLD_UNCERTAIN,
    STATUS_NORMALIZED_MATCH,
    STATUS_EXACT,
    STATUS_UNLABELED,
    evaluate_ratecon_against_gold,
    load_gold_labels,
    read_jsonl,
    write_json,
)
from app.document_ai.ratecon_shadow_audit import RATECON_SHADOW_AUDIT_JSONL  # noqa: E402


DEFAULT_GOLD_DIR = Path(".local_outputs") / "private_ratecon_gold_labels"
DEFAULT_AUDIT = Path(".local_outputs") / "private_ratecon_measurement" / RATECON_SHADOW_AUDIT_JSONL
DEFAULT_OUTPUT_DIR = Path(".local_outputs") / "private_ratecon_gold_eval"


def _normalize_local_output_dir(output_dir, allow_custom_output_dir=False):
    path = Path(output_dir)
    if not allow_custom_output_dir and (not path.parts or path.parts[0] != ".local_outputs"):
        raise ValueError("gold evaluation output must be under .local_outputs unless --allow-custom-output-dir is used")
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_parser():
    parser = argparse.ArgumentParser(
        description="Evaluate local RateCon gold labels against legacy and shadow outputs."
    )
    parser.add_argument("--gold-dir", default=str(DEFAULT_GOLD_DIR))
    parser.add_argument("--gold-jsonl", default="")
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    parser.add_argument(
        "--legacy-output-dir",
        default="",
        help=(
            "Optional private measurement output directory. Safe summary files "
            "do not contain private legacy values; use audits generated with "
            "--include-private-eval-values for comparable local evaluation."
        ),
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--baseline-summary", default="")
    parser.add_argument("--allow-custom-output-dir", action="store_true")
    return parser


def _write_csv(path, fieldnames, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    return path


def _record_keys(record):
    keys = []
    document_id = str((record or {}).get("document_id") or "").strip()
    file_hash = str((record or {}).get("file_hash") or "").strip()
    file_name = str((record or {}).get("file_name") or "").strip()
    if document_id:
        keys.append(("document_id", document_id))
    if file_hash:
        keys.append(("file_hash", file_hash))
        keys.append(("file_hash_prefix", file_hash[:16]))
    if file_name:
        keys.append(("file_name", file_name))
        keys.append(("file_stem", Path(file_name).stem))
    return keys


def _merge_private_eval_sidecar(audit_records, legacy_output_dir, audit_path):
    if not legacy_output_dir:
        return audit_records, False
    sidecar = Path(legacy_output_dir) / RATECON_SHADOW_AUDIT_JSONL
    if not sidecar.exists() or sidecar.resolve() == Path(audit_path).resolve():
        return audit_records, False
    sidecar_records = read_jsonl(sidecar)
    indexed = {}
    for record in sidecar_records:
        for key in _record_keys(record):
            indexed.setdefault(key, record)
    merged = []
    changed = False
    for record in audit_records:
        updated = dict(record)
        match = next((indexed.get(key) for key in _record_keys(record) if indexed.get(key)), None)
        if (
            match
            and not updated.get("private_eval_values")
            and match.get("private_eval_values")
        ):
            updated["private_eval_values"] = match.get("private_eval_values")
            updated["private_eval_values_included"] = True
            changed = True
        merged.append(updated)
    return merged, changed


def _field_metric_rows(evaluation):
    rows = []
    for system_name, fields in (evaluation.get("field_metrics", {}) or {}).items():
        for field_name, metric in fields.items():
            row = {"system": system_name, "field": field_name}
            row.update(metric)
            rows.append(row)
    return rows


def _document_metric_rows(evaluation):
    rows = []
    for document in evaluation.get("document_metrics", []) or []:
        field_results = document.get("field_results", {}) or {}
        for field_name, result in field_results.items():
            rows.append(
                {
                    "document_id": document.get("document_id", ""),
                    "file_hash": document.get("file_hash", ""),
                    "field": field_name,
                    "legacy_vs_gold": result.get("legacy_vs_gold", ""),
                    "shadow_vs_gold": result.get("shadow_vs_gold", ""),
                    "winner": result.get("winner", ""),
                    "adjudication_category": result.get("adjudication_category", ""),
                    "recommended_action": result.get("recommended_action", ""),
                }
            )
    return rows


def _error_case_rows(evaluation):
    rows = []
    for row in evaluation.get("comparison_rows", []) or []:
        status = row.get("status")
        if status in {STATUS_EXACT, STATUS_NORMALIZED_MATCH, STATUS_UNLABELED, STATUS_GOLD_UNCERTAIN}:
            continue
        rows.append(
            {
                "document_id": row.get("document_id", ""),
                "file_hash": row.get("file_hash", ""),
                "system": row.get("system", ""),
                "field": row.get("field", ""),
                "status": status,
                "issues": ",".join(row.get("issues", []) or []),
                "confidence": row.get("confidence", ""),
                "source_status": row.get("source_status", ""),
                "source": row.get("source", ""),
                "pairing_method": row.get("pairing_method", ""),
                "section_context": row.get("section_context", ""),
                "document_region": row.get("document_region", ""),
                "id_type_hint": row.get("id_type_hint", ""),
                "money_context": row.get("money_context", ""),
                "rate_safety": row.get("rate_safety", ""),
                "rate_safety_reason": row.get("rate_safety_reason", ""),
                "rate_abstained": row.get("rate_abstained", ""),
                "rate_abstention_reason": row.get("rate_abstention_reason", ""),
                "rate_demoted_from_total_carrier_rate": row.get(
                    "rate_demoted_from_total_carrier_rate",
                    "",
                ),
                "stop_role": row.get("stop_role", ""),
                "has_location": row.get("has_location", ""),
                "has_date": row.get("has_date", ""),
                "has_time": row.get("has_time", ""),
                "stop_selection_policy": row.get("stop_selection_policy", ""),
                "stop_abstained": row.get("stop_abstained", ""),
                "stop_abstention_reason": row.get("stop_abstention_reason", ""),
                "stop_usability_tier": row.get("stop_usability_tier", ""),
                "role_confidence": row.get("role_confidence", ""),
                "component_completeness": row.get("component_completeness", ""),
                "table_context_role": row.get("table_context_role", ""),
                "table_row_role": row.get("table_row_role", ""),
                "table_neighbor_safety": row.get("table_neighbor_safety", ""),
                "table_neighbor_penalty_reason": row.get("table_neighbor_penalty_reason", ""),
                "table_neighbor_abstained": row.get("table_neighbor_abstained", ""),
                "table_neighbor_abstention_reason": row.get(
                    "table_neighbor_abstention_reason",
                    "",
                ),
                "selection_policy": row.get("selection_policy", ""),
                "error_reason": row.get("error_reason", ""),
            }
        )
    return rows


def _markdown_report(evaluation):
    lines = [
        "# RateCon Gold Evaluation",
        "",
        f"labels_loaded: {evaluation.get('labels_loaded', 0)}",
        f"labels_evaluated: {evaluation.get('labels_evaluated', 0)}",
        f"labels_skipped: {evaluation.get('labels_skipped', 0)}",
        f"labels_matched_to_audit: {evaluation.get('labels_matched_to_audit', 0)}",
        f"labels_unmatched_to_audit: {evaluation.get('labels_unmatched_to_audit', 0)}",
        "",
    ]
    if evaluation.get("labels_evaluated", 0) <= 0:
        lines.extend(
            [
                "No labeled gold records were available.",
                "",
                "Manual labels are required before accuracy, calibration, or migration decisions can be made.",
            ]
        )
        return "\n".join(lines) + "\n"
    lines.extend(["## Field Metrics", ""])
    for system_name in EVALUATION_SYSTEMS:
        fields = (evaluation.get("field_metrics", {}) or {}).get(system_name, {})
        if not fields:
            continue
        lines.extend([f"### {system_name}", ""])
        lines.append("| field | labeled | precision | recall | missing_rate | unavailable_rate | serialized_gap_rate | wrong_rate | partial_rate |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for field_name in EVALUATION_FIELDS:
            metric = fields.get(field_name, {}) or {}
            lines.append(
                "| {field} | {labeled} | {precision} | {recall} | {missing} | {unavailable} | {serialized} | {wrong} | {partial} |".format(
                    field=field_name,
                    labeled=metric.get("labeled_count", 0),
                    precision=metric.get("precision", 0.0),
                    recall=metric.get("recall", 0.0),
                    missing=metric.get("missing_rate", 0.0),
                    unavailable=metric.get("source_not_available_rate", 0.0),
                    serialized=metric.get("field_not_serialized_rate", 0.0),
                    wrong=metric.get("wrong_value_rate", 0.0),
                    partial=metric.get("partial_match_rate", 0.0),
                )
            )
        lines.append("")
    lines.extend(["## Adjudication", ""])
    adjudication = evaluation.get("adjudication", {}) or {}
    lines.append(f"winner_counts: {json.dumps(adjudication.get('winner_counts', {}), sort_keys=True)}")
    lines.append(f"category_counts: {json.dumps(adjudication.get('category_counts', {}), sort_keys=True)}")
    lines.append(
        "recommended_action_counts: "
        + json.dumps(adjudication.get("recommended_action_counts", {}), sort_keys=True)
    )
    lines.extend(["", "## Error Case Breakdown", ""])
    lines.append(
        "load_number: "
        + json.dumps(
            (evaluation.get("error_case_breakdown", {}) or {}).get("load_number", {}),
            sort_keys=True,
        )
    )
    lines.append(
        "total_carrier_rate: "
        + json.dumps(
            (evaluation.get("error_case_breakdown", {}) or {}).get("total_carrier_rate", {}),
            sort_keys=True,
        )
    )
    lines.extend(["", "## Error Analysis", ""])
    lines.append(
        "load_number_error_analysis: "
        + json.dumps(evaluation.get("load_number_error_analysis", {}) or {}, sort_keys=True)
    )
    lines.append(
        "load_table_neighbor_error_summary: "
        + json.dumps(evaluation.get("load_table_neighbor_error_summary", {}) or {}, sort_keys=True)
    )
    lines.append(
        "load_table_neighbor_value_cell_forensics: "
        + json.dumps(
            evaluation.get("load_table_neighbor_value_cell_forensics", {}) or {},
            sort_keys=True,
        )
    )
    lines.append(
        "remaining_table_neighbor_wrong_summary: "
        + json.dumps(
            evaluation.get("remaining_table_neighbor_wrong_summary", {}) or {},
            sort_keys=True,
        )
    )
    lines.append(
        "table_neighbor_abstention_summary: "
        + json.dumps(
            evaluation.get("table_neighbor_abstention_summary", {}) or {},
            sort_keys=True,
        )
    )
    lines.append(
        "rate_error_analysis: "
        + json.dumps(evaluation.get("rate_error_analysis", {}) or {}, sort_keys=True)
    )
    lines.append(
        "rate_wrong_case_summary: "
        + json.dumps(evaluation.get("rate_wrong_case_summary", {}) or {}, sort_keys=True)
    )
    lines.append(
        "residual_wrong_rate_forensics: "
        + json.dumps(
            evaluation.get("residual_wrong_rate_forensics", {}) or {},
            sort_keys=True,
        )
    )
    lines.append(
        "gold_rate_consistency_audit: "
        + json.dumps(
            evaluation.get("gold_rate_consistency_audit", {}) or {},
            sort_keys=True,
        )
    )
    lines.append(
        "missing_rate_forensics: "
        + json.dumps(evaluation.get("missing_rate_forensics", {}) or {}, sort_keys=True)
    )
    lines.append(
        "rate_abstention_summary: "
        + json.dumps(evaluation.get("rate_abstention_summary", {}) or {}, sort_keys=True)
    )
    lines.extend(["", "## Load Candidate Recall", ""])
    recall = dict(evaluation.get("load_candidate_recall_summary", {}) or {})
    recall.pop("documents", None)
    lines.append("load_candidate_recall_summary: " + json.dumps(recall, sort_keys=True))
    lines.extend(["", "## OCR/Vision Backlog", ""])
    backlog = dict(evaluation.get("ocr_vision_backlog_summary", {}) or {})
    backlog.pop("documents", None)
    lines.append("ocr_vision_backlog_summary: " + json.dumps(backlog, sort_keys=True))
    lines.append(
        "ocr_gold_eval_summary: "
        + json.dumps(evaluation.get("ocr_gold_eval_summary", {}) or {}, sort_keys=True)
    )
    load_gap = dict(evaluation.get("ocr_load_candidate_gap_summary", {}) or {})
    load_gap.pop("documents", None)
    lines.append(
        "ocr_load_candidate_gap_summary: "
        + json.dumps(load_gap, sort_keys=True)
    )
    rate_selection = dict(evaluation.get("ocr_rate_selection_summary", {}) or {})
    rate_selection.pop("cases", None)
    lines.append(
        "ocr_rate_selection_summary: "
        + json.dumps(rate_selection, sort_keys=True)
    )
    lines.append(
        "ocr_accessorial_noise_summary: "
        + json.dumps(
            evaluation.get("ocr_accessorial_noise_summary", {}) or {},
            sort_keys=True,
        )
    )
    lines.extend(["", "## Stop Component Forensics", ""])
    lines.append(
        "stop_component_forensics_summary: "
        + json.dumps(
            evaluation.get("stop_component_forensics_summary", {}) or {},
            sort_keys=True,
        )
    )
    lines.append(
        "stop_usability_summary: "
        + json.dumps(
            evaluation.get("stop_usability_summary", {}) or {},
            sort_keys=True,
        )
    )
    lines.append(
        "stop_gold_consistency_audit: "
        + json.dumps(
            evaluation.get("stop_gold_consistency_audit", {}) or {},
            sort_keys=True,
        )
    )
    lines.append(
        "stop_gold_completeness_summary: "
        + json.dumps(
            evaluation.get("stop_gold_completeness_summary", {}) or {},
            sort_keys=True,
        )
    )
    lines.append(
        "dispatch_usable_handoff_summary: "
        + json.dumps(
            {
                key: value
                for key, value in (
                    evaluation.get("dispatch_usable_handoff_summary", {}) or {}
                ).items()
                if key != "cases"
            },
            sort_keys=True,
        )
    )
    lines.append(
        "stop_candidate_group_metrics: "
        + json.dumps(
            evaluation.get("stop_candidate_group_metrics", {}) or {},
            sort_keys=True,
        )
    )
    lines.append(
        "stop_draft_profile_metrics: "
        + json.dumps(
            evaluation.get("stop_draft_profile_metrics", {}) or {},
            sort_keys=True,
        )
    )
    lines.append(
        "ocr_stop_evidence_gap_summary: "
        + json.dumps(
            evaluation.get("ocr_stop_evidence_gap_summary", {}) or {},
            sort_keys=True,
        )
    )
    lines.extend(["", "## Calibration", ""])
    calibration = evaluation.get("confidence_calibration", {}) or {}
    for field_name in EVALUATION_FIELDS:
        field = calibration.get(field_name, {}) or {}
        lines.append(
            f"{field_name}: labeled={field.get('labeled_count', 0)} "
            f"small_sample_warning={field.get('small_sample_warning', True)} "
            "do_not_apply_automatically=True"
        )
    lines.append("")
    return "\n".join(lines)


def evaluate_and_write(
    gold_path,
    audit_path,
    output_dir,
    legacy_output_dir="",
    allow_custom_output_dir=False,
):
    output_dir = _normalize_local_output_dir(
        output_dir,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    gold_labels = load_gold_labels(gold_path)
    audit_records = read_jsonl(audit_path)
    audit_records, sidecar_loaded = _merge_private_eval_sidecar(
        audit_records,
        legacy_output_dir=legacy_output_dir,
        audit_path=audit_path,
    )
    evaluation = evaluate_ratecon_against_gold(gold_labels, audit_records)
    evaluation["legacy_source"] = {
        "legacy_output_dir": str(legacy_output_dir or ""),
        "explicit_legacy_source_loaded": bool(sidecar_loaded),
        "note": (
            "Comparable legacy values are read from private_eval_values. "
            "Safe measurement summaries are redacted and are not used as truth."
        ),
    }
    summary_path = output_dir / "ratecon_gold_evaluation_summary.json"
    report_path = output_dir / "ratecon_gold_evaluation_report.md"
    field_csv = output_dir / "ratecon_gold_field_metrics.csv"
    document_csv = output_dir / "ratecon_gold_document_metrics.csv"
    error_csv = output_dir / "ratecon_gold_error_cases.csv"
    write_json(summary_path, evaluation)
    report_path.write_text(_markdown_report(evaluation), encoding="utf-8")
    _write_csv(
        field_csv,
        [
            "system",
            "field",
            "labeled_count",
            "uncertain_count",
            "predicted_count",
            "exact_match_count",
            "normalized_match_count",
            "partial_match_count",
            "missing_count",
            "extractor_missing_count",
            "source_not_available_count",
            "field_not_serialized_count",
            "redacted_not_comparable_count",
            "unsupported_value_type_count",
            "wrong_value_count",
            "conflict_count",
            "precision",
            "recall",
            "exact_match_rate",
            "normalized_match_rate",
            "partial_match_rate",
            "missing_rate",
            "wrong_value_rate",
            "low_confidence_but_correct_count",
            "high_confidence_but_wrong_count",
        ],
        _field_metric_rows(evaluation),
    )
    _write_csv(
        document_csv,
        [
            "document_id",
            "file_hash",
            "field",
            "legacy_vs_gold",
            "shadow_vs_gold",
            "winner",
            "adjudication_category",
            "recommended_action",
        ],
        _document_metric_rows(evaluation),
    )
    _write_csv(
        error_csv,
        [
            "document_id",
            "file_hash",
            "system",
            "field",
            "status",
            "issues",
            "confidence",
            "source_status",
            "source",
            "pairing_method",
            "section_context",
            "document_region",
            "id_type_hint",
            "money_context",
            "rate_safety",
            "rate_safety_reason",
            "rate_abstained",
            "rate_abstention_reason",
            "rate_demoted_from_total_carrier_rate",
            "stop_role",
            "has_location",
            "has_date",
            "has_time",
            "stop_selection_policy",
            "stop_abstained",
            "stop_abstention_reason",
            "stop_usability_tier",
            "role_confidence",
            "component_completeness",
            "table_context_role",
            "table_row_role",
            "table_neighbor_safety",
            "table_neighbor_penalty_reason",
            "table_neighbor_abstained",
            "table_neighbor_abstention_reason",
            "selection_policy",
            "error_reason",
        ],
        _error_case_rows(evaluation),
    )
    return {
        "files": {
            "summary": summary_path.name,
            "report": report_path.name,
            "field_metrics": field_csv.name,
            "document_metrics": document_csv.name,
            "error_cases": error_csv.name,
        },
        "labels_loaded": evaluation.get("labels_loaded", 0),
        "labels_evaluated": evaluation.get("labels_evaluated", 0),
        "labels_skipped": evaluation.get("labels_skipped", 0),
        "labels_matched_to_audit": evaluation.get("labels_matched_to_audit", 0),
        "labels_unmatched_to_audit": evaluation.get("labels_unmatched_to_audit", 0),
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def main(argv=None):
    args = build_parser().parse_args(argv)
    gold_path = args.gold_jsonl or args.gold_dir
    result = evaluate_and_write(
        gold_path=gold_path,
        audit_path=args.audit,
        output_dir=args.output_dir,
        legacy_output_dir=args.legacy_output_dir,
        allow_custom_output_dir=args.allow_custom_output_dir,
    )
    print(
        "ratecon_gold_evaluation_written: "
        + json.dumps(
            {
                "files": result["files"],
                "labels_loaded": result["labels_loaded"],
                "labels_evaluated": result["labels_evaluated"],
                "labels_skipped": result["labels_skipped"],
                "labels_matched_to_audit": result["labels_matched_to_audit"],
                "labels_unmatched_to_audit": result["labels_unmatched_to_audit"],
                "private_values_printed": False,
                "raw_text_printed": False,
            },
            sort_keys=True,
        )
    )
    if result["labels_evaluated"] <= 0:
        print("no_labeled_gold_records_found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
