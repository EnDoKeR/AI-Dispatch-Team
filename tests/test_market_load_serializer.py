import unittest

from app.market_intelligence.market_load_serializer import market_load_to_dict
from app.market_intelligence.market_models import MarketLoad


class TestMarketLoadSerializer(unittest.TestCase):
    def test_market_load_to_dict_preserves_existing_payload_shape(self):
        load = MarketLoad(
            origin="Dallas, TX",
            destination="Houston, TX",
            rate=2200,
            loaded_miles=240,
            empty_miles=20,
            pickup_time="10 AM",
            delivery_time="2 PM",
            weight=36000,
            posted_trailer_type="Flatbed",
            equipment="Flatbed",
            commodity="Steel",
            notes="Clean load",
            parsed_notes={"requires_tarp": False},
            broker_name="Test Broker",
            broker_mc="123456",
            broker_contact="dispatch@example.com",
            broker_contact_raw="Call 555-111-2222 or email dispatch@example.com",
            parsed_contact={
                "email": "dispatch@example.com",
                "phone": "555-111-2222",
            },
            credit_score="95",
            days_to_pay="18",
            reference_id="REF-123",
            is_bookable=True,
            is_private=True,
            is_partial=False,
            is_od=False,
            is_tracking_required=True,
            broker_status="NEEDS CHECK",
            delivery_zone="GOOD / STRONG RELOAD AREA",
            custom_field="kept",
        )
        load.driver_match_status = "MATCH"

        data = market_load_to_dict(load)

        self.assertEqual(data["origin"], "Dallas, TX")
        self.assertEqual(data["destination"], "Houston, TX")
        self.assertEqual(data["pickup"], "Dallas, TX")
        self.assertEqual(data["delivery"], "Houston, TX")
        self.assertEqual(data["rate"], 2200)
        self.assertEqual(data["loaded_miles"], 240)
        self.assertEqual(data["empty_miles"], 20)
        self.assertEqual(data["total_miles"], 260)
        self.assertEqual(data["total_rpm"], 8.46)
        self.assertEqual(data["loaded_rpm"], 9.17)
        self.assertEqual(data["bucket"], "0-450")
        self.assertEqual(data["pickup_time"], "10 AM")
        self.assertEqual(data["delivery_time"], "2 PM")
        self.assertEqual(data["weight"], 36000)
        self.assertEqual(data["posted_trailer_type"], "Flatbed")
        self.assertEqual(data["equipment"], "Flatbed")
        self.assertEqual(data["commodity"], "Steel")
        self.assertEqual(data["notes"], "Clean load")
        self.assertEqual(data["parsed_notes"], {"requires_tarp": False})
        self.assertEqual(data["broker_name"], "Test Broker")
        self.assertEqual(data["broker_mc"], "123456")
        self.assertEqual(data["broker_contact"], "dispatch@example.com")
        self.assertEqual(data["primary_email"], "dispatch@example.com")
        self.assertEqual(data["primary_phone"], "555-111-2222")
        self.assertTrue(data["has_email"])
        self.assertTrue(data["has_phone"])
        self.assertEqual(data["broker_contact_raw"], "Call 555-111-2222 or email dispatch@example.com")
        self.assertEqual(data["parsed_contact"]["phone"], "555-111-2222")
        self.assertEqual(data["credit_score"], "95")
        self.assertEqual(data["days_to_pay"], "18")
        self.assertEqual(data["reference_id"], "REF-123")
        self.assertEqual(data["driver_match_status"], "MATCH")
        self.assertEqual(data["driver_match_notes"], [])
        self.assertEqual(data["opportunity_score"], 80)
        self.assertEqual(data["priority"], "MEDIUM")
        self.assertEqual(data["suggested_action"], "CALL IF AVAILABLE")
        self.assertTrue(data["is_bookable"])
        self.assertTrue(data["is_private"])
        self.assertFalse(data["is_partial"])
        self.assertFalse(data["is_od"])
        self.assertTrue(data["is_tracking_required"])
        self.assertEqual(data["broker_status"], "NEEDS CHECK")
        self.assertEqual(data["delivery_zone"], "GOOD / STRONG RELOAD AREA")
        self.assertEqual(data["extra"], {"custom_field": "kept"})

    def test_market_load_to_dict_matches_market_load_method(self):
        load = MarketLoad(
            pickup="Dallas, TX",
            delivery="Houston, TX",
            rate=2200,
            loaded_miles=240,
        )

        self.assertEqual(market_load_to_dict(load), load.to_dict())


if __name__ == "__main__":
    unittest.main()
