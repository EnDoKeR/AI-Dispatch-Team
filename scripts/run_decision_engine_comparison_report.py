import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.decision_engine.comparison_report import (  # noqa: E402
    build_decision_comparison_report,
)
from tests.fixtures.decision_engine_comparison_loads import (  # noqa: E402
    DECISION_ENGINE_COMPARISON_LOADS,
)


def format_counts(counts):
    if not counts:
        return "none"

    return ", ".join(
        f"{key}: {value}"
        for key, value in sorted(counts.items())
    )


def main(argv=None):
    _ = argv
    loads = [
        fixture["load"]
        for fixture in DECISION_ENGINE_COMPARISON_LOADS
    ]
    report = build_decision_comparison_report(loads)

    print("DECISIONENGINE COMPARISON REPORT DRY-RUN")
    print(f"Total comparisons: {report['total']}")
    print(f"Decision matches: {report['decision_match_count']}")
    print(f"Decision mismatches: {report['decision_mismatch_count']}")
    print(f"Category matches: {report['category_match_count']}")
    print(f"Category mismatches: {report['category_mismatch_count']}")
    print(f"Risk flag summary: {format_counts(report['risk_flag_summary'])}")
    print("")

    for comparison in report["comparisons"]:
        print(
            f"- {comparison['load_id'] or 'NO LOAD ID'} | "
            f"{comparison['reference_id'] or 'NO REF'} | "
            f"{comparison['original_decision']} -> {comparison['adapter_decision']} | "
            f"{comparison['original_category'] or 'NO CATEGORY'} -> "
            f"{comparison['adapter_category'] or 'NO CATEGORY'}"
        )

        if comparison["adapter_risk_flags"]:
            print(f"  Risk flags: {', '.join(comparison['adapter_risk_flags'])}")

        if comparison["warnings"]:
            print(f"  Warnings: {', '.join(comparison['warnings'])}")

    print("")
    print("DRY RUN ONLY - comparison report only, no runtime behavior changed")

    return 0 if report["decision_mismatch_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
