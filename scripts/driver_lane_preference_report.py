import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.driver_lane_preference_rules import (
    average,
    build_lane_groups,
    classify_lane_signal,
    connect_db,
    format_lane_preference_status,
    get_lane_feedback_rows,
)
from app.market_intelligence.sqlite_memory import SQLITE_DB_FILE


def print_overview(lane_groups):
    print("")
    print("Driver Lane Preference Overview")
    print("-------------------------------")
    print(f"Lanes with feedback: {len(lane_groups)}")

    status_counts = {}

    for group in lane_groups:
        classification = classify_lane_signal(group["feedback_counts"])
        status = classification.get("status", "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1

    print("")
    print("Lane Signal Counts")
    print("------------------")

    if not status_counts:
        print("No lane signals.")
        return

    for status, count in sorted(
        status_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        print(f"{status}: {count}")


def print_lane_groups(lane_groups, args):
    print("")
    print("Driver Lane Preference Details")
    print("------------------------------")

    if not lane_groups:
        print("No lane feedback found.")
        return

    sorted_groups = sorted(
        lane_groups,
        key=lambda group: (
            -sum(group["feedback_counts"].values()),
            group["driver_name"],
            group["pickup"],
            group["delivery"],
        ),
    )

    shown = 0

    for group in sorted_groups:
        if shown >= args.limit:
            break

        feedback_counts = group["feedback_counts"]
        classification = classify_lane_signal(feedback_counts)

        if args.only_actionable:
            if classification.get("status") in [
                "INSUFFICIENT_LANE_DATA",
                "WEAK_POSITIVE_LANE",
            ]:
                continue

        avg_rate = average(group["avg_rate_values"])
        avg_miles = average(group["avg_miles_values"])
        avg_rpm = average(group["avg_rpm_values"])
        avg_weight = average(group["avg_weight_values"])

        print("")
        print(
            f"{group['driver_name']} | "
            f"{group['pickup']} -> {group['delivery']}"
        )
        print(f"Lane Status: {format_lane_preference_status(classification)}")
        print(
            f"Cases: {group['case_count']} | "
            f"Avg rate: ${round(avg_rate, 2)} | "
            f"Avg RPM: {round(avg_rpm, 2)} | "
            f"Avg miles: {round(avg_miles, 1)} | "
            f"Avg weight: {round(avg_weight, 1)}"
        )
        print(
            f"AI: MATCH {group['match_cases']} | "
            f"REVIEW_ONCE {group['review_once_cases']} | "
            f"BLOCK {group['blocked_cases']}"
        )
        print(
            f"Categories: LOAD_OPP {group['load_opportunity_cases']} | "
            f"RATE_CHECK {group['rate_check_cases']} | "
            f"BROKER_REVIEW {group['broker_review_cases']}"
        )

        print("Feedback:")
        for feedback, count in sorted(
            feedback_counts.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            print(f"- {feedback}: {count}")

        print(f"Latest feedback: {group['latest_feedback']}")

        shown += 1

    if shown == 0:
        print("No actionable lane signals found.")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Analyze driver preference signals by lane."
    )

    parser.add_argument("--driver", default="")
    parser.add_argument("--pickup", default="")
    parser.add_argument("--delivery", default="")
    parser.add_argument("--broker-mc", default="")
    parser.add_argument("--feedback", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--scan-limit", type=int, default=500)
    parser.add_argument("--summary", action="store_true")
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
    rows = get_lane_feedback_rows(
        connection=connection,
        driver_name=args.driver,
        pickup=args.pickup,
        delivery=args.delivery,
        broker_mc=args.broker_mc,
        feedback=args.feedback,
        limit=args.scan_limit,
    )
    connection.close()

    lane_groups = build_lane_groups(rows)

    print("=" * 80)
    print("DRIVER LANE PREFERENCE REPORT")
    print("=" * 80)

    print_overview(lane_groups)

    if not args.summary:
        print_lane_groups(lane_groups, args)


if __name__ == "__main__":
    main()