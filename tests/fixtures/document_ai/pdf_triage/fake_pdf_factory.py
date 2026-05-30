"""Temp-generated fake PDFs for document AI tests."""

from pathlib import Path


FAKE_RATECON_TEXT = (
    "TRUCKLOAD RATE CONFIRMATION\n"
    "Customer: FAKE BROKER LLC\n"
    "Load No: FAKE-REF-001\n"
    "Pickup: Fake City, ST 00000\n"
    "Pickup Date: 2026-06-01\n"
    "Delivery: Example City, ST 00000\n"
    "Delivery Date: 2026-06-02\n"
    "Rate: $0000.00\n"
    "Commodity: FAKE PRODUCT\n"
    "Weight: 40000 lbs\n"
    "Equipment: FAKE TRAILER\n"
)


def _escape_pdf_text(text):
    return (
        str(text or "")
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", "")
        .replace("\n", "\\n")
    )


def fake_text_pdf_bytes(text=FAKE_RATECON_TEXT):
    content = f"BT /F1 12 Tf 72 720 Td ({_escape_pdf_text(text)}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
    ]

    parts = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in parts))
        parts.append(f"{index} 0 obj\n".encode("ascii"))
        parts.append(obj)
        parts.append(b"\nendobj\n")

    xref_offset = sum(len(part) for part in parts)
    parts.append(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    parts.append(b"0000000000 65535 f \n")

    for offset in offsets[1:]:
        parts.append(f"{offset:010d} 00000 n \n".encode("ascii"))

    parts.append(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )

    return b"".join(parts)


def fake_empty_text_pdf_bytes():
    return fake_text_pdf_bytes("")


def fake_invalid_pdf_bytes():
    return b"not a real pdf"


def write_fake_text_pdf(directory, file_name="digital_text_ratecon_like.pdf", text=FAKE_RATECON_TEXT):
    path = Path(directory) / file_name
    path.write_bytes(fake_text_pdf_bytes(text))
    return path


def write_fake_empty_text_pdf(directory, file_name="image_like_or_empty_text.pdf"):
    path = Path(directory) / file_name
    path.write_bytes(fake_empty_text_pdf_bytes())
    return path


def write_fake_invalid_pdf(directory, file_name="broken_or_invalid.pdf"):
    path = Path(directory) / file_name
    path.write_bytes(fake_invalid_pdf_bytes())
    return path
