"""Read-only reporting for intake-to-case link candidates."""

from collections import Counter
from copy import deepcopy

from app.market_intelligence.intake.case_link_candidate import (
    CREATE_CASE_REVIEW,
    KEEP_UNLINKED,
    LINK_EXISTING,
    NEEDS_REVIEW,
    build_intake_case_link_candidate,
)


RECOMMENDED_ACTIONS = [
    LINK_EXISTING,
    CREATE_CASE_REVIEW,
    KEEP_UNLINKED,
    NEEDS_REVIEW,
]


def _scenario_intake_record(record):
    if isinstance(record, dict) and "intake_record" in record:
        return record.get("intake_record")

    return record


def _scenario_case_record(record):
    if isinstance(record, dict) and "case_record" in record:
        return record.get("case_record")

    return None


def _count_items(values):
    counter = Counter()

    for value in values:
        if value:
            counter[str(value)] += 1

    return dict(sorted(counter.items()))


def _field_summary(candidates, field_name):
    values = []

    for candidate in candidates:
        values.extend(candidate.get(field_name, []))

    return _count_items(values)


def _action_counts(candidates):
    counts = {action: 0 for action in RECOMMENDED_ACTIONS}

    for candidate in candidates:
        action = candidate.get("recommended_action", "")

        if action not in counts:
            counts[action] = 0

        counts[action] += 1

    return counts


def build_intake_case_link_candidate_report(records=None):
    candidates = [
        build_intake_case_link_candidate(
            _scenario_intake_record(record),
            _scenario_case_record(record),
        )
        for record in records or []
    ]

    return {
        "total_candidates": len(candidates),
        "counts_by_recommended_action": _action_counts(candidates),
        "approval_required_count": sum(
            1 for candidate in candidates if candidate.get("approval_required")
        ),
        "missing_fields_summary": _field_summary(candidates, "missing_fields"),
        "needs_check_summary": _field_summary(candidates, "needs_check_fields"),
        "mismatch_reason_summary": _field_summary(candidates, "mismatch_reasons"),
        "candidates": deepcopy(candidates),
    }
