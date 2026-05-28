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


def build_where_clause(args):
    filters = []
    params = []

    if args.broker_mc:
        filters.append("c.broker_mc = ?")
        params.append(args.broker_mc)

    if args.broker_name:
        filters.append("LOWER(c.broker_name) LIKE LOWER(?)")
        params.append(f"%{args.broker_name}%")

    if args.driver:
        filters.append("LOWER(c.driver_name) = LOWER(?)")
        params.append(args.driver)

    if not filters:
        return "", params

    return "WHERE " + " AND ".join(filters), params


def get_broker_feedback_summary(connection, args):
    where_clause, params = build_where_clause(args)

    base_filter = """
        c.broker_mc IS NOT NULL
        AND c.broker_mc != ''
        AND c.broker_mc != 'NEEDS CHECK'
    """

    if where_clause:
        where_clause = where_clause + " AND " + base_filter
    else:
        where_clause = "WHERE " + base_filter

    query = f"""
        SELECT
            c.broker_mc,
            COALESCE(NULLIF(c.broker_name, ''), 'UNKNOWN') AS broker_name,

            COUNT(DISTINCT c.case_id) AS total_cases,
            SUM(c.telegram_alert_count) AS telegram_alerts,
            SUM(c.dispatcher_feedback_count) AS feedback_items,
            SUM(c.ratecon_count) AS ratecons,

            SUM(CASE WHEN c.ai_category = 'LOAD OPPORTUNITY' THEN 1 ELSE 0 END) AS load_opportunity_cases,
            SUM(CASE WHEN c.ai_category = 'RATE CHECK' THEN 1 ELSE 0 END) AS rate_check_cases,
            SUM(CASE WHEN c.ai_category = 'BROKER REVIEW' THEN 1 ELSE 0 END) AS broker_review_cases,
            SUM(CASE WHEN c.ai_category = 'BLOCK' THEN 1 ELSE 0 END) AS blocked_cases,

            SUM(CASE WHEN c.status = 'BOOKED' THEN 1 ELSE 0 END) AS booked_cases,
            SUM(CASE WHEN c.status = 'SENT_TO_DRIVER' THEN 1 ELSE 0 END) AS sent_to_driver_cases,
            SUM(CASE WHEN c.status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected_cases,
            SUM(CASE WHEN c.status = 'SKIPPED' THEN 1 ELSE 0 END) AS skipped_cases,
            SUM(CASE WHEN c.status = 'COVERED' THEN 1 ELSE 0 END) AS covered_cases,
            SUM(CASE WHEN c.status = 'RATECON_RECEIVED' THEN 1 ELSE 0 END) AS ratecon_received_cases,

            MAX(c.updated_at_utc) AS latest_update
        FROM dispatch_cases c
        {where_clause}
        GROUP BY c.broker_mc, c.broker_name
        ORDER BY feedback_items DESC, telegram_alerts DESC, total_cases DESC
        LIMIT ?
    """

    query_params = list(params)
    query_params.append(args.limit)

    cursor = connection.cursor()
    cursor.execute(query, query_params)
    return cursor.fetchall()


def get_feedback_counts_for_broker(connection, broker_mc):
    query = """
        SELECT
            f.feedback,
            COUNT(*) AS count
        FROM dispatcher_feedback f
        JOIN dispatch_cases c ON f.case_id = c.case_id
        WHERE c.broker_mc = ?
        GROUP BY f.feedback
        ORDER BY count DESC, f.feedback ASC
    """

    cursor = connection.cursor()
    cursor.execute(query, (broker_mc,))
    rows = cursor.fetchall()

    return {
        row["feedback"]: row["count"]
        for row in rows
    }


def build_recommendations(row, feedback_counts, args):
    recommendations = []

    broker_mc = row["broker_mc"]
    memory_status = get_broker_memory_status(broker_mc)
    memory_status_name = memory_status.get("status", "UNKNOWN")
    memory_text = format_broker_memory_status(memory_status)

    bad_broker = feedback_counts.get("bad_broker", 0)
    rate_too_low = feedback_counts.get("rate_too_low", 0)
    booked = feedback_counts.get("booked", 0)
    ratecon_received = feedback_counts.get("ratecon_received", 0)
    sent_to_driver = feedback_counts.get("sent_to_driver", 0)
    covered = feedback_counts.get("covered", 0)
    skipped = feedback_counts.get("skipped", 0)
    called_broker = feedback_counts.get("called_broker", 0)

    total_cases = row["total_cases"] or 0
    rate_check_cases = row["rate_check_cases"] or 0
    load_opportunity_cases = row["load_opportunity_cases"] or 0
    telegram_alerts = row["telegram_alerts"] or 0
    feedback_items = row["feedback_items"] or 0

    if bad_broker >= args.bad_broker_threshold:
        recommendations.append(
            {
                "level": "HIGH",
                "type": "KEEP_BAD_BROKER_REVIEW",
                "text": (
                    f"Keep broker as BAD_BROKER_REVIEW. "
                    f"bad_broker feedback repeated {bad_broker}x."
                ),
            }
        )

    if rate_too_low >= args.rate_too_low_threshold:
        recommendations.append(
            {
                "level": "MEDIUM",
                "type": "KEEP_RATE_NEGOTIATION_REQUIRED",
                "text": (
                    f"Keep rate negotiation warning. "
                    f"rate_too_low feedback repeated {rate_too_low}x."
                ),
            }
        )

    if booked >= 1 or ratecon_received >= 1:
        recommendations.append(
            {
                "level": "POSITIVE",
                "type": "POSITIVE_BROKER_SIGNAL",
                "text": (
                    f"Positive broker signal. "
                    f"booked={booked}, ratecon_received={ratecon_received}."
                ),
            }
        )

    if sent_to_driver >= 2 and bad_broker == 0:
        recommendations.append(
            {
                "level": "POSITIVE",
                "type": "DRIVER_INTEREST_SIGNAL",
                "text": (
                    f"Driver interest signal. "
                    f"sent_to_driver feedback repeated {sent_to_driver}x."
                ),
            }
        )

    if covered >= 2:
        recommendations.append(
            {
                "level": "MEDIUM",
                "type": "COVERED_WATCHLIST",
                "text": (
                    f"Watch broker/load timing. "
                    f"covered feedback repeated {covered}x."
                ),
            }
        )

    if skipped >= 2 and load_opportunity_cases >= 1:
        recommendations.append(
            {
                "level": "LOW",
                "type": "CHECK_LOAD_QUALITY",
                "text": (
                    f"Dispatcher skipped this broker's loads {skipped}x. "
                    "Review if AI is over-ranking these loads."
                ),
            }
        )

    if called_broker >= 2 and rate_check_cases >= 1 and rate_too_low == 0 and bad_broker == 0:
        recommendations.append(
            {
                "level": "LOW",
                "type": "MONITOR_RATE_CHECK_FLOW",
                "text": (
                    f"Broker has {called_broker} called_broker feedback item(s) "
                    "on rate-check activity. Monitor until outcome is clearer."
                ),
            }
        )

    if feedback_items == 0 and telegram_alerts >= 3:
        recommendations.append(
            {
                "level": "LOW",
                "type": "NEEDS_DISPATCHER_FEEDBACK",
                "text": (
                    f"Broker has {telegram_alerts} Telegram alert(s) but no feedback. "
                    "Need more dispatcher actions before learning a rule."
                ),
            }
        )

    if total_cases >= 3 and load_opportunity_cases == 0 and rate_check_cases >= 2:
        recommendations.append(
            {
                "level": "MEDIUM",
                "type": "RATE_CHECK_HEAVY_BROKER",
                "text": (
                    f"Broker has {rate_check_cases} RATE CHECK cases and no clean load opportunities. "
                    "Keep rate-check review flow."
                ),
            }
        )

    if memory_status_name == "UNKNOWN" and feedback_items > 0:
        recommendations.append(
            {
                "level": "LOW",
                "type": "INSUFFICIENT_SIGNAL",
                "text": (
                    f"Feedback exists but not enough repeated signal yet. "
                    f"Current broker memory: {memory_text}."
                ),
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "level": "INFO",
                "type": "NO_ACTION",
                "text": (
                    f"No strong recommendation yet. "
                    f"Current broker memory: {memory_text}."
                ),
            }
        )

    return recommendations


def print_overview(rows):
    print("")
    print("Learning Recommendations Overview")
    print("---------------------------------")
    print(f"Brokers analyzed: {len(rows)}")

    total_feedback = sum(row["feedback_items"] or 0 for row in rows)
    total_alerts = sum(row["telegram_alerts"] or 0 for row in rows)
    total_cases = sum(row["total_cases"] or 0 for row in rows)

    print(f"Total broker cases: {total_cases}")
    print(f"Total Telegram alerts: {total_alerts}")
    print(f"Total feedback items: {total_feedback}")


def print_recommendations(connection, rows, args):
    print("")
    print("Recommendations")
    print("---------------")

    if not rows:
        print("No broker records found.")
        return

    printed = 0

    for row in rows:
        broker_mc = row["broker_mc"]
        broker_name = row["broker_name"]

        feedback_counts = get_feedback_counts_for_broker(connection, broker_mc)
        recommendations = build_recommendations(row, feedback_counts, args)

        if args.only_actionable:
            recommendations = [
                recommendation
                for recommendation in recommendations
                if recommendation["type"] not in ["NO_ACTION", "INSUFFICIENT_SIGNAL"]
            ]

            if not recommendations:
                continue

        memory_status = get_broker_memory_status(broker_mc)
        memory_text = format_broker_memory_status(memory_status)

        print("")
        print(f"MC: {broker_mc}")
        print(f"Broker: {broker_name}")
        print(f"Broker Memory: {memory_text}")
        print(
            f"Cases: {row['total_cases']} | "
            f"TG: {row['telegram_alerts'] or 0} | "
            f"Feedback: {row['feedback_items'] or 0} | "
            f"RateCons: {row['ratecons'] or 0}"
        )
        print(
            f"Categories: "
            f"LOAD_OPP {row['load_opportunity_cases'] or 0} | "
            f"RATE_CHECK {row['rate_check_cases'] or 0} | "
            f"BROKER_REVIEW {row['broker_review_cases'] or 0} | "
            f"BLOCK {row['blocked_cases'] or 0}"
        )

        if feedback_counts:
            print("Feedback:")
            for feedback, count in sorted(feedback_counts.items(), key=lambda item: (-item[1], item[0])):
                print(f"- {feedback}: {count}")
        else:
            print("Feedback: none")

        print("Recommendations:")
        for recommendation in recommendations:
            print(
                f"- [{recommendation['level']}] "
                f"{recommendation['type']}: {recommendation['text']}"
            )

        printed += 1

    if printed == 0:
        print("No actionable recommendations found.")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Suggest learning recommendations from broker feedback and memory."
    )

    parser.add_argument("--broker-mc", default="")
    parser.add_argument("--broker-name", default="")
    parser.add_argument("--driver", default="")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--bad-broker-threshold", type=int, default=2)
    parser.add_argument("--rate-too-low-threshold", type=int, default=2)
    parser.add_argument("--only-actionable", action="store_true")

    return parser


def main():
    args = build_parser().parse_args()

    if not SQLITE_DB_FILE.exists():
        print(f"Missing SQLite database: {SQLITE_DB_FILE}")
        print("Run first:")
        print("py scripts/build_sqlite_memory.py")
        return

    connection = connect_db()
    rows = get_broker_feedback_summary(connection, args)

    print("=" * 80)
    print("LEARNING RECOMMENDATIONS REPORT")
    print("=" * 80)

    print_overview(rows)
    print_recommendations(connection, rows, args)

    connection.close()


if __name__ == "__main__":
    main()