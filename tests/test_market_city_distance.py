import unittest

from app.market_intelligence.market_city_distance import distance_between_known_cities


class TestMarketCityDistance(unittest.TestCase):
    def test_distance_returns_9999_when_city_is_missing(self):
        self.assertEqual(distance_between_known_cities("", "Denver, CO"), 9999)
        self.assertEqual(distance_between_known_cities("Denver, CO", ""), 9999)
        self.assertEqual(distance_between_known_cities(None, "Denver, CO"), 9999)

    def test_distance_returns_zero_for_same_city(self):
        self.assertEqual(
            distance_between_known_cities("Denver, CO", "Denver, CO"),
            0,
        )

    def test_distance_returns_known_distance_in_both_directions(self):
        self.assertEqual(
            distance_between_known_cities("Englewood, CO", "Denver, CO"),
            15,
        )
        self.assertEqual(
            distance_between_known_cities("Denver, CO", "Englewood, CO"),
            15,
        )

    def test_distance_normalizes_spacing_and_case(self):
        self.assertEqual(
            distance_between_known_cities("  ENGLEWOOD, CO  ", " denver, co "),
            15,
        )

    def test_distance_returns_9999_for_unknown_pair(self):
        self.assertEqual(
            distance_between_known_cities("Unknown, XX", "Nowhere, YY"),
            9999,
        )


if __name__ == "__main__":
    unittest.main()
