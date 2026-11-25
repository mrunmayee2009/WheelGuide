"""
Maps/offline_maps.py
----------------------
Feature 7: Offline maps.

True "no internet at all" vector maps are a big undertaking (usually done
with MBTiles + a library like `folium` pointed at a local tile server, or
Mapbox GL's offline packs). For a diploma project, this module implements
a practical, working version:

 1. WHILE ONLINE: download and cache the map tile images for an area
    around the user's frequent locations (tile_cache/ folder).
 2. WHILE OFFLINE: build a folium map that reads tiles from the local
    cache folder instead of the internet, so previously-visited areas are
    still viewable with no connection.

This is the same technique real offline-map apps use under the hood.
"""

import os
import math
import requests
import folium
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TILE_CACHE_DIR

TILE_SERVER = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
HEADERS = {"User-Agent": "WheelGuideApp/1.0 (student diploma project)"}


def _deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def cache_area_tiles(center_lat, center_lon, zoom_levels=(13, 14, 15), tile_radius=2):
    """
    Downloads and saves tiles around a center point for offline use later.
    Call this while the user has internet (e.g. at home before a trip).
    tile_radius: how many tiles out from the center tile to also cache.
    """
    os.makedirs(TILE_CACHE_DIR, exist_ok=True)
    downloaded, failed = 0, 0

    for zoom in zoom_levels:
        cx, cy = _deg2num(center_lat, center_lon, zoom)
        for dx in range(-tile_radius, tile_radius + 1):
            for dy in range(-tile_radius, tile_radius + 1):
                x, y = cx + dx, cy + dy
                tile_dir = os.path.join(TILE_CACHE_DIR, str(zoom), str(x))
                tile_path = os.path.join(tile_dir, f"{y}.png")
                if os.path.exists(tile_path):
                    continue
                os.makedirs(tile_dir, exist_ok=True)
                url = TILE_SERVER.format(z=zoom, x=x, y=y)
                try:
                    resp = requests.get(url, headers=HEADERS, timeout=5)
                    if resp.status_code == 200:
                        with open(tile_path, "wb") as f:
                            f.write(resp.content)
                        downloaded += 1
                    else:
                        failed += 1
                except requests.RequestException:
                    failed += 1

    return {"downloaded": downloaded, "failed": failed, "cache_dir": TILE_CACHE_DIR}


def is_area_cached(center_lat, center_lon, zoom=14):
    x, y = _deg2num(center_lat, center_lon, zoom)
    return os.path.exists(os.path.join(TILE_CACHE_DIR, str(zoom), str(x), f"{y}.png"))


def build_offline_map(center, zoom_start=14, save_path=None):
    """
    Builds a folium map that loads tiles from the local file cache
    (file:// URL) instead of the internet. Only works well for areas you
    already ran cache_area_tiles() on.
    """
    tiles_template = os.path.join(TILE_CACHE_DIR, "{z}", "{x}", "{y}.png")
    # folium needs a URL-style template; convert Windows backslashes if any
    tiles_url = "file://" + tiles_template.replace(os.sep, "/")

    fmap = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles=tiles_url,
        attr="Offline cached OpenStreetMap tiles (WheelGuide)",
    )
    folium.Marker(center, popup="You are here (offline mode)").add_to(fmap)

    if save_path is None:
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offline_map.html")
    fmap.save(save_path)
    return save_path


if __name__ == "__main__":
    # Example: cache tiles for Mumbai while online
    result = cache_area_tiles(19.0760, 72.8777)
    print("Tile caching result:", result)
    path = build_offline_map((19.0760, 72.8777))
    print("Offline map saved to:", path)
