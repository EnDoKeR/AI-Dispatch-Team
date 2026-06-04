"""Output path construction for private RateCon measurement artifacts."""

from dataclasses import dataclass
from pathlib import Path


DEFAULT_PRIVATE_RATECON_OUTPUT_DIR = Path(".local_outputs/private_ratecon_measurement")
DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR = DEFAULT_PRIVATE_RATECON_OUTPUT_DIR

SAFE_SUMMARY_JSON = "safe_summary.json"
SAFE_SUMMARY_CSV = "safe_summary.csv"
SAFE_AGGREGATE_JSON = "safe_aggregate.json"
SAFE_AGGREGATE_MD = "safe_aggregate.md"
VALUE_REVIEW_TEMPLATE_CSV = "value_review_template.csv"

RATECON_SHADOW_AUDIT_JSONL = "ratecon_shadow_document_pipeline_audit.jsonl"
RATECON_SHADOW_AUDIT_SUMMARY_JSON = "ratecon_shadow_document_pipeline_summary.json"

REVIEW_WORKBOOK_XLSX = "ratecon_review_workbook.xlsx"
REVIEW_GOOGLE_SHEET_CSV = "ratecon_review_google_sheet.csv"
REVIEW_DOCUMENT_SUMMARY_CSV = "ratecon_review_document_summary.csv"
REVIEW_STOP_REVIEW_CSV = "ratecon_review_stop_review.csv"
REVIEW_FIELD_REVIEW_CSV = "ratecon_review_field_review.csv"
REVIEW_RATE_REVIEW_CSV = "ratecon_review_rate_review.csv"

REVIEW_V2_WORKBOOK_XLSX = "ratecon_review_v2_workbook.xlsx"
REVIEW_V2_DOCUMENT_SUMMARY_CSV = "ratecon_review_v2_document_summary.csv"
REVIEW_V2_CORE_FIELDS_CSV = "ratecon_review_v2_core_fields.csv"
REVIEW_V2_STOPS_CSV = "ratecon_review_v2_stops.csv"
REVIEW_V2_RATES_CSV = "ratecon_review_v2_rates.csv"
REVIEW_V2_LOAD_IDS_CSV = "ratecon_review_v2_load_ids.csv"
REVIEW_V2_INSTRUCTIONS_CSV = "ratecon_review_v2_instructions.csv"

STOP_REVIEW_PACKET_CSV = "stop_review_packet.csv"
STOP_REVIEW_PACKET_MD = "stop_review_packet.md"
STOP_GROUP_PROVENANCE_JSON = "stop_group_provenance.json"
STOP_GROUP_PROVENANCE_MD = "stop_group_provenance_report.md"
LAYOUT_PROVIDER_DIAGNOSTICS_MD = "layout_provider_diagnostics.md"


class PrivateRateconOutputPathError(ValueError):
    """Raised when output path settings could leak local artifacts."""


@dataclass(frozen=True)
class PrivateRateconOutputPaths:
    """Resolved private RateCon measurement output paths.

    This object only constructs paths. It does not create directories, write
    artifacts, read PDFs, or run measurement.
    """

    output_dir: Path
    safe_summary_json: Path
    safe_summary_csv: Path
    safe_aggregate_json: Path
    safe_aggregate_md: Path
    value_review_template_csv: Path
    ratecon_shadow_audit_jsonl: Path
    ratecon_shadow_summary_json: Path
    review_workbook_xlsx: Path
    review_google_sheet_csv: Path
    review_document_summary_csv: Path
    review_stop_review_csv: Path
    review_field_review_csv: Path
    review_rate_review_csv: Path
    review_v2_workbook_xlsx: Path
    review_v2_document_summary_csv: Path
    review_v2_core_fields_csv: Path
    review_v2_stops_csv: Path
    review_v2_rates_csv: Path
    review_v2_load_ids_csv: Path
    review_v2_instructions_csv: Path
    stop_review_packet_csv: Path
    stop_review_packet_md: Path
    stop_group_provenance_json: Path
    stop_group_provenance_md: Path
    layout_provider_diagnostics_md: Path


def private_ratecon_output_dir(output_dir=None):
    """Return the requested output directory or the stable local default."""
    return Path(output_dir) if output_dir else DEFAULT_PRIVATE_RATECON_OUTPUT_DIR


def default_private_ratecon_output_dir(config=None):
    """Return the configured private RateCon output directory."""
    if config is not None and getattr(config, "output_dir", None):
        return private_ratecon_output_dir(config.output_dir)
    return DEFAULT_PRIVATE_RATECON_OUTPUT_DIR


def _path(output_dir, filename):
    return private_ratecon_output_dir(output_dir) / filename


def private_measurement_summary_path(output_dir):
    return _path(output_dir, SAFE_SUMMARY_JSON)


def private_measurement_rows_path(output_dir):
    return _path(output_dir, SAFE_SUMMARY_CSV)


def private_measurement_aggregate_path(output_dir):
    return _path(output_dir, SAFE_AGGREGATE_JSON)


def private_measurement_report_path(output_dir):
    return _path(output_dir, SAFE_AGGREGATE_MD)


def value_review_template_path(output_dir):
    return _path(output_dir, VALUE_REVIEW_TEMPLATE_CSV)


def ratecon_shadow_audit_jsonl_path(output_dir):
    return _path(output_dir, RATECON_SHADOW_AUDIT_JSONL)


def ratecon_shadow_summary_json_path(output_dir):
    return _path(output_dir, RATECON_SHADOW_AUDIT_SUMMARY_JSON)


def review_workbook_path(output_dir):
    return _path(output_dir, REVIEW_WORKBOOK_XLSX)


def review_google_sheet_csv_path(output_dir):
    return _path(output_dir, REVIEW_GOOGLE_SHEET_CSV)


def review_document_summary_csv_path(output_dir):
    return _path(output_dir, REVIEW_DOCUMENT_SUMMARY_CSV)


def review_stop_review_csv_path(output_dir):
    return _path(output_dir, REVIEW_STOP_REVIEW_CSV)


def review_field_review_csv_path(output_dir):
    return _path(output_dir, REVIEW_FIELD_REVIEW_CSV)


def review_rate_review_csv_path(output_dir):
    return _path(output_dir, REVIEW_RATE_REVIEW_CSV)


def review_v2_workbook_path(output_dir):
    return _path(output_dir, REVIEW_V2_WORKBOOK_XLSX)


def review_v2_document_summary_csv_path(output_dir):
    return _path(output_dir, REVIEW_V2_DOCUMENT_SUMMARY_CSV)


def review_v2_core_fields_csv_path(output_dir):
    return _path(output_dir, REVIEW_V2_CORE_FIELDS_CSV)


def review_v2_stops_csv_path(output_dir):
    return _path(output_dir, REVIEW_V2_STOPS_CSV)


def review_v2_rates_csv_path(output_dir):
    return _path(output_dir, REVIEW_V2_RATES_CSV)


def review_v2_load_ids_csv_path(output_dir):
    return _path(output_dir, REVIEW_V2_LOAD_IDS_CSV)


def review_v2_instructions_csv_path(output_dir):
    return _path(output_dir, REVIEW_V2_INSTRUCTIONS_CSV)


def stop_review_packet_csv_path(output_dir):
    return _path(output_dir, STOP_REVIEW_PACKET_CSV)


def stop_review_packet_md_path(output_dir):
    return _path(output_dir, STOP_REVIEW_PACKET_MD)


def stop_group_provenance_json_path(output_dir):
    return _path(output_dir, STOP_GROUP_PROVENANCE_JSON)


def stop_group_provenance_md_path(output_dir):
    return _path(output_dir, STOP_GROUP_PROVENANCE_MD)


def layout_provider_diagnostics_path(output_dir):
    return _path(output_dir, LAYOUT_PROVIDER_DIAGNOSTICS_MD)


def output_dir_is_local_only(output_dir):
    """Return whether the path is under an explicit local-only output area."""
    return ".local_outputs" in private_ratecon_output_dir(output_dir).parts


def validate_private_ratecon_output_dir(output_dir, *, allow_custom_output_dir=False):
    """Validate private output directory settings without touching the filesystem."""
    if output_dir_is_local_only(output_dir):
        return
    if allow_custom_output_dir:
        return
    raise PrivateRateconOutputPathError(
        "custom output directory requires allow_custom_output_dir=True"
    )


def validate_default_scoped_output_dir(
    output_dir,
    *,
    allow_custom_output_dir=False,
    error_message="custom output directory requires allow_custom_output_dir=True",
):
    """Validate writer compatibility with the historical default output root."""
    path = private_ratecon_output_dir(output_dir)
    if output_dir and not allow_custom_output_dir:
        default_parts = DEFAULT_PRIVATE_RATECON_OUTPUT_DIR.parts
        if path.parts[: len(default_parts)] != default_parts:
            raise PrivateRateconOutputPathError(error_message)


def command_requests_local_output_write(config):
    """Return whether this command asks the CLI to write local artifacts."""
    if getattr(config, "dry_run", False):
        return False
    output_flags = [
        "write_json",
        "write_csv",
        "write_md",
        "write_value_review_template",
        "write_stop_review_packet",
        "write_stop_provenance_report",
        "write_google_sheet_export",
        "write_review_workbook",
        "write_review_csvs",
        "write_candidate_coverage",
        "write_load_identifier_audit",
        "write_load_identifier_source_line_audit",
        "write_rate_forensics",
        "write_rate_conflict_audit",
        "write_ratecon_shadow_audit",
        "layout_diagnostics",
    ]
    return any(bool(getattr(config, flag, False)) for flag in output_flags)


def build_private_ratecon_output_paths(config=None, output_dir=None):
    """Build all known private RateCon measurement output paths."""
    root = default_private_ratecon_output_dir(config)
    if output_dir is not None:
        root = private_ratecon_output_dir(output_dir)
    if config is not None and command_requests_local_output_write(config):
        validate_private_ratecon_output_dir(
            root,
            allow_custom_output_dir=getattr(config, "allow_custom_output_dir", False),
        )
    return PrivateRateconOutputPaths(
        output_dir=root,
        safe_summary_json=private_measurement_summary_path(root),
        safe_summary_csv=private_measurement_rows_path(root),
        safe_aggregate_json=private_measurement_aggregate_path(root),
        safe_aggregate_md=private_measurement_report_path(root),
        value_review_template_csv=value_review_template_path(root),
        ratecon_shadow_audit_jsonl=ratecon_shadow_audit_jsonl_path(root),
        ratecon_shadow_summary_json=ratecon_shadow_summary_json_path(root),
        review_workbook_xlsx=review_workbook_path(root),
        review_google_sheet_csv=review_google_sheet_csv_path(root),
        review_document_summary_csv=review_document_summary_csv_path(root),
        review_stop_review_csv=review_stop_review_csv_path(root),
        review_field_review_csv=review_field_review_csv_path(root),
        review_rate_review_csv=review_rate_review_csv_path(root),
        review_v2_workbook_xlsx=review_v2_workbook_path(root),
        review_v2_document_summary_csv=review_v2_document_summary_csv_path(root),
        review_v2_core_fields_csv=review_v2_core_fields_csv_path(root),
        review_v2_stops_csv=review_v2_stops_csv_path(root),
        review_v2_rates_csv=review_v2_rates_csv_path(root),
        review_v2_load_ids_csv=review_v2_load_ids_csv_path(root),
        review_v2_instructions_csv=review_v2_instructions_csv_path(root),
        stop_review_packet_csv=stop_review_packet_csv_path(root),
        stop_review_packet_md=stop_review_packet_md_path(root),
        stop_group_provenance_json=stop_group_provenance_json_path(root),
        stop_group_provenance_md=stop_group_provenance_md_path(root),
        layout_provider_diagnostics_md=layout_provider_diagnostics_path(root),
    )


def output_file_name(path):
    return Path(path).name


def output_file_labels(paths):
    return {
        key: output_file_name(value)
        for key, value in (paths or {}).items()
    }
