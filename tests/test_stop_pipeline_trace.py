import json
import unittest

from app.document_ai.stop_pipeline_trace import (
    STOP_STAGE_POST_SINGLE_LINE_CLUSTER,
    STOP_STAGE_PREMERGE_GROUPS,
    build_stop_pipeline_stage_stats,
    build_stop_pipeline_trace,
)


class StopPipelineTraceTests(unittest.TestCase):
    def test_trace_serializes(self):
        trace = build_stop_pipeline_trace(
            document_alias="RATECON_FAKE",
            stages=[
                build_stop_pipeline_stage_stats(
                    STOP_STAGE_PREMERGE_GROUPS,
                    input_count=3,
                    output_count=3,
                )
            ],
            no_change_reason="no_mergeable_groups",
        )

        payload = json.loads(json.dumps(trace))

        self.assertEqual(payload["document_alias"], "RATECON_FAKE")
        self.assertEqual(payload["trace_version"], "stop_pipeline_trace_v1")

    def test_passthrough_detection_when_all_counts_same(self):
        trace = build_stop_pipeline_trace(
            stages=[
                build_stop_pipeline_stage_stats(
                    STOP_STAGE_PREMERGE_GROUPS,
                    input_count=8,
                    output_count=8,
                )
            ],
            no_change_reason="merge_functions_not_triggered",
        )

        self.assertTrue(trace["passthrough_detected"])
        self.assertEqual(trace["first_stage_that_changed"], "")
        self.assertEqual(trace["no_change_reason"], "merge_functions_not_triggered")

    def test_first_changed_stage_detected(self):
        trace = build_stop_pipeline_trace(
            stages=[
                build_stop_pipeline_stage_stats(
                    STOP_STAGE_PREMERGE_GROUPS,
                    input_count=8,
                    output_count=8,
                ),
                build_stop_pipeline_stage_stats(
                    STOP_STAGE_POST_SINGLE_LINE_CLUSTER,
                    input_count=8,
                    output_count=1,
                    merge_count=7,
                ),
            ]
        )

        self.assertFalse(trace["passthrough_detected"])
        self.assertEqual(
            trace["first_stage_that_changed"],
            STOP_STAGE_POST_SINGLE_LINE_CLUSTER,
        )
        self.assertEqual(trace["no_change_reason"], "")

    def test_trace_contains_no_private_value_fields(self):
        trace = build_stop_pipeline_trace(
            stages=[
                build_stop_pipeline_stage_stats(
                    STOP_STAGE_PREMERGE_GROUPS,
                    input_count=1,
                    output_count=1,
                )
            ]
        )

        serialized = json.dumps(trace)

        for forbidden in ["raw_text", "filename", "address", "rate", "reference_value"]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
