import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.decision_engine.combined_report import (  # noqa: E402
    build_decision_timeline_comparison_report,
)
from tests.fixtures.decision_engine_combined_report_loads import (  # noqa: E402
    DECISION_ENGINE_COMBINED_REPORT_LOADS,
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
    loads = [
        scenario["load"]
        for scenario in DECISION_ENGINE_COMBINED_REPORT_LOADS
    ]
    report = build_decision_timeline_comparison_report(loads)

    print("DECISIONENGINE TIMELINE COMBINED REPORT DRY-RUN")
    print(f"Total loads: {report['total']}")
    print(f"Decisions by type: {format_counts(report['decisions_by_type'])}")
    print(f"Risk flag summary: {format_counts(report['risk_flag_summary'])}")
    print(f"Warning count: {report['warning_count']}")
    print(f"Preview events: {report['preview_event_count']}")
    print("")

    for item in report["items"]:
        result = item["decision_result"]
        print(
            f"- {item['load_id'] or 'NO_LOAD_ID'} / "
            f"{item['reference_id'] or 'NO_REFERENCE_ID'} | "
            f"original: {item['original_decision'] or 'NO_DECISION'} "
            f"({item['original_category'] or 'NO_CATEGORY'}) | "
            f"result: {result['decision']} ({result['category'] or 'NO_CATEGORY'})"
        )

    print("")
    print("DRY RUN ONLY - DecisionEngine timeline combined report, no events written")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
