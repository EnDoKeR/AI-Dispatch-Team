"""Compare local-only RateCon generated load provenance boundaries.

This tool reads existing sidecar/detail artifacts only. It does not run
private measurement, process PDFs, invoke OCR, call Google, call model/cloud
services, or change selected load-number behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.load_identifier_generated_provenance_boundary import (  # noqa: E402
    BOUNDARY_ROW_FIELDNAMES,
    LOAD_GENERATED_PROVENANCE_BOUNDARY_SCHEMA_VERSION,
    compare_generated_provenance_boundaries,
)


STAGE_ROW_FILE = "load_generated_provenance_boundary_stage_rows.csv"
GENERATED_FILES = (("load_generated_candidates.csv", "generated"), ("generated_candidates.csv", "generated"))
ADAPTER_FILES = (
    ("load_adapter_roundtrip_rows.csv", ""),
    ("load_adapter_input_candidates.csv", "adapter_input"),
    ("load_adapter_output_candidates.csv", "adapter_output"),
    ("adapter_input.csv", "adapter_input"),
    ("adapter_output.csv", "adapter_output"),
)
DEDUPE_FILES = (
    ("load_dedupe_lineage_rows.csv", ""),
    ("load_dedupe_input_candidates.csv", "dedupe_input"),
    ("load_dedupe_output_candidates.csv", "dedupe_output"),
    ("dedupe_input.csv", "dedupe_input"),
    ("dedupe_output.csv", "dedupe_output"),
)
RESOLVER_FILES = (("load_resolver_visible_candidates.csv", "resolver"), ("resolver_trace.csv", "resolver"))
SERIALIZATION_FILE = "load_source_line_serialization_rows.csv"
DETAIL_FILE = "load_source_line_detail_rows.csv"
ADAPTER_DEDUPE_CURRENT_RUN_SUMMARY_FILE = "load_adapter_dedupe_current_run_summary.json"

FORBIDDEN_PRIVATE_MARKERS = (
    ".gold.json",
    "api_key",
    "service account",
    "google token",
    "raw extracted",
    "private pdf",
    "data/private_ratecons",
)


class boundary_compare_error(ValueError):
    """Raised for safe user-facing boundary comparison failures."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare local-only RateCon load generated provenance boundaries.",
    )
    parser.add_argument("--generated-resolver-sidecar-dir", required=True)
    parser.add_argument("--serialization-dir")
    parser.add_argument("--detail-inventory-dir")
    parser.add_argument("--adapter-dedupe-current-run-dir")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confirm-local-audit-run", action="store_true")
    return parser.parse_args(argv)


def _resolve(path: str | Path | None) -> Path | None:
    if not path:
        return None
    return Path(path).expanduser().resolve()


def _require_output_under_local_outputs(path: Path) -> Path:
    if ".local_outputs" not in path.parts:
        raise boundary_compare_error("output-dir must be inside .local_outputs")
    return path


def _check_safe_text(path: Path, text: str) -> None:
    lower = text.lower()
    hits = [marker for marker in FORBIDDEN_PRIVATE_MARKERS if marker in lower]
    if hits:
        raise boundary_compare_error(f"input contains forbidden private markers: {path.name}: {hits}")


def _csv_rows(path: Path | None, default_stage: str = "") -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    _check_safe_text(path, text)
    rows: list[dict[str, Any]] = []
    for row in csv.DictReader(text.splitlines()):
        row_dict = dict(row)
        if default_stage and not row_dict.get("stage"):
            row_dict["stage"] = default_stage
        rows.append(row_dict)
    return rows


def _csv_rows_from_first(directory: Path, names: tuple[tuple[str, str], ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, default_stage in names:
        rows.extend(_csv_rows(directory / name, default_stage))
    return rows


def _json_summary(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    _check_safe_text(path, text)
    payload = json.loads(text)
    if not isinstance(payload, dict):
        return {}
    return dict(payload.get("summary") or payload)


def _collect_stage_rows(
    generated_resolver_sidecar_dir: Path,
    serialization_dir: Path | None,
    detail_inventory_dir: Path | None,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    statuses: dict[str, str] = {}
    explicit_rows = _csv_rows(generated_resolver_sidecar_dir / STAGE_ROW_FILE)
    if explicit_rows:
        statuses["stage_rows"] = "present"
        return explicit_rows, statuses
    statuses["stage_rows"] = "missing"

    generated_rows = _csv_rows_from_first(
        generated_resolver_sidecar_dir,
        GENERATED_FILES,
    )
    adapter_rows = _csv_rows_from_first(generated_resolver_sidecar_dir, ADAPTER_FILES)
    dedupe_rows = _csv_rows_from_first(generated_resolver_sidecar_dir, DEDUPE_FILES)
    resolver_rows = _csv_rows_from_first(
        generated_resolver_sidecar_dir,
        RESOLVER_FILES,
    )
    serialization_rows = _csv_rows(
        serialization_dir / SERIALIZATION_FILE if serialization_dir else None,
        "sidecar",
    )
    detail_rows = _csv_rows(
        detail_inventory_dir / DETAIL_FILE if detail_inventory_dir else None,
        "evaluator",
    )
    statuses.update(
        {
            "generated_rows": "present" if generated_rows else "missing",
            "adapter_rows": "present" if adapter_rows else "missing",
            "dedupe_rows": "present" if dedupe_rows else "missing",
            "resolver_rows": "present" if resolver_rows else "missing",
            "serialization_rows": "present" if serialization_rows else "missing",
            "detail_inventory_rows": "present" if detail_rows else "missing",
        }
    )
    return (
        generated_rows
        + adapter_rows
        + dedupe_rows
        + resolver_rows
        + serialization_rows
        + detail_rows,
        statuses,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# RateCon Load Generated Provenance Boundary Compare",
        "",
        "Local-only comparison over existing generated/resolver/detail sidecars.",
        "",
        f"- schema_version: {summary['schema_version']}",
        f"- candidate_count: {summary['candidate_count']}",
        f"- complete_roundtrip_count: {summary['complete_roundtrip_count']}",
        f"- first_loss_boundary: {summary['first_loss_boundary']}",
        f"- private_values_included: {summary['private_values_included']}",
        f"- private_values_redacted: {summary['private_values_redacted']}",
        f"- pdf_processing_attempted: {summary['pdf_processing_attempted']}",
        f"- ocr_attempted: {summary['ocr_attempted']}",
        f"- google_called: {summary['google_called']}",
        f"- model_or_cloud_called: {summary['model_or_cloud_called']}",
        "",
        "## Boundary Counts",
    ]
    for status, count in summary["loss_boundary_counts"].items():
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Input Statuses"])
    for key, value in summary.get("input_statuses", {}).items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def write_boundary_outputs(output_dir: Path, payload: dict[str, Any]) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary": output_dir / "load_generated_provenance_boundary_summary.json",
        "report": output_dir / "load_generated_provenance_boundary_report.md",
        "rows": output_dir / "load_generated_provenance_boundary_rows.csv",
        "loss_by_stage": output_dir / "load_generated_provenance_boundary_loss_by_stage.csv",
        "review_items": output_dir / "load_generated_provenance_boundary_review_items.csv",
    }
    _write_json(paths["summary"], payload)
    paths["report"].write_text(_report(payload), encoding="utf-8")
    _write_csv(paths["rows"], payload["boundary_rows"], BOUNDARY_ROW_FIELDNAMES)
    _write_csv(paths["loss_by_stage"], payload["loss_by_stage_rows"], ["loss_boundary", "count"])
    _write_csv(
        paths["review_items"],
        payload["review_rows"],
        [
            "document_id",
            "candidate_id",
            "loss_boundary",
            "recommended_action",
            "behavior_change_allowed",
        ],
    )
    return paths


def build_boundary_compare(args: argparse.Namespace) -> dict[str, Any]:
    sidecar_dir = _resolve(args.generated_resolver_sidecar_dir)
    if sidecar_dir is None:
        raise boundary_compare_error("generated-resolver-sidecar-dir is required")
    stage_rows, input_statuses = _collect_stage_rows(
        sidecar_dir,
        _resolve(args.serialization_dir),
        _resolve(args.detail_inventory_dir),
    )
    payload = compare_generated_provenance_boundaries(stage_rows)
    payload["summary"]["input_statuses"] = input_statuses
    current_run_dir = _resolve(getattr(args, "adapter_dedupe_current_run_dir", None))
    current_run_summary = _json_summary(
        current_run_dir / ADAPTER_DEDUPE_CURRENT_RUN_SUMMARY_FILE
        if current_run_dir is not None
        else None
    )
    payload["summary"]["adapter_dedupe_current_run_status"] = current_run_summary.get(
        "current_run_status",
        "skipped_missing_optional_dir"
        if getattr(args, "adapter_dedupe_current_run_dir", None)
        else "skipped_not_requested",
    )
    payload["summary"]["adapter_dedupe_current_run_complete_roundtrip_count"] = int(
        current_run_summary.get("sidecar", {}).get("complete_roundtrip_count") or 0
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.confirm_local_audit_run:
        raise SystemExit("--confirm-local-audit-run is required for this local-only audit.")
    output_dir = _require_output_under_local_outputs(_resolve(args.output_dir) or Path(""))
    payload = build_boundary_compare(args)
    write_boundary_outputs(output_dir, payload)
    summary = payload["summary"]
    print("RateCon load generated provenance boundary compare")
    print(f"schema_version: {LOAD_GENERATED_PROVENANCE_BOUNDARY_SCHEMA_VERSION}")
    print(f"candidate_count: {summary['candidate_count']}")
    print(f"complete_roundtrip_count: {summary['complete_roundtrip_count']}")
    print(f"first_loss_boundary: {summary['first_loss_boundary']}")
    print(f"private_values_included: {summary['private_values_included']}")
    print(f"private_values_redacted: {summary['private_values_redacted']}")
    print(f"pdf_processing_attempted: {summary['pdf_processing_attempted']}")
    print(f"ocr_attempted: {summary['ocr_attempted']}")
    print(f"google_called: {summary['google_called']}")
    print(f"model_or_cloud_called: {summary['model_or_cloud_called']}")
    print(f"output_dir: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
