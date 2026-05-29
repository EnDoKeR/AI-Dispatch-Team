from app.market_intelligence.intake_record import build_intake_record
from app.market_intelligence.intake_record_status import (
    classify_intake_record_status,
    intake_record_ready_for_review,
)


SUMMARY_IMPORT_FIELDS = [
    "intake_id",
    "source_type",
    "source_file_name",
    "received_at_utc",
    "broker_name",
    "broker_mc",
    "rate",
    "pickup_location",
    "pickup_date",
    "pickup_time",
    "delivery_location",
    "delivery_date",
    "delivery_time",
    "commodity",
    "weight",
    "reference_id",
    "equipment",
    "linked_dispatch_case_id",
]


def has_value(value):
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)

    return value != ""


def build_imported_fields(record):
    imported_fields = []

    for field_name in SUMMARY_IMPORT_FIELDS:
        if has_value(record.get(field_name, "")):
            imported_fields.append(field_name)

    if record.get("special_requirements"):
        imported_fields.append("special_requirements")

    if record.get("field_confidence"):
        imported_fields.append("field_confidence")

    return imported_fields


def status_for_record(record):
    return classify_intake_record_status(record)


def build_human_summary_lines(record, status):
    lines = [
        "INTAKE RECORD DRY RUN",
        "DRY RUN ONLY - no parser/storage/integration used",
        f"Status: {status}",
        f"Intake ID: {record['intake_id'] or 'MISSING'}",
        f"Broker: {record['broker_name'] or 'MISSING'}",
        f"Broker MC: {record['broker_mc'] or 'MISSING'}",
        f"Rate: {record['rate'] or 'MISSING'}",
        f"Pickup: {record['pickup_location'] or 'MISSING'}",
        f"Pickup date: {record['pickup_date'] or 'MISSING'}",
        f"Delivery: {record['delivery_location'] or 'MISSING'}",
        f"Delivery date: {record['delivery_date'] or 'MISSING'}",
        f"Reference ID: {record['reference_id'] or 'MISSING'}",
        f"Equipment: {record['equipment'] or 'MISSING'}",
    ]

    if record["special_requirements"]:
        lines.append(
            "Special requirements: "
            + ", ".join(record["special_requirements"])
        )

    if record["missing_fields"]:
        lines.append("Missing fields: " + ", ".join(record["missing_fields"]))
    else:
        lines.append("Missing fields: none")

    if record["needs_check_fields"]:
        lines.append(
            "Needs check fields: " + ", ".join(record["needs_check_fields"])
        )
    else:
        lines.append("Needs check fields: none")

    lines.append("DispatchCase linking: disabled in dry run")

    return lines


def build_intake_record_summary(source=None, received_at_utc="", intake_id=""):
    record = build_intake_record(
        source=source,
        received_at_utc=received_at_utc,
        intake_id=intake_id,
    )
    status = status_for_record(record)

    return {
        "status": status,
        "imported_fields": build_imported_fields(record),
        "missing_fields": list(record["missing_fields"]),
        "needs_check_fields": list(record["needs_check_fields"]),
        "ready_for_review": intake_record_ready_for_review(record),
        "ready_for_dispatch_case_linking": False,
        "human_summary_lines": build_human_summary_lines(record, status),
        "intake_record": record,
    }


def format_intake_record_summary(summary):
    return "\n".join(summary["human_summary_lines"])
