import argparse
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.market_intelligence.intake_record_summary import (
    build_intake_record_summary,
    format_intake_record_summary,
)
from app.market_intelligence.intake_record_repository import (
    INTAKE_RECORDS_FILE,
    upsert_intake_record,
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
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--json",
        dest="json_text",
        help="JSON object string with intake fields.",
    )
    input_group.add_argument(
        "--json-file",
        dest="json_file",
        help="Local JSON file containing one intake record object.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the normalized intake record to the local JSON repository.",
    )
    parser.add_argument(
        "--records-file",
        default=INTAKE_RECORDS_FILE,
        help="JSON repository path for --save.",
    )

    return parser.parse_args(args)


def load_json_source(json_text):
    try:
        source = json.loads(json_text)
    except json.JSONDecodeError as error:
        print(DRY_RUN_WARNING)
        print(f"Invalid JSON input: {error.msg}")
        return None, 1

    if not isinstance(source, dict):
        print(DRY_RUN_WARNING)
        print("JSON input must be an object.")
        return None, 1

    return source, 0


def load_json_file(file_path):
    path = Path(file_path)

    try:
        json_text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(DRY_RUN_WARNING)
        print(f"JSON file not found: {file_path}")
        return None, 1
    except OSError as error:
        print(DRY_RUN_WARNING)
        print(f"Could not read JSON file: {error}")
        return None, 1

    return load_json_source(json_text)


def source_from_args(args):
    if args.json_text:
        return load_json_source(args.json_text)

    if args.json_file:
        return load_json_file(args.json_file)

    return SAMPLE_SOURCE, 0


def saved_record_from_summary(summary):
    record = dict(summary["intake_record"])
    record["status"] = summary["status"]

    return record


def save_summary_record(summary, records_file):
    return upsert_intake_record(
        saved_record_from_summary(summary),
        records_file,
    )


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

    if parsed_args.save:
        saved_record = save_summary_record(summary, parsed_args.records_file)
        print(f"Saved intake record: {saved_record['intake_id'] or 'NO ID'}")
        print(f"Records file: {parsed_args.records_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
