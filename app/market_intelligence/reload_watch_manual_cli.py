import argparse
import sys

from app.market_intelligence.reload_watch_repository import RELOAD_WATCH_FILE
from app.market_intelligence.reload_watch_service import handle_reload_watch_event
from app.market_intelligence.telegram_watch_formatter import (
    format_reload_watch_message,
)


SUPPORTED_EVENTS = [
    "NORMAL_STATUS_DUE",
    "MUTE_WATCH_UPDATES",
    "PARENT_LOAD_UPDATED",
    "PARENT_LOAD_REMOVED",
    "CLEAN_EXIT_FOUND",
    "STRONG_CHAIN_FOUND",
    "DRIVER_LOADED",
    "STOP_SEARCH",
]


def build_parser():
    parser = argparse.ArgumentParser(
        description="Dry-run one reload-watch event without sending Telegram."
    )
    parser.add_argument("--watch-id", default="", help="Reload-watch id to update.")
    parser.add_argument(
        "--event",
        required=True,
        choices=SUPPORTED_EVENTS,
        help="Reload-watch event to simulate.",
    )
    parser.add_argument(
        "--file-path",
        default=RELOAD_WATCH_FILE,
        help="Reload-watch JSON records file.",
    )
    parser.add_argument("--timestamp", default="", help="UTC timestamp to record.")
    parser.add_argument("--old-rate", type=float, default=None)
    parser.add_argument("--new-rate", type=float, default=None)
    parser.add_argument("--clean-exits", type=int, default=None)
    parser.add_argument("--review-exits", type=int, default=None)
    parser.add_argument("--rate-check-exits", type=int, default=None)
    parser.add_argument("--best-exit-reference-id", default="")
    parser.add_argument("--best-exit-pickup", default="")
    parser.add_argument("--best-exit-delivery", default="")
    parser.add_argument("--best-exit-rate", type=float, default=None)
    parser.add_argument("--chain-status", default="")
    parser.add_argument("--combined-rpm", type=float, default=None)
    parser.add_argument("--market-median-rpm", type=float, default=None)
    parser.add_argument(
        "--preview-message",
        action="store_true",
        help="Print Telegram formatter preview text without sending anything.",
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


def build_exit_context(args):
    return optional_dict(
        [
            ("clean_exit_count", args.clean_exits),
            ("review_exit_count", args.review_exits),
            ("rate_check_exit_count", args.rate_check_exits),
        ]
    )


def build_best_exit_load(args):
    return optional_dict(
        [
            ("reference_id", args.best_exit_reference_id),
            ("pickup", args.best_exit_pickup),
            ("delivery", args.best_exit_delivery),
            ("rate", args.best_exit_rate),
        ]
    )


def build_chain_result(args):
    return optional_dict(
        [
            ("chain_status", args.chain_status),
            ("combined_rpm", args.combined_rpm),
            ("market_median_rpm", args.market_median_rpm),
        ]
    )


def build_rate_update(args):
    return optional_dict(
        [
            ("old_rate", args.old_rate),
            ("new_rate", args.new_rate),
        ]
    )


def print_result_summary(result):
    action_plan = result.get("action_plan") or {}
    watch_record = result.get("watch_record") or {}

    print("RELOAD WATCH EVENT DRY-RUN")
    print("--------------------------")

    if not result.get("saved"):
        print(f"ERROR: {result.get('reason', 'Reload watch event failed.')}")
        return

    print(f"watch_id: {watch_record.get('watch_id', '')}")
    print(f"event_type: {action_plan.get('event_type', '')}")
    print(f"action_type: {action_plan.get('action_type', '')}")
    print(f"watch_status: {watch_record.get('watch_status', '')}")
    print(f"continue_watch: {action_plan.get('continue_watch', False)}")
    print(f"stop_watch: {action_plan.get('stop_watch', False)}")
    print(f"send_normal_status: {action_plan.get('send_normal_status', False)}")
    print(f"send_critical_alert: {action_plan.get('send_critical_alert', False)}")
    print(f"saved: {result.get('saved', False)}")
    print(f"reason: {result.get('reason', '')}")


def print_preview(action_plan):
    print("")
    print("TELEGRAM PREVIEW ONLY - no message sent")
    print("---------------------------------------")

    preview = format_reload_watch_message(action_plan)

    if preview:
        print(console_safe_text(preview))
    else:
        print("No preview text for this action.")


def console_safe_text(text):
    text = str(text)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"

    try:
        text.encode(encoding)
    except UnicodeEncodeError:
        return text.encode(encoding, errors="replace").decode(encoding)

    return text


def run_reload_watch_event(args):
    result = handle_reload_watch_event(
        watch_id=args.watch_id,
        event_type=args.event,
        exit_context=build_exit_context(args),
        best_exit_load=build_best_exit_load(args),
        chain_result=build_chain_result(args),
        rate_update=build_rate_update(args),
        timestamp_utc=args.timestamp,
        file_path=args.file_path,
    )

    print_result_summary(result)

    if result.get("saved") and args.preview_message:
        print_preview(result.get("action_plan") or {})

    return 0 if result.get("saved") else 1


def main(argv=None):
    args = build_parser().parse_args(argv)

    return run_reload_watch_event(args)
