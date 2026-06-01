"""Generate one-row-per-document dispatcher review table v3."""

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.dispatcher_review_table import (
    build_dispatcher_review_table_from_rows,
    write_dispatcher_review_v3_artifacts,
)
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)
from app.document_ai.ratecon_review_workbook import (
    REVIEW_FIELD_REVIEW_CSV,
    REVIEW_V2_CORE_FIELDS_CSV,
    REVIEW_V2_DOCUMENT_SUMMARY_CSV,
    REVIEW_V2_LOAD_IDS_CSV,
    REVIEW_V2_RATES_CSV,
    REVIEW_V2_STOPS_CSV,
)


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Generate a local dispatcher-style RateCon review table v3."
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


def _read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _missing_required(root):
    required = [
        REVIEW_V2_DOCUMENT_SUMMARY_CSV,
        REVIEW_V2_CORE_FIELDS_CSV,
        REVIEW_V2_STOPS_CSV,
        REVIEW_V2_RATES_CSV,
        REVIEW_V2_LOAD_IDS_CSV,
    ]
    return [name for name in required if not (root / name).exists()]


def build_dispatcher_review_table_from_local_outputs(
    input_dir,
    include_private_values=False,
):
    root = Path(input_dir)
    missing = _missing_required(root)
    if missing:
        raise FileNotFoundError(
            "missing required local review outputs: " + ",".join(missing)
        )
    return build_dispatcher_review_table_from_rows(
        _read_csv(root / REVIEW_V2_DOCUMENT_SUMMARY_CSV),
        core_field_rows=_read_csv(root / REVIEW_V2_CORE_FIELDS_CSV),
        stop_rows=_read_csv(root / REVIEW_V2_STOPS_CSV),
        rate_rows=_read_csv(root / REVIEW_V2_RATES_CSV),
        load_id_rows=_read_csv(root / REVIEW_V2_LOAD_IDS_CSV),
        detailed_field_rows=_read_csv(root / REVIEW_FIELD_REVIEW_CSV),
        include_private_values=include_private_values,
    )


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        table = build_dispatcher_review_table_from_local_outputs(
            args.input_dir,
            include_private_values=args.include_private_values_local_only,
        )
    except FileNotFoundError as exc:
        print(f"dispatcher_review_table_v3_error: {exc}")
        return 2

    result = write_dispatcher_review_v3_artifacts(
        table["dispatcher_rows"],
        table["audit_rows"],
        output_dir=args.output_dir,
        include_private_values=args.include_private_values_local_only,
        allow_custom_output_dir=True,
    )
    summary = result["summary"]
    print("Dispatcher review table v3 summary")
    print(f"document_rows: {summary.get('document_rows', 0)}")
    print(f"audit_rows: {summary.get('audit_rows', 0)}")
    print(
        "outputs_written: "
        f"{sorted(path.name for path in result.get('paths', {}).values())}"
    )
    print(
        "include_private_values_local_only: "
        f"{bool(args.include_private_values_local_only)}"
    )
    print("private_values_printed: False")
    print("money_values_printed: False")
    print("raw_text_printed: False")
    print("local_paths_printed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
