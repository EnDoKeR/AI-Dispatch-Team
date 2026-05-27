import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))


ENV_FILE = Path(".env")

DECISION_HISTORY_FILE = Path("data/decision_history.jsonl")
DISPATCHER_FEEDBACK_FILE = Path("data/dispatcher_feedback.jsonl")
TELEGRAM_STATE_FILE = Path("data/telegram_feedback_state.json")
RATECONS_FOLDER = Path("data/ratecons")


ALLOWED_FEEDBACK_TYPES = [
    "booked",
    "skipped",
    "called_broker",
    "sent_to_driver",
    "driver_rejected",
    "rate_too_low",
    "bad_broker",
    "wrong_equipment",
    "weight_issue",
    "time_issue",
    "covered",
    "duplicate",
    "good_option",
    "not_interested",
    "ratecon",
    "ratecon_received",
    "other",
]


SHORT_COMMANDS = {
    "/booked": "booked",
    "/skipped": "skipped",
    "/called": "called_broker",
    "/called_broker": "called_broker",
    "/sent": "sent_to_driver",
    "/sent_to_driver": "sent_to_driver",
    "/driver_rejected": "driver_rejected",
    "/rate_too_low": "rate_too_low",
    "/bad_broker": "bad_broker",
    "/wrong_equipment": "wrong_equipment",
    "/weight_issue": "weight_issue",
    "/time_issue": "time_issue",
    "/covered": "covered",
    "/duplicate": "duplicate",
    "/good_option": "good_option",
    "/not_interested": "not_interested",
    "/ratecon": "ratecon_received",
    "/other": "other",
}


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_env():
    values = {}

    if not ENV_FILE.exists():
        return values

    with open(ENV_FILE, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()

    return values


def telegram_api_url(method):
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing in .env")

    return f"https://api.telegram.org/bot{token}/{method}"


def telegram_file_url(file_path):
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing in .env")

    return f"https://api.telegram.org/file/bot{token}/{file_path}"


def api_post(method, data):
    url = telegram_api_url(method)
    encoded_data = urllib.parse.urlencode(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=encoded_data,
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def api_get(method, params=None):
    params = params or {}
    url = telegram_api_url(method)

    if params:
        url += "?" + urllib.parse.urlencode(params)

    with urllib.request.urlopen(url, timeout=70) as response:
        return json.loads(response.read().decode("utf-8"))


def send_message(chat_id, text):
    try:
        api_post(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": "true",
            },
        )
    except Exception as error:
        print("Failed to send Telegram reply:")
        print(error)


def load_jsonl(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        return []

    records = []

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return records


def append_jsonl(file_path, record):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_state():
    if not TELEGRAM_STATE_FILE.exists():
        return {"offset": 0}

    try:
        with open(TELEGRAM_STATE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {"offset": 0}


def save_state(state):
    TELEGRAM_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(TELEGRAM_STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, ensure_ascii=False)


def find_recent_decision(load_id):
    records = load_jsonl(DECISION_HISTORY_FILE)

    load_id = str(load_id or "").strip().lower()

    if not load_id:
        return None

    for record in reversed(records):
        record_load_id = str(record.get("load_id", "") or "").strip().lower()
        reference_id = str(record.get("reference_id", "") or "").strip().lower()

        if record_load_id == load_id:
            return record

        if reference_id and reference_id == load_id:
            return record

    return None


def sanitize_filename(value):
    value = str(value or "").strip()

    if not value:
        return "file"

    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    value = value.strip("._")

    if not value:
        return "file"

    return value[:120]


def get_file_info(file_id):
    result = api_get(
        "getFile",
        {
            "file_id": file_id,
        },
    )

    if not result.get("ok"):
        return None

    return result.get("result", {})


def download_telegram_file(file_id, target_folder, prefix):
    file_info = get_file_info(file_id)

    if not file_info:
        return ""

    file_path = file_info.get("file_path", "")

    if not file_path:
        return ""

    source_url = telegram_file_url(file_path)

    original_name = Path(file_path).name
    final_name = f"{sanitize_filename(prefix)}_{sanitize_filename(original_name)}"

    target_folder = Path(target_folder)
    target_folder.mkdir(parents=True, exist_ok=True)

    target_path = target_folder / final_name

    with urllib.request.urlopen(source_url, timeout=120) as response:
        content = response.read()

    with open(target_path, "wb") as file:
        file.write(content)

    return str(target_path)


def parse_command(text):
    text = str(text or "").strip()

    if not text:
        return None

    parts = text.split(maxsplit=3)
    command = parts[0].strip().lower()

    if "@" in command:
        command = command.split("@", 1)[0]

    if command == "/help":
        return {
            "command": "help",
        }

    if command == "/feedback":
        if len(parts) < 3:
            return {
                "command": "invalid",
                "error": "Use: /feedback <REF> <feedback_type> <note>",
            }

        load_id = parts[1].strip()
        feedback_type = parts[2].strip().lower()
        note = parts[3].strip() if len(parts) >= 4 else ""

        return {
            "command": "feedback",
            "load_id": load_id,
            "feedback_type": feedback_type,
            "note": note,
        }

    if command in SHORT_COMMANDS:
        if len(parts) < 2:
            return {
                "command": "invalid",
                "error": f"Use: {command} <REF> <note>",
            }

        load_id = parts[1].strip()
        note = parts[2].strip() if len(parts) >= 3 else ""

        if len(parts) >= 4:
            note = (note + " " + parts[3].strip()).strip()

        return {
            "command": "feedback",
            "load_id": load_id,
            "feedback_type": SHORT_COMMANDS[command],
            "note": note,
        }

    return {
        "command": "unknown",
    }


def build_feedback_record(
    load_id,
    feedback_type,
    note,
    source,
    telegram_message=None,
    document_path="",
):
    matched_decision = find_recent_decision(load_id)

    if matched_decision:
        record = {
            "timestamp_utc": utc_now_iso(),
            "load_id": matched_decision.get("load_id", ""),
            "reference_id": matched_decision.get("reference_id", ""),
            "driver_name": matched_decision.get("driver_name", ""),
            "pickup": matched_decision.get("pickup", ""),
            "delivery": matched_decision.get("delivery", ""),
            "rate": matched_decision.get("rate", 0),
            "broker_name": matched_decision.get("broker_name", ""),
            "broker_mc": matched_decision.get("broker_mc", ""),
            "ai_decision": matched_decision.get("decision", ""),
            "ai_category": matched_decision.get("category", ""),
            "ai_score": matched_decision.get("score", 0),
            "ai_reasons": matched_decision.get("reasons", []),
            "dispatcher_feedback": feedback_type,
            "dispatcher_note": note,
            "document_path": document_path,
            "source": source,
        }
    else:
        record = {
            "timestamp_utc": utc_now_iso(),
            "load_id": load_id,
            "reference_id": load_id,
            "driver_name": "",
            "pickup": "",
            "delivery": "",
            "rate": 0,
            "broker_name": "",
            "broker_mc": "",
            "ai_decision": "UNKNOWN",
            "ai_category": "UNKNOWN",
            "ai_score": 0,
            "ai_reasons": [],
            "dispatcher_feedback": feedback_type,
            "dispatcher_note": note,
            "document_path": document_path,
            "source": source,
            "warning": "No matching decision found in decision_history.jsonl",
        }

    if telegram_message:
        record["telegram_chat_id"] = telegram_message.get("chat", {}).get("id", "")
        record["telegram_message_id"] = telegram_message.get("message_id", "")
        record["telegram_user"] = telegram_message.get("from", {}).get("username", "")

    return record


def save_feedback(
    chat_id,
    load_id,
    feedback_type,
    note,
    source,
    telegram_message=None,
    document_path="",
):
    if feedback_type not in ALLOWED_FEEDBACK_TYPES:
        send_message(
            chat_id,
            f"Unknown feedback type: {feedback_type}\n\nUse /help",
        )
        return

    record = build_feedback_record(
        load_id=load_id,
        feedback_type=feedback_type,
        note=note,
        source=source,
        telegram_message=telegram_message,
        document_path=document_path,
    )

    append_jsonl(DISPATCHER_FEEDBACK_FILE, record)

    warning = record.get("warning", "")

    reply = "✅ Feedback saved.\n\n"
    reply += f"Feedback: {feedback_type}\n"
    reply += f"Load ID / Reference: {load_id}\n"

    if record.get("pickup") or record.get("delivery"):
        reply += f"Load: {record.get('pickup')} → {record.get('delivery')}\n"

    if record.get("ai_decision"):
        reply += f"AI decision: {record.get('ai_decision')}\n"

    if record.get("ai_category"):
        reply += f"AI category: {record.get('ai_category')}\n"

    if document_path:
        reply += f"Document saved: {document_path}\n"

    if note:
        reply += f"Note: {note}\n"

    if warning:
        reply += f"\n⚠️ {warning}"

    send_message(chat_id, reply)


def help_text():
    return (
        "AI Dispatch Feedback Bot\n\n"
        "Main commands:\n"
        "/booked <REF> <note>\n"
        "/called_broker <REF> <note>\n"
        "/sent_to_driver <REF> <note>\n"
        "/driver_rejected <REF> <note>\n"
        "/rate_too_low <REF> <note>\n"
        "/bad_broker <REF> <note>\n"
        "/wrong_equipment <REF> <note>\n"
        "/weight_issue <REF> <note>\n"
        "/time_issue <REF> <note>\n"
        "/covered <REF> <note>\n"
        "/duplicate <REF> <note>\n"
        "/good_option <REF> <note>\n"
        "/not_interested <REF> <note>\n"
        "/other <REF> <note>\n\n"
        "Generic command:\n"
        "/feedback <REF> <feedback_type> <note>\n\n"
        "Rate con PDF:\n"
        "Send PDF with caption:\n"
        "/ratecon <REF> <note>\n\n"
        "Examples:\n"
        "/booked MANUAL-CLEAN-FLATBED-001 booked at posted rate\n"
        "/rate_too_low MANUAL-RATECHECK-001 broker offered only 3200\n"
        "/ratecon MANUAL-CLEAN-FLATBED-001 rate con received"
    )


def chat_allowed(chat_id):
    env = load_env()
    allowed_chat_id = str(env.get("TELEGRAM_CHAT_ID", "") or "").strip()

    if not allowed_chat_id:
        return True

    return str(chat_id) == allowed_chat_id


def handle_text_message(message):
    chat_id = message.get("chat", {}).get("id", "")

    if not chat_allowed(chat_id):
        return

    text = message.get("text", "")
    parsed = parse_command(text)

    if not parsed:
        return

    command = parsed.get("command")

    if command == "help":
        send_message(chat_id, help_text())
        return

    if command == "invalid":
        send_message(chat_id, f"⚠️ {parsed.get('error')}\n\nUse /help")
        return

    if command == "unknown":
        send_message(
            chat_id,
            "I did not understand this message.\n\nUse /help",
        )
        return

    if command == "feedback":
        save_feedback(
            chat_id=chat_id,
            load_id=parsed.get("load_id", ""),
            feedback_type=parsed.get("feedback_type", ""),
            note=parsed.get("note", ""),
            source="telegram_text",
            telegram_message=message,
        )


def handle_document_message(message):
    chat_id = message.get("chat", {}).get("id", "")

    if not chat_allowed(chat_id):
        return

    document = message.get("document", {})
    caption = message.get("caption", "")

    parsed = parse_command(caption)

    if not parsed or parsed.get("command") != "feedback":
        send_message(
            chat_id,
            "PDF received, but I need a caption to connect it to a load.\n\n"
            "Send PDF with caption:\n"
            "/ratecon <REF> <note>\n\n"
            "Example:\n"
            "/ratecon MANUAL-CLEAN-FLATBED-001 rate con received",
        )
        return

    load_id = parsed.get("load_id", "")
    feedback_type = parsed.get("feedback_type", "ratecon_received")
    note = parsed.get("note", "")

    file_id = document.get("file_id", "")
    file_name = document.get("file_name", "ratecon.pdf")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    target_folder = RATECONS_FOLDER / today
    prefix = f"{load_id}_{file_name}"

    document_path = ""

    if file_id:
        try:
            document_path = download_telegram_file(
                file_id=file_id,
                target_folder=target_folder,
                prefix=prefix,
            )
        except Exception as error:
            send_message(
                chat_id,
                f"Failed to download document:\n{error}",
            )
            return

    save_feedback(
        chat_id=chat_id,
        load_id=load_id,
        feedback_type=feedback_type,
        note=note,
        source="telegram_document",
        telegram_message=message,
        document_path=document_path,
    )


def handle_update(update):
    message = update.get("message")

    if not message:
        return

    if "document" in message:
        handle_document_message(message)
        return

    if "text" in message:
        handle_text_message(message)
        return


def run_bot():
    print("Telegram feedback bot started.")
    print("Use Ctrl + C to stop.")
    print("Waiting for messages...")

    state = load_state()
    offset = int(state.get("offset", 0) or 0)

    while True:
        try:
            params = {
                "timeout": 50,
                "offset": offset,
                "allowed_updates": json.dumps(["message"]),
            }

            result = api_get("getUpdates", params)

            if not result.get("ok"):
                print("Telegram getUpdates returned error:")
                print(result)
                time.sleep(5)
                continue

            updates = result.get("result", [])

            for update in updates:
                update_id = update.get("update_id", 0)
                offset = max(offset, update_id + 1)

                handle_update(update)

            state["offset"] = offset
            save_state(state)

        except KeyboardInterrupt:
            print("\nTelegram feedback bot stopped.")
            break

        except Exception as error:
            print("Telegram feedback bot error:")
            print(error)
            time.sleep(5)


if __name__ == "__main__":
    run_bot()