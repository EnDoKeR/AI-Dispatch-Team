from app.market_intelligence.case_event_payload import build_event_payload
from app.market_intelligence.case_event_types import AI_DECISION_CREATED
from app.market_intelligence.decision_engine.result import build_decision_result


def build_decision_result_timeline_preview(
    decision_result,
    case_id="",
    timestamp_utc="",
    source="decision_engine_preview",
    related_ids=None,
):
    normalized_result = build_decision_result(decision_result)

    return build_event_payload(
        event_type=AI_DECISION_CREATED,
        case_id=case_id,
        timestamp_utc=timestamp_utc,
        source=source,
        related_ids=related_ids,
        details={
            "decision_result": normalized_result,
            "preview_only": True,
            "runtime_wired": False,
        },
    )
