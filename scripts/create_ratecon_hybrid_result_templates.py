"""Create blank local-only RateCon hybrid result templates.

The generator reads only safe document identifiers from an existing audit JSONL
or creates a single generic template when no audit is available. It does not
fill private extraction values by default and does not call models, OCR, cloud,
or PDF processing.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.ratecon_hybrid_contract import (  # noqa: E402
    build_hybrid_result_template,
    is_under_local_outputs,
)


DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_hybrid_result_templates")


class HybridTemplateError(ValueError):
    """Raised when template generation would be unsafe."""


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _read_audit_records(path: Path | None) -> list[dict]:
    if not path:
        return []
    resolved = _repo_relative(path)
    if not resolved.exists():
        return []
    records = []
    with resolved.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                payload = json.loads(line)
                if isinstance(payload, dict):
                    records.append(payload)
    return records


def _safe_document_rows(records: list[dict], include_private_values_local_only: bool) -> list[dict]:
    rows = []
    if not records:
        return [{"document_id": "RATECON_001", "file_name": "", "file_hash_prefix": ""}]
    for index, record in enumerate(records, start=1):
        document_id = str(record.get("document_id") or f"RATECON_{index:03d}")
        row = {
            "document_id": document_id,
            "file_name": str(record.get("file_name") or "") if include_private_values_local_only else "",
            "file_hash_prefix": str(record.get("file_hash_prefix") or "") if include_private_values_local_only else "",
        }
        rows.append(row)
    return rows


def _template_file_name(document_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in document_id)
    return f"{safe or 'RATECON_001'}.hybrid_result.json"


def create_hybrid_result_templates(
    *,
    audit: Path | None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    include_private_values_local_only: bool = False,
) -> dict:
    if not is_under_local_outputs(output_dir, REPO_ROOT):
        raise HybridTemplateError("Output directory must be under .local_outputs.")
    resolved_output = _repo_relative(output_dir)
    resolved_output.mkdir(parents=True, exist_ok=True)
    rows = _safe_document_rows(_read_audit_records(audit), include_private_values_local_only)
    index_rows = []
    for row in rows:
        template = build_hybrid_result_template(row["document_id"])
        if include_private_values_local_only:
            template["file_name"] = row.get("file_name") or ""
            template["file_hash_prefix"] = row.get("file_hash_prefix") or ""
        file_name = _template_file_name(row["document_id"])
        (resolved_output / file_name).write_text(
            json.dumps(template, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        index_rows.append(
            {
                "document_id": row["document_id"],
                "template_file": file_name,
                "stops_review_required": True,
                "stop_auto_accept": False,
                "private_values_included": bool(include_private_values_local_only),
            }
        )
    with (resolved_output / "hybrid_template_index.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "document_id",
                "template_file",
                "stops_review_required",
                "stop_auto_accept",
                "private_values_included",
            ],
        )
        writer.writeheader()
        writer.writerows(index_rows)
    readme = """# RateCon Hybrid Result Templates

These templates are local-only scaffolds for future human or model-filled hybrid
results. They contain no extracted private values by default. Fill the JSON
objects manually or with a future local/model pipeline, then run
`scripts/run_ratecon_hybrid_benchmark.py` to validate and score them.

Phase 1 policy: all stops are review-required and `auto_accept=false`.
"""
    (resolved_output / "hybrid_template_readme.md").write_text(readme, encoding="utf-8")
    return {
        "output_dir": str(output_dir),
        "template_count": len(index_rows),
        "private_values_included": bool(include_private_values_local_only),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create local-only RateCon hybrid result templates.")
    parser.add_argument("--audit", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required for local private template generation")
    summary = create_hybrid_result_templates(
        audit=args.audit,
        output_dir=args.output_dir,
        include_private_values_local_only=args.include_private_values_local_only,
    )
    print("RateCon hybrid template summary")
    print(f"output_dir: {summary['output_dir']}")
    print(f"template_count: {summary['template_count']}")
    print(f"private_values_included: {summary['private_values_included']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
