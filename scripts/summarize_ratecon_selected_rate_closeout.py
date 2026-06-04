"""Summarize RateCon selected-rate cleanup closeout evidence.

This local-only tool reads existing sanitized selected-rate snapshot, aggregate
gate, and optional audit outputs. It does not run extraction, resolver logic,
private measurement, PDF processing, OCR, Google, or model/cloud services.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


closeout_status_behavior_preserved = "selected_rate_cleanup_closed_behavior_preserved"
closeout_status_known_debt = "selected_rate_cleanup_closed_with_known_debt"
closeout_status_incomplete = "selected_rate_closeout_incomplete_missing_required_gate"
closeout_status_failed_gate = "selected_rate_closeout_failed_gate_regression"
closeout_status_private_baseline_skipped = "selected_rate_closeout_private_baseline_skipped"

forbidden_private_markers = (
    ".gold.json",
    "api_key",
    "secret",
    "service account",
    "google token",
    "raw extracted",
)

required_doc_paths = (
    "docs/ratecon_rate_money_safety_ownership_v1.md",
    "docs/ratecon_rate_ranking_penalty_ownership_v1.md",
    "docs/ratecon_rate_score_trace_explanation_v1.md",
    "docs/ratecon_rate_forensics_diagnosis_mapping_v1.md",
    "docs/MODULE_MAP.md",
)

required_gate_paths = (
    "tests/test_ratecon_selected_rate_regression_harness.py",
    "scripts/run_ratecon_selected_rate_regression_snapshot.py",
    "scripts/compare_ratecon_private_selected_rate_aggregates.py",
    "tests/test_compare_ratecon_private_selected_rate_aggregates.py",
)


class closeout_error(ValueError):
    """Raised for safe user-facing closeout failures."""


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Summarize RateCon selected-rate cleanup closeout evidence.",
    )
    parser.add_argument("--selected-rate-snapshot-dir", required=True)
    parser.add_argument("--aggregate-gate-dir", required=True)
    parser.add_argument("--rate-money-audit-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confirm-local-audit-run", action="store_true")
    return parser.parse_args(argv)


def _resolve(path: str) -> Path:
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
    return json.loads(text), "present"


def _snapshot_summary(snapshot_dir: Path) -> dict[str, Any]:
    payload, status = _read_json_if_present(
        snapshot_dir / "selected_rate_regression_snapshot.json"
    )
    summary = dict(payload.get("summary") or {}) if payload else {}
    cases = list(payload.get("cases") or []) if payload else []
    known_debt_cases = [
        {
            "case_id": case.get("case_id", ""),
            "known_debt": bool(case.get("known_debt")),
            "debt_note": case.get("debt_note", ""),
        }
        for case in cases
        if case.get("known_debt")
    ]
    passed = bool(summary.get("all_passed")) and (
        int(summary.get("case_count") or 0) == int(summary.get("passed_count") or -1)
    )
    return {
        "status": status,
        "path": str(snapshot_dir),
        "case_count": int(summary.get("case_count") or 0),
        "passed_count": int(summary.get("passed_count") or 0),
        "known_debt_count": int(summary.get("known_debt_count") or len(known_debt_cases)),
        "all_passed": passed,
        "known_debt_cases": known_debt_cases,
        "private_values_used": bool(summary.get("private_values_used")),
        "pdf_processing_attempted": bool(summary.get("pdf_processing_attempted")),
        "ocr_attempted": bool(summary.get("ocr_attempted")),
        "google_called": bool(summary.get("google_called")),
        "model_or_cloud_called": bool(summary.get("model_or_cloud_called")),
    }


def _aggregate_gate_summary(gate_dir: Path) -> dict[str, Any]:
    payload, status = _read_json_if_present(
        gate_dir / "private_selected_rate_aggregate_compare_summary.json"
    )
    summary = dict(payload.get("summary") or {}) if payload else {}
    gate = dict(payload.get("gate") or {}) if payload else {}
    delta = dict(summary.get("delta") or {})
    return {
        "status": status,
        "path": str(gate_dir),
        "gate_passed": bool(gate.get("passed")) if payload else False,
        "selected_value_comparison_status": summary.get(
            "selected_value_comparison_status",
            "missing",
        ),
        "selected_value_changed_count": int(
            summary.get("selected_value_changed_count") or 0
        ),
        "wrong_count_delta": int(delta.get("wrong_count") or 0),
        "high_confidence_wrong_delta": int(
            delta.get("high_confidence_wrong_count") or 0
        ),
        "selected_wrong_money_context_delta": int(
            delta.get("selected_wrong_money_context_count") or 0
        ),
        "private_values_included": bool(summary.get("private_values_included")),
        "private_measurement_run": bool(gate.get("private_measurement_run")),
        "pdf_processing_attempted": bool(gate.get("pdf_processing_attempted")),
        "ocr_attempted": bool(gate.get("ocr_attempted")),
        "google_called": bool(gate.get("google_called")),
        "model_or_cloud_called": bool(gate.get("model_or_cloud_called")),
    }


def _rate_money_audit_summary(audit_dir: Path) -> dict[str, Any]:
    possible_names = (
        "rate_money_safety_ownership_summary.json",
        "ratecon_rate_money_safety_ownership_summary.json",
        "rate_forensics_diagnosis_mapping_summary.json",
    )
    for name in possible_names:
        payload, status = _read_json_if_present(audit_dir / name)
        if status == "present":
            return {
                "status": "present",
                "path": str(audit_dir / name),
                "module_count": int(payload.get("module_count") or 0),
                "risk_finding_count": int(payload.get("risk_finding_count") or 0),
                "status_recommendation_counts": dict(
                    payload.get("status_recommendation_counts") or {}
                ),
            }
    return {
        "status": "skipped_missing_optional_dir",
        "path": str(audit_dir),
        "module_count": 0,
        "risk_finding_count": 0,
        "status_recommendation_counts": {},
    }


def _repo_evidence(repo_root: Path) -> dict[str, Any]:
    docs = {
        path: (repo_root / path).exists()
        for path in required_doc_paths
    }
    gates = {
        path: (repo_root / path).exists()
        for path in required_gate_paths
    }
    return {
        "docs": docs,
        "gates": gates,
        "all_required_docs_present": all(docs.values()),
        "all_required_gate_files_present": all(gates.values()),
    }


def _success_criteria(snapshot: dict, gate: dict, repo_evidence: dict) -> list[dict]:
    return [
        {
            "criterion": "selected_rate_sanitized_regression_harness_passes",
            "passed": snapshot["status"] == "present" and snapshot["all_passed"],
            "required": True,
            "evidence": f"{snapshot['passed_count']}/{snapshot['case_count']} cases passed",
        },
        {
            "criterion": "private_aggregate_gate_same_output_passes",
            "passed": gate["status"] == "present" and gate["gate_passed"],
            "required": True,
            "evidence": (
                f"wrong_delta={gate['wrong_count_delta']} "
                f"high_conf_delta={gate['high_confidence_wrong_delta']} "
                f"wrong_context_delta={gate['selected_wrong_money_context_delta']}"
            ),
        },
        {
            "criterion": "required_docs_present",
            "passed": repo_evidence["all_required_docs_present"],
            "required": True,
            "evidence": json.dumps(repo_evidence["docs"], sort_keys=True),
        },
        {
            "criterion": "required_gate_files_present",
            "passed": repo_evidence["all_required_gate_files_present"],
            "required": True,
            "evidence": json.dumps(repo_evidence["gates"], sort_keys=True),
        },
        {
            "criterion": "no_private_runtime_side_effects_reported",
            "passed": not any(
                [
                    snapshot["private_values_used"],
                    snapshot["pdf_processing_attempted"],
                    snapshot["ocr_attempted"],
                    snapshot["google_called"],
                    snapshot["model_or_cloud_called"],
                    gate["private_values_included"],
                    gate["private_measurement_run"],
                    gate["pdf_processing_attempted"],
                    gate["ocr_attempted"],
                    gate["google_called"],
                    gate["model_or_cloud_called"],
                ]
            ),
            "required": True,
            "evidence": "snapshot/gate side-effect flags are false",
        },
    ]


def _gate_inventory(snapshot: dict, gate: dict, audit: dict) -> list[dict]:
    return [
        {
            "gate": "sanitized_selected_rate_regression_snapshot",
            "status": snapshot["status"],
            "passed": snapshot["all_passed"],
            "evidence": f"{snapshot['passed_count']}/{snapshot['case_count']} cases",
        },
        {
            "gate": "private_selected_rate_aggregate_same_output",
            "status": gate["status"],
            "passed": gate["gate_passed"],
            "evidence": f"selected_value_changed_count={gate['selected_value_changed_count']}",
        },
        {
            "gate": "rate_money_static_audit_optional",
            "status": audit["status"],
            "passed": audit["status"] != "present" or audit["risk_finding_count"] == 0,
            "evidence": f"risk_finding_count={audit['risk_finding_count']}",
        },
    ]


def _known_debt_rows(snapshot: dict) -> list[dict]:
    if not snapshot["known_debt_cases"]:
        return [
            {
                "case_id": "",
                "known_debt": False,
                "debt_note": "No known-debt selected-rate cases reported by snapshot.",
            }
        ]
    return snapshot["known_debt_cases"]


def _next_actions(status: str, audit: dict) -> list[dict]:
    rows = [
        {
            "action": "preserve_current_behavior",
            "priority": "required",
            "detail": "Do not change selected-rate output, scoring, penalties, thresholds, traces, diagnosis strings, or gate semantics inside closeout work.",
        },
        {
            "action": "capture_private_full_corpus_baseline",
            "priority": "recommended",
            "detail": "Run private measurement/evaluation only when explicitly requested and keep all outputs under ignored .local_outputs.",
        },
        {
            "action": "use_gates_before_experimental_ranking_profile",
            "priority": "required",
            "detail": "Run sanitized selected-rate harness, snapshot compare, aggregate gate, and explicit metric-delta review before behavior changes.",
        },
    ]
    if status in {closeout_status_incomplete, closeout_status_failed_gate}:
        rows.insert(
            0,
            {
                "action": "resolve_closeout_blocker",
                "priority": "required",
                "detail": f"Closeout status is {status}; do not proceed to ranking experiments.",
            },
        )
    if audit["status"] != "present":
        rows.append(
            {
                "action": "optional_rate_money_audit_rerun",
                "priority": "optional",
                "detail": "Optional rate/money audit summary was unavailable and was skipped.",
            }
        )
    return rows


def _closeout_status(snapshot: dict, gate: dict, criteria: list[dict], audit: dict) -> str:
    required_failed = [row for row in criteria if row["required"] and not row["passed"]]
    if snapshot["status"] != "present" or gate["status"] != "present" or required_failed:
        if gate["status"] == "present" and not gate["gate_passed"]:
            return closeout_status_failed_gate
        return closeout_status_incomplete
    if not gate["gate_passed"]:
        return closeout_status_failed_gate
    if snapshot["known_debt_count"]:
        return closeout_status_known_debt
    if audit["status"] != "present":
        return closeout_status_private_baseline_skipped
    return closeout_status_behavior_preserved


def summarize_closeout(
    selected_rate_snapshot_dir: Path,
    aggregate_gate_dir: Path,
    rate_money_audit_dir: Path,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    repo_root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    snapshot = _snapshot_summary(selected_rate_snapshot_dir)
    gate = _aggregate_gate_summary(aggregate_gate_dir)
    audit = _rate_money_audit_summary(rate_money_audit_dir)
    repo = _repo_evidence(repo_root)
    criteria = _success_criteria(snapshot, gate, repo)
    gate_rows = _gate_inventory(snapshot, gate, audit)
    status = _closeout_status(snapshot, gate, criteria, audit)
    known_debt = _known_debt_rows(snapshot)
    return {
        "schema_version": "ratecon_selected_rate_closeout_v1",
        "closeout_status": status,
        "selected_rate_snapshot": snapshot,
        "aggregate_gate": gate,
        "rate_money_audit": audit,
        "repo_evidence": repo,
        "success_criteria": criteria,
        "known_debt": known_debt,
        "gate_inventory": gate_rows,
        "next_actions": _next_actions(status, audit),
        "private_values_redacted": True,
        "private_full_corpus_baseline_status": (
            "skipped_local_inputs_unavailable" if audit["status"] != "present" else "not_run_by_closeout_tool"
        ),
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
        "private_measurement_run": False,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_dict_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_report(path: Path, summary: dict) -> None:
    snapshot = summary["selected_rate_snapshot"]
    gate = summary["aggregate_gate"]
    lines = [
        "# RateCon Selected-Rate Cleanup Closeout",
        "",
        "This local-only closeout reads existing sanitized gate outputs only.",
        "",
        f"- closeout_status: {summary['closeout_status']}",
        f"- snapshot_cases: {snapshot['passed_count']}/{snapshot['case_count']}",
        f"- known_debt_count: {snapshot['known_debt_count']}",
        f"- aggregate_gate_passed: {gate['gate_passed']}",
        f"- selected_value_changed_count: {gate['selected_value_changed_count']}",
        f"- private_full_corpus_baseline_status: {summary['private_full_corpus_baseline_status']}",
        "- private_values_redacted: True",
        "- pdf_processing_attempted: False",
        "- ocr_attempted: False",
        "- google_called: False",
        "- model_or_cloud_called: False",
        "- private_measurement_run: False",
        "",
        "## Success Criteria",
        "",
    ]
    for row in summary["success_criteria"]:
        lines.append(
            f"- {row['criterion']}: passed={row['passed']} required={row['required']}"
        )
    lines.extend(["", "## Known Debt", ""])
    for row in summary["known_debt"]:
        if row.get("case_id"):
            lines.append(f"- {row['case_id']}: {row.get('debt_note', '')}")
        else:
            lines.append(f"- {row.get('debt_note', '')}")
    lines.extend(["", "## Next Actions", ""])
    for row in summary["next_actions"]:
        lines.append(f"- {row['priority']}: {row['action']} - {row['detail']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(output_dir: Path, summary: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "selected_rate_closeout_summary.json", summary)
    _write_report(output_dir / "selected_rate_closeout_report.md", summary)
    _write_dict_csv(
        output_dir / "selected_rate_closeout_success_criteria.csv",
        summary["success_criteria"],
        ["criterion", "passed", "required", "evidence"],
    )
    _write_dict_csv(
        output_dir / "selected_rate_closeout_known_debt.csv",
        summary["known_debt"],
        ["case_id", "known_debt", "debt_note"],
    )
    _write_dict_csv(
        output_dir / "selected_rate_closeout_gate_inventory.csv",
        summary["gate_inventory"],
        ["gate", "status", "passed", "evidence"],
    )
    _write_dict_csv(
        output_dir / "selected_rate_closeout_next_actions.csv",
        summary["next_actions"],
        ["action", "priority", "detail"],
    )


def main(argv=None) -> int:
    args = _parse_args(argv)
    if not args.confirm_local_audit_run:
        print("--confirm-local-audit-run is required", file=sys.stderr)
        return 2
    try:
        output_dir = _require_output_under_local_outputs(_resolve(args.output_dir))
        summary = summarize_closeout(
            _resolve(args.selected_rate_snapshot_dir),
            _resolve(args.aggregate_gate_dir),
            _resolve(args.rate_money_audit_dir),
        )
        write_outputs(output_dir, summary)
    except (OSError, closeout_error, json.JSONDecodeError) as exc:
        print(f"selected_rate_closeout_error: {exc}", file=sys.stderr)
        return 1

    print("RateCon selected-rate cleanup closeout")
    print(f"closeout_status: {summary['closeout_status']}")
    print(
        "snapshot_cases: "
        f"{summary['selected_rate_snapshot']['passed_count']}/"
        f"{summary['selected_rate_snapshot']['case_count']}"
    )
    print(f"known_debt_count: {summary['selected_rate_snapshot']['known_debt_count']}")
    print(f"aggregate_gate_passed: {summary['aggregate_gate']['gate_passed']}")
    print(
        "private_full_corpus_baseline_status: "
        f"{summary['private_full_corpus_baseline_status']}"
    )
    print("private_values_redacted: True")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("google_called: False")
    print("model_or_cloud_called: False")
    print("private_measurement_run: False")
    print(f"output_dir: {output_dir}")
    return 0 if summary["closeout_status"] not in {
        closeout_status_incomplete,
        closeout_status_failed_gate,
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
