"""Safe extraction artifact contract without raw private text."""

EXTRACTION_ARTIFACT_VERSION = "extraction_artifact_v1"


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


def build_extraction_artifact(
    document_id="",
    method="",
    pages=None,
    text_summary="",
    word_count=0,
    block_count=0,
    table_count=0,
    warnings=None,
    artifact_version=EXTRACTION_ARTIFACT_VERSION,
):
    return {
        "document_id": str(document_id or "").strip(),
        "method": str(method or "").strip(),
        "pages": normalize_list(pages),
        "text_summary": str(text_summary or "").strip(),
        "word_count": int(word_count or 0),
        "block_count": int(block_count or 0),
        "table_count": int(table_count or 0),
        "warnings": normalize_list(warnings),
        "artifact_version": str(artifact_version or EXTRACTION_ARTIFACT_VERSION).strip(),
        "raw_text_included": False,
    }
