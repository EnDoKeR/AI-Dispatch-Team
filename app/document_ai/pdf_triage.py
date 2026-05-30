"""Safe local PDF triage without OCR, Vision, or raw text output."""

from contextlib import redirect_stderr
from importlib import import_module
from io import StringIO
from pathlib import Path

from app.document_ai.pdf_triage_contract import (
    DIGITAL_TEXT,
    MANUAL_REVIEW,
    OCR_NEEDED,
    UNSUPPORTED,
    build_pdf_page_profile,
    build_pdf_triage_result,
)


LOW_TEXT_CHARS_PER_PAGE = 40
TRIAGE_PROVIDER = "pypdf"
TRIAGE_VERSION = "pypdf_triage_v1"


def _load_pypdf_reader():
    module = import_module("pypdf")
    return module.PdfReader


def _safe_pages(reader):
    pages = getattr(reader, "pages", [])

    if pages is None:
        return []

    return list(pages)


def _extract_page_text(page, page_number, warnings):
    try:
        with redirect_stderr(StringIO()):
            return page.extract_text() or ""
    except Exception as exc:  # pragma: no cover - extractor-specific failure
        warnings.append(f"page_{page_number}_text_extract_failed:{exc.__class__.__name__}")
        return ""


def _word_count(text):
    return len(str(text or "").split())


def _recommended_route(
    page_count,
    char_count,
    chars_per_page,
    encrypted=False,
    broken=False,
    mixed_pdf=False,
):
    if broken:
        return UNSUPPORTED

    if encrypted:
        return MANUAL_REVIEW

    if page_count <= 0:
        return UNSUPPORTED

    if char_count <= 0:
        return OCR_NEEDED

    if mixed_pdf:
        return OCR_NEEDED

    if chars_per_page < LOW_TEXT_CHARS_PER_PAGE:
        return OCR_NEEDED

    return DIGITAL_TEXT


def triage_pdf(path, document_id=None):
    """Return safe PDF triage metadata for a local PDF path."""
    file_path = Path(path or "")
    warnings = []

    if not file_path.exists():
        return build_pdf_triage_result(
            document_id=document_id or "",
            file_name="",
            broken=True,
            recommended_route=UNSUPPORTED,
            warnings=["file_not_found"],
        )

    if file_path.is_dir():
        return build_pdf_triage_result(
            document_id=document_id or "",
            file_name=file_path.name,
            broken=True,
            recommended_route=UNSUPPORTED,
            warnings=["path_is_directory"],
        )

    if file_path.suffix.lower() != ".pdf":
        return build_pdf_triage_result(
            document_id=document_id or "",
            file_name=file_path.name,
            broken=True,
            recommended_route=UNSUPPORTED,
            warnings=["unsupported_file_type"],
        )

    try:
        pdf_reader = _load_pypdf_reader()
    except Exception as exc:
        return build_pdf_triage_result(
            document_id=document_id or "",
            file_name=file_path.name,
            recommended_route=MANUAL_REVIEW,
            warnings=[f"pypdf_unavailable:{exc.__class__.__name__}"],
        )

    try:
        with redirect_stderr(StringIO()):
            reader = pdf_reader(str(file_path))
    except Exception as exc:
        return build_pdf_triage_result(
            document_id=document_id or "",
            file_name=file_path.name,
            broken=True,
            recommended_route=UNSUPPORTED,
            warnings=[f"pdf_read_failed:{exc.__class__.__name__}"],
        )

    encrypted = bool(getattr(reader, "is_encrypted", False))

    if encrypted:
        return build_pdf_triage_result(
            document_id=document_id or "",
            file_name=file_path.name,
            encrypted=True,
            recommended_route=MANUAL_REVIEW,
            warnings=["encrypted_pdf"],
        )

    try:
        pages = _safe_pages(reader)
    except Exception as exc:
        return build_pdf_triage_result(
            document_id=document_id or "",
            file_name=file_path.name,
            broken=True,
            recommended_route=UNSUPPORTED,
            warnings=[f"page_read_failed:{exc.__class__.__name__}"],
        )

    page_profiles = []

    for index, page in enumerate(pages, start=1):
        page_text = _extract_page_text(page, index, warnings)
        stripped_text = str(page_text or "").strip()
        char_count = len(stripped_text)
        page_profiles.append(
            build_pdf_page_profile(
                page_number=index,
                char_count=char_count,
                word_count=_word_count(stripped_text),
                has_text=char_count > 0,
                image_like=char_count == 0,
            )
        )

    page_count = len(page_profiles)
    char_count = sum(profile["char_count"] for profile in page_profiles)
    chars_per_page = round(char_count / page_count, 2) if page_count else 0.0
    has_text_layer = char_count > 0
    likely_image_based = page_count > 0 and char_count == 0
    mixed_pdf = (
        page_count > 0
        and any(profile["has_text"] for profile in page_profiles)
        and any(not profile["has_text"] for profile in page_profiles)
    )
    recommended_route = _recommended_route(
        page_count=page_count,
        char_count=char_count,
        chars_per_page=chars_per_page,
        mixed_pdf=mixed_pdf,
    )

    if page_count == 0:
        warnings.append("no_pages")

    if likely_image_based:
        warnings.append("no_extractable_text")

    if mixed_pdf:
        warnings.append("mixed_text_layer")

    if page_count > 0 and char_count > 0 and chars_per_page < LOW_TEXT_CHARS_PER_PAGE:
        warnings.append("low_text_density")

    return build_pdf_triage_result(
        document_id=document_id or "",
        file_name=file_path.name,
        page_count=page_count,
        char_count=char_count,
        chars_per_page=chars_per_page,
        has_text_layer=has_text_layer,
        likely_image_based=likely_image_based,
        mixed_pdf=mixed_pdf,
        recommended_route=recommended_route,
        page_profiles=page_profiles,
        warnings=warnings,
    )
