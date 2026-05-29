import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.decision_engine.timeline_preview import (  # noqa: E402
    build_decision_result_timeline_preview,
)
from app.market_intelligence.decision_engine.timeline_preview_report import (  # noqa: E402
    build_decision_result_timeline_preview_report,
)
from tests.fixtures.decision_result_timeline_previews import (  # noqa: E402
    DECISION_RESULT_TIMELINE_PREVIEWS,
)


def format_counts(counts):
    if not counts:
        return "none"

    return ", ".join(
        f"{key or 'EMPTY'}: {value}"
        for key, value in sorted(counts.items())
    )


def build_previews():
    return [
        build_decision_result_timeline_preview(
            fixture["decision_result"],
            case_id=fixture["case_id"],
            timestamp_utc=fixture["timestamp_utc"],
            related_ids=fixture.get("related_ids", {}),
        )
        for fixture in DECISION_RESULT_TIMELINE_PREVIEWS
    ]


def main(argv=None):
    _ = argv
    report = build_decision_result_timeline_preview_report(build_previews())

    print("DECISIONRESULT TIMELINE PREVIEW DRY-RUN")
    print(f"Total previews: {report['total_previews']}")
    print(f"Decision summary: {format_counts(report['counts_by_decision'])}")
    print(f"Risk flag summary: {format_counts(report['counts_by_risk_flag'])}")
    print(f"Cases: {format_counts(report['counts_by_case_id'])}")
    print("")

    for preview in report["preview_payloads"]:
        decision_result = preview["details"]["decision_result"]
        print(
            f"- {preview['case_id']} | {preview['event_type']} | "
            f"{decision_result['decision']} | {decision_result['category'] or 'NO CATEGORY'}"
        )

        if decision_result["risk_flags"]:
            print(f"  Risk flags: {', '.join(decision_result['risk_flags'])}")

    if report["validation_warnings"]:
        print("")
        print("Validation warnings:")

        for warning in report["validation_warnings"]:
            print(
                f"- index {warning['index']} | "
                f"{warning['event_type'] or 'NO EVENT'} | "
                f"{', '.join(warning['warnings'])}"
            )

    print("")
    print("DRY RUN ONLY - DecisionResult timeline preview, no events written")

    return 0 if not report["validation_warnings"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
