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


def column_name(name, table_alias=""):
    if table_alias:
        return f"{table_alias}.{name}"

    return name


def build_where_clause(args, table_alias=""):
    filters = []
    params = []

    driver_name = column_name("driver_name", table_alias)
    status = column_name("status", table_alias)
    ai_category = column_name("ai_category", table_alias)
    ai_decision = column_name("ai_decision", table_alias)
    broker_mc = column_name("broker_mc", table_alias)
    reference_id = column_name("reference_id", table_alias)
    telegram_alert_count = column_name("telegram_alert_count", table_alias)
    dispatcher_feedback_count = column_name("dispatcher_feedback_count", table_alias)
    ratecon_count = column_name("ratecon_count", table_alias)

    if args.driver:
        filters.append(f"LOWER({driver_name}) = LOWER(?)")
        params.append(args.driver)

    if args.status:
        filters.append(f"LOWER({status}) = LOWER(?)")
        params.append(args.status)

    if args.category:
        filters.append(f"LOWER({ai_category}) = LOWER(?)")
        params.append(args.category)

    if args.decision:
        filters.append(f"LOWER({ai_decision}) = LOWER(?)")
        params.append(args.decision)

    if args.broker_mc:
        filters.append(f"{broker_mc} = ?")
        params.append(args.broker_mc)

    if args.reference_id:
        filters.append(f"{reference_id} = ?")
        params.append(args.reference_id)

    if args.has_telegram:
        filters.append(f"{telegram_alert_count} > 0")

    if args.has_feedback:
        filters.append(f"{dispatcher_feedback_count} > 0")

    if args.has_ratecon:
        filters.append(f"{ratecon_count} > 0")

    if not filters:
        return "", params

    return "WHERE " + " AND ".join(filters), params


def print_count(connection, table_name):
    cursor = connection.cursor()
    cursor.execute(f"SELECT COUNT(*) AS count FROM {table_name}")
    row = cursor.fetchone()
    print(f"{table_name}: {row['count']}")


def print_overview(connection):
    print("")
    print("SQLite Dispatch Memory Overview")
    print("-------------------------------")
    print(f"Database: {SQLITE_DB_FILE}")

    print_count(connection, "dispatch_cases")
    print_count(connection, "dispatch_events")
    print_count(connection, "dispatcher_feedback")
    print_count(connection, "telegram_alerts")
    print_count(connection, "ratecons")


def print_group_counts(connection, title, field_name, where_clause="", params=None):
    params = params or []

    print("")
    print(title)
    print("-" * len(title))

    query = f"""
        SELECT {field_name} AS value, COUNT(*) AS count
        FROM dispatch_cases
        {where_clause}
        GROUP BY {field_name}
        ORDER BY count DESC, value ASC
    """

    cursor = connection.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()

    if not rows:
        print("No data.")
        return

    for row in rows:
        value = row["value"] or "UNKNOWN"
        print(f"{value}: {row['count']}")


def print_cases(connection, args):
    where_clause, params = build_where_clause(args)

    query = f"""
        SELECT
            case_id,
            driver_name,
            status,
            final_outcome,
            ai_decision,
            ai_category,
            pickup,
            delivery,
            rate,
            reference_id,
            broker_name,
            broker_mc,
            telegram_alert_count,
            dispatcher_feedback_count,
            ratecon_count,
            events_count,
            updated_at_utc
        FROM dispatch_cases
        {where_clause}
        ORDER BY updated_at_utc DESC
        LIMIT ?
    """

    query_params = list(params)
    query_params.append(args.limit)

    cursor = connection.cursor()
    cursor.execute(query, query_params)
    rows = cursor.fetchall()

    print("")
    print("Cases")
    print("-----")

    if not rows:
        print("No cases found.")
        return

    for row in rows:
        print(
            f"{row['case_id']} | "
            f"{row['driver_name']} | "
            f"{row['status']} | "
            f"{row['ai_decision']}/{row['ai_category']} | "
            f"{row['pickup']} -> {row['delivery']} | "
            f"${row['rate']} | "
            f"REF: {row['reference_id']} | "
            f"MC: {row['broker_mc']} | "
            f"{row['broker_name']} | "
            f"TG:{row['telegram_alert_count']} "
            f"FB:{row['dispatcher_feedback_count']} "
            f"RC:{row['ratecon_count']} "
            f"EV:{row['events_count']}"
        )


def print_replay_examples(connection, args):
    where_clause, params = build_where_clause(args)

    if where_clause:
        query = f"""
            SELECT reference_id, driver_name
            FROM dispatch_cases
            {where_clause}
            AND reference_id IS NOT NULL
            AND reference_id != ''
            ORDER BY updated_at_utc DESC
            LIMIT 5
        """
    else:
        query = """
            SELECT reference_id, driver_name
            FROM dispatch_cases
            WHERE reference_id IS NOT NULL
            AND reference_id != ''
            ORDER BY updated_at_utc DESC
            LIMIT 5
        """

    cursor = connection.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()

    print("")
    print("Replay examples")
    print("---------------")

    if not rows:
        print("No replay examples.")
        return

    for row in rows:
        print(
            f"py scripts/case_replay_report.py "
            f"{row['reference_id']} {row['driver_name']} --latest"
        )


def print_event_counts(connection, args):
    print("")
    print("Event Counts")
    print("------------")

    where_clause, params = build_where_clause(args, table_alias="c")

    if where_clause:
        query = f"""
            SELECT e.event_type AS event_type, COUNT(*) AS count
            FROM dispatch_events e
            JOIN dispatch_cases c ON e.case_id = c.case_id
            {where_clause}
            GROUP BY e.event_type
            ORDER BY count DESC, e.event_type ASC
        """
    else:
        query = """
            SELECT event_type AS event_type, COUNT(*) AS count
            FROM dispatch_events
            GROUP BY event_type
            ORDER BY count DESC, event_type ASC
        """

    cursor = connection.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()

    if not rows:
        print("No events.")
        return

    for row in rows:
        print(f"{row['event_type']}: {row['count']}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Query SQLite dispatch memory."
    )

    parser.add_argument("--driver", default="")
    parser.add_argument("--status", default="")
    parser.add_argument("--category", default="")
    parser.add_argument("--decision", default="")
    parser.add_argument("--broker-mc", default="")
    parser.add_argument("--reference-id", default="")
    parser.add_argument("--has-telegram", action="store_true")
    parser.add_argument("--has-feedback", action="store_true")
    parser.add_argument("--has-ratecon", action="store_true")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--limit", type=int, default=10)

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
    print("SQLITE DISPATCH MEMORY REPORT")
    print("=" * 80)

    print_overview(connection)

    where_clause, params = build_where_clause(args)

    print_group_counts(connection, "Status Counts", "status", where_clause, params)
    print_group_counts(connection, "AI Decision Counts", "ai_decision", where_clause, params)
    print_group_counts(connection, "AI Category Counts", "ai_category", where_clause, params)

    if not args.summary:
        print_cases(connection, args)

    print_event_counts(connection, args)
    print_replay_examples(connection, args)

    connection.close()


if __name__ == "__main__":
    main()
