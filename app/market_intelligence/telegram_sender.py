import json
import urllib.parse
import urllib.request

from app.market_intelligence.telegram_outbox_logger import (
    log_outgoing_telegram_message,
)


ENV_FILE = ".env"


def load_env():
    values = {}

    try:
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

    except FileNotFoundError:
        print(".env file not found")

    return values


def send_telegram_message(text, reply_markup=None):
    env = load_env()

    token = env.get("TELEGRAM_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_CHAT_ID")

    if not token:
        print("TELEGRAM_BOT_TOKEN is missing in .env")

        log_outgoing_telegram_message(
            text=text,
            success=False,
            telegram_response=None,
            error_text="TELEGRAM_BOT_TOKEN is missing in .env",
        )

        return False

    if not chat_id:
        print("TELEGRAM_CHAT_ID is missing in .env")

        log_outgoing_telegram_message(
            text=text,
            success=False,
            telegram_response=None,
            error_text="TELEGRAM_CHAT_ID is missing in .env",
        )

        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": "true",
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)

    encoded_data = urllib.parse.urlencode(data).encode("utf-8")

    try:
        request = urllib.request.Request(
            url,
            data=encoded_data,
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            response_text = response.read().decode("utf-8")
            result = json.loads(response_text)

    except Exception as error:
        print("Telegram send failed:")
        print(error)

        log_outgoing_telegram_message(
            text=text,
            success=False,
            telegram_response=None,
            error_text=str(error),
        )

        return False

    if result.get("ok"):
        print("Telegram message sent РІСљвЂ¦")

        log_outgoing_telegram_message(
            text=text,
            success=True,
            telegram_response=result,
            error_text="",
        )

        return True

    print("Telegram API returned error:")
    print(result)

    log_outgoing_telegram_message(
        text=text,
        success=False,
        telegram_response=result,
        error_text=str(result),
    )

    return False
