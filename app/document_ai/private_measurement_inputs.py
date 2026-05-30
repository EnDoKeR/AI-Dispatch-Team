"""Private measurement input discovery and safe aliasing helpers."""

import json
from pathlib import Path


class PrivateMeasurementInputError(ValueError):
    """Raised when private measurement input configuration is invalid."""


def validate_private_input_dir(path):
    input_dir = Path(path)

    if not input_dir.exists():
        raise PrivateMeasurementInputError("private input directory does not exist")

    if not input_dir.is_dir():
        raise PrivateMeasurementInputError("private input path is not a directory")

    return input_dir


def discover_private_pdfs(input_dir):
    directory = validate_private_input_dir(input_dir)

    return sorted(
        [
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() == ".pdf"
        ],
        key=lambda path: path.name.lower(),
    )


def build_safe_aliases(paths, prefix="RATECON"):
    safe_prefix = str(prefix or "RATECON").strip().upper() or "RATECON"

    return {
        Path(path): f"{safe_prefix}_{index:03d}"
        for index, path in enumerate(sorted(paths, key=lambda item: Path(item).name.lower()), start=1)
    }


def load_alias_map(path):
    alias_path = Path(path)
    if not alias_path.exists():
        return {}

    payload = json.loads(alias_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PrivateMeasurementInputError("alias map must be a JSON object")

    return {
        str(key): str(value)
        for key, value in payload.items()
        if str(key).strip() and str(value).strip()
    }
