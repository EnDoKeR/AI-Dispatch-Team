import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.intake.ratecon_text_dry_run import (  # noqa: E402
    run_ratecon_text_dry_run,
)


SAMPLE_TEXT = """
Broker: Synthetic Manual Broker
Broker MC: 000123
Rate: 3400
Pickup: Dallas, TX
Pickup Date: 2026-09-01
Pickup Time: 08:00
Delivery: Denver, CO
Delivery Date: 2026-09-03
Delivery Time: 09:00
Commodity: Synthetic steel
Weight: 40000
Reference: SYN-MANUAL-001
Equipment: Conestoga
Special Requirements: APPOINTMENT_REQUIRED
""".strip()


SAMPLE_CASE = {
    "case_id": "CASE-MANUAL-001",
    "reference_id": "SYN-MANUAL-001",
    "broker_name": "Synthetic Manual Broker",
    "broker_mc": "000123",
    "pickup": "Dallas, TX",
    "delivery": "Denver, CO",
    "rate": 3400,
}


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
        description="Manual local RateCon text dry-run. No files are read."
    )
    parser.add_argument(
        "--text",
        default=None,
        help="Manual pasted RateCon-like text. If omitted, sample mode is used.",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read pasted text from terminal stdin. No files are read.",
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


def confidence_text(field_confidence):
    if not field_confidence:
        return "none"

    return ", ".join(
        f"{field_name}: {field_confidence[field_name]}"
        for field_name in sorted(field_confidence)
    )


def selected_text(args):
    if args.stdin and args.text is not None:
        raise ValueError("Use either --text or --stdin, not both.")

    if args.stdin:
        return sys.stdin.read(), "stdin", None

    if args.text is not None:
        return args.text, "manual text", None

    return SAMPLE_TEXT, "sample", SAMPLE_CASE


def format_result(result, input_mode):
    record = result["intake_record"]
    parser_output = result["parser_output"]
    candidate = result["link_candidate"]
    lines = [
        "MANUAL RATECON TEXT DRY RUN",
        "DRY RUN ONLY - no private text saved, no cases linked or created",
        f"Input mode: {input_mode}",
        f"Status: {result['status']}",
        "",
        "Extracted parser fields:",
    ]

    for field_name, label in DISPLAY_FIELDS:
        lines.append(f"- {label}: {safe_value(record.get(field_name, ''))}")

    lines.append(
        "- Special requirements: "
        + list_text(record.get("special_requirements", []))
    )
    lines.append("")
    lines.append(
        "Confidence: "
        + confidence_text(parser_output.get("field_confidence", {}))
    )
    lines.append("Missing fields: " + list_text(result["intake_summary"]["missing_fields"]))
    lines.append(
        "Needs-check fields: "
        + list_text(result["intake_summary"]["needs_check_fields"])
    )
    lines.append("Warnings: " + list_text(result["warnings"]))
    lines.append("")

    if candidate:
        lines.append("Link candidate:")
        lines.append(f"- Recommended action: {candidate['recommended_action']}")
        lines.append(f"- Approval required: {candidate['approval_required']}")
        lines.append(f"- Match score: {candidate['match_score']}")
        lines.append(
            "- Match reasons: " + list_text(candidate["match_reasons"])
        )
        lines.append(
            "- Mismatch reasons: " + list_text(candidate["mismatch_reasons"])
        )
    else:
        lines.append("Link candidate: none")

    lines.append("")
    lines.append(f"Private text saved: {result['private_text_saved']}")
    lines.append(f"Cases created: {result['cases_created']}")
    lines.append(f"Events written: {result['events_written']}")

    return "\n".join(lines)


def main(argv=None):
    args = build_parser().parse_args(argv)

    try:
        text, input_mode, case_record = selected_text(args)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    result = run_ratecon_text_dry_run(text, case_record=case_record)

    print(format_result(result, input_mode))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
