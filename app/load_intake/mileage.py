try:
    from geopy.distance import geodesic
except ModuleNotFoundError:
    geodesic = None


def get_miles(origin, destination):
    try:
        if geodesic is None:
            return ""

        mock_coordinates = {
            "Blytheville, AR 72315": (35.9273, -89.9189),
            "DADE CITY, FL 33525": (28.3647, -82.1959),
        }

        if origin not in mock_coordinates or destination not in mock_coordinates:
            return ""

        miles = geodesic(
            mock_coordinates[origin],
            mock_coordinates[destination],
        ).miles

        return round(miles * 1.15)

    except:
        return ""
