import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.intake.case_link_candidate_report import (  # noqa: E402
    build_intake_case_link_candidate_report,
)
from tests.fixtures.intake_case_link_candidates import (  # noqa: E402
    INTAKE_CASE_LINK_CANDIDATE_SCENARIOS,
)


def format_counts(counts):
    if not counts:
        return "none"

    return ", ".join(
        f"{key or 'NO_VALUE'}: {value}"
        for key, value in sorted(counts.items())
    )


def main(argv=None):
    _ = argv
    report = build_intake_case_link_candidate_report(
        INTAKE_CASE_LINK_CANDIDATE_SCENARIOS
    )

    print("INTAKE-TO-CASE LINK CANDIDATE REPORT DRY-RUN")
    print(f"Total candidates: {report['total_candidates']}")
    print(
        "Recommended action counts: "
        f"{format_counts(report['counts_by_recommended_action'])}"
    )
    print(f"Approval required: {report['approval_required_count']}")
    print(f"Missing field summary: {format_counts(report['missing_fields_summary'])}")
    print(f"Needs-check summary: {format_counts(report['needs_check_summary'])}")
    print(
        "Mismatch reason summary: "
        f"{format_counts(report['mismatch_reason_summary'])}"
    )
    print("")

    for candidate in report["candidates"]:
        evidence = candidate["evidence"]
        intake = evidence["intake"]
        print(
            f"- {candidate['intake_id'] or 'NO_INTAKE_ID'} | "
            f"{candidate['candidate_case_id'] or 'NO_CASE'} | "
            f"{candidate['recommended_action']} | "
            f"score {candidate['match_score']} | "
            f"ref {intake.get('reference_id', '') or 'NO_REF'}"
        )

    print("")
    print("DRY RUN ONLY - intake-to-case candidate report, no cases linked or created")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
