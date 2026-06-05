"""Summarize RateCon load adapter/dedupe current-run evidence.

This local-only closeout reads existing generated/resolver sidecar and boundary
comparison outputs only. It does not run private measurement, process PDFs,
invoke OCR, call Google/model/cloud services, or change selected load-number
behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


STATUS_FULL = "adapter_dedupe_current_run_full_roundtrip_measurable"
STATUS_GENERATION_TO_ADAPTER = "adapter_dedupe_current_run_generation_to_adapter_loss"
STATUS_ADAPTER_TO_DEDUPE = "adapter_dedupe_current_run_adapter_to_dedupe_loss"
STATUS_DEDUPE_TO_RESOLVER = "adapter_dedupe_current_run_dedupe_to_resolver_loss"
STATUS_RESOLVER_TO_AUDIT = "adapter_dedupe_current_run_resolver_to_audit_loss"
STATUS_AUDIT_TO_EVALUATOR = "adapter_dedupe_current_run_audit_to_evaluator_loss"
STATUS_CANDIDATE_NOT_COMPARABLE = "adapter_dedupe_current_run_candidate_not_comparable"
STATUS_STAGE_UNAVAILABLE = "adapter_dedupe_current_run_stage_unavailable"
STATUS_PRIVATE_INPUTS_UNAVAILABLE = "adapter_dedupe_current_run_private_inputs_unavailable"
STATUS_UNKNOWN = "adapter_dedupe_current_run_unknown"

SIDE_CAR_SUMMARY_FILE = "load_generated_resolver_provenance_summary.json"
BOUNDARY_SUMMARY_FILE = "load_generated_provenance_boundary_summary.json"
RESOLVER_TO_AUDIT_SUMMARY_FILE = "load_resolver_to_audit_provenance_summary.json"

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

BOUNDARY_STATUS_MAP = {
    "boundary_generation_to_adapter_loss": STATUS_GENERATION_TO_ADAPTER,
    "boundary_adapter_to_dedupe_loss": STATUS_ADAPTER_TO_DEDUPE,
    "boundary_dedupe_to_resolver_loss": STATUS_DEDUPE_TO_RESOLVER,
    "boundary_resolver_to_audit_loss": STATUS_RESOLVER_TO_AUDIT,
    "boundary_audit_to_evaluator_loss": STATUS_AUDIT_TO_EVALUATOR,
    "boundary_candidate_not_comparable": STATUS_CANDIDATE_NOT_COMPARABLE,
    "boundary_stage_unavailable": STATUS_STAGE_UNAVAILABLE,
}


class adapter_dedupe_current_run_error(ValueError):
    """Raised for safe user-facing current-run summary failures."""


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize RateCon load adapter/dedupe current-run evidence."
    )
    parser.add_argument("--generated-resolver-sidecar-dir", required=True)
    parser.add_argument("--boundary-compare-dir")
    parser.add_argument("--resolver-to-audit-sidecar-dir")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confirm-local-audit-run", action="store_true")
    return parser.parse_args(argv)


def _resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _require_output_under_local_outputs(path: Path) -> Path:
    resolved = path.resolve()
    if ".local_outputs" not in resolved.parts:
        raise adapter_dedupe_current_run_error("output-dir must be inside .local_outputs")
    return resolved


def _read_json_if_present(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        return {}, "missing"
    text = path.read_text(encoding="utf-8")
    lower = text.lower()
    hits = [marker for marker in FORBIDDEN_PRIVATE_MARKERS if marker in lower]
    if hits:
        raise adapter_dedupe_current_run_error(
            f"input contains forbidden private markers: {path.name}: {hits}"
        )
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise adapter_dedupe_current_run_error(f"expected JSON object at {path}")
    return payload, "present"


def _summary_payload(path: Path, filename: str) -> tuple[dict[str, Any], str]:
    payload, status = _read_json_if_present(path / filename)
    if status == "missing":
        return {}, status
    return dict(payload.get("summary") or payload), status


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


def _sidecar_summary(sidecar_dir: Path) -> dict[str, Any]:
    summary, status = _summary_payload(sidecar_dir, SIDE_CAR_SUMMARY_FILE)
    stage_counts = dict(summary.get("stage_loss_bucket_counts") or {})
    return {
        "status": status,
        "path": str(sidecar_dir),
        "current_artifacts_status": str(
            summary.get("current_artifacts_status")
            or ("missing" if status == "missing" else "")
        ),
        "provenance_candidate_count": _to_int(summary.get("provenance_candidate_count")),
        "generated_candidate_count": _to_int(summary.get("generated_candidate_count")),
        "adapter_input_count": _to_int(summary.get("adapter_input_count")),
        "adapter_output_count": _to_int(summary.get("adapter_output_count")),
        "dedupe_input_count": _to_int(summary.get("dedupe_input_count")),
        "dedupe_output_count": _to_int(summary.get("dedupe_output_count")),
        "resolver_visible_candidate_count": _to_int(
            summary.get("resolver_visible_candidate_count")
        ),
        "complete_roundtrip_count": _to_int(summary.get("complete_roundtrip_count")),
        "adapter_detail_preserved_count": _to_int(
            summary.get("adapter_detail_preserved_count")
        ),
        "adapter_detail_lost_count": _to_int(summary.get("adapter_detail_lost_count")),
        "dedupe_detail_preserved_count": _to_int(
            summary.get("dedupe_detail_preserved_count")
        ),
        "dedupe_detail_lost_count": _to_int(summary.get("dedupe_detail_lost_count")),
        "generated_candidate_detail_available_count": _to_int(
            summary.get("generated_candidate_detail_available_count")
        ),
        "resolver_visible_detail_available_count": _to_int(
            summary.get("resolver_visible_detail_available_count")
        ),
        "stage_loss_bucket_counts": {
            str(key): _to_int(value) for key, value in stage_counts.items()
        },
        "private_values_included": _as_bool(summary.get("private_values_included")),
        "values_redacted": not _as_bool(summary.get("private_values_included")),
        "pdf_processing_attempted": _as_bool(summary.get("pdf_processing_attempted")),
        "ocr_attempted": _as_bool(summary.get("ocr_attempted")),
        "google_called": _as_bool(summary.get("google_called")),
        "model_or_cloud_called": _as_bool(summary.get("model_or_cloud_called")),
    }


def _boundary_summary(boundary_dir: Path | None) -> dict[str, Any]:
    if boundary_dir is None:
        return {
            "status": "skipped_not_requested",
            "path": "",
            "candidate_count": 0,
            "complete_roundtrip_count": 0,
            "first_loss_boundary": "",
            "loss_boundary_counts": {},
            "blocks_experiment": False,
        }
    summary, status = _summary_payload(boundary_dir, BOUNDARY_SUMMARY_FILE)
    first_loss_boundary = str(summary.get("first_loss_boundary") or "")
    complete_roundtrip_count = _to_int(summary.get("complete_roundtrip_count"))
    loss_counts = {
        str(key): _to_int(value)
        for key, value in dict(summary.get("loss_boundary_counts") or {}).items()
    }
    return {
        "status": status,
        "path": str(boundary_dir),
        "candidate_count": _to_int(summary.get("candidate_count")),
        "complete_roundtrip_count": complete_roundtrip_count,
        "first_loss_boundary": first_loss_boundary,
        "loss_boundary_counts": loss_counts,
        "blocks_experiment": status == "present"
        and (
            complete_roundtrip_count <= 0
            or first_loss_boundary
            not in {"", "boundary_no_loss_complete_roundtrip"}
        ),
    }


def _resolver_to_audit_summary(sidecar_dir: Path | None) -> dict[str, Any]:
    if sidecar_dir is None:
        return {
            "status": "skipped_not_requested",
            "resolver_to_audit_preserved_count": 0,
            "resolver_to_audit_loss_count": 0,
            "resolver_to_audit_status_counts": {},
        }
    summary, status = _summary_payload(sidecar_dir, RESOLVER_TO_AUDIT_SUMMARY_FILE)
    return {
        "status": status,
        "resolver_to_audit_preserved_count": _to_int(
            summary.get("resolver_to_audit_preserved_count")
        ),
        "resolver_to_audit_loss_count": _to_int(summary.get("resolver_to_audit_loss_count")),
        "resolver_to_audit_status_counts": dict(
            summary.get("resolver_to_audit_status_counts") or {}
        ),
    }
def _has_all_stage_rows(sidecar: dict[str, Any]) -> bool:
    return (
        sidecar["generated_candidate_count"] > 0
        and sidecar["adapter_input_count"] > 0
        and sidecar["adapter_output_count"] > 0
        and sidecar["dedupe_input_count"] > 0
        and sidecar["dedupe_output_count"] > 0
        and sidecar["resolver_visible_candidate_count"] > 0
    )


def _determine_status(sidecar: dict[str, Any], boundary: dict[str, Any]) -> str:
    if sidecar["status"] == "missing":
        return STATUS_PRIVATE_INPUTS_UNAVAILABLE
    if (
        sidecar["private_values_included"]
        or sidecar["pdf_processing_attempted"]
        or sidecar["ocr_attempted"]
        or sidecar["google_called"]
        or sidecar["model_or_cloud_called"]
    ):
        return STATUS_UNKNOWN
    if _has_all_stage_rows(sidecar) and sidecar["complete_roundtrip_count"] > 0:
        if boundary["status"] != "present" or boundary["first_loss_boundary"] in {
            "",
            "boundary_no_loss_complete_roundtrip",
        }:
            return STATUS_FULL
    if boundary["status"] == "present":
        mapped = BOUNDARY_STATUS_MAP.get(boundary["first_loss_boundary"])
        if mapped:
            return mapped
    if sidecar["generated_candidate_count"] > 0 and sidecar["adapter_input_count"] == 0:
        return STATUS_GENERATION_TO_ADAPTER
    if sidecar["adapter_output_count"] > 0 and sidecar["dedupe_input_count"] == 0:
        return STATUS_ADAPTER_TO_DEDUPE
    if sidecar["dedupe_output_count"] > 0 and sidecar["resolver_visible_candidate_count"] == 0:
        return STATUS_DEDUPE_TO_RESOLVER
    if not _has_all_stage_rows(sidecar):
        return STATUS_STAGE_UNAVAILABLE
    return STATUS_UNKNOWN


def _gate_rows(
    status: str,
    sidecar: dict[str, Any],
    boundary: dict[str, Any],
) -> list[dict[str, Any]]:
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
            "criterion": "adapter_rows_present",
            "passed": sidecar["adapter_input_count"] > 0
            and sidecar["adapter_output_count"] > 0,
            "required": True,
            "notes": f"{sidecar['adapter_input_count']}/{sidecar['adapter_output_count']}",
        },
        {
            "criterion": "dedupe_rows_present",
            "passed": sidecar["dedupe_input_count"] > 0
            and sidecar["dedupe_output_count"] > 0,
            "required": True,
            "notes": f"{sidecar['dedupe_input_count']}/{sidecar['dedupe_output_count']}",
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
            "criterion": "boundary_compare_present",
            "passed": boundary["status"] == "present",
            "required": True,
            "notes": boundary["status"],
        },
        {
            "criterion": "private_values_redacted",
            "passed": sidecar["values_redacted"],
            "required": True,
            "notes": str(sidecar["values_redacted"]),
        },
        {
            "criterion": "ready_for_table_neighbor_experiment",
            "passed": False,
            "required": True,
            "notes": (
                f"{status}; boundary={boundary['first_loss_boundary']}; "
                "selected-load gates are not evaluated by this current-run closeout"
            ),
        },
    ]


def _next_actions(status: str, boundary: dict[str, Any]) -> list[dict[str, Any]]:
    boundary_name = boundary.get("first_loss_boundary") or ""
    action_by_status = {
        STATUS_FULL: (
            "run_selected_load_harness_and_private_aggregate_gate_before_shadow_experiment",
            "Full diagnostic roundtrip is measurable; behavior experiments still require selected-load gates.",
        ),
        STATUS_GENERATION_TO_ADAPTER: (
            "repair_generation_to_adapter_diagnostic_boundary",
            "Generated rows are present but adapter visibility/preservation is the first blocking boundary.",
        ),
        STATUS_ADAPTER_TO_DEDUPE: (
            "repair_adapter_to_dedupe_diagnostic_boundary",
            "Adapter rows are present but dedupe visibility/preservation is the first blocking boundary.",
        ),
        STATUS_DEDUPE_TO_RESOLVER: (
            "repair_dedupe_to_resolver_diagnostic_boundary",
            "Dedupe rows are present but resolver visibility/preservation is the first blocking boundary.",
        ),
        STATUS_RESOLVER_TO_AUDIT: (
            "repair_resolver_to_audit_diagnostic_sidecar_boundary",
            "Resolver detail is present but audit stage detail is not serialized in local diagnostics.",
        ),
        STATUS_AUDIT_TO_EVALUATOR: (
            "repair_audit_to_evaluator_diagnostic_sidecar_boundary",
            "Audit detail is present but evaluator sidecar detail is not serialized.",
        ),
        STATUS_CANDIDATE_NOT_COMPARABLE: (
            "repair_candidate_identity_visibility_before_behavior_experiment",
            "Candidate ids cannot be compared across stages without fabricating identity.",
        ),
        STATUS_STAGE_UNAVAILABLE: (
            "emit_missing_diagnostic_stage_rows_before_behavior_experiment",
            "One or more required diagnostic stages are unavailable.",
        ),
        STATUS_PRIVATE_INPUTS_UNAVAILABLE: (
            "run_explicit_local_private_diagnostic_measurement_when_inputs_exist",
            "Private current-run inputs were unavailable for this closeout.",
        ),
        STATUS_UNKNOWN: (
            "inspect_sidecar_and_boundary_summaries_before_repair",
            "The current evidence does not map to a stable adapter/dedupe status.",
        ),
    }
    action, reason = action_by_status.get(status, action_by_status[STATUS_UNKNOWN])
    rows = [
        {
            "action": action,
            "required_before_experiment": True,
            "reason": reason if not boundary_name else f"{reason} Boundary={boundary_name}.",
        },
        {
            "action": "preserve_current_load_behavior",
            "required_before_experiment": True,
            "reason": "Do not change selected load output, generation, dedupe decisions, resolver scoring, sources, confidence, or evaluator statuses.",
        },
    ]
    return rows


def _known_debt_rows(status: str, sidecar: dict[str, Any], boundary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "known_debt": "complete_generated_to_resolver_roundtrip_not_proven",
            "current_status": status,
            "count": sidecar["complete_roundtrip_count"],
            "notes": "Behavior experiments remain blocked while complete roundtrip count is zero.",
        },
        {
            "known_debt": "first_proven_boundary_blocks_behavior_experiment",
            "current_status": status,
            "count": boundary["candidate_count"],
            "notes": boundary["first_loss_boundary"] or "boundary compare missing or inconclusive",
        },
    ]


def build_summary(
    *,
    sidecar_dir: Path,
    boundary_compare_dir: Path | None = None,
    resolver_to_audit_sidecar_dir: Path | None = None,
) -> dict[str, Any]:
    sidecar = _sidecar_summary(sidecar_dir)
    boundary = _boundary_summary(boundary_compare_dir)
    resolver_to_audit = _resolver_to_audit_summary(resolver_to_audit_sidecar_dir)
    status = _determine_status(sidecar, boundary)
    return {
        "schema_version": "ratecon_load_adapter_dedupe_current_run_v1",
        "current_run_status": status,
        "behavior_change_allowed": False,
        "table_neighbor_experiment_ready": False,
        "sidecar": sidecar,
        "boundary_compare": boundary,
        "resolver_to_audit_sidecar": resolver_to_audit,
        "gate": _gate_rows(status, sidecar, boundary),
        "next_actions": _next_actions(status, boundary),
        "known_debt": _known_debt_rows(status, sidecar, boundary),
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
    resolver_to_audit = payload["resolver_to_audit_sidecar"]
    lines = [
        "# RateCon Load Adapter/Dedupe Current Run",
        "",
        "Local-only adapter/dedupe current-run closeout. Private values are redacted by default.",
        "",
        f"- current_run_status: {payload['current_run_status']}",
        f"- behavior_change_allowed: {payload['behavior_change_allowed']}",
        f"- table_neighbor_experiment_ready: {payload['table_neighbor_experiment_ready']}",
        f"- generated_candidate_count: {sidecar['generated_candidate_count']}",
        f"- adapter_input_count: {sidecar['adapter_input_count']}",
        f"- adapter_output_count: {sidecar['adapter_output_count']}",
        f"- dedupe_input_count: {sidecar['dedupe_input_count']}",
        f"- dedupe_output_count: {sidecar['dedupe_output_count']}",
        f"- resolver_visible_candidate_count: {sidecar['resolver_visible_candidate_count']}",
        f"- complete_roundtrip_count: {sidecar['complete_roundtrip_count']}",
        f"- adapter_detail_lost_count: {sidecar['adapter_detail_lost_count']}",
        f"- dedupe_detail_lost_count: {sidecar['dedupe_detail_lost_count']}",
        f"- boundary_compare_status: {boundary['status']}",
        f"- first_loss_boundary: {boundary['first_loss_boundary']}",
        f"- boundary_candidate_count: {boundary['candidate_count']}",
        f"- boundary_complete_roundtrip_count: {boundary['complete_roundtrip_count']}",
        f"- resolver_to_audit_sidecar_status: {resolver_to_audit['status']}",
        f"- resolver_to_audit_preserved_count: {resolver_to_audit['resolver_to_audit_preserved_count']}",
        f"- resolver_to_audit_loss_count: {resolver_to_audit['resolver_to_audit_loss_count']}",
        f"- private_values_redacted: {payload['private_values_redacted']}",
        f"- pdf_processing_attempted: {payload['pdf_processing_attempted']}",
        f"- ocr_attempted: {payload['ocr_attempted']}",
        f"- google_called: {payload['google_called']}",
        f"- model_or_cloud_called: {payload['model_or_cloud_called']}",
        "",
        "## Boundary Counts",
    ]
    for boundary_name, count in boundary["loss_boundary_counts"].items():
        lines.append(f"- {boundary_name}: {count}")
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
        "summary": output_dir / "load_adapter_dedupe_current_run_summary.json",
        "report": output_dir / "load_adapter_dedupe_current_run_report.md",
        "gate": output_dir / "load_adapter_dedupe_current_run_gate.csv",
        "next_actions": output_dir / "load_adapter_dedupe_current_run_next_actions.csv",
        "known_debt": output_dir / "load_adapter_dedupe_current_run_known_debt.csv",
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
            boundary_compare_dir=_resolve(args.boundary_compare_dir)
            if args.boundary_compare_dir
            else None,
            resolver_to_audit_sidecar_dir=_resolve(args.resolver_to_audit_sidecar_dir)
            if args.resolver_to_audit_sidecar_dir
            else None,
        )
        write_outputs(output_dir, payload)
    except (OSError, adapter_dedupe_current_run_error, json.JSONDecodeError) as exc:
        print(f"adapter_dedupe_current_run_error: {exc}", file=sys.stderr)
        return 1

    sidecar = payload["sidecar"]
    boundary = payload["boundary_compare"]
    resolver_to_audit = payload["resolver_to_audit_sidecar"]
    print("RateCon load adapter/dedupe current-run closeout")
    print(f"current_run_status: {payload['current_run_status']}")
    print(f"generated_candidate_count: {sidecar['generated_candidate_count']}")
    print(f"adapter_input_count: {sidecar['adapter_input_count']}")
    print(f"adapter_output_count: {sidecar['adapter_output_count']}")
    print(f"dedupe_input_count: {sidecar['dedupe_input_count']}")
    print(f"dedupe_output_count: {sidecar['dedupe_output_count']}")
    print(f"resolver_visible_candidate_count: {sidecar['resolver_visible_candidate_count']}")
    print(f"complete_roundtrip_count: {sidecar['complete_roundtrip_count']}")
    print(f"first_loss_boundary: {boundary['first_loss_boundary']}")
    print(f"resolver_to_audit_sidecar_status: {resolver_to_audit['status']}")
    print(f"resolver_to_audit_preserved_count: {resolver_to_audit['resolver_to_audit_preserved_count']}")
    print(f"resolver_to_audit_loss_count: {resolver_to_audit['resolver_to_audit_loss_count']}")
    print(f"table_neighbor_experiment_ready: {payload['table_neighbor_experiment_ready']}")
    print(f"private_values_redacted: {payload['private_values_redacted']}")
    print(f"pdf_processing_attempted: {payload['pdf_processing_attempted']}")
    print(f"ocr_attempted: {payload['ocr_attempted']}")
    print(f"google_called: {payload['google_called']}")
    print(f"model_or_cloud_called: {payload['model_or_cloud_called']}")
    print(f"output_dir: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
