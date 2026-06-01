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
    SYSTEM_LEGACY,
    SYSTEM_SHADOW,
    SYSTEM_SHADOW_CANDIDATE_BEST,
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
        if status in {"exact", "normalized_match", "unlabeled", "gold_uncertain"}:
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
    for system_name in [SYSTEM_LEGACY, SYSTEM_SHADOW, SYSTEM_SHADOW_CANDIDATE_BEST]:
        fields = (evaluation.get("field_metrics", {}) or {}).get(system_name, {})
        if not fields:
            continue
        lines.extend([f"### {system_name}", ""])
        lines.append("| field | labeled | precision | recall | missing_rate | wrong_rate | partial_rate |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for field_name in EVALUATION_FIELDS:
            metric = fields.get(field_name, {}) or {}
            lines.append(
                "| {field} | {labeled} | {precision} | {recall} | {missing} | {wrong} | {partial} |".format(
                    field=field_name,
                    labeled=metric.get("labeled_count", 0),
                    precision=metric.get("precision", 0.0),
                    recall=metric.get("recall", 0.0),
                    missing=metric.get("missing_rate", 0.0),
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
    allow_custom_output_dir=False,
):
    output_dir = _normalize_local_output_dir(
        output_dir,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    gold_labels = load_gold_labels(gold_path)
    audit_records = read_jsonl(audit_path)
    evaluation = evaluate_ratecon_against_gold(gold_labels, audit_records)
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
        ["document_id", "file_hash", "system", "field", "status", "issues", "confidence"],
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
