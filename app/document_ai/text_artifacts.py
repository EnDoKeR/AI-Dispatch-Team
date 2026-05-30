"""Safe text artifact contracts for candidate extraction."""

TEXT_ARTIFACT_VERSION = "text_artifact_v1"


def safe_text(value):
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n")


def normalize_list(value):
    if value is None:
        return []

    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]

    return [
        str(item).strip()
        for item in values
        if str(item).strip()
    ]


def build_text_page_artifact(
    page_number=0,
    text="",
    source_method="synthetic_fixture",
    warnings=None,
):
    page_text = safe_text(text)

    return {
        "page_number": int(page_number or 0),
        "text": page_text,
        "char_count": len(page_text),
        "line_count": len(page_text.splitlines()) if page_text else 0,
        "source_method": str(source_method or "").strip(),
        "warnings": normalize_list(warnings),
    }


def normalize_pages(pages):
    normalized = []

    for index, page in enumerate(pages or [], start=1):
        if isinstance(page, dict):
            normalized.append(
                build_text_page_artifact(
                    page_number=page.get("page_number", index),
                    text=page.get("text", ""),
                    source_method=page.get("source_method", "synthetic_fixture"),
                    warnings=page.get("warnings", []),
                )
            )
        else:
            normalized.append(
                build_text_page_artifact(
                    page_number=index,
                    text=page,
                    source_method="synthetic_fixture",
                )
            )

    return normalized


def build_text_extraction_artifact_for_candidates(
    artifact_id="",
    document_id="",
    source_name="",
    pages=None,
    full_text="",
    source_method="synthetic_fixture",
    warnings=None,
    contains_private_text=False,
    artifact_version=TEXT_ARTIFACT_VERSION,
):
    normalized_pages = normalize_pages(pages)

    if not normalized_pages and full_text:
        normalized_pages = [
            build_text_page_artifact(
                page_number=1,
                text=full_text,
                source_method=source_method,
            )
        ]

    computed_full_text = safe_text(full_text)

    if not computed_full_text:
        computed_full_text = "\n".join(page["text"] for page in normalized_pages)

    char_count = sum(page["char_count"] for page in normalized_pages)
    normalized_warnings = normalize_list(warnings)
    private_text_flag = bool(contains_private_text)

    if private_text_flag and "contains_private_text" not in normalized_warnings:
        normalized_warnings.append("contains_private_text")

    return {
        "artifact_id": str(artifact_id or "").strip(),
        "document_id": str(document_id or "").strip(),
        "source_name": str(source_name or "").strip(),
        "pages": normalized_pages,
        "full_text": computed_full_text,
        "char_count": char_count,
        "page_count": len(normalized_pages),
        "artifact_version": str(artifact_version or TEXT_ARTIFACT_VERSION).strip(),
        "source_method": str(source_method or "").strip(),
        "warnings": normalized_warnings,
        "contains_private_text": private_text_flag,
    }
