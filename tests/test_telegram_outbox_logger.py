import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.market_intelligence import telegram_outbox_logger
from app.market_intelligence.telegram_outbox_logger import (
    extract_telegram_message_id,
    infer_message_type,
    log_outgoing_telegram_message,
    parse_broker,
    parse_category,
    parse_driver_name,
    parse_lane,
    parse_mc,
    parse_rate,
    parse_reference_id,
)


MOJIBAKE_DASH = "\u0432\u0402\u201d"
MOJIBAKE_ARROW = "\u0432\u2020\u2019"


def opportunity_message():
    return "\n".join(
        [
            f"LOAD OPPORTUNITY #1 {MOJIBAKE_DASH} Alex",
            "",
            f"Dallas, TX {MOJIBAKE_ARROW} Houston, TX",
            "",
            "Rate: $2200",
            "Broker / Contact:",
            "Broker: Test Broker",
            "MC: 123456",
            "Reference ID: REF-123",
        ]
    )


class TestTelegramOutboxLogger(unittest.TestCase):
    def test_infer_message_type_from_current_message_text(self):
        examples = {
            "MARKET SNAPSHOT\nDriver: Alex": "MARKET_SNAPSHOT",
            "LOAD OPPORTUNITY #1": "LOAD_OPPORTUNITY",
            "REVIEW ONCE - RATE CHECK": "REVIEW_ONCE",
            "SEARCH HEALTH CHECK": "SEARCH_HEALTH_CHECK",
            "LOAD WITH RELOAD PLAN #1": "RELOAD_CHAIN",
            "plain text": "UNKNOWN",
        }

        for text, expected in examples.items():
            with self.subTest(text=text):
                self.assertEqual(infer_message_type(text), expected)

    def test_parses_current_load_opportunity_message_fields(self):
        text = opportunity_message()

        self.assertEqual(parse_driver_name(text), "Alex")
        self.assertEqual(parse_lane(text), ("Dallas, TX", "Houston, TX"))
        self.assertEqual(parse_rate(text), "2200")
        self.assertEqual(parse_broker(text), "Test Broker")
        self.assertEqual(parse_mc(text), "123456")
        self.assertEqual(parse_reference_id(text), "REF-123")
        self.assertEqual(parse_category(text), "LOAD OPPORTUNITY")

    def test_review_once_category_comes_from_first_line(self):
        text = (
            f"REVIEW ONCE {MOJIBAKE_DASH} RATE CHECK {MOJIBAKE_DASH} Alex #1\n\n"
            f"Dallas, TX {MOJIBAKE_ARROW} Houston, TX"
        )

        self.assertEqual(parse_driver_name(text), "Alex")
        self.assertEqual(parse_category(text), "RATE CHECK")

    def test_lane_parser_skips_google_map_lines(self):
        text = "\n".join(
            [
                f"Google Maps {MOJIBAKE_ARROW} ignore this",
                f"Dallas, TX {MOJIBAKE_ARROW} Houston, TX",
            ]
        )

        self.assertEqual(parse_lane(text), ("Dallas, TX", "Houston, TX"))

    def test_extract_telegram_message_id_handles_missing_or_invalid_response(self):
        self.assertEqual(extract_telegram_message_id(None), "")
        self.assertEqual(extract_telegram_message_id({"ok": False}), "")
        self.assertEqual(
            extract_telegram_message_id({"result": {"message_id": 77}}),
            77,
        )

    def test_log_outgoing_telegram_message_writes_structured_outbox_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outbox_file = Path(temp_dir) / "telegram_outbox.jsonl"

            with patch.object(
                telegram_outbox_logger,
                "TELEGRAM_OUTBOX_FILE",
                outbox_file,
            ):
                with patch.object(
                    telegram_outbox_logger,
                    "utc_now_iso",
                    return_value="2026-05-29T12:00:00+00:00",
                ):
                    record = log_outgoing_telegram_message(
                        text=opportunity_message(),
                        success=True,
                        telegram_response={"result": {"message_id": 99}},
                    )

            saved_records = [
                json.loads(line)
                for line in outbox_file.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(len(saved_records), 1)
        self.assertEqual(saved_records[0], record)
        self.assertEqual(record["timestamp_utc"], "2026-05-29T12:00:00+00:00")
        self.assertEqual(record["message_type"], "LOAD_OPPORTUNITY")
        self.assertEqual(record["category"], "LOAD OPPORTUNITY")
        self.assertEqual(record["driver_name"], "Alex")
        self.assertEqual(record["pickup"], "Dallas, TX")
        self.assertEqual(record["delivery"], "Houston, TX")
        self.assertEqual(record["rate"], "2200")
        self.assertEqual(record["broker"], "Test Broker")
        self.assertEqual(record["broker_mc"], "123456")
        self.assertEqual(record["reference_id"], "REF-123")
        self.assertTrue(record["send_success"])
        self.assertEqual(record["telegram_message_id"], 99)
        self.assertEqual(record["error_text"], "")

    def test_log_outgoing_telegram_message_prefers_metadata_over_text_parsing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outbox_file = Path(temp_dir) / "telegram_outbox.jsonl"

            with patch.object(
                telegram_outbox_logger,
                "TELEGRAM_OUTBOX_FILE",
                outbox_file,
            ):
                record = log_outgoing_telegram_message(
                    text="text shape can change without breaking metadata",
                    success=True,
                    telegram_response={"result": {"message_id": 100}},
                    metadata={
                        "message_type": "LOAD_OPPORTUNITY",
                        "category": "LOAD OPPORTUNITY",
                        "driver_name": "Alex",
                        "pickup": "Dallas, TX",
                        "delivery": "Houston, TX",
                        "rate": 2200,
                        "broker": "Structured Broker",
                        "broker_mc": "222333",
                        "reference_id": "REF-META",
                    },
                )

        self.assertEqual(record["message_type"], "LOAD_OPPORTUNITY")
        self.assertEqual(record["category"], "LOAD OPPORTUNITY")
        self.assertEqual(record["driver_name"], "Alex")
        self.assertEqual(record["pickup"], "Dallas, TX")
        self.assertEqual(record["delivery"], "Houston, TX")
        self.assertEqual(record["rate"], 2200)
        self.assertEqual(record["broker"], "Structured Broker")
        self.assertEqual(record["broker_mc"], "222333")
        self.assertEqual(record["reference_id"], "REF-META")
        self.assertEqual(record["telegram_message_id"], 100)
        self.assertEqual(record["text"], "text shape can change without breaking metadata")

    def test_log_outgoing_telegram_message_falls_back_to_text_for_missing_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outbox_file = Path(temp_dir) / "telegram_outbox.jsonl"

            with patch.object(
                telegram_outbox_logger,
                "TELEGRAM_OUTBOX_FILE",
                outbox_file,
            ):
                record = log_outgoing_telegram_message(
                    text=opportunity_message(),
                    success=True,
                    telegram_response=None,
                    metadata={
                        "driver_name": "Structured Alex",
                        "rate": 2300,
                    },
                )

        self.assertEqual(record["message_type"], "LOAD_OPPORTUNITY")
        self.assertEqual(record["category"], "LOAD OPPORTUNITY")
        self.assertEqual(record["driver_name"], "Structured Alex")
        self.assertEqual(record["pickup"], "Dallas, TX")
        self.assertEqual(record["delivery"], "Houston, TX")
        self.assertEqual(record["rate"], 2300)
        self.assertEqual(record["broker"], "Test Broker")
        self.assertEqual(record["broker_mc"], "123456")
        self.assertEqual(record["reference_id"], "REF-123")


if __name__ == "__main__":
    unittest.main()
