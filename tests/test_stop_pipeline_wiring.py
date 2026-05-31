import json
import unittest
from pathlib import Path

from app.document_ai.stop_association import build_stop_association_result
from app.document_ai.stop_normalization import build_normalized_stop_set
from app.document_ai.stop_pipeline_trace import STOP_STAGE_POST_SINGLE_LINE_CLUSTER


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "stop_pipeline_wiring"
)


def _load_fixture(name):
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _build_stop_set(name):
    fixture = _load_fixture(name)
    return build_normalized_stop_set(
        build_stop_association_result(stop_groups=fixture["stop_groups"]),
        classification_result={
            "document_alias": "RATECON_FAKE",
            "normal_load_movement": True,
        },
    )


class StopPipelineWiringTests(unittest.TestCase):
    def test_mergeable_single_line_fixture_must_reduce_counts(self):
        stop_set = _build_stop_set("fake_mergeable_single_line_stop_section")

        self.assertLess(
            stop_set["post_single_line_cluster_group_count"],
            stop_set["premerge_group_count"],
        )
        self.assertEqual(len(stop_set["stops"]), 1)

    def test_two_single_line_sections_become_two_stops(self):
        stop_set = _build_stop_set("fake_two_mergeable_single_line_sections")

        self.assertEqual(len(stop_set["stops"]), 2)
        self.assertEqual(stop_set["pickup_count"], 1)
        self.assertEqual(stop_set["delivery_count"], 1)

    def test_signature_noise_removed(self):
        stop_set = _build_stop_set("fake_noise_signature_lines")

        self.assertGreater(stop_set["stop_noise_removed_count"], 0)
        self.assertEqual(len(stop_set["stops"]), 1)

    def test_pipeline_trace_detects_passthrough(self):
        stop_set = _build_stop_set("fake_passthrough_should_fail")
        trace = stop_set["stop_pipeline_trace"]

        self.assertFalse(trace["passthrough_detected"])
        self.assertEqual(
            trace["first_stage_that_changed"],
            STOP_STAGE_POST_SINGLE_LINE_CLUSTER,
        )


if __name__ == "__main__":
    unittest.main()
