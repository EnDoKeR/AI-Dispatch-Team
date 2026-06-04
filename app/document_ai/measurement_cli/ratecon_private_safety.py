"""Preflight safety validation for private RateCon measurement commands."""

from app.document_ai.layout_provider import (
    LayoutProviderDependencyError,
    get_available_layout_providers,
    require_provider_dependency,
)
from app.document_ai.measurement_cli.ratecon_private_output_paths import (
    PrivateRateconOutputPathError,
    command_requests_local_output_write,
    validate_private_ratecon_output_dir,
)


class PrivateRateconMeasurementSafetyError(ValueError):
    """Raised when CLI config is unsafe or internally inconsistent."""

    def __init__(self, message, *, stream="stderr", style="config"):
        super().__init__(message)
        self.stream = stream
        self.style = style


def validate_private_output_dir(output_dir, *, allow_custom_output_dir=False):
    """Validate output directory settings without creating directories."""
    try:
        validate_private_ratecon_output_dir(
            output_dir,
            allow_custom_output_dir=allow_custom_output_dir,
        )
    except PrivateRateconOutputPathError as exc:
        raise PrivateRateconMeasurementSafetyError(
            str(exc),
            style="expected",
        )


def validate_private_ratecon_measurement_config(config):
    """Validate local/private CLI safety without running measurement."""
    if not config.confirm_private_local_run:
        raise PrivateRateconMeasurementSafetyError(
            "Refusing to run: pass --confirm-private-local-run for local private measurement.",
            stream="stdout",
        )

    if command_requests_local_output_write(config):
        validate_private_output_dir(
            config.output_dir,
            allow_custom_output_dir=config.allow_custom_output_dir,
        )

    if config.enable_layout_candidates and not config.layout_provider:
        raise PrivateRateconMeasurementSafetyError(
            "--enable-layout-candidates requires --layout-provider pdfplumber"
        )

    if config.enable_layout_fusion and not config.enable_layout_candidates:
        raise PrivateRateconMeasurementSafetyError(
            "--enable-layout-fusion requires --enable-layout-candidates"
        )

    if config.allow_layout_regression_for_debug and not config.enable_layout_fusion:
        raise PrivateRateconMeasurementSafetyError(
            "--allow-layout-regression-for-debug requires --enable-layout-fusion"
        )

    if config.compare_pdfplumber_table_profiles and config.layout_provider != "pdfplumber":
        raise PrivateRateconMeasurementSafetyError(
            "--compare-pdfplumber-table-profiles requires --layout-provider pdfplumber"
        )

    if config.enable_stop_span_extractor and not config.enable_layout_candidates:
        raise PrivateRateconMeasurementSafetyError(
            "--enable-stop-span-extractor requires --enable-layout-candidates"
        )

    if (
        config.compare_stop_span_to_stop_group_pipeline
        and not config.enable_stop_span_extractor
    ):
        raise PrivateRateconMeasurementSafetyError(
            "--compare-stop-span-to-stop-group-pipeline requires --enable-stop-span-extractor"
        )

    if config.write_ratecon_shadow_audit and not config.ratecon_shadow_document_pipeline:
        raise PrivateRateconMeasurementSafetyError(
            "--write-ratecon-shadow-audit requires --ratecon-shadow-document-pipeline"
        )

    if config.include_document_ai_debug and not config.ratecon_shadow_document_pipeline:
        raise PrivateRateconMeasurementSafetyError(
            "--include-document-ai-debug requires --ratecon-shadow-document-pipeline"
        )

    if config.include_private_eval_values and not (
        config.ratecon_shadow_document_pipeline and config.write_ratecon_shadow_audit
    ):
        raise PrivateRateconMeasurementSafetyError(
            "--include-private-eval-values requires --ratecon-shadow-document-pipeline and --write-ratecon-shadow-audit"
        )

    if (
        config.strict_ratecon_shadow_document_pipeline
        and not config.ratecon_shadow_document_pipeline
    ):
        raise PrivateRateconMeasurementSafetyError(
            "--strict-ratecon-shadow-document-pipeline requires --ratecon-shadow-document-pipeline"
        )

    if config.include_private_stop_values_local_only and not config.write_stop_review_packet:
        raise PrivateRateconMeasurementSafetyError(
            "--include-private-stop-values-local-only requires --write-stop-review-packet"
        )

    if config.include_private_review_values_local_only and not (
        config.write_review_workbook or config.write_review_csvs
    ):
        raise PrivateRateconMeasurementSafetyError(
            "--include-private-review-values-local-only requires --write-review-workbook or --write-review-csvs"
        )

    if config.sync_review_google_sheet and not config.confirm_google_review_sync:
        raise PrivateRateconMeasurementSafetyError(
            "--sync-review-google-sheet requires --confirm-google-review-sync"
        )

    if config.sync_review_google_sheet and not (
        config.write_review_workbook or config.write_review_csvs
    ):
        raise PrivateRateconMeasurementSafetyError(
            "--sync-review-google-sheet requires --write-review-workbook or --write-review-csvs"
        )

    if (
        config.include_private_review_values_google_test_only
        and not config.sync_review_google_sheet
    ):
        raise PrivateRateconMeasurementSafetyError(
            "--include-private-review-values-google-test-only requires --sync-review-google-sheet"
        )

    if (
        config.private_template_dir
        and not config.allow_private_template_overlay
    ):
        raise PrivateRateconMeasurementSafetyError(
            "private template overlay requires --allow-private-template-overlay",
            style="expected",
        )

    if config.layout_provider and config.layout_provider not in get_available_layout_providers():
        raise PrivateRateconMeasurementSafetyError(
            f"unknown layout provider {config.layout_provider!r}"
        )

    if config.layout_provider == "pdfplumber":
        try:
            require_provider_dependency(config.layout_provider)
        except LayoutProviderDependencyError:
            raise PrivateRateconMeasurementSafetyError(
                "pdfplumber is not installed. Install optional dependency with: pip install pdfplumber"
            )
