import copy
import inspect
import json
import unittest

from app.market_intelligence.intake import case_link_candidate_report
from app.market_intelligence.intake.case_link_candidate import (
    CREATE_CASE_REVIEW,
    LINK_EXISTING,
    NEEDS_REVIEW,
)
from app.market_intelligence.intake.case_link_candidate_report import (
    build_intake_case_link_candidate_report,
)
from tests.fixtures.intake_case_link_candidates import (
    INTAKE_CASE_LINK_CANDIDATE_SCENARIOS,
)


class TestIntakeCaseLinkCandidateReport(unittest.TestCase):
    def test_empty_report_is_safe(self):
        report = build_intake_case_link_candidate_report([])

        self.assertEqual(report["total_candidates"], 0)
        self.assertEqual(report["approval_required_count"], 0)
        self.assertEqual(report["missing_fields_summary"], {})
        self.assertEqual(report["needs_check_summary"], {})
        self.assertEqual(report["mismatch_reason_summary"], {})

    def test_report_processes_fixtures(self):
        report = build_intake_case_link_candidate_report(
            INTAKE_CASE_LINK_CANDIDATE_SCENARIOS
        )

        self.assertEqual(
            report["total_candidates"],
            len(INTAKE_CASE_LINK_CANDIDATE_SCENARIOS),
        )
        self.assertEqual(
            len(report["candidates"]),
            len(INTAKE_CASE_LINK_CANDIDATE_SCENARIOS),
        )

    def test_report_counts_actions(self):
        report = build_intake_case_link_candidate_report(
            INTAKE_CASE_LINK_CANDIDATE_SCENARIOS
        )
        counts = report["counts_by_recommended_action"]

        self.assertEqual(counts[LINK_EXISTING], 2)
        self.assertEqual(counts[CREATE_CASE_REVIEW], 1)
        self.assertGreaterEqual(counts[NEEDS_REVIEW], 1)

    def test_report_counts_approval_required(self):
        report = build_intake_case_link_candidate_report(
            INTAKE_CASE_LINK_CANDIDATE_SCENARIOS
        )

        self.assertEqual(
            report["approval_required_count"],
            len(INTAKE_CASE_LINK_CANDIDATE_SCENARIOS),
        )

    def test_report_summarizes_missing_fields(self):
        report = build_intake_case_link_candidate_report(
            INTAKE_CASE_LINK_CANDIDATE_SCENARIOS
        )

        self.assertEqual(report["missing_fields_summary"]["broker_mc"], 1)
        self.assertEqual(report["missing_fields_summary"]["rate"], 1)
        self.assertEqual(report["missing_fields_summary"]["weight"], 1)

    def test_report_summarizes_mismatch_reasons(self):
        report = build_intake_case_link_candidate_report(
            INTAKE_CASE_LINK_CANDIDATE_SCENARIOS
        )

        self.assertEqual(report["mismatch_reason_summary"]["reference_id_mismatch"], 1)
        self.assertEqual(report["mismatch_reason_summary"]["broker_mc_mismatch"], 1)
        self.assertEqual(report["mismatch_reason_summary"]["lane_mismatch"], 1)

    def test_report_is_json_serializable(self):
        report = build_intake_case_link_candidate_report(
            INTAKE_CASE_LINK_CANDIDATE_SCENARIOS
        )

        json.dumps(report)

    def test_report_does_not_mutate_inputs(self):
        scenarios = copy.deepcopy(INTAKE_CASE_LINK_CANDIDATE_SCENARIOS)
        before = copy.deepcopy(scenarios)

        build_intake_case_link_candidate_report(scenarios)

        self.assertEqual(scenarios, before)

    def test_report_has_no_forbidden_imports(self):
        source = inspect.getsource(case_link_candidate_report)

        forbidden = [
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "telegram_sender",
            "telegram_notifier",
            "pypdf",
            "pytesseract",
            "gspread",
            "google.oauth",
            "googlemaps",
            "dat_api",
            "load_intake",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
