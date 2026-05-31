import base64
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts import import_google_service_account_local as import_script


def _fake_service_account(email=None, include_private_key=True):
    payload = {
        "type": "service_account",
        "project_id": "fake-project",
        "private_key_id": "fake-key-id",
        "client_email": email or import_script.EXPECTED_SERVICE_ACCOUNT_EMAIL,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    if include_private_key:
        payload["private_key"] = (
            "-----BEGIN PRIVATE KEY-----\nFAKE_TEST_KEY\n-----END PRIVATE KEY-----\n"
        )
    return json.dumps(payload)


class ImportGoogleServiceAccountLocalTests(unittest.TestCase):
    def _patched_paths(self, root):
        local_private = Path(root) / ".local_private"
        return patch.multiple(
            import_script,
            REPO_ROOT=Path(root),
            LOCAL_PRIVATE_DIR=local_private,
            DEFAULT_OUTPUT=local_private / "google-service-account.json",
        )

    def test_valid_fake_json_writes_to_temp_local_private_without_printing_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.json"
            source.write_text(_fake_service_account(), encoding="utf-8")
            output = root / ".local_private" / "google-service-account.json"
            stdout = io.StringIO()

            with self._patched_paths(root), redirect_stdout(stdout):
                exit_code = import_script.main(
                    [
                        "--from-file",
                        str(source),
                        "--output",
                        str(output),
                    ]
                )
            written = json.loads(output.read_text(encoding="utf-8"))
            console = stdout.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            written["client_email"],
            import_script.EXPECTED_SERVICE_ACCOUNT_EMAIL,
        )
        self.assertIn("credential_written: yes", console)
        self.assertIn("client_email_matches: yes", console)
        self.assertNotIn("FAKE_TEST_KEY", console)
        self.assertNotIn(str(output), console)

    def test_invalid_one_line_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stderr = io.StringIO()
            with self._patched_paths(root), redirect_stderr(stderr), patch(
                "sys.stdin",
                io.StringIO("short-key-like-string"),
            ):
                exit_code = import_script.main(
                    [
                        "--from-stdin",
                        "--output",
                        str(root / ".local_private" / "google-service-account.json"),
                    ]
                )

        self.assertEqual(exit_code, 2)
        self.assertIn("Expected full Google service account JSON", stderr.getvalue())

    def test_missing_private_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self._patched_paths(root):
                with self.assertRaises(import_script.ServiceAccountImportError) as ctx:
                    import_script.write_local_service_account_json(
                        _fake_service_account(include_private_key=False),
                        output=root / ".local_private" / "google-service-account.json",
                    )

        self.assertIn("missing required fields", str(ctx.exception))

    def test_email_mismatch_fails_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self._patched_paths(root):
                with self.assertRaises(import_script.ServiceAccountImportError) as ctx:
                    import_script.write_local_service_account_json(
                        _fake_service_account(email="other@example.com"),
                        output=root / ".local_private" / "google-service-account.json",
                    )

        self.assertIn("email does not match", str(ctx.exception))

    def test_refuses_output_outside_local_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self._patched_paths(root):
                with self.assertRaises(import_script.ServiceAccountImportError) as ctx:
                    import_script.write_local_service_account_json(
                        _fake_service_account(),
                        output=root / "outside.json",
                    )

        self.assertIn(".local_private", str(ctx.exception))

    def test_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / ".local_private" / "google-service-account.json"
            output.parent.mkdir(parents=True)
            output.write_text("{}", encoding="utf-8")
            with self._patched_paths(root):
                with self.assertRaises(import_script.ServiceAccountImportError) as ctx:
                    import_script.write_local_service_account_json(
                        _fake_service_account(),
                        output=output,
                    )

        self.assertIn("already exists", str(ctx.exception))

    def test_base64_env_payload_is_supported(self):
        payload = _fake_service_account()
        encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")

        with patch.dict(
            os.environ,
            {"AI_DISPATCH_GOOGLE_SERVICE_ACCOUNT_JSON_B64": encoded},
            clear=True,
        ):
            args = type("Args", (), {"from_file": "", "from_stdin": False})()
            loaded = import_script._payload_from_args(args)

        self.assertEqual(json.loads(loaded)["type"], "service_account")


if __name__ == "__main__":
    unittest.main()
