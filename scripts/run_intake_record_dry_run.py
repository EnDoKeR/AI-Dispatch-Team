import argparse
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.market_intelligence.intake_record_summary import (
    build_intake_record_summary,
    format_intake_record_summary,
)


SAMPLE_SOURCE = {
    "source_type": "manual_dry_run",
    "source_file_name": "synthetic_ratecon_sample.pdf",
    "broker_name": "Synthetic Broker",
    "broker_mc": "123456",
    "rate": 3200,
    "pickup_location": "Dallas, TX",
    "pickup_date": "2026-05-30",
    "pickup_time": "08:00",
    "delivery_location": "Denver, CO",
    "delivery_date": "2026-05-31",
    "delivery_time": "09:00",
    "commodity": "Steel coils",
    "weight": 42000,
    "reference_id": "SYNTH-RC-001",
    "equipment": "Conestoga",
    "special_requirements": ["TARPS", "APPOINTMENT_REQUIRED"],
}


DRY_RUN_WARNING = "DRY RUN ONLY - no parser/storage/integration used"


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Run a manual intake record dry-run summary.",
    )
    parser.add_argument(
        "--json",
        dest="json_text",
        help="JSON object string with intake fields.",
    )

    return parser.parse_args(args)


def source_from_args(args):
    if not args.json_text:
        return SAMPLE_SOURCE, 0

    try:
        source = json.loads(args.json_text)
    except json.JSONDecodeError as error:
        print(DRY_RUN_WARNING)
        print(f"Invalid JSON input: {error.msg}")
        return None, 1

    if not isinstance(source, dict):
        print(DRY_RUN_WARNING)
        print("JSON input must be an object.")
        return None, 1

    return source, 0


def main(args=None):
    if args is None:
        args = []

    parsed_args = parse_args(args)
    source, error_code = source_from_args(parsed_args)

    if error_code:
        return error_code

    summary = build_intake_record_summary(
        source,
        received_at_utc="2026-05-29T10:00:00Z",
        intake_id="DRY-RUN-INTAKE-1",
    )

    print(format_intake_record_summary(summary))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
