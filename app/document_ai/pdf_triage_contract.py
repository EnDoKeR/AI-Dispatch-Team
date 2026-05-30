"""PDF triage contract for future document routing."""

DIGITAL_TEXT = "DIGITAL_TEXT"
OCR_NEEDED = "OCR_NEEDED"
VISION_REVIEW_CANDIDATE = "VISION_REVIEW_CANDIDATE"
UNSUPPORTED = "UNSUPPORTED"
MANUAL_REVIEW = "MANUAL_REVIEW"

RECOMMENDED_ROUTES = (
    DIGITAL_TEXT,
    OCR_NEEDED,
    VISION_REVIEW_CANDIDATE,
    UNSUPPORTED,
    MANUAL_REVIEW,
)

PDF_TRIAGE_VERSION = "pdf_triage_v1"


def normalize_route(value):
    text = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")

    if text in RECOMMENDED_ROUTES:
        return text

    return MANUAL_REVIEW


def normalize_list(value):
    if value is None:
        return []

    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]

    return [
        str(item).strip()
        for item in items
        if str(item).strip()
    ]


def build_pdf_triage_result(
    page_count=0,
    char_count=0,
    has_text_layer=False,
    image_like=False,
    mixed_pdf=False,
    encrypted=False,
    broken=False,
    recommended_route=MANUAL_REVIEW,
    warnings=None,
):
    return {
        "page_count": int(page_count or 0),
        "char_count": int(char_count or 0),
        "has_text_layer": bool(has_text_layer),
        "image_like": bool(image_like),
        "mixed_pdf": bool(mixed_pdf),
        "encrypted": bool(encrypted),
        "broken": bool(broken),
        "recommended_route": normalize_route(recommended_route),
        "warnings": normalize_list(warnings),
        "triage_version": PDF_TRIAGE_VERSION,
    }
