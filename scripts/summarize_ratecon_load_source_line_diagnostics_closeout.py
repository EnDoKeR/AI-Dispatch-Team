"""Summarize RateCon load source-line diagnostics closeout readiness.

This local-only tool reads existing diagnostics, static audit, and aggregate
gate outputs. It does not run extraction, private measurement, PDF processing,
OCR, Google, or model/cloud services. Default reports redact private values.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


status_closed_actionable = "load_source_line_diagnostics_closed_actionable"
status_closed_known_debt = "load_source_line_diagnostics_closed_with_known_debt"
status_incomplete_detail = "load_source_line_diagnostics_incomplete_detail_unavailable"
status_failed_gate = "load_source_line_diagnostics_failed_required_gate"
status_private_baseline_skipped = "load_source_line_diagnostics_private_baseline_skipped"
status_not_ready = "load_source_line_diagnostics_not_ready_for_experiment"

dominance_threshold = 0.5

forbidden_private_markers = (
    ".gold.json",
    "api_key",
    "secret",
    "service account",
    "google token",
    "raw extracted",
    "private pdf",
    "data/private_ratecons",
)

required_repo_gate_paths = (
    "tests/test_ratecon_selected_load_regression_harness.py",
    "tests/helpers/ratecon_selected_load_regression.py",
    "tests/fixtures/ratecon_selected_load_regression/selected_load_cases.json",
    "scripts/compare_ratecon_private_selected_load_aggregates.py",
    "tests/test_compare_ratecon_private_selected_load_aggregates.py",
    "scripts/create_ratecon_load_source_line_diagnostics.py",
    "tests/test_create_ratecon_load_source_line_diagnostics.py",
)

required_fixture_paths = (
    "tests/fixtures/ratecon_load_source_line_diagnostics/table_neighbor_wrong_cell",
    "tests/fixtures/ratecon_load_source_line_diagnostics/nearby_row_wrong_pair",
    "tests/fixtures/ratecon_load_source_line_diagnostics/gold_absent_from_candidates",
    "tests/fixtures/ratecon_load_source_line_diagnostics/gold_present_not_selected",
)

required_doc_paths = (
    "docs/ratecon_load_identifier_ownership_v1.md",
    "docs/ratecon_load_source_line_evidence_diagnostics_v1.md",
    "docs/MODULE_MAP.md",
)

known_debt_buckets = {
    "selected_table_neighbor_wrong_cell",
    "selected_nearby_row_wrong_pair",
    "selected_footer_or_barcode_noise",
    "selected_reference_number_noise",
    "selected_po_number_noise",
    "selected_pro_number_noise",
    "selected_bol_number_noise",
    "ambiguous_multiple_load_ids",
    "duplicate_same_value_candidates",
    "layout_ordering_ambiguous",
    "text_extraction_ordering_ambiguous",
}

blocking_detail_buckets = {
    "candidate_source_line_unavailable",
    "candidate_page_line_unavailable",
    "evaluator_detail_unavailable",
}


class closeout_error(ValueError):
    """Raised for safe user-facing closeout failures."""


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize RateCon load source-line diagnostics closeout readiness."
    )
    parser.add_argument("--diagnostics-dir", required=True)
    parser.add_argument("--ownership-audit-dir", required=True)
    parser.add_argument("--source-line-audit-dir", required=True)
    parser.add_argument("--aggregate-gate-dir", required=True)
    parser.add_argument("--detail-inventory-dir")
    parser.add_argument("--generated-resolver-provenance-dir")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confirm-local-audit-run", action="store_true")
    return parser.parse_args(argv)


def _resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _is_under_local_outputs(path: Path) -> bool:
    return ".local_outputs" in path.parts


def _require_output_under_local_outputs(path: Path) -> Path:
    resolved = path.resolve()
    if not _is_under_local_outputs(resolved):
        raise closeout_error("output-dir must be inside .local_outputs")
    return resolved


def _read_json_if_present(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        return {}, "missing"
    text = path.read_text(encoding="utf-8")
    lower = text.lower()
    hits = [marker for marker in forbidden_private_markers if marker in lower]
    if hits:
        raise closeout_error(f"input contains forbidden private markers: {path.name}: {hits}")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise closeout_error(f"expected JSON object at {path}")
    return payload, "present"


def _read_csv_if_present(path: Path) -> tuple[list[dict[str, str]], str]:
    if not path.exists():
        return [], "missing"
    text = path.read_text(encoding="utf-8")
    lower = text.lower()
    hits = [marker for marker in forbidden_private_markers if marker in lower]
    if hits:
        raise closeout_error(f"input contains forbidden private markers: {path.name}: {hits}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)], "present"


def _to_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _diagnostics_summary(diagnostics_dir: Path) -> dict[str, Any]:
    payload, status = _read_json_if_present(
        diagnostics_dir / "load_source_line_diagnostics_summary.json"
    )
    summary = dict(payload.get("summary") or {}) if payload else {}
    rows, rows_status = _read_csv_if_present(diagnostics_dir / "load_source_line_error_cases.csv")
    bucket_counts = {
        str(key): _to_int(value)
        for key, value in dict(summary.get("diagnostic_bucket_counts") or {}).items()
    }
    document_count = _to_int(summary.get("document_count"), len(rows))
    if not document_count and rows:
        document_count = len(rows)
    known_debt_count = _to_int(
        summary.get("known_debt_count"),
        sum(bucket_counts.get(bucket, 0) for bucket in known_debt_buckets),
    )
    source_line_unavailable_count = sum(
        bucket_counts.get(bucket, 0) for bucket in blocking_detail_buckets
    )
    unknown_count = bucket_counts.get("unknown", 0)
    detail_status = str(summary.get("detail_status") or ("missing" if status == "missing" else "available"))
    return {
        "status": status,
        "path": str(diagnostics_dir),
        "row_status": rows_status,
        "detail_status": detail_status,
        "document_count": document_count,
        "diagnostic_bucket_counts": bucket_counts,
        "known_debt_count": known_debt_count,
        "source_line_unavailable_count": source_line_unavailable_count,
        "unknown_count": unknown_count,
        "source_line_unavailable_ratio": (
            source_line_unavailable_count / document_count if document_count else 0.0
        ),
        "unknown_ratio": unknown_count / document_count if document_count else 0.0,
        "covered_fixture_bucket_count": _to_int(summary.get("covered_fixture_bucket_count")),
        "expected_failure_fixture_nonzero_count": _to_int(
            summary.get("expected_failure_fixture_nonzero_count")
        ),
        "known_debt_only": _as_bool(summary.get("known_debt_only")),
        "private_baseline_skipped": _as_bool(summary.get("private_baseline_skipped")),
        "private_values_included": _as_bool(summary.get("private_values_included")),
        "values_redacted": not _as_bool(summary.get("private_values_included")),
        "pdf_processing_attempted": _as_bool(summary.get("pdf_processing_attempted")),
        "ocr_attempted": _as_bool(summary.get("ocr_attempted")),
        "google_called": _as_bool(summary.get("google_called")),
        "model_or_cloud_called": _as_bool(summary.get("model_or_cloud_called")),
        "private_measurement_run": _as_bool(summary.get("private_measurement_run")),
    }


def _ownership_audit_summary(audit_dir: Path) -> dict[str, Any]:
    payload, status = _read_json_if_present(audit_dir / "load_identifier_ownership_summary.json")
    return {
        "status": status if status == "present" else "skipped_missing_optional_dir",
        "path": str(audit_dir),
        "module_count": _to_int(payload.get("module_count")),
        "symbol_count": _to_int(payload.get("symbol_count")),
        "risk_finding_count": _to_int(payload.get("risk_finding_count")),
    }


def _source_line_audit_summary(audit_dir: Path) -> dict[str, Any]:
    payload, status = _read_json_if_present(audit_dir / "load_source_line_evidence_summary.json")
    return {
        "status": status if status == "present" else "skipped_missing_optional_dir",
        "path": str(audit_dir),
        "module_count": _to_int(payload.get("module_count")),
        "symbol_count": _to_int(payload.get("symbol_count")),
        "reason_constant_count": _to_int(payload.get("reason_constant_count")),
        "risk_finding_count": _to_int(payload.get("risk_finding_count")),
    }


def _aggregate_gate_summary(gate_dir: Path) -> dict[str, Any]:
    payload, status = _read_json_if_present(
        gate_dir / "private_selected_load_aggregate_compare_summary.json"
    )
    gate = dict(payload.get("gate") or {}) if payload else {}
    summary = dict(payload.get("summary") or {}) if payload else {}
    delta = dict(summary.get("delta") or {})
    return {
        "status": status,
        "path": str(gate_dir),
        "gate_passed": _as_bool(gate.get("passed")) if payload else False,
        "selected_value_comparison_status": gate.get(
            "selected_value_comparison_status",
            "missing",
        ),
        "selected_value_changed_count": _to_int(summary.get("selected_value_changed_count")),
        "wrong_count_delta": _to_int(delta.get("wrong_count")),
        "high_confidence_wrong_delta": _to_int(delta.get("high_confidence_wrong_count")),
        "table_neighbor_wrong_delta": _to_int(
            delta.get("selected_table_neighbor_wrong_cell_count")
        ),
        "nearby_row_wrong_delta": _to_int(
            delta.get("selected_nearby_row_wrong_pair_count")
        ),
        "missing_count_delta": _to_int(delta.get("missing_count")),
        "private_values_included": _as_bool(gate.get("private_values_included")),
        "private_measurement_run": _as_bool(gate.get("private_measurement_run")),
        "pdf_processing_attempted": _as_bool(gate.get("pdf_processing_attempted")),
        "ocr_attempted": _as_bool(gate.get("ocr_attempted")),
        "google_called": _as_bool(gate.get("google_called")),
        "model_or_cloud_called": _as_bool(gate.get("model_or_cloud_called")),
    }


def _detail_inventory_summary(detail_dir: Path | None) -> dict[str, Any]:
    if detail_dir is None:
        return {
            "status": "skipped_not_requested",
            "path": "",
            "detail_input_status": "skipped",
            "candidate_detail_row_count": 0,
            "complete_source_detail_count": 0,
            "missing_page_line_count": 0,
            "missing_source_count": 0,
            "dropped_detail_count": 0,
            "unknown_caused_by_missing_detail_count": 0,
            "serialization_sidecar_status": "skipped_not_requested",
            "serialization_complete_detail_count": 0,
            "serialization_loss_bucket_counts": {},
            "serialization_loss_dominates": False,
            "adapter_roundtrip_status_counts": {},
            "adapter_detail_preserved_count": 0,
            "adapter_detail_lost_count": 0,
            "adapter_loss_blocks_readiness": False,
            "generated_resolver_sidecar_status": "skipped_not_requested",
            "generated_resolver_current_artifacts_status": "skipped",
            "generated_candidate_detail_available_count": 0,
            "resolver_visible_detail_available_count": 0,
            "generated_resolver_complete_roundtrip_count": 0,
            "generated_resolver_blocks_readiness": False,
            "missing_page_line_ratio": 0.0,
            "missing_source_ratio": 0.0,
            "unknown_caused_by_missing_detail_ratio": 0.0,
            "private_values_included": False,
            "values_redacted": True,
        }
    payload, status = _read_json_if_present(
        detail_dir / "load_source_line_detail_inventory_summary.json"
    )
    summary = dict(payload.get("summary") or {}) if payload else {}
    candidate_count = _to_int(summary.get("candidate_detail_row_count"))
    missing_page_line_count = _to_int(summary.get("missing_page_line_count"))
    missing_source_count = _to_int(summary.get("missing_source_count"))
    unknown_missing_count = _to_int(summary.get("unknown_caused_by_missing_detail_count"))
    serialization_counts = {
        str(key): _to_int(value)
        for key, value in dict(summary.get("serialization_loss_bucket_counts") or {}).items()
    }
    serialization_complete_count = _to_int(summary.get("serialization_complete_detail_count"))
    serialization_total = sum(serialization_counts.values())
    serialization_loss_count = max(serialization_total - serialization_complete_count, 0)
    adapter_counts = {
        str(key): _to_int(value)
        for key, value in dict(summary.get("adapter_roundtrip_status_counts") or {}).items()
    }
    adapter_lost_count = _to_int(summary.get("adapter_detail_lost_count"))
    generated_resolver_status = str(
        summary.get("generated_resolver_current_artifacts_status") or "skipped"
    )
    generated_resolver_sidecar_status = str(
        summary.get("generated_resolver_sidecar_status") or "skipped_missing_optional_dir"
    )
    generated_detail_available_count = _to_int(
        summary.get("generated_candidate_detail_available_count")
    )
    resolver_detail_available_count = _to_int(
        summary.get("resolver_visible_detail_available_count")
    )
    generated_resolver_complete_count = _to_int(
        summary.get("generated_resolver_complete_roundtrip_count")
    )
    return {
        "status": status if status == "present" else "skipped_missing_optional_dir",
        "path": str(detail_dir),
        "detail_input_status": str(summary.get("detail_input_status") or "missing"),
        "candidate_detail_row_count": candidate_count,
        "complete_source_detail_count": _to_int(summary.get("complete_source_detail_count")),
        "missing_page_line_count": missing_page_line_count,
        "missing_source_count": missing_source_count,
        "dropped_detail_count": _to_int(summary.get("dropped_detail_count")),
        "unknown_caused_by_missing_detail_count": unknown_missing_count,
        "serialization_sidecar_status": str(
            summary.get("serialization_sidecar_status") or "skipped_missing_optional_dir"
        ),
        "serialization_complete_detail_count": serialization_complete_count,
        "serialization_loss_bucket_counts": serialization_counts,
        "serialization_loss_dominates": (
            serialization_total > 0
            and (serialization_loss_count / serialization_total) >= dominance_threshold
        ),
        "adapter_roundtrip_status_counts": adapter_counts,
        "adapter_detail_preserved_count": _to_int(
            summary.get("adapter_detail_preserved_count")
        ),
        "adapter_detail_lost_count": adapter_lost_count,
        "adapter_loss_blocks_readiness": adapter_lost_count > 0,
        "generated_resolver_sidecar_status": generated_resolver_sidecar_status,
        "generated_resolver_current_artifacts_status": generated_resolver_status,
        "generated_candidate_detail_available_count": generated_detail_available_count,
        "resolver_visible_detail_available_count": resolver_detail_available_count,
        "generated_resolver_complete_roundtrip_count": generated_resolver_complete_count,
        "generated_resolver_blocks_readiness": (
            generated_resolver_sidecar_status == "present"
            and (
                generated_resolver_status == "current_like_eval_audit_only_unmeasurable"
                or generated_detail_available_count == 0
                or resolver_detail_available_count == 0
            )
        ),
        "missing_page_line_ratio": (
            missing_page_line_count / candidate_count if candidate_count else 0.0
        ),
        "missing_source_ratio": (
            missing_source_count / candidate_count if candidate_count else 0.0
        ),
        "unknown_caused_by_missing_detail_ratio": (
            unknown_missing_count / candidate_count if candidate_count else 0.0
        ),
        "private_values_included": _as_bool(summary.get("private_values_included")),
        "values_redacted": not _as_bool(summary.get("private_values_included")),
    }


def _generated_resolver_provenance_summary(sidecar_dir: Path | None) -> dict[str, Any]:
    if sidecar_dir is None:
        return {
            "generated_resolver_sidecar_status": "skipped_not_requested",
            "generated_resolver_current_artifacts_status": "skipped",
            "generated_candidate_detail_available_count": 0,
            "resolver_visible_detail_available_count": 0,
            "generated_resolver_complete_roundtrip_count": 0,
            "generated_resolver_blocks_readiness": False,
        }
    payload, status = _read_json_if_present(
        sidecar_dir / "load_generated_resolver_provenance_summary.json"
    )
    summary = dict(payload.get("summary") or {}) if payload else {}
    generated_detail_available_count = _to_int(
        summary.get("generated_candidate_detail_available_count")
    )
    resolver_detail_available_count = _to_int(
        summary.get("resolver_visible_detail_available_count")
    )
    current_status = str(summary.get("current_artifacts_status") or "missing")
    complete_roundtrip_count = _to_int(summary.get("complete_roundtrip_count"))
    return {
        "generated_resolver_sidecar_status": (
            status if status == "present" else "skipped_missing_optional_dir"
        ),
        "generated_resolver_current_artifacts_status": current_status,
        "generated_candidate_detail_available_count": generated_detail_available_count,
        "resolver_visible_detail_available_count": resolver_detail_available_count,
        "generated_resolver_complete_roundtrip_count": complete_roundtrip_count,
        "generated_resolver_blocks_readiness": (
            status == "present"
            and (
                current_status == "current_like_eval_audit_only_unmeasurable"
                or generated_detail_available_count == 0
                or resolver_detail_available_count == 0
            )
        ),
    }


def _merge_generated_resolver_into_detail(
    detail_inventory: dict[str, Any],
    generated_resolver: dict[str, Any],
) -> dict[str, Any]:
    if generated_resolver["generated_resolver_sidecar_status"] == "skipped_not_requested":
        return detail_inventory
    merged = dict(detail_inventory)
    merged.update(generated_resolver)
    return merged


def _repo_evidence(repo_root: Path) -> dict[str, Any]:
    gates = {path: (repo_root / path).exists() for path in required_repo_gate_paths}
    fixtures = {path: (repo_root / path).exists() for path in required_fixture_paths}
    docs = {path: (repo_root / path).exists() for path in required_doc_paths}
    return {
        "gates": gates,
        "fixtures": fixtures,
        "docs": docs,
        "all_required_gate_files_present": all(gates.values()),
        "all_required_fixture_dirs_present": all(fixtures.values()),
        "all_required_docs_present": all(docs.values()),
    }


def _detail_dominates(diagnostics: dict[str, Any]) -> bool:
    return (
        diagnostics["detail_status"] == "detail_unavailable"
        or diagnostics["source_line_unavailable_ratio"] >= dominance_threshold
    )


def _unknown_dominates(diagnostics: dict[str, Any]) -> bool:
    return diagnostics["unknown_ratio"] >= dominance_threshold


def _detail_inventory_blocks_readiness(detail_inventory: dict[str, Any]) -> bool:
    if detail_inventory["status"] != "present":
        return False
    if detail_inventory["detail_input_status"] == "detail_input_unavailable":
        return True
    return (
        detail_inventory["missing_page_line_ratio"] >= dominance_threshold
        or detail_inventory["missing_source_ratio"] >= dominance_threshold
        or detail_inventory["unknown_caused_by_missing_detail_ratio"] >= dominance_threshold
        or detail_inventory["serialization_loss_dominates"]
        or detail_inventory["adapter_loss_blocks_readiness"]
        or detail_inventory["generated_resolver_blocks_readiness"]
    )


def _success_criteria(
    diagnostics: dict[str, Any],
    gate: dict[str, Any],
    repo: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "criterion": "selected_load_regression_harness_exists",
            "passed": repo["all_required_gate_files_present"],
            "required": True,
            "evidence": json.dumps(repo["gates"], sort_keys=True),
        },
        {
            "criterion": "key_source_line_diagnostic_fixtures_exist",
            "passed": repo["all_required_fixture_dirs_present"],
            "required": True,
            "evidence": json.dumps(repo["fixtures"], sort_keys=True),
        },
        {
            "criterion": "load_source_line_diagnostics_available",
            "passed": diagnostics["status"] == "present" or diagnostics["private_baseline_skipped"],
            "required": True,
            "evidence": (
                f"detail_status={diagnostics['detail_status']} "
                f"document_count={diagnostics['document_count']}"
            ),
        },
        {
            "criterion": "private_selected_load_aggregate_gate_passes",
            "passed": gate["status"] == "present" and gate["gate_passed"],
            "required": True,
            "evidence": (
                f"wrong_delta={gate['wrong_count_delta']} "
                f"high_conf_delta={gate['high_confidence_wrong_delta']} "
                f"table_neighbor_delta={gate['table_neighbor_wrong_delta']}"
            ),
        },
        {
            "criterion": "required_ownership_docs_present",
            "passed": repo["all_required_docs_present"],
            "required": True,
            "evidence": json.dumps(repo["docs"], sort_keys=True),
        },
        {
            "criterion": "no_private_runtime_side_effects_reported",
            "passed": not any(
                [
                    diagnostics["private_values_included"],
                    diagnostics["pdf_processing_attempted"],
                    diagnostics["ocr_attempted"],
                    diagnostics["google_called"],
                    diagnostics["model_or_cloud_called"],
                    diagnostics["private_measurement_run"],
                    gate["private_values_included"],
                    gate["private_measurement_run"],
                    gate["pdf_processing_attempted"],
                    gate["ocr_attempted"],
                    gate["google_called"],
                    gate["model_or_cloud_called"],
                ]
            ),
            "required": True,
            "evidence": "diagnostics/gate side-effect flags are false",
        },
    ]


def _readiness_rows(
    diagnostics: dict[str, Any],
    gate: dict[str, Any],
    source_line_audit: dict[str, Any],
    detail_inventory: dict[str, Any],
    repo: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "readiness_check": "source_line_detail_available",
            "passed": not _detail_dominates(diagnostics),
            "blocking": True,
            "evidence": (
                f"detail_status={diagnostics['detail_status']} "
                f"source_line_unavailable_ratio={diagnostics['source_line_unavailable_ratio']:.3f}"
            ),
        },
        {
            "readiness_check": "unknown_bucket_not_dominant",
            "passed": not _unknown_dominates(diagnostics),
            "blocking": True,
            "evidence": f"unknown_ratio={diagnostics['unknown_ratio']:.3f}",
        },
        {
            "readiness_check": "aggregate_gate_same_output_available",
            "passed": gate["status"] == "present" and gate["gate_passed"],
            "blocking": True,
            "evidence": f"gate_passed={gate['gate_passed']}",
        },
        {
            "readiness_check": "table_and_nearby_fixtures_present",
            "passed": repo["all_required_fixture_dirs_present"],
            "blocking": True,
            "evidence": json.dumps(repo["fixtures"], sort_keys=True),
        },
        {
            "readiness_check": "source_line_static_audit_has_no_risk_findings",
            "passed": (
                source_line_audit["status"] != "present"
                or source_line_audit["risk_finding_count"] == 0
            ),
            "blocking": False,
            "evidence": (
                f"status={source_line_audit['status']} "
                f"risk_finding_count={source_line_audit['risk_finding_count']}"
            ),
        },
        {
            "readiness_check": "detail_inventory_not_dominated_by_missing_detail",
            "passed": not _detail_inventory_blocks_readiness(detail_inventory),
            "blocking": detail_inventory["status"] == "present",
            "evidence": (
                f"status={detail_inventory['status']} "
                f"missing_page_line_ratio={detail_inventory['missing_page_line_ratio']:.3f} "
                f"missing_source_ratio={detail_inventory['missing_source_ratio']:.3f} "
                f"unknown_caused_by_missing_detail_ratio={detail_inventory['unknown_caused_by_missing_detail_ratio']:.3f} "
                f"serialization_sidecar_status={detail_inventory['serialization_sidecar_status']} "
                f"serialization_loss_dominates={detail_inventory['serialization_loss_dominates']} "
                f"adapter_detail_lost_count={detail_inventory['adapter_detail_lost_count']} "
                f"generated_resolver_status={detail_inventory['generated_resolver_current_artifacts_status']}"
            ),
        },
    ]


def _known_debt_rows(diagnostics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for bucket in sorted(known_debt_buckets):
        count = diagnostics["diagnostic_bucket_counts"].get(bucket, 0)
        if count:
            rows.append(
                {
                    "bucket": bucket,
                    "count": count,
                    "known_debt": True,
                    "detail": "Classified for evidence-quality review only; behavior remains pinned.",
                }
            )
    if rows:
        return rows
    return [
        {
            "bucket": "",
            "count": 0,
            "known_debt": False,
            "detail": "No known-debt diagnostic buckets reported by the closeout input.",
        }
    ]


def _gate_inventory(
    diagnostics: dict[str, Any],
    gate: dict[str, Any],
    ownership_audit: dict[str, Any],
    source_line_audit: dict[str, Any],
    detail_inventory: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "gate": "load_source_line_diagnostics",
            "status": diagnostics["status"],
            "passed": diagnostics["status"] == "present" or diagnostics["private_baseline_skipped"],
            "evidence": (
                f"document_count={diagnostics['document_count']} "
                f"detail_status={diagnostics['detail_status']}"
            ),
        },
        {
            "gate": "private_selected_load_aggregate_same_output",
            "status": gate["status"],
            "passed": gate["status"] == "present" and gate["gate_passed"],
            "evidence": (
                f"selected_value_changed_count={gate['selected_value_changed_count']} "
                f"wrong_delta={gate['wrong_count_delta']}"
            ),
        },
        {
            "gate": "load_identifier_ownership_audit_optional",
            "status": ownership_audit["status"],
            "passed": (
                ownership_audit["status"] != "present"
                or ownership_audit["risk_finding_count"] == 0
            ),
            "evidence": f"risk_finding_count={ownership_audit['risk_finding_count']}",
        },
        {
            "gate": "load_source_line_static_audit_optional",
            "status": source_line_audit["status"],
            "passed": (
                source_line_audit["status"] != "present"
                or source_line_audit["risk_finding_count"] == 0
            ),
            "evidence": f"risk_finding_count={source_line_audit['risk_finding_count']}",
        },
        {
            "gate": "load_source_line_detail_inventory_optional",
            "status": detail_inventory["status"],
            "passed": not _detail_inventory_blocks_readiness(detail_inventory),
            "evidence": (
                f"candidate_detail_row_count={detail_inventory['candidate_detail_row_count']} "
                f"missing_page_line_count={detail_inventory['missing_page_line_count']} "
                f"missing_source_count={detail_inventory['missing_source_count']} "
                f"dropped_detail_count={detail_inventory['dropped_detail_count']} "
                f"serialization_complete_detail_count={detail_inventory['serialization_complete_detail_count']} "
                f"adapter_detail_lost_count={detail_inventory['adapter_detail_lost_count']} "
                f"generated_resolver_sidecar_status={detail_inventory['generated_resolver_sidecar_status']} "
                f"generated_resolver_current_artifacts_status={detail_inventory['generated_resolver_current_artifacts_status']}"
            ),
        },
    ]


def _closeout_status(
    diagnostics: dict[str, Any],
    gate: dict[str, Any],
    detail_inventory: dict[str, Any],
    criteria: list[dict[str, Any]],
) -> str:
    if diagnostics["private_baseline_skipped"] or diagnostics["status"] == "missing":
        return status_private_baseline_skipped
    if gate["status"] != "present" or not gate["gate_passed"]:
        return status_failed_gate
    required_failed = [row for row in criteria if row["required"] and not row["passed"]]
    if required_failed:
        return status_failed_gate
    if _detail_inventory_blocks_readiness(detail_inventory):
        return status_incomplete_detail
    if _detail_dominates(diagnostics):
        return status_incomplete_detail
    if _unknown_dominates(diagnostics):
        return status_not_ready
    if diagnostics["known_debt_only"] or (
        diagnostics["known_debt_count"] and diagnostics["covered_fixture_bucket_count"] < 4
    ):
        return status_closed_known_debt
    if diagnostics["covered_fixture_bucket_count"] >= 4:
        return status_closed_actionable
    if diagnostics["known_debt_count"]:
        return status_closed_known_debt
    return status_not_ready


def _next_actions(status: str) -> list[dict[str, Any]]:
    rows = [
        {
            "action": "preserve_current_load_behavior",
            "priority": "required",
            "detail": "Do not change selected load output, candidate generation, resolver ranking, source labels, confidence values, schemas, or evaluator statuses in closeout work.",
        },
        {
            "action": "run_selected_load_harness_before_experiments",
            "priority": "required",
            "detail": "Use the selected-load regression harness and private selected-load aggregate gate before any behavior experiment.",
        },
        {
            "action": "keep_experiments_shadow_only",
            "priority": "required",
            "detail": "Any table-neighbor or nearby-row evidence experiment must be shadow-only until separately approved.",
        },
    ]
    if status in {status_incomplete_detail, status_not_ready}:
        rows.insert(
            0,
            {
                "action": "enrich_source_line_detail_first",
                "priority": "required",
                "detail": "Diagnostics are not actionable enough for behavior experiments because detail is unavailable or unknown buckets dominate.",
            },
        )
    if status == status_failed_gate:
        rows.insert(
            0,
            {
                "action": "resolve_required_gate_failure",
                "priority": "required",
                "detail": "Do not proceed to load evidence experiments until the aggregate gate and required closeout gates pass.",
            },
        )
    if status == status_private_baseline_skipped:
        rows.append(
            {
                "action": "optional_private_baseline",
                "priority": "optional",
                "detail": "Run local diagnostics against existing private eval/audit outputs only when explicitly available; do not run private measurement from closeout.",
            },
        )
    return rows


def summarize_closeout(
    diagnostics_dir: Path,
    ownership_audit_dir: Path,
    source_line_audit_dir: Path,
    aggregate_gate_dir: Path,
    detail_inventory_dir: Path | None = None,
    generated_resolver_provenance_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    repo_root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    diagnostics = _diagnostics_summary(diagnostics_dir)
    ownership_audit = _ownership_audit_summary(ownership_audit_dir)
    source_line_audit = _source_line_audit_summary(source_line_audit_dir)
    aggregate_gate = _aggregate_gate_summary(aggregate_gate_dir)
    detail_inventory = _merge_generated_resolver_into_detail(
        _detail_inventory_summary(detail_inventory_dir),
        _generated_resolver_provenance_summary(generated_resolver_provenance_dir),
    )
    repo = _repo_evidence(repo_root)
    criteria = _success_criteria(diagnostics, aggregate_gate, repo)
    readiness = _readiness_rows(
        diagnostics,
        aggregate_gate,
        source_line_audit,
        detail_inventory,
        repo,
    )
    status = _closeout_status(diagnostics, aggregate_gate, detail_inventory, criteria)
    return {
        "schema_version": "ratecon_load_source_line_diagnostics_closeout_v1",
        "closeout_status": status,
        "experiment_readiness_status": status,
        "diagnostics": diagnostics,
        "ownership_audit": ownership_audit,
        "source_line_audit": source_line_audit,
        "aggregate_gate": aggregate_gate,
        "detail_inventory": detail_inventory,
        "repo_evidence": repo,
        "success_criteria": criteria,
        "readiness": readiness,
        "known_debt": _known_debt_rows(diagnostics),
        "gate_inventory": _gate_inventory(
            diagnostics,
            aggregate_gate,
            ownership_audit,
            source_line_audit,
            detail_inventory,
        ),
        "next_actions": _next_actions(status),
        "private_values_redacted": True,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
        "private_measurement_run": False,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_dict_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    diagnostics = summary["diagnostics"]
    gate = summary["aggregate_gate"]
    detail_inventory = summary["detail_inventory"]
    lines = [
        "# RateCon Load Source-Line Diagnostics Closeout",
        "",
        "This local-only closeout reads existing diagnostics, audit, and gate outputs only.",
        "",
        f"- closeout_status: {summary['closeout_status']}",
        f"- experiment_readiness_status: {summary['experiment_readiness_status']}",
        f"- diagnostic_document_count: {diagnostics['document_count']}",
        f"- detail_status: {diagnostics['detail_status']}",
        f"- source_line_unavailable_ratio: {diagnostics['source_line_unavailable_ratio']:.3f}",
        f"- unknown_ratio: {diagnostics['unknown_ratio']:.3f}",
        f"- aggregate_gate_passed: {gate['gate_passed']}",
        f"- detail_inventory_status: {detail_inventory['status']}",
        f"- detail_inventory_candidate_detail_row_count: {detail_inventory['candidate_detail_row_count']}",
        f"- detail_inventory_complete_source_detail_count: {detail_inventory['complete_source_detail_count']}",
        f"- detail_inventory_missing_page_line_count: {detail_inventory['missing_page_line_count']}",
        f"- detail_inventory_missing_source_count: {detail_inventory['missing_source_count']}",
        f"- detail_inventory_dropped_detail_count: {detail_inventory['dropped_detail_count']}",
        f"- detail_inventory_unknown_caused_by_missing_detail_count: {detail_inventory['unknown_caused_by_missing_detail_count']}",
        f"- detail_inventory_serialization_sidecar_status: {detail_inventory['serialization_sidecar_status']}",
        f"- detail_inventory_serialization_complete_detail_count: {detail_inventory['serialization_complete_detail_count']}",
        f"- detail_inventory_serialization_loss_dominates: {detail_inventory['serialization_loss_dominates']}",
        f"- detail_inventory_adapter_detail_preserved_count: {detail_inventory['adapter_detail_preserved_count']}",
        f"- detail_inventory_adapter_detail_lost_count: {detail_inventory['adapter_detail_lost_count']}",
        f"- detail_inventory_adapter_loss_blocks_readiness: {detail_inventory['adapter_loss_blocks_readiness']}",
        f"- detail_inventory_generated_resolver_sidecar_status: {detail_inventory['generated_resolver_sidecar_status']}",
        f"- detail_inventory_generated_resolver_current_artifacts_status: {detail_inventory['generated_resolver_current_artifacts_status']}",
        f"- detail_inventory_generated_candidate_detail_available_count: {detail_inventory['generated_candidate_detail_available_count']}",
        f"- detail_inventory_resolver_visible_detail_available_count: {detail_inventory['resolver_visible_detail_available_count']}",
        "- private_values_redacted: True",
        "- pdf_processing_attempted: False",
        "- ocr_attempted: False",
        "- google_called: False",
        "- model_or_cloud_called: False",
        "- private_measurement_run: False",
        "",
        "## Diagnostic Buckets",
        "",
    ]
    for bucket, count in sorted(diagnostics["diagnostic_bucket_counts"].items()):
        lines.append(f"- {bucket}: {count}")
    lines.extend(["", "## Readiness", ""])
    for row in summary["readiness"]:
        lines.append(
            f"- {row['readiness_check']}: passed={row['passed']} blocking={row['blocking']} evidence={row['evidence']}"
        )
    lines.extend(["", "## Known Debt", ""])
    for row in summary["known_debt"]:
        if row.get("bucket"):
            lines.append(f"- {row['bucket']}: count={row['count']} - {row['detail']}")
        else:
            lines.append(f"- {row['detail']}")
    lines.extend(["", "## Next Actions", ""])
    for row in summary["next_actions"]:
        lines.append(f"- {row['priority']}: {row['action']} - {row['detail']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(output_dir: Path, summary: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "load_source_line_closeout_summary.json", summary)
    _write_report(output_dir / "load_source_line_closeout_report.md", summary)
    _write_dict_csv(
        output_dir / "load_source_line_closeout_success_criteria.csv",
        summary["success_criteria"],
        ["criterion", "passed", "required", "evidence"],
    )
    _write_dict_csv(
        output_dir / "load_source_line_closeout_known_debt.csv",
        summary["known_debt"],
        ["bucket", "count", "known_debt", "detail"],
    )
    _write_dict_csv(
        output_dir / "load_source_line_closeout_gate_inventory.csv",
        summary["gate_inventory"],
        ["gate", "status", "passed", "evidence"],
    )
    _write_dict_csv(
        output_dir / "load_source_line_closeout_readiness.csv",
        summary["readiness"],
        ["readiness_check", "passed", "blocking", "evidence"],
    )
    _write_dict_csv(
        output_dir / "load_source_line_closeout_next_actions.csv",
        summary["next_actions"],
        ["action", "priority", "detail"],
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.confirm_local_audit_run:
        print("--confirm-local-audit-run is required", file=sys.stderr)
        return 2
    try:
        output_dir = _require_output_under_local_outputs(_resolve(args.output_dir))
        summary = summarize_closeout(
            _resolve(args.diagnostics_dir),
            _resolve(args.ownership_audit_dir),
            _resolve(args.source_line_audit_dir),
            _resolve(args.aggregate_gate_dir),
            _resolve(args.detail_inventory_dir) if args.detail_inventory_dir else None,
            _resolve(args.generated_resolver_provenance_dir)
            if args.generated_resolver_provenance_dir
            else None,
        )
        write_outputs(output_dir, summary)
    except (OSError, closeout_error, json.JSONDecodeError) as exc:
        print(f"load_source_line_closeout_error: {exc}", file=sys.stderr)
        return 1

    print("RateCon load source-line diagnostics closeout")
    print(f"closeout_status: {summary['closeout_status']}")
    print(f"experiment_readiness_status: {summary['experiment_readiness_status']}")
    print(f"diagnostic_document_count: {summary['diagnostics']['document_count']}")
    print(f"detail_status: {summary['diagnostics']['detail_status']}")
    print(
        "source_line_unavailable_ratio: "
        f"{summary['diagnostics']['source_line_unavailable_ratio']:.3f}"
    )
    print(f"unknown_ratio: {summary['diagnostics']['unknown_ratio']:.3f}")
    print(f"aggregate_gate_passed: {summary['aggregate_gate']['gate_passed']}")
    print(f"detail_inventory_status: {summary['detail_inventory']['status']}")
    print(
        "detail_inventory_candidate_detail_row_count: "
        f"{summary['detail_inventory']['candidate_detail_row_count']}"
    )
    print(
        "detail_inventory_missing_page_line_count: "
        f"{summary['detail_inventory']['missing_page_line_count']}"
    )
    print(
        "detail_inventory_missing_source_count: "
        f"{summary['detail_inventory']['missing_source_count']}"
    )
    print(
        "detail_inventory_dropped_detail_count: "
        f"{summary['detail_inventory']['dropped_detail_count']}"
    )
    print(
        "detail_inventory_serialization_sidecar_status: "
        f"{summary['detail_inventory']['serialization_sidecar_status']}"
    )
    print(
        "detail_inventory_serialization_complete_detail_count: "
        f"{summary['detail_inventory']['serialization_complete_detail_count']}"
    )
    print(
        "detail_inventory_serialization_loss_dominates: "
        f"{summary['detail_inventory']['serialization_loss_dominates']}"
    )
    print(
        "detail_inventory_adapter_detail_lost_count: "
        f"{summary['detail_inventory']['adapter_detail_lost_count']}"
    )
    print(
        "detail_inventory_generated_resolver_sidecar_status: "
        f"{summary['detail_inventory']['generated_resolver_sidecar_status']}"
    )
    print(
        "detail_inventory_generated_resolver_current_artifacts_status: "
        f"{summary['detail_inventory']['generated_resolver_current_artifacts_status']}"
    )
    print("private_values_redacted: True")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("google_called: False")
    print("model_or_cloud_called: False")
    print("private_measurement_run: False")
    print(f"output_dir: {output_dir}")
    return 1 if summary["closeout_status"] == status_failed_gate else 0


if __name__ == "__main__":
    raise SystemExit(main())
