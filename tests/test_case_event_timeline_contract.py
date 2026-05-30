import copy
import inspect
import json
import unittest

from app.market_intelligence import case_event_timeline_contract
from app.market_intelligence.case_event_timeline_contract import (
    TIMELINE_SCHEMA_VERSION,
    append_timeline_event,
    build_timeline_event,
    sort_timeline_events,
)
from app.market_intelligence.case_event_types import (
    AI_EVALUATED,
    CASE_CREATED,
    EVENT_GROUP_INTAKE_DOCUMENT,
    EVENT_GROUP_LOAD_LEVEL,
    FIELD_CORRECTED,
    LOAD_SEEN,
    MISSING_DOCUMENT_DETECTED,
    OCR_FALLBACK_NEEDED,
    PDF_TRIAGED,
    RATE_CON_PARSED,
    RATE_CON_RECEIVED,
    RATE_CON_REVIEW_REQUIRED,
    TEXT_EXTRACTED,
    event_type_group,
    is_known_event_type,
)


class CaseEventTimelineContractTests(unittest.TestCase):
    def test_builds_timeline_event_contract(self):
        event = build_timeline_event(
            event_type=RATE_CON_RECEIVED,
            case_id="CASE-001",
            event_id="EVENT-001",
            created_at="2026-05-30T12:00:00Z",
            actor_type="system",
            payload={"document_id": "DOC-001"},
            evidence_refs=["EVIDENCE-001"],
            source="dry_run",
            idempotency_key="ratecon-received-DOC-001",
        )

        self.assertEqual(event["event_id"], "EVENT-001")
        self.assertEqual(event["case_id"], "CASE-001")
        self.assertEqual(event["event_type"], RATE_CON_RECEIVED)
        self.assertEqual(event["event_group"], EVENT_GROUP_INTAKE_DOCUMENT)
        self.assertEqual(event["schema_version"], TIMELINE_SCHEMA_VERSION)
        self.assertTrue(event["known_event_type"])

    def test_required_dispatch_workflow_event_types_are_known(self):
        for event_type in [
            LOAD_SEEN,
            RATE_CON_RECEIVED,
            PDF_TRIAGED,
            TEXT_EXTRACTED,
            OCR_FALLBACK_NEEDED,
            RATE_CON_PARSED,
            RATE_CON_REVIEW_REQUIRED,
            FIELD_CORRECTED,
            CASE_CREATED,
            AI_EVALUATED,
            MISSING_DOCUMENT_DETECTED,
        ]:
            with self.subTest(event_type=event_type):
                self.assertTrue(is_known_event_type(event_type))

    def test_event_groups_for_append_points_are_stable(self):
        self.assertEqual(event_type_group(CASE_CREATED), EVENT_GROUP_LOAD_LEVEL)
        self.assertEqual(event_type_group(AI_EVALUATED), EVENT_GROUP_LOAD_LEVEL)
        self.assertEqual(event_type_group(PDF_TRIAGED), EVENT_GROUP_INTAKE_DOCUMENT)

    def test_append_event_prevents_duplicate_idempotency_key(self):
        event = build_timeline_event(
            event_type=TEXT_EXTRACTED,
            event_id="EVENT-001",
            idempotency_key="text-extracted-DOC-001",
        )

        first = append_timeline_event([], event)
        second = append_timeline_event(first, event)

        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)

    def test_event_sorting_is_by_created_at_then_event_id(self):
        events = [
            build_timeline_event(
                event_type=AI_EVALUATED,
                event_id="EVENT-002",
                created_at="2026-05-30T12:00:02Z",
            ),
            build_timeline_event(
                event_type=CASE_CREATED,
                event_id="EVENT-001",
                created_at="2026-05-30T12:00:01Z",
            ),
        ]

        sorted_events = sort_timeline_events(events)

        self.assertEqual(sorted_events[0]["event_id"], "EVENT-001")
        self.assertEqual(sorted_events[1]["event_id"], "EVENT-002")

    def test_unknown_event_type_is_safe(self):
        event = build_timeline_event(event_type="unknown future event")

        self.assertEqual(event["event_type"], "UNKNOWN_FUTURE_EVENT")
        self.assertEqual(event["event_group"], "unknown")
        self.assertFalse(event["known_event_type"])

    def test_output_is_json_serializable(self):
        event = build_timeline_event(
            event_type=RATE_CON_REVIEW_REQUIRED,
            payload={"missing_fields": {"rate", "weight"}},
        )

        json.dumps(event)

    def test_does_not_mutate_input(self):
        event = {
            "event_type": RATE_CON_PARSED,
            "payload": {"missing_fields": ["rate"]},
            "idempotency_key": "parsed-DOC-001",
        }
        before = copy.deepcopy(event)

        append_timeline_event([], event)

        self.assertEqual(event, before)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(case_event_timeline_contract).lower()
        forbidden = [
            "telegram",
            "case_event_builder",
            "event_logger",
            "repository",
            "sqlite",
            "jsonl",
            "pypdf",
            "pdfplumber",
            "pytesseract",
            "gspread",
            "googlemaps",
            "dat_api",
            "openai",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
