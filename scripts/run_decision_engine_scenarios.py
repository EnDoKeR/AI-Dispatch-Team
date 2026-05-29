import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.decision_engine.scenario_runner import (  # noqa: E402
    run_decision_engine_scenarios,
)
from tests.fixtures.decision_engine_scenarios import (  # noqa: E402
    DECISION_ENGINE_SCENARIOS,
)


def format_counts(counts):
    if not counts:
        return "none"

    return ", ".join(
        f"{key}: {value}"
        for key, value in sorted(counts.items())
    )


def main(argv=None):
    report = run_decision_engine_scenarios(DECISION_ENGINE_SCENARIOS)

    print("DECISIONENGINE SCENARIO DRY-RUN")
    print(f"Total scenarios: {report['total']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print(f"Decision summary: {format_counts(report['decision_summary'])}")
    print(f"Risk flag summary: {format_counts(report['risk_flag_summary'])}")
    print("")

    for result in report["scenario_results"]:
        print(
            f"- {result['scenario_id']} | {result['scenario_name']} | "
            f"{result['status']} | {result['decision']} | {result['category']}"
        )

        if result["issues"]:
            print(f"  Issues: {'; '.join(result['issues'])}")

    print("")
    print("DRY RUN ONLY - synthetic DecisionEngine scenarios only")

    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
