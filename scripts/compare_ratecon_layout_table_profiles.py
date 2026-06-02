"""Compare safe shadow layout table-profile diagnostics.

This script reads already-generated shadow audit/summary artifacts. It does
not open private PDFs and does not require pdfplumber.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.document_ai.private_measurement_outputs import DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR  # noqa: E402
from app.document_ai.ratecon_shadow_audit import (  # noqa: E402
    RATECON_SHADOW_AUDIT_JSONL,
    RATECON_SHADOW_AUDIT_SUMMARY_JSON,
)
from app.document_ai.ratecon_shadow_root_cause_analysis import (  # noqa: E402
    analyze_ratecon_shadow_audit,
    load_shadow_audit_jsonl,
    load_shadow_summary,
)


OUTPUT_JSON = "ratecon_layout_table_profile_comparison.json"
OUTPUT_MD = "ratecon_layout_table_profile_comparison.md"
OUTPUT_CSV = "ratecon_layout_table_profile_comparison.csv"


def _safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _profile_row(profile, analysis):
    coverage = analysis.get("candidate_coverage", {}) or {}
    table_profile = analysis.get("table_profile_summary", {}) or {}
    provider = analysis.get("layout_provider_summary", {}) or {}
    layout_load = analysis.get("layout_load_pairing_summary", {}) or {}
    layout_stop = analysis.get("layout_stop_pairing_summary", {}) or {}
    failure_codes = analysis.get("failure_code_counts", {}) or {}
    return {
        "profile": profile,
        "docs_processed": _safe_int(analysis.get("documents_processed")),
        "provider_success": _safe_int((provider.get("provider_status_counts", {}) or {}).get("status:success")),
        "provider_partial": _safe_int((provider.get("provider_status_counts", {}) or {}).get("status:partial")),
        "pages_with_tables": _safe_int(provider.get("pages_with_tables")),
        "tables_detected": _safe_int(table_profile.get("tables_detected")),
        "table_cells": _safe_int(provider.get("table_cell_count")),
        "recognized_stop_tables": _safe_int(table_profile.get("recognized_stop_tables")),
        "recognized_rate_tables": _safe_int(table_profile.get("recognized_rate_tables")),
        "recognized_load_tables": _safe_int(table_profile.get("recognized_load_tables")),
        "layout_load_candidates": _safe_int(layout_load.get("layout_candidates_emitted")),
        "table_cell_load_candidates": _safe_int(layout_load.get("table_cell_pairings")),
        "layout_structured_stop_candidates": _safe_int(layout_stop.get("layout_structured_stop_candidates")),
        "ambiguous_stop_candidates": _safe_int(
            (analysis.get("stop_assembly_summary", {}) or {}).get("ambiguous_stop_candidate_count")
        ),
        "pickup_stops_present": _safe_int(
            (coverage.get("pickup_stops", {}) or {}).get("candidate_present_count")
        ),
        "delivery_stops_present": _safe_int(
            (coverage.get("delivery_stops", {}) or {}).get("candidate_present_count")
        ),
        "load_number_present": _safe_int(
            (coverage.get("load_number", {}) or {}).get("candidate_present_count")
        ),
        "table_extraction_not_available": _safe_int(failure_codes.get("TABLE_EXTRACTION_NOT_AVAILABLE")),
    }


def _parse_profile_result(value):
    parts = str(value or "").split("|")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            "--profile-result must be formatted as profile|summary.json|audit.jsonl"
        )
    return tuple(parts)


def build_parser():
    default_root = DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR
    parser = argparse.ArgumentParser(description="Compare safe RateCon table-profile shadow diagnostics.")
    parser.add_argument(
        "--profile-result",
        action="append",
        type=_parse_profile_result,
        default=[],
        help="Profile result formatted as profile|summary.json|audit.jsonl. Repeat for each profile.",
    )
    parser.add_argument(
        "--summary",
        default=str(default_root / RATECON_SHADOW_AUDIT_SUMMARY_JSON),
        help="Single-profile summary path when --profile-result is omitted.",
    )
    parser.add_argument(
        "--audit",
        default=str(default_root / RATECON_SHADOW_AUDIT_JSONL),
        help="Single-profile audit path when --profile-result is omitted.",
    )
    parser.add_argument("--profile", default="current")
    parser.add_argument("--output-dir", default=str(default_root))
    parser.add_argument("--top-n", type=int, default=25)
    return parser


def compare_profiles(profile_results, top_n=25):
    rows = []
    for profile, summary_path, audit_path in profile_results:
        analysis = analyze_ratecon_shadow_audit(
            summary=load_shadow_summary(summary_path),
            audit_records=load_shadow_audit_jsonl(audit_path),
            top_n=top_n,
        )
        rows.append(_profile_row(profile, analysis))
    best = ""
    if rows:
        best = sorted(
            rows,
            key=lambda row: (
                row["load_number_present"],
                row["recognized_stop_tables"],
                row["layout_structured_stop_candidates"],
                -row["table_extraction_not_available"],
            ),
            reverse=True,
        )[0]["profile"]
    return {
        "profiles": rows,
        "best_profile": best,
        "private_values_printed": False,
        "raw_text_printed": False,
        "money_values_printed": False,
    }


def write_outputs(comparison, output_dir):
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / OUTPUT_JSON
    md_path = output_root / OUTPUT_MD
    csv_path = output_root / OUTPUT_CSV
    json_path.write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RateCon Layout Table Profile Comparison",
        "",
        "Safe local comparison. No private values or full text are required.",
        "",
        f"- best_profile: {comparison.get('best_profile', '')}",
        "",
        "## Profiles",
    ]
    for row in comparison.get("profiles", []) or []:
        lines.extend(
            [
                f"- profile: {row.get('profile')}",
                f"  - docs_processed: {row.get('docs_processed')}",
                f"  - tables_detected: {row.get('tables_detected')}",
                f"  - recognized_load_tables: {row.get('recognized_load_tables')}",
                f"  - recognized_stop_tables: {row.get('recognized_stop_tables')}",
                f"  - table_cell_load_candidates: {row.get('table_cell_load_candidates')}",
                f"  - load_number_present: {row.get('load_number_present')}",
                f"  - pickup_stops_present: {row.get('pickup_stops_present')}",
                f"  - delivery_stops_present: {row.get('delivery_stops_present')}",
            ]
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rows = comparison.get("profiles", []) or []
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        if rows:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            writer = csv.writer(handle)
            writer.writerow(["profile"])
    return {"json": json_path.name, "md": md_path.name, "csv": csv_path.name}


def main(argv=None):
    args = build_parser().parse_args(argv)
    profile_results = args.profile_result or [(args.profile, args.summary, args.audit)]
    comparison = compare_profiles(profile_results, top_n=args.top_n)
    files = write_outputs(comparison, args.output_dir)
    print(
        "ratecon_layout_table_profile_comparison_written: "
        f"{{'files': {files}, 'profiles': {len(comparison.get('profiles', []))}, "
        f"'best_profile': '{comparison.get('best_profile', '')}', "
        "'private_values_printed': False, 'raw_text_printed': False, 'money_values_printed': False}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
