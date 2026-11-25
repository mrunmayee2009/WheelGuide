"""
Maps/maps.py
-------------
Core mapping helpers: geocoding addresses, searching nearby places, and
rendering an interactive folium map (saved as HTML, opened in a browser
from the GUI).
"""

import os
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import folium

geolocator = Nominatim(user_agent="wheelguide_app")


def geocode_address(address: str):
    """Returns (lat, lon) for a text address, or None if not found."""
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return (location.latitude, location.longitude)
        return None
    except Exception as e:
        print(f"[maps.py] geocoding failed: {e}")
        return None


def reverse_geocode(lat: float, lon: float):
    """Returns a human-readable address for coordinates."""
    try:
        location = geolocator.reverse((lat, lon), timeout=10)
        return location.address if location else "Unknown location"
    except Exception as e:
        print(f"[maps.py] reverse geocoding failed: {e}")
        return "Unknown location"


def distance_km(point_a, point_b):
    """point_a / point_b are (lat, lon) tuples."""
    return geodesic(point_a, point_b).km


def build_map(center, markers=None, zoom_start=15, save_path=None):
    """
    center: (lat, lon)
    markers: list of dicts: {"location": (lat,lon), "popup": str,
                              "color": "green"/"orange"/"red"}
    Returns the path to the saved HTML map file.
    """
    fmap = folium.Map(location=center, zoom_start=zoom_start, tiles="OpenStreetMap")

    folium.Marker(
        location=center, popup="You are here",
        icon=folium.Icon(color="blue", icon="user"),
    ).add_to(fmap)

    if markers:
        for m in markers:
            folium.Marker(
                location=m["location"],
                popup=m.get("popup", ""),
                icon=folium.Icon(color=m.get("color", "green"), icon=m.get("icon", "info-sign")),
            ).add_to(fmap)

    if save_path is None:
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "current_map.html")

    fmap.save(save_path)
    return save_path


def accessibility_color(score: float) -> str:
    """Maps an accessibility score (0-10) to a marker color for the map."""
    if score >= 7:
        return "green"
    elif score >= 4:
        return "orange"
    return "red"


if __name__ == "__main__":
    coords = geocode_address("Mumbai, India")
    print("Geocoded:", coords)
    if coords:
        path = build_map(coords, markers=[
            {"location": coords, "popup": "Sample accessible place", "color": "green"}
        ])
        print("Map saved to:", path)
