"""Optional local Tesseract OCR provider for shadow-only diagnostics."""

from contextlib import suppress
from importlib import import_module
from pathlib import Path

from app.document_ai.ocr_provider_contract import (
    OCR_PAGES_ALL,
    OCR_PAGES_FIRST_PAGE_ONLY,
    OCR_PAGES_OCR_REQUIRED,
    OCR_PROVIDER_AUTO,
    OCR_PROVIDER_TESSERACT,
    OCR_STATUS_FAILED,
    OCR_STATUS_PARTIAL,
    OCR_STATUS_SKIPPED,
    OCR_STATUS_SUCCESS,
    OCR_STATUS_UNAVAILABLE,
    build_ocr_page_result,
    build_ocr_provider_result,
    normalize_ocr_dpi,
    normalize_ocr_page_mode,
)
from app.document_ai.pdf_triage_contract import OCR_NEEDED


def _text(value):
    return str(value or "").strip()


def _safe_import(module_name):
    try:
        return import_module(module_name)
    except Exception:
        return None


def _dependency_status():
    ocr_module = _safe_import("pytesseract")
    tesseract_version = ""
    executable_found = False
    if ocr_module is not None:
        with suppress(Exception):
            tesseract_version = str(ocr_module.get_tesseract_version())
            executable_found = True
    renderers = {
        "pypdfium2": _safe_import("pypdfium2") is not None,
        "pymupdf": _safe_import("fitz") is not None,
        "pdf2image": _safe_import("pdf2image") is not None,
    }
    return {
        "pytesseract_installed": ocr_module is not None,
        "tesseract_executable_found": executable_found,
        "tesseract_version": tesseract_version,
        "renderers": renderers,
        "renderer_available": any(renderers.values()),
        "can_run_ocr": bool(ocr_module is not None and executable_found and any(renderers.values())),
    }


def check_tesseract_ocr_dependencies():
    status = _dependency_status()
    guidance = []
    if not status["pytesseract_installed"]:
        guidance.append("Install pytesseract in the local dev environment.")
    if not status["tesseract_executable_found"]:
        guidance.append("Install Tesseract OCR and ensure tesseract.exe is on PATH.")
    if not status["renderer_available"]:
        guidance.append(
            "Install one local PDF renderer: pypdfium2, PyMuPDF, or pdf2image with Poppler."
        )
    return {
        **status,
        "provider_name": OCR_PROVIDER_TESSERACT,
        "windows_install_guidance": guidance,
    }


def _selected_page_numbers(triage_result, page_mode):
    page_mode = normalize_ocr_page_mode(page_mode)
    page_count = int((triage_result or {}).get("page_count") or 0)
    if page_count <= 0:
        return []
    if page_mode == OCR_PAGES_ALL:
        return list(range(1, page_count + 1))
    if page_mode == OCR_PAGES_FIRST_PAGE_ONLY:
        return [1]
    profiles = (triage_result or {}).get("page_profiles", []) or []
    image_pages = [
        int(profile.get("page_number") or 0)
        for profile in profiles
        if isinstance(profile, dict) and profile.get("image_like")
    ]
    image_pages = [page for page in image_pages if page > 0]
    if image_pages:
        return image_pages
    if (triage_result or {}).get("ocr_required"):
        return list(range(1, page_count + 1))
    if _text((triage_result or {}).get("recommended_route")) == OCR_NEEDED:
        return list(range(1, page_count + 1))
    return []


def _render_with_pypdfium2(pdf_path, page_numbers, dpi):
    pdfium = _safe_import("pypdfium2")
    if pdfium is None:
        return None
    scale = float(dpi) / 72.0
    document = pdfium.PdfDocument(str(pdf_path))
    try:
        rendered = []
        for page_number in page_numbers:
            page = document[page_number - 1]
            bitmap = page.render(scale=scale)
            rendered.append((page_number, bitmap.to_pil(), "pypdfium2"))
        return rendered
    finally:
        with suppress(Exception):
            document.close()


def _render_with_pymupdf(pdf_path, page_numbers, dpi):
    fitz = _safe_import("fitz")
    image_module = _safe_import("PIL.Image")
    if fitz is None or image_module is None:
        return None
    from io import BytesIO

    scale = float(dpi) / 72.0
    document = fitz.open(str(pdf_path))
    try:
        rendered = []
        for page_number in page_numbers:
            page = document[page_number - 1]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image = image_module.open(BytesIO(pixmap.tobytes("png")))
            rendered.append((page_number, image, "pymupdf"))
        return rendered
    finally:
        with suppress(Exception):
            document.close()


def _render_with_pdf2image(pdf_path, page_numbers, dpi):
    pdf2image = _safe_import("pdf2image")
    if pdf2image is None:
        return None
    rendered = []
    for page_number in page_numbers:
        images = pdf2image.convert_from_path(
            str(pdf_path),
            dpi=int(dpi),
            first_page=page_number,
            last_page=page_number,
        )
        if images:
            rendered.append((page_number, images[0], "pdf2image"))
    return rendered


def _render_pages(pdf_path, page_numbers, dpi):
    for renderer in [_render_with_pypdfium2, _render_with_pymupdf, _render_with_pdf2image]:
        try:
            rendered = renderer(pdf_path, page_numbers, dpi)
        except Exception:
            rendered = None
        if rendered:
            return rendered
    return []


def _safe_float(value, default=-1.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _bbox(left, top, width, height):
    left = _safe_int(left)
    top = _safe_int(top)
    width = _safe_int(width)
    height = _safe_int(height)
    return {
        "x0": left,
        "y0": top,
        "x1": left + max(width, 0),
        "y1": top + max(height, 0),
        "left": left,
        "top": top,
        "right": left + max(width, 0),
        "bottom": top + max(height, 0),
        "width": max(width, 0),
        "height": max(height, 0),
    }


def _ocr_boxes_from_tsv(data, page_number):
    words = []
    line_groups = {}
    text_items = data.get("text", []) or []
    def column_value(name, index, default=""):
        values = data.get(name, []) or []
        return values[index] if index < len(values) else default

    for index, text in enumerate(text_items):
        token = _text(text)
        if not token:
            continue
        confidence = _safe_float(column_value("conf", index), default=-1.0)
        left = _safe_int(column_value("left", index))
        top = _safe_int(column_value("top", index))
        width = _safe_int(column_value("width", index))
        height = _safe_int(column_value("height", index))
        block_num = _safe_int(column_value("block_num", index))
        par_num = _safe_int(column_value("par_num", index))
        line_num = _safe_int(column_value("line_num", index))
        word_num = _safe_int(column_value("word_num", index))
        line_key = (page_number, block_num, par_num, line_num)
        word = {
            "page": page_number,
            "text": token,
            "confidence": confidence if confidence >= 0 else None,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "block_num": block_num,
            "par_num": par_num,
            "line_num": line_num,
            "word_num": word_num,
            "line_index": len(line_groups) if line_key not in line_groups else line_groups[line_key]["line_index"],
            "word_id": f"ocr-p{page_number}-b{block_num}-p{par_num}-l{line_num}-w{word_num}",
            "line_id": f"ocr-p{page_number}-b{block_num}-p{par_num}-l{line_num}",
            "source": "ocr",
            "bbox": _bbox(left, top, width, height),
        }
        words.append(word)
        group = line_groups.setdefault(
            line_key,
            {
                "page": page_number,
                "block_num": block_num,
                "par_num": par_num,
                "line_num": line_num,
                "line_index": len(line_groups),
                "words": [],
            },
        )
        group["words"].append(word)

    line_boxes = []
    for group in line_groups.values():
        line_words = sorted(group["words"], key=lambda item: item.get("word_num", 0))
        if not line_words:
            continue
        left = min(word["bbox"]["x0"] for word in line_words)
        top = min(word["bbox"]["y0"] for word in line_words)
        right = max(word["bbox"]["x1"] for word in line_words)
        bottom = max(word["bbox"]["y1"] for word in line_words)
        confidences = [
            word.get("confidence")
            for word in line_words
            if isinstance(word.get("confidence"), (int, float))
        ]
        mean = round(sum(confidences) / len(confidences), 2) if confidences else None
        line_boxes.append(
            {
                "page": page_number,
                "text": " ".join(word["text"] for word in line_words),
                "confidence": mean,
                "left": left,
                "top": top,
                "width": right - left,
                "height": bottom - top,
                "block_num": group["block_num"],
                "par_num": group["par_num"],
                "line_num": group["line_num"],
                "line_index": group["line_index"],
                "line_id": f"ocr-p{page_number}-b{group['block_num']}-p{group['par_num']}-l{group['line_num']}",
                "source": "ocr",
                "bbox": {
                    "x0": left,
                    "y0": top,
                    "x1": right,
                    "y1": bottom,
                    "left": left,
                    "top": top,
                    "right": right,
                    "bottom": bottom,
                    "width": right - left,
                    "height": bottom - top,
                },
                "words": [
                    {
                        "text": word["text"],
                        "confidence": word.get("confidence"),
                        "bbox": word["bbox"],
                        "word_num": word.get("word_num"),
                    }
                    for word in line_words
                ],
            }
        )
    line_boxes.sort(key=lambda item: (item.get("top", 0), item.get("left", 0)))
    for index, line in enumerate(line_boxes):
        line["line_index"] = index
    return words, line_boxes


def _ocr_image(ocr_module, image, page_number, dpi):
    try:
        data = ocr_module.image_to_data(image, output_type=ocr_module.Output.DICT)
        word_boxes, line_boxes = _ocr_boxes_from_tsv(data, page_number)
        words = []
        confidences = []
        for word in word_boxes:
            words.append(word["text"])
            parsed = _safe_float(word.get("confidence"), default=-1.0)
            if parsed >= 0:
                confidences.append(parsed)
        text = " ".join(words)
        mean = round(sum(confidences) / len(confidences), 2) if confidences else None
        return build_ocr_page_result(
            page_number=page_number,
            text=text,
            mean_confidence=mean,
            source_image_dpi=dpi,
            status=OCR_STATUS_SUCCESS if text.strip() else OCR_STATUS_FAILED,
            word_boxes=word_boxes,
            line_boxes=line_boxes,
            diagnostics={
                "ocr_engine": "tesseract",
                "ocr_method": "image_to_data",
                "ocr_geometry_available": bool(word_boxes or line_boxes),
                "ocr_word_box_count": len(word_boxes),
                "ocr_line_box_count": len(line_boxes),
            },
        )
    except Exception:
        text = ocr_module.image_to_string(image) or ""
        return build_ocr_page_result(
            page_number=page_number,
            text=text,
            mean_confidence=None,
            source_image_dpi=dpi,
            status=OCR_STATUS_SUCCESS if text.strip() else OCR_STATUS_FAILED,
            warnings=["tesseract_image_to_data_failed"],
            diagnostics={"ocr_engine": "tesseract", "ocr_method": "image_to_string"},
        )


def extract_tesseract_ocr(
    pdf_path,
    triage_result=None,
    page_mode=OCR_PAGES_OCR_REQUIRED,
    dpi=200,
    strict=False,
    provider_requested=OCR_PROVIDER_TESSERACT,
):
    requested = provider_requested or OCR_PROVIDER_TESSERACT
    page_numbers = _selected_page_numbers(triage_result or {}, page_mode)
    if not page_numbers:
        return build_ocr_provider_result(
            provider_name=OCR_PROVIDER_TESSERACT,
            provider_requested=requested,
            available=False,
            status=OCR_STATUS_SKIPPED,
            pages=[],
            warnings=["ocr_skipped_no_selected_pages"],
            diagnostics={"selected_page_numbers": []},
        )

    dependency = check_tesseract_ocr_dependencies()
    if not dependency["pytesseract_installed"]:
        result = build_ocr_provider_result(
            provider_name=OCR_PROVIDER_TESSERACT,
            provider_requested=requested,
            available=False,
            status=OCR_STATUS_UNAVAILABLE,
            errors=["pytesseract is not installed."],
            diagnostics=dependency,
        )
        if strict:
            raise RuntimeError("pytesseract is not installed.")
        return result
    if not dependency["tesseract_executable_found"]:
        result = build_ocr_provider_result(
            provider_name=OCR_PROVIDER_TESSERACT,
            provider_requested=requested,
            available=False,
            status=OCR_STATUS_UNAVAILABLE,
            errors=["Tesseract OCR is not installed or not on PATH."],
            diagnostics=dependency,
        )
        if strict:
            raise RuntimeError("Tesseract OCR is not installed or not on PATH.")
        return result
    if not dependency["renderer_available"]:
        result = build_ocr_provider_result(
            provider_name=OCR_PROVIDER_TESSERACT,
            provider_requested=requested,
            available=False,
            status=OCR_STATUS_UNAVAILABLE,
            errors=["No PDF page renderer is available for OCR."],
            diagnostics=dependency,
        )
        if strict:
            raise RuntimeError("No PDF page renderer is available for OCR.")
        return result

    path = Path(pdf_path or "")
    dpi = normalize_ocr_dpi(dpi)
    rendered = _render_pages(path, page_numbers, dpi)
    if not rendered:
        result = build_ocr_provider_result(
            provider_name=OCR_PROVIDER_TESSERACT,
            provider_requested=requested,
            available=False,
            status=OCR_STATUS_UNAVAILABLE,
            errors=["No PDF page renderer is available for OCR."],
            diagnostics={**dependency, "selected_page_numbers": page_numbers},
        )
        if strict:
            raise RuntimeError("No PDF page renderer is available for OCR.")
        return result

    ocr_module = _safe_import("pytesseract")
    pages = []
    renderer_names = []
    for page_number, image, renderer_name in rendered:
        renderer_names.append(renderer_name)
        try:
            page_result = _ocr_image(ocr_module, image, page_number, dpi)
        except Exception as exc:
            if strict:
                raise
            page_result = build_ocr_page_result(
                page_number=page_number,
                text="",
                source_image_dpi=dpi,
                status=OCR_STATUS_FAILED,
                warnings=[f"ocr_page_failed:{exc.__class__.__name__}"],
                diagnostics={"ocr_engine": "tesseract"},
            )
        pages.append(page_result)
    success = sum(1 for page in pages if page.get("status") == OCR_STATUS_SUCCESS)
    failed = sum(1 for page in pages if page.get("status") == OCR_STATUS_FAILED)
    status = OCR_STATUS_SUCCESS if success == len(pages) else (
        OCR_STATUS_PARTIAL if success else OCR_STATUS_FAILED
    )
    return build_ocr_provider_result(
        provider_name=OCR_PROVIDER_TESSERACT,
        provider_requested=requested or OCR_PROVIDER_AUTO,
        available=True,
        status=status,
        pages=pages,
        warnings=["ocr_partial_page_failure"] if success and failed else [],
        errors=[] if success else ["ocr_failed_no_page_text"],
        diagnostics={
            **dependency,
            "selected_page_numbers": page_numbers,
            "renderer_used": sorted(set(renderer_names))[0] if renderer_names else "",
        },
    )
