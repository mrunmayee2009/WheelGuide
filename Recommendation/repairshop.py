"""
Recommendation/repairshop.py
-------------------------------
Feature 4 (part 2): Wheelchair / mobility-aid repair shop recommendations.

OpenStreetMap doesn't have a dedicated "wheelchair repair shop" tag in
common use, so this searches a few relevant shop/craft categories
(mobility equipment suppliers, orthopedic shops, general repair shops)
and lets the user/admin also add known local repair shops manually to a
local list, which is merged into the results.
"""

import requests
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Maps.maps import distance_km

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

MANUAL_SHOPS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manual_repair_shops.json")

OFFLINE_SAMPLE_SHOPS = [
    {"name": "Mobility Care Repairs", "lat": 19.0790, "lon": 72.8750, "type": "mobility_equipment"},
]


def find_nearby_repair_shops(lat, lon, radius_m=8000):
    """
    Searches OSM for shop=mobility, healthcare=orthotics, and
    shop=medical_supply near the user, then merges in any manually added
    shops from manual_repair_shops.json.
    """
    query = f"""
    [out:json][timeout:15];
    (
      node["shop"="mobility"](around:{radius_m},{lat},{lon});
      node["healthcare"="orthotics"](around:{radius_m},{lat},{lon});
      node["shop"="medical_supply"](around:{radius_m},{lat},{lon});
    );
    out center 15;
    """
    shops = []
    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            shops.append({
                "name": tags.get("name", "Mobility equipment / repair shop"),
                "lat": el.get("lat"),
                "lon": el.get("lon"),
                "type": tags.get("shop", tags.get("healthcare", "mobility")),
                "phone": tags.get("phone", "N/A"),
            })
    except Exception as e:
        print(f"[repairshop.py] Overpass query failed, using offline sample data: {e}")
        shops = list(OFFLINE_SAMPLE_SHOPS)

    shops.extend(_load_manual_shops())

    for s in shops:
        s["distance_km"] = round(distance_km((lat, lon), (s["lat"], s["lon"])), 2)
    return sorted(shops, key=lambda s: s["distance_km"])


def _load_manual_shops():
    if not os.path.exists(MANUAL_SHOPS_PATH):
        return []
    with open(MANUAL_SHOPS_PATH, "r") as f:
        return json.load(f)


def add_manual_repair_shop(name, lat, lon, shop_type="wheelchair_repair", phone="N/A"):
    """Lets an admin/user add a known local wheelchair repair shop that
    isn't on OpenStreetMap yet."""
    shops = _load_manual_shops()
    shops.append({"name": name, "lat": lat, "lon": lon, "type": shop_type, "phone": phone})
    with open(MANUAL_SHOPS_PATH, "w") as f:
        json.dump(shops, f, indent=2)
    return True


if __name__ == "__main__":
    results = find_nearby_repair_shops(19.0760, 72.8777)
    for s in results:
        print(f"{s['name']} - {s['distance_km']} km - type: {s['type']}")
