import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.market_intelligence.load_source import (
    build_market_load,
    load_market_loads,
    read_load_dicts,
)


class TestLoadSource(unittest.TestCase):
    def test_read_load_dicts_returns_empty_when_file_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_file = Path(temp_dir) / "missing.json"

            self.assertEqual(read_load_dicts(missing_file), [])

    def test_read_load_dicts_returns_empty_when_json_is_not_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "loads.json"
            file_path.write_text(
                json.dumps({"not": "a list"}),
                encoding="utf-8",
            )

            self.assertEqual(read_load_dicts(file_path), [])

    def test_read_load_dicts_keeps_only_dict_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "loads.json"
            file_path.write_text(
                json.dumps(
                    [
                        {"pickup": "Dallas, TX"},
                        "bad item",
                        123,
                        ["bad list"],
                        {"delivery": "Houston, TX"},
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                read_load_dicts(file_path),
                [
                    {"pickup": "Dallas, TX"},
                    {"delivery": "Houston, TX"},
                ],
            )

    def test_build_market_load_maps_primary_fields(self):
        load = build_market_load(
            {
                "origin": "Dallas, TX",
                "destination": "Houston, TX",
                "rate": "2200",
                "loaded_miles": "240",
                "empty_miles": "20",
                "pickup_date": "2026-05-28",
                "delivery_date": "2026-05-29",
                "pickup_time": "10 AM",
                "delivery_time": "2 PM",
                "weight": "36000",
                "posted_trailer_type": "Flatbed",
                "equipment": "Flatbed",
                "commodity": "Steel",
                "notes": "Call broker. Email dispatch@example.com Phone 555-111-2222",
                "parsed_notes": {"tarp": False},
                "broker_name": "Test Broker",
                "broker_mc": "123456",
                "broker_contact": "dispatch@example.com",
                "broker_contact_raw": "dispatch@example.com / 555-111-2222",
                "parsed_contact": {
                    "email": "dispatch@example.com",
                    "phone": "555-111-2222",
                },
                "credit_score": "95",
                "days_to_pay": "18",
                "reference_id": "REF-123",
                "is_bookable": True,
                "is_private": False,
                "is_partial": False,
                "is_od": False,
                "is_tracking_required": True,
                "broker_status": "NEEDS CHECK",
                "delivery_zone": "GOOD / STRONG RELOAD AREA",
            }
        )

        self.assertEqual(load.origin, "Dallas, TX")
        self.assertEqual(load.destination, "Houston, TX")
        self.assertEqual(load.pickup, "Dallas, TX")
        self.assertEqual(load.delivery, "Houston, TX")
        self.assertEqual(load.rate, 2200)
        self.assertEqual(load.loaded_miles, 240)
        self.assertEqual(load.empty_miles, 20)
        self.assertEqual(load.total_miles, 260)
        self.assertEqual(load.total_rpm, 8.46)
        self.assertEqual(load.pickup_date, "2026-05-28")
        self.assertEqual(load.delivery_date, "2026-05-29")
        self.assertEqual(load.pickup_time, "10 AM")
        self.assertEqual(load.delivery_time, "2 PM")
        self.assertEqual(load.weight, 36000)
        self.assertEqual(load.posted_trailer_type, "Flatbed")
        self.assertEqual(load.equipment, "Flatbed")
        self.assertEqual(load.commodity, "Steel")
        self.assertEqual(load.parsed_notes, {"tarp": False})
        self.assertEqual(load.broker_name, "Test Broker")
        self.assertEqual(load.broker_mc, "123456")
        self.assertEqual(load.broker_contact, "dispatch@example.com")
        self.assertEqual(load.broker_contact_raw, "dispatch@example.com / 555-111-2222")
        self.assertEqual(load.parsed_contact["email"], "dispatch@example.com")
        self.assertEqual(load.primary_email, "dispatch@example.com")
        self.assertEqual(load.primary_phone, "555-111-2222")
        self.assertEqual(load.credit_score, "95")
        self.assertEqual(load.days_to_pay, "18")
        self.assertEqual(load.reference_id, "REF-123")
        self.assertTrue(load.is_bookable)
        self.assertFalse(load.is_private)
        self.assertFalse(load.is_partial)
        self.assertFalse(load.is_od)
        self.assertTrue(load.is_tracking_required)
        self.assertEqual(load.broker_status, "NEEDS CHECK")
        self.assertEqual(load.delivery_zone, "GOOD / STRONG RELOAD AREA")

    def test_build_market_load_uses_fallback_fields(self):
        load = build_market_load(
            {
                "pickup": "Austin, TX",
                "delivery": "San Antonio, TX",
                "rate": 1000,
                "trip": 80,
                "equipment": "Step Deck",
                "truck": "Flatbed",
            }
        )

        self.assertEqual(load.origin, "Austin, TX")
        self.assertEqual(load.destination, "San Antonio, TX")
        self.assertEqual(load.pickup, "Austin, TX")
        self.assertEqual(load.delivery, "San Antonio, TX")
        self.assertEqual(load.loaded_miles, 80)
        self.assertEqual(load.total_miles, 80)
        self.assertEqual(load.posted_trailer_type, "Step Deck")
        self.assertEqual(load.equipment, "Step Deck")

    def test_load_market_loads_combines_imported_manual_and_simulated_loads(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            imported_file = temp_path / "current_loads.json"
            manual_file = temp_path / "manual_test_loads.json"
            simulated_file = temp_path / "current_simulated_loads.json"

            imported_file.write_text(
                json.dumps(
                    [
                        {
                            "pickup": "Dallas, TX",
                            "delivery": "Houston, TX",
                            "rate": 2200,
                            "loaded_miles": 240,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            manual_file.write_text(
                json.dumps(
                    [
                        {
                            "pickup": "Austin, TX",
                            "delivery": "Waco, TX",
                            "rate": 900,
                            "loaded_miles": 100,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            simulated_file.write_text(
                json.dumps(
                    [
                        {
                            "pickup": "Laredo, TX",
                            "delivery": "Dallas, TX",
                            "rate": 1800,
                            "loaded_miles": 430,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            with patch(
                "app.market_intelligence.load_source.MANUAL_TEST_LOADS_FILE",
                manual_file,
            ), patch(
                "app.market_intelligence.load_source.SIMULATED_LOADS_FILE",
                simulated_file,
            ):
                loads = load_market_loads(file_path=imported_file)

            self.assertEqual(len(loads), 3)
            self.assertEqual(
                [load.pickup for load in loads],
                ["Dallas, TX", "Austin, TX", "Laredo, TX"],
            )

    def test_load_market_loads_returns_empty_when_all_sources_empty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            imported_file = temp_path / "current_loads.json"
            manual_file = temp_path / "manual_test_loads.json"
            simulated_file = temp_path / "current_simulated_loads.json"

            imported_file.write_text("[]", encoding="utf-8")
            manual_file.write_text("[]", encoding="utf-8")
            simulated_file.write_text("[]", encoding="utf-8")

            with patch(
                "app.market_intelligence.load_source.MANUAL_TEST_LOADS_FILE",
                manual_file,
            ), patch(
                "app.market_intelligence.load_source.SIMULATED_LOADS_FILE",
                simulated_file,
            ):
                loads = load_market_loads(file_path=imported_file)

            self.assertEqual(loads, [])


if __name__ == "__main__":
    unittest.main()
