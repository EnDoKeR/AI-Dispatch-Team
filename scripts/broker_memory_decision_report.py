import argparse
import json
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE


BROKER_MEMORY_KEYWORDS = [
    "broker memory requires review",
    "broker memory shows rate negotiation risk",
    "broker memory watchlist",
    "broker memory positive signal",
]


def connect_db():
    connection = sqlite3.connect(SQLITE_DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def normalize(value):
    return str(value or "").strip().lower()


def parse_reasons(reasons_json):
    if not reasons_json:
        return []

    try:
        reasons = json.loads(reasons_json)
    except json.JSONDecodeError:
        return []

    if not isinstance(reasons, list):
        return []

    return [str(reason) for reason in reasons]


def broker_memory_reasons(reasons):
    matched_reasons = []

    for reason in reasons:
        reason_lower = normalize(reason)

        for keyword in BROKER_MEMORY_KEYWORDS:
            if keyword in reason_lower:
                matched_reasons.append(reason)
                break

    return matched_reasons


def build_where_clause(args):
    filters = []
    params = []

    if args.driver:
        filters.append("LOWER(driver_name) = LOWER(?)")
        params.append(args.driver)

    if args.broker_mc:
        filters.append("broker_mc = ?")
        params.append(args.broker_mc)

    if args.status:
        filters.append("LOWER(status) = LOWER(?)")
        params.append(args.status)

    if args.category:
        filters.append("LOWER(ai_category) = LOWER(?)")
        params.append(args.category)

    if args.decision:
        filters.append("LOWER(ai_decision) = LOWER(?)")
        params.append(args.decision)

    if not filters:
        return "", params

    return "WHERE " + " AND ".join(filters), params


def fetch_cases(connection, args):
    where_clause, params = build_where_clause(args)

    query = f"""
        SELECT
            case_id,
            created_at_utc,
            updated_at_utc,
            status,
            final_outcome,

            driver_name,
            driver_location,
            driver_equipment,

            load_id,
            reference_id,
            pickup,
            delivery,
            rate,
            total_miles,
            total_rpm,
            weight,
            posted_trailer_type,

            broker_name,
            broker_mc,
            broker_status,

            ai_decision,
            ai_category,
            ai_score,
            ai_priority,
            ai_suggested_action,
            ai_reasons_json,

            telegram_alert_count,
            dispatcher_feedback_count,
            ratecon_count,
            events_count
        FROM dispatch_cases
        {where_clause}
        ORDER BY updated_at_utc DESC
        LIMIT ?
    """

    query_params = list(params)
    query_params.append(args.scan_limit)

    cursor = connection.cursor()
    cursor.execute(query, query_params)
    return cursor.fetchall()


def collect_broker_memory_decisions(rows):
    results = []

    for row in rows:
        reasons = parse_reasons(row["ai_reasons_json"])
        matched_reasons = broker_memory_reasons(reasons)

        if not matched_reasons:
            continue

        results.append(
            {
                "row": row,
                "broker_memory_reasons": matched_reasons,
            }
        )

    return results


def print_overview(results):
    print("")
    print("Broker Memory Decision Overview")
    print("-------------------------------")
    print(f"Cases affected by broker memory: {len(results)}")

    by_category = {}
    by_decision = {}
    by_broker = {}

    for item in results:
        row = item["row"]

        category = row["ai_category"] or "UNKNOWN"
        decision = row["ai_decision"] or "UNKNOWN"
        broker_mc = row["broker_mc"] or "UNKNOWN"
        broker_name = row["broker_name"] or "UNKNOWN"
        broker_key = f"{broker_mc} | {broker_name}"

        by_category[category] = by_category.get(category, 0) + 1
        by_decision[decision] = by_decision.get(decision, 0) + 1
        by_broker[broker_key] = by_broker.get(broker_key, 0) + 1

    print("")
    print("By decision:")
    if by_decision:
        for key, count in sorted(by_decision.items(), key=lambda item: (-item[1], item[0])):
            print(f"- {key}: {count}")
    else:
        print("- No data.")

    print("")
    print("By category:")
    if by_category:
        for key, count in sorted(by_category.items(), key=lambda item: (-item[1], item[0])):
            print(f"- {key}: {count}")
    else:
        print("- No data.")

    print("")
    print("By broker:")
    if by_broker:
        for key, count in sorted(by_broker.items(), key=lambda item: (-item[1], item[0])):
            print(f"- {key}: {count}")
    else:
        print("- No data.")


def print_cases(results, limit):
    print("")
    print("Broker Memory Affected Cases")
    print("----------------------------")

    if not results:
        print("No broker memory affected cases found.")
        return

    for item in results[:limit]:
        row = item["row"]
        reasons = item["broker_memory_reasons"]

        print("")
        print(
            f"{row['case_id']} | {row['driver_name']} | "
            f"{row['status']} | {row['ai_decision']}/{row['ai_category']}"
        )
        print(
            f"Lane: {row['pickup']} -> {row['delivery']} | "
            f"Rate: ${row['rate']} | RPM: {row['total_rpm']} | "
            f"REF: {row['reference_id']}"
        )
        print(
            f"Broker: {row['broker_name']} | MC: {row['broker_mc']} | "
            f"Broker Status: {row['broker_status']}"
        )
        print(
            f"Activity: TG:{row['telegram_alert_count']} "
            f"FB:{row['dispatcher_feedback_count']} "
            f"RC:{row['ratecon_count']} "
            f"EV:{row['events_count']}"
        )

        print("Broker memory reasons:")
        for reason in reasons:
            print(f"- {reason}")

        print(
            "Replay: "
            f"py scripts/case_replay_report.py {row['reference_id']} "
            f"{row['driver_name']} --latest"
        )


def print_recommendations(results):
    print("")
    print("Review Recommendations")
    print("----------------------")

    if not results:
        print("No recommendations.")
        return

    high_risk_count = 0
    rate_negotiation_count = 0
    positive_count = 0

    for item in results:
        reasons = " ".join(item["broker_memory_reasons"]).lower()

        if "bad_broker" in reasons or "risk: high" in reasons:
            high_risk_count += 1

        if "rate_too_low" in reasons or "rate negotiation" in reasons:
            rate_negotiation_count += 1

        if "positive signal" in reasons or "booked" in reasons or "ratecon_received" in reasons:
            positive_count += 1

    if high_risk_count:
        print(
            f"- {high_risk_count} case(s) affected by high-risk broker memory. "
            "Keep as REVIEW_ONCE; do not auto-block until dispatcher confirms."
        )

    if rate_negotiation_count:
        print(
            f"- {rate_negotiation_count} case(s) affected by rate negotiation memory. "
            "Keep review/rate-check flow and compare broker offers against target RPM."
        )

    if positive_count:
        print(
            f"- {positive_count} case(s) have positive broker memory signals. "
            "Use as confidence boost, not as automatic booking."
        )

    if not high_risk_count and not rate_negotiation_count and not positive_count:
        print("- Broker memory is present, but no strong recommendation category was detected.")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Report cases where broker memory affected AI decision reasons."
    )

    parser.add_argument("--driver", default="")
    parser.add_argument("--broker-mc", default="")
    parser.add_argument("--status", default="")
    parser.add_argument("--category", default="")
    parser.add_argument("--decision", default="")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--scan-limit", type=int, default=500)

    return parser


def main():
    args = build_parser().parse_args()

    if not SQLITE_DB_FILE.exists():
        print(f"Missing SQLite database: {SQLITE_DB_FILE}")
        print("Run first:")
        print("py scripts/build_sqlite_memory.py")
        return

    connection = connect_db()
    rows = fetch_cases(connection, args)
    connection.close()

    results = collect_broker_memory_decisions(rows)

    print("=" * 80)
    print("BROKER MEMORY DECISION REPORT")
    print("=" * 80)

    print_overview(results)
    print_recommendations(results)

    if not args.summary:
        print_cases(results, args.limit)


if __name__ == "__main__":
    main()