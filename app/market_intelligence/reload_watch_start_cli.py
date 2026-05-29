import argparse

from app.market_intelligence.reload_watch_repository import RELOAD_WATCH_FILE
from app.market_intelligence.reload_watch_service import start_reload_watch


def build_parser():
    parser = argparse.ArgumentParser(
        description="Start one reload-watch record without live automation."
    )
    parser.add_argument("--watch-id", default="", help="Reload-watch id to create.")
    parser.add_argument("--driver-name", default="")
    parser.add_argument("--parent-load-id", default="")
    parser.add_argument("--parent-reference-id", default="")
    parser.add_argument("--pickup", default="")
    parser.add_argument("--delivery", default="")
    parser.add_argument("--rate", type=float, default=None)
    parser.add_argument("--clean-exits", type=int, default=None)
    parser.add_argument("--review-exits", type=int, default=None)
    parser.add_argument("--rate-check-exits", type=int, default=None)
    parser.add_argument("--timestamp", default="", help="UTC timestamp to record.")
    parser.add_argument(
        "--file-path",
        default=RELOAD_WATCH_FILE,
        help="Reload-watch JSON records file.",
    )

    return parser


def compact_number(value):
    if value is None:
        return None

    if isinstance(value, float) and value.is_integer():
        return int(value)

    return value


def optional_dict(pairs):
    data = {}

    for key, value in pairs:
        value = compact_number(value)
        if value in ["", None]:
            continue
        data[key] = value

    return data


def build_parent_load(args):
    return optional_dict(
        [
            ("load_id", args.parent_load_id),
            ("reference_id", args.parent_reference_id),
            ("driver_name", args.driver_name),
            ("pickup", args.pickup),
            ("delivery", args.delivery),
            ("rate", args.rate),
        ]
    )


def build_payload(args):
    return optional_dict(
        [
            ("clean_exit_count", args.clean_exits),
            ("review_exit_count", args.review_exits),
            ("rate_check_exit_count", args.rate_check_exits),
        ]
    )


def delivery_text(record):
    city = str(record.get("delivery_city", "") or "").strip()
    state = str(record.get("delivery_state", "") or "").strip()

    if city and state:
        return f"{city}, {state}"

    if city:
        return city

    if state:
        return state

    return "NEEDS CHECK"


def number_text(value):
    value = compact_number(value)
    return "0" if value in ["", None] else str(value)


def print_start_summary(result, file_path):
    watch_record = result.get("watch_record") or {}

    print("RELOAD WATCH START DRY-RUN")
    print("--------------------------")

    if not result.get("saved"):
        print(f"ERROR: {result.get('reason', 'Reload watch was not started.')}")
        return

    print(f"watch_id: {watch_record.get('watch_id', '')}")
    print(f"saved: {result.get('saved', False)}")
    print(f"watch_status: {watch_record.get('watch_status', '')}")
    print(f"driver_name: {watch_record.get('driver_name', '')}")
    print(f"parent_reference_id: {watch_record.get('parent_reference_id', '')}")
    print(f"delivery: {delivery_text(watch_record)}")
    print(f"clean_exit_count: {number_text(watch_record.get('clean_exit_count', 0))}")
    print(f"review_exit_count: {number_text(watch_record.get('review_exit_count', 0))}")
    print(
        "rate_check_exit_count: "
        f"{number_text(watch_record.get('rate_check_exit_count', 0))}"
    )
    print(f"file_path: {file_path}")
    print(f"reason: {result.get('reason', '')}")


def run_start_reload_watch(args):
    result = start_reload_watch(
        watch_id=args.watch_id,
        parent_load=build_parent_load(args),
        payload=build_payload(args),
        timestamp_utc=args.timestamp,
        file_path=args.file_path,
    )

    print_start_summary(result, args.file_path)

    return 0 if result.get("saved") else 1


def main(argv=None):
    args = build_parser().parse_args(argv)

    return run_start_reload_watch(args)
