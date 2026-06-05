"""Create local-only RateCon load resolver-to-audit provenance sidecars.

This script reads existing resolver sidecar and audit JSONL outputs only. It
does not run private measurement, process PDFs, invoke OCR, call Google, call
model/cloud services, or change selected load-number behavior.
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

from app.document_ai.load_identifier_resolver_to_audit_provenance import (  # noqa: E402
    LOAD_RESOLVER_TO_AUDIT_PROVENANCE_SCHEMA_VERSION,
    audit_rows_from_payloads,
    build_resolver_to_audit_provenance_sidecar,
    write_resolver_to_audit_outputs,
)


RESOLVER_VISIBLE_FILE = "load_resolver_visible_candidates.csv"
FORBIDDEN_PRIVATE_MARKERS = (
    ".gold.json",
    "api_key",
    "service account",
    "google token",
    "raw extracted",
    "private pdf",
    "data/private_ratecons",
)


class resolver_to_audit_error(ValueError):
    """Raised for safe user-facing resolver-to-audit failures."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create local-only RateCon load resolver-to-audit provenance sidecars."
    )
    parser.add_argument("--generated-resolver-sidecar-dir", required=True)
    parser.add_argument("--audit")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    return parser.parse_args(argv)


def _resolve(path: str | Path | None) -> Path | None:
    if not path:
        return None
    return Path(path).expanduser().resolve()


def _require_output_under_local_outputs(path: Path) -> Path:
    resolved = path.resolve()
    if ".local_outputs" not in resolved.parts:
        raise resolver_to_audit_error("output-dir must be inside .local_outputs")
    return resolved


def _check_safe_text(path: Path, text: str) -> None:
    if path.name.endswith(".jsonl"):
        return
    lower = text.lower()
    hits = [marker for marker in FORBIDDEN_PRIVATE_MARKERS if marker in lower]
    if hits:
        raise resolver_to_audit_error(
            f"input contains forbidden private markers: {path.name}: {hits}"
        )


def _csv_rows(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    _check_safe_text(path, text)
    return [dict(row) for row in csv.DictReader(text.splitlines())]


def _jsonl_payloads(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def build_sidecar(args: argparse.Namespace) -> dict[str, Any]:
    sidecar_dir = _resolve(args.generated_resolver_sidecar_dir)
    if sidecar_dir is None:
        raise resolver_to_audit_error("generated-resolver-sidecar-dir is required")
    return build_resolver_to_audit_provenance_sidecar(
        resolver_rows=_csv_rows(sidecar_dir / RESOLVER_VISIBLE_FILE),
        audit_rows=audit_rows_from_payloads(_jsonl_payloads(_resolve(args.audit))),
        include_private_values=bool(args.include_private_values_local_only),
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.confirm_private_local_run:
        raise SystemExit("--confirm-private-local-run is required for this local-only sidecar.")
    try:
        output_dir = _require_output_under_local_outputs(_resolve(args.output_dir) or Path(""))
        payload = build_sidecar(args)
        write_resolver_to_audit_outputs(output_dir, payload)
    except (OSError, resolver_to_audit_error, json.JSONDecodeError) as exc:
        print(f"resolver_to_audit_error: {exc}", file=sys.stderr)
        return 1

    summary = payload["summary"]
    print("RateCon load resolver-to-audit provenance sidecar")
    print(f"schema_version: {LOAD_RESOLVER_TO_AUDIT_PROVENANCE_SCHEMA_VERSION}")
    print(f"resolver_visible_candidate_count: {summary['resolver_visible_candidate_count']}")
    print(f"audit_candidate_count: {summary['audit_candidate_count']}")
    print(f"resolver_to_audit_preserved_count: {summary['resolver_to_audit_preserved_count']}")
    print(f"resolver_to_audit_loss_count: {summary['resolver_to_audit_loss_count']}")
    print(f"resolver_to_audit_status_counts: {summary['resolver_to_audit_status_counts']}")
    print(f"private_values_redacted: {summary['private_values_redacted']}")
    print(f"pdf_processing_attempted: {summary['pdf_processing_attempted']}")
    print(f"ocr_attempted: {summary['ocr_attempted']}")
    print(f"google_called: {summary['google_called']}")
    print(f"model_or_cloud_called: {summary['model_or_cloud_called']}")
    print(f"output_dir: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
