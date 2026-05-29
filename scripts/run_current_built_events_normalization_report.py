import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.case_event_built_report import (  # noqa: E402
    build_current_built_events_normalization_report,
)
from tests.fixtures.current_built_event_samples import (  # noqa: E402
    CURRENT_BUILT_EVENT_SAMPLES,
)


def format_counts(counts):
    if not counts:
        return "none"

    return ", ".join(
        f"{key or 'NO_VALUE'}: {value}"
        for key, value in sorted(counts.items())
    )


def main(argv=None):
    _ = argv
    events = [
        scenario["event"]
        for scenario in CURRENT_BUILT_EVENT_SAMPLES
    ]
    report = build_current_built_events_normalization_report(events)

    print("CURRENT BUILT-EVENTS NORMALIZATION REPORT DRY-RUN")
    print(f"Total events: {report['total_events']}")
    print(f"Known events: {report['known_event_count']}")
    print(f"Unknown events: {report['unknown_event_count']}")
    print(f"Warnings: {report['warnings_count']}")
    print(f"Warning counts: {format_counts(report['warnings_by_type'])}")
    print(f"Event type counts: {format_counts(report['counts_by_event_type'])}")
    print(f"Event group counts: {format_counts(report['counts_by_event_group'])}")
    print("")

    for wrapper in report["normalized_events"]:
        payload = wrapper["normalized_payload"]
        warnings = ", ".join(wrapper["warnings"]) or "none"
        print(
            f"- {payload['event_type'] or 'NO_EVENT_TYPE'} | "
            f"{payload['event_group'] or 'NO_GROUP'} | "
            f"warnings: {warnings}"
        )

    print("")
    print("DRY RUN ONLY - current built-events normalization report, no runtime data read")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
