"""Document extraction artifact with page structure and plain-text fallback."""

from contextlib import redirect_stderr
from importlib import import_module
from io import StringIO
from pathlib import Path

from app.document_ai.layout_provider_contract import (
    PROVIDER_AUTO,
    PROVIDER_NATIVE_TEXT,
    PROVIDER_PDFPLUMBER,
    STATUS_FAILED,
    STATUS_NATIVE_TEXT,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
    STATUS_UNAVAILABLE,
    build_layout_provider_summary,
    empty_layout_provider_summary,
    normalize_shadow_layout_provider,
)
from app.document_ai.ocr_provider_contract import (
    OCR_PROVIDER_NONE,
    OCR_PROVIDER_TESSERACT,
    OCR_STATUS_PARTIAL,
    OCR_STATUS_SUCCESS,
    empty_ocr_provider_result,
    normalize_ocr_dpi,
    normalize_ocr_page_mode,
    normalize_ocr_provider,
    safe_ocr_provider_summary,
)
from app.document_ai.pdf_triage import triage_document


DOCUMENT_EXTRACTION_ARTIFACT_VERSION = "document_extraction_artifact_v1"

SOURCE_NATIVE = "native"
SOURCE_OCR = "ocr"
SOURCE_HYBRID = "hybrid"
SOURCE_UNKNOWN = "unknown"


def _text(value):
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n")


def _safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _bbox(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return [
            _safe_float(value.get("x0")),
            _safe_float(value.get("y0")),
            _safe_float(value.get("x1")),
            _safe_float(value.get("y1")),
        ]
    if isinstance(value, (list, tuple)) and len(value) >= 4:
        return [_safe_float(item) for item in value[:4]]
    return None


def build_document_line(
    text="",
    bbox=None,
    source=SOURCE_UNKNOWN,
    page=None,
    line_index=None,
    word_count=0,
    line_id="",
):
    return {
        "text": _text(text).strip(),
        "bbox": _bbox(bbox),
        "source": str(source or SOURCE_UNKNOWN).strip() or SOURCE_UNKNOWN,
        "page": _safe_int(page),
        "line_index": _safe_int(line_index),
        "word_count": _safe_int(word_count),
        "line_id": str(line_id or "").strip(),
    }


def build_document_word(
    text="",
    bbox=None,
    source=SOURCE_UNKNOWN,
    page=None,
    line_index=None,
    word_id="",
    line_id="",
):
    return {
        "text": _text(text).strip(),
        "bbox": _bbox(bbox),
        "source": str(source or SOURCE_UNKNOWN).strip() or SOURCE_UNKNOWN,
        "page": _safe_int(page),
        "line_index": _safe_int(line_index),
        "word_id": str(word_id or "").strip(),
        "line_id": str(line_id or "").strip(),
    }


def _layout_bbox(value):
    if not isinstance(value, dict):
        return _bbox(value)
    return _bbox(
        [
            value.get("x0", 0),
            value.get("y0", 0),
            value.get("x1", 0),
            value.get("y1", 0),
        ]
    )


def _layout_table_to_document_table(table, source=SOURCE_UNKNOWN):
    if not isinstance(table, dict):
        return {}
    rows = {}
    for row in table.get("rows", []) or []:
        if not isinstance(row, dict):
            continue
        row_index = _safe_int(row.get("row_index"))
        for cell in row.get("cells", []) or []:
            if not isinstance(cell, dict):
                continue
            rows.setdefault(row_index, []).append(
                {
                    "text": _text(cell.get("text", cell.get("text_redacted"))),
                    "bbox": _layout_bbox(cell.get("bbox")),
                    "column_index": _safe_int(
                        cell.get("column_index", cell.get("col_index"))
                    ),
                }
            )
    for cell in table.get("cells", []) or []:
        if not isinstance(cell, dict):
            continue
        row_index = _safe_int(cell.get("row_index"))
        rows.setdefault(row_index, []).append(
            {
                "text": _text(cell.get("text_redacted") or cell.get("text")),
                "bbox": _layout_bbox(cell.get("bbox")),
                "column_index": _safe_int(cell.get("col_index", cell.get("column_index"))),
            }
        )
    normalized_rows = [
        {
            "row_index": row_index,
            "cells": sorted(row_cells, key=lambda item: item.get("column_index", 0)),
        }
        for row_index, row_cells in sorted(rows.items())
    ]
    column_count = 0
    for row in normalized_rows:
        column_count = max(column_count, len(row.get("cells", [])))
    return {
        "page": _safe_int(table.get("page_number", table.get("page"))),
        "bbox": _layout_bbox(table.get("bbox")),
        "rows": normalized_rows,
        "column_count": column_count,
        "row_count": len(normalized_rows),
        "source": str(table.get("source") or source or SOURCE_UNKNOWN).strip(),
        "confidence": table.get("confidence", ""),
        "diagnostics": {
            "table_id": str(table.get("table_id", "")).strip(),
            "warning_codes": list(table.get("warning_codes", []) or []),
        },
    }


def build_document_page_artifact(
    page_number=0,
    width=0,
    height=0,
    text="",
    lines=None,
    words=None,
    tables=None,
    source=SOURCE_UNKNOWN,
):
    page_text = _text(text)
    page_lines = [
        build_document_line(
            line,
            source=source,
            page=page_number,
            line_index=index,
            word_count=len(str(line or "").split()),
        )
        for index, line in enumerate(page_text.splitlines())
        if line.strip()
    ]
    if lines is not None:
        page_lines = [
            build_document_line(
                line.get("text", line.get("text_redacted", "")) if isinstance(line, dict) else line,
                bbox=_layout_bbox(line.get("bbox")) if isinstance(line, dict) else None,
                source=line.get("source", source) if isinstance(line, dict) else source,
                page=line.get("page", line.get("page_number", page_number)) if isinstance(line, dict) else page_number,
                line_index=line.get("line_index", line.get("reading_order_index")) if isinstance(line, dict) else 0,
                word_count=line.get("word_count", len(str(line.get("text", line.get("text_redacted", ""))).split())) if isinstance(line, dict) else len(str(line).split()),
                line_id=line.get("line_id", "") if isinstance(line, dict) else "",
            )
            for line in lines
            if (
                (isinstance(line, dict) and _text(line.get("text", line.get("text_redacted", ""))).strip())
                or (not isinstance(line, dict) and _text(line).strip())
            )
        ]
    return {
        "page_number": _safe_int(page_number),
        "width": _safe_float(width),
        "height": _safe_float(height),
        "text": page_text,
        "lines": page_lines,
        "words": [
            build_document_word(
                word.get("text", "") if isinstance(word, dict) else word,
                bbox=_layout_bbox(word.get("bbox")) if isinstance(word, dict) else None,
                source=word.get("source", source) if isinstance(word, dict) else source,
                page=word.get("page", page_number) if isinstance(word, dict) else page_number,
                line_index=word.get("line_index") if isinstance(word, dict) else None,
                word_id=word.get("word_id", "") if isinstance(word, dict) else "",
                line_id=word.get("line_id", "") if isinstance(word, dict) else "",
            )
            for word in words or []
            if (
                (isinstance(word, dict) and _text(word.get("text", "")).strip())
                or (not isinstance(word, dict) and _text(word).strip())
            )
        ],
        "tables": [
            _layout_table_to_document_table(table, source=source)
            for table in tables or []
            if isinstance(table, dict)
        ],
    }


def build_document_extraction_artifact(
    document_id="",
    pages=None,
    full_text="",
    source=SOURCE_UNKNOWN,
    triage=None,
    layout_provider_summary=None,
    layout_artifact=None,
    ocr_provider_result=None,
):
    normalized_pages = [
        build_document_page_artifact(
            page_number=page.get("page_number", index),
            width=page.get("width", 0),
            height=page.get("height", 0),
            text=page.get("text", ""),
            lines=page.get("lines"),
            words=page.get("words"),
            tables=page.get("tables"),
            source=page.get("source", source),
        )
        for index, page in enumerate(pages or [], start=1)
        if isinstance(page, dict)
    ]
    computed_full_text = _text(full_text)
    if not computed_full_text:
        computed_full_text = "\n".join(page["text"] for page in normalized_pages if page["text"])
    return {
        "document_id": str(document_id or "").strip(),
        "pages": normalized_pages,
        "full_text": computed_full_text,
        "source": str(source or SOURCE_UNKNOWN).strip() or SOURCE_UNKNOWN,
        "triage": triage if isinstance(triage, dict) else {},
        "layout_provider_summary": (
            layout_provider_summary
            if isinstance(layout_provider_summary, dict)
            else empty_layout_provider_summary()
        ),
        "layout_artifact": layout_artifact if isinstance(layout_artifact, dict) else {},
        "ocr_provider_result": (
            ocr_provider_result
            if isinstance(ocr_provider_result, dict)
            else empty_ocr_provider_result()
        ),
        "artifact_version": DOCUMENT_EXTRACTION_ARTIFACT_VERSION,
        "raw_text_included": bool(computed_full_text),
        "line_count": sum(len(page["lines"]) for page in normalized_pages),
        "word_count": sum(len(page["words"]) for page in normalized_pages),
        "table_count": sum(len(page["tables"]) for page in normalized_pages),
    }


def _layout_artifact_pages(layout_artifact):
    pages = []
    for page in (layout_artifact or {}).get("pages", []) or []:
        if not isinstance(page, dict):
            continue
        pages.append(
            {
                "page_number": page.get("page_number", 0),
                "width": page.get("width", 0),
                "height": page.get("height", 0),
                "text": "\n".join(
                    _text(line.get("text_redacted") or line.get("text"))
                    for line in page.get("lines", []) or []
                    if isinstance(line, dict) and _text(line.get("text_redacted") or line.get("text"))
                ),
                "lines": page.get("lines", []),
                "words": page.get("words", []),
                "tables": page.get("tables", []),
                "source": (layout_artifact or {}).get("provider", SOURCE_UNKNOWN),
            }
        )
    return pages


def _merge_native_and_layout_pages(native_pages, layout_pages):
    by_page = {int(page.get("page_number") or index): dict(page) for index, page in enumerate(native_pages or [], start=1)}
    for layout_page in layout_pages or []:
        page_number = int(layout_page.get("page_number") or 0)
        if page_number not in by_page:
            by_page[page_number] = dict(layout_page)
            continue
        merged = dict(by_page[page_number])
        for key in ["width", "height"]:
            if layout_page.get(key):
                merged[key] = layout_page.get(key)
        if layout_page.get("lines"):
            merged["lines"] = layout_page.get("lines")
        if layout_page.get("words"):
            merged["words"] = layout_page.get("words")
        if layout_page.get("tables"):
            merged["tables"] = layout_page.get("tables")
        by_page[page_number] = merged
    return [by_page[key] for key in sorted(by_page)]


def _ocr_result_pages(ocr_result):
    pages = []
    for page in (ocr_result or {}).get("pages", []) or []:
        if not isinstance(page, dict) or not _text(page.get("text")).strip():
            continue
        pages.append(
            build_document_page_artifact(
                page_number=page.get("page_number", 0),
                text=page.get("text", ""),
                source=SOURCE_OCR,
            )
        )
    return pages


def _ocr_document_classification_diagnostic(ocr_result):
    pages = (ocr_result or {}).get("pages", []) or []
    text = "\n".join(
        _text(page.get("text"))
        for page in pages
        if isinstance(page, dict) and _text(page.get("text")).strip()
    ).lower()
    has_ratecon_signal = any(
        token in text
        for token in [
            "rate confirmation",
            "load confirmation",
            "carrier load tender",
            "carrier rate",
            "tender",
        ]
    )
    has_bol_pod_signal = any(
        token in text
        for token in [
            "bill of lading",
            "proof of delivery",
            "delivery receipt",
            " bol ",
            "pod",
        ]
    )
    if has_bol_pod_signal and not has_ratecon_signal:
        document_type = "non_rate_confirmation"
        skip_reason = "bol_pod_or_delivery_document"
    elif has_ratecon_signal:
        document_type = "rate_confirmation"
        skip_reason = ""
    elif text:
        document_type = "unknown"
        skip_reason = ""
    else:
        document_type = "unknown"
        skip_reason = "ocr_text_unavailable"
    return {
        "document_type": document_type,
        "skip_reason": skip_reason,
        "rate_confirmation_signal": has_ratecon_signal,
        "bol_pod_signal": has_bol_pod_signal,
        "ocr_text_available": bool(text),
        "raw_text_included": False,
    }


def _merge_ocr_pages(base_pages, ocr_pages):
    by_page = {
        int(page.get("page_number") or index): dict(page)
        for index, page in enumerate(base_pages or [], start=1)
    }
    for ocr_page in ocr_pages or []:
        page_number = int(ocr_page.get("page_number") or 0)
        if page_number not in by_page:
            merged = dict(ocr_page)
            merged["ocr_text_present"] = True
            by_page[page_number] = merged
            continue
        merged = dict(by_page[page_number])
        native_text = _text(merged.get("text"))
        ocr_text = _text(ocr_page.get("text"))
        if native_text and ocr_text and ocr_text not in native_text:
            merged["native_text"] = native_text
            merged["text"] = f"{native_text}\n{ocr_text}"
        elif ocr_text and not native_text:
            merged["text"] = ocr_text
        merged["lines"] = list(merged.get("lines", []) or []) + list(
            ocr_page.get("lines", []) or []
        )
        merged["ocr_text_present"] = bool(ocr_text)
        by_page[page_number] = merged
    return [by_page[key] for key in sorted(by_page)]


def _layout_provider_result(path, provider_name, document_id, table_settings_profile, strict):
    provider = normalize_shadow_layout_provider(provider_name)
    if provider == PROVIDER_NATIVE_TEXT:
        return None
    try:
        from app.document_ai.layout_provider import extract_layout_artifact

        provider_result = extract_layout_artifact(
            path,
            provider_name=PROVIDER_PDFPLUMBER,
            document_id=document_id,
            table_settings_profile=table_settings_profile,
        )
    except Exception:
        if strict:
            raise
        return {
            "provider_name": PROVIDER_PDFPLUMBER,
            "status": STATUS_FAILED,
            "artifact": {},
            "warning_codes": ["LAYOUT_PROVIDER_FAILED"],
            "error_code": "layout_provider_exception",
            "table_settings_profile": table_settings_profile,
        }
    if provider == PROVIDER_AUTO and provider_result.get("status") not in {"success", "empty_text"}:
        return provider_result
    if strict and provider == PROVIDER_PDFPLUMBER and provider_result.get("status") not in {"success", "empty_text"}:
        raise RuntimeError(provider_result.get("safe_message") or "Shadow layout provider failed.")
    return provider_result


def _ocr_provider_result(path, provider_name, triage, page_mode, dpi, strict):
    provider = normalize_ocr_provider(provider_name)
    if provider == OCR_PROVIDER_NONE:
        return empty_ocr_provider_result(provider_requested=provider)
    try:
        from app.document_ai.tesseract_ocr_provider import extract_tesseract_ocr

        return extract_tesseract_ocr(
            path,
            triage_result=triage,
            page_mode=normalize_ocr_page_mode(page_mode),
            dpi=normalize_ocr_dpi(dpi),
            strict=strict,
            provider_requested=provider,
        )
    except Exception:
        if strict:
            raise
        return {
            **empty_ocr_provider_result(provider_requested=provider),
            "provider_name": OCR_PROVIDER_TESSERACT,
            "status": "failed",
            "errors": ["ocr_provider_exception"],
        }


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


def extract_document_artifact_from_pdf(
    path,
    document_id=None,
    triage_result=None,
    layout_provider_name=PROVIDER_NATIVE_TEXT,
    table_settings_profile="default",
    strict_layout_provider=False,
    ocr_provider_name=OCR_PROVIDER_NONE,
    ocr_pages="ocr_required",
    ocr_dpi=200,
    strict_ocr=False,
):
    """Build an in-memory document artifact from a local PDF.

    This uses native text by default. Optional OCR remains shadow-only and is
    invoked only when a non-``none`` OCR provider is explicitly requested.
    """
    triage = triage_result if isinstance(triage_result, dict) else triage_document(
        path,
        document_id=document_id,
    )
    file_path = Path(path or "")
    warnings = []
    pages = []
    provider_requested = normalize_shadow_layout_provider(layout_provider_name)
    layout_provider_summary = empty_layout_provider_summary(provider_requested)
    layout_artifact = {}
    ocr_provider = normalize_ocr_provider(ocr_provider_name)
    ocr_result = empty_ocr_provider_result(provider_requested=ocr_provider)

    if not file_path.exists() or file_path.suffix.lower() != ".pdf":
        return build_document_extraction_artifact(
            document_id=triage.get("document_id", document_id or ""),
            pages=[],
            source=SOURCE_UNKNOWN,
            triage=triage,
            layout_provider_summary=layout_provider_summary,
            ocr_provider_result=ocr_result,
        )

    try:
        reader_type = _load_pypdf_reader()
        with redirect_stderr(StringIO()):
            reader = reader_type(str(file_path))
            pdf_pages = _safe_pages(reader)
    except Exception as exc:
        triage = dict(triage)
        triage.setdefault("warnings", []).append(f"artifact_pdf_read_failed:{exc.__class__.__name__}")
        return build_document_extraction_artifact(
            document_id=triage.get("document_id", document_id or ""),
            pages=[],
            source=SOURCE_UNKNOWN,
            triage=triage,
            layout_provider_summary=layout_provider_summary,
            ocr_provider_result=ocr_result,
        )

    for index, page in enumerate(pdf_pages, start=1):
        page_text = _extract_page_text(page, index, warnings)
        pages.append(
            build_document_page_artifact(
                page_number=index,
                width=getattr(page, "mediabox", {}).width if getattr(page, "mediabox", None) else 0,
                height=getattr(page, "mediabox", {}).height if getattr(page, "mediabox", None) else 0,
                text=page_text,
                source=SOURCE_NATIVE,
            )
        )

    if warnings:
        triage = dict(triage)
        triage["warnings"] = sorted(set(list(triage.get("warnings", [])) + warnings))

    provider_result = _layout_provider_result(
        file_path,
        provider_requested,
        triage.get("document_id", document_id or ""),
        table_settings_profile,
        strict_layout_provider,
    )
    if provider_result:
        layout_artifact = provider_result.get("artifact") or {}
        layout_pages = _layout_artifact_pages(layout_artifact)
        if layout_pages and provider_result.get("status") == STATUS_SUCCESS:
            pages = _merge_native_and_layout_pages(pages, layout_pages)
        status = provider_result.get("status") or STATUS_UNAVAILABLE
        summary_status = STATUS_SUCCESS if status == "success" else (
            STATUS_PARTIAL if status == "empty_text" else STATUS_UNAVAILABLE
        )
        layout_provider_summary = build_layout_provider_summary(
            provider_requested=provider_requested,
            provider_used=provider_result.get("provider_name") or PROVIDER_PDFPLUMBER,
            available=status not in {"dependency_missing", "unavailable"},
            status=summary_status,
            pages=_layout_artifact_pages(layout_artifact),
            warnings=provider_result.get("warning_codes", []),
            errors=[provider_result.get("error_code")] if provider_result.get("error_code") else [],
            table_settings_profile=provider_result.get("table_settings_profile", table_settings_profile),
        )

    base_has_text_before_ocr = any(_text(page.get("text")) for page in pages)
    ocr_result = _ocr_provider_result(
        file_path,
        ocr_provider,
        triage,
        ocr_pages,
        ocr_dpi,
        strict_ocr,
    )
    ocr_pages_artifact = _ocr_result_pages(ocr_result)
    if ocr_pages_artifact and ocr_result.get("status") in {
        OCR_STATUS_SUCCESS,
        OCR_STATUS_PARTIAL,
    }:
        pages = _merge_ocr_pages(pages, ocr_pages_artifact)

    has_ocr_text = bool(ocr_pages_artifact)
    source = (
        SOURCE_HYBRID
        if has_ocr_text and base_has_text_before_ocr
        else SOURCE_OCR
        if has_ocr_text
        else layout_provider_summary.get("provider_used")
        if layout_provider_summary.get("status") == STATUS_SUCCESS
        else SOURCE_NATIVE
        if any(page["text"].strip() for page in pages)
        else SOURCE_UNKNOWN
    )
    return build_document_extraction_artifact(
        document_id=triage.get("document_id", document_id or ""),
        pages=pages,
        source=source,
        triage=triage,
        layout_provider_summary=layout_provider_summary,
        layout_artifact=layout_artifact,
        ocr_provider_result=ocr_result,
    )


def artifact_summary(artifact):
    pages = artifact.get("pages", []) if isinstance(artifact, dict) else []
    full_text = (artifact or {}).get("full_text", "")
    return {
        "page_count": len(pages),
        "source": (artifact or {}).get("source", ""),
        "line_count": sum(len(page.get("lines", [])) for page in pages),
        "word_count": sum(len(page.get("words", [])) for page in pages),
        "table_count": sum(len(page.get("tables", [])) for page in pages),
        "full_text_length": len(full_text or ""),
        "full_text_present": bool(str(full_text or "").strip()),
        "layout_provider_summary": (artifact or {}).get("layout_provider_summary", {}),
        "ocr_provider_summary": safe_ocr_provider_summary(
            (artifact or {}).get("ocr_provider_result", {})
        ),
        "ocr_document_classification": _ocr_document_classification_diagnostic(
            (artifact or {}).get("ocr_provider_result", {})
        ),
    }
