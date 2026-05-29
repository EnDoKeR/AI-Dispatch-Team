import copy
import inspect
import json
import unittest
from types import SimpleNamespace

from app.market_intelligence.decision_engine import signals
from app.market_intelligence.decision_engine.signals import (
    SIGNAL_GROUPS,
    build_decision_signal_bundle,
)


class DecisionEngineSignalsTest(unittest.TestCase):
    def test_empty_signals_produce_safe_defaults(self):
        bundle = build_decision_signal_bundle()

        self.assertEqual(set(bundle.keys()), set(SIGNAL_GROUPS))

        for group in SIGNAL_GROUPS:
            self.assertIsInstance(bundle[group], dict)

        self.assertEqual(bundle["approval_context"], {"approval_mode": "COPILOT"})

    def test_load_facts_preserved(self):
        bundle = build_decision_signal_bundle(
            load_facts={
                "pickup": "Dallas, TX",
                "delivery": "Denver, CO",
                "rate": 3600,
            }
        )

        self.assertEqual(bundle["load_facts"]["pickup"], "Dallas, TX")
        self.assertEqual(bundle["load_facts"]["delivery"], "Denver, CO")
        self.assertEqual(bundle["load_facts"]["rate"], 3600)

    def test_notes_facts_preserved(self):
        bundle = build_decision_signal_bundle(
            notes_facts=SimpleNamespace(
                requires_tarp=True,
                no_conestoga=False,
            )
        )

        self.assertEqual(bundle["notes_facts"]["requires_tarp"], True)
        self.assertEqual(bundle["notes_facts"]["no_conestoga"], False)

    def test_market_context_preserved(self):
        bundle = build_decision_signal_bundle(
            market_context={
                "baseline": {"median_rpm": 2.55},
                "exit_status": "WEAK_EXIT_MARKET",
            }
        )

        self.assertEqual(bundle["market_context"]["baseline"]["median_rpm"], 2.55)
        self.assertEqual(bundle["market_context"]["exit_status"], "WEAK_EXIT_MARKET")

    def test_intake_evidence_preserved(self):
        bundle = build_decision_signal_bundle(
            intake_evidence={
                "missing_fields": ["weight"],
                "field_confidence": {"rate": "HIGH"},
            }
        )

        self.assertEqual(bundle["intake_evidence"]["missing_fields"], ["weight"])
        self.assertEqual(bundle["intake_evidence"]["field_confidence"]["rate"], "HIGH")

    def test_approval_context_normalizes_mode(self):
        bundle = build_decision_signal_bundle(
            approval_context={"approval_mode": "supervised", "source": "manual"}
        )

        self.assertEqual(bundle["approval_context"]["approval_mode"], "SUPERVISED")
        self.assertEqual(bundle["approval_context"]["source"], "manual")

    def test_json_serializable(self):
        bundle = build_decision_signal_bundle(
            load_facts={"custom": SimpleNamespace(value="x")},
            dispatch_memory={"samples": {1, 2}},
        )

        json.dumps(bundle)
        self.assertEqual(bundle["load_facts"]["custom"]["value"], "x")

    def test_does_not_mutate_input(self):
        source = {
            "load_facts": {"rate": 3000},
            "market_context": {"flags": ["WEAK_EXIT_MARKET"]},
        }
        before = copy.deepcopy(source)

        bundle = build_decision_signal_bundle(source)
        bundle["load_facts"]["rate"] = 100
        bundle["market_context"]["flags"].append("OTHER")

        self.assertEqual(source, before)

    def test_source_object_supported(self):
        source = SimpleNamespace(
            load_facts={"rate": 3200},
            driver_profile=SimpleNamespace(equipment="Conestoga"),
        )

        bundle = build_decision_signal_bundle(source)

        self.assertEqual(bundle["load_facts"]["rate"], 3200)
        self.assertEqual(bundle["driver_profile"]["equipment"], "Conestoga")

    def test_no_forbidden_imports(self):
        source = inspect.getsource(signals).lower()

        forbidden_terms = [
            "telegram",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "pypdf",
            "gspread",
            "googlemaps",
            "dat_api",
            "apscheduler",
            "threading",
            "sqlite",
            "jsonl",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
