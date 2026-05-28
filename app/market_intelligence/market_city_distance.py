KNOWN_CITY_DISTANCES = {
    ("englewood, co", "denver, co"): 15,
    ("denver, co", "englewood, co"): 15,

    ("atlanta, ga", "marietta, ga"): 25,
    ("marietta, ga", "atlanta, ga"): 25,

    ("atlanta, ga", "fairburn, ga"): 20,
    ("fairburn, ga", "atlanta, ga"): 20,

    ("chicago, il", "dekalb, il"): 65,
    ("dekalb, il", "chicago, il"): 65,

    ("tampa, fl", "lakeland, fl"): 35,
    ("lakeland, fl", "tampa, fl"): 35,

    ("orlando, fl", "davenport, fl"): 35,
    ("davenport, fl", "orlando, fl"): 35,

    ("orlando, fl", "sanford, fl"): 25,
    ("sanford, fl", "orlando, fl"): 25,

    ("ocala, fl", "groveland, fl"): 55,
    ("groveland, fl", "ocala, fl"): 55,

    ("ocala, fl", "gainesville, fl"): 40,
    ("gainesville, fl", "ocala, fl"): 40,

    ("salt lake city, ut", "ogden, ut"): 40,
    ("ogden, ut", "salt lake city, ut"): 40,

    ("stockton, ca", "sacramento, ca"): 50,
    ("sacramento, ca", "stockton, ca"): 50,

    ("oakland, ca", "san leandro, ca"): 10,
    ("san leandro, ca", "oakland, ca"): 10,

    ("oakland, ca", "stockton, ca"): 75,
    ("stockton, ca", "oakland, ca"): 75,
}


def distance_between_known_cities(city_a, city_b):
    city_a = str(city_a or "").strip().lower()
    city_b = str(city_b or "").strip().lower()

    if not city_a or not city_b:
        return 9999

    if city_a == city_b:
        return 0

    return KNOWN_CITY_DISTANCES.get((city_a, city_b), 9999)
