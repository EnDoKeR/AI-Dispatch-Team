"""PDF triage contract for future document routing."""

PDF_KIND_DIGITAL_TEXT = "DIGITAL_TEXT"
PDF_KIND_IMAGE_BASED = "IMAGE_BASED"
PDF_KIND_MIXED = "MIXED"
PDF_KIND_ENCRYPTED = "ENCRYPTED"
PDF_KIND_BROKEN = "BROKEN"
PDF_KIND_UNKNOWN = "UNKNOWN"

PDF_KINDS = (
    PDF_KIND_DIGITAL_TEXT,
    PDF_KIND_IMAGE_BASED,
    PDF_KIND_MIXED,
    PDF_KIND_ENCRYPTED,
    PDF_KIND_BROKEN,
    PDF_KIND_UNKNOWN,
)

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


def _safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def normalize_pdf_kind(value):
    text = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")

    if text in PDF_KINDS:
        return text

    return PDF_KIND_UNKNOWN


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


def build_pdf_page_profile(
    page_number=0,
    char_count=0,
    word_count=0,
    has_text=False,
    image_like=False,
    warnings=None,
):
    return {
        "page_number": _safe_int(page_number),
        "char_count": _safe_int(char_count),
        "word_count": _safe_int(word_count),
        "has_text": bool(has_text),
        "image_like": bool(image_like),
        "warnings": normalize_list(warnings),
    }


def normalize_page_profiles(page_profiles):
    profiles = []

    for profile in page_profiles or []:
        if isinstance(profile, dict):
            profiles.append(
                build_pdf_page_profile(
                    page_number=profile.get("page_number", 0),
                    char_count=profile.get("char_count", 0),
                    word_count=profile.get("word_count", 0),
                    has_text=profile.get("has_text", False),
                    image_like=profile.get("image_like", False),
                    warnings=profile.get("warnings", []),
                )
            )

    return profiles


def _average_chars_per_page(char_count, page_count):
    if not page_count:
        return 0.0

    return round(_safe_int(char_count) / _safe_int(page_count), 2)


def infer_pdf_kind(
    has_text_layer=False,
    likely_image_based=False,
    mixed_pdf=False,
    encrypted=False,
    broken=False,
):
    if broken:
        return PDF_KIND_BROKEN

    if encrypted:
        return PDF_KIND_ENCRYPTED

    if mixed_pdf:
        return PDF_KIND_MIXED

    if likely_image_based:
        return PDF_KIND_IMAGE_BASED

    if has_text_layer:
        return PDF_KIND_DIGITAL_TEXT

    return PDF_KIND_UNKNOWN


def build_pdf_triage_result(
    document_id="",
    file_name="",
    page_count=0,
    char_count=0,
    chars_per_page=None,
    has_text_layer=False,
    likely_image_based=False,
    mixed_pdf=False,
    encrypted=False,
    broken=False,
    pdf_kind="",
    recommended_route=MANUAL_REVIEW,
    page_profiles=None,
    warnings=None,
):
    safe_page_profiles = normalize_page_profiles(page_profiles)
    safe_page_count = _safe_int(page_count)
    safe_char_count = _safe_int(char_count)

    if safe_page_profiles:
        safe_page_count = safe_page_count or len(safe_page_profiles)
        safe_char_count = safe_char_count or sum(
            profile["char_count"] for profile in safe_page_profiles
        )
        has_text_layer = bool(has_text_layer) or any(
            profile["has_text"] for profile in safe_page_profiles
        )
        likely_image_based = bool(likely_image_based) or (
            safe_page_count > 0
            and not any(profile["has_text"] for profile in safe_page_profiles)
        )
        mixed_pdf = bool(mixed_pdf) or (
            any(profile["has_text"] for profile in safe_page_profiles)
            and any(not profile["has_text"] for profile in safe_page_profiles)
        )

    resolved_kind = normalize_pdf_kind(pdf_kind) if pdf_kind else infer_pdf_kind(
        has_text_layer=has_text_layer,
        likely_image_based=likely_image_based,
        mixed_pdf=mixed_pdf,
        encrypted=encrypted,
        broken=broken,
    )

    return {
        "document_id": str(document_id or "").strip(),
        "file_name": str(file_name or "").strip(),
        "pdf_kind": resolved_kind,
        "page_count": safe_page_count,
        "char_count": safe_char_count,
        "chars_per_page": (
            float(chars_per_page)
            if chars_per_page not in [None, ""]
            else _average_chars_per_page(safe_char_count, safe_page_count)
        ),
        "has_text_layer": bool(has_text_layer),
        "likely_image_based": bool(likely_image_based),
        "mixed_pdf": bool(mixed_pdf),
        "encrypted": bool(encrypted),
        "broken": bool(broken),
        "recommended_route": normalize_route(recommended_route),
        "page_profiles": safe_page_profiles,
        "warnings": normalize_list(warnings),
        "triage_version": PDF_TRIAGE_VERSION,
    }
