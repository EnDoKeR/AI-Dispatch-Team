import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
MARKET_INTELLIGENCE = ROOT / "app" / "market_intelligence"
INTAKE_PACKAGE = MARKET_INTELLIGENCE / "intake"
DECISION_ENGINE_PACKAGE = MARKET_INTELLIGENCE / "decision_engine"
DOCUMENT_AI_PACKAGE = APP / "document_ai"
SCRIPTS = ROOT / "scripts"


def python_files(root):
    return sorted(
        path
        for path in root.glob("*.py")
        if path.name != "__init__.py"
    )


def parse_file(path):
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def imported_modules(path):
    tree = parse_file(path)
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)

        if isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return imports


def string_literals(path):
    tree = parse_file(path)
    values = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.append(node.value)

    return values


def assert_no_import_prefix(test_case, path, forbidden_prefixes):
    imports = imported_modules(path)

    for imported_name in imports:
        for forbidden_prefix in forbidden_prefixes:
            test_case.assertFalse(
                imported_name == forbidden_prefix
                or imported_name.startswith(forbidden_prefix + "."),
                f"{path} imports forbidden boundary dependency {imported_name}",
            )


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_decision_engine_does_not_import_adapters_or_external_extractors(self):
        forbidden_prefixes = [
            "app.market_intelligence.telegram",
            "gspread",
            "google.oauth",
            "googleapiclient",
            "imaplib",
            "smtplib",
            "pypdf",
            "pdfplumber",
            "fitz",
            "googlemaps",
        ]

        for path in python_files(DECISION_ENGINE_PACKAGE):
            with self.subTest(path=str(path)):
                assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_intake_and_ratecon_modules_do_not_import_decision_or_output_layers(self):
        forbidden_prefixes = [
            "app.market_intelligence.decision_engine",
            "app.market_intelligence.dispatch_case",
            "app.market_intelligence.case_event_builder",
            "app.market_intelligence.event_logger",
            "app.market_intelligence.telegram",
            "gspread",
            "google.oauth",
            "googleapiclient",
            "imaplib",
            "smtplib",
            "googlemaps",
        ]

        target_files = python_files(INTAKE_PACKAGE) + sorted(
            MARKET_INTELLIGENCE.glob("intake_*.py")
        )

        for path in target_files:
            with self.subTest(path=str(path)):
                assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_intake_and_ratecon_modules_do_not_emit_dispatch_recommendations(self):
        forbidden_literals = {
            "ACCEPT",
            "REJECT",
            "MATCH",
            "REVIEW_ONCE",
            "BLOCK",
        }

        target_files = python_files(INTAKE_PACKAGE) + sorted(
            MARKET_INTELLIGENCE.glob("intake_*.py")
        )

        for path in target_files:
            literals = set(string_literals(path))

            for forbidden_literal in forbidden_literals:
                with self.subTest(path=str(path), literal=forbidden_literal):
                    self.assertNotIn(
                        forbidden_literal,
                        literals,
                        f"{path} emits dispatch recommendation literal {forbidden_literal}",
                    )

    def test_repositories_do_not_import_decision_or_adapter_layers(self):
        forbidden_prefixes = [
            "app.market_intelligence.decision_engine",
            "app.market_intelligence.telegram",
            "app.market_intelligence.case_event_builder",
            "app.market_intelligence.event_logger",
            "gspread",
            "google.oauth",
            "googleapiclient",
            "googlemaps",
        ]
        repository_files = [
            INTAKE_PACKAGE / "repository.py",
            MARKET_INTELLIGENCE / "intake_record_repository.py",
            MARKET_INTELLIGENCE / "reload_watch_repository.py",
            MARKET_INTELLIGENCE / "sqlite_memory_repository.py",
        ]

        for path in repository_files:
            with self.subTest(path=str(path)):
                assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_telegram_presentation_modules_do_not_import_core_decision_or_case_layers(self):
        forbidden_prefixes = [
            "app.market_intelligence.decision_engine",
            "app.market_intelligence.dispatch_case",
            "app.market_intelligence.case_event_builder",
            "app.market_intelligence.event_logger",
            "app.market_intelligence.notes_parser",
            "app.market_intelligence.intake",
            "app.market_intelligence.sqlite_memory",
            "app.market_intelligence.market_weight_rules",
            "app.market_intelligence.market_payment_risk_rules",
            "app.market_intelligence.market_quality_rules",
            "app.market_intelligence.market_conestoga_rules",
            "app.market_intelligence.market_od_permit_rules",
        ]
        presentation_files = [
            MARKET_INTELLIGENCE / "telegram_opportunity_formatter.py",
            MARKET_INTELLIGENCE / "telegram_review_once_formatter.py",
            MARKET_INTELLIGENCE / "telegram_chain_formatter.py",
            MARKET_INTELLIGENCE / "telegram_market_summary_formatter.py",
            MARKET_INTELLIGENCE / "telegram_search_health_formatter.py",
            MARKET_INTELLIGENCE / "telegram_watch_formatter.py",
            MARKET_INTELLIGENCE / "telegram_text_helpers.py",
            MARKET_INTELLIGENCE / "telegram_duplicate_keys.py",
            MARKET_INTELLIGENCE / "telegram_load_metadata.py",
            MARKET_INTELLIGENCE / "telegram_summary_metadata.py",
            MARKET_INTELLIGENCE / "telegram_search_health_metadata.py",
        ]

        for path in presentation_files:
            with self.subTest(path=str(path)):
                assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_core_app_does_not_require_future_dat_api_adapter(self):
        for path in MARKET_INTELLIGENCE.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue

            source = path.read_text(encoding="utf-8-sig").lower()

            with self.subTest(path=str(path)):
                self.assertNotIn("dat_api", source)

    def test_document_ai_modules_do_not_import_business_or_output_layers(self):
        forbidden_prefixes = [
            "app.market_intelligence.decision_engine",
            "app.market_intelligence.dispatch_case",
            "app.market_intelligence.case_event_builder",
            "app.market_intelligence.event_logger",
            "app.market_intelligence.telegram",
            "gspread",
            "google.oauth",
            "googleapiclient",
            "googlemaps",
            "openai",
            "pytesseract",
            "easyocr",
            "smtplib",
            "imaplib",
        ]

        for path in python_files(DOCUMENT_AI_PACKAGE):
            with self.subTest(path=str(path)):
                assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_document_ai_modules_do_not_emit_dispatch_recommendations(self):
        forbidden_literals = {
            "ACCEPT",
            "REJECT",
            "MATCH",
            "REVIEW_ONCE",
            "BLOCK",
        }

        for path in python_files(DOCUMENT_AI_PACKAGE):
            literals = set(string_literals(path))

            for forbidden_literal in forbidden_literals:
                with self.subTest(path=str(path), literal=forbidden_literal):
                    self.assertNotIn(
                        forbidden_literal,
                        literals,
                        f"{path} emits dispatch recommendation literal {forbidden_literal}",
                    )

    def test_fake_pdf_triage_cli_does_not_import_private_ratecon_flows(self):
        forbidden_prefixes = [
            "scripts.run_private_ratecon_pdf_dry_run",
            "scripts.run_private_ratecon_redacted_diagnostics",
            "scripts.run_private_ratecon_layout_diagnostics",
            "scripts.export_private_ratecon_value_review_csv",
            "app.market_intelligence.intake.ratecon_pdf_dry_run",
            "app.market_intelligence.intake.pdf_text_extraction",
            "app.market_intelligence.dispatch_case",
            "app.market_intelligence.case_event_builder",
            "app.market_intelligence.telegram",
        ]
        path = SCRIPTS / "run_fake_pdf_triage_dry_run.py"

        assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_ratecon_candidate_modules_do_not_import_decision_output_or_heavy_extractors(self):
        forbidden_prefixes = [
            "app.market_intelligence.decision_engine",
            "app.market_intelligence.dispatch_case",
            "app.market_intelligence.case_event_builder",
            "app.market_intelligence.event_logger",
            "app.market_intelligence.telegram",
            "pypdf",
            "pdfplumber",
            "fitz",
            "openai",
            "pytesseract",
            "easyocr",
            "requests",
            "gspread",
            "google.oauth",
            "googleapiclient",
        ]
        candidate_files = [
            DOCUMENT_AI_PACKAGE / "ratecon_candidates.py",
            DOCUMENT_AI_PACKAGE / "ratecon_candidate_generators.py",
            DOCUMENT_AI_PACKAGE / "ratecon_candidate_extraction.py",
            DOCUMENT_AI_PACKAGE / "ratecon_field_resolution.py",
            DOCUMENT_AI_PACKAGE / "ratecon_intake_draft.py",
        ]

        for path in candidate_files:
            with self.subTest(path=str(path)):
                assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_fake_candidate_extraction_cli_does_not_import_private_ratecon_flows(self):
        forbidden_prefixes = [
            "scripts.run_private_ratecon_pdf_dry_run",
            "scripts.run_private_ratecon_redacted_diagnostics",
            "scripts.run_private_ratecon_layout_diagnostics",
            "scripts.export_private_ratecon_value_review_csv",
            "app.market_intelligence.intake.ratecon_pdf_dry_run",
            "app.market_intelligence.intake.pdf_text_extraction",
            "app.market_intelligence.dispatch_case",
            "app.market_intelligence.case_event_builder",
            "app.market_intelligence.telegram",
            "openai",
            "pytesseract",
            "easyocr",
        ]
        path = SCRIPTS / "run_fake_ratecon_candidate_extraction.py"

        assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_broker_template_modules_do_not_import_business_memory_or_output_layers(self):
        forbidden_prefixes = [
            "app.market_intelligence.decision_engine",
            "app.market_intelligence.dispatch_case",
            "app.market_intelligence.case_event_builder",
            "app.market_intelligence.event_logger",
            "app.market_intelligence.telegram",
            "app.market_intelligence.broker_memory_core",
            "app.market_intelligence.broker_memory_queries",
            "app.market_intelligence.broker_memory_rules",
            "app.market_intelligence.market_broker_memory",
            "pypdf",
            "pdfplumber",
            "fitz",
            "openai",
            "pytesseract",
            "easyocr",
            "requests",
            "gspread",
            "google.oauth",
            "googleapiclient",
        ]
        template_files = [
            DOCUMENT_AI_PACKAGE / "broker_templates.py",
            DOCUMENT_AI_PACKAGE / "broker_template_registry.py",
            DOCUMENT_AI_PACKAGE / "broker_template_matcher.py",
            DOCUMENT_AI_PACKAGE / "broker_template_scoring.py",
            DOCUMENT_AI_PACKAGE / "broker_template_candidate_extraction.py",
        ]

        for path in template_files:
            with self.subTest(path=str(path)):
                assert_no_import_prefix(self, path, forbidden_prefixes)


if __name__ == "__main__":
    unittest.main()
