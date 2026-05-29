import ast
import unittest
from pathlib import Path


INTAKE_PACKAGE = Path("app/market_intelligence/intake")

FORBIDDEN_IMPORT_PREFIXES = [
    "app.load_intake",
    "app.market_intelligence.dispatch_case",
    "app.market_intelligence.case_event_builder",
    "app.market_intelligence.event_logger",
    "app.market_intelligence.telegram_notifier",
    "app.market_intelligence.telegram_sender",
    "gspread",
    "google.oauth",
    "googleapiclient",
    "imaplib",
    "smtplib",
    "pypdf",
    "pytesseract",
    "googlemaps",
    "apscheduler",
    "threading",
]

FORBIDDEN_SOURCE_TERMS = [
    "telegram_sender",
    "telegram_notifier",
    "send_telegram_message",
    "case_event_builder",
    "event_logger",
    "gspread",
    "google.oauth",
    "googleapiclient",
    "gmail",
    "imaplib",
    "smtplib",
    "pypdf",
    "pdfreader",
    "pytesseract",
    "ocr",
    "dat_api",
    "googlemaps",
    "apscheduler",
    "scheduler",
    "threading",
    "app.load_intake",
]

ALLOWED_SOURCE_TERMS_BY_FILE = {
    "pdf_text_extraction.py": {
        "pypdf",
        "pdfreader",
    },
}


def intake_python_files():
    return sorted(INTAKE_PACKAGE.glob("*.py"))


def imported_module_names(source):
    tree = ast.parse(source)
    names = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)

        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names.append(module)

            for alias in node.names:
                if module:
                    names.append(f"{module}.{alias.name}")
                else:
                    names.append(alias.name)

    return names


class IntakePackageBoundaryTests(unittest.TestCase):
    def test_intake_package_exists(self):
        self.assertTrue(INTAKE_PACKAGE.exists())
        self.assertTrue((INTAKE_PACKAGE / "__init__.py").exists())

    def test_intake_package_does_not_import_forbidden_layers(self):
        for path in intake_python_files():
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8")
                imports = imported_module_names(source)

                for imported_name in imports:
                    for forbidden_prefix in FORBIDDEN_IMPORT_PREFIXES:
                        self.assertFalse(
                            imported_name == forbidden_prefix
                            or imported_name.startswith(forbidden_prefix + "."),
                            f"{path} imports forbidden dependency {imported_name}",
                        )

    def test_intake_package_source_has_no_forbidden_runtime_hooks(self):
        for path in intake_python_files():
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8").lower()
                allowed_terms = ALLOWED_SOURCE_TERMS_BY_FILE.get(path.name, set())

                for term in FORBIDDEN_SOURCE_TERMS:
                    if term in allowed_terms:
                        continue
                    self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
