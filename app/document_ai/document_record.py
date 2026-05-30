"""JSON-ready document record contract."""

from app.document_ai.document_types import UNKNOWN, normalize_document_type


DOCUMENT_RECORD_VERSION = "document_record_v1"


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


def build_document_record(
    document_id="",
    document_type=UNKNOWN,
    source="",
    received_at_utc="",
    local_file_label="",
    privacy_classification="private",
    page_count="",
    linked_case_id="",
    warnings=None,
):
    return {
        "document_id": str(document_id or "").strip(),
        "document_type": normalize_document_type(document_type),
        "source": str(source or "").strip(),
        "received_at_utc": str(received_at_utc or "").strip(),
        "local_file_label": str(local_file_label or "").strip(),
        "privacy_classification": str(privacy_classification or "private").strip(),
        "page_count": page_count if page_count not in [None, ""] else "",
        "linked_case_id": str(linked_case_id or "").strip(),
        "warnings": normalize_list(warnings),
        "record_version": DOCUMENT_RECORD_VERSION,
    }
