from copy import deepcopy

from app.market_intelligence.intake.repository import (
    INTAKE_RECORDS_FILE,
    load_intake_records,
    record_status,
)


REPORT_STATUSES = [
    "READY_FOR_REVIEW",
    "MISSING_FIELDS",
    "NEEDS_CHECK",
]


INTAKE_REPORT_FIELDS = [
    "intake_id",
    "status",
    "broker_name",
    "rate",
    "pickup_location",
    "delivery_location",
    "missing_fields",
    "needs_check_fields",
]


def summarize_intake_record(record):
    return {
        field: deepcopy((record or {}).get(field, [] if field.endswith("_fields") else ""))
        for field in INTAKE_REPORT_FIELDS
    }


def build_status_counts(records):
    counts = {status: 0 for status in REPORT_STATUSES}

    for record in records:
        status = record_status(record)
        if status not in counts:
            counts[status] = 0
        counts[status] += 1

    return counts


def build_intake_record_report(file_path=INTAKE_RECORDS_FILE):
    records = load_intake_records(file_path)

    return {
        "total_records": len(records),
        "status_counts": build_status_counts(records),
        "records": [
            summarize_intake_record(record)
            for record in records
        ],
    }


def safe_text(value, fallback="NEEDS CHECK"):
    text = str(value or "").strip()
    return text if text else fallback


def number_text(value):
    if value in ["", None]:
        return "0"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    if number.is_integer():
        return str(int(number))

    return str(number)


def money_text(value):
    return f"${number_text(value)}"


def list_text(values):
    if not values:
        return "none"

    return ", ".join(str(value) for value in values)


def format_record_line(record):
    lines = [
        f"- Intake ID: {safe_text(record.get('intake_id', ''))}",
        f"  Status: {safe_text(record.get('status', ''))}",
        f"  Broker: {safe_text(record.get('broker_name', ''))}",
        f"  Rate: {money_text(record.get('rate', 0))}",
        f"  Pickup: {safe_text(record.get('pickup_location', ''))}",
        f"  Delivery: {safe_text(record.get('delivery_location', ''))}",
        f"  Missing fields: {list_text(record.get('missing_fields', []))}",
        f"  Needs-check fields: {list_text(record.get('needs_check_fields', []))}",
    ]

    return "\n".join(lines)


def format_intake_record_report(report):
    report = report or {}
    status_counts = report.get("status_counts", {})
    lines = [
        "INTAKE RECORDS DRY-RUN REPORT",
        "-----------------------------",
        f"Total records: {report.get('total_records', 0)}",
        "",
        "Status counts:",
    ]

    for status in REPORT_STATUSES:
        lines.append(f"- {status}: {status_counts.get(status, 0)}")

    records = report.get("records", [])

    if not records:
        lines.append("")
        lines.append("No intake records found.")
        return "\n".join(lines)

    lines.append("")
    lines.append("Records:")
    lines.append("--------")

    for index, record in enumerate(records):
        if index:
            lines.append("")
        lines.append(format_record_line(record))

    return "\n".join(lines)
