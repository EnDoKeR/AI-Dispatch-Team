import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from app.market_intelligence.reload_watch_repository import (
    get_reload_watch_by_id,
)


def temp_file(directory):
    return Path(directory) / "reload_watch_records.json"


class TestReloadWatchDryRunWorkflow(unittest.TestCase):
    def run_script(self, *args):
        result = subprocess.run(
            [sys.executable, *args],
            text=True,
            capture_output=True,
            check=False,
        )

        return result.returncode, result.stdout, result.stderr

    def test_manual_dry_run_workflow_start_report_event_preview_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            start_code, start_output, start_error = self.run_script(
                "scripts/start_reload_watch.py",
                "--file-path",
                str(file_path),
                "--watch-id",
                "WATCH-1",
                "--driver-name",
                "Alex",
                "--parent-load-id",
                "LOAD-1",
                "--parent-reference-id",
                "REF-1",
                "--pickup",
                "Dallas, TX",
                "--delivery",
                "Denver, CO",
                "--rate",
                "3200",
                "--timestamp",
                "2026-05-29T10:00:00Z",
            )

            self.assertEqual(start_code, 0, start_error)
            self.assertIn("RELOAD WATCH START DRY-RUN", start_output)
            self.assertIn("watch_id: WATCH-1", start_output)

            report_code, report_output, report_error = self.run_script(
                "scripts/report_reload_watch.py",
                "--file-path",
                str(file_path),
            )

            self.assertEqual(report_code, 0, report_error)
            self.assertIn("RELOAD WATCH DRY-RUN REPORT", report_output)
            self.assertIn("WATCH-1", report_output)

            event_code, event_output, event_error = self.run_script(
                "scripts/run_reload_watch_event.py",
                "--file-path",
                str(file_path),
                "--watch-id",
                "WATCH-1",
                "--event",
                "CLEAN_EXIT_FOUND",
                "--clean-exits",
                "2",
                "--best-exit-reference-id",
                "EXIT-1",
                "--best-exit-pickup",
                "Denver, CO",
                "--best-exit-delivery",
                "Houston, TX",
                "--best-exit-rate",
                "2600",
                "--timestamp",
                "2026-05-29T10:10:00Z",
                "--preview-message",
            )

            self.assertEqual(event_code, 0, event_error)
            self.assertIn("action_type: CRITICAL_ALERT", event_output)
            self.assertIn("TELEGRAM PREVIEW ONLY - no message sent", event_output)
            self.assertIn("CLEAN EXIT FOUND", event_output)

            final_report_code, final_report_output, final_report_error = self.run_script(
                "scripts/report_reload_watch.py",
                "--file-path",
                str(file_path),
            )

            self.assertEqual(final_report_code, 0, final_report_error)
            self.assertIn("Clean exits: 2", final_report_output)
            self.assertIn("Best exit: Denver, CO -> Houston, TX | $2600 | REF: EXIT-1", final_report_output)

            record = get_reload_watch_by_id("WATCH-1", file_path)

            self.assertEqual(record["clean_exit_count"], 2)
            self.assertEqual(record["best_exit_reference_id"], "EXIT-1")
            self.assertIn(str(Path(temp_dir)), str(file_path))


if __name__ == "__main__":
    unittest.main()
