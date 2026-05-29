import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.case_event_normalizer_report import (  # noqa: E402
    build_case_event_normalizer_report,
)
from tests.fixtures.normalized_event_wrapper_cases import (  # noqa: E402
    NORMALIZED_EVENT_WRAPPER_CASES,
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
        for scenario in NORMALIZED_EVENT_WRAPPER_CASES
    ]
    report = build_case_event_normalizer_report(events)

    print("NORMALIZED CASE EVENT WRAPPER REPORT DRY-RUN")
    print(f"Total events: {report['total_events']}")
    print(f"Normalized events: {report['normalized_count']}")
    print(f"Unknown event types: {report['unknown_event_type_count']}")
    print(f"Warnings: {report['warnings_count']}")
    print(f"Event type counts: {format_counts(report['counts_by_event_type'])}")
    print(f"Event group counts: {format_counts(report['counts_by_event_group'])}")
    print(f"Warning counts: {format_counts(report['warnings_by_type'])}")
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
    print("DRY RUN ONLY - normalized event wrapper report, no events written")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
