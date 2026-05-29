import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.market_intelligence.intake.parser_scenario_runner import (
    build_parser_scenario_report,
    format_parser_scenario_report,
)
from tests.fixtures.parser_expected_outputs import PARSER_EXPECTED_OUTPUTS


def main():
    report = build_parser_scenario_report(PARSER_EXPECTED_OUTPUTS)

    print(format_parser_scenario_report(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
