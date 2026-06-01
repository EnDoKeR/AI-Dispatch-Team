import unittest

from app.document_ai.document_extraction_artifact import (
    artifact_summary,
    build_document_extraction_artifact,
)
from app.document_ai.layout_provider_contract import (
    SHADOW_LAYOUT_PROVIDER_CHOICES,
    build_layout_provider_summary,
)
from app.document_ai.layout_shadow_candidates import (
    generate_layout_load_identity_candidates,
    generate_layout_stop_table_candidates,
    summarize_tables_for_shadow,
)


def fake_bbox(x0=0, y0=0, x1=100, y1=10):
    return [x0, y0, x1, y1]


class LayoutShadowCandidateTests(unittest.TestCase):
    def test_layout_contract_imports_without_optional_provider(self):
        self.assertIn("native_text", SHADOW_LAYOUT_PROVIDER_CHOICES)
        self.assertIn("auto", SHADOW_LAYOUT_PROVIDER_CHOICES)
        self.assertIn("pdfplumber", SHADOW_LAYOUT_PROVIDER_CHOICES)

    def test_artifact_population_preserves_provider_words_lines_tables(self):
        summary = build_layout_provider_summary(
            provider_requested="pdfplumber",
            provider_used="pdfplumber",
            available=True,
            status="success",
            pages=[
                {
                    "words": [{"text": "Load"}],
                    "lines": [{"text": "Load # ABC123"}],
                    "tables": [
                        {
                            "rows": [
                                {
                                    "row_index": 0,
                                    "cells": [{"text": "Load #", "column_index": 0}],
                                }
                            ]
                        }
                    ],
                }
            ],
        )
        artifact = build_document_extraction_artifact(
            document_id="DOC",
            source="pdfplumber",
            layout_provider_summary=summary,
            pages=[
                {
                    "page_number": 1,
                    "lines": [
                        {
                            "text": "Load # ABC123",
                            "bbox": fake_bbox(),
                            "reading_order_index": 1,
                            "source": "pdfplumber",
                        }
                    ],
                    "words": [
                        {
                            "text": "ABC123",
                            "bbox": fake_bbox(60, 0, 100, 10),
                            "word_id": "W1",
                            "line_id": "L1",
                            "source": "pdfplumber",
                        }
                    ],
                    "tables": [
                        {
                            "page": 1,
                            "rows": [
                                {
                                    "row_index": 0,
                                    "cells": [
                                        {
                                            "text": "Load #",
                                            "bbox": fake_bbox(),
                                            "column_index": 0,
                                        },
                                        {
                                            "text": "ABC123",
                                            "bbox": fake_bbox(60, 0, 100, 10),
                                            "column_index": 1,
                                        },
                                    ],
                                }
                            ],
                            "source": "pdfplumber",
                        }
                    ],
                }
            ],
        )

        page = artifact["pages"][0]
        self.assertEqual(page["lines"][0]["line_index"], 1)
        self.assertTrue(page["lines"][0]["bbox"])
        self.assertEqual(page["words"][0]["line_id"], "L1")
        self.assertEqual(page["tables"][0]["rows"][0]["cells"][1]["text"], "ABC123")
        self.assertEqual(artifact_summary(artifact)["layout_provider_summary"]["status"], "success")

    def test_layout_load_same_row_and_table_cell_candidates(self):
        artifact = build_document_extraction_artifact(
            document_id="DOC",
            source="pdfplumber",
            pages=[
                {
                    "page_number": 1,
                    "lines": [
                        {
                            "text": "Load # ABC123",
                            "bbox": fake_bbox(),
                            "reading_order_index": 1,
                            "source": "pdfplumber",
                        }
                    ],
                    "tables": [
                        {
                            "page": 1,
                            "rows": [
                                {
                                    "row_index": 0,
                                    "cells": [
                                        {
                                            "text": "Shipment ID",
                                            "column_index": 0,
                                            "bbox": fake_bbox(0, 20, 50, 30),
                                        },
                                        {
                                            "text": "SHIP-123",
                                            "column_index": 1,
                                            "bbox": fake_bbox(60, 20, 100, 30),
                                        },
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        )

        candidates, diagnostics = generate_layout_load_identity_candidates(artifact)

        self.assertGreaterEqual(diagnostics["same_row_pairings"], 1)
        self.assertGreaterEqual(diagnostics["table_cell_pairings"], 1)
        self.assertGreaterEqual(diagnostics["layout_candidates_emitted"], 2)
        self.assertTrue(any(candidate["field"] == "load_number" for candidate in candidates))
        self.assertTrue(all(candidate["metadata"].get("has_bbox") for candidate in candidates))

    def test_table_header_value_load_candidate(self):
        artifact = build_document_extraction_artifact(
            document_id="DOC",
            source="pdfplumber",
            pages=[
                {
                    "page_number": 1,
                    "tables": [
                        {
                            "page": 1,
                            "rows": [
                                {
                                    "row_index": 0,
                                    "cells": [
                                        {"text": "Load #", "column_index": 0, "bbox": fake_bbox()},
                                        {"text": "Pickup", "column_index": 1, "bbox": fake_bbox()},
                                    ],
                                },
                                {
                                    "row_index": 1,
                                    "cells": [
                                        {
                                            "text": "ABC123",
                                            "column_index": 0,
                                            "bbox": fake_bbox(0, 20, 50, 30),
                                        },
                                        {"text": "Fake City, ST", "column_index": 1},
                                    ],
                                },
                            ],
                        }
                    ],
                }
            ],
        )

        candidates, diagnostics = generate_layout_load_identity_candidates(artifact)

        self.assertTrue(
            any(
                candidate["metadata"].get("pairing_method") == "table_header_value_column"
                for candidate in candidates
            )
        )
        self.assertGreaterEqual(diagnostics["table_cell_pairings"], 1)

    def test_table_same_cell_load_candidate(self):
        artifact = build_document_extraction_artifact(
            document_id="DOC",
            source="pdfplumber",
            pages=[
                {
                    "page_number": 1,
                    "tables": [
                        {
                            "rows": [
                                {
                                    "row_index": 0,
                                    "cells": [{"text": "Load #: ABC123", "column_index": 0}],
                                }
                            ]
                        }
                    ],
                }
            ],
        )

        candidates, _diagnostics = generate_layout_load_identity_candidates(artifact)

        self.assertTrue(
            any(
                candidate["metadata"].get("pairing_method") == "table_same_cell"
                for candidate in candidates
            )
        )

    def test_reference_table_candidate_is_weak_reference(self):
        artifact = build_document_extraction_artifact(
            document_id="DOC",
            source="pdfplumber",
            pages=[
                {
                    "page_number": 1,
                    "tables": [
                        {
                            "rows": [
                                {
                                    "row_index": 0,
                                    "cells": [
                                        {"text": "PO #", "column_index": 0},
                                        {"text": "PO1234", "column_index": 1},
                                    ],
                                }
                            ]
                        }
                    ],
                }
            ],
        )

        candidates, _diagnostics = generate_layout_load_identity_candidates(artifact)

        self.assertTrue(candidates)
        self.assertTrue(all(candidate["field"] != "load_number" for candidate in candidates))
        self.assertTrue(all(candidate["confidence"] <= 0.55 for candidate in candidates))

    def test_layout_load_rejects_unsafe_value_shape(self):
        artifact = build_document_extraction_artifact(
            document_id="DOC",
            pages=[
                {
                    "page_number": 1,
                    "lines": [
                        {
                            "text": "Load # 06/10/2026",
                            "bbox": fake_bbox(),
                            "reading_order_index": 1,
                        }
                    ],
                }
            ],
        )

        candidates, diagnostics = generate_layout_load_identity_candidates(artifact)

        self.assertEqual(candidates, [])
        self.assertIn(
            "candidate_looks_like_date",
            diagnostics["layout_rejection_reason_counts"],
        )

    def test_layout_stop_table_row_candidates(self):
        artifact = build_document_extraction_artifact(
            document_id="DOC",
            source="pdfplumber",
            pages=[
                {
                    "page_number": 1,
                    "tables": [
                        {
                            "page": 1,
                            "rows": [
                                {
                                    "row_index": 1,
                                    "cells": [
                                        {"text": "Pickup", "column_index": 0},
                                        {"text": "Fake Facility", "column_index": 1},
                                        {"text": "06/10/2026", "column_index": 2},
                                    ],
                                },
                                {
                                    "row_index": 2,
                                    "cells": [
                                        {"text": "Delivery", "column_index": 0},
                                        {"text": "Fake Destination", "column_index": 1},
                                        {"text": "06/11/2026", "column_index": 2},
                                    ],
                                },
                            ],
                        }
                    ],
                }
            ],
        )

        candidates, diagnostics = generate_layout_stop_table_candidates(artifact)

        fields = {candidate["field"] for candidate in candidates}
        self.assertIn("pickup_stops", fields)
        self.assertIn("delivery_stops", fields)
        self.assertEqual(diagnostics["layout_structured_stop_candidates"], 2)
        self.assertEqual(diagnostics["table_row_stop_candidates"], 2)

    def test_split_pickup_delivery_columns_emit_role_specific_candidates(self):
        artifact = build_document_extraction_artifact(
            document_id="DOC",
            source="pdfplumber",
            pages=[
                {
                    "page_number": 1,
                    "tables": [
                        {
                            "rows": [
                                {
                                    "row_index": 0,
                                    "cells": [
                                        {"text": "Pickup Location", "column_index": 0},
                                        {"text": "Pickup Date", "column_index": 1},
                                        {"text": "Delivery Location", "column_index": 2},
                                        {"text": "Delivery Date", "column_index": 3},
                                    ],
                                },
                                {
                                    "row_index": 1,
                                    "cells": [
                                        {"text": "Fake Origin, ST", "column_index": 0},
                                        {"text": "06/10/2026", "column_index": 1},
                                        {"text": "Fake Destination, ST", "column_index": 2},
                                        {"text": "06/11/2026", "column_index": 3},
                                    ],
                                },
                            ]
                        }
                    ],
                }
            ],
        )

        candidates, diagnostics = generate_layout_stop_table_candidates(artifact)

        fields = {candidate["field"] for candidate in candidates}
        self.assertIn("pickup_stops", fields)
        self.assertIn("delivery_stops", fields)
        self.assertGreaterEqual(diagnostics["table_stop_candidates_complete"], 2)
        self.assertIn("table_split_pickup_delivery_columns", diagnostics["table_pairings_by_method"])

    def test_unknown_role_table_row_is_ambiguous_not_crash(self):
        artifact = build_document_extraction_artifact(
            document_id="DOC",
            source="pdfplumber",
            pages=[
                {
                    "page_number": 1,
                    "tables": [
                        {
                            "rows": [
                                {
                                    "row_index": 1,
                                    "cells": [
                                        {"text": "Facility", "column_index": 0},
                                        {"text": "06/10/2026", "column_index": 1},
                                    ],
                                }
                            ]
                        }
                    ],
                }
            ],
        )

        candidates, diagnostics = generate_layout_stop_table_candidates(artifact)

        self.assertEqual(candidates, [])
        self.assertGreaterEqual(
            diagnostics["layout_ambiguity_reason_counts"].get("LAYOUT_STOP_ROLE_AMBIGUOUS", 0),
            1,
        )

    def test_table_summary_is_safe_counts_only(self):
        artifact = build_document_extraction_artifact(
            document_id="DOC",
            pages=[
                {
                    "page_number": 1,
                    "tables": [
                        {
                            "rows": [
                                {
                                    "row_index": 1,
                                    "cells": [
                                        {"text": "Pickup", "column_index": 0},
                                        {"text": "Date", "column_index": 1},
                                        {"text": "Location", "column_index": 2},
                                    ],
                                }
                            ]
                        }
                    ],
                }
            ],
        )

        summary = summarize_tables_for_shadow(artifact)

        self.assertEqual(summary["docs_with_tables"], 1)
        self.assertEqual(summary["tables_detected"], 1)
        self.assertGreaterEqual(summary["table_rows_with_stop_role"], 1)


if __name__ == "__main__":
    unittest.main()
