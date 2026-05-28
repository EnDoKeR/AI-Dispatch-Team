import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.market_intelligence.decision_logger import append_jsonl, log_decisions


class FakeSearchRequest:
    driver_name = "Alex"
    current_location = "Dallas, TX"
    equipment = "Flatbed"
    target_direction = "TX"


class FakeLoad:
    def __init__(self, name, status):
        self.name = name
        self.pickup = "Dallas, TX"
        self.delivery = "Houston, TX"
        self.rate = 2200
        self.loaded_miles = 240
        self.empty_miles = 20
        self.total_miles = 260
        self.total_rpm = 8.46
        self.weight = 36000
        self.posted_trailer_type = "Flatbed"
        self.commodity = "Steel"
        self.broker_name = "Test Broker"
        self.broker_mc = "123456"
        self.broker_contact = "broker@example.com"
        self.reference_id = f"REF-{name}"
        self.broker_status = "UNKNOWN"
        self.credit_score = 95
        self.days_to_pay = 18
        self.driver_match_status = status
        self.driver_match_notes = [f"{status} reason"]
        self.notes = f"{name} notes"

    def opportunity_score(self):
        if self.driver_match_status == "MATCH":
            return 90

        if self.driver_match_status == "REVIEW_ONCE":
            return 70

        return 20

    def priority(self):
        return "HIGH"

    def suggested_action(self):
        return "SEND"

    def is_good(self):
        return self.driver_match_status in ["MATCH", "REVIEW_ONCE"]

    def is_qualified(self):
        return self.driver_match_status != "BLOCK"

    def review_category(self):
        return "RATE CHECK"


class TestDecisionLoggerFlow(unittest.TestCase):
    def test_append_jsonl_creates_parent_folder_and_writes_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "nested" / "records.jsonl"

            append_jsonl(
                output_file,
                [
                    {"id": 1, "name": "first"},
                    {"id": 2, "name": "second"},
                ],
            )

            self.assertTrue(output_file.exists())

            lines = output_file.read_text(encoding="utf-8").splitlines()
            records = [json.loads(line) for line in lines]

            self.assertEqual(
                records,
                [
                    {"id": 1, "name": "first"},
                    {"id": 2, "name": "second"},
                ],
            )

    def test_log_decisions_writes_run_and_decision_history_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_file = Path(temp_dir) / "decision_runs.jsonl"
            history_file = Path(temp_dir) / "decision_history.jsonl"

            loads = [
                FakeLoad(name="MATCH-001", status="MATCH"),
                FakeLoad(name="REVIEW-001", status="REVIEW_ONCE"),
                FakeLoad(name="BLOCK-001", status="BLOCK"),
            ]

            recommendation = {
                "market_activity": "MEDIUM",
                "driver_fit": "WORKABLE",
                "action_status": "SOME_MATCHES_AVAILABLE",
            }

            with patch(
                "app.market_intelligence.decision_logger.DECISION_RUNS_FILE",
                runs_file,
            ), patch(
                "app.market_intelligence.decision_logger.DECISION_HISTORY_FILE",
                history_file,
            ), patch(
                "app.market_intelligence.decision_logger.utc_now_iso",
                return_value="2026-05-28T10:00:00+00:00",
            ):
                result = log_decisions(
                    search_request=FakeSearchRequest(),
                    loads=loads,
                    recommendation=recommendation,
                )

            self.assertTrue(result["run_id"].startswith("RUN-"))
            self.assertEqual(result["loads_logged"], 3)
            self.assertEqual(result["match_count"], 1)
            self.assertEqual(result["review_once_count"], 1)
            self.assertEqual(result["block_count"], 1)

            run_records = [
                json.loads(line)
                for line in runs_file.read_text(encoding="utf-8").splitlines()
            ]
            decision_records = [
                json.loads(line)
                for line in history_file.read_text(encoding="utf-8").splitlines()
            ]

            self.assertEqual(len(run_records), 1)
            self.assertEqual(len(decision_records), 3)

            run_record = run_records[0]

            self.assertEqual(run_record["run_id"], result["run_id"])
            self.assertEqual(run_record["driver_name"], "Alex")
            self.assertEqual(run_record["driver_location"], "Dallas, TX")
            self.assertEqual(run_record["loads_analyzed"], 3)
            self.assertEqual(run_record["match_count"], 1)
            self.assertEqual(run_record["review_once_count"], 1)
            self.assertEqual(run_record["block_count"], 1)
            self.assertEqual(run_record["market_activity"], "MEDIUM")
            self.assertEqual(run_record["market_driver_fit"], "WORKABLE")
            self.assertEqual(
                run_record["market_action_status"],
                "SOME_MATCHES_AVAILABLE",
            )

            decisions = [record["decision"] for record in decision_records]

            self.assertEqual(decisions, ["MATCH", "REVIEW_ONCE", "BLOCK"])

            for record in decision_records:
                self.assertEqual(record["run_id"], result["run_id"])
                self.assertEqual(record["driver_name"], "Alex")
                self.assertEqual(record["market_activity"], "MEDIUM")


if __name__ == "__main__":
    unittest.main()
