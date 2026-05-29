"""Local-only PDF text extraction helper for private dry-runs."""

from importlib import import_module
from pathlib import Path


TEXT_EXTRACTED = "TEXT_EXTRACTED"
EMPTY_TEXT = "EMPTY_TEXT"
EXTRACTION_FAILED = "EXTRACTION_FAILED"
UNSUPPORTED = "UNSUPPORTED"


def _base_result():
    return {
        "text": "",
        "extractor_name": "",
        "page_count": 0,
        "char_count": 0,
        "extraction_status": EXTRACTION_FAILED,
        "warnings": [],
        "private_text_saved": False,
    }


def _load_pypdf_reader():
    module = import_module("pypdf")
    return module.PdfReader


def _safe_pages(reader):
    pages = getattr(reader, "pages", [])
    if pages is None:
        return []
    return list(pages)


def _extract_page_text(page, page_index, warnings):
    try:
        return page.extract_text() or ""
    except Exception as exc:  # pragma: no cover - exception type depends on extractor
        warnings.append(f"page_{page_index}_extraction_failed:{exc.__class__.__name__}")
        return ""


def extract_pdf_text_local(file_path):
    """Extract text from one local PDF path without saving the extracted text."""
    result = _base_result()
    path = Path(file_path or "")

    if not path.exists():
        result["warnings"].append("file_not_found")
        return result

    if path.is_dir():
        result["extraction_status"] = UNSUPPORTED
        result["warnings"].append("path_is_directory")
        return result

    if path.suffix.lower() != ".pdf":
        result["extraction_status"] = UNSUPPORTED
        result["warnings"].append("unsupported_file_type")
        return result

    try:
        pdf_reader = _load_pypdf_reader()
    except Exception as exc:
        result["extraction_status"] = UNSUPPORTED
        result["warnings"].append(f"pypdf_unavailable:{exc.__class__.__name__}")
        return result

    result["extractor_name"] = "pypdf"

    try:
        reader = pdf_reader(str(path))
        pages = _safe_pages(reader)
        result["page_count"] = len(pages)
        page_text = [
            _extract_page_text(page, index + 1, result["warnings"])
            for index, page in enumerate(pages)
        ]
        text = "\n".join(part.strip() for part in page_text if str(part or "").strip())
    except Exception as exc:
        result["extraction_status"] = EXTRACTION_FAILED
        result["warnings"].append(f"extraction_failed:{exc.__class__.__name__}")
        return result

    result["text"] = text
    result["char_count"] = len(text)

    if text:
        result["extraction_status"] = TEXT_EXTRACTED
    else:
        result["extraction_status"] = EMPTY_TEXT
        result["warnings"].append("no_extractable_text")

    return result
