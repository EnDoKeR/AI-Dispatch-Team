import unittest

from app.document_ai.ratecon_hybrid_contract import (
    build_hybrid_result_template,
    build_stop_template,
    validate_hybrid_result,
)


class RateConHybridContractTests(unittest.TestCase):
    def test_minimal_valid_result_passes(self):
        result = build_hybrid_result_template("DOC-1")

        validation = validate_hybrid_result(result)

        self.assertTrue(validation.valid)

    def test_missing_schema_version_fails(self):
        result = build_hybrid_result_template("DOC-1")
        result.pop("schema_version")

        validation = validate_hybrid_result(result)

        self.assertFalse(validation.valid)
        self.assertTrue(any("schema_version" in error for error in validation.errors))

    def test_stop_without_role_fails(self):
        result = build_hybrid_result_template("DOC-1")
        result["fields"]["pickup_stops"] = [build_stop_template("pickup", 1)]
        result["fields"]["pickup_stops"][0].pop("role")

        validation = validate_hybrid_result(result)

        self.assertFalse(validation.valid)
        self.assertTrue(any(".role" in error for error in validation.errors))

    def test_stop_with_auto_accept_true_fails(self):
        result = build_hybrid_result_template("DOC-1")
        result["fields"]["pickup_stops"][0]["auto_accept"] = True

        validation = validate_hybrid_result(result)

        self.assertFalse(validation.valid)
        self.assertTrue(any("auto_accept" in error for error in validation.errors))

    def test_stop_with_values_but_no_evidence_fails_strict(self):
        result = build_hybrid_result_template("DOC-1")
        result["fields"]["pickup_stops"][0]["city"] = "Dallas"

        validation = validate_hybrid_result(result)

        self.assertFalse(validation.valid)
        self.assertTrue(any("no evidence" in error for error in validation.errors))

    def test_private_local_only_false_fails_private_benchmark(self):
        result = build_hybrid_result_template("DOC-1")
        result["private_local_only"] = False

        validation = validate_hybrid_result(result)

        self.assertFalse(validation.valid)
        self.assertTrue(any("private_local_only" in error for error in validation.errors))

    def test_unknown_document_type_fails(self):
        result = build_hybrid_result_template("DOC-1")
        result["document_type"] = "invoice"

        validation = validate_hybrid_result(result)

        self.assertFalse(validation.valid)
        self.assertTrue(any("document_type" in error for error in validation.errors))

    def test_non_rate_confirmation_document_types_pass(self):
        for document_type in ("non_rate_confirmation", "bill_of_lading_or_delivery_receipt"):
            result = build_hybrid_result_template("DOC-1")
            result["document_type"] = document_type

            validation = validate_hybrid_result(result)

            self.assertTrue(validation.valid)

    def test_private_raw_text_requires_private_flag(self):
        result = build_hybrid_result_template("DOC-1")
        stop = result["fields"]["pickup_stops"][0]
        stop["raw_text_local_only"] = "PRIVATE_SENTINEL"
        stop["evidence_page"] = 1

        validation = validate_hybrid_result(result)
        private_validation = validate_hybrid_result(
            result,
            include_private_values_local_only=True,
        )

        self.assertFalse(validation.valid)
        self.assertTrue(private_validation.valid)


if __name__ == "__main__":
    unittest.main()
