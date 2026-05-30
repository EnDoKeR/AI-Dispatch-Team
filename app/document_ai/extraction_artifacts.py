"""Safe extraction artifact contract without raw private text."""

EXTRACTION_ARTIFACT_VERSION = "extraction_artifact_v1"

METHOD_PYPDF = "pypdf"
METHOD_PDFPLUMBER_FUTURE = "pdfplumber_future"
METHOD_OCR_FUTURE = "ocr_future"
METHOD_VISION_FUTURE = "vision_future"
METHOD_SYNTHETIC_FIXTURE = "synthetic_fixture"

EXTRACTION_METHODS = (
    METHOD_PYPDF,
    METHOD_PDFPLUMBER_FUTURE,
    METHOD_OCR_FUTURE,
    METHOD_VISION_FUTURE,
    METHOD_SYNTHETIC_FIXTURE,
)


def normalize_method(value):
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")

    if text in EXTRACTION_METHODS:
        return text

    return text


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


def normalize_page_profiles(page_profiles):
    profiles = []

    for profile in page_profiles or []:
        if not isinstance(profile, dict):
            continue

        profiles.append(
            {
                "page_number": int(profile.get("page_number", 0) or 0),
                "char_count": int(profile.get("char_count", 0) or 0),
                "word_count": int(profile.get("word_count", 0) or 0),
                "has_text": bool(profile.get("has_text", False)),
                "image_like": bool(profile.get("image_like", False)),
                "warnings": normalize_list(profile.get("warnings", [])),
            }
        )

    return profiles


def build_extraction_artifact(
    artifact_id="",
    document_id="",
    method="",
    provider="",
    extractor_version="",
    page_count=0,
    char_count=0,
    pages=None,
    text_summary="",
    page_profiles=None,
    word_count=0,
    block_count=0,
    table_count=0,
    warnings=None,
    source_file_hash="",
    created_at="",
    raw_text_stored=False,
    contains_private_text=False,
    artifact_version=EXTRACTION_ARTIFACT_VERSION,
):
    normalized_warnings = normalize_list(warnings)
    safe_raw_text_stored = bool(raw_text_stored)
    safe_contains_private_text = bool(contains_private_text)

    if safe_raw_text_stored and "raw_text_stored" not in normalized_warnings:
        normalized_warnings.append("raw_text_stored")

    if safe_contains_private_text and "contains_private_text" not in normalized_warnings:
        normalized_warnings.append("contains_private_text")

    return {
        "artifact_id": str(artifact_id or "").strip(),
        "document_id": str(document_id or "").strip(),
        "method": normalize_method(method),
        "provider": str(provider or "").strip(),
        "extractor_version": str(extractor_version or "").strip(),
        "page_count": int(page_count or 0),
        "char_count": int(char_count or 0),
        "pages": normalize_list(pages),
        "text_summary": str(text_summary or "").strip(),
        "page_profiles": normalize_page_profiles(page_profiles),
        "word_count": int(word_count or 0),
        "block_count": int(block_count or 0),
        "table_count": int(table_count or 0),
        "warnings": normalized_warnings,
        "source_file_hash": str(source_file_hash or "").strip(),
        "created_at": str(created_at or "").strip(),
        "raw_text_stored": safe_raw_text_stored,
        "contains_private_text": safe_contains_private_text,
        "artifact_version": str(artifact_version or EXTRACTION_ARTIFACT_VERSION).strip(),
        "raw_text_included": False,
    }
