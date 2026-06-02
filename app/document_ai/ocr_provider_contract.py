"""Optional local OCR provider contract for shadow RateCon diagnostics."""

from dataclasses import asdict, dataclass, field


OCR_PROVIDER_NONE = "none"
OCR_PROVIDER_AUTO = "auto"
OCR_PROVIDER_TESSERACT = "tesseract"
OCR_PROVIDER_UNAVAILABLE = "unavailable"

OCR_PROVIDER_CHOICES = (
    OCR_PROVIDER_NONE,
    OCR_PROVIDER_AUTO,
    OCR_PROVIDER_TESSERACT,
)

OCR_PAGES_OCR_REQUIRED = "ocr_required"
OCR_PAGES_ALL = "all"
OCR_PAGES_FIRST_PAGE_ONLY = "first_page_only"

OCR_PAGE_MODE_CHOICES = (
    OCR_PAGES_OCR_REQUIRED,
    OCR_PAGES_ALL,
    OCR_PAGES_FIRST_PAGE_ONLY,
)

OCR_STATUS_SUCCESS = "success"
OCR_STATUS_UNAVAILABLE = "unavailable"
OCR_STATUS_FAILED = "failed"
OCR_STATUS_PARTIAL = "partial"
OCR_STATUS_SKIPPED = "skipped"
OCR_STATUS_LOW_CONFIDENCE = "low_confidence"


def _text(value):
    return str(value or "").strip()


def _safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float_or_none(value):
    if value in [None, ""]:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_ocr_provider(value):
    token = _text(value).lower()
    return token if token in OCR_PROVIDER_CHOICES else OCR_PROVIDER_NONE


def normalize_ocr_page_mode(value):
    token = _text(value).lower()
    return token if token in OCR_PAGE_MODE_CHOICES else OCR_PAGES_OCR_REQUIRED


def normalize_ocr_dpi(value):
    parsed = _safe_int(value) or 200
    if parsed not in {150, 200, 300}:
        return 200
    return parsed


@dataclass(frozen=True)
class OcrPageResult:
    page_number: int = 0
    text: str = ""
    line_count: int = 0
    word_count: int = 0
    mean_confidence: float | None = None
    source_image_dpi: int = 200
    status: str = OCR_STATUS_SKIPPED
    word_boxes: list[dict] = field(default_factory=list)
    line_boxes: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)

    def to_dict(self):
        payload = asdict(self)
        payload["page_number"] = _safe_int(payload.get("page_number"))
        payload["text"] = str(payload.get("text") or "")
        payload["line_count"] = _safe_int(payload.get("line_count"))
        payload["word_count"] = _safe_int(payload.get("word_count"))
        payload["mean_confidence"] = _safe_float_or_none(payload.get("mean_confidence"))
        payload["source_image_dpi"] = _safe_int(payload.get("source_image_dpi")) or 200
        payload["status"] = _text(payload.get("status")) or OCR_STATUS_SKIPPED
        payload["word_boxes"] = [
            dict(item or {})
            for item in payload.get("word_boxes", []) or []
            if isinstance(item, dict) and _text(item.get("text"))
        ]
        payload["line_boxes"] = [
            dict(item or {})
            for item in payload.get("line_boxes", []) or []
            if isinstance(item, dict) and _text(item.get("text"))
        ]
        payload["warnings"] = [_text(item) for item in payload.get("warnings", []) if _text(item)]
        payload["diagnostics"] = (
            dict(payload.get("diagnostics") or {})
            if isinstance(payload.get("diagnostics"), dict)
            else {}
        )
        return payload


@dataclass(frozen=True)
class OcrProviderResult:
    provider_name: str = OCR_PROVIDER_NONE
    provider_requested: str = OCR_PROVIDER_NONE
    available: bool = False
    status: str = OCR_STATUS_SKIPPED
    pages: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)

    def to_dict(self):
        pages = [
            page.to_dict() if isinstance(page, OcrPageResult) else dict(page or {})
            for page in self.pages
        ]
        return {
            "provider_name": _text(self.provider_name) or OCR_PROVIDER_NONE,
            "provider_requested": _text(self.provider_requested) or OCR_PROVIDER_NONE,
            "available": bool(self.available),
            "status": _text(self.status) or OCR_STATUS_SKIPPED,
            "pages": pages,
            "warnings": [_text(item) for item in self.warnings if _text(item)],
            "errors": [_text(item) for item in self.errors if _text(item)],
            "diagnostics": (
                dict(self.diagnostics) if isinstance(self.diagnostics, dict) else {}
            ),
        }


def build_ocr_page_result(
    page_number=0,
    text="",
    mean_confidence=None,
    source_image_dpi=200,
    status="",
    word_boxes=None,
    line_boxes=None,
    warnings=None,
    diagnostics=None,
):
    page_text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line for line in page_text.splitlines() if line.strip()]
    words = page_text.split()
    resolved_status = _text(status) or (
        OCR_STATUS_SUCCESS if page_text.strip() else OCR_STATUS_FAILED
    )
    return OcrPageResult(
        page_number=_safe_int(page_number),
        text=page_text,
        line_count=len(lines),
        word_count=len(words),
        mean_confidence=_safe_float_or_none(mean_confidence),
        source_image_dpi=normalize_ocr_dpi(source_image_dpi),
        status=resolved_status,
        word_boxes=list(word_boxes or []),
        line_boxes=list(line_boxes or []),
        warnings=list(warnings or []),
        diagnostics=dict(diagnostics or {}),
    ).to_dict()


def build_ocr_provider_result(
    provider_name=OCR_PROVIDER_NONE,
    provider_requested=OCR_PROVIDER_NONE,
    available=False,
    status="",
    pages=None,
    warnings=None,
    errors=None,
    diagnostics=None,
):
    return OcrProviderResult(
        provider_name=provider_name,
        provider_requested=provider_requested,
        available=available,
        status=status or OCR_STATUS_SKIPPED,
        pages=list(pages or []),
        warnings=list(warnings or []),
        errors=list(errors or []),
        diagnostics=dict(diagnostics or {}),
    ).to_dict()


def empty_ocr_provider_result(provider_requested=OCR_PROVIDER_NONE):
    return build_ocr_provider_result(
        provider_name=OCR_PROVIDER_NONE,
        provider_requested=normalize_ocr_provider(provider_requested),
        available=False,
        status=OCR_STATUS_SKIPPED,
        pages=[],
        diagnostics={"ocr_text_included": False},
    )


def safe_ocr_provider_summary(result):
    result = result if isinstance(result, dict) else {}
    pages = [page for page in result.get("pages", []) or [] if isinstance(page, dict)]
    warnings = result.get("warnings", []) or []
    errors = result.get("errors", []) or []
    page_status_counts = {}
    for page in pages:
        status = _text(page.get("status")) or OCR_STATUS_SKIPPED
        page_status_counts[status] = page_status_counts.get(status, 0) + 1
    word_box_count = sum(len(page.get("word_boxes", []) or []) for page in pages)
    line_box_count = sum(len(page.get("line_boxes", []) or []) for page in pages)
    return {
        "provider_requested": _text(result.get("provider_requested")),
        "provider_used": _text(result.get("provider_name")),
        "available": bool(result.get("available")),
        "status": _text(result.get("status")) or OCR_STATUS_SKIPPED,
        "pages_attempted": len(pages),
        "pages_ocr_success": sum(
            1 for page in pages if page.get("status") == OCR_STATUS_SUCCESS
        ),
        "ocr_text_page_count": sum(1 for page in pages if _text(page.get("text"))),
        "ocr_word_count": sum(_safe_int(page.get("word_count")) for page in pages),
        "ocr_line_count": sum(_safe_int(page.get("line_count")) for page in pages),
        "ocr_geometry_available": bool(word_box_count or line_box_count),
        "ocr_geometry_page_count": sum(
            1
            for page in pages
            if page.get("word_boxes") or page.get("line_boxes")
        ),
        "ocr_word_box_count": word_box_count,
        "ocr_line_box_count": line_box_count,
        "page_status_counts": dict(sorted(page_status_counts.items())),
        "warnings": sorted({_text(item) for item in warnings if _text(item)}),
        "errors": sorted({_text(item) for item in errors if _text(item)}),
        "raw_text_included": False,
    }
