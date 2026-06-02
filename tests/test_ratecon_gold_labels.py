import unittest

from app.document_ai.ratecon_gold_labels import (
    FIELD_BROKER_NAME,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_STOPS,
    FIELD_TOTAL_CARRIER_RATE,
    LABEL_LABELED,
    LABEL_PARTIAL,
    STATUS_NORMALIZED_MATCH,
    STATUS_PARTIAL_MATCH,
    build_gold_label_template,
    compare_field,
    validate_gold_label,
)


class RateconGoldLabelsTests(unittest.TestCase):
    def _complete_label(self):
        label = build_gold_label_template(document_id="DOC-1", file_hash="hash")
        label["label_status"] = LABEL_LABELED
        label["gold"][FIELD_LOAD_NUMBER]["value"] = "ABC-123"
        label["gold"][FIELD_TOTAL_CARRIER_RATE]["value"] = "2500.00"
        label["gold"][FIELD_BROKER_NAME]["value"] = "Acme Logistics LLC"
        label["gold"]["carrier_name"]["value"] = "Carrier Co"
        label["gold"][FIELD_PICKUP_STOPS] = [
            {
                "stop_index": 1,
                "facility": "Dock",
                "address": None,
                "city": "Dallas",
                "state": "TX",
                "zip": None,
                "date": "01/02/2026",
                "time": "08:00",
                "appointment_window": None,
                "uncertain": False,
                "notes": "",
            }
        ]
        label["gold"]["delivery_stops"] = [
            {
                "stop_index": 1,
                "facility": None,
                "address": None,
                "city": "Houston",
                "state": "TX",
                "zip": None,
                "date": "01/03/2026",
                "time": None,
                "appointment_window": None,
                "uncertain": False,
                "notes": "",
            }
        ]
        return label

    def test_valid_complete_label(self):
        self.assertEqual(validate_gold_label(self._complete_label()), [])

    def test_valid_partial_label_allows_missing_critical_fields(self):
        label = build_gold_label_template(document_id="DOC-1")
        label["label_status"] = LABEL_PARTIAL
        label["gold"][FIELD_LOAD_NUMBER]["value"] = "ABC-123"

        self.assertEqual(validate_gold_label(label), [])

    def test_invalid_labeled_missing_critical_field(self):
        label = build_gold_label_template(document_id="DOC-1")
        label["label_status"] = LABEL_LABELED
        label["gold"][FIELD_LOAD_NUMBER]["value"] = "ABC-123"

        errors = validate_gold_label(label)

        self.assertTrue(any("total_carrier_rate" in error for error in errors))

    def test_invalid_stop_structure(self):
        label = build_gold_label_template(document_id="DOC-1")
        label["gold"][FIELD_PICKUP_STOPS] = [{"stop_index": "one"}]

        errors = validate_gold_label(label)

        self.assertIn("gold.pickup_stops[0].stop_index must be integer", errors)

    def test_load_alternate_acceptable_value_matches(self):
        gold = {
            "value": "PRIMARY",
            "alternate_acceptable_values": ["ALT-123"],
            "uncertain": False,
        }

        result = compare_field(FIELD_LOAD_NUMBER, {"value": "alt123"}, gold)

        self.assertEqual(result["status"], STATUS_NORMALIZED_MATCH)

    def test_money_normalized_match(self):
        result = compare_field(
            FIELD_TOTAL_CARRIER_RATE,
            {"value": "$2,500.00"},
            {"value": "2500", "currency": "USD", "uncertain": False},
        )

        self.assertEqual(result["status"], STATUS_NORMALIZED_MATCH)

    def test_name_normalized_match_removes_legal_suffix(self):
        result = compare_field(
            FIELD_BROKER_NAME,
            {"value": "Acme Logistics"},
            {"value": "ACME LOGISTICS LLC", "uncertain": False},
        )

        self.assertEqual(result["status"], STATUS_NORMALIZED_MATCH)

    def test_stop_partial_match(self):
        gold_stops = [
            {
                "stop_index": 1,
                "facility": None,
                "address": None,
                "city": "Dallas",
                "state": "TX",
                "zip": None,
                "date": "01/02/2026",
                "time": None,
                "appointment_window": None,
                "uncertain": False,
            }
        ]
        predicted = {"value": [{"city": "Dallas", "state": "TX"}]}

        result = compare_field(FIELD_PICKUP_STOPS, predicted, gold_stops)

        self.assertEqual(result["status"], STATUS_PARTIAL_MATCH)


if __name__ == "__main__":
    unittest.main()
