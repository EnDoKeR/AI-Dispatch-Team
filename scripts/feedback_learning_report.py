import argparse
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE


def connect_db():
    connection = sqlite3.connect(SQLITE_DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def build_where_clause(args, table_alias="c"):
    filters = []
    params = []

    prefix = f"{table_alias}."

    if args.driver:
        filters.append(f"LOWER({prefix}driver_name) = LOWER(?)")
        params.append(args.driver)

    if args.feedback:
        filters.append("LOWER(f.feedback) = LOWER(?)")
        params.append(args.feedback)

    if args.broker_mc:
        filters.append(f"{prefix}broker_mc = ?")
        params.append(args.broker_mc)

    if args.category:
        filters.append(f"LOWER({prefix}ai_category) = LOWER(?)")
        params.append(args.category)

    if args.decision:
        filters.append(f"LOWER({prefix}ai_decision) = LOWER(?)")
        params.append(args.decision)

    if not filters:
        return "", params

    return "WHERE " + " AND ".join(filters), params


def print_overview(connection, args):
    where_clause, params = build_where_clause(args)

    query = f"""
        SELECT
            COUNT(*) AS total_feedback,
            COUNT(DISTINCT f.case_id) AS cases_with_feedback,
            COUNT(DISTINCT c.broker_mc) AS brokers_with_feedback,
            COUNT(DISTINCT c.driver_name) AS drivers_with_feedback
        FROM dispatcher_feedback f
        JOIN dispatch_cases c ON f.case_id = c.case_id
        {where_clause}
    """

    cursor = connection.cursor()
    cursor.execute(query, params)
    row = cursor.fetchone()

    print("")
    print("Feedback Learning Overview")
    print("--------------------------")
    print(f"Database: {SQLITE_DB_FILE}")
    print(f"Total feedback items: {row['total_feedback'] or 0}")
    print(f"Cases with feedback: {row['cases_with_feedback'] or 0}")
    print(f"Brokers with feedback: {row['brokers_with_feedback'] or 0}")
    print(f"Drivers with feedback: {row['drivers_with_feedback'] or 0}")


def print_feedback_counts(connection, args):
    where_clause, params = build_where_clause(args)

    query = f"""
        SELECT
            f.feedback,
            COUNT(*) AS count
        FROM dispatcher_feedback f
        JOIN dispatch_cases c ON f.case_id = c.case_id
        {where_clause}
        GROUP BY f.feedback
        ORDER BY count DESC, f.feedback ASC
    """

    cursor = connection.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()

    print("")
    print("Feedback Counts")
    print("---------------")

    if not rows:
        print("No feedback data.")
        return

    for row in rows:
        print(f"{row['feedback']}: {row['count']}")


def print_feedback_by_category(connection, args):
    where_clause, params = build_where_clause(args)

    query = f"""
        SELECT
            c.ai_category,
            f.feedback,
            COUNT(*) AS count
        FROM dispatcher_feedback f
        JOIN dispatch_cases c ON f.case_id = c.case_id
        {where_clause}
        GROUP BY c.ai_category, f.feedback
        ORDER BY c.ai_category ASC, count DESC
    """

    cursor = connection.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()

    print("")
    print("Feedback By AI Category")
    print("-----------------------")

    if not rows:
        print("No category feedback data.")
        return

    current_category = None

    for row in rows:
        category = row["ai_category"] or "UNKNOWN"

        if category != current_category:
            current_category = category
            print("")
            print(f"{category}:")

        print(f"- {row['feedback']}: {row['count']}")


def print_feedback_by_broker(connection, args):
    where_clause, params = build_where_clause(args)

    query = f"""
        SELECT
            c.broker_mc,
            COALESCE(NULLIF(c.broker_name, ''), 'UNKNOWN') AS broker_name,
            f.feedback,
            COUNT(*) AS count
        FROM dispatcher_feedback f
        JOIN dispatch_cases c ON f.case_id = c.case_id
        {where_clause}
        GROUP BY c.broker_mc, c.broker_name, f.feedback
        ORDER BY count DESC, c.broker_mc ASC
        LIMIT ?
    """

    query_params = list(params)
    query_params.append(args.limit)

    cursor = connection.cursor()
    cursor.execute(query, query_params)
    rows = cursor.fetchall()

    print("")
    print("Feedback By Broker")
    print("------------------")

    if not rows:
        print("No broker feedback data.")
        return

    for row in rows:
        print(
            f"MC {row['broker_mc']} | {row['broker_name']} | "
            f"{row['feedback']}: {row['count']}"
        )


def print_recent_feedback(connection, args):
    where_clause, params = build_where_clause(args)

    query = f"""
        SELECT
            f.timestamp_utc,
            f.feedback,
            f.note,
            f.source,

            c.case_id,
            c.driver_name,
            c.status,
            c.ai_decision,
            c.ai_category,
            c.pickup,
            c.delivery,
            c.rate,
            c.reference_id,
            c.broker_name,
            c.broker_mc
        FROM dispatcher_feedback f
        JOIN dispatch_cases c ON f.case_id = c.case_id
        {where_clause}
        ORDER BY f.timestamp_utc DESC
        LIMIT ?
    """

    query_params = list(params)
    query_params.append(args.limit)

    cursor = connection.cursor()
    cursor.execute(query, query_params)
    rows = cursor.fetchall()

    print("")
    print("Recent Feedback")
    print("---------------")

    if not rows:
        print("No recent feedback.")
        return

    for row in rows:
        print("")
        print(f"Time: {row['timestamp_utc']}")
        print(f"Feedback: {row['feedback']}")
        print(f"Note: {row['note']}")
        print(f"Source: {row['source']}")
        print(
            f"Case: {row['case_id']} | {row['driver_name']} | "
            f"{row['status']} | {row['ai_decision']}/{row['ai_category']}"
        )
        print(
            f"Load: {row['pickup']} -> {row['delivery']} | "
            f"Rate: ${row['rate']} | REF: {row['reference_id']}"
        )
        print(f"Broker: {row['broker_name']} | MC: {row['broker_mc']}")
        print(
            "Replay: "
            f"py scripts/case_replay_report.py {row['reference_id']} {row['driver_name']} --latest"
        )


def print_learning_signals(connection, args):
    where_clause, params = build_where_clause(args)

    query = f"""
        SELECT
            f.feedback,
            c.ai_category,
            c.broker_mc,
            COALESCE(NULLIF(c.broker_name, ''), 'UNKNOWN') AS broker_name,
            COUNT(*) AS count
        FROM dispatcher_feedback f
        JOIN dispatch_cases c ON f.case_id = c.case_id
        {where_clause}
        GROUP BY f.feedback, c.ai_category, c.broker_mc, c.broker_name
        HAVING COUNT(*) >= ?
        ORDER BY count DESC, f.feedback ASC
    """

    query_params = list(params)
    query_params.append(args.min_signal_count)

    cursor = connection.cursor()
    cursor.execute(query, query_params)
    rows = cursor.fetchall()

    print("")
    print("Learning Signals")
    print("----------------")

    if not rows:
        print("No strong repeated signals yet.")
        return

    for row in rows:
        feedback = row["feedback"]
        category = row["ai_category"] or "UNKNOWN"
        broker_mc = row["broker_mc"] or "UNKNOWN"
        broker_name = row["broker_name"] or "UNKNOWN"
        count = row["count"]

        print(
            f"{feedback} repeated {count}x | "
            f"Category: {category} | MC: {broker_mc} | Broker: {broker_name}"
        )


def build_parser():
    parser = argparse.ArgumentParser(
        description="Analyze dispatcher feedback learning signals from SQLite memory."
    )

    parser.add_argument("--driver", default="")
    parser.add_argument("--feedback", default="")
    parser.add_argument("--broker-mc", default="")
    parser.add_argument("--category", default="")
    parser.add_argument("--decision", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--min-signal-count", type=int, default=2)

    return parser


def main():
    args = build_parser().parse_args()

    if not SQLITE_DB_FILE.exists():
        print(f"Missing SQLite database: {SQLITE_DB_FILE}")
        print("Run first:")
        print("py scripts/build_sqlite_memory.py")
        return

    connection = connect_db()

    print("=" * 80)
    print("FEEDBACK LEARNING REPORT")
    print("=" * 80)

    print_overview(connection, args)
    print_feedback_counts(connection, args)
    print_feedback_by_category(connection, args)
    print_feedback_by_broker(connection, args)
    print_learning_signals(connection, args)

    if not args.summary:
        print_recent_feedback(connection, args)

    connection.close()


if __name__ == "__main__":
    main()