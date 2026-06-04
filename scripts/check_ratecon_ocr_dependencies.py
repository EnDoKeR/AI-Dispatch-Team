"""Report optional local OCR dependencies for shadow RateCon diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.document_ai.tesseract_ocr_provider import (  # noqa: E402
    check_tesseract_ocr_dependencies,
)


def _format_lines(status):
    lines = [
        "RateCon shadow OCR dependency check",
        f"pytesseract_installed: {status.get('pytesseract_installed')}",
        f"tesseract_executable_found: {status.get('tesseract_executable_found')}",
        f"tesseract_version: {status.get('tesseract_version') or ''}",
        "renderers:",
    ]
    renderers = status.get("renderers", {}) or {}
    for name in ["pypdfium2", "pymupdf", "pdf2image"]:
        lines.append(f"  {name}: {bool(renderers.get(name))}")
    lines.append(f"can_run_ocr: {status.get('can_run_ocr')}")
    if not status.get("can_run_ocr"):
        lines.append("missing_dependency_guidance:")
        for item in status.get("windows_install_guidance", []) or []:
            lines.append(f"  - {item}")
    return lines


def main(argv=None):
    status = check_tesseract_ocr_dependencies()
    print(json.dumps(status, indent=2, sort_keys=True))
    print()
    print("\n".join(_format_lines(status)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
