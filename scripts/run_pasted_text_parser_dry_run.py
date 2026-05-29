import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.market_intelligence.intake.parser_contract import normalize_parser_output
from app.market_intelligence.intake.pasted_text_parser_adapter import (
    parse_pasted_text_to_parser_output,
)
from app.market_intelligence.intake.summary import build_intake_record_summary


SAMPLE_PASTED_TEXT = """
Broker: Synthetic CLI Broker
Broker MC: SYNTH-MC-CLI
Rate: 3200
Pickup: Dallas, TX
Pickup Date: 2026-08-01
Pickup Time: 08:00
Delivery: Denver, CO
Delivery Date: 2026-08-03
Delivery Time: 09:00
Commodity: Synthetic steel
Weight: 40000
Reference: SYNTH-CLI-001
Equipment: Conestoga
Special Requirements: CONESTOGA_REQUIRED
""".strip()

DISPLAY_FIELDS = [
    ("broker_name", "Broker"),
    ("broker_mc", "Broker MC"),
    ("rate", "Rate"),
    ("pickup_location", "Pickup"),
    ("pickup_date", "Pickup date"),
    ("pickup_time", "Pickup time"),
    ("delivery_location", "Delivery"),
    ("delivery_date", "Delivery date"),
    ("delivery_time", "Delivery time"),
    ("commodity", "Commodity"),
    ("weight", "Weight"),
    ("reference_id", "Reference ID"),
    ("equipment", "Equipment"),
]


def build_parser():
    parser = argparse.ArgumentParser(
        description="Dry-run synthetic/manual pasted RateCon text parsing."
    )
    parser.add_argument(
        "--text",
        default=None,
        help="Pasted synthetic/manual RateCon-like text. If omitted, sample mode is used.",
    )

    return parser


def safe_value(value):
    if value in ["", None, []]:
        return "MISSING"

    return str(value)


def list_text(values):
    if not values:
        return "none"

    return ", ".join(str(value) for value in values)


def format_confidence(field_confidence):
    if not field_confidence:
        return ["- none"]

    return [
        f"- {field_name}: {field_confidence[field_name]}"
        for field_name in sorted(field_confidence)
    ]


def build_dry_run_summary(text):
    parser_output = parse_pasted_text_to_parser_output(text)
    record = normalize_parser_output(parser_output)
    summary = build_intake_record_summary(record)

    return {
        "parser_output": parser_output,
        "intake_record": record,
        "summary": summary,
    }


def format_dry_run_summary(result, sample_mode=False):
    parser_output = result["parser_output"]
    record = result["intake_record"]
    summary = result["summary"]
    lines = [
        "PASTED TEXT PARSER DRY RUN",
        "DRY RUN ONLY - pasted text only, no PDF/OCR/private file processing",
        f"Input mode: {'sample' if sample_mode else 'manual text'}",
        f"Status: {summary['status']}",
        "",
        "Extracted fields:",
    ]

    for field_name, label in DISPLAY_FIELDS:
        lines.append(f"- {label}: {safe_value(record.get(field_name, ''))}")

    lines.append(
        "- Special requirements: "
        + list_text(record.get("special_requirements", []))
    )
    lines.append("")
    lines.append("Field confidence:")
    lines.extend(format_confidence(parser_output.get("field_confidence", {})))
    lines.append("")
    lines.append("Missing fields: " + list_text(summary["missing_fields"]))
    lines.append("Needs-check fields: " + list_text(summary["needs_check_fields"]))

    return "\n".join(lines)


def main(argv=None):
    args = build_parser().parse_args(argv)
    sample_mode = args.text is None
    text = SAMPLE_PASTED_TEXT if sample_mode else args.text
    result = build_dry_run_summary(text)

    print(format_dry_run_summary(result, sample_mode=sample_mode))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
