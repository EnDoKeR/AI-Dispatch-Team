"""Import a Google service account JSON into ignored local config storage."""

import argparse
import base64
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_PRIVATE_DIR = REPO_ROOT / ".local_private"
DEFAULT_OUTPUT = LOCAL_PRIVATE_DIR / "google-service-account.json"
EXPECTED_SERVICE_ACCOUNT_EMAIL = (
    "ai-dispatch-sheet@ai-dispatch-team.iam.gserviceaccount.com"
)
REQUIRED_SERVICE_ACCOUNT_FIELDS = {
    "type",
    "project_id",
    "private_key_id",
    "private_key",
    "client_email",
    "token_uri",
}
FULL_JSON_ERROR = (
    "Expected full Google service account JSON, not private_key_id/hash/API key."
)


class ServiceAccountImportError(ValueError):
    """Raised when local service account import input is missing or unsafe."""


def _text(value):
    return str(value or "").strip()


def _resolve_under_local_private(path):
    requested = Path(path or DEFAULT_OUTPUT)
    if not requested.is_absolute():
        requested = REPO_ROOT / requested
    resolved = requested.resolve()
    local_private = LOCAL_PRIVATE_DIR.resolve()
    if resolved != local_private and local_private not in resolved.parents:
        raise ServiceAccountImportError(
            "credential output must be under ignored .local_private"
        )
    return resolved


def _decode_json_payload(payload):
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ServiceAccountImportError(FULL_JSON_ERROR) from exc
    if not isinstance(data, dict):
        raise ServiceAccountImportError(FULL_JSON_ERROR)
    return data


def validate_service_account_payload(payload):
    data = _decode_json_payload(payload)
    missing = sorted(
        field for field in REQUIRED_SERVICE_ACCOUNT_FIELDS if not _text(data.get(field))
    )
    if missing:
        raise ServiceAccountImportError(
            f"service account JSON is missing required fields: {','.join(missing)}"
        )
    if data.get("type") != "service_account":
        raise ServiceAccountImportError(FULL_JSON_ERROR)
    if "BEGIN PRIVATE KEY" not in _text(data.get("private_key")):
        raise ServiceAccountImportError(FULL_JSON_ERROR)
    if _text(data.get("client_email")) != EXPECTED_SERVICE_ACCOUNT_EMAIL:
        raise ServiceAccountImportError("service account email does not match expected review sync account")
    return data


def write_local_service_account_json(payload, output=DEFAULT_OUTPUT, overwrite=False):
    data = validate_service_account_payload(payload)
    output_path = _resolve_under_local_private(output)
    if output_path.exists() and not overwrite:
        raise ServiceAccountImportError(
            "local service account credential already exists; pass --overwrite"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "credential_written": True,
        "client_email_matches": data.get("client_email") == EXPECTED_SERVICE_ACCOUNT_EMAIL,
        "output_under_local_private": True,
        "private_key_printed": False,
        "raw_json_printed": False,
        "credential_path_printed": False,
    }


def _payload_from_args(args):
    if args.from_file:
        return Path(args.from_file).read_text(encoding="utf-8")
    if args.from_stdin:
        return sys.stdin.read()
    env_payload = os.environ.get("AI_DISPATCH_GOOGLE_SERVICE_ACCOUNT_JSON")
    if env_payload:
        return env_payload
    env_payload_b64 = os.environ.get("AI_DISPATCH_GOOGLE_SERVICE_ACCOUNT_JSON_B64")
    if env_payload_b64:
        try:
            return base64.b64decode(env_payload_b64, validate=True).decode("utf-8")
        except Exception as exc:
            raise ServiceAccountImportError(FULL_JSON_ERROR) from exc
    raise ServiceAccountImportError("service account JSON input is missing")


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Safely import full Google service account JSON into .local_private."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--from-file", default="")
    source.add_argument("--from-stdin", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _safe_summary_lines(result):
    return [
        f"credential_written: {'yes' if result.get('credential_written') else 'no'}",
        f"client_email_matches: {'yes' if result.get('client_email_matches') else 'no'}",
        f"output_under_local_private: {'yes' if result.get('output_under_local_private') else 'no'}",
        f"private_key_printed: {result.get('private_key_printed', False)}",
        f"raw_json_printed: {result.get('raw_json_printed', False)}",
        f"credential_path_printed: {result.get('credential_path_printed', False)}",
    ]


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        payload = _payload_from_args(args)
        result = write_local_service_account_json(
            payload,
            output=args.output,
            overwrite=args.overwrite,
        )
    except (OSError, ServiceAccountImportError) as exc:
        print("Google service account credential was not imported.", file=sys.stderr)
        print(f"Reason: {exc}.", file=sys.stderr)
        return 2

    for line in _safe_summary_lines(result):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
