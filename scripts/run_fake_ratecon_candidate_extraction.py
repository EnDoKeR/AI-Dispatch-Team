"""Run candidate-based RateCon extraction on fake/anonymized fixtures only."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.broker_template_candidate_extraction import (
    extract_ratecon_candidates_with_template_context,
)
from app.document_ai.broker_template_registry import BrokerTemplateRegistry
from app.document_ai.document_classification import classify_document_from_text_artifact
from app.document_ai.extraction_scope import (
    select_pages_for_rate_candidates,
    select_pages_for_ratecon_core,
    select_pages_for_requirements_candidates,
    select_pages_for_stop_candidates,
    should_skip_ratecon_extraction,
)
from app.document_ai.ratecon_field_resolution import (
    FIELD_RESOLUTION_STATUS_RESOLVED,
    resolve_ratecon_fields_with_template_context,
)
from app.document_ai.ratecon_intake_draft import build_ratecon_intake_from_resolution
from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates


DEFAULT_FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "document_ai" / "ratecon_text"
DEFAULT_HARD_LAYOUT_FIXTURE_DIR = DEFAULT_FIXTURE_DIR / "hard_layouts"
DEFAULT_TEMPLATE_DIR = REPO_ROOT / "tests" / "fixtures" / "document_ai" / "broker_templates"


def _candidate_counts(candidates):
    return dict(sorted(Counter(candidate["field_name"] for candidate in candidates).items()))


def _adjustment_counts(adjustments):
    return dict(sorted(Counter(adjustment["field_name"] for adjustment in adjustments).items()))


def _fixture_paths(fixture_dir, include_hard_layouts=False):
    paths = list(Path(fixture_dir).glob("*.txt"))
    hard_layout_dir = Path(fixture_dir) / "hard_layouts"

    if include_hard_layouts and hard_layout_dir.exists():
        paths.extend(hard_layout_dir.glob("*.txt"))

    return sorted(set(paths))


def _artifact_for_fixture(path):
    return build_text_extraction_artifact_for_candidates(
        artifact_id=f"ART-{path.stem.upper()}",
        document_id=f"DOC-{path.stem.upper()}",
        source_name=path.name,
        full_text=path.read_text(encoding="utf-8"),
        source_method="synthetic_fixture",
    )


def _selected_pages_for_candidate_extraction(classification_result, artifact):
    pages_by_number = {
        int(page.get("page_number", index) or index): page
        for index, page in enumerate(artifact.get("pages", []), start=1)
    }
    selected_numbers = []
    for page in (
        select_pages_for_ratecon_core(classification_result, artifact)
        + select_pages_for_rate_candidates(classification_result, artifact)
        + select_pages_for_stop_candidates(classification_result, artifact)
        + select_pages_for_requirements_candidates(classification_result, artifact)
    ):
        page_number = int(page.get("page_number", 0) or 0)
        if page_number and page_number not in selected_numbers:
            selected_numbers.append(page_number)

    return [
        pages_by_number[number]
        for number in selected_numbers
        if number in pages_by_number
    ]


def _scoped_artifact(artifact, selected_pages):
    return build_text_extraction_artifact_for_candidates(
        artifact_id=f"{artifact['artifact_id']}-SCOPED",
        document_id=artifact["document_id"],
        source_name=artifact["source_name"],
        pages=selected_pages,
        source_method=artifact.get("source_method", "synthetic_fixture"),
        warnings=["classification_extraction_scope_applied"],
    )


def _classification_summary(classification_result, show_page_roles=False, show_section_roles=False):
    summary = {
        "document_type": classification_result.get("document_type", ""),
        "ratecon_eligible": classification_result.get("ratecon_eligible", False),
        "supplemental_only": classification_result.get("supplemental_only", False),
        "classification_status": classification_result.get("classification_status", ""),
        "classification_warning_codes": classification_result.get("warning_codes", []),
    }

    if show_page_roles:
        summary["page_roles"] = classification_result.get("page_roles", [])

    if show_section_roles:
        roles = []
        for page in classification_result.get("page_results", []):
            for section in page.get("section_summaries", []):
                role = section.get("section_role", "")
                if role and role not in roles:
                    roles.append(role)
        summary["section_roles"] = roles

    return summary


def _safe_fixture_summary(
    path,
    registry,
    classify_document=False,
    show_page_roles=False,
    show_section_roles=False,
    respect_extraction_scope=False,
):
    artifact = _artifact_for_fixture(path)
    classification_result = None
    classification_summary = {}
    ratecon_extraction_skipped = False

    if classify_document:
        classification_result = classify_document_from_text_artifact(artifact)
        classification_summary = _classification_summary(
            classification_result,
            show_page_roles=show_page_roles,
            show_section_roles=show_section_roles,
        )
        if respect_extraction_scope and should_skip_ratecon_extraction(classification_result):
            ratecon_extraction_skipped = True

    if ratecon_extraction_skipped:
        return {
            "fixture": path.name,
            "template_match_status": "not_run",
            "selected_template_id": "",
            "template_match_confidence": 0.0,
            "template_scoring_applied": False,
            "template_context_limited": True,
            "candidate_counts_by_field": {},
            "boosted_candidate_counts_by_field": {},
            "resolved_fields": [],
            "missing_fields": [],
            "needs_check_fields": [],
            "conflict_fields": [],
            "intake_status": "CLASSIFICATION_SKIPPED_RATECON_EXTRACTION",
            "warnings": ["classification_skipped_ratecon_extraction"],
            "ratecon_extraction_skipped": True,
            "classification": classification_summary,
        }

    if classify_document and respect_extraction_scope:
        selected_pages = _selected_pages_for_candidate_extraction(classification_result, artifact)
        if selected_pages:
            artifact = _scoped_artifact(artifact, selected_pages)

    extraction_result = extract_ratecon_candidates_with_template_context(artifact, registry)
    candidate_result = extraction_result["adjusted_candidate_result"]
    template_selection = extraction_result["template_selection_result"]
    resolution_result = resolve_ratecon_fields_with_template_context(extraction_result)
    intake = build_ratecon_intake_from_resolution(resolution_result)
    resolved_fields = [
        resolution["field_name"]
        for resolution in resolution_result["resolutions"]
        if resolution["status"] == FIELD_RESOLUTION_STATUS_RESOLVED
    ]

    return {
        "fixture": path.name,
        "template_match_status": template_selection["status"],
        "selected_template_id": template_selection["selected_template_id"],
        "template_match_confidence": template_selection["selected_confidence"],
        "template_scoring_applied": extraction_result.get("template_scoring_applied", False),
        "template_context_limited": extraction_result.get("template_context_limited", True),
        "candidate_counts_by_field": _candidate_counts(candidate_result["candidates"]),
        "boosted_candidate_counts_by_field": _adjustment_counts(
            extraction_result["scoring_adjustments"]
        ),
        "resolved_fields": resolved_fields,
        "missing_fields": resolution_result["missing_fields"],
        "needs_check_fields": resolution_result["needs_check_fields"],
        "conflict_fields": resolution_result["conflict_fields"],
        "intake_status": intake["status"],
        "warnings": sorted(
            set(
                extraction_result["warnings"]
                + candidate_result["warnings"]
                + resolution_result["warnings"]
            )
        ),
        "ratecon_extraction_skipped": False,
        "classification": classification_summary,
    }


def build_fake_candidate_extraction_summary(
    input_dir=DEFAULT_FIXTURE_DIR,
    template_dir=DEFAULT_TEMPLATE_DIR,
    include_hard_layouts=False,
    classify_document=False,
    show_page_roles=False,
    show_section_roles=False,
    respect_extraction_scope=False,
):
    fixture_dir = Path(input_dir)
    registry = BrokerTemplateRegistry.from_directory(template_dir)
    summaries = [
        _safe_fixture_summary(
            path,
            registry,
            classify_document=classify_document,
            show_page_roles=show_page_roles,
            show_section_roles=show_section_roles,
            respect_extraction_scope=respect_extraction_scope,
        )
        for path in _fixture_paths(fixture_dir, include_hard_layouts=include_hard_layouts)
    ]

    return {
        "fixture_dir": str(fixture_dir),
        "template_dir": str(template_dir),
        "include_hard_layouts": bool(include_hard_layouts),
        "classify_document": bool(classify_document),
        "respect_extraction_scope": bool(respect_extraction_scope),
        "total_fixtures": len(summaries),
        "summaries": summaries,
        "dry_run_only": True,
        "raw_text_printed": False,
    }


def format_summary_lines(summary):
    lines = [
        "Fake RateCon candidate extraction dry run",
        f"Total fixtures: {summary['total_fixtures']}",
    ]

    for item in summary["summaries"]:
        lines.extend(
            [
                "",
                item["fixture"],
                f"  template_match_status: {item['template_match_status']}",
                f"  selected_template_id: {item['selected_template_id']}",
                f"  template_match_confidence: {item['template_match_confidence']}",
                f"  template_scoring_applied: {item['template_scoring_applied']}",
                f"  template_context_limited: {item['template_context_limited']}",
                f"  candidate_counts_by_field: {item['candidate_counts_by_field']}",
                f"  boosted_candidate_counts_by_field: {item['boosted_candidate_counts_by_field']}",
                f"  resolved_fields: {item['resolved_fields']}",
                f"  missing_fields: {item['missing_fields']}",
                f"  needs_check_fields: {item['needs_check_fields']}",
                f"  conflict_fields: {item['conflict_fields']}",
                f"  intake_status: {item['intake_status']}",
                f"  warnings: {item['warnings']}",
            ]
        )
        if item.get("classification"):
            lines.extend(
                [
                    f"  document_type: {item['classification'].get('document_type', '')}",
                    f"  ratecon_eligible: {item['classification'].get('ratecon_eligible', False)}",
                    f"  supplemental_only: {item['classification'].get('supplemental_only', False)}",
                    f"  classification_status: {item['classification'].get('classification_status', '')}",
                    f"  page_roles: {item['classification'].get('page_roles', [])}",
                    f"  section_roles: {item['classification'].get('section_roles', [])}",
                    f"  ratecon_extraction_skipped: {item.get('ratecon_extraction_skipped', False)}",
                ]
            )

    lines.append("")
    lines.append("DRY RUN ONLY - fake/anonymized fixtures, no raw text printed")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Run fake/anonymized RateCon candidate extraction. "
            "This fake-only CLI does not read private RateCon directories."
        ),
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_FIXTURE_DIR),
        help="Directory of fake/anonymized .txt fixtures.",
    )
    parser.add_argument(
        "--template-dir",
        default=str(DEFAULT_TEMPLATE_DIR),
        help="Directory of fake/anonymized broker template JSON fixtures.",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional path for safe summary JSON with no raw fixture text.",
    )
    parser.add_argument(
        "--include-hard-layouts",
        action="store_true",
        help=(
            "Also process fake/anonymized hard-layout fixtures under the input "
            "directory's hard_layouts folder."
        ),
    )
    parser.add_argument("--classify-document", action="store_true")
    parser.add_argument("--show-page-roles", action="store_true")
    parser.add_argument("--show-section-roles", action="store_true")
    parser.add_argument("--respect-extraction-scope", action="store_true")
    args = parser.parse_args(argv)

    summary = build_fake_candidate_extraction_summary(
        args.input_dir,
        args.template_dir,
        include_hard_layouts=args.include_hard_layouts,
        classify_document=args.classify_document,
        show_page_roles=args.show_page_roles,
        show_section_roles=args.show_section_roles,
        respect_extraction_scope=args.respect_extraction_scope,
    )

    for line in format_summary_lines(summary):
        print(line)

    if args.output_json:
        Path(args.output_json).write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
