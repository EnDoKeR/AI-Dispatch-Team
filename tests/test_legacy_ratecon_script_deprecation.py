import importlib
import io
import unittest
from contextlib import redirect_stdout


class LegacyRateConScriptDeprecationTests(unittest.TestCase):
    def test_import_ratecon_is_blocked_by_default(self):
        module = importlib.import_module("scripts.import_ratecon")
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = module.main([])

        text = output.getvalue()
        self.assertEqual(exit_code, 2)
        self.assertIn("DEPRECATED LEGACY PROTOTYPE", text)
        self.assertIn("No PDF was read", text)
        self.assertIn("no Google Sheet was written", text)

    def test_read_ratecon_is_blocked_by_default(self):
        module = importlib.import_module("scripts.read_ratecon")
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = module.main([])

        text = output.getvalue()
        self.assertEqual(exit_code, 2)
        self.assertIn("DEPRECATED LEGACY PROTOTYPE", text)
        self.assertIn("No PDF was read", text)
        self.assertIn("no extracted values were printed", text)

    def test_legacy_modules_import_without_optional_integrations(self):
        import_ratecon = importlib.import_module("scripts.import_ratecon")
        read_ratecon = importlib.import_module("scripts.read_ratecon")

        self.assertTrue(hasattr(import_ratecon, "main"))
        self.assertTrue(hasattr(read_ratecon, "main"))


if __name__ == "__main__":
    unittest.main()
