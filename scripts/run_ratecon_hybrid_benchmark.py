"""Local-only benchmark runner for submitted RateCon hybrid result JSON files.

The runner validates manually supplied or future model-supplied JSON results and
compares review-only drafts to local gold labels. It does not call AI models,
cloud APIs, OCR, local model runtimes, or PDF processing.
"""

from __future__ import annotations

import argparse
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
    FIELD_DELIVERY_STOPS,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_STOPS,
    FIELD_TOTAL_CARRIER_RATE,
    STATUS_EXACT,
    STATUS_MISSING,
    STATUS_NORMALIZED_MATCH,
    STATUS_PARTIAL_MATCH,
    STATUS_UNLABELED,
    STATUS_WRONG_VALUE,
    compare_field,
    load_gold_labels,
)
from app.document_ai.ratecon_hybrid_contract import (  # noqa: E402
    _field_has_value,
    is_under_local_outputs,
    validate_hybrid_result,
)


DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_hybrid_benchmark")
STOP_TIERS = (
    "exact_complete",
    "dispatch_usable",
    "useful_partial",
    "unsafe_wrong",
    "missing_review_required",
)
BASELINE = {
    "load_number": {"correct": 25, "wrong": 1, "missing": 5},
    "total_carrier_rate": {"correct": 26, "wrong": 3, "missing": 2},
    "pickup_stops": {"exact": 0, "partial": 17, "wrong": 5, "missing": 3},
    "delivery_stops": {"exact": 0, "partial": 12, "wrong": 5, "missing": 4},
}


class HybridBenchmarkError(ValueError):
    """Raised when the local-only benchmark would be unsafe or invalid."""


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _file_name_or_label(result: dict[str, Any], fallback: str = "") -> str:
    return (
        _text(result.get("file_name"))
        or _text(result.get("file_name_or_label"))
        or _text(result.get("document_label"))
        or fallback
    )


def _has_evidence_ids(item: dict[str, Any]) -> bool:
    evidence_ids = item.get("evidence_ids") or []
    return isinstance(evidence_ids, list) and any(_text(eid) for eid in evidence_ids)


def _has_stop_evidence(stop: dict[str, Any]) -> bool:
    return isinstance(stop.get("evidence_page"), int) or _has_evidence_ids(stop)


def _has_field_evidence(field: dict[str, Any]) -> bool:
    return _has_evidence_ids(field)


def _confidence(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("confidence")
    try:
        if value in [None, ""]:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence_bucket(value: float | None) -> str:
    if value is None:
        return "missing"
    if value >= 0.9:
        return "gte_0_90"
    if value >= 0.8:
        return "0_80_to_0_89"
    if value >= 0.7:
        return "0_70_to_0_79"
    if value >= 0.6:
        return "0_60_to_0_69"
    return "lt_0_60"


def _is_correct_status(status: str) -> bool:
    return status in {STATUS_EXACT, STATUS_NORMALIZED_MATCH}


def _is_missing_status(status: str) -> bool:
    return status in {STATUS_MISSING, STATUS_UNLABELED}


def _stop_tier(compare_result: dict[str, Any], prediction: dict[str, Any], gold_stops: list[dict[str, Any]]) -> str:
    status = compare_result.get("status")
    if _is_correct_status(status):
        return "exact_complete"
    if status == STATUS_PARTIAL_MATCH:
        issues = set(compare_result.get("issues") or [])
        has_location = any(_text(prediction.get(key)) for key in ("city", "state", "address", "facility"))
        has_date = bool(_text(prediction.get("date")))
        has_time = bool(_text(prediction.get("time") or prediction.get("appointment_window")))
        gold_requires_time = any(
            isinstance(stop, dict) and _text(stop.get("time") or stop.get("appointment_window"))
            for stop in gold_stops or []
        )
        wrong_issues = {issue for issue in issues if issue.startswith("wrong_")}
        if wrong_issues:
            return "unsafe_wrong"
        if has_location and has_date and (has_time or not gold_requires_time):
            return "dispatch_usable"
        return "useful_partial"
    if _is_missing_status(status):
        return "missing_review_required"
    if status == STATUS_WRONG_VALUE:
        return "unsafe_wrong"
    return "unsafe_wrong"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HybridBenchmarkError(f"{path.name} must contain a JSON object")
    return payload


def _load_hybrid_results(results_dir: Path, *, allow_missing: bool) -> list[tuple[Path, dict[str, Any]]]:
    resolved = _repo_relative(results_dir)
    if not resolved.exists():
        if allow_missing:
            return []
        raise HybridBenchmarkError(f"Hybrid results directory does not exist: {results_dir}")
    files = sorted(resolved.glob("*.json"))
    if not files and not allow_missing:
        raise HybridBenchmarkError(f"No hybrid JSON files found in {results_dir}")
    return [(path, _load_json(path)) for path in files]


def _gold_indexes(labels: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    indexes = {"document_id": {}, "file_name": {}, "file_hash": {}}
    for label in labels:
        for key in indexes:
            value = _text(label.get(key))
            if value:
                indexes[key][value] = label
    return indexes


def _match_gold(result: dict[str, Any], indexes: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any] | None:
    for key in ("document_id", "file_name", "file_hash"):
        value = _text(result.get(key))
        if value and value in indexes[key]:
            return indexes[key][value]
    file_hash_prefix = _text(result.get("file_hash_prefix"))
    if file_hash_prefix:
        for full_hash, label in indexes["file_hash"].items():
            if full_hash.startswith(file_hash_prefix):
                return label
    return None


def _prediction_for_scalar(result: dict[str, Any], field_name: str) -> dict[str, Any]:
    field = (result.get("fields") or {}).get(field_name) or {}
    if not isinstance(field, dict):
        field = {"value": field}
    return {"value": field.get("value"), "confidence": field.get("confidence")}


def _compare_scalar_field(result: dict[str, Any], gold: dict[str, Any], field_name: str) -> dict[str, Any]:
    prediction = _prediction_for_scalar(result, field_name)
    gold_field = (gold.get("gold") or {}).get(field_name)
    compare_result = compare_field(field_name, prediction, gold_field)
    return {
        "field": field_name,
        "status": compare_result.get("status"),
        "issues": compare_result.get("issues") or [],
        "confidence": prediction.get("confidence"),
        "confidence_bucket": _confidence_bucket(_confidence(prediction)),
        "has_evidence": _has_field_evidence((result.get("fields") or {}).get(field_name) or {}),
    }


def _compare_stop_field(result: dict[str, Any], gold: dict[str, Any], field_name: str) -> list[dict[str, Any]]:
    fields = result.get("fields") or {}
    stops = fields.get(field_name) or []
    if not isinstance(stops, list):
        stops = []
    gold_stops = (gold.get("gold") or {}).get(field_name) or []
    if not stops:
        compare_result = compare_field(field_name, {"value": []}, gold_stops)
        return [
            {
                "field": field_name,
                "stop_index": None,
                "status": compare_result.get("status"),
                "tier": "missing_review_required",
                "issues": compare_result.get("issues") or [],
                "confidence": None,
                "confidence_bucket": "missing",
                "has_evidence": False,
                "requires_human_review": True,
                "auto_accept": False,
            }
        ]
    rows = []
    for index, stop in enumerate(stops):
        compare_result = compare_field(field_name, {"value": [stop], "confidence": stop.get("confidence")}, gold_stops)
        rows.append(
            {
                "field": field_name,
                "stop_index": stop.get("stop_index") or index + 1,
                "status": compare_result.get("status"),
                "tier": _stop_tier(compare_result, stop, gold_stops),
                "issues": compare_result.get("issues") or [],
                "confidence": stop.get("confidence"),
                "confidence_bucket": _confidence_bucket(_confidence(stop)),
                "has_evidence": _has_stop_evidence(stop),
                "requires_human_review": stop.get("requires_human_review") is True,
                "auto_accept": stop.get("auto_accept") is True,
            }
        )
    return rows


def _document_type_status(result: dict[str, Any], gold: dict[str, Any] | None) -> str:
    if not gold:
        return "missing_gold"
    predicted = _text(result.get("document_type"))
    gold_type = _text((gold.get("gold") or {}).get("document_type")) or "rate_confirmation"
    if not predicted:
        return "missing"
    if predicted == gold_type:
        return "correct"
    return "wrong"


def _empty_field_metrics() -> dict[str, dict[str, int]]:
    return {
        FIELD_LOAD_NUMBER: {"correct": 0, "wrong": 0, "missing": 0, "high_confidence_wrong": 0},
        FIELD_TOTAL_CARRIER_RATE: {"correct": 0, "wrong": 0, "missing": 0, "high_confidence_wrong": 0},
    }


def _empty_stop_metrics() -> dict[str, dict[str, int]]:
    return {
        FIELD_PICKUP_STOPS: {tier: 0 for tier in STOP_TIERS},
        FIELD_DELIVERY_STOPS: {tier: 0 for tier in STOP_TIERS},
    }


def run_hybrid_benchmark(
    *,
    hybrid_results_dir: Path,
    gold_dir: Path,
    audit: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    include_private_values_local_only: bool = False,
    strict_schema: bool = False,
    allow_missing_hybrid_results: bool = False,
    write_review_packets: bool = False,
) -> dict[str, Any]:
    if not is_under_local_outputs(output_dir, REPO_ROOT):
        raise HybridBenchmarkError("Output directory must be under .local_outputs.")
    resolved_output = _repo_relative(output_dir)
    resolved_output.mkdir(parents=True, exist_ok=True)
    labels = load_gold_labels(_repo_relative(gold_dir))
    indexes = _gold_indexes(labels)
    hybrid_results = _load_hybrid_results(hybrid_results_dir, allow_missing=allow_missing_hybrid_results)

    schema_errors: list[dict[str, Any]] = []
    document_rows: list[dict[str, Any]] = []
    field_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    field_metrics = _empty_field_metrics()
    stop_metrics = _empty_stop_metrics()
    doc_type_counts = Counter()
    review_policy = Counter()
    evidence_metrics = Counter()
    confidence_buckets = Counter()

    for path, result in hybrid_results:
        validation = validate_hybrid_result(
            result,
            strict=strict_schema,
            include_private_values_local_only=include_private_values_local_only,
        )
        if not validation.valid:
            schema_errors.append(
                {
                    "file": path.name,
                    "document_id": _text(result.get("document_id")),
                    "errors": "; ".join(validation.errors),
                }
            )
            if strict_schema:
                continue
        gold = _match_gold(result, indexes)
        doc_status = _document_type_status(result, gold)
        doc_type_counts[doc_status] += 1
        document_id = _text(result.get("document_id")) or path.stem
        file_name_or_label = _file_name_or_label(result, path.stem)
        document_type = _text(result.get("document_type"))
        doc_row = {
            "document_id": document_id,
            "file_name_or_label": file_name_or_label,
            "document_type": document_type,
            "schema_valid": validation.valid,
            "document_type_status": doc_status,
            "gold_matched": bool(gold),
            "requires_human_review": result.get("requires_human_review") is True,
            "private_local_only": result.get("private_local_only") is True,
        }
        document_rows.append(doc_row)
        if not gold:
            error_rows.append(
                {
                    "document_id": document_id,
                    "field": "document",
                    "status": "missing_gold",
                    "issue": "hybrid_result_not_matched_to_gold",
                    "recommended_action": "needs_human_review",
                }
            )
            continue
        for field_name in (FIELD_LOAD_NUMBER, FIELD_TOTAL_CARRIER_RATE):
            row = _compare_scalar_field(result, gold, field_name)
            row["document_id"] = document_id
            field_rows.append(row)
            confidence_buckets[(field_name, row["confidence_bucket"])] += 1
            if _is_correct_status(row["status"]):
                field_metrics[field_name]["correct"] += 1
            elif _is_missing_status(row["status"]):
                field_metrics[field_name]["missing"] += 1
            else:
                field_metrics[field_name]["wrong"] += 1
                if (row.get("confidence") or 0) >= 0.8:
                    field_metrics[field_name]["high_confidence_wrong"] += 1
            if _field_has_value((result.get("fields") or {}).get(field_name)) and not row["has_evidence"]:
                evidence_metrics["field_without_evidence"] += 1
                error_rows.append(
                    {
                        "document_id": document_id,
                        "field": field_name,
                        "status": row["status"],
                        "issue": "missing_evidence",
                        "recommended_action": "missing_evidence",
                    }
                )
        for field_name in (FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS):
            for row in _compare_stop_field(result, gold, field_name):
                row["document_id"] = document_id
                field_rows.append(row)
                stop_metrics[field_name][row["tier"]] += 1
                confidence_buckets[(field_name, row["confidence_bucket"])] += 1
                if row["auto_accept"]:
                    review_policy["stop_auto_accept_violation"] += 1
                    error_rows.append(
                        {
                            "document_id": document_id,
                            "field": field_name,
                            "status": row["status"],
                            "issue": "stop_auto_accept_violation",
                            "recommended_action": "reject_wrong",
                        }
                    )
                if not row["requires_human_review"]:
                    review_policy["missing_review_required_flag"] += 1
                    error_rows.append(
                        {
                            "document_id": document_id,
                            "field": field_name,
                            "status": row["status"],
                            "issue": "missing_review_required",
                            "recommended_action": "needs_human_review",
                        }
                    )
                if row["tier"] != "missing_review_required" and not row["has_evidence"]:
                    evidence_metrics["missing_evidence"] += 1
                    error_rows.append(
                        {
                            "document_id": document_id,
                            "field": field_name,
                            "status": row["status"],
                            "issue": "missing_evidence",
                            "recommended_action": "missing_evidence",
                        }
                    )
                if row["tier"] == "unsafe_wrong":
                    error_rows.append(
                        {
                            "document_id": document_id,
                            "field": field_name,
                            "status": row["status"],
                            "issue": "unsafe_wrong",
                            "recommended_action": "reject_wrong",
                        }
                    )
                if write_review_packets:
                    missing_evidence = row["tier"] != "missing_review_required" and not row["has_evidence"]
                    review_rows.append(
                        {
                            "document_id": document_id,
                            "file_name_or_label": file_name_or_label,
                            "document_type": document_type,
                            "field": field_name,
                            "stop_role": _stop_role(field_name),
                            "stop_index": row.get("stop_index") or "",
                            "status": row["tier"],
                            "review_reason": ",".join(row.get("issues") or []),
                            "evidence_status": "present" if row["has_evidence"] else "missing",
                            "confidence": row.get("confidence"),
                            "auto_accept_violation": bool(row["auto_accept"]),
                            "missing_evidence": bool(missing_evidence),
                            "recommended_action": _recommended_action(row),
                        }
                    )

    summary = {
        "schema_version": "ratecon_hybrid_benchmark_summary_v1",
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ai_model_invocation_attempted": False,
        "hybrid_result_count": len(hybrid_results),
        "gold_label_count": len(labels),
        "audit_path_supplied": bool(audit),
        "schema_error_count": len(schema_errors),
        "document_classification": {
            "rate_confirmation_correct": doc_type_counts.get("correct", 0),
            "wrong": doc_type_counts.get("wrong", 0),
            "missing": doc_type_counts.get("missing", 0),
            "missing_gold": doc_type_counts.get("missing_gold", 0),
            "non_rc_bol_pod_filtered": sum(
                1
                for _, result in hybrid_results
                if result.get("document_type") == "bol_pod"
            ),
        },
        "field_metrics": field_metrics,
        "stop_metrics": stop_metrics,
        "review_policy": dict(review_policy),
        "evidence_metrics": dict(evidence_metrics),
        "confidence_buckets": {
            f"{field}:{bucket}": count
            for (field, bucket), count in sorted(confidence_buckets.items())
        },
        "baseline": BASELINE,
    }
    summary["one_screen_summary"] = {
        "results": len(hybrid_results),
        "schema_errors": len(schema_errors),
        "error_cases": len(error_rows),
        "stop_auto_accept_violations": review_policy.get("stop_auto_accept_violation", 0),
        "missing_evidence": evidence_metrics.get("missing_evidence", 0)
        + evidence_metrics.get("field_without_evidence", 0),
        "unsafe_wrong_stops": sum(metrics.get("unsafe_wrong", 0) for metrics in stop_metrics.values()),
        "non_rc_bol_pod_filtered": sum(
            1
            for _, result in hybrid_results
            if result.get("document_type") == "bol_pod"
        ),
        "next_action": None,
    }
    summary["safety"] = {
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ai_model_invocation_attempted": False,
        "private_values_included": bool(include_private_values_local_only),
    }
    summary["error_case_examples"] = error_rows[:5]
    summary["next_action"] = _next_action(summary)
    summary["one_screen_summary"]["next_action"] = summary["next_action"]
    _write_outputs(
        resolved_output,
        summary=summary,
        document_rows=document_rows,
        field_rows=field_rows,
        error_rows=error_rows,
        schema_errors=schema_errors,
        review_rows=review_rows,
        include_private_values_local_only=include_private_values_local_only,
        write_review_packets=write_review_packets,
    )
    return summary


def _recommended_action(row: dict[str, Any]) -> str:
    if row.get("auto_accept"):
        return "reject_wrong"
    if not row.get("has_evidence"):
        return "missing_evidence"
    if row.get("tier") == "unsafe_wrong":
        return "reject_wrong"
    if row.get("tier") in {"exact_complete", "dispatch_usable", "useful_partial"}:
        return "accept_for_review_draft"
    return "needs_human_review"


def _stop_role(field_name: str) -> str:
    if field_name == FIELD_PICKUP_STOPS:
        return "pickup"
    if field_name == FIELD_DELIVERY_STOPS:
        return "delivery"
    return ""


def _next_action(summary: dict[str, Any]) -> str:
    if summary.get("schema_error_count", 0):
        return "fix_schema_errors"
    if summary.get("review_policy", {}).get("stop_auto_accept_violation", 0):
        return "remove_stop_auto_accept_flags"
    evidence = summary.get("evidence_metrics", {})
    if evidence.get("missing_evidence", 0) or evidence.get("field_without_evidence", 0):
        return "add_missing_evidence"
    unsafe_wrong = sum(
        metrics.get("unsafe_wrong", 0)
        for metrics in (summary.get("stop_metrics") or {}).values()
        if isinstance(metrics, dict)
    )
    if unsafe_wrong:
        return "review_or_reject_unsafe_wrong_stops"
    return "review_hybrid_drafts"


def _stop_metric_line(field_name: str, metrics: dict[str, int]) -> str:
    return (
        f"- {field_name}: exact {metrics.get('exact_complete', 0)} / "
        f"dispatch {metrics.get('dispatch_usable', 0)} / "
        f"partial {metrics.get('useful_partial', 0)} / "
        f"unsafe {metrics.get('unsafe_wrong', 0)} / "
        f"missing {metrics.get('missing_review_required', 0)}"
    )


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_outputs(
    output_dir: Path,
    *,
    summary: dict[str, Any],
    document_rows: list[dict[str, Any]],
    field_rows: list[dict[str, Any]],
    error_rows: list[dict[str, Any]],
    schema_errors: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
    include_private_values_local_only: bool,
    write_review_packets: bool,
) -> None:
    _write_json(output_dir / "hybrid_benchmark_summary.json", summary)
    one_screen = summary.get("one_screen_summary", {})
    safety = summary.get("safety", {})
    field_metrics = summary.get("field_metrics", {})
    stop_metrics = summary.get("stop_metrics", {})
    error_examples = summary.get("error_case_examples") or []
    report = [
        "# RateCon Hybrid Benchmark Report",
        "",
        "This local-only benchmark made no AI, cloud, OCR, model, or PDF processing calls.",
        "",
        "## One-Screen Summary",
        "",
        f"- hybrid results: {one_screen.get('results', 0)}",
        f"- schema errors: {one_screen.get('schema_errors', 0)}",
        f"- error cases: {one_screen.get('error_cases', 0)}",
        f"- missing evidence: {one_screen.get('missing_evidence', 0)}",
        f"- stop auto-accept violations: {one_screen.get('stop_auto_accept_violations', 0)}",
        f"- unsafe wrong stops: {one_screen.get('unsafe_wrong_stops', 0)}",
        f"- non-RC BOL/POD filtered: {one_screen.get('non_rc_bol_pod_filtered', 0)}",
        f"- next action: {summary.get('next_action', 'review_hybrid_drafts')}",
        "",
        "## Safety",
        "",
        f"- external API calls attempted: {safety.get('external_api_calls_attempted', False)}",
        f"- PDF processing attempted: {safety.get('pdf_processing_attempted', False)}",
        f"- AI/model invocation attempted: {safety.get('ai_model_invocation_attempted', False)}",
        f"- private values included: {safety.get('private_values_included', bool(include_private_values_local_only))}",
        "",
        "## Baseline Comparison",
        "",
        "- load_number: 25 correct / 1 wrong / 5 missing",
        (
            f"  - hybrid: {field_metrics.get(FIELD_LOAD_NUMBER, {}).get('correct', 0)} correct / "
            f"{field_metrics.get(FIELD_LOAD_NUMBER, {}).get('wrong', 0)} wrong / "
            f"{field_metrics.get(FIELD_LOAD_NUMBER, {}).get('missing', 0)} missing"
        ),
        "- total_carrier_rate: 26 correct / 3 wrong / 2 missing",
        (
            f"  - hybrid: {field_metrics.get(FIELD_TOTAL_CARRIER_RATE, {}).get('correct', 0)} correct / "
            f"{field_metrics.get(FIELD_TOTAL_CARRIER_RATE, {}).get('wrong', 0)} wrong / "
            f"{field_metrics.get(FIELD_TOTAL_CARRIER_RATE, {}).get('missing', 0)} missing"
        ),
        "- pickup stops: 0 exact / 17 partial / 5 wrong / 3 missing",
        _stop_metric_line(FIELD_PICKUP_STOPS, stop_metrics.get(FIELD_PICKUP_STOPS, {})),
        "- delivery stops: 0 exact / 12 partial / 5 wrong / 4 missing",
        _stop_metric_line(FIELD_DELIVERY_STOPS, stop_metrics.get(FIELD_DELIVERY_STOPS, {})),
        "",
        "## Error Case Examples",
        "",
    ]
    if error_examples:
        for row in error_examples:
            report.append(
                f"- {row.get('document_id', '')} {row.get('field', '')}: "
                f"{row.get('issue', '')} -> {row.get('recommended_action', '')}"
            )
    else:
        report.append("- none")
    report.extend(
        [
            "",
            "## Next Action",
            "",
            f"- {summary.get('next_action', 'review_hybrid_drafts')}",
        ]
    )
    (output_dir / "hybrid_benchmark_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    _write_csv(
        output_dir / "hybrid_field_metrics.csv",
        field_rows,
        [
            "document_id",
            "field",
            "stop_index",
            "status",
            "tier",
            "issues",
            "confidence",
            "confidence_bucket",
            "has_evidence",
            "requires_human_review",
            "auto_accept",
        ],
    )
    _write_csv(
        output_dir / "hybrid_document_metrics.csv",
        document_rows,
        [
            "document_id",
            "file_name_or_label",
            "document_type",
            "schema_valid",
            "document_type_status",
            "gold_matched",
            "requires_human_review",
            "private_local_only",
        ],
    )
    _write_csv(
        output_dir / "hybrid_error_cases.csv",
        error_rows,
        ["document_id", "field", "status", "issue", "recommended_action"],
    )
    _write_csv(output_dir / "hybrid_schema_errors.csv", schema_errors, ["file", "document_id", "errors"])
    if write_review_packets:
        _write_json(output_dir / "hybrid_review_packet.json", {"items": review_rows})
        _write_csv(
            output_dir / "hybrid_review_items.csv",
            review_rows,
            [
                "document_id",
                "file_name_or_label",
                "document_type",
                "field",
                "stop_role",
                "stop_index",
                "status",
                "review_reason",
                "evidence_status",
                "confidence",
                "auto_accept_violation",
                "missing_evidence",
                "recommended_action",
            ],
        )
        lines = ["# Hybrid Review Packet", ""]
        for row in review_rows:
            lines.append(
                f"- {row['document_id']} {row['field']}[{row.get('stop_index', '')}]: "
                f"{row['recommended_action']} ({row['status']})"
            )
        (output_dir / "hybrid_review_packet.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark local-only RateCon hybrid result JSON files.")
    parser.add_argument("--hybrid-results-dir", type=Path, required=True)
    parser.add_argument("--gold-dir", type=Path, required=True)
    parser.add_argument("--audit", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    parser.add_argument("--strict-schema", action="store_true")
    parser.add_argument("--allow-missing-hybrid-results", action="store_true")
    parser.add_argument("--write-review-packets", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required for local private benchmarks")
    summary = run_hybrid_benchmark(
        hybrid_results_dir=args.hybrid_results_dir,
        gold_dir=args.gold_dir,
        audit=args.audit,
        output_dir=args.output_dir,
        include_private_values_local_only=args.include_private_values_local_only,
        strict_schema=args.strict_schema,
        allow_missing_hybrid_results=args.allow_missing_hybrid_results,
        write_review_packets=args.write_review_packets,
    )
    print("RateCon hybrid benchmark summary")
    print(f"hybrid_result_count: {summary['hybrid_result_count']}")
    print(f"schema_error_count: {summary['schema_error_count']}")
    print("external_api_calls_attempted: False")
    print("pdf_processing_attempted: False")
    print("ai_model_invocation_attempted: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
