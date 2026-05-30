"""Document type constants and normalization helpers."""

RATE_CONFIRMATION = "RATE_CONFIRMATION"
REVISED_RATE_CONFIRMATION = "REVISED_RATE_CONFIRMATION"
BOL = "BOL"
POD = "POD"
LUMPER_RECEIPT = "LUMPER_RECEIPT"
INVOICE = "INVOICE"
DETENTION_PROOF = "DETENTION_PROOF"
LAYOVER_PROOF = "LAYOVER_PROOF"
TONU_PROOF = "TONU_PROOF"
OTHER = "OTHER"
UNKNOWN = "UNKNOWN"

DOCUMENT_TYPES = (
    RATE_CONFIRMATION,
    REVISED_RATE_CONFIRMATION,
    BOL,
    POD,
    LUMPER_RECEIPT,
    INVOICE,
    DETENTION_PROOF,
    LAYOVER_PROOF,
    TONU_PROOF,
    OTHER,
    UNKNOWN,
)


def normalize_document_type(value):
    text = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")

    if text in DOCUMENT_TYPES:
        return text

    return UNKNOWN
