from collections import Counter
from copy import deepcopy

from app.market_intelligence.case_event_normalizer import normalize_case_event
from app.market_intelligence.case_event_payload import json_safe


def _sorted_counts(counter):
    return {
        key: counter[key]
        for key in sorted(counter)
    }


def build_case_event_normalizer_report(events):
    source_events = deepcopy(list(events or []))
    normalized_events = []
    event_type_counts = Counter()
    event_group_counts = Counter()
    warning_counts = Counter()
    unknown_event_type_count = 0

    for event in source_events:
        wrapper = normalize_case_event(event)
        normalized_events.append(wrapper)

        normalized_payload = wrapper["normalized_payload"]
        event_type_counts[normalized_payload["event_type"]] += 1
        event_group_counts[normalized_payload["event_group"]] += 1

        for warning in wrapper["warnings"]:
            warning_counts[warning] += 1

        if "unknown_event_type" in wrapper["warnings"]:
            unknown_event_type_count += 1

    report = {
        "total_events": len(source_events),
        "normalized_count": len(normalized_events),
        "unknown_event_type_count": unknown_event_type_count,
        "warnings_count": sum(warning_counts.values()),
        "warnings_by_type": _sorted_counts(warning_counts),
        "counts_by_event_type": _sorted_counts(event_type_counts),
        "counts_by_event_group": _sorted_counts(event_group_counts),
        "normalized_events": normalized_events,
    }

    return json_safe(report)
