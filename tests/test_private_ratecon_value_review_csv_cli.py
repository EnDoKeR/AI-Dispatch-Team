import inspect
import tempfile
import unittest
from pathlib import Path

import scripts.export_private_ratecon_value_review_csv as export_cli


def fake_runner(path, anonymized_label=""):
    return {
        "status": "READY_FOR_REVIEW",
        "warnings": ["fake_warning"],
        "dry_run_result": {
            "parser_output": {
                "customer_name": "FAKE BROKER LLC",
                "load_label": "FAKE LOAD",
                "pickup_location": "Fake City, ST 00000",
                "pickup_date": "2026-05-30",
                "delivery_location": "Example City, ST 00000",
                "delivery_date": "2026-05-31",
                "load_number": "FAKE-REF-001",
                "rate": 2500,
                "commodity": "FAKE COMMODITY",
                "weight": 42000,
                "field_confidence": {},
            },
            "ratecon_core_summary": {
                "missing_core_fields": [],
                "optional_missing_fields": ["broker_mc"],
                "deferred_fields": ["loaded_miles"],
                "loaded_miles": "",
                "miles_status": "DEFERRED_GOOGLE_MAPS",
                "miles_source": "NOT_FROM_RATECON",
            },
            "intake_summary": {
                "needs_check_fields": [],
            },
        },
    }


class PrivateRateConValueReviewCsvCliTests(unittest.TestCase):
    def test_cli_default_limit_is_batch_three(self):
        parser = export_cli.build_parser()
        args = parser.parse_args([])

        self.assertEqual(args.limit, 3)

    def test_builds_limited_private_value_summaries_with_fake_runner(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "first.pdf").touch()
            (root / "second.pdf").touch()
            report = export_cli.build_private_ratecon_value_review_summaries(
                directory=root,
                limit=1,
                runner=fake_runner,
            )

        self.assertEqual(report["total_pdf_files"], 2)
        self.assertEqual(report["processed_count"], 1)
        self.assertEqual(report["summaries"][0]["label"], "RATECON_001")
        self.assertFalse(report["private_text_saved"])
        self.assertFalse(report["cases_created"])
        self.assertFalse(report["events_written"])

    def test_format_export_result_does_not_print_private_values(self):
        output = export_cli.format_export_result(
            {
                "output_path": "data/private_ratecons/dry_run_results/ratecon_value_review.csv",
                "rows_written": 3,
            }
        )

        self.assertIn("Rows written: 3", output)
        self.assertIn("DRY RUN ONLY", output)
        self.assertNotIn("FAKE BROKER LLC", output)
        self.assertNotIn("FAKE-REF-001", output)

    def test_cli_source_has_no_forbidden_integrations(self):
        source = inspect.getsource(export_cli).lower()
        forbidden = [
            "gspread",
            "google.oauth",
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "gmail",
            "googlemaps",
            "dat_api",
            "load_intake",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
