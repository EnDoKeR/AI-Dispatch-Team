"""Generate simplified local RateCon review packet v2.

The command reads ignored local review CSVs and writes a smaller local-only
packet. Console output is limited to counts and artifact basenames.
"""

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)
from app.document_ai.ratecon_review_workbook import (
    REVIEW_DOCUMENT_SUMMARY_CSV,
    REVIEW_FIELD_REVIEW_CSV,
    REVIEW_RATE_REVIEW_CSV,
    REVIEW_STOP_REVIEW_CSV,
    SHEET_V2_CORE_FIELDS,
    SHEET_V2_DOCUMENT_SUMMARY,
    SHEET_V2_INSTRUCTIONS,
    SHEET_V2_LOAD_IDS,
    SHEET_V2_RATES,
    SHEET_V2_STOPS,
    V2_CORE_FIELD_NAMES,
    V2_STOP_FIELD_NAMES,
    _v2_instruction_rows,
    write_ratecon_review_v2_rows_artifacts,
)


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Generate a simplified local-only RateCon review packet v2."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR),
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR),
    )
    parser.add_argument("--include-private-values-local-only", action="store_true")
    parser.add_argument("--natural-sort-inputs", action="store_true")
    return parser


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _blank_private(row, include_private_values):
    return _text(row.get("Predicted Value LOCAL ONLY")) if include_private_values else ""


def _sort_key(row):
    order = _text(row.get("Folder Order"))
    try:
        order_value = int(order)
    except ValueError:
        order_value = 0
    return (
        order_value,
        _text(row.get("Measurement Alias")),
        _text(row.get("Stop ID")),
        _text(row.get("Field Name")),
    )


def _top_blockers(row):
    blockers = []
    for column in (
        "Intake Core Blockers",
        "Extraction Review Blockers",
        "Dispatch Decision Blockers",
        "Top Blocker",
    ):
        value = _text(row.get(column))
        if value:
            blockers.extend(part for part in value.split(";") if part)
    return ";".join(dict.fromkeys(blockers))


def _review_priority(row):
    value = _text(row.get("Recommended Review Priority"))
    if value:
        return value
    return "high" if _token(row.get("Readiness Level")) == "not_ready" else "normal"


def _document_rows(rows):
    output = []
    for row in rows:
        output.append(
            {
                "Folder Order": row.get("Folder Order", ""),
                "Local Document Name / File Stem": row.get(
                    "Local Document Name / File Stem",
                    "",
                ),
                "Measurement Alias": row.get("Measurement Alias", ""),
                "Document Type": row.get("Document Type", ""),
                "OCR Needed": row.get("OCR Needed", ""),
                "Extraction Relevant": row.get("Extraction Relevant", ""),
                "Readiness Level": row.get("Readiness Level", ""),
                "Top Blockers": _top_blockers(row),
                "Review Priority": _review_priority(row),
                "User Document Type Correct?": "",
                "User Notes Local Only": "",
            }
        )
    return output


def _rate_index(rate_rows):
    by_alias = {}
    for row in rate_rows:
        alias = _text(row.get("Measurement Alias"))
        if alias:
            by_alias.setdefault(alias, []).append(row)
    return by_alias


def _core_rows(field_rows, rate_rows_by_alias, include_private_values):
    rows = []
    for row in field_rows:
        field_name = _token(row.get("Field Name"))
        if field_name not in V2_CORE_FIELD_NAMES:
            continue
        alias = _text(row.get("Measurement Alias"))
        rate_row = (rate_rows_by_alias.get(alias) or [{}])[0]
        candidate_count = row.get("Load Identifier Candidate Count", "")
        gap_reason = row.get("Policy Gap Reason", "")
        if field_name == "rate":
            candidate_count = rate_row.get("Main Rate Candidate Count", candidate_count)
            gap_reason = rate_row.get("Rate Conflict Reason", gap_reason)
        if field_name == "load_number":
            gap_reason = row.get("Load Identifier Gap Reason", gap_reason)
        rows.append(
            {
                "Measurement Alias": alias,
                "Field Name": field_name,
                "Predicted Value LOCAL ONLY": _blank_private(
                    row,
                    include_private_values,
                ),
                "Predicted Status": row.get("Status", ""),
                "Needs Review": row.get("Needs Review", ""),
                "Candidate Count": candidate_count,
                "Gap Reason": gap_reason,
                "Evidence Type": row.get("Evidence Type", ""),
                "User Correct? yes/no/unknown": "",
                "User Expected Value LOCAL ONLY": "",
                "User Issue Type": "",
                "User Notes Local Only": "",
            }
        )
    return rows


def _stop_rows(stop_rows, include_private_values):
    rows = []
    for row in stop_rows:
        stop_type = _token(row.get("Stop Type"))
        field_name = _token(row.get("Field Name"))
        if stop_type not in {"pickup", "delivery"}:
            continue
        if field_name not in V2_STOP_FIELD_NAMES and _token(row.get("Needs Review")) != "yes":
            continue
        rows.append(
            {
                "Measurement Alias": row.get("Measurement Alias", ""),
                "Stop ID": row.get("Stop ID", ""),
                "Stop Type": row.get("Stop Type", ""),
                "Sequence": row.get("Stop Sequence", ""),
                "Field Name": row.get("Field Name", ""),
                "Predicted Value LOCAL ONLY": _blank_private(
                    row,
                    include_private_values,
                ),
                "Status": row.get("Status", ""),
                "User Correct? yes/no/unknown": "",
                "User Expected Value LOCAL ONLY": "",
                "User Issue Type": "",
            }
        )
    return rows


def _rate_rows(rate_rows, include_private_values):
    rows = []
    for row in rate_rows:
        rows.append(
            {
                "Measurement Alias": row.get("Measurement Alias", ""),
                "Rate Candidate Type": row.get("Rate Field Type", ""),
                "Predicted Value LOCAL ONLY": _blank_private(
                    row,
                    include_private_values,
                ),
                "Status": row.get("Status", ""),
                "Conflict Reason": row.get("Rate Conflict Reason", ""),
                "Main Rate? yes/no/unknown": row.get("Main Rate? yes/no/unknown", ""),
                "User Correct? yes/no/unknown": "",
                "User Issue Type": "",
            }
        )
    return rows


def _positive_int(value):
    try:
        return max(int(value or 0), 0)
    except ValueError:
        return 0


def _load_id_rows(field_rows, include_private_values):
    rows = []
    for row in field_rows:
        if _token(row.get("Field Name")) != "load_number":
            continue
        primary_count = _positive_int(row.get("Load Identifier Candidate Count"))
        rejected_count = _positive_int(row.get("Rejected Non-primary Reference Count"))
        identifier_type = _text(row.get("Primary Load Identifier Candidate Type"))
        if primary_count:
            rows.append(
                {
                    "Measurement Alias": row.get("Measurement Alias", ""),
                    "Identifier Type": identifier_type or "load_number",
                    "Predicted Value LOCAL ONLY": _blank_private(
                        row,
                        include_private_values,
                    ),
                    "Primary Candidate?": "yes",
                    "Rejected Non-primary?": "no",
                    "User Correct? yes/no/unknown": "",
                    "User Issue Type": "",
                }
            )
        if rejected_count:
            rows.append(
                {
                    "Measurement Alias": row.get("Measurement Alias", ""),
                    "Identifier Type": "non_primary_reference",
                    "Predicted Value LOCAL ONLY": "",
                    "Primary Candidate?": "no",
                    "Rejected Non-primary?": "yes",
                    "User Correct? yes/no/unknown": "",
                    "User Issue Type": "",
                }
            )
        if not primary_count and not rejected_count:
            rows.append(
                {
                    "Measurement Alias": row.get("Measurement Alias", ""),
                    "Identifier Type": "load_number",
                    "Predicted Value LOCAL ONLY": "",
                    "Primary Candidate?": "no",
                    "Rejected Non-primary?": "no",
                    "User Correct? yes/no/unknown": "",
                    "User Issue Type": "",
                }
            )
    return rows


def build_v2_rows_from_review_csvs(input_dir, include_private_values=False):
    root = Path(input_dir)
    document_rows = _read_csv(root / REVIEW_DOCUMENT_SUMMARY_CSV)
    stop_rows = _read_csv(root / REVIEW_STOP_REVIEW_CSV)
    field_rows = _read_csv(root / REVIEW_FIELD_REVIEW_CSV)
    rate_rows = _read_csv(root / REVIEW_RATE_REVIEW_CSV)
    rate_rows_by_alias = _rate_index(rate_rows)

    rows_by_sheet = {
        SHEET_V2_INSTRUCTIONS: _v2_instruction_rows(
            include_private_values=include_private_values
        ),
        SHEET_V2_DOCUMENT_SUMMARY: _document_rows(document_rows),
        SHEET_V2_CORE_FIELDS: _core_rows(
            field_rows,
            rate_rows_by_alias,
            include_private_values,
        ),
        SHEET_V2_STOPS: _stop_rows(stop_rows, include_private_values),
        SHEET_V2_RATES: _rate_rows(rate_rows, include_private_values),
        SHEET_V2_LOAD_IDS: _load_id_rows(field_rows, include_private_values),
    }
    return {
        sheet: sorted(rows, key=_sort_key)
        if sheet != SHEET_V2_INSTRUCTIONS
        else rows
        for sheet, rows in rows_by_sheet.items()
    }


def main(argv=None):
    args = _build_parser().parse_args(argv)
    rows_by_sheet = build_v2_rows_from_review_csvs(
        args.input_dir,
        include_private_values=args.include_private_values_local_only,
    )
    result = write_ratecon_review_v2_rows_artifacts(
        rows_by_sheet,
        output_dir=args.output_dir,
        write_workbook=True,
        write_csvs=True,
        allow_custom_output_dir=True,
    )
    summary = result["summary"]
    print("RateCon review packet v2 summary")
    print(f"document_rows: {summary.get('document_rows', 0)}")
    print(f"core_field_rows: {summary.get('core_field_rows', 0)}")
    print(f"stop_rows: {summary.get('stop_rows', 0)}")
    print(f"rate_rows: {summary.get('rate_rows', 0)}")
    print(f"load_id_rows: {summary.get('load_id_rows', 0)}")
    print(
        "outputs_written: "
        f"{sorted(path.name for path in result.get('paths', {}).values())}"
    )
    print(
        "include_private_values_local_only: "
        f"{bool(args.include_private_values_local_only)}"
    )
    print("private_values_printed: False")
    print("raw_text_printed: False")
    print("local_paths_printed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
