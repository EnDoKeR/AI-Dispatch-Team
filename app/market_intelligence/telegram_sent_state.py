from pathlib import Path

from app.market_intelligence.telegram_duplicate_keys import (
    load_duplicate_key,
    search_health_key,
)


SENT_FILE = "data/sent_telegram_loads.txt"
SENT_REVIEW_ONCE_FILE = "data/sent_review_once_loads.txt"
SENT_HEALTH_FILE = "data/sent_search_health_alerts.txt"
SENT_SUMMARY_FILE = "data/sent_market_summaries.txt"


def get_lines(file_path):
    path = Path(file_path)

    if not path.exists():
        return set()

    with open(path, "r", encoding="utf-8") as file:
        return set(file.read().splitlines())


def save_line(file_path, value):
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a", encoding="utf-8") as file:
        file.write(value + "\n")


def get_sent_loads():
    return get_lines(SENT_FILE)


def save_sent_load(load, search_request):
    save_line(
        SENT_FILE,
        load_duplicate_key(
            load,
            driver_name=search_request.driver_name,
        ),
    )


def get_sent_review_once_loads():
    return get_lines(SENT_REVIEW_ONCE_FILE)


def save_sent_review_once_load(load, search_request):
    save_line(
        SENT_REVIEW_ONCE_FILE,
        load_duplicate_key(
            load,
            driver_name=search_request.driver_name,
        ),
    )


def get_sent_health_alerts():
    return get_lines(SENT_HEALTH_FILE)


def save_sent_health_alert(search_request):
    save_line(SENT_HEALTH_FILE, search_health_key(search_request))


def get_sent_summaries():
    return get_lines(SENT_SUMMARY_FILE)


def save_sent_summary(summary_key):
    save_line(SENT_SUMMARY_FILE, summary_key)
