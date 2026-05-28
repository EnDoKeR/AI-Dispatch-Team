import argparse
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE


DRIVER_POSITIVE_FEEDBACK = [
    "booked",
    "sent_to_driver",
    "ratecon_received",
]

RATE_SIGNAL_FEEDBACK = [
    "rate_too_low",
]

BROKER_SIGNAL_FEEDBACK = [
    "bad_broker",
]

BROKER_OR_MARKET_SIGNAL_FEEDBACK = [
    "covered",
]

WORKFLOW_SIGNAL_FEEDBACK = [
    "called_broker",
]

DISPATCHER_OR_DRIVER_NEGATIVE_FEEDBACK = [
    "driver_rejected",
    "skipped",
    "not_interested",
]

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

    if args.category:
        filters.append(f"LOWER({prefix}ai_category) = LOWER(?)")
        params.append(args.category)

    if args.broker_mc:
        filters.append(f"{prefix}broker_mc = ?")
        params.append(args.broker_mc)

    if not filters:
        return "", params

    return "WHERE " + " AND ".join(filters), params


def get_driver_feedback_rows(connection, args):
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
            c.final_outcome,
            c.ai_decision,
            c.ai_category,
            c.pickup,
            c.delivery,
            c.rate,
            c.total_miles,
            c.total_rpm,
            c.weight,
            c.posted_trailer_type,
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
    query_params.append(args.scan_limit)

    cursor = connection.cursor()
    cursor.execute(query, query_params)
    return cursor.fetchall()


def get_driver_case_summary(connection, args):
    filters = []
    params = []

    if args.driver:
        filters.append("LOWER(driver_name) = LOWER(?)")
        params.append(args.driver)

    where_clause = ""

    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    query = f"""
        SELECT
            driver_name,
            COUNT(*) AS total_cases,

            SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) AS open_cases,
            SUM(CASE WHEN status = 'CALLED' THEN 1 ELSE 0 END) AS called_cases,
            SUM(CASE WHEN status = 'SENT_TO_DRIVER' THEN 1 ELSE 0 END) AS sent_to_driver_cases,
            SUM(CASE WHEN status = 'BOOKED' THEN 1 ELSE 0 END) AS booked_cases,
            SUM(CASE WHEN status = 'RATECON_RECEIVED' THEN 1 ELSE 0 END) AS ratecon_received_cases,
            SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected_cases,
            SUM(CASE WHEN status = 'SKIPPED' THEN 1 ELSE 0 END) AS skipped_cases,
            SUM(CASE WHEN status = 'COVERED' THEN 1 ELSE 0 END) AS covered_cases,

            SUM(CASE WHEN ai_decision = 'MATCH' THEN 1 ELSE 0 END) AS match_cases,
            SUM(CASE WHEN ai_decision = 'REVIEW_ONCE' THEN 1 ELSE 0 END) AS review_once_cases,
            SUM(CASE WHEN ai_decision = 'BLOCK' THEN 1 ELSE 0 END) AS blocked_cases,

            SUM(CASE WHEN ai_category = 'LOAD OPPORTUNITY' THEN 1 ELSE 0 END) AS load_opportunity_cases,
            SUM(CASE WHEN ai_category = 'RATE CHECK' THEN 1 ELSE 0 END) AS rate_check_cases,
            SUM(CASE WHEN ai_category = 'BROKER REVIEW' THEN 1 ELSE 0 END) AS broker_review_cases,
            SUM(CASE WHEN ai_category = 'CONESTOGA VERIFY' THEN 1 ELSE 0 END) AS conestoga_verify_cases,

            SUM(telegram_alert_count) AS telegram_alerts,
            SUM(dispatcher_feedback_count) AS feedback_items,
            SUM(ratecon_count) AS ratecons
        FROM dispatch_cases
        {where_clause}
        GROUP BY driver_name
        ORDER BY feedback_items DESC, telegram_alerts DESC, total_cases DESC
        LIMIT ?
    """

    query_params = list(params)
    query_params.append(args.limit)

    cursor = connection.cursor()
    cursor.execute(query, query_params)
    return cursor.fetchall()


def count_feedback_by_driver(rows):
    counts = {}

    for row in rows:
        driver_name = row["driver_name"] or "UNKNOWN"
        feedback = row["feedback"] or "UNKNOWN"

        if driver_name not in counts:
            counts[driver_name] = {}

        counts[driver_name][feedback] = counts[driver_name].get(feedback, 0) + 1

    return counts


def count_feedback_by_lane(rows):
    lane_counts = {}

    for row in rows:
        driver_name = row["driver_name"] or "UNKNOWN"
        pickup = row["pickup"] or "UNKNOWN"
        delivery = row["delivery"] or "UNKNOWN"
        feedback = row["feedback"] or "UNKNOWN"

        key = (driver_name, pickup, delivery, feedback)
        lane_counts[key] = lane_counts.get(key, 0) + 1

    return lane_counts


def classify_feedback_signal(feedback):
    feedback = str(feedback or "").lower().strip()

    if feedback in DRIVER_POSITIVE_FEEDBACK:
        return "DRIVER_POSITIVE"

    if feedback in RATE_SIGNAL_FEEDBACK:
        return "RATE_SIGNAL"

    if feedback in BROKER_SIGNAL_FEEDBACK:
        return "BROKER_SIGNAL"

    if feedback in BROKER_OR_MARKET_SIGNAL_FEEDBACK:
        return "BROKER_OR_MARKET_SIGNAL"

    if feedback in WORKFLOW_SIGNAL_FEEDBACK:
        return "WORKFLOW_SIGNAL"

    if feedback in DISPATCHER_OR_DRIVER_NEGATIVE_FEEDBACK:
        return "DISPATCHER_OR_DRIVER_NEGATIVE"

    return "OTHER"

def build_driver_recommendations(driver_name, feedback_counts):
    recommendations = []

    booked = feedback_counts.get("booked", 0)
    sent_to_driver = feedback_counts.get("sent_to_driver", 0)
    ratecon_received = feedback_counts.get("ratecon_received", 0)
    driver_rejected = feedback_counts.get("driver_rejected", 0)
    skipped = feedback_counts.get("skipped", 0)
    rate_too_low = feedback_counts.get("rate_too_low", 0)
    bad_broker = feedback_counts.get("bad_broker", 0)
    covered = feedback_counts.get("covered", 0)
    called_broker = feedback_counts.get("called_broker", 0)

    if booked >= 1 or ratecon_received >= 1:
        recommendations.append(
            {
                "level": "POSITIVE",
                "type": "STRONG_DRIVER_ACCEPTANCE_SIGNAL",
                "text": (
                    f"{driver_name} has successful outcome signal: "
                    f"booked={booked}, ratecon_received={ratecon_received}. "
                    "This can support future driver preference learning."
                ),
            }
        )

    if sent_to_driver >= 2:
        recommendations.append(
            {
                "level": "POSITIVE",
                "type": "DRIVER_INTEREST_SIGNAL",
                "text": (
                    f"{driver_name} had {sent_to_driver} load(s) sent to driver. "
                    "Use as weak positive interest signal, not as confirmed acceptance."
                ),
            }
        )

    if driver_rejected >= 2:
        recommendations.append(
            {
                "level": "MEDIUM",
                "type": "DRIVER_REJECTION_PATTERN",
                "text": (
                    f"{driver_name} rejected loads {driver_rejected}x. "
                    "Review lane, weight, timing, equipment, appointment type, and rate."
                ),
            }
        )

    if skipped >= 2:
        recommendations.append(
            {
                "level": "LOW",
                "type": "DISPATCHER_OR_DRIVER_SKIP_PATTERN",
                "text": (
                    f"Dispatcher skipped {driver_name}'s loads {skipped}x. "
                    "This may mean driver preference issue, dispatcher choice, or AI over-ranking. "
                    "Do not auto-update driver profile yet."
                ),
            }
        )

    if rate_too_low >= 2:
        recommendations.append(
            {
                "level": "MEDIUM",
                "type": "RATE_SIGNAL_NOT_PURE_DRIVER_SIGNAL",
                "text": (
                    f"{driver_name} has repeated rate_too_low feedback {rate_too_low}x. "
                    "Treat this primarily as rate/market signal. Review target RPM and market bucket assumptions "
                    "before changing driver preferences."
                ),
            }
        )

    if bad_broker >= 1:
        recommendations.append(
            {
                "level": "BROKER",
                "type": "BROKER_SIGNAL_NOT_DRIVER_SIGNAL",
                "text": (
                    f"{driver_name} has bad_broker feedback {bad_broker}x. "
                    "Treat this as broker memory, not driver preference."
                ),
            }
        )

    if covered >= 1:
        recommendations.append(
            {
                "level": "MARKET",
                "type": "COVERED_MARKET_SIGNAL",
                "text": (
                    f"{driver_name} has covered feedback {covered}x. "
                    "Treat this as broker/market timing signal, not driver rejection."
                ),
            }
        )

    if called_broker >= 2:
        recommendations.append(
            {
                "level": "WORKFLOW",
                "type": "CALL_ACTIVITY_SIGNAL",
                "text": (
                    f"{driver_name} has called_broker feedback {called_broker}x. "
                    "This shows dispatcher workflow activity, not necessarily driver preference."
                ),
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "level": "INFO",
                "type": "INSUFFICIENT_DRIVER_SIGNAL",
                "text": (
                    f"Not enough repeated driver-specific signal for {driver_name} yet."
                ),
            }
        )

    return recommendations
def print_overview(driver_summaries, feedback_rows):
    print("")
    print("Driver Learning Overview")
    print("------------------------")
    print(f"Drivers analyzed: {len(driver_summaries)}")
    print(f"Feedback rows scanned: {len(feedback_rows)}")

    total_cases = sum(row["total_cases"] or 0 for row in driver_summaries)
    total_alerts = sum(row["telegram_alerts"] or 0 for row in driver_summaries)
    total_feedback = sum(row["feedback_items"] or 0 for row in driver_summaries)

    print(f"Total cases: {total_cases}")
    print(f"Total Telegram alerts: {total_alerts}")
    print(f"Total feedback items: {total_feedback}")


def print_driver_summaries(driver_summaries, feedback_counts_by_driver, args):
    print("")
    print("Driver Summaries")
    print("----------------")

    if not driver_summaries:
        print("No driver records found.")
        return

    for row in driver_summaries:
        driver_name = row["driver_name"] or "UNKNOWN"
        feedback_counts = feedback_counts_by_driver.get(driver_name, {})

        print("")
        print(f"Driver: {driver_name}")
        print(
            f"Cases: {row['total_cases']} | "
            f"TG: {row['telegram_alerts'] or 0} | "
            f"Feedback: {row['feedback_items'] or 0} | "
            f"RateCons: {row['ratecons'] or 0}"
        )
        print(
            f"Statuses: "
            f"OPEN {row['open_cases'] or 0} | "
            f"CALLED {row['called_cases'] or 0} | "
            f"SENT_TO_DRIVER {row['sent_to_driver_cases'] or 0} | "
            f"BOOKED {row['booked_cases'] or 0} | "
            f"RATECON {row['ratecon_received_cases'] or 0} | "
            f"REJECTED {row['rejected_cases'] or 0} | "
            f"SKIPPED {row['skipped_cases'] or 0} | "
            f"COVERED {row['covered_cases'] or 0}"
        )
        print(
            f"AI: "
            f"MATCH {row['match_cases'] or 0} | "
            f"REVIEW_ONCE {row['review_once_cases'] or 0} | "
            f"BLOCK {row['blocked_cases'] or 0}"
        )
        print(
            f"Categories: "
            f"LOAD_OPP {row['load_opportunity_cases'] or 0} | "
            f"RATE_CHECK {row['rate_check_cases'] or 0} | "
            f"BROKER_REVIEW {row['broker_review_cases'] or 0} | "
            f"CONESTOGA_VERIFY {row['conestoga_verify_cases'] or 0}"
        )

        if feedback_counts:
            print("Feedback:")
            for feedback, count in sorted(
                feedback_counts.items(),
                key=lambda item: (-item[1], item[0]),
            ):
                signal_type = classify_feedback_signal(feedback)
                print(f"- {feedback}: {count} ({signal_type})")
        else:
            print("Feedback: none")

        if args.show_recommendations:
            recommendations = build_driver_recommendations(
                driver_name=driver_name,
                feedback_counts=feedback_counts,
            )

            print("Recommendations:")
            for recommendation in recommendations:
                print(
                    f"- [{recommendation['level']}] "
                    f"{recommendation['type']}: {recommendation['text']}"
                )


def print_lane_signals(feedback_rows, args):
    if not args.show_lanes:
        return

    lane_counts = count_feedback_by_lane(feedback_rows)

    print("")
    print("Driver Lane Feedback Signals")
    print("----------------------------")

    if not lane_counts:
        print("No lane feedback signals.")
        return

    sorted_lanes = sorted(
        lane_counts.items(),
        key=lambda item: (-item[1], item[0]),
    )

    shown = 0

    for (driver_name, pickup, delivery, feedback), count in sorted_lanes:
        if shown >= args.limit:
            break

        print(
            f"{driver_name} | {pickup} -> {delivery} | "
            f"{feedback}: {count}"
        )

        shown += 1


def print_recent_feedback(feedback_rows, args):
    if args.summary:
        return

    print("")
    print("Recent Driver Feedback")
    print("----------------------")

    if not feedback_rows:
        print("No recent feedback.")
        return

    for row in feedback_rows[: args.limit]:
        signal_type = classify_feedback_signal(row["feedback"])

        print("")
        print(f"Time: {row['timestamp_utc']}")
        print(f"Driver: {row['driver_name']}")
        print(f"Feedback: {row['feedback']} ({signal_type})")
        print(f"Note: {row['note']}")
        print(f"Source: {row['source']}")
        print(
            f"Case: {row['case_id']} | "
            f"{row['status']} | "
            f"Final: {row['final_outcome'] or 'NONE'} | "
            f"{row['ai_decision']}/{row['ai_category']}"
        )
        print(
            f"Load: {row['pickup']} -> {row['delivery']} | "
            f"Rate: ${row['rate']} | RPM: {row['total_rpm']} | "
            f"Weight: {row['weight']} | Trailer: {row['posted_trailer_type']}"
        )
        print(
            f"Broker: {row['broker_name']} | MC: {row['broker_mc']} | "
            f"REF: {row['reference_id']}"
        )
        print(
            "Replay: "
            f"py scripts/case_replay_report.py {row['reference_id']} "
            f"{row['driver_name']} --latest"
        )


def build_parser():
    parser = argparse.ArgumentParser(
        description="Analyze driver learning signals from dispatch feedback."
    )

    parser.add_argument("--driver", default="")
    parser.add_argument("--feedback", default="")
    parser.add_argument("--category", default="")
    parser.add_argument("--broker-mc", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--scan-limit", type=int, default=500)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--show-lanes", action="store_true")
    parser.add_argument("--show-recommendations", action="store_true")

    return parser


def main():
    args = build_parser().parse_args()

    if not SQLITE_DB_FILE.exists():
        print(f"Missing SQLite database: {SQLITE_DB_FILE}")
        print("Run first:")
        print("py scripts/build_sqlite_memory.py")
        return

    connection = connect_db()

    driver_summaries = get_driver_case_summary(connection, args)
    feedback_rows = get_driver_feedback_rows(connection, args)

    connection.close()

    feedback_counts_by_driver = count_feedback_by_driver(feedback_rows)

    print("=" * 80)
    print("DRIVER LEARNING REPORT")
    print("=" * 80)

    print_overview(driver_summaries, feedback_rows)
    print_driver_summaries(
        driver_summaries=driver_summaries,
        feedback_counts_by_driver=feedback_counts_by_driver,
        args=args,
    )
    print_lane_signals(feedback_rows, args)
    print_recent_feedback(feedback_rows, args)


if __name__ == "__main__":
    main()