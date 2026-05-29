import unittest
from dataclasses import dataclass, field, replace

from app.market_intelligence.reload_chain import (
    build_chain_candidates,
    build_chain_score,
    chain_identity,
    city_state_key,
    is_good_reload_load,
    is_same_load,
    is_strong_first_load,
    is_wrong_direction_block,
    load_identity,
    pickup_near_first_delivery,
    same_state,
)


@dataclass
class FakeSearchRequest:
    driver_name: str = "Alex"
    max_weight: int = 45000
    min_total_rpm: float = 2.0


@dataclass
class FakeLoad:
    pickup: str = "Dallas, TX"
    delivery: str = "Denver, CO"
    rate: int = 3500
    loaded_miles: int = 1000
    empty_miles: int = 80
    total_miles: int = 1080
    weight: int = 42000
    total_rpm: float = 3.24
    broker_status: str = "BUY"
    reference_id: str = ""
    is_od: bool = False
    is_overweight: bool = False
    driver_match_notes: list = field(default_factory=list)
    target_state_match: bool = True
    target_city_match: bool = False
    distances: dict = field(default_factory=dict)

    def matches_target_state_or_region(self, search_request):
        return self.target_state_match

    def matches_target_city_radius(self, search_request):
        return self.target_city_match

    def distance_between_known_cities(self, location_a, location_b):
        return self.distances.get((location_a, location_b))


class TestReloadChain(unittest.TestCase):
    def test_load_identity_uses_reference_id_when_available(self):
        load = FakeLoad(reference_id=" REF-123 ")

        self.assertEqual(load_identity(load), "ref-123")

    def test_load_identity_falls_back_to_route_and_metrics(self):
        load = FakeLoad(reference_id="")

        self.assertEqual(
            load_identity(load),
            "dallas, tx|denver, co|3500|1000|42000",
        )

    def test_chain_identity_includes_driver_and_both_loads(self):
        first_load = FakeLoad(reference_id="FIRST-1")
        reload_load = FakeLoad(reference_id="RELOAD-2")

        self.assertEqual(
            chain_identity(first_load, reload_load, FakeSearchRequest()),
            "alex|first-1|reload-2",
        )

    def test_is_same_load_uses_load_identity(self):
        self.assertTrue(
            is_same_load(
                FakeLoad(reference_id="LOAD-1"),
                FakeLoad(reference_id=" load-1 "),
            )
        )
        self.assertFalse(
            is_same_load(
                FakeLoad(reference_id="LOAD-1"),
                FakeLoad(reference_id="LOAD-2"),
            )
        )

    def test_is_strong_first_load_accepts_clean_high_value_load(self):
        self.assertTrue(is_strong_first_load(FakeLoad()))

    def test_is_strong_first_load_rejects_hard_risk_and_weak_economics(self):
        cases = [
            replace(FakeLoad(), is_od=True),
            replace(FakeLoad(), is_overweight=True),
            replace(FakeLoad(), weight=46001),
            replace(FakeLoad(), broker_status="NO BUY"),
            replace(FakeLoad(), rate=2999),
            replace(FakeLoad(), total_rpm=2.99),
            replace(FakeLoad(), empty_miles=151),
        ]

        for load in cases:
            with self.subTest(load=load):
                self.assertFalse(is_strong_first_load(load))

    def test_is_good_reload_load_accepts_clean_target_match(self):
        self.assertTrue(is_good_reload_load(FakeLoad(), FakeSearchRequest()))

    def test_is_good_reload_load_allows_target_city_radius_fallback(self):
        load = FakeLoad(target_state_match=False, target_city_match=True)

        self.assertTrue(is_good_reload_load(load, FakeSearchRequest()))

    def test_is_good_reload_load_rejects_hard_risk_and_weak_economics(self):
        search_request = FakeSearchRequest()
        cases = [
            replace(FakeLoad(), is_od=True),
            replace(FakeLoad(), is_overweight=True),
            replace(FakeLoad(), weight=48001),
            replace(FakeLoad(), broker_status="NO BUY"),
            replace(FakeLoad(), rate=1999),
            replace(FakeLoad(), total_rpm=1.99),
            replace(FakeLoad(), target_state_match=False, target_city_match=False),
        ]

        for load in cases:
            with self.subTest(load=load):
                self.assertFalse(is_good_reload_load(load, search_request))

    def test_city_state_key_normalizes_city_and_state(self):
        self.assertEqual(city_state_key("Denver, CO 80216"), "Denver, CO")
        self.assertEqual(city_state_key("Denver"), "Denver")

    def test_same_state_requires_comma_locations_and_matching_state(self):
        self.assertTrue(same_state("Denver, CO", "Boulder, CO"))
        self.assertFalse(same_state("Denver, CO", "Dallas, TX"))
        self.assertFalse(same_state("Denver", "Boulder, CO"))

    def test_pickup_near_first_delivery_uses_known_city_distance(self):
        first_load = FakeLoad(
            delivery="Denver, CO",
            distances={("Denver, CO", "Boulder, CO"): 35},
        )
        reload_load = FakeLoad(pickup="Boulder, CO")

        self.assertTrue(pickup_near_first_delivery(first_load, reload_load))

    def test_pickup_near_first_delivery_rejects_known_city_distance_over_limit(self):
        first_load = FakeLoad(
            delivery="Denver, CO",
            distances={("Denver, CO", "Cheyenne, WY"): 200},
        )
        reload_load = FakeLoad(pickup="Cheyenne, WY")

        self.assertFalse(pickup_near_first_delivery(first_load, reload_load))

    def test_pickup_near_first_delivery_falls_back_to_same_state(self):
        self.assertTrue(
            pickup_near_first_delivery(
                FakeLoad(delivery="Denver, CO"),
                FakeLoad(pickup="Boulder, CO"),
            )
        )
        self.assertFalse(
            pickup_near_first_delivery(
                FakeLoad(delivery="Denver, CO"),
                FakeLoad(pickup="Dallas, TX"),
            )
        )

    def test_is_wrong_direction_block_recognizes_target_notes(self):
        self.assertTrue(
            is_wrong_direction_block(
                FakeLoad(
                    driver_match_notes=[
                        "Delivery does not match target direction",
                    ]
                )
            )
        )
        self.assertTrue(
            is_wrong_direction_block(
                FakeLoad(
                    driver_match_notes=[
                        "Delivery does not match strict target",
                    ]
                )
            )
        )
        self.assertFalse(is_wrong_direction_block(FakeLoad(driver_match_notes=[])))
