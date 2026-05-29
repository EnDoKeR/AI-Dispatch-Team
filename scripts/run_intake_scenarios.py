import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.market_intelligence.intake_scenario_runner import (
    build_intake_scenario_report,
    format_intake_scenario_report,
)
from tests.fixtures.synthetic_intake_records import SYNTHETIC_INTAKE_RECORDS


def main():
    report = build_intake_scenario_report(SYNTHETIC_INTAKE_RECORDS)

    print(format_intake_scenario_report(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
