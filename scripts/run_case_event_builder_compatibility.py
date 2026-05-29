import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.case_event_builder_report import (  # noqa: E402
    build_case_event_builder_shape_report,
)
from tests.fixtures.case_event_builder_outputs import (  # noqa: E402
    SYNTHETIC_CASE_EVENT_BUILDER_OUTPUTS,
)


def format_counts(counts):
    if not counts:
        return "none"

    return ", ".join(
        f"{key or 'EMPTY'}: {value}"
        for key, value in sorted(counts.items())
    )


def format_list(items):
    return ", ".join(items) if items else "none"


def main(argv=None):
    _ = argv
    report = build_case_event_builder_shape_report(
        SYNTHETIC_CASE_EVENT_BUILDER_OUTPUTS
    )

    print("CASE EVENT BUILDER COMPATIBILITY DRY-RUN")
    print(f"Total event samples: {report['total_events']}")
    print(f"Known event types: {report['total_events'] - len(report['unknown_event_types'])}")
    print(f"Unknown event types: {format_list(report['unknown_event_types'])}")
    print(f"Event groups: {format_counts(report['event_group_summary'])}")
    print(f"JSON serializable: {report['json_serializable']}")
    print("")

    print("Keys by event type:")
    for event_type, keys in report["keys_by_event_type"].items():
        print(f"- {event_type}: {format_list(keys)}")

    print("")
    print("Missing base payload keys:")
    for event_type, keys in report["missing_base_keys_by_event_type"].items():
        print(f"- {event_type}: {format_list(keys)}")

    print("")
    print("DRY RUN ONLY - event builder compatibility report only")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
