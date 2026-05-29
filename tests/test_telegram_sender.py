import json
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

from app.market_intelligence.telegram_sender import (
    load_env,
    send_telegram_message,
)
from app.market_intelligence import telegram_notifier
from app.market_intelligence import telegram_sender


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class TestTelegramSender(unittest.TestCase):
    def write_env_file(self, lines):
        temp_dir = tempfile.TemporaryDirectory()
        env_file = Path(temp_dir.name) / ".env"
        env_file.write_text("\n".join(lines), encoding="utf-8")
        self.addCleanup(temp_dir.cleanup)
        return str(env_file)

    def send_quietly(self, *args, **kwargs):
        with patch("builtins.print"):
            return send_telegram_message(*args, **kwargs)

    def test_load_env_reads_key_value_lines_and_skips_noise(self):
        env_file = self.write_env_file(
            [
                "# comment",
                "",
                "TELEGRAM_BOT_TOKEN = token-123",
                "ignored line",
                "TELEGRAM_CHAT_ID=chat-456",
            ]
        )

        with patch("app.market_intelligence.telegram_sender.ENV_FILE", env_file):
            self.assertEqual(
                load_env(),
                {
                    "TELEGRAM_BOT_TOKEN": "token-123",
                    "TELEGRAM_CHAT_ID": "chat-456",
                },
            )

    def test_notifier_keeps_sender_helpers_as_backward_compatible_imports(self):
        self.assertIs(telegram_notifier.load_env, telegram_sender.load_env)
        self.assertIs(
            telegram_notifier.send_telegram_message,
            telegram_sender.send_telegram_message,
        )

    def test_send_telegram_message_logs_missing_token(self):
        env_file = self.write_env_file(["TELEGRAM_CHAT_ID=chat-456"])

        with patch("app.market_intelligence.telegram_sender.ENV_FILE", env_file):
            with patch(
                "app.market_intelligence.telegram_sender.log_outgoing_telegram_message"
            ) as log_message:
                self.assertFalse(self.send_quietly("Hello"))

        log_message.assert_called_once_with(
            text="Hello",
            success=False,
            telegram_response=None,
            error_text="TELEGRAM_BOT_TOKEN is missing in .env",
        )

    def test_send_telegram_message_logs_missing_token_with_metadata(self):
        env_file = self.write_env_file(["TELEGRAM_CHAT_ID=chat-456"])
        metadata = {"message_type": "LOAD_OPPORTUNITY", "driver_name": "Alex"}

        with patch("app.market_intelligence.telegram_sender.ENV_FILE", env_file):
            with patch(
                "app.market_intelligence.telegram_sender.log_outgoing_telegram_message"
            ) as log_message:
                self.assertFalse(self.send_quietly("Hello", metadata=metadata))

        log_message.assert_called_once_with(
            text="Hello",
            success=False,
            telegram_response=None,
            error_text="TELEGRAM_BOT_TOKEN is missing in .env",
            metadata=metadata,
        )

    def test_send_telegram_message_logs_missing_chat_id(self):
        env_file = self.write_env_file(["TELEGRAM_BOT_TOKEN=token-123"])

        with patch("app.market_intelligence.telegram_sender.ENV_FILE", env_file):
            with patch(
                "app.market_intelligence.telegram_sender.log_outgoing_telegram_message"
            ) as log_message:
                self.assertFalse(self.send_quietly("Hello"))

        log_message.assert_called_once_with(
            text="Hello",
            success=False,
            telegram_response=None,
            error_text="TELEGRAM_CHAT_ID is missing in .env",
        )

    def test_send_telegram_message_logs_missing_chat_id_with_metadata(self):
        env_file = self.write_env_file(["TELEGRAM_BOT_TOKEN=token-123"])
        metadata = {"message_type": "REVIEW_ONCE", "driver_name": "Alex"}

        with patch("app.market_intelligence.telegram_sender.ENV_FILE", env_file):
            with patch(
                "app.market_intelligence.telegram_sender.log_outgoing_telegram_message"
            ) as log_message:
                self.assertFalse(self.send_quietly("Hello", metadata=metadata))

        log_message.assert_called_once_with(
            text="Hello",
            success=False,
            telegram_response=None,
            error_text="TELEGRAM_CHAT_ID is missing in .env",
            metadata=metadata,
        )

    def test_send_telegram_message_sends_request_and_logs_success(self):
        env_file = self.write_env_file(
            [
                "TELEGRAM_BOT_TOKEN=token-123",
                "TELEGRAM_CHAT_ID=chat-456",
            ]
        )
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse({"ok": True, "result": {"message_id": 99}})

        with patch("app.market_intelligence.telegram_sender.ENV_FILE", env_file):
            with patch(
                "app.market_intelligence.telegram_sender.urllib.request.urlopen",
                side_effect=fake_urlopen,
            ):
                with patch(
                    "app.market_intelligence.telegram_sender.log_outgoing_telegram_message"
                ) as log_message:
                    self.assertTrue(
                        self.send_quietly(
                            "Hello",
                            reply_markup={"inline_keyboard": []},
                        )
                    )

        self.assertEqual(captured["timeout"], 20)
        self.assertEqual(
            captured["request"].full_url,
            "https://api.telegram.org/bottoken-123/sendMessage",
        )
        parsed_data = urllib.parse.parse_qs(captured["request"].data.decode("utf-8"))
        self.assertEqual(parsed_data["chat_id"], ["chat-456"])
        self.assertEqual(parsed_data["text"], ["Hello"])
        self.assertEqual(parsed_data["disable_web_page_preview"], ["true"])
        self.assertEqual(
            json.loads(parsed_data["reply_markup"][0]),
            {"inline_keyboard": []},
        )
        log_message.assert_called_once_with(
            text="Hello",
            success=True,
            telegram_response={"ok": True, "result": {"message_id": 99}},
            error_text="",
        )

    def test_send_telegram_message_sends_request_and_logs_success_with_metadata(self):
        env_file = self.write_env_file(
            [
                "TELEGRAM_BOT_TOKEN=token-123",
                "TELEGRAM_CHAT_ID=chat-456",
            ]
        )
        captured = {}
        metadata = {
            "message_type": "LOAD_OPPORTUNITY",
            "driver_name": "Alex",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
        }
        original_metadata = dict(metadata)

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse({"ok": True, "result": {"message_id": 99}})

        with patch("app.market_intelligence.telegram_sender.ENV_FILE", env_file):
            with patch(
                "app.market_intelligence.telegram_sender.urllib.request.urlopen",
                side_effect=fake_urlopen,
            ):
                with patch(
                    "app.market_intelligence.telegram_sender.log_outgoing_telegram_message"
                ) as log_message:
                    self.assertTrue(
                        self.send_quietly(
                            "Hello",
                            reply_markup={"inline_keyboard": []},
                            metadata=metadata,
                        )
                    )

        parsed_data = urllib.parse.parse_qs(captured["request"].data.decode("utf-8"))
        self.assertEqual(
            json.loads(parsed_data["reply_markup"][0]),
            {"inline_keyboard": []},
        )
        self.assertEqual(metadata, original_metadata)
        log_message.assert_called_once_with(
            text="Hello",
            success=True,
            telegram_response={"ok": True, "result": {"message_id": 99}},
            error_text="",
            metadata=metadata,
        )

    def test_send_telegram_message_logs_api_error(self):
        env_file = self.write_env_file(
            [
                "TELEGRAM_BOT_TOKEN=token-123",
                "TELEGRAM_CHAT_ID=chat-456",
            ]
        )
        response = {"ok": False, "description": "Bad Request"}

        with patch("app.market_intelligence.telegram_sender.ENV_FILE", env_file):
            with patch(
                "app.market_intelligence.telegram_sender.urllib.request.urlopen",
                return_value=FakeResponse(response),
            ):
                with patch(
                    "app.market_intelligence.telegram_sender.log_outgoing_telegram_message"
                ) as log_message:
                    self.assertFalse(self.send_quietly("Hello"))

        log_message.assert_called_once_with(
            text="Hello",
            success=False,
            telegram_response=response,
            error_text=str(response),
        )

    def test_send_telegram_message_logs_api_error_with_metadata(self):
        env_file = self.write_env_file(
            [
                "TELEGRAM_BOT_TOKEN=token-123",
                "TELEGRAM_CHAT_ID=chat-456",
            ]
        )
        response = {"ok": False, "description": "Bad Request"}
        metadata = {"message_type": "SEARCH_HEALTH_CHECK", "driver_name": "Alex"}

        with patch("app.market_intelligence.telegram_sender.ENV_FILE", env_file):
            with patch(
                "app.market_intelligence.telegram_sender.urllib.request.urlopen",
                return_value=FakeResponse(response),
            ):
                with patch(
                    "app.market_intelligence.telegram_sender.log_outgoing_telegram_message"
                ) as log_message:
                    self.assertFalse(self.send_quietly("Hello", metadata=metadata))

        log_message.assert_called_once_with(
            text="Hello",
            success=False,
            telegram_response=response,
            error_text=str(response),
            metadata=metadata,
        )

    def test_send_telegram_message_logs_transport_exception(self):
        env_file = self.write_env_file(
            [
                "TELEGRAM_BOT_TOKEN=token-123",
                "TELEGRAM_CHAT_ID=chat-456",
            ]
        )

        with patch("app.market_intelligence.telegram_sender.ENV_FILE", env_file):
            with patch(
                "app.market_intelligence.telegram_sender.urllib.request.urlopen",
                side_effect=RuntimeError("network down"),
            ):
                with patch(
                    "app.market_intelligence.telegram_sender.log_outgoing_telegram_message"
                ) as log_message:
                    self.assertFalse(self.send_quietly("Hello"))

        log_message.assert_called_once_with(
            text="Hello",
            success=False,
            telegram_response=None,
            error_text="network down",
        )

    def test_send_telegram_message_logs_transport_exception_with_metadata(self):
        env_file = self.write_env_file(
            [
                "TELEGRAM_BOT_TOKEN=token-123",
                "TELEGRAM_CHAT_ID=chat-456",
            ]
        )
        metadata = {"message_type": "MARKET_SNAPSHOT", "driver_name": "Alex"}

        with patch("app.market_intelligence.telegram_sender.ENV_FILE", env_file):
            with patch(
                "app.market_intelligence.telegram_sender.urllib.request.urlopen",
                side_effect=RuntimeError("network down"),
            ):
                with patch(
                    "app.market_intelligence.telegram_sender.log_outgoing_telegram_message"
                ) as log_message:
                    self.assertFalse(self.send_quietly("Hello", metadata=metadata))

        log_message.assert_called_once_with(
            text="Hello",
            success=False,
            telegram_response=None,
            error_text="network down",
            metadata=metadata,
        )


if __name__ == "__main__":
    unittest.main()
