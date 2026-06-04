"""Review workbook orchestration for private RateCon measurement CLI."""

from dataclasses import dataclass

from app.document_ai.measurement_cli.ratecon_private_output_paths import (
    output_file_labels,
)
from app.document_ai.ratecon_review_workbook import write_ratecon_review_artifacts


@dataclass(frozen=True)
class PrivateRateconReviewWorkbookResult:
    """Console-safe result for local review workbook artifact generation."""

    message_label: str
    payload: dict
    review: dict

    @property
    def review_rows_by_sheet(self):
        return self.review.get("rows_by_sheet", {})


def build_private_ratecon_review_workbook_plan(config, output_paths=None):
    """Return enabled review workbook tasks without running measurement."""
    if getattr(config, "dry_run", False):
        return []
    if getattr(config, "write_review_workbook", False) or getattr(
        config,
        "write_review_csvs",
        False,
    ):
        return ["review_workbook"]
    return []


def private_ratecon_review_workbook_labels(review):
    """Return the historical console-safe review workbook label payload."""
    summary = review.get("summary", {})
    return {
        "files": output_file_labels(review.get("paths", {})),
        "document_rows": summary.get("document_rows", 0),
        "stop_review_rows": summary.get("stop_review_rows", 0),
        "field_review_rows": summary.get("field_review_rows", 0),
        "rate_review_rows": summary.get("rate_review_rows", 0),
        "readiness_level_counts": summary.get("readiness_level_counts", {}),
        "integrity_issue_counts": summary.get("integrity_issue_counts", {}),
        "include_private_values_local_only": review.get(
            "include_private_values_local_only",
            False,
        ),
        "xlsx_written": review.get("xlsx_written", False),
        "csvs_written": review.get("csvs_written", False),
    }


def write_private_ratecon_review_workbook_if_enabled(
    report,
    config,
    output_paths,
    *,
    writer=write_ratecon_review_artifacts,
):
    """Write local review workbook artifacts when requested by CLI flags."""
    if "review_workbook" not in build_private_ratecon_review_workbook_plan(
        config,
        output_paths,
    ):
        return None

    review = writer(
        report["rows"],
        output_dir=output_paths.output_dir,
        local_document_names_by_alias=report.get("local_document_names_by_alias", {}),
        include_private_values=getattr(
            config,
            "include_private_review_values_local_only",
            False,
        ),
        write_workbook=getattr(config, "write_review_workbook", False),
        write_csvs=getattr(config, "write_review_csvs", False),
        allow_custom_output_dir=getattr(config, "allow_custom_output_dir", False),
    )
    return PrivateRateconReviewWorkbookResult(
        message_label="review_workbook_export_written",
        payload=private_ratecon_review_workbook_labels(review),
        review=review,
    )
