from copy import deepcopy

from app.market_intelligence.reload_watch_repository import (
    ACTIVE_WATCH_STATUSES,
    RELOAD_WATCH_FILE,
    load_reload_watch_records,
    record_status,
)


REPORT_STATUSES = [
    "WATCH_ACTIVE",
    "WATCH_MUTED",
    "WATCH_STOPPED",
    "DRIVER_LOADED",
    "PARENT_LOAD_REMOVED",
]


WATCH_SUMMARY_FIELDS = [
    "watch_id",
    "driver_name",
    "parent_reference_id",
    "delivery_city",
    "delivery_state",
    "watch_status",
    "last_event_type",
    "clean_exit_count",
    "review_exit_count",
    "rate_check_exit_count",
    "best_exit_reference_id",
    "best_exit_pickup",
    "best_exit_delivery",
    "best_exit_rate",
    "chain_status",
    "combined_rpm",
    "updated_at_utc",
]

NUMERIC_SUMMARY_FIELDS = {
    "clean_exit_count",
    "review_exit_count",
    "rate_check_exit_count",
    "best_exit_rate",
    "combined_rpm",
}


def summary_default(field):
    return 0 if field in NUMERIC_SUMMARY_FIELDS else ""


def summarize_watch(record):
    return {
        field: deepcopy((record or {}).get(field, summary_default(field)))
        for field in WATCH_SUMMARY_FIELDS
    }


def build_status_counts(records):
    counts = {status: 0 for status in REPORT_STATUSES}

    for record in records:
        status = record_status(record)
        if status not in counts:
            counts[status] = 0
        counts[status] += 1

    return counts


def build_reload_watch_report(file_path=RELOAD_WATCH_FILE):
    records = load_reload_watch_records(file_path)
    active_watches = []
    inactive_watches = []

    for record in records:
        summary = summarize_watch(record)

        if record_status(record) in ACTIVE_WATCH_STATUSES:
            active_watches.append(summary)
        else:
            inactive_watches.append(summary)

    return {
        "total_watches": len(records),
        "status_counts": build_status_counts(records),
        "active_watches": active_watches,
        "inactive_watches": inactive_watches,
    }


def safe_text(value, fallback="NEEDS CHECK"):
    text = str(value or "").strip()
    return text if text else fallback


def money_text(value):
    if value in ["", None]:
        return "$0"

    return f"${number_text(value)}"


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


def delivery_text(watch):
    city = safe_text(watch.get("delivery_city", ""))
    state = safe_text(watch.get("delivery_state", ""))

    if city == "NEEDS CHECK" and state == "NEEDS CHECK":
        return "NEEDS CHECK"

    if city == "NEEDS CHECK":
        return state

    if state == "NEEDS CHECK":
        return city

    return f"{city}, {state}"


def format_watch_line(watch):
    best_exit = (
        f"{safe_text(watch.get('best_exit_pickup', ''))} -> "
        f"{safe_text(watch.get('best_exit_delivery', ''))} | "
        f"{money_text(watch.get('best_exit_rate', 0))} | "
        f"REF: {safe_text(watch.get('best_exit_reference_id', ''))}"
    )
    chain = (
        f"{safe_text(watch.get('chain_status', ''))} | "
        f"RPM: {money_text(watch.get('combined_rpm', 0))}"
    )

    lines = [
        f"- Watch ID: {safe_text(watch.get('watch_id', ''))}",
        f"  Driver: {safe_text(watch.get('driver_name', ''))}",
        f"  Parent Ref: {safe_text(watch.get('parent_reference_id', ''))}",
        f"  Delivery: {delivery_text(watch)}",
        f"  Status: {safe_text(watch.get('watch_status', ''))}",
        f"  Last event: {safe_text(watch.get('last_event_type', ''))}",
        f"  Clean exits: {number_text(watch.get('clean_exit_count', 0))}",
        f"  Review exits: {number_text(watch.get('review_exit_count', 0))}",
        f"  Rate-check exits: {number_text(watch.get('rate_check_exit_count', 0))}",
        f"  Best exit: {best_exit}",
        f"  Chain: {chain}",
        f"  Updated: {safe_text(watch.get('updated_at_utc', ''))}",
    ]

    return "\n".join(lines)


def format_watch_section(title, watches):
    lines = ["", title, "-" * len(title)]

    if not watches:
        lines.append("None.")
        return "\n".join(lines)

    for index, watch in enumerate(watches):
        if index:
            lines.append("")
        lines.append(format_watch_line(watch))

    return "\n".join(lines)


def format_reload_watch_report(report):
    report = report or {}
    status_counts = report.get("status_counts", {})
    lines = [
        "RELOAD WATCH DRY-RUN REPORT",
        "---------------------------",
        f"Total watches: {report.get('total_watches', 0)}",
        "",
        "Status counts:",
    ]

    for status in REPORT_STATUSES:
        lines.append(f"- {status}: {status_counts.get(status, 0)}")

    if not report.get("total_watches", 0):
        lines.append("")
        lines.append("No reload watches found.")
        return "\n".join(lines)

    lines.append(format_watch_section("Active Watches", report.get("active_watches", [])))
    lines.append(format_watch_section("Inactive Watches", report.get("inactive_watches", [])))

    return "\n".join(lines)
