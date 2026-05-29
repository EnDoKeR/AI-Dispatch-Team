import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / "app" / "market_intelligence"


def module_tree(name):
    path = MODULES / name
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_modules(tree):
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    return imports


def called_names(tree):
    calls = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if isinstance(node.func, ast.Name):
            calls.append(node.func.id)

        if isinstance(node.func, ast.Attribute):
            calls.append(node.func.attr)

    return calls


class TestReloadWatchBoundaries(unittest.TestCase):
    def assert_no_imports(self, filename, banned_modules):
        imports = imported_modules(module_tree(filename))

        for banned_module in banned_modules:
            with self.subTest(filename=filename, banned_module=banned_module):
                self.assertNotIn(banned_module, imports)

    def assert_no_calls(self, filename, banned_calls):
        calls = called_names(module_tree(filename))

        for banned_call in banned_calls:
            with self.subTest(filename=filename, banned_call=banned_call):
                self.assertNotIn(banned_call, calls)

    def test_telegram_watch_formatter_does_not_import_sender_or_notifier(self):
        self.assert_no_imports(
            "telegram_watch_formatter.py",
            [
                "app.market_intelligence.telegram_sender",
                "app.market_intelligence.telegram_notifier",
                "app.market_intelligence.telegram_outbox_logger",
                "app.market_intelligence.reload_watch_action_planner",
            ],
        )

    def test_reload_watch_action_planner_does_not_import_formatter_or_side_effect_layers(self):
        self.assert_no_imports(
            "reload_watch_action_planner.py",
            [
                "app.market_intelligence.telegram_watch_formatter",
                "app.market_intelligence.telegram_sender",
                "app.market_intelligence.telegram_notifier",
                "app.market_intelligence.telegram_sent_state",
                "app.market_intelligence.event_logger",
                "app.market_intelligence.dispatch_case",
                "app.market_intelligence.case_event_builder",
            ],
        )

    def test_reload_watch_event_builder_does_not_import_persistence_or_case_layers(self):
        self.assert_no_imports(
            "reload_watch_event_builder.py",
            [
                "app.market_intelligence.event_logger",
                "app.market_intelligence.dispatch_case",
                "app.market_intelligence.case_event_builder",
                "app.market_intelligence.telegram_sender",
                "app.market_intelligence.telegram_notifier",
                "app.market_intelligence.telegram_sent_state",
            ],
        )

    def test_reload_watch_state_stays_side_effect_free(self):
        self.assert_no_imports(
            "reload_watch_state.py",
            [
                "time",
                "threading",
                "sched",
                "json",
                "pathlib",
                "app.market_intelligence.telegram_sender",
                "app.market_intelligence.telegram_notifier",
                "app.market_intelligence.event_logger",
                "app.market_intelligence.dispatch_case",
            ],
        )
        self.assert_no_calls(
            "reload_watch_state.py",
            ["open", "write", "sleep", "send_telegram_message"],
        )

    def test_reload_watch_record_has_no_persistence_or_messaging_imports(self):
        self.assert_no_imports(
            "reload_watch_record.py",
            [
                "json",
                "sqlite3",
                "pathlib",
                "app.market_intelligence.telegram_sender",
                "app.market_intelligence.telegram_notifier",
                "app.market_intelligence.telegram_sent_state",
                "app.market_intelligence.event_logger",
                "app.market_intelligence.dispatch_case",
                "app.market_intelligence.case_event_builder",
            ],
        )
        self.assert_no_calls(
            "reload_watch_record.py",
            ["open", "write", "save_line", "send_telegram_message"],
        )


if __name__ == "__main__":
    unittest.main()
