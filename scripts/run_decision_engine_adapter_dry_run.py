import json
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.decision_engine.marketload_adapter import (  # noqa: E402
    decision_result_from_market_load,
)


class SampleLoad(SimpleNamespace):
    def review_category(self):
        return "RATE CHECK"


def build_sample_load():
    return SampleLoad(
        driver_match_status="REVIEW_ONCE",
        driver_fit_status="REVIEW_ONCE",
        driver_match_notes=[
            "Rate is missing / posted as $0; dispatcher should check rate with broker."
        ],
        match_reasons=[],
        review_reasons=[
            "Rate is missing / posted as $0; dispatcher should check rate with broker."
        ],
        block_reasons=[],
        rate=0,
        broker_mc="000000",
        reference_id="SAMPLE-ADAPTER-1",
        load_id="LOAD-SAMPLE-ADAPTER-1",
    )


def main(argv=None):
    _ = argv
    load = build_sample_load()
    result = decision_result_from_market_load(load)

    print("DECISIONENGINE ADAPTER DRY-RUN")
    print(f"Input decision: {load.driver_match_status}")
    print(f"Input category/status: {load.driver_fit_status}")
    print(f"DecisionResult decision: {result['decision']}")
    print(f"DecisionResult category: {result['category']}")
    print(f"Risk flags: {', '.join(result['risk_flags']) or 'none'}")
    print(f"Review reasons: {'; '.join(result['review_reasons']) or 'none'}")
    print(f"Block reasons: {'; '.join(result['block_reasons']) or 'none'}")
    print("")
    print("DecisionResult JSON:")
    print(json.dumps(result, indent=2, sort_keys=True))
    print("")
    print("DRY RUN ONLY - adapter preview only, no runtime behavior changed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
