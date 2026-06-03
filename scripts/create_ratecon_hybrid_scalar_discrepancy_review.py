"""Create a local-only scalar discrepancy review packet for hybrid RateCon results.

The review packet explains load/rate mismatches between manually supplied
hybrid results and local gold labels. It does not call AI models, cloud APIs,
OCR, local model runtimes, PDF processing, or modify gold/template files.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
import csv
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.ratecon_gold_labels import (  # noqa: E402
    FIELD_LOAD_NUMBER,
    FIELD_TOTAL_CARRIER_RATE,
    STATUS_EXACT,
    STATUS_GOLD_UNCERTAIN,
    STATUS_MISSING,
    STATUS_NORMALIZED_MATCH,
    STATUS_UNLABELED,
    compare_field,
    load_gold_labels,
    normalize_load_number,
    normalize_money,
)
from app.document_ai.ratecon_hybrid_contract import is_under_local_outputs  # noqa: E402
from scripts.run_ratecon_hybrid_benchmark import (  # noqa: E402
    _file_name_or_label,
    _gold_indexes,
    _load_hybrid_results,
    _match_gold,
    _prediction_for_scalar,
    _scalar_source_path,
    _scalar_value_from_field,
    _text,
)


DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_hybrid_scalar_discrepancy_review")
SCALAR_FIELDS = (FIELD_LOAD_NUMBER, FIELD_TOTAL_CARRIER_RATE)
CORRECT_STATUSES = {STATUS_EXACT, STATUS_NORMALIZED_MATCH}
LOCAL_ONLY = "<redacted>"


class ScalarDiscrepancyReviewError(ValueError):
    """Raised when scalar discrepancy review would be unsafe or invalid."""


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    resolved = _repo_relative(path)
    if not resolved.exists():
        return []
    records: list[dict[str, Any]] = []
    with resolved.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _read_csv_index(path: Path, key_fields: tuple[str, ...]) -> dict[tuple[str, ...], dict[str, Any]]:
    resolved = _repo_relative(path)
    if not resolved.exists():
        return {}
    with resolved.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {tuple(_text(row.get(key)) for key in key_fields): row for row in rows}


def _issue_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(item) for item in value if _text(item)]
    text = _text(value)
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            parsed = None
        if isinstance(parsed, list):
            return [_text(item) for item in parsed if _text(item)]
    return [_text(part) for part in text.split(",") if _text(part)]


def _benchmark_field_index(benchmark_dir: Path | None) -> dict[tuple[str, str], dict[str, Any]]:
    if not benchmark_dir:
        return {}
    return _read_csv_index(_repo_relative(benchmark_dir) / "hybrid_field_metrics.csv", ("document_id", "field"))


def _benchmark_money_index(benchmark_dir: Path | None) -> dict[tuple[str, str], dict[str, Any]]:
    if not benchmark_dir:
        return {}
    return _read_csv_index(_repo_relative(benchmark_dir) / "hybrid_money_diagnostics.csv", ("document_id", "field"))


def _audit_index(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        for key in ("document_id", "file_name", "file_hash", "file_hash_prefix"):
            value = _text(record.get(key))
            if value and value not in indexed:
                indexed[value] = record
    return indexed


def _match_audit(result: dict[str, Any], index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for key in ("document_id", "file_name", "file_hash"):
        value = _text(result.get(key))
        if value and value in index:
            return index[value]
    file_hash_prefix = _text(result.get("file_hash_prefix"))
    if file_hash_prefix:
        for key, record in index.items():
            if key.startswith(file_hash_prefix) or file_hash_prefix.startswith(key):
                return record
    return {}


def _gold_scalar_value(gold_field: Any) -> Any:
    if isinstance(gold_field, dict):
        return gold_field.get("value")
    return gold_field


def _gold_uncertain(gold_field: Any) -> bool:
    return isinstance(gold_field, dict) and bool(gold_field.get("uncertain"))


def _gold_adjudication_status(gold_field: Any) -> str:
    if not isinstance(gold_field, dict):
        return ""
    return _text(
        gold_field.get("adjudication_status")
        or gold_field.get("review_status")
        or gold_field.get("status")
    )


def _normalized(value: Any, field_name: str) -> str:
    if field_name == FIELD_TOTAL_CARRIER_RATE:
        return normalize_money(value)
    if field_name == FIELD_LOAD_NUMBER:
        return normalize_load_number(value)
    return _text(value).lower()


def _safe_value(value: Any, *, include_private_values_local_only: bool) -> Any:
    if include_private_values_local_only:
        return value
    return LOCAL_ONLY if _text(value) else ""


def _match_key(result: dict[str, Any], gold: dict[str, Any] | None) -> str:
    if not gold:
        return "unknown"
    for key in ("document_id", "file_name", "file_hash"):
        left = _text(result.get(key))
        right = _text(gold.get(key))
        if left and right and left == right:
            return key
    prefix = _text(result.get("file_hash_prefix"))
    gold_hash = _text(gold.get("file_hash"))
    if prefix and gold_hash and gold_hash.startswith(prefix):
        return "file_hash_prefix"
    return "unknown"


def _has_match_disagreement(result: dict[str, Any], gold: dict[str, Any] | None, key: str) -> bool:
    if not gold:
        return False
    left = _text(result.get(key))
    right = _text(gold.get(key))
    return bool(left and right and left != right)


def _classification(
    *,
    field_name: str,
    status: str,
    issues: list[str],
    result: dict[str, Any],
    gold: dict[str, Any] | None,
    hybrid_norm: str,
    gold_norm: str,
    has_evidence: bool,
) -> str:
    if not gold:
        return "benchmark_lookup_bug"
    gold_field = (gold.get("gold") or {}).get(field_name)
    if _gold_uncertain(gold_field):
        return "uncertain_gold_review_required"
    matched_by = _match_key(result, gold)
    if matched_by in {"file_name", "file_hash", "file_hash_prefix"} and _has_match_disagreement(result, gold, "document_id"):
        return "document_id_match_wrong"
    if matched_by == "document_id" and _has_match_disagreement(result, gold, "file_hash"):
        return "file_hash_match_wrong"
    if status not in CORRECT_STATUSES and hybrid_norm and gold_norm and hybrid_norm == gold_norm:
        if field_name == FIELD_TOTAL_CARRIER_RATE:
            return "numeric_normalization_bug"
        return "benchmark_lookup_bug"
    if STATUS_MISSING in {status, *issues} or not hybrid_norm:
        return "hybrid_template_wrong"
    if not has_evidence:
        return "hybrid_template_wrong"
    if gold_norm and hybrid_norm and gold_norm != hybrid_norm:
        return "gold_label_wrong_or_outdated"
    return "unknown"


def _recommended_action(classification: str) -> str:
    return {
        "hybrid_template_wrong": "correct_hybrid_template",
        "gold_label_wrong_or_outdated": "review_gold_label",
        "document_evidence_ambiguous": "needs_human_review",
        "document_id_match_wrong": "review_document_id_match",
        "file_hash_match_wrong": "review_file_hash_match",
        "benchmark_lookup_bug": "benchmark_bug_suspected",
        "numeric_normalization_bug": "numeric_normalization_bug_suspected",
        "uncertain_gold_review_required": "needs_human_review",
    }.get(classification, "needs_human_review")


def _field_has_evidence(field: Any) -> bool:
    if not isinstance(field, dict):
        return False
    evidence_ids = field.get("evidence_ids") or []
    return isinstance(evidence_ids, list) and any(_text(item) for item in evidence_ids)


def _hybrid_evidence_ids(field: Any) -> str:
    if not isinstance(field, dict):
        return ""
    evidence_ids = field.get("evidence_ids") or []
    if not isinstance(evidence_ids, list):
        return ""
    return ",".join(_text(item) for item in evidence_ids if _text(item))


def _build_item(
    *,
    result_path: Path,
    result: dict[str, Any],
    gold: dict[str, Any] | None,
    audit_record: dict[str, Any],
    field_name: str,
    benchmark_row: dict[str, Any] | None,
    money_row: dict[str, Any] | None,
    include_private_values_local_only: bool,
) -> dict[str, Any] | None:
    fields = result.get("fields") or {}
    field = fields.get(field_name) or {}
    prediction = _prediction_for_scalar(result, field_name)
    gold_field = (gold.get("gold") or {}).get(field_name) if gold else None
    compare_result = compare_field(field_name, prediction, gold_field)
    status = _text((benchmark_row or {}).get("status")) or _text(compare_result.get("status"))
    issues = _issue_list((benchmark_row or {}).get("issues")) or _issue_list(compare_result.get("issues") or [])
    if status in CORRECT_STATUSES or status == STATUS_UNLABELED:
        return None
    hybrid_value = _scalar_value_from_field(field, field_name)
    gold_value = _gold_scalar_value(gold_field)
    hybrid_norm = _normalized(hybrid_value, field_name)
    gold_norm = _normalized(gold_value, field_name)
    has_evidence = _field_has_evidence(field)
    classification = _classification(
        field_name=field_name,
        status=status,
        issues=issues,
        result=result,
        gold=gold,
        hybrid_norm=hybrid_norm,
        gold_norm=gold_norm,
        has_evidence=has_evidence,
    )
    document_id = _text(result.get("document_id")) or result_path.stem
    return {
        "document_id": document_id,
        "file_name": _file_name_or_label(result, result_path.stem),
        "file_hash_prefix": _text(result.get("file_hash_prefix") or result.get("file_hash"))[:16],
        "field": field_name,
        "benchmark_status": status,
        "benchmark_reason": ",".join(issues),
        "hybrid_value_normalized": _safe_value(hybrid_norm, include_private_values_local_only=include_private_values_local_only),
        "gold_value_normalized": _safe_value(gold_norm, include_private_values_local_only=include_private_values_local_only),
        "hybrid_value_local_only": _safe_value(hybrid_value, include_private_values_local_only=include_private_values_local_only),
        "gold_value_local_only": _safe_value(gold_value, include_private_values_local_only=include_private_values_local_only),
        "hybrid_source_path": _scalar_source_path(field, field_name),
        "gold_source_path": f"gold.{field_name}.value",
        "hybrid_evidence_ids": _hybrid_evidence_ids(field),
        "gold_adjudication_status": _gold_adjudication_status(gold_field),
        "gold_uncertain": bool(_gold_uncertain(gold_field)),
        "matched_by": _match_key(result, gold),
        "audit_document_id": _text(audit_record.get("document_id")),
        "audit_file_name": _text(audit_record.get("file_name")),
        "diagnostic_classification": classification,
        "recommended_action": _recommended_action(classification),
        "money_comparison_reason": _text((money_row or {}).get("comparison_reason")),
        "money_source_field_path": _text((money_row or {}).get("source_field_path")),
        "normalized_equal": bool(hybrid_norm and gold_norm and hybrid_norm == gold_norm),
    }


def create_scalar_discrepancy_review(
    *,
    hybrid_results_dir: Path,
    gold_dir: Path,
    audit: Path | None = None,
    benchmark_dir: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    include_private_values_local_only: bool = False,
    fields: list[str] | None = None,
    document_ids: list[str] | None = None,
) -> dict[str, Any]:
    if not is_under_local_outputs(output_dir, REPO_ROOT):
        raise ScalarDiscrepancyReviewError("Output directory must be under .local_outputs.")
    requested_fields = fields or list(SCALAR_FIELDS)
    invalid_fields = sorted(set(requested_fields) - set(SCALAR_FIELDS))
    if invalid_fields:
        raise ScalarDiscrepancyReviewError(f"Unsupported scalar field(s): {', '.join(invalid_fields)}")

    resolved_output = _repo_relative(output_dir)
    resolved_output.mkdir(parents=True, exist_ok=True)

    labels = load_gold_labels(_repo_relative(gold_dir))
    gold_indexes = _gold_indexes(labels)
    hybrid_results = _load_hybrid_results(hybrid_results_dir, allow_missing=False)
    audit_records = _read_jsonl(audit)
    audit_by_key = _audit_index(audit_records)
    benchmark_rows = _benchmark_field_index(benchmark_dir)
    money_rows = _benchmark_money_index(benchmark_dir)
    wanted_docs = set(document_ids or [])

    items: list[dict[str, Any]] = []
    match_rows: list[dict[str, Any]] = []
    money_diagnostics: list[dict[str, Any]] = []
    for result_path, result in hybrid_results:
        document_id = _text(result.get("document_id")) or result_path.stem
        if wanted_docs and document_id not in wanted_docs:
            continue
        gold = _match_gold(result, gold_indexes)
        audit_record = _match_audit(result, audit_by_key)
        matched_by = _match_key(result, gold)
        match_rows.append(
            {
                "document_id": document_id,
                "hybrid_file": result_path.name,
                "gold_document_id": _text((gold or {}).get("document_id")),
                "gold_file_name": _text((gold or {}).get("file_name")),
                "audit_document_id": _text(audit_record.get("document_id")),
                "audit_file_name": _text(audit_record.get("file_name")),
                "matched_by": matched_by,
                "document_id_agrees": not _has_match_disagreement(result, gold, "document_id"),
                "file_name_agrees": not _has_match_disagreement(result, gold, "file_name"),
                "file_hash_agrees": not _has_match_disagreement(result, gold, "file_hash"),
            }
        )
        for field_name in requested_fields:
            item = _build_item(
                result_path=result_path,
                result=result,
                gold=gold,
                audit_record=audit_record,
                field_name=field_name,
                benchmark_row=benchmark_rows.get((document_id, field_name)),
                money_row=money_rows.get((document_id, field_name)),
                include_private_values_local_only=include_private_values_local_only,
            )
            if not item:
                continue
            items.append(item)
            if field_name == FIELD_TOTAL_CARRIER_RATE:
                money_diagnostics.append(
                    {
                        "document_id": item["document_id"],
                        "field": item["field"],
                        "benchmark_status": item["benchmark_status"],
                        "benchmark_reason": item["benchmark_reason"],
                        "hybrid_value_normalized": item["hybrid_value_normalized"],
                        "gold_value_normalized": item["gold_value_normalized"],
                        "hybrid_source_path": item["hybrid_source_path"],
                        "gold_source_path": item["gold_source_path"],
                        "normalized_equal": item["normalized_equal"],
                        "diagnostic_classification": item["diagnostic_classification"],
                    }
                )

    classification_counts = Counter(item["diagnostic_classification"] for item in items)
    recommended_counts = Counter(item["recommended_action"] for item in items)
    patch_rows = [
        {
            "document_id": item["document_id"],
            "field": item["field"],
            "diagnostic_classification": item["diagnostic_classification"],
            "recommended_action": item["recommended_action"],
            "proposed_hybrid_value": None,
            "proposed_gold_value": None,
            "notes": "",
        }
        for item in items
        if item["diagnostic_classification"] not in {"benchmark_lookup_bug", "numeric_normalization_bug"}
    ]
    patch_template = {
        "schema_version": "ratecon_hybrid_scalar_discrepancy_patch_template_v1",
        "dry_run_only": True,
        "auto_apply_supported": False,
        "planned_change_count": 0,
        "patches": patch_rows,
    }
    summary = {
        "schema_version": "ratecon_hybrid_scalar_discrepancy_review_summary_v1",
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ai_model_invocation_attempted": False,
        "hybrid_result_count": len(hybrid_results),
        "gold_label_count": len(labels),
        "discrepancy_item_count": len(items),
        "fields_checked": requested_fields,
        "classification_counts": dict(classification_counts),
        "recommended_action_counts": dict(recommended_counts),
        "patch_template_row_count": len(patch_rows),
        "planned_change_count": 0,
        "private_values_included": bool(include_private_values_local_only),
    }
    _write_outputs(
        resolved_output,
        summary=summary,
        items=items,
        money_diagnostics=money_diagnostics,
        match_rows=match_rows,
        patch_template=patch_template,
    )
    return summary


ITEM_FIELDNAMES = [
    "document_id",
    "file_name",
    "file_hash_prefix",
    "field",
    "benchmark_status",
    "benchmark_reason",
    "hybrid_value_normalized",
    "gold_value_normalized",
    "hybrid_value_local_only",
    "gold_value_local_only",
    "hybrid_source_path",
    "gold_source_path",
    "hybrid_evidence_ids",
    "gold_adjudication_status",
    "gold_uncertain",
    "matched_by",
    "audit_document_id",
    "audit_file_name",
    "diagnostic_classification",
    "recommended_action",
    "normalized_equal",
]


def _write_outputs(
    output_dir: Path,
    *,
    summary: dict[str, Any],
    items: list[dict[str, Any]],
    money_diagnostics: list[dict[str, Any]],
    match_rows: list[dict[str, Any]],
    patch_template: dict[str, Any],
) -> None:
    _write_json(output_dir / "scalar_discrepancy_items.json", {"items": items})
    _write_json(output_dir / "scalar_discrepancy_patch_template.json", patch_template)
    _write_csv(output_dir / "scalar_discrepancy_items.csv", items, ITEM_FIELDNAMES)
    _write_csv(
        output_dir / "scalar_money_diagnostics.csv",
        money_diagnostics,
        [
            "document_id",
            "field",
            "benchmark_status",
            "benchmark_reason",
            "hybrid_value_normalized",
            "gold_value_normalized",
            "hybrid_source_path",
            "gold_source_path",
            "normalized_equal",
            "diagnostic_classification",
        ],
    )
    _write_csv(
        output_dir / "scalar_match_diagnostics.csv",
        match_rows,
        [
            "document_id",
            "hybrid_file",
            "gold_document_id",
            "gold_file_name",
            "audit_document_id",
            "audit_file_name",
            "matched_by",
            "document_id_agrees",
            "file_name_agrees",
            "file_hash_agrees",
        ],
    )
    lines = [
        "# RateCon Hybrid Scalar Discrepancy Review",
        "",
        "This local-only review packet made no AI, cloud, OCR, model, or PDF processing calls.",
        "",
        "## Summary",
        "",
        f"- hybrid results checked: {summary['hybrid_result_count']}",
        f"- discrepancy items: {summary['discrepancy_item_count']}",
        f"- fields checked: {', '.join(summary['fields_checked'])}",
        f"- patch template rows: {summary['patch_template_row_count']}",
        f"- planned changes: {summary['planned_change_count']}",
        f"- private values included: {summary['private_values_included']}",
        "",
        "## Classification Counts",
        "",
    ]
    for key, count in sorted(summary["classification_counts"].items()):
        lines.append(f"- {key}: {count}")
    if not summary["classification_counts"]:
        lines.append("- none")
    lines.extend(["", "## Recommended Action Counts", ""])
    for key, count in sorted(summary["recommended_action_counts"].items()):
        lines.append(f"- {key}: {count}")
    if not summary["recommended_action_counts"]:
        lines.append("- none")
    lines.extend(["", "## Output Files", ""])
    for name in [
        "scalar_discrepancy_items.csv",
        "scalar_discrepancy_items.json",
        "scalar_discrepancy_patch_template.json",
        "scalar_money_diagnostics.csv",
        "scalar_match_diagnostics.csv",
    ]:
        lines.append(f"- {name}")
    (output_dir / "scalar_discrepancy_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a local-only hybrid scalar discrepancy review packet.")
    parser.add_argument("--hybrid-results-dir", type=Path, required=True)
    parser.add_argument("--gold-dir", type=Path, required=True)
    parser.add_argument("--audit", type=Path, default=None)
    parser.add_argument("--benchmark-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    parser.add_argument("--field", action="append", choices=list(SCALAR_FIELDS), default=None)
    parser.add_argument("--document-id", action="append", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required for local private scalar review")
    summary = create_scalar_discrepancy_review(
        hybrid_results_dir=args.hybrid_results_dir,
        gold_dir=args.gold_dir,
        audit=args.audit,
        benchmark_dir=args.benchmark_dir,
        output_dir=args.output_dir,
        include_private_values_local_only=args.include_private_values_local_only,
        fields=args.field,
        document_ids=args.document_id,
    )
    print("RateCon hybrid scalar discrepancy review")
    print(f"discrepancy_item_count: {summary['discrepancy_item_count']}")
    print(f"patch_template_row_count: {summary['patch_template_row_count']}")
    print("external_api_calls_attempted: False")
    print("pdf_processing_attempted: False")
    print("ai_model_invocation_attempted: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
