import json
import re
from datetime import datetime, timezone
from pathlib import Path


TELEGRAM_OUTBOX_FILE = Path("data/telegram_outbox.jsonl")


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(file_path, record):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def first_match(pattern, text, default=""):
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)

    if match:
        return match.group(1).strip()

    return default


def infer_message_type(text):
    text_upper = str(text or "").upper()

    if "MARKET SNAPSHOT" in text_upper:
        return "MARKET_SNAPSHOT"

    if "LOAD OPPORTUNITY" in text_upper:
        return "LOAD_OPPORTUNITY"

    if "REVIEW ONCE" in text_upper:
        return "REVIEW_ONCE"

    if "SEARCH HEALTH CHECK" in text_upper:
        return "SEARCH_HEALTH_CHECK"

    if "RELOAD" in text_upper:
        return "RELOAD_CHAIN"

    return "UNKNOWN"


def parse_driver_name(text):
    first_line = str(text or "").splitlines()[0] if text else ""

    if "—" in first_line:
        return first_line.split("—")[-1].strip().split("#")[0].strip()

    return ""


def parse_lane(text):
    for line in str(text or "").splitlines():
        if "→" not in line:
            continue

        if "Google" in line:
            continue

        parts = line.split("→", 1)

        if len(parts) != 2:
            continue

        pickup = parts[0].strip()
        delivery = parts[1].strip()

        if pickup and delivery:
            return pickup, delivery

    return "", ""


def parse_reference_id(text):
    reference_id = first_match(
        r"Reference ID:\s*([A-Za-z0-9_.\-]+)",
        text,
        default="",
    )

    return reference_id


def parse_rate(text):
    return first_match(
        r"^Rate:\s*\$?([0-9.,]+)",
        text,
        default="",
    )


def parse_broker(text):
    return first_match(
        r"^Broker:\s*(.+)$",
        text,
        default="",
    )


def parse_mc(text):
    return first_match(
        r"^MC:\s*(.+)$",
        text,
        default="",
    )


def parse_category(text):
    first_line = str(text or "").splitlines()[0] if text else ""

    if "REVIEW ONCE" in first_line and "—" in first_line:
        parts = [part.strip() for part in first_line.split("—")]

        if len(parts) >= 2:
            return parts[1]

    if "LOAD OPPORTUNITY" in first_line:
        return "LOAD OPPORTUNITY"

    if "MARKET SNAPSHOT" in first_line:
        return "MARKET SNAPSHOT"

    if "SEARCH HEALTH CHECK" in first_line:
        return "SEARCH HEALTH CHECK"

    return ""


def extract_telegram_message_id(telegram_response):
    if not isinstance(telegram_response, dict):
        return ""

    result = telegram_response.get("result", {})

    if not isinstance(result, dict):
        return ""

    return result.get("message_id", "")


def log_outgoing_telegram_message(
    text,
    success,
    telegram_response=None,
    error_text="",
):
    text = str(text or "")

    pickup, delivery = parse_lane(text)

    record = {
        "timestamp_utc": utc_now_iso(),
        "message_type": infer_message_type(text),
        "category": parse_category(text),
        "driver_name": parse_driver_name(text),
        "pickup": pickup,
        "delivery": delivery,
        "rate": parse_rate(text),
        "broker": parse_broker(text),
        "broker_mc": parse_mc(text),
        "reference_id": parse_reference_id(text),
        "send_success": bool(success),
        "telegram_message_id": extract_telegram_message_id(telegram_response),
        "error_text": error_text,
        "text": text,
    }

    append_jsonl(TELEGRAM_OUTBOX_FILE, record)

    return record