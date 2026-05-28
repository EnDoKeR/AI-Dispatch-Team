import argparse
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.driver_preference_rules import (
    format_driver_preference_status,
    get_driver_preference_status,
)
from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE


def connect_db():
    connection = sqlite3.connect(SQLITE_DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def get_known_drivers(connection, limit=50):
    query = """
        SELECT
            driver_name,
            COUNT(*) AS total_cases,
            SUM(telegram_alert_count) AS telegram_alerts,
            SUM(dispatcher_feedback_count) AS feedback_items,
            SUM(ratecon_count) AS ratecons,
            MAX(updated_at_utc) AS latest_update
        FROM dispatch_cases
        WHERE driver_name IS NOT NULL
        AND driver_name != ''
        AND driver_name != 'UNKNOWN'
        GROUP BY driver_name
        ORDER BY feedback_items DESC, telegram_alerts DESC, total_cases DESC
        LIMIT ?
    """

    cursor = connection.cursor()
    cursor.execute(query, (limit,))
    return cursor.fetchall()


def print_single_driver(driver_name):
    preference_status = get_driver_preference_status(driver_name)

    print("")
    print(f"Driver: {preference_status.get('driver_name', '')}")
    print(
        f"Driver Preference Status: "
        f"{format_driver_preference_status(preference_status)}"
    )

    print("")
    print("Feedback counts:")
    feedback_counts = preference_status.get("feedback_counts", {}) or {}

    if feedback_counts:
        for feedback, count in sorted(
            feedback_counts.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            print(f"- {feedback}: {count}")
    else:
        print("- No feedback yet.")

    print("")
    print("Case counts:")
    case_counts = preference_status.get("case_counts", {}) or {}

    if case_counts:
        for key, value in sorted(case_counts.items()):
            print(f"- {key}: {value}")
    else:
        print("- No cases yet.")

    print("")
    print("Lane feedback:")
    lane_feedback = preference_status.get("lane_feedback", []) or []

    if lane_feedback:
        for row in lane_feedback:
            print(
                f"- {row['pickup']} -> {row['delivery']} | "
                f"{row['feedback']}: {row['count']} | "
                f"Avg RPM: {round(row['avg_rpm'] or 0, 2)} | "
                f"Avg miles: {round(row['avg_total_miles'] or 0, 1)}"
            )
    else:
        print("- No lane feedback yet.")


def print_all_drivers(limit):
    connection = connect_db()
    drivers = get_known_drivers(connection, limit=limit)
    connection.close()

    print("")
    print("Driver Preference Rules")
    print("-----------------------")

    if not drivers:
        print("No driver records found.")
        return

    for driver in drivers:
        driver_name = driver["driver_name"]
        preference_status = get_driver_preference_status(driver_name)

        print("")
        print(f"Driver: {driver_name}")
        print(f"Total cases: {driver['total_cases']}")
        print(f"Telegram alerts: {driver['telegram_alerts'] or 0}")
        print(f"Feedback items: {driver['feedback_items'] or 0}")
        print(f"RateCons: {driver['ratecons'] or 0}")
        print(f"Status: {format_driver_preference_status(preference_status)}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Evaluate driver preference rules from SQLite feedback."
    )

    parser.add_argument("--driver", default="")
    parser.add_argument("--limit", type=int, default=30)

    return parser


def main():
    args = build_parser().parse_args()

    if not SQLITE_DB_FILE.exists():
        print(f"Missing SQLite database: {SQLITE_DB_FILE}")
        print("Run first:")
        print("py scripts/build_sqlite_memory.py")
        return

    print("=" * 80)
    print("DRIVER PREFERENCE RULES REPORT")
    print("=" * 80)

    if args.driver:
        print_single_driver(args.driver)
    else:
        print_all_drivers(args.limit)


if __name__ == "__main__":
    main()