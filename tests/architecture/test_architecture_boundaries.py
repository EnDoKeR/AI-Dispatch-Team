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


def source_text(path):
    return path.read_text(encoding="utf-8-sig")


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

    def test_repositories_do_not_invent_extraction_or_decision_status(self):
        forbidden_status_literals = {
            "READY_FOR_REVIEW",
            "REVIEW_REQUIRED",
            "MISSING_FIELDS",
            "NEEDS_CHECK",
            "ACCEPT",
            "REJECT",
        }
        repository_files = [
            INTAKE_PACKAGE / "repository.py",
            MARKET_INTELLIGENCE / "intake_record_repository.py",
            MARKET_INTELLIGENCE / "reload_watch_repository.py",
            MARKET_INTELLIGENCE / "sqlite_memory_repository.py",
        ]

        for path in repository_files:
            literals = set(string_literals(path))

            for forbidden_literal in forbidden_status_literals:
                with self.subTest(path=str(path), literal=forbidden_literal):
                    self.assertNotIn(
                        forbidden_literal,
                        literals,
                        f"{path} invents status literal {forbidden_literal}",
                    )

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

    def test_document_ai_modules_do_not_import_legacy_ratecon_paths(self):
        forbidden_prefixes = [
            "app.market_intelligence.intake.pasted_text_parser_adapter",
            "app.market_intelligence.intake.ratecon_text_dry_run",
            "app.market_intelligence.intake.ratecon_pdf_dry_run",
            "app.market_intelligence.intake.pdf_text_extraction",
            "scripts.import_ratecon",
            "scripts.read_ratecon",
            "scripts.run_private_ratecon_pdf_dry_run",
            "scripts.export_private_ratecon_value_review_csv",
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
            "scripts.import_ratecon",
            "scripts.read_ratecon",
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
            "scripts.import_ratecon",
            "scripts.read_ratecon",
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

    def test_fake_candidate_extraction_cli_has_no_private_path_assumptions(self):
        source = source_text(SCRIPTS / "run_fake_ratecon_candidate_extraction.py").lower()

        forbidden_fragments = [
            "data/private_ratecons",
            "data\\private_ratecons",
            "private_ratecons",
            "run_private_ratecon",
            "export_private_ratecon",
        ]

        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)

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

    def test_document_ai_modules_have_no_private_ratecon_path_coupling(self):
        forbidden_fragments = [
            "data/private_ratecons",
            "data\\private_ratecons",
            "private_ratecons",
            "run_private_ratecon",
            "export_private_ratecon",
        ]

        for path in python_files(DOCUMENT_AI_PACKAGE):
            source = source_text(path).lower()
            for fragment in forbidden_fragments:
                with self.subTest(path=str(path), fragment=fragment):
                    self.assertNotIn(fragment, source)

    def test_hard_layout_fixture_helpers_do_not_import_private_flows(self):
        forbidden_prefixes = [
            "scripts.run_private_ratecon_pdf_dry_run",
            "scripts.run_private_ratecon_redacted_diagnostics",
            "scripts.run_private_ratecon_layout_diagnostics",
            "scripts.export_private_ratecon_value_review_csv",
            "app.market_intelligence.intake.ratecon_pdf_dry_run",
            "app.market_intelligence.intake.pdf_text_extraction",
        ]
        helper = (
            ROOT
            / "tests"
            / "fixtures"
            / "document_ai"
            / "ratecon_text"
            / "fixture_loader.py"
        )

        assert_no_import_prefix(self, helper, forbidden_prefixes)
        source = source_text(helper).lower()
        self.assertNotIn("data/private_ratecons", source)
        self.assertNotIn("private_ratecons", source)

    def test_private_measurement_modules_do_not_import_business_or_cloud_layers(self):
        forbidden_prefixes = [
            "app.market_intelligence.decision_engine",
            "app.market_intelligence.dispatch_case",
            "app.market_intelligence.case_event_builder",
            "app.market_intelligence.event_logger",
            "app.market_intelligence.telegram",
            "scripts.import_ratecon",
            "scripts.read_ratecon",
            "scripts.run_private_ratecon_pdf_dry_run",
            "openai",
            "pytesseract",
            "easyocr",
            "requests",
            "google.oauth",
            "googleapiclient",
            "boto3",
            "azure",
        ]
        private_measurement_files = [
            DOCUMENT_AI_PACKAGE / "private_measurement.py",
            DOCUMENT_AI_PACKAGE / "private_measurement_inputs.py",
            DOCUMENT_AI_PACKAGE / "private_measurement_pipeline.py",
            DOCUMENT_AI_PACKAGE / "private_measurement_reports.py",
            DOCUMENT_AI_PACKAGE / "private_measurement_outputs.py",
            DOCUMENT_AI_PACKAGE / "private_measurement_blockers.py",
        ]

        for path in private_measurement_files:
            with self.subTest(path=str(path)):
                assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_private_measurement_modules_do_not_emit_dispatch_recommendations(self):
        forbidden_literals = {
            "ACCEPT",
            "REJECT",
            "REVIEW_ONCE",
            "BOOK",
            "BLOCK",
        }
        private_measurement_files = [
            DOCUMENT_AI_PACKAGE / "private_measurement.py",
            DOCUMENT_AI_PACKAGE / "private_measurement_pipeline.py",
            DOCUMENT_AI_PACKAGE / "private_measurement_reports.py",
            DOCUMENT_AI_PACKAGE / "private_measurement_outputs.py",
            DOCUMENT_AI_PACKAGE / "private_measurement_blockers.py",
        ]

        for path in private_measurement_files:
            literals = set(string_literals(path))
            for literal in forbidden_literals:
                with self.subTest(path=str(path), literal=literal):
                    self.assertNotIn(literal, literals)

    def test_private_measurement_output_writer_rejects_raw_text_fields(self):
        source = source_text(DOCUMENT_AI_PACKAGE / "private_measurement_outputs.py")

        self.assertIn('"raw_text"', source)
        self.assertIn("unsafe output field detected", source)

    def test_private_measurement_cli_requires_explicit_confirmation(self):
        path = SCRIPTS / "run_private_ratecon_measurement.py"
        source = source_text(path)

        assert_no_import_prefix(
            self,
            path,
            [
                "scripts.import_ratecon",
                "scripts.read_ratecon",
                "app.market_intelligence.dispatch_case",
                "app.market_intelligence.decision_engine",
                "app.market_intelligence.telegram",
                "openai",
                "pytesseract",
                "easyocr",
                "googleapiclient",
            ],
        )
        self.assertIn("--confirm-private-local-run", source)
        self.assertIn("Refusing to run", source)

    def test_private_template_modules_do_not_import_business_memory_or_cloud_layers(self):
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
            "scripts.import_ratecon",
            "scripts.read_ratecon",
            "scripts.run_private_ratecon_pdf_dry_run",
            "openai",
            "pytesseract",
            "easyocr",
            "requests",
            "google.oauth",
            "googleapiclient",
            "boto3",
            "azure",
        ]
        private_template_files = [
            DOCUMENT_AI_PACKAGE / "private_template_patterns.py",
            DOCUMENT_AI_PACKAGE / "private_template_redaction.py",
            DOCUMENT_AI_PACKAGE / "private_template_pattern_collector.py",
            DOCUMENT_AI_PACKAGE / "private_template_pattern_families.py",
            DOCUMENT_AI_PACKAGE / "private_template_drafts.py",
            DOCUMENT_AI_PACKAGE / "private_template_overlay_comparison.py",
        ]

        for path in private_template_files:
            with self.subTest(path=str(path)):
                assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_private_pattern_collector_does_not_persist_raw_text(self):
        source = source_text(DOCUMENT_AI_PACKAGE / "private_template_pattern_collector.py")

        self.assertNotIn("write_text", source)
        self.assertNotIn("raw_text_saved", source)

    def test_private_template_pattern_cli_requires_confirmation(self):
        path = SCRIPTS / "run_private_ratecon_template_pattern_collection.py"
        source = source_text(path)

        assert_no_import_prefix(
            self,
            path,
            [
                "scripts.import_ratecon",
                "scripts.read_ratecon",
                "app.market_intelligence.dispatch_case",
                "app.market_intelligence.decision_engine",
                "app.market_intelligence.telegram",
                "openai",
                "pytesseract",
                "easyocr",
                "googleapiclient",
            ],
        )
        self.assertIn("--confirm-private-local-run", source)
        self.assertIn("Refusing to run", source)

    def test_private_overlay_paths_are_gitignored(self):
        gitignore = source_text(ROOT / ".gitignore")

        self.assertIn(".local_private/", gitignore)
        self.assertIn(".local_outputs/", gitignore)

    def test_document_classification_modules_do_not_import_business_output_or_cloud_layers(self):
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
            "openai",
            "pytesseract",
            "easyocr",
            "pdfplumber",
            "fitz",
            "requests",
            "google.oauth",
            "googleapiclient",
            "boto3",
            "azure",
        ]
        classification_files = [
            DOCUMENT_AI_PACKAGE / "document_classification.py",
            DOCUMENT_AI_PACKAGE / "extraction_scope.py",
            DOCUMENT_AI_PACKAGE / "classification_audit.py",
        ]

        for path in classification_files:
            with self.subTest(path=str(path)):
                assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_document_classification_modules_do_not_emit_dispatch_recommendations(self):
        forbidden_literals = {
            "ACCEPT",
            "REJECT",
            "REVIEW_ONCE",
            "BOOK",
            "DISPATCH",
        }
        classification_files = [
            DOCUMENT_AI_PACKAGE / "document_classification.py",
            DOCUMENT_AI_PACKAGE / "extraction_scope.py",
            DOCUMENT_AI_PACKAGE / "classification_audit.py",
        ]

        for path in classification_files:
            literals = set(string_literals(path))
            for literal in forbidden_literals:
                with self.subTest(path=str(path), literal=literal):
                    self.assertNotIn(literal, literals)

    def test_extraction_scope_filter_does_not_write_timeline_or_files(self):
        source = source_text(DOCUMENT_AI_PACKAGE / "extraction_scope.py")

        forbidden_fragments = [
            "write_text",
            "open(",
            "event_logger",
            "case_event",
            "timeline",
            "DispatchCase",
        ]

        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)

    def test_classification_audit_outputs_are_local_only_and_redacted(self):
        source = source_text(DOCUMENT_AI_PACKAGE / "classification_audit.py")

        self.assertIn(".local_outputs/private_ratecon_measurement", source)
        self.assertIn("No raw text, filenames, paths, or private values included.", source)
        self.assertIn("FORBIDDEN_AUDIT_KEYS", source)
        self.assertNotIn("DispatchCase", source)
        self.assertNotIn("DecisionEngine", source)

    def test_layout_modules_do_not_import_business_output_or_pdf_dependencies(self):
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
            "camelot",
            "openai",
            "pytesseract",
            "easyocr",
            "requests",
            "google.oauth",
            "googleapiclient",
            "boto3",
            "azure",
        ]
        layout_files = [
            DOCUMENT_AI_PACKAGE / "layout_artifacts.py",
            DOCUMENT_AI_PACKAGE / "layout_index.py",
            DOCUMENT_AI_PACKAGE / "layout_proximity.py",
            DOCUMENT_AI_PACKAGE / "layout_candidate_adapter.py",
            DOCUMENT_AI_PACKAGE / "layout_rate_candidates.py",
            DOCUMENT_AI_PACKAGE / "layout_stop_candidates.py",
            DOCUMENT_AI_PACKAGE / "layout_operational_candidates.py",
            DOCUMENT_AI_PACKAGE / "layout_candidate_extraction.py",
        ]

        for path in layout_files:
            with self.subTest(path=str(path)):
                assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_layout_modules_do_not_emit_dispatch_recommendations(self):
        forbidden_literals = {
            "ACCEPT",
            "REJECT",
            "REVIEW_ONCE",
            "BOOK",
            "DISPATCH",
        }
        layout_files = [
            DOCUMENT_AI_PACKAGE / "layout_artifacts.py",
            DOCUMENT_AI_PACKAGE / "layout_index.py",
            DOCUMENT_AI_PACKAGE / "layout_proximity.py",
            DOCUMENT_AI_PACKAGE / "layout_candidate_adapter.py",
            DOCUMENT_AI_PACKAGE / "layout_rate_candidates.py",
            DOCUMENT_AI_PACKAGE / "layout_stop_candidates.py",
            DOCUMENT_AI_PACKAGE / "layout_operational_candidates.py",
            DOCUMENT_AI_PACKAGE / "layout_candidate_extraction.py",
        ]

        for path in layout_files:
            literals = set(string_literals(path))
            for literal in forbidden_literals:
                with self.subTest(path=str(path), literal=literal):
                    self.assertNotIn(literal, literals)

    def test_layout_provider_modules_do_not_import_business_output_or_disallowed_extractors(self):
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
            "fitz",
            "camelot",
            "openai",
            "pytesseract",
            "easyocr",
            "requests",
            "google.oauth",
            "googleapiclient",
            "boto3",
            "azure",
        ]
        provider_files = [
            DOCUMENT_AI_PACKAGE / "layout_provider.py",
            DOCUMENT_AI_PACKAGE / "pdfplumber_layout_provider.py",
            DOCUMENT_AI_PACKAGE / "layout_pipeline.py",
            DOCUMENT_AI_PACKAGE / "layout_provider_comparison.py",
            DOCUMENT_AI_PACKAGE / "layout_provider_diagnostics.py",
        ]

        for path in provider_files:
            with self.subTest(path=str(path)):
                assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_layout_provider_modules_do_not_write_timeline_or_private_outputs(self):
        provider_files = [
            DOCUMENT_AI_PACKAGE / "layout_provider.py",
            DOCUMENT_AI_PACKAGE / "pdfplumber_layout_provider.py",
            DOCUMENT_AI_PACKAGE / "layout_pipeline.py",
            DOCUMENT_AI_PACKAGE / "layout_provider_comparison.py",
            DOCUMENT_AI_PACKAGE / "layout_provider_diagnostics.py",
        ]
        forbidden_fragments = [
            "event_logger",
            "case_event",
            "timeline",
            "DispatchCase",
            "DecisionEngine",
            "telegram",
            "private_ratecons",
        ]

        for path in provider_files:
            source = source_text(path)
            for fragment in forbidden_fragments:
                with self.subTest(path=str(path), fragment=fragment):
                    self.assertNotIn(fragment, source)

    def test_only_pdfplumber_layout_dependency_was_added(self):
        requirements = "\n".join(
            line.strip().lower()
            for line in source_text(ROOT / "requirements.txt").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

        self.assertIn("pdfplumber==0.11.9", requirements)
        for forbidden in [
            "pymupdf",
            "fitz",
            "camelot",
            "tesseract",
            "paddleocr",
            "pytesseract",
            "easyocr",
            "openai",
            "boto3",
            "azure",
            "google-cloud",
        ]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, requirements)

    def test_fake_layout_candidate_cli_does_not_import_private_or_provider_flows(self):
        path = SCRIPTS / "run_fake_layout_candidate_extraction.py"
        forbidden_prefixes = [
            "scripts.run_private_ratecon_pdf_dry_run",
            "scripts.run_private_ratecon_measurement",
            "scripts.run_private_ratecon_layout_diagnostics",
            "scripts.import_ratecon",
            "scripts.read_ratecon",
            "app.market_intelligence.intake.pdf_text_extraction",
            "app.market_intelligence.dispatch_case",
            "app.market_intelligence.decision_engine",
            "app.market_intelligence.telegram",
            "pypdf",
            "pdfplumber",
            "fitz",
            "camelot",
            "openai",
            "pytesseract",
            "easyocr",
        ]

        assert_no_import_prefix(self, path, forbidden_prefixes)
        source = source_text(path).lower()
        self.assertIn("fake-only", source)
        self.assertIn("synthetic layout fixtures", source)
        self.assertNotIn("private_ratecons", source)

    def test_layout_fusion_modules_do_not_import_business_output_or_disallowed_extractors(self):
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
            "camelot",
            "openai",
            "pytesseract",
            "easyocr",
            "requests",
            "google.oauth",
            "googleapiclient",
            "boto3",
            "azure",
        ]
        fusion_files = [
            DOCUMENT_AI_PACKAGE / "candidate_fusion.py",
            DOCUMENT_AI_PACKAGE / "stop_association.py",
            DOCUMENT_AI_PACKAGE / "rate_fusion.py",
            DOCUMENT_AI_PACKAGE / "operational_fusion.py",
            DOCUMENT_AI_PACKAGE / "layout_field_delta_audit.py",
        ]

        for path in fusion_files:
            with self.subTest(path=str(path)):
                assert_no_import_prefix(self, path, forbidden_prefixes)

    def test_layout_fusion_modules_do_not_emit_dispatch_recommendations(self):
        forbidden_literals = {
            "ACCEPT",
            "REJECT",
            "REVIEW_ONCE",
            "BOOK",
            "DISPATCH",
        }
        fusion_files = [
            DOCUMENT_AI_PACKAGE / "candidate_fusion.py",
            DOCUMENT_AI_PACKAGE / "stop_association.py",
            DOCUMENT_AI_PACKAGE / "rate_fusion.py",
            DOCUMENT_AI_PACKAGE / "operational_fusion.py",
            DOCUMENT_AI_PACKAGE / "layout_field_delta_audit.py",
        ]

        for path in fusion_files:
            literals = set(string_literals(path))
            for literal in forbidden_literals:
                with self.subTest(path=str(path), literal=literal):
                    self.assertNotIn(literal, literals)

    def test_layout_fusion_modules_do_not_write_timeline_or_nonlocal_outputs(self):
        fusion_files = [
            DOCUMENT_AI_PACKAGE / "candidate_fusion.py",
            DOCUMENT_AI_PACKAGE / "stop_association.py",
            DOCUMENT_AI_PACKAGE / "rate_fusion.py",
            DOCUMENT_AI_PACKAGE / "operational_fusion.py",
        ]
        forbidden_fragments = [
            "write_text",
            "open(",
            "event_logger",
            "case_event",
            "timeline",
            "DispatchCase",
            "DecisionEngine",
            "telegram",
            "private_ratecons",
        ]

        for path in fusion_files:
            source = source_text(path)
            for fragment in forbidden_fragments:
                with self.subTest(path=str(path), fragment=fragment):
                    self.assertNotIn(fragment, source)

    def test_layout_field_delta_audit_outputs_are_local_only_and_redacted(self):
        source = source_text(DOCUMENT_AI_PACKAGE / "layout_field_delta_audit.py")

        self.assertIn("DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR", source)
        self.assertIn("layout_field_delta_audit.md", source)
        self.assertIn("No raw text, filenames, paths, or private values included.", source)
        self.assertIn("FORBIDDEN_AUDIT_KEYS", source)
        self.assertNotIn("DispatchCase", source)
        self.assertNotIn("DecisionEngine", source)
        self.assertNotIn("telegram", source)

    def test_layout_provider_diagnostics_outputs_are_local_only_and_redacted(self):
        source = source_text(DOCUMENT_AI_PACKAGE / "layout_provider_diagnostics.py")

        self.assertIn("DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR", source)
        self.assertIn("layout_provider_diagnostics.md", source)
        self.assertIn('"raw_text_included": False', source)
        self.assertIn('"private_values_redacted": True', source)
        self.assertNotIn("DispatchCase", source)
        self.assertNotIn("DecisionEngine", source)
        self.assertNotIn("telegram", source)

    def test_layout_fixture_directory_contains_no_pdf_or_screenshots(self):
        fixture_dir = ROOT / "tests" / "fixtures" / "document_ai" / "layout_artifacts"
        banned_suffixes = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}

        for path in fixture_dir.rglob("*"):
            if path.is_file():
                with self.subTest(path=str(path)):
                    self.assertNotIn(path.suffix.lower(), banned_suffixes)


if __name__ == "__main__":
    unittest.main()
