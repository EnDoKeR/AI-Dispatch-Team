import copy
import contextlib
import inspect
import io
import tempfile
from pathlib import Path
import unittest

from app.market_intelligence.reload_watch_repository import (
    get_reload_watch_by_id,
)


def temp_file(directory):
    return Path(directory) / "scenario_reload_watch_records.json"


class TestMarketReloadWatchScenarioRunner(unittest.TestCase):
    def test_builtin_scenario_returns_dry_run_and_not_sent(self):
        from app.market_intelligence.market_reload_watch_scenario_runner import (
            run_market_reload_watch_scenario,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_market_reload_watch_scenario(file_path=temp_file(temp_dir))

            self.assertTrue(result["dry_run"])
            self.assertFalse(result["sent"])
            self.assertEqual(
                result["scenario_name"],
                "strong_inbound_weak_exit_then_clean_exit",
            )

    def test_scenario_includes_market_baseline(self):
        from app.market_intelligence.market_reload_watch_scenario_runner import (
            run_market_reload_watch_scenario,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_market_reload_watch_scenario(file_path=temp_file(temp_dir))

            self.assertIn("market_baseline", result)
            self.assertGreater(result["market_baseline"]["load_count"], 0)
            self.assertLess(
                result["market_baseline"]["median_rpm"],
                result["parent_load"]["total_rpm"],
            )

    def test_scenario_includes_city_state_zone_snapshot(self):
        from app.market_intelligence.market_reload_watch_scenario_runner import (
            run_market_reload_watch_scenario,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_market_reload_watch_scenario(file_path=temp_file(temp_dir))

            zone_snapshot = result["zone_snapshot"]

            self.assertIn("Denver, CO", zone_snapshot["cities"])
            self.assertEqual(
                zone_snapshot["cities"]["Denver, CO"]["status"],
                "RISKY_EXIT_MARKET",
            )

    def test_scenario_exit_classification_recommends_reload_watch(self):
        from app.market_intelligence.market_reload_watch_scenario_runner import (
            run_market_reload_watch_scenario,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_market_reload_watch_scenario(file_path=temp_file(temp_dir))

            classification = result["exit_classification"]

            self.assertEqual(
                classification["exit_status"],
                "STRONG_PAY_RELOAD_WATCH_RECOMMENDED",
            )
            self.assertTrue(classification["recommend_reload_watch"])

    def test_scenario_starts_watch_in_temp_file(self):
        from app.market_intelligence.market_reload_watch_scenario_runner import (
            run_market_reload_watch_scenario,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            result = run_market_reload_watch_scenario(file_path=file_path)
            saved_watch = get_reload_watch_by_id(
                result["watch_start_result"]["watch_record"]["watch_id"],
                file_path,
            )

            self.assertEqual(saved_watch["watch_status"], "WATCH_ACTIVE")
            self.assertEqual(saved_watch["parent_reference_id"], "INBOUND-1")
            self.assertIn(str(Path(temp_dir)), str(file_path))

    def test_scenario_simulates_clean_exit_found_critical_alert(self):
        from app.market_intelligence.market_reload_watch_scenario_runner import (
            run_market_reload_watch_scenario,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_market_reload_watch_scenario(file_path=temp_file(temp_dir))

            self.assertEqual(
                result["event_result"]["action_plan"]["action_type"],
                "CRITICAL_ALERT",
            )
            self.assertEqual(
                result["event_result"]["watch_record"]["clean_exit_count"],
                1,
            )

    def test_scenario_includes_clean_exit_telegram_preview_only(self):
        from app.market_intelligence.market_reload_watch_scenario_runner import (
            run_market_reload_watch_scenario,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_market_reload_watch_scenario(file_path=temp_file(temp_dir))

            self.assertIn("CLEAN EXIT FOUND", result["telegram_preview"])
            self.assertIn("Houston, TX", result["telegram_preview"])
            self.assertFalse(result["sent"])

    def test_scenario_does_not_mutate_synthetic_loads(self):
        from app.market_intelligence.market_reload_watch_scenario_runner import (
            build_strong_inbound_weak_exit_scenario,
            run_market_reload_watch_scenario,
        )

        scenario = build_strong_inbound_weak_exit_scenario()
        before = copy.deepcopy([load.__dict__ for load in scenario["all_loads"]])

        with tempfile.TemporaryDirectory() as temp_dir:
            run_market_reload_watch_scenario(
                scenario=scenario,
                file_path=temp_file(temp_dir),
            )

        after = [load.__dict__ for load in scenario["all_loads"]]

        self.assertEqual(after, before)

    def test_scenario_module_does_not_import_sender_or_notifier(self):
        import app.market_intelligence.market_reload_watch_scenario_runner as module

        source = inspect.getsource(module)
        script_source = Path("scripts/run_market_reload_watch_scenario.py").read_text(
            encoding="utf-8"
        )

        for text in [source, script_source]:
            self.assertNotIn("telegram_sender", text)
            self.assertNotIn("telegram_notifier", text)
            self.assertNotIn("event_logger", text)
            self.assertNotIn("dispatch_case", text)

    def test_script_exists_and_prints_dry_run_only_message(self):
        from scripts.run_market_reload_watch_scenario import main

        script_path = Path("scripts/run_market_reload_watch_scenario.py")
        output = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            with contextlib.redirect_stdout(output):
                exit_code = main(["--file-path", str(temp_file(temp_dir))])

        text = output.getvalue()

        self.assertTrue(script_path.exists())
        self.assertEqual(exit_code, 0)
        self.assertIn("strong inbound load into weak exit market", text.lower())
        self.assertIn("DRY RUN ONLY - no Telegram message sent", text)


if __name__ == "__main__":
    unittest.main()
