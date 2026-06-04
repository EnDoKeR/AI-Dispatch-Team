"""Write a local-only sanitized selected-rate regression snapshot."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from tests.helpers.ratecon_selected_rate_regression import (  # noqa: E402
    assert_no_private_fixture_values,
    load_selected_rate_cases,
    run_selected_rate_case,
)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run sanitized RateCon selected-rate regression snapshot.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory under .local_outputs for generated snapshot files.",
    )
    parser.add_argument(
        "--confirm-local-audit-run",
        action="store_true",
        help="Required confirmation for this local-only sanitized audit run.",
    )
    return parser.parse_args(argv)


def _require_safe_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    if ".local_outputs" not in resolved.parts:
        raise ValueError("output-dir must be inside .local_outputs")
    return resolved


def _case_snapshot(case: dict) -> dict:
    actual = run_selected_rate_case(case)
    expected = dict(case["expected"])
    expected["case_id"] = case["id"]
    expected["known_debt"] = bool(case.get("known_debt"))
    return {
        "case_id": case["id"],
        "description": case.get("description", ""),
        "known_debt": bool(case.get("known_debt")),
        "debt_note": case.get("debt_note", ""),
        "candidate_count": len(case.get("candidates") or []),
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_markdown(path: Path, summary: dict, case_rows: list[dict]) -> None:
    lines = [
        "# RateCon Selected-Rate Regression Snapshot",
        "",
        "This local-only snapshot uses sanitized fixture candidates only.",
        "",
        f"- case_count: {summary['case_count']}",
        f"- passed_count: {summary['passed_count']}",
        f"- known_debt_count: {summary['known_debt_count']}",
        f"- private_values_used: {summary['private_values_used']}",
        f"- pdf_processing_attempted: {summary['pdf_processing_attempted']}",
        f"- ocr_attempted: {summary['ocr_attempted']}",
        f"- google_called: {summary['google_called']}",
        f"- model_or_cloud_called: {summary['model_or_cloud_called']}",
        "",
        "## Cases",
        "",
        "| case | passed | known_debt | selected_value | selected_context | needs_review |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in case_rows:
        actual = row["actual"]
        lines.append(
            "| {case_id} | {passed} | {known_debt} | {selected_value} | "
            "{selected_money_context} | {needs_review} |".format(
                case_id=row["case_id"],
                passed=str(row["passed"]).lower(),
                known_debt=str(row["known_debt"]).lower(),
                selected_value=actual["selected_value"],
                selected_money_context=actual["selected_money_context"],
                needs_review=str(actual["needs_review"]).lower(),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(path: Path, case_rows: list[dict]) -> None:
    fieldnames = [
        "case_id",
        "passed",
        "known_debt",
        "candidate_count",
        "selected_value",
        "selected_label",
        "selected_source",
        "selected_confidence",
        "selected_score",
        "selected_money_context",
        "selected_rate_safety",
        "needs_review",
        "review_reasons",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in case_rows:
            actual = row["actual"]
            writer.writerow(
                {
                    "case_id": row["case_id"],
                    "passed": row["passed"],
                    "known_debt": row["known_debt"],
                    "candidate_count": row["candidate_count"],
                    "selected_value": actual["selected_value"],
                    "selected_label": actual["selected_label"],
                    "selected_source": actual["selected_source"],
                    "selected_confidence": actual["selected_confidence"],
                    "selected_score": actual["selected_score"],
                    "selected_money_context": actual["selected_money_context"],
                    "selected_rate_safety": actual["selected_rate_safety"],
                    "needs_review": actual["needs_review"],
                    "review_reasons": ";".join(actual["review_reasons"]),
                }
            )


def main(argv=None) -> int:
    args = _parse_args(argv)
    if not args.confirm_local_audit_run:
        print("--confirm-local-audit-run is required", file=sys.stderr)
        return 2

    try:
        output_dir = _require_safe_output_dir(Path(args.output_dir))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    cases = load_selected_rate_cases()
    assert_no_private_fixture_values(cases)
    case_rows = [_case_snapshot(case) for case in cases]
    passed_count = sum(1 for row in case_rows if row["passed"])
    known_debt_count = sum(1 for row in case_rows if row["known_debt"])
    status_counts = Counter(row["actual"]["selected_rate_safety"] for row in case_rows)
    value_counts = Counter(row["actual"]["selected_value"] for row in case_rows)

    summary = {
        "case_count": len(case_rows),
        "passed_count": passed_count,
        "known_debt_count": known_debt_count,
        "all_passed": passed_count == len(case_rows),
        "selected_rate_safety_distribution": dict(sorted(status_counts.items())),
        "selected_value_distribution": dict(sorted(value_counts.items())),
        "private_values_used": False,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
    }

    payload = {
        "summary": summary,
        "cases": case_rows,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "selected_rate_regression_snapshot.json", payload)
    _write_markdown(output_dir / "selected_rate_regression_snapshot.md", summary, case_rows)
    _write_csv(output_dir / "selected_rate_regression_cases.csv", case_rows)

    print("RateCon selected-rate regression snapshot")
    print(f"case_count: {summary['case_count']}")
    print(f"passed_count: {summary['passed_count']}")
    print(f"known_debt_count: {summary['known_debt_count']}")
    print(f"output_dir: {output_dir}")
    print("private_values_used: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("google_called: False")
    print("model_or_cloud_called: False")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
