"""Provider boundary for normalized layout extraction artifacts."""

from importlib import import_module
from importlib import metadata
from pathlib import Path


PROVIDER_SYNTHETIC = "synthetic"
PROVIDER_PDFPLUMBER = "pdfplumber"
PROVIDER_CURRENT_TEXT_FALLBACK = "current_text_fallback"
LAYOUT_PROVIDER_NAMES = (
    PROVIDER_SYNTHETIC,
    PROVIDER_PDFPLUMBER,
    PROVIDER_CURRENT_TEXT_FALLBACK,
)

STATUS_SUCCESS = "success"
STATUS_EMPTY_TEXT = "empty_text"
STATUS_UNSUPPORTED_PDF = "unsupported_pdf"
STATUS_DEPENDENCY_MISSING = "dependency_missing"
STATUS_EXTRACTION_FAILED = "extraction_failed"
STATUS_SKIPPED_NON_DIGITAL = "skipped_non_digital"
STATUS_REVIEW_REQUIRED = "review_required"
LAYOUT_PROVIDER_STATUSES = (
    STATUS_SUCCESS,
    STATUS_EMPTY_TEXT,
    STATUS_UNSUPPORTED_PDF,
    STATUS_DEPENDENCY_MISSING,
    STATUS_EXTRACTION_FAILED,
    STATUS_SKIPPED_NON_DIGITAL,
    STATUS_REVIEW_REQUIRED,
)


class LayoutProviderError(ValueError):
    """Raised when a layout provider request is invalid."""


class LayoutProviderDependencyError(ImportError):
    """Raised when an explicitly requested provider dependency is unavailable."""


def normalize_provider_name(value):
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return text


def normalize_provider_status(value):
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return text if text in LAYOUT_PROVIDER_STATUSES else STATUS_REVIEW_REQUIRED


def normalize_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]
    return [str(item).strip() for item in values if str(item).strip()]


def get_available_layout_providers():
    return LAYOUT_PROVIDER_NAMES


def get_provider_version(provider_name):
    provider = normalize_provider_name(provider_name)
    if provider != PROVIDER_PDFPLUMBER:
        return ""

    try:
        return metadata.version("pdfplumber")
    except metadata.PackageNotFoundError:
        return ""


def require_provider_dependency(provider_name):
    provider = normalize_provider_name(provider_name)

    if provider not in LAYOUT_PROVIDER_NAMES:
        raise LayoutProviderError(f"unknown layout provider: {provider}")

    if provider != PROVIDER_PDFPLUMBER:
        return True

    try:
        import_module("pdfplumber")
    except ImportError as exc:
        raise LayoutProviderDependencyError("pdfplumber dependency is not installed") from exc

    return True


def build_layout_provider_result(
    provider_name=PROVIDER_PDFPLUMBER,
    status=STATUS_REVIEW_REQUIRED,
    artifact=None,
    page_count=0,
    warning_codes=None,
    error_code="",
    safe_message="",
    provider_version="",
    table_settings_profile="",
):
    provider = normalize_provider_name(provider_name)
    normalized_status = normalize_provider_status(status)
    normalized_artifact = artifact if isinstance(artifact, dict) else None

    return {
        "provider_name": provider,
        "status": normalized_status,
        "artifact": normalized_artifact,
        "page_count": int(page_count or 0),
        "warning_codes": normalize_list(warning_codes),
        "error_code": str(error_code or "").strip(),
        "safe_message": str(safe_message or "").strip(),
        "provider_version": str(provider_version or get_provider_version(provider)).strip(),
        "table_settings_profile": str(table_settings_profile or "").strip(),
        "raw_text_saved": False,
        "private_values_redacted": True,
    }


def extract_layout_artifact(
    path,
    provider_name=PROVIDER_PDFPLUMBER,
    document_id=None,
    table_settings_profile="default",
):
    provider = normalize_provider_name(provider_name)
    pdf_path = Path(path)

    if provider not in LAYOUT_PROVIDER_NAMES:
        return build_layout_provider_result(
            provider_name=provider,
            status=STATUS_REVIEW_REQUIRED,
            warning_codes=["unknown_layout_provider"],
            error_code="unknown_layout_provider",
            safe_message="Unknown layout provider requested.",
        )

    if not pdf_path.exists():
        return build_layout_provider_result(
            provider_name=provider,
            status=STATUS_EXTRACTION_FAILED,
            warning_codes=["layout_input_missing"],
            error_code="layout_input_missing",
            safe_message="Layout input file does not exist.",
        )

    try:
        require_provider_dependency(provider)
    except LayoutProviderDependencyError:
        return build_layout_provider_result(
            provider_name=provider,
            status=STATUS_DEPENDENCY_MISSING,
            warning_codes=["layout_provider_dependency_missing"],
            error_code="layout_provider_dependency_missing",
            safe_message="Requested layout provider dependency is not installed.",
        )

    if provider == PROVIDER_PDFPLUMBER:
        from app.document_ai.pdfplumber_layout_provider import extract_pdfplumber_layout

        return extract_pdfplumber_layout(
            pdf_path,
            document_id=document_id,
            table_settings_profile=table_settings_profile,
        )

    return build_layout_provider_result(
        provider_name=provider,
        status=STATUS_REVIEW_REQUIRED,
        warning_codes=["layout_provider_not_implemented"],
        error_code="layout_provider_not_implemented",
        safe_message="Layout provider contract is available; provider extraction is not implemented yet.",
    )
