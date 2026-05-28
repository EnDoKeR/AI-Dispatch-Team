import argparse
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.broker_memory_rules import (
    format_broker_memory_status,
    get_broker_memory_status,
)
from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE


def connect_db():
    connection = sqlite3.connect(SQLITE_DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def get_known_brokers(connection, limit=50):
    query = """
        SELECT
            broker_mc,
            COALESCE(NULLIF(broker_name, ''), 'UNKNOWN') AS broker_name,
            COUNT(*) AS total_cases,
            SUM(telegram_alert_count) AS telegram_alerts,
            SUM(dispatcher_feedback_count) AS feedback_items,
            MAX(updated_at_utc) AS latest_update
        FROM dispatch_cases
        WHERE broker_mc IS NOT NULL
        AND broker_mc != ''
        AND broker_mc != 'NEEDS CHECK'
        GROUP BY broker_mc, broker_name
        ORDER BY feedback_items DESC, telegram_alerts DESC, total_cases DESC
        LIMIT ?
    """

    cursor = connection.cursor()
    cursor.execute(query, (limit,))
    return cursor.fetchall()


def print_single_broker(broker_mc):
    memory_status = get_broker_memory_status(broker_mc)

    print("")
    print(f"MC: {memory_status.get('broker_mc', '')}")
    print(f"Broker Memory Status: {format_broker_memory_status(memory_status)}")

    print("")
    print("Feedback counts:")
    feedback_counts = memory_status.get("feedback_counts", {}) or {}

    if feedback_counts:
        for feedback, count in sorted(feedback_counts.items(), key=lambda item: (-item[1], item[0])):
            print(f"- {feedback}: {count}")
    else:
        print("- No feedback yet.")

    print("")
    print("Case counts:")
    case_counts = memory_status.get("case_counts", {}) or {}

    if case_counts:
        for key, value in sorted(case_counts.items()):
            print(f"- {key}: {value}")
    else:
        print("- No cases yet.")


def print_all_brokers(limit):
    connection = connect_db()
    brokers = get_known_brokers(connection, limit=limit)
    connection.close()

    print("")
    print("Broker Memory Rules")
    print("-------------------")

    if not brokers:
        print("No broker records found.")
        return

    for broker in brokers:
        broker_mc = broker["broker_mc"]
        broker_name = broker["broker_name"]

        memory_status = get_broker_memory_status(broker_mc)

        print("")
        print(f"MC: {broker_mc}")
        print(f"Broker: {broker_name}")
        print(f"Total cases: {broker['total_cases']}")
        print(f"Telegram alerts: {broker['telegram_alerts'] or 0}")
        print(f"Feedback items: {broker['feedback_items'] or 0}")
        print(f"Status: {format_broker_memory_status(memory_status)}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Evaluate broker memory rules from SQLite feedback."
    )

    parser.add_argument("--broker-mc", default="")
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
    print("BROKER MEMORY RULES REPORT")
    print("=" * 80)

    if args.broker_mc:
        print_single_broker(args.broker_mc)
    else:
        print_all_brokers(args.limit)


if __name__ == "__main__":
    main()
