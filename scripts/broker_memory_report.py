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


def broker_key_clause(args):
    filters = []
    params = []

    if args.broker_mc:
        filters.append("broker_mc = ?")
        params.append(args.broker_mc)

    if args.broker_name:
        filters.append("LOWER(broker_name) LIKE LOWER(?)")
        params.append(f"%{args.broker_name}%")

    if args.driver:
        filters.append("LOWER(driver_name) = LOWER(?)")
        params.append(args.driver)

    if not filters:
        return "", params

    return "WHERE " + " AND ".join(filters), params


def print_overview(connection):
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            COUNT(*) AS total_cases,
            COUNT(DISTINCT broker_mc) AS unique_broker_mc,
            SUM(CASE WHEN telegram_alert_count > 0 THEN 1 ELSE 0 END) AS cases_with_telegram,
            SUM(dispatcher_feedback_count) AS total_feedback,
            SUM(ratecon_count) AS total_ratecons
        FROM dispatch_cases
        WHERE broker_mc IS NOT NULL
        AND broker_mc != ''
        AND broker_mc != 'NEEDS CHECK'
        """
    )

    row = cursor.fetchone()

    print("")
    print("Broker Memory Overview")
    print("----------------------")
    print(f"Database: {SQLITE_DB_FILE}")
    print(f"Total broker cases: {row['total_cases'] or 0}")
    print(f"Unique broker MCs: {row['unique_broker_mc'] or 0}")
    print(f"Cases with Telegram: {row['cases_with_telegram'] or 0}")
    print(f"Total feedback items: {row['total_feedback'] or 0}")
    print(f"Total RateCons: {row['total_ratecons'] or 0}")


def print_broker_summary(connection, args):
    where_clause, params = broker_key_clause(args)

    extra_filter = """
        broker_mc IS NOT NULL
        AND broker_mc != ''
        AND broker_mc != 'NEEDS CHECK'
    """

    if where_clause:
        where_clause = where_clause + " AND " + extra_filter
    else:
        where_clause = "WHERE " + extra_filter

    query = f"""
        SELECT
            broker_mc,
            COALESCE(NULLIF(broker_name, ''), 'UNKNOWN') AS broker_name,

            COUNT(*) AS total_cases,

            SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) AS open_cases,
            SUM(CASE WHEN status = 'COVERED' THEN 1 ELSE 0 END) AS covered_cases,
            SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected_cases,
            SUM(CASE WHEN status = 'RATECON_RECEIVED' THEN 1 ELSE 0 END) AS ratecon_received_cases,

            SUM(CASE WHEN ai_category = 'LOAD OPPORTUNITY' THEN 1 ELSE 0 END) AS load_opportunity_cases,
            SUM(CASE WHEN ai_category = 'RATE CHECK' THEN 1 ELSE 0 END) AS rate_check_cases,
            SUM(CASE WHEN ai_category = 'CONESTOGA VERIFY' THEN 1 ELSE 0 END) AS conestoga_verify_cases,
            SUM(CASE WHEN ai_category = 'OD / PERMIT' THEN 1 ELSE 0 END) AS od_permit_cases,
            SUM(CASE WHEN ai_category = 'BLOCK' THEN 1 ELSE 0 END) AS blocked_cases,

            SUM(telegram_alert_count) AS telegram_alerts,
            SUM(dispatcher_feedback_count) AS feedback_items,
            SUM(ratecon_count) AS ratecons,

            MAX(updated_at_utc) AS latest_update
        FROM dispatch_cases
        {where_clause}
        GROUP BY broker_mc, broker_name
        ORDER BY total_cases DESC, telegram_alerts DESC, latest_update DESC
        LIMIT ?
    """

    query_params = list(params)
    query_params.append(args.limit)

    cursor = connection.cursor()
    cursor.execute(query, query_params)
    rows = cursor.fetchall()

    print("")
    print("Broker Summary")
    print("--------------")

    if not rows:
        print("No broker records found.")
        return

    for row in rows:
        print("")
        print(f"MC: {row['broker_mc']}")
        print(f"Broker: {row['broker_name']}")
        print(f"Total cases: {row['total_cases']}")
        print(
            "Statuses: "
            f"OPEN {row['open_cases'] or 0} | "
            f"COVERED {row['covered_cases'] or 0} | "
            f"REJECTED {row['rejected_cases'] or 0} | "
            f"RATECON_RECEIVED {row['ratecon_received_cases'] or 0}"
        )
        print(
            "Categories: "
            f"LOAD OPPORTUNITY {row['load_opportunity_cases'] or 0} | "
            f"RATE CHECK {row['rate_check_cases'] or 0} | "
            f"CONESTOGA VERIFY {row['conestoga_verify_cases'] or 0} | "
            f"OD/PERMIT {row['od_permit_cases'] or 0} | "
            f"BLOCK {row['blocked_cases'] or 0}"
        )
        print(
            "Activity: "
            f"Telegram {row['telegram_alerts'] or 0} | "
            f"Feedback {row['feedback_items'] or 0} | "
            f"RateCons {row['ratecons'] or 0}"
        )
        print(f"Latest update: {row['latest_update']}")


def print_broker_cases(connection, args):
    where_clause, params = broker_key_clause(args)

    if not args.show_cases:
        return

    query = f"""
        SELECT
            case_id,
            driver_name,
            status,
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
            updated_at_utc
        FROM dispatch_cases
        {where_clause}
        ORDER BY updated_at_utc DESC
        LIMIT ?
    """

    query_params = list(params)
    query_params.append(args.case_limit)

    cursor = connection.cursor()
    cursor.execute(query, query_params)
    rows = cursor.fetchall()

    print("")
    print("Broker Cases")
    print("------------")

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
            f"RC:{row['ratecon_count']}"
        )


def print_broker_feedback(connection, args):
    if not args.show_feedback:
        return

    where_clause, params = broker_key_clause(args)

    if where_clause:
        where_clause = where_clause.replace("broker_mc", "c.broker_mc")
        where_clause = where_clause.replace("broker_name", "c.broker_name")
        where_clause = where_clause.replace("driver_name", "c.driver_name")

    query = f"""
        SELECT
            c.broker_mc,
            c.broker_name,
            c.driver_name,
            c.pickup,
            c.delivery,
            c.reference_id,
            f.timestamp_utc,
            f.feedback,
            f.note,
            f.source
        FROM dispatcher_feedback f
        JOIN dispatch_cases c ON f.case_id = c.case_id
        {where_clause}
        ORDER BY f.timestamp_utc DESC
        LIMIT ?
    """

    query_params = list(params)
    query_params.append(args.case_limit)

    cursor = connection.cursor()
    cursor.execute(query, query_params)
    rows = cursor.fetchall()

    print("")
    print("Broker Feedback")
    print("---------------")

    if not rows:
        print("No feedback found.")
        return

    for row in rows:
        print("")
        print(f"MC: {row['broker_mc']} | Broker: {row['broker_name']}")
        print(f"Driver: {row['driver_name']}")
        print(f"Lane: {row['pickup']} -> {row['delivery']}")
        print(f"Reference ID: {row['reference_id']}")
        print(f"Time: {row['timestamp_utc']}")
        print(f"Feedback: {row['feedback']}")
        print(f"Note: {row['note']}")
        print(f"Source: {row['source']}")


def print_replay_examples(connection, args):
    where_clause, params = broker_key_clause(args)

    query = f"""
        SELECT reference_id, driver_name
        FROM dispatch_cases
        {where_clause}
        WHERE reference_id IS NOT NULL
        AND reference_id != ''
        ORDER BY updated_at_utc DESC
        LIMIT 5
    """

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


def build_parser():
    parser = argparse.ArgumentParser(
        description="Broker memory report from SQLite dispatch memory."
    )

    parser.add_argument("--broker-mc", default="")
    parser.add_argument("--broker-name", default="")
    parser.add_argument("--driver", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--show-cases", action="store_true")
    parser.add_argument("--show-feedback", action="store_true")
    parser.add_argument("--case-limit", type=int, default=10)

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
    print("BROKER MEMORY REPORT")
    print("=" * 80)

    print_overview(connection)
    print_broker_summary(connection, args)
    print_broker_cases(connection, args)
    print_broker_feedback(connection, args)
    print_replay_examples(connection, args)

    connection.close()


if __name__ == "__main__":
    main()