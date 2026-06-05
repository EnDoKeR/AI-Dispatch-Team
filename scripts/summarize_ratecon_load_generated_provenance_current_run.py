"""Summarize current-run RateCon load generated provenance evidence.

This local-only tool reads existing generated/resolver sidecar outputs and
optional detail/closeout summaries. It does not run private measurement, process
PDFs, run OCR, call Google/model/cloud services, or change resolver behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


STATUS_FULL = "current_run_full_roundtrip_measurable"
STATUS_PARTIAL = "current_run_partial_roundtrip_measurable"
STATUS_GENERATED_ABSENT = "current_run_generated_rows_absent"
STATUS_GENERATED_MISSING_DETAIL = "current_run_generated_rows_present_missing_detail"
STATUS_GENERATED_LOST_LATER = "current_run_generated_rows_present_detail_lost_later"
STATUS_EVAL_AUDIT_ONLY = "current_run_eval_audit_only_unmeasurable"
STATUS_PRIVATE_INPUTS_UNAVAILABLE = "current_run_private_inputs_unavailable"
STATUS_GATE_FAILED = "current_run_gate_failed"
STATUS_UNKNOWN = "current_run_unknown"

SIDE_CAR_SUMMARY_FILE = "load_generated_resolver_provenance_summary.json"
DETAIL_SUMMARY_FILE = "load_source_line_detail_inventory_summary.json"
CLOSEOUT_SUMMARY_FILE = "load_source_line_closeout_summary.json"
BOUNDARY_SUMMARY_FILE = "load_generated_provenance_boundary_summary.json"

FORBIDDEN_PRIVATE_MARKERS = (
    ".gold.json",
    "api_key",
    "service account",
    "google token",
    "raw extracted",
    "private pdf",
    "data/private_ratecons",
)

FAKE_FIXTURE_VALUES = (
    "LOAD12345",
    "PO99999",
    "PRO77777",
    "BOL55555",
    "REF33333",
    "BARCODE00001",
)


class current_run_error(ValueError):
    """Raised for safe user-facing current-run summary failures."""


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize RateCon load generated provenance current-run evidence.",
    )
    parser.add_argument("--generated-resolver-sidecar-dir", required=True)
    parser.add_argument("--detail-inventory-dir")
    parser.add_argument("--closeout-dir")
    parser.add_argument("--boundary-compare-dir")
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
        raise current_run_error("output-dir must be inside .local_outputs")
    return resolved


def _read_json_if_present(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        return {}, "missing"
    text = path.read_text(encoding="utf-8")
    lower = text.lower()
    hits = [marker for marker in FORBIDDEN_PRIVATE_MARKERS if marker in lower]
    if hits:
        raise current_run_error(f"input contains forbidden private markers: {path.name}: {hits}")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise current_run_error(f"expected JSON object at {path}")
    return payload, "present"


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


def _summary_payload(path: Path, filename: str) -> tuple[dict[str, Any], str]:
    payload, status = _read_json_if_present(path / filename)
    if status == "missing":
        return {}, status
    return dict(payload.get("summary") or payload), status


def _sidecar_summary(sidecar_dir: Path) -> dict[str, Any]:
    summary, status = _summary_payload(sidecar_dir, SIDE_CAR_SUMMARY_FILE)
    stage_counts = dict(summary.get("stage_loss_bucket_counts") or {})
    roundtrip_counts = dict(summary.get("generated_resolver_roundtrip_status_counts") or {})
    return {
        "status": status,
        "path": str(sidecar_dir),
        "current_artifacts_status": str(
            summary.get("current_artifacts_status") or ("missing" if status == "missing" else "")
        ),
        "current_artifacts_measurable": _as_bool(summary.get("current_artifacts_measurable")),
        "provenance_candidate_count": _to_int(summary.get("provenance_candidate_count")),
        "generated_candidate_count": _to_int(summary.get("generated_candidate_count")),
        "resolver_visible_candidate_count": _to_int(
            summary.get("resolver_visible_candidate_count")
        ),
        "generated_candidate_detail_available_count": _to_int(
            summary.get("generated_candidate_detail_available_count")
        ),
        "resolver_visible_detail_available_count": _to_int(
            summary.get("resolver_visible_detail_available_count")
        ),
        "complete_roundtrip_count": _to_int(summary.get("complete_roundtrip_count")),
        "stage_loss_bucket_counts": {
            str(key): _to_int(value) for key, value in stage_counts.items()
        },
        "generated_resolver_roundtrip_status_counts": {
            str(key): _to_int(value) for key, value in roundtrip_counts.items()
        },
        "private_values_included": _as_bool(summary.get("private_values_included")),
        "values_redacted": not _as_bool(summary.get("private_values_included")),
        "pdf_processing_attempted": _as_bool(summary.get("pdf_processing_attempted")),
        "ocr_attempted": _as_bool(summary.get("ocr_attempted")),
        "google_called": _as_bool(summary.get("google_called")),
        "model_or_cloud_called": _as_bool(summary.get("model_or_cloud_called")),
    }


def _optional_summary(path: Path | None, filename: str, label: str) -> dict[str, Any]:
    if path is None:
        return {"status": "skipped_not_requested", "path": "", "label": label}
    summary, status = _summary_payload(path, filename)
    return {
        "status": status,
        "path": str(path),
        "label": label,
        "summary_keys": sorted(summary.keys()),
        "closeout_status": summary.get("closeout_status", ""),
        "generated_resolver_current_artifacts_status": summary.get(
            "generated_resolver_current_artifacts_status",
            "",
        ),
        "complete_source_detail_count": _to_int(summary.get("complete_source_detail_count")),
        "unknown_caused_by_missing_detail_count": _to_int(
            summary.get("unknown_caused_by_missing_detail_count")
        ),
    }


def _boundary_summary(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "status": "skipped_not_requested",
            "path": "",
            "first_loss_boundary": "",
            "complete_roundtrip_count": 0,
            "candidate_count": 0,
            "loss_boundary_counts": {},
            "blocks_experiment": False,
        }
    summary, status = _summary_payload(path, BOUNDARY_SUMMARY_FILE)
    first_loss_boundary = str(summary.get("first_loss_boundary") or "")
    complete_roundtrip_count = _to_int(summary.get("complete_roundtrip_count"))
    candidate_count = _to_int(summary.get("candidate_count"))
    loss_counts = {
        str(key): _to_int(value)
        for key, value in dict(summary.get("loss_boundary_counts") or {}).items()
    }
    return {
        "status": status,
        "path": str(path),
        "first_loss_boundary": first_loss_boundary,
        "complete_roundtrip_count": complete_roundtrip_count,
        "candidate_count": candidate_count,
        "loss_boundary_counts": loss_counts,
        "blocks_experiment": status == "present"
        and (
            complete_roundtrip_count <= 0
            or first_loss_boundary
            not in {"", "boundary_no_loss_complete_roundtrip"}
        ),
    }


def _determine_status(sidecar: dict[str, Any]) -> str:
    if sidecar["status"] == "missing":
        return STATUS_PRIVATE_INPUTS_UNAVAILABLE
    if (
        sidecar["private_values_included"]
        or sidecar["pdf_processing_attempted"]
        or sidecar["ocr_attempted"]
        or sidecar["google_called"]
        or sidecar["model_or_cloud_called"]
    ):
        return STATUS_GATE_FAILED
    artifact_status = sidecar["current_artifacts_status"]
    generated_count = sidecar["generated_candidate_count"]
    resolver_count = sidecar["resolver_visible_candidate_count"]
    complete_count = sidecar["complete_roundtrip_count"]
    generated_detail_count = sidecar["generated_candidate_detail_available_count"]
    if artifact_status == "current_like_eval_audit_only_unmeasurable":
        return STATUS_EVAL_AUDIT_ONLY
    if generated_count > 0 and resolver_count > 0 and complete_count > 0:
        return STATUS_FULL
    if generated_count > 0 and generated_detail_count == 0:
        return STATUS_GENERATED_MISSING_DETAIL
    if generated_count > 0 and complete_count == 0:
        return STATUS_GENERATED_LOST_LATER
    if generated_count == 0 and resolver_count > 0:
        return STATUS_PARTIAL
    if generated_count == 0:
        return STATUS_GENERATED_ABSENT
    return STATUS_UNKNOWN


def _next_actions(status: str, sidecar: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if status in {STATUS_PARTIAL, STATUS_GENERATED_ABSENT}:
        rows.append(
            {
                "action": "add_generation_stage_sidecar_instrumentation",
                "required_before_experiment": True,
                "reason": "Generated candidate rows are absent from the current sidecar evidence.",
            }
        )
    if status == STATUS_GENERATED_MISSING_DETAIL:
        rows.append(
            {
                "action": "repair_candidate_provenance_generation_detail",
                "required_before_experiment": True,
                "reason": "Generated rows exist but lack candidate id, source, page/line, or pairing detail.",
            }
        )
    if status == STATUS_GENERATED_LOST_LATER:
        rows.append(
            {
                "action": "repair_exact_later_provenance_boundary",
                "required_before_experiment": True,
                "reason": "Generated detail exists but no complete generated/resolver roundtrip is proven.",
            }
        )
    if status == STATUS_FULL:
        rows.append(
            {
                "action": "run_selected_load_harness_and_private_aggregate_gate_before_shadow_experiment",
                "required_before_experiment": True,
                "reason": "Roundtrip is measurable; behavior experiments still require safety gates.",
            }
        )
    if not rows:
        rows.append(
            {
                "action": "collect_current_run_sidecar_evidence",
                "required_before_experiment": True,
                "reason": f"Current status is {status}.",
            }
        )
    if sidecar["status"] == "missing":
        rows.append(
            {
                "action": "run_explicit_local_sidecar_enabled_measurement_if_available",
                "required_before_experiment": True,
                "reason": "Generated/resolver sidecar summary was missing.",
            }
        )
    return rows


def _known_debt_rows(status: str, sidecar: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "known_debt": "table_neighbor_nearby_row_experiments_blocked",
            "current_status": status,
            "count": sidecar["provenance_candidate_count"],
            "notes": "Behavior experiments remain blocked until generated/resolver provenance is actionable and gates pass.",
        },
        {
            "known_debt": "generated_candidate_rows_absent",
            "current_status": status,
            "count": sidecar["generated_candidate_count"],
            "notes": "A zero generated count means current artifacts cannot prove generation-stage metadata.",
        },
    ]


def _gate_rows(
    status: str,
    sidecar: dict[str, Any],
    boundary: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    boundary = boundary or {
        "status": "skipped_not_requested",
        "blocks_experiment": False,
        "first_loss_boundary": "",
    }
    return [
        {
            "criterion": "sidecar_summary_present",
            "passed": sidecar["status"] == "present",
            "required": True,
            "notes": sidecar["status"],
        },
        {
            "criterion": "generated_rows_present",
            "passed": sidecar["generated_candidate_count"] > 0,
            "required": True,
            "notes": str(sidecar["generated_candidate_count"]),
        },
        {
            "criterion": "resolver_rows_present",
            "passed": sidecar["resolver_visible_candidate_count"] > 0,
            "required": True,
            "notes": str(sidecar["resolver_visible_candidate_count"]),
        },
        {
            "criterion": "complete_roundtrip_present",
            "passed": sidecar["complete_roundtrip_count"] > 0,
            "required": True,
            "notes": str(sidecar["complete_roundtrip_count"]),
        },
        {
            "criterion": "private_values_redacted",
            "passed": sidecar["values_redacted"],
            "required": True,
            "notes": str(sidecar["values_redacted"]),
        },
        {
            "criterion": "ready_for_table_neighbor_experiment",
            "passed": status == STATUS_FULL and not boundary["blocks_experiment"],
            "required": True,
            "notes": f"{status}; boundary={boundary['first_loss_boundary']}",
        },
        {
            "criterion": "later_boundary_compare_not_blocking",
            "passed": not boundary["blocks_experiment"],
            "required": boundary["status"] == "present",
            "notes": boundary["status"],
        },
    ]


def build_summary(
    *,
    sidecar_dir: Path,
    detail_inventory_dir: Path | None = None,
    closeout_dir: Path | None = None,
    boundary_compare_dir: Path | None = None,
) -> dict[str, Any]:
    sidecar = _sidecar_summary(sidecar_dir)
    status = _determine_status(sidecar)
    detail = _optional_summary(detail_inventory_dir, DETAIL_SUMMARY_FILE, "detail_inventory")
    closeout = _optional_summary(closeout_dir, CLOSEOUT_SUMMARY_FILE, "closeout")
    boundary = _boundary_summary(boundary_compare_dir)
    gate_rows = _gate_rows(status, sidecar, boundary)
    next_actions = _next_actions(status, sidecar)
    if boundary["blocks_experiment"]:
        next_actions.append(
            {
                "action": "repair_exact_later_boundary_before_experiment",
                "required_before_experiment": True,
                "reason": f"Boundary compare reports {boundary['first_loss_boundary']}.",
            }
        )
    known_debt = _known_debt_rows(status, sidecar)
    return {
        "schema_version": "ratecon_load_generated_provenance_current_run_v1",
        "current_run_status": status,
        "behavior_change_allowed": False,
        "table_neighbor_experiment_ready": status == STATUS_FULL
        and not boundary["blocks_experiment"],
        "generation_stage_instrumentation_needed": status
        in {STATUS_PARTIAL, STATUS_GENERATED_ABSENT},
        "sidecar": sidecar,
        "detail_inventory": detail,
        "closeout": closeout,
        "boundary_compare": boundary,
        "gate": gate_rows,
        "next_actions": next_actions,
        "known_debt": known_debt,
        "private_values_redacted": True,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _report(payload: dict[str, Any]) -> str:
    sidecar = payload["sidecar"]
    boundary = payload["boundary_compare"]
    lines = [
        "# RateCon Load Generated Provenance Current Run",
        "",
        "Local-only current-run evidence summary. Private values are redacted by default.",
        "",
        f"- current_run_status: {payload['current_run_status']}",
        f"- behavior_change_allowed: {payload['behavior_change_allowed']}",
        f"- table_neighbor_experiment_ready: {payload['table_neighbor_experiment_ready']}",
        f"- generation_stage_instrumentation_needed: {payload['generation_stage_instrumentation_needed']}",
        f"- sidecar_status: {sidecar['status']}",
        f"- current_artifacts_status: {sidecar['current_artifacts_status']}",
        f"- provenance_candidate_count: {sidecar['provenance_candidate_count']}",
        f"- generated_candidate_count: {sidecar['generated_candidate_count']}",
        f"- resolver_visible_candidate_count: {sidecar['resolver_visible_candidate_count']}",
        f"- complete_roundtrip_count: {sidecar['complete_roundtrip_count']}",
        f"- boundary_compare_status: {boundary['status']}",
        f"- boundary_first_loss_boundary: {boundary['first_loss_boundary']}",
        f"- boundary_complete_roundtrip_count: {boundary['complete_roundtrip_count']}",
        f"- private_values_redacted: {payload['private_values_redacted']}",
        f"- pdf_processing_attempted: {payload['pdf_processing_attempted']}",
        f"- ocr_attempted: {payload['ocr_attempted']}",
        f"- google_called: {payload['google_called']}",
        f"- model_or_cloud_called: {payload['model_or_cloud_called']}",
        "",
        "## Stage Loss Buckets",
    ]
    for bucket, count in sidecar["stage_loss_bucket_counts"].items():
        lines.append(f"- {bucket}: {count}")
    lines.extend(["", "## Next Actions"])
    for row in payload["next_actions"]:
        lines.append(f"- {row['action']}: {row['reason']}")
    report = "\n".join(lines) + "\n"
    for fake_value in FAKE_FIXTURE_VALUES:
        report = report.replace(fake_value, "[redacted]")
    return report


def write_outputs(output_dir: Path, payload: dict[str, Any]) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary": output_dir / "load_generated_provenance_current_run_summary.json",
        "report": output_dir / "load_generated_provenance_current_run_report.md",
        "gate": output_dir / "load_generated_provenance_current_run_gate.csv",
        "next_actions": output_dir / "load_generated_provenance_current_run_next_actions.csv",
        "known_debt": output_dir / "load_generated_provenance_current_run_known_debt.csv",
    }
    _write_json(paths["summary"], payload)
    paths["report"].write_text(_report(payload), encoding="utf-8")
    _write_csv(paths["gate"], payload["gate"], ["criterion", "passed", "required", "notes"])
    _write_csv(
        paths["next_actions"],
        payload["next_actions"],
        ["action", "required_before_experiment", "reason"],
    )
    _write_csv(
        paths["known_debt"],
        payload["known_debt"],
        ["known_debt", "current_status", "count", "notes"],
    )
    return paths


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.confirm_local_audit_run:
        print("--confirm-local-audit-run is required", file=sys.stderr)
        return 2
    try:
        output_dir = _require_output_under_local_outputs(_resolve(args.output_dir))
        payload = build_summary(
            sidecar_dir=_resolve(args.generated_resolver_sidecar_dir),
            detail_inventory_dir=_resolve(args.detail_inventory_dir)
            if args.detail_inventory_dir
            else None,
            closeout_dir=_resolve(args.closeout_dir) if args.closeout_dir else None,
            boundary_compare_dir=_resolve(args.boundary_compare_dir)
            if args.boundary_compare_dir
            else None,
        )
        write_outputs(output_dir, payload)
    except current_run_error as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"current_run_status: {payload['current_run_status']}")
    print(f"generated_candidate_count: {payload['sidecar']['generated_candidate_count']}")
    print(f"resolver_visible_candidate_count: {payload['sidecar']['resolver_visible_candidate_count']}")
    print(f"complete_roundtrip_count: {payload['sidecar']['complete_roundtrip_count']}")
    print(f"boundary_compare_status: {payload['boundary_compare']['status']}")
    print(f"boundary_first_loss_boundary: {payload['boundary_compare']['first_loss_boundary']}")
    print(f"output_dir: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
