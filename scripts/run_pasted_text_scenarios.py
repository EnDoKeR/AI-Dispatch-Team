import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.market_intelligence.intake.pasted_text_scenario_runner import (
    build_pasted_text_scenario_report,
    format_pasted_text_scenario_report,
)
from tests.fixtures.pasted_text_ratecon_examples import (
    PASTED_TEXT_RATECON_EXAMPLES,
)


def main():
    report = build_pasted_text_scenario_report(PASTED_TEXT_RATECON_EXAMPLES)

    print(format_pasted_text_scenario_report(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
