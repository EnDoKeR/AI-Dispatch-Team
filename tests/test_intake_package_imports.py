import importlib
import inspect
import unittest


MODULE_COMPATIBILITY = [
    (
        "app.market_intelligence.intake_record",
        "app.market_intelligence.intake.record",
        "build_intake_record",
    ),
    (
        "app.market_intelligence.intake_parser_contract",
        "app.market_intelligence.intake.parser_contract",
        "normalize_parser_output",
    ),
    (
        "app.market_intelligence.intake_record_summary",
        "app.market_intelligence.intake.summary",
        "build_intake_record_summary",
    ),
    (
        "app.market_intelligence.intake_record_repository",
        "app.market_intelligence.intake.repository",
        "load_intake_records",
    ),
    (
        "app.market_intelligence.intake_record_status",
        "app.market_intelligence.intake.status",
        "classify_intake_record_status",
    ),
    (
        "app.market_intelligence.intake_record_report",
        "app.market_intelligence.intake.report",
        "build_intake_record_report",
    ),
    (
        "app.market_intelligence.intake_scenario_runner",
        "app.market_intelligence.intake.scenario_runner",
        "build_intake_scenario_report",
    ),
]


class IntakePackageImportTests(unittest.TestCase):
    def test_new_intake_package_imports_work(self):
        package = importlib.import_module("app.market_intelligence.intake")

        self.assertIn("Intake", inspect.getdoc(package))

        for _old_path, new_path, symbol_name in MODULE_COMPATIBILITY:
            with self.subTest(module=new_path):
                module = importlib.import_module(new_path)
                self.assertTrue(hasattr(module, symbol_name))

    def test_old_import_paths_remain_compatible(self):
        for old_path, new_path, symbol_name in MODULE_COMPATIBILITY:
            with self.subTest(module=old_path):
                old_module = importlib.import_module(old_path)
                new_module = importlib.import_module(new_path)

                self.assertIs(
                    getattr(old_module, symbol_name),
                    getattr(new_module, symbol_name),
                )

    def test_legacy_wrappers_stay_thin(self):
        for old_path, new_path, _symbol_name in MODULE_COMPATIBILITY:
            with self.subTest(module=old_path):
                old_module = importlib.import_module(old_path)
                source = inspect.getsource(old_module)

                self.assertIn(f"from {new_path} import *", source)
                self.assertLessEqual(len(source.splitlines()), 4)

    def test_intake_scripts_still_import(self):
        script_modules = [
            "scripts.run_intake_record_dry_run",
            "scripts.run_intake_scenarios",
            "scripts.report_intake_records",
        ]

        for module_path in script_modules:
            with self.subTest(module=module_path):
                module = importlib.import_module(module_path)
                self.assertTrue(callable(module.main))


if __name__ == "__main__":
    unittest.main()
