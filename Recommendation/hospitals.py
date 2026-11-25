"""
Recommendation/hospitals.py
----------------------------

WheelGuide - Nearby Hospital Recommendation Engine

Purpose
-------
Find real hospitals near the user's current location using
OpenStreetMap / Overpass API.

The module is designed to work with WheelGuide's existing
architecture and provides:

    find_nearby_hospitals(lat, lon)

without requiring changes to existing GUI code.

Features
--------
* OpenStreetMap hospital search
* Multiple Overpass API servers
* Retry and timeout handling
* HTTP error handling
* Proper request headers
* Radius-based search
* Distance calculation
* Result limiting
* Duplicate removal
* Node / Way / Relation support
* Wheelchair accessibility information
* Emergency information
* Phone number
* Website
* Opening hours
* Address
* Operator
* Hospital type
* OSM ID
* Map coordinates
* Local result cache
* Offline fallback
* Search metadata
* Safe handling of malformed OSM data
* GUI-friendly return structure

Important
---------
OpenStreetMap data is community-maintained. Missing wheelchair
information means UNKNOWN, not accessible.

No accessibility feature should be invented by this module.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import threading
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests


# ---------------------------------------------------------------------------
# PROJECT ROOT
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


# ---------------------------------------------------------------------------
# EXISTING WHEELGUIDE DISTANCE FUNCTION
# ---------------------------------------------------------------------------

try:
    from Maps.maps import distance_km

except Exception:

    def distance_km(
        point1,
        point2
    ):
        """
        Fallback Haversine distance calculation.

        Used only if Maps.maps.distance_km cannot be imported.
        """

        from math import radians, sin, cos, sqrt, atan2

        lat1, lon1 = point1
        lat2, lon2 = point2

        earth_radius_km = 6371.0088

        d_lat = radians(lat2 - lat1)
        d_lon = radians(lon2 - lon1)

        a = (
            sin(d_lat / 2) ** 2
            +
            cos(radians(lat1))
            *
            cos(radians(lat2))
            *
            sin(d_lon / 2) ** 2
        )

        c = 2 * atan2(
            sqrt(a),
            sqrt(1 - a)
        )

        return earth_radius_km * c


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

DEFAULT_RADIUS_M = 5000

MIN_RADIUS_M = 100

MAX_RADIUS_M = 50000

DEFAULT_LIMIT = 10

MAX_LIMIT = 100

REQUEST_TIMEOUT = 25

MAX_RETRIES_PER_SERVER = 2

CACHE_TTL_SECONDS = 300

USER_AGENT = (
    "WheelGuide/1.0 "
    "(wheelchair accessibility project; "
    "OpenStreetMap data consumer)"
)

REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
}


# ---------------------------------------------------------------------------
# OFFLINE FALLBACK DATA
# ---------------------------------------------------------------------------

OFFLINE_SAMPLE_HOSPITALS = [
    {
        "name": "City General Hospital",
        "lat": 19.0800,
        "lon": 72.8810,
        "wheelchair": "yes",
        "phone": "N/A",
        "website": "N/A",
        "opening_hours": "24/7",
        "emergency": "yes",
        "address": "Mumbai",
        "operator": "N/A",
        "hospital_type": "general hospital",
    },
    {
        "name": "Sunrise Multi-Specialty Hospital",
        "lat": 19.0700,
        "lon": 72.8700,
        "wheelchair": "unknown",
        "phone": "N/A",
        "website": "N/A",
        "opening_hours": "N/A",
        "emergency": "unknown",
        "address": "Mumbai",
        "operator": "N/A",
        "hospital_type": "multi-specialty hospital",
    },
]


# ---------------------------------------------------------------------------
# CACHE
# ---------------------------------------------------------------------------

_CACHE: Dict[
    Tuple[float, float, int, int],
    Dict[str, Any]
] = {}

_CACHE_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# SESSION
# ---------------------------------------------------------------------------

_SESSION = requests.Session()

_SESSION.headers.update(
    REQUEST_HEADERS
)


# ---------------------------------------------------------------------------
# BASIC HELPERS
# ---------------------------------------------------------------------------

def _safe_float(
    value: Any,
    default: float = 0.0
) -> float:
    """
    Safely convert a value to float.
    """

    try:
        return float(value)

    except (
        TypeError,
        ValueError
    ):
        return default


def _safe_int(
    value: Any,
    default: int = 0
) -> int:
    """
    Safely convert a value to integer.
    """

    try:
        return int(value)

    except (
        TypeError,
        ValueError
    ):
        return default


def _clean_text(
    value: Any,
    default: str = ""
) -> str:
    """
    Convert a value to clean text.
    """

    if value is None:
        return default

    text = str(value)

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def _normalize_coordinate(
    value: Any
) -> Optional[float]:
    """
    Normalize latitude/longitude values.
    """

    try:

        number = float(value)

    except (
        TypeError,
        ValueError
    ):

        return None

    if not -180 <= number <= 180:
        return None

    return number


def _clamp_radius(
    radius_m: Any
) -> int:
    """
    Keep search radius within safe limits.
    """

    radius = _safe_int(
        radius_m,
        DEFAULT_RADIUS_M
    )

    return max(
        MIN_RADIUS_M,
        min(
            MAX_RADIUS_M,
            radius
        )
    )


def _clamp_limit(
    limit: Any
) -> int:
    """
    Keep result limit within safe limits.
    """

    value = _safe_int(
        limit,
        DEFAULT_LIMIT
    )

    return max(
        1,
        min(
            MAX_LIMIT,
            value
        )
    )


# ---------------------------------------------------------------------------
# CACHE KEY
# ---------------------------------------------------------------------------

def _cache_key(
    lat: float,
    lon: float,
    radius_m: int,
    limit: int
) -> Tuple[float, float, int, int]:
    """
    Generate stable cache key.
    """

    return (
        round(lat, 4),
        round(lon, 4),
        radius_m,
        limit
    )


# ---------------------------------------------------------------------------
# CACHE MANAGEMENT
# ---------------------------------------------------------------------------

def _get_cached(
    key
) -> Optional[Dict[str, Any]]:
    """
    Return cached data if still valid.
    """

    with _CACHE_LOCK:

        cached = _CACHE.get(
            key
        )

        if not cached:
            return None

        timestamp = cached.get(
            "timestamp",
            0
        )

        if (
            time.time()
            -
            timestamp
            >
            CACHE_TTL_SECONDS
        ):

            _CACHE.pop(
                key,
                None
            )

            return None

        return copy.deepcopy(
            cached.get(
                "data"
            )
        )


def _store_cache(
    key,
    data
):
    """
    Store a deep copy in cache.
    """

    with _CACHE_LOCK:

        _CACHE[key] = {
            "timestamp": time.time(),
            "data": copy.deepcopy(data)
        }


def clear_cache():
    """
    Clear hospital search cache.

    Useful after the user changes location
    or wants fresh results.
    """

    with _CACHE_LOCK:

        _CACHE.clear()


# ---------------------------------------------------------------------------
# OSM QUERY
# ---------------------------------------------------------------------------

def _build_overpass_query(
    lat: float,
    lon: float,
    radius_m: int,
    limit: int
) -> str:
    """
    Build a robust Overpass query.

    Searches:
        node
        way
        relation

    Hospital-like healthcare facilities are included.
    """

    query = f"""
[out:json][timeout:20];

(
    node["amenity"="hospital"](around:{radius_m},{lat},{lon});
    way["amenity"="hospital"](around:{radius_m},{lat},{lon});
    relation["amenity"="hospital"](around:{radius_m},{lat},{lon});

    node["healthcare"="hospital"](around:{radius_m},{lat},{lon});
    way["healthcare"="hospital"](around:{radius_m},{lat},{lon});
    relation["healthcare"="hospital"](around:{radius_m},{lat},{lon});
);

out center tags {limit};
"""

    return query


# ---------------------------------------------------------------------------
# SERVER REQUEST
# ---------------------------------------------------------------------------

def _request_overpass(
    server: str,
    query: str
) -> Optional[Dict[str, Any]]:
    """
    Execute an Overpass request.

    Returns
    -------
    dict or None
    """

    for attempt in range(
        MAX_RETRIES_PER_SERVER
    ):

        try:

            response = _SESSION.post(
                server,
                data={
                    "data": query
                },
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT
            )

            # ---------------------------------------------------------------
            # Rate limit
            # ---------------------------------------------------------------

            if response.status_code == 429:

                retry_after = response.headers.get(
                    "Retry-After"
                )

                try:
                    wait_seconds = min(
                        10,
                        max(
                            1,
                            int(
                                retry_after
                            )
                        )
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    wait_seconds = 3

                time.sleep(
                    wait_seconds
                )

                continue

            # ---------------------------------------------------------------
            # Server errors
            # ---------------------------------------------------------------

            if response.status_code >= 500:

                if attempt + 1 < MAX_RETRIES_PER_SERVER:

                    time.sleep(
                        1.5 * (attempt + 1)
                    )

                    continue

                return None

            # ---------------------------------------------------------------
            # Client errors
            # ---------------------------------------------------------------

            if response.status_code == 406:

                # Some Overpass servers reject particular
                # request/header combinations. Try another server.
                return None

            response.raise_for_status()

            # ---------------------------------------------------------------
            # Parse JSON
            # ---------------------------------------------------------------

            try:

                data = response.json()

            except ValueError:

                return None

            if not isinstance(
                data,
                dict
            ):

                return None

            return data

        except requests.Timeout:

            if attempt + 1 < MAX_RETRIES_PER_SERVER:

                time.sleep(
                    1.5 * (attempt + 1)
                )

                continue

            return None

        except requests.ConnectionError:

            if attempt + 1 < MAX_RETRIES_PER_SERVER:

                time.sleep(
                    1.5 * (attempt + 1)
                )

                continue

            return None

        except requests.RequestException:

            return None

        except Exception:

            return None

    return None


# ---------------------------------------------------------------------------
# OSM TAG HELPERS
# ---------------------------------------------------------------------------

def _get_tag(
    tags: Dict[str, Any],
    *keys: str,
    default: str = "N/A"
) -> str:
    """
    Return the first useful OSM tag.
    """

    for key in keys:

        value = tags.get(
            key
        )

        if value is None:
            continue

        text = _clean_text(
            value
        )

        if text:
            return text

    return default


def _normalize_wheelchair(
    value: Any
) -> str:
    """
    Normalize OSM wheelchair tag.

    Possible values:
        yes
        no
        limited
        unknown
    """

    text = _clean_text(
        value,
        "unknown"
    ).lower()

    if text in {
        "yes",
        "true",
        "accessible"
    }:

        return "yes"

    if text in {
        "no",
        "false",
        "inaccessible"
    }:

        return "no"

    if text in {
        "limited",
        "partial"
    }:

        return "limited"

    return "unknown"


def _normalize_emergency(
    value: Any
) -> str:
    """
    Normalize emergency tag.
    """

    text = _clean_text(
        value,
        "unknown"
    ).lower()

    if text in {
        "yes",
        "true"
    }:

        return "yes"

    if text in {
        "no",
        "false"
    }:

        return "no"

    return "unknown"


# ---------------------------------------------------------------------------
# ADDRESS
# ---------------------------------------------------------------------------

def _build_address(
    tags: Dict[str, Any]
) -> str:
    """
    Build a human-readable address from OSM address tags.
    """

    parts = []

    for key in [
        "addr:housenumber",
        "addr:street",
        "addr:suburb",
        "addr:city",
        "addr:state",
        "addr:postcode"
    ]:

        value = _clean_text(
            tags.get(key)
        )

        if value:
            parts.append(
                value
            )

    if parts:
        return ", ".join(
            parts
        )

    return _get_tag(
        tags,
        "addr:full",
        default="N/A"
    )


# ---------------------------------------------------------------------------
# COORDINATES
# ---------------------------------------------------------------------------

def _extract_coordinates(
    element: Dict[str, Any]
) -> Optional[Tuple[float, float]]:
    """
    Extract coordinates from OSM node/way/relation.
    """

    element_type = element.get(
        "type"
    )

    # Node
    if element_type == "node":

        lat = _normalize_coordinate(
            element.get("lat")
        )

        lon = _normalize_coordinate(
            element.get("lon")
        )

        if lat is None or lon is None:
            return None

        return lat, lon

    # Way / relation center
    center = element.get(
        "center"
    )

    if isinstance(
        center,
        dict
    ):

        lat = _normalize_coordinate(
            center.get("lat")
        )

        lon = _normalize_coordinate(
            center.get("lon")
        )

        if lat is None or lon is None:
            return None

        return lat, lon

    return None


# ---------------------------------------------------------------------------
# HOSPITAL NORMALIZATION
# ---------------------------------------------------------------------------

def _normalize_hospital(
    element: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Convert raw OSM element into WheelGuide hospital object.
    """

    coordinates = _extract_coordinates(
        element
    )

    if coordinates is None:
        return None

    lat, lon = coordinates

    tags = element.get(
        "tags",
        {}
    )

    if not isinstance(
        tags,
        dict
    ):

        tags = {}

    hospital_id = (
        f"{element.get('type', 'unknown')}:"
        f"{element.get('id', 'unknown')}"
    )

    name = _get_tag(
        tags,
        "name",
        "official_name",
        "short_name",
        default="Unnamed hospital"
    )

    wheelchair = _normalize_wheelchair(
        tags.get(
            "wheelchair"
        )
    )

    emergency = _normalize_emergency(
        tags.get(
            "emergency"
        )
    )

    phone = _get_tag(
        tags,
        "phone",
        "contact:phone",
        "contact:mobile",
        default="N/A"
    )

    website = _get_tag(
        tags,
        "website",
        "contact:website",
        "url",
        default="N/A"
    )

    opening_hours = _get_tag(
        tags,
        "opening_hours",
        default="N/A"
    )

    operator = _get_tag(
        tags,
        "operator",
        default="N/A"
    )

    hospital_type = _get_tag(
        tags,
        "healthcare:speciality",
        "healthcare",
        "type",
        default="hospital"
    )

    address = _build_address(
        tags
    )

    return {
        "id": hospital_id,

        "osm_id": element.get(
            "id"
        ),

        "osm_type": element.get(
            "type",
            "unknown"
        ),

        "name": name,

        "lat": lat,

        "lon": lon,

        "wheelchair": wheelchair,

        "phone": phone,

        "website": website,

        "opening_hours": opening_hours,

        "emergency": emergency,

        "address": address,

        "operator": operator,

        "hospital_type": hospital_type,

        "source": "OpenStreetMap",
    }


# ---------------------------------------------------------------------------
# DUPLICATE KEY
# ---------------------------------------------------------------------------

def _hospital_duplicate_key(
    hospital: Dict[str, Any]
) -> str:
    """
    Create duplicate-detection key.

    Prefer OSM ID. Otherwise use normalized name + coordinates.
    """

    if hospital.get(
        "id"
    ):

        return str(
            hospital["id"]
        )

    name = _clean_text(
        hospital.get(
            "name"
        ),
        "unknown"
    ).lower()

    lat = round(
        _safe_float(
            hospital.get(
                "lat"
            )
        ),
        5
    )

    lon = round(
        _safe_float(
            hospital.get(
                "lon"
            )
        ),
        5
    )

    raw = (
        f"{name}|{lat}|{lon}"
    )

    return hashlib.sha1(
        raw.encode(
            "utf-8"
        )
    ).hexdigest()


# ---------------------------------------------------------------------------
# REMOVE DUPLICATES
# ---------------------------------------------------------------------------

def _remove_duplicates(
    hospitals: Iterable[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Remove duplicate hospital entries.
    """

    unique = {}

    for hospital in hospitals:

        key = _hospital_duplicate_key(
            hospital
        )

        if key not in unique:

            unique[key] = hospital

    return list(
        unique.values()
    )


# ---------------------------------------------------------------------------
# DISTANCE
# ---------------------------------------------------------------------------

def _add_distances(
    hospitals: List[Dict[str, Any]],
    user_lat: float,
    user_lon: float
) -> List[Dict[str, Any]]:
    """
    Add distance from user to every hospital.
    """

    results = []

    for hospital in hospitals:

        lat = _safe_float(
            hospital.get(
                "lat"
            )
        )

        lon = _safe_float(
            hospital.get(
                "lon"
            )
        )

        try:

            distance = distance_km(
                (user_lat, user_lon),
                (lat, lon)
            )

        except Exception:

            distance = 0.0

        item = dict(
            hospital
        )

        item["distance_km"] = round(
            _safe_float(
                distance
            ),
            2
        )

        results.append(
            item
        )

    results.sort(
        key=lambda item:
            item.get(
                "distance_km",
                float("inf")
            )
    )

    return results


# ---------------------------------------------------------------------------
# WHEELCHAIR RANKING
# ---------------------------------------------------------------------------

def _wheelchair_rank(
    value: str
) -> int:
    """
    Rank wheelchair accessibility.

    Higher is better.
    """

    value = _normalize_wheelchair(
        value
    )

    if value == "yes":
        return 3

    if value == "limited":
        return 2

    if value == "unknown":
        return 1

    return 0


# ---------------------------------------------------------------------------
# OPTIONAL ACCESSIBILITY SORT
# ---------------------------------------------------------------------------

def _sort_hospitals(
    hospitals: List[Dict[str, Any]],
    prioritize_accessibility: bool
) -> List[Dict[str, Any]]:
    """
    Sort hospitals.

    Default:
        nearest first

    Accessibility mode:
        wheelchair accessibility first,
        then distance.
    """

    if not prioritize_accessibility:

        return sorted(
            hospitals,
            key=lambda h:
                h.get(
                    "distance_km",
                    float("inf")
                )
        )

    return sorted(
        hospitals,
        key=lambda h: (
            -_wheelchair_rank(
                h.get(
                    "wheelchair",
                    "unknown"
                )
            ),
            h.get(
                "distance_km",
                float("inf")
            )
        )
    )


# ---------------------------------------------------------------------------
# OFFLINE RESULTS
# ---------------------------------------------------------------------------

def _offline_results(
    lat: float,
    lon: float,
    limit: int,
    prioritize_accessibility: bool
) -> List[Dict[str, Any]]:
    """
    Return offline sample hospitals.

    This keeps WheelGuide usable without internet.
    """

    hospitals = copy.deepcopy(
        OFFLINE_SAMPLE_HOSPITALS
    )

    hospitals = _add_distances(
        hospitals,
        lat,
        lon
    )

    hospitals = _sort_hospitals(
        hospitals,
        prioritize_accessibility
    )

    return hospitals[
        :limit
    ]


# ---------------------------------------------------------------------------
# RESULT METADATA
# ---------------------------------------------------------------------------

def _build_result_metadata(
    source: str,
    latitude: float,
    longitude: float,
    radius_m: int,
    hospitals: List[Dict[str, Any]],
    server: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build metadata useful to GUI/debugging.
    """

    return {
        "source": source,

        "latitude": latitude,

        "longitude": longitude,

        "radius_m": radius_m,

        "result_count": len(
            hospitals
        ),

        "server": server,

        "timestamp": time.time(),
    }


# ---------------------------------------------------------------------------
# MAIN SEARCH FUNCTION
# ---------------------------------------------------------------------------

def find_nearby_hospitals(
    lat,
    lon,
    radius_m=DEFAULT_RADIUS_M,
    limit=DEFAULT_LIMIT,
    prioritize_accessibility=False,
    use_cache=True
) -> List[Dict[str, Any]]:
    """
    Find nearby hospitals.

    Parameters
    ----------
    lat:
        User latitude.

    lon:
        User longitude.

    radius_m:
        Search radius in meters.

    limit:
        Maximum number of hospitals.

    prioritize_accessibility:
        If True, hospitals with known wheelchair accessibility
        are ranked before unknown/inaccessible hospitals.

    use_cache:
        If True, use short-term local cache.

    Returns
    -------
    list

    Each hospital contains:

        id
        osm_id
        osm_type
        name
        lat
        lon
        distance_km
        wheelchair
        phone
        website
        opening_hours
        emergency
        address
        operator
        hospital_type
        source

    The function NEVER raises an Overpass network exception.
    It falls back to offline results.
    """

    # -----------------------------------------------------------------------
    # Validate coordinates
    # -----------------------------------------------------------------------

    latitude = _normalize_coordinate(
        lat
    )

    longitude = _normalize_coordinate(
        lon
    )

    if latitude is None:

        return []

    if longitude is None:

        return []

    # Latitude has a stricter valid range.
    if not -90 <= latitude <= 90:

        return []

    radius = _clamp_radius(
        radius_m
    )

    result_limit = _clamp_limit(
        limit
    )

    key = _cache_key(
        latitude,
        longitude,
        radius,
        result_limit
    )

    # -----------------------------------------------------------------------
    # Cache
    # -----------------------------------------------------------------------

    if use_cache:

        cached = _get_cached(
            key
        )

        if cached is not None:

            return cached

    # -----------------------------------------------------------------------
    # Build query
    # -----------------------------------------------------------------------

    query = _build_overpass_query(
        latitude,
        longitude,
        radius,
        result_limit
    )

    raw_data = None

    successful_server = None

    # -----------------------------------------------------------------------
    # Try multiple Overpass servers
    # -----------------------------------------------------------------------

    for server in OVERPASS_SERVERS:

        data = _request_overpass(
            server,
            query
        )

        if data is None:
            continue

        raw_data = data

        successful_server = server

        break

    # -----------------------------------------------------------------------
    # Network failed
    # -----------------------------------------------------------------------

    if raw_data is None:

        results = _offline_results(
            latitude,
            longitude,
            result_limit,
            prioritize_accessibility
        )

        for item in results:

            item["source"] = (
                "offline_sample"
            )

        if use_cache:

            _store_cache(
                key,
                results
            )

        return results

    # -----------------------------------------------------------------------
    # Parse OSM
    # -----------------------------------------------------------------------

    elements = raw_data.get(
        "elements",
        []
    )

    if not isinstance(
        elements,
        list
    ):

        elements = []

    hospitals = []

    for element in elements:

        if not isinstance(
            element,
            dict
        ):
            continue

        hospital = _normalize_hospital(
            element
        )

        if hospital is None:
            continue

        hospitals.append(
            hospital
        )

    # -----------------------------------------------------------------------
    # Remove duplicates
    # -----------------------------------------------------------------------

    hospitals = _remove_duplicates(
        hospitals
    )

    # -----------------------------------------------------------------------
    # Calculate distance
    # -----------------------------------------------------------------------

    hospitals = _add_distances(
        hospitals,
        latitude,
        longitude
    )

    # -----------------------------------------------------------------------
    # Sort
    # -----------------------------------------------------------------------

    hospitals = _sort_hospitals(
        hospitals,
        prioritize_accessibility
    )

    # -----------------------------------------------------------------------
    # Limit
    # -----------------------------------------------------------------------

    hospitals = hospitals[
        :result_limit
    ]

    # -----------------------------------------------------------------------
    # If API returned nothing
    # -----------------------------------------------------------------------

    if not hospitals:

        hospitals = _offline_results(
            latitude,
            longitude,
            result_limit,
            prioritize_accessibility
        )

        for item in hospitals:

            item["source"] = (
                "offline_sample"
            )

    # -----------------------------------------------------------------------
    # Cache
    # -----------------------------------------------------------------------

    if use_cache:

        _store_cache(
            key,
            hospitals
        )

    return copy.deepcopy(
        hospitals
    )


# ---------------------------------------------------------------------------
# SEARCH WITH METADATA
# ---------------------------------------------------------------------------

def find_nearby_hospitals_detailed(
    lat,
    lon,
    radius_m=DEFAULT_RADIUS_M,
    limit=DEFAULT_LIMIT,
    prioritize_accessibility=False,
    use_cache=True
) -> Dict[str, Any]:
    """
    Detailed version of hospital search.

    Useful for the dashboard because it returns:

        {
            "hospitals": [...],
            "source": "...",
            "result_count": ...,
            "radius_m": ...,
            "coordinates": ...
        }
    """

    latitude = _normalize_coordinate(
        lat
    )

    longitude = _normalize_coordinate(
        lon
    )

    radius = _clamp_radius(
        radius_m
    )

    result_limit = _clamp_limit(
        limit
    )

    hospitals = find_nearby_hospitals(
        latitude,
        longitude,
        radius,
        result_limit,
        prioritize_accessibility,
        use_cache
    )

    if not hospitals:

        source = "none"

    else:

        source = hospitals[0].get(
            "source",
            "unknown"
        )

    return {
        "hospitals": hospitals,

        "source": source,

        "result_count": len(
            hospitals
        ),

        "radius_m": radius,

        "latitude": latitude,

        "longitude": longitude,

        "success": bool(
            hospitals
        )
    }


# ---------------------------------------------------------------------------
# NEAREST HOSPITAL
# ---------------------------------------------------------------------------

def get_nearest_hospital(
    lat,
    lon,
    radius_m=DEFAULT_RADIUS_M,
    wheelchair_friendly=False
) -> Optional[Dict[str, Any]]:
    """
    Return the nearest suitable hospital.
    """

    hospitals = find_nearby_hospitals(
        lat,
        lon,
        radius_m=radius_m,
        limit=20,
        prioritize_accessibility=wheelchair_friendly
    )

    if not hospitals:

        return None

    if wheelchair_friendly:

        accessible = [
            h
            for h in hospitals
            if h.get(
                "wheelchair"
            ) == "yes"
        ]

        if accessible:

            return min(
                accessible,
                key=lambda h:
                    h.get(
                        "distance_km",
                        float("inf")
                    )
            )

    return min(
        hospitals,
        key=lambda h:
            h.get(
                "distance_km",
                float("inf")
            )
    )


# ---------------------------------------------------------------------------
# FILTER BY WHEELCHAIR ACCESSIBILITY
# ---------------------------------------------------------------------------

def filter_wheelchair_accessible(
    hospitals: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Return hospitals explicitly marked wheelchair=yes.
    """

    if not hospitals:
        return []

    return [
        hospital
        for hospital in hospitals
        if _normalize_wheelchair(
            hospital.get(
                "wheelchair",
                "unknown"
            )
        ) == "yes"
    ]


# ---------------------------------------------------------------------------
# FILTER BY EMERGENCY
# ---------------------------------------------------------------------------

def filter_emergency_hospitals(
    hospitals: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Return hospitals explicitly marked as providing emergency services.
    """

    if not hospitals:
        return []

    return [
        hospital
        for hospital in hospitals
        if _normalize_emergency(
            hospital.get(
                "emergency",
                "unknown"
            )
        ) == "yes"
    ]


# ---------------------------------------------------------------------------
# FORMAT FOR GUI
# ---------------------------------------------------------------------------

def format_hospital_for_gui(
    hospital: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convert hospital data into simple GUI-ready fields.
    """

    wheelchair = _normalize_wheelchair(
        hospital.get(
            "wheelchair"
        )
    )

    if wheelchair == "yes":

        wheelchair_text = (
            "Wheelchair accessible"
        )

    elif wheelchair == "limited":

        wheelchair_text = (
            "Limited wheelchair accessibility"
        )

    elif wheelchair == "no":

        wheelchair_text = (
            "Not marked wheelchair accessible"
        )

    else:

        wheelchair_text = (
            "Wheelchair accessibility unknown"
        )

    emergency = _normalize_emergency(
        hospital.get(
            "emergency"
        )
    )

    if emergency == "yes":

        emergency_text = (
            "Emergency services available"
        )

    elif emergency == "no":

        emergency_text = (
            "Emergency service information "
            "indicates unavailable"
        )

    else:

        emergency_text = (
            "Emergency service information unknown"
        )

    return {
        "name":
            _clean_text(
                hospital.get(
                    "name"
                ),
                "Unnamed hospital"
            ),

        "distance":
            f"{_safe_float(hospital.get('distance_km')):.2f} km",

        "wheelchair":
            wheelchair_text,

        "emergency":
            emergency_text,

        "phone":
            _clean_text(
                hospital.get(
                    "phone"
                ),
                "N/A"
            ),

        "website":
            _clean_text(
                hospital.get(
                    "website"
                ),
                "N/A"
            ),

        "opening_hours":
            _clean_text(
                hospital.get(
                    "opening_hours"
                ),
                "N/A"
            ),

        "address":
            _clean_text(
                hospital.get(
                    "address"
                ),
                "N/A"
            ),

        "lat":
            hospital.get(
                "lat"
            ),

        "lon":
            hospital.get(
                "lon"
            ),

        "raw":
            hospital
    }


# ---------------------------------------------------------------------------
# TEXT SUMMARY
# ---------------------------------------------------------------------------

def hospital_summary(
    hospital: Dict[str, Any]
) -> str:
    """
    Generate a concise hospital summary.
    """

    if not hospital:

        return (
            "No hospital information available."
        )

    name = _clean_text(
        hospital.get(
            "name"
        ),
        "Unnamed hospital"
    )

    distance = _safe_float(
        hospital.get(
            "distance_km"
        )
    )

    wheelchair = _normalize_wheelchair(
        hospital.get(
            "wheelchair"
        )
    )

    if wheelchair == "yes":

        accessibility = (
            "wheelchair accessibility is marked available"
        )

    elif wheelchair == "limited":

        accessibility = (
            "limited wheelchair accessibility is indicated"
        )

    elif wheelchair == "no":

        accessibility = (
            "wheelchair accessibility is marked unavailable"
        )

    else:

        accessibility = (
            "wheelchair accessibility information is unknown"
        )

    return (
        f"{name} is approximately "
        f"{distance:.2f} km away; "
        f"{accessibility}."
    )


# ---------------------------------------------------------------------------
# JSON EXPORT
# ---------------------------------------------------------------------------

def save_hospitals_json(
    hospitals: List[Dict[str, Any]],
    file_path: str
) -> bool:
    """
    Save hospital results to JSON.

    Returns True on success.
    """

    try:

        directory = os.path.dirname(
            os.path.abspath(
                file_path
            )
        )

        os.makedirs(
            directory,
            exist_ok=True
        )

        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                hospitals,
                file,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as exc:

        print(
            f"[hospitals.py] "
            f"Could not save JSON: {exc}"
        )

        return False


# ---------------------------------------------------------------------------
# TEST CONNECTION
# ---------------------------------------------------------------------------

def test_overpass_connection() -> Dict[str, Any]:
    """
    Test available Overpass servers.

    Useful for debugging network problems.
    """

    results = []

    test_query = """
[out:json][timeout:5];
node["amenity"="hospital"](around:100,19.0760,72.8777);
out 1;
"""

    for server in OVERPASS_SERVERS:

        start = time.time()

        data = _request_overpass(
            server,
            test_query
        )

        elapsed = round(
            time.time() - start,
            2
        )

        results.append(
            {
                "server": server,

                "working": data is not None,

                "response_time_seconds":
                    elapsed
            }
        )

    return {
        "servers": results,

        "working_servers": [
            item["server"]
            for item in results
            if item["working"]
        ]
    }


# ---------------------------------------------------------------------------
# CONSOLE DISPLAY
# ---------------------------------------------------------------------------

def print_hospital_results(
    hospitals: List[Dict[str, Any]]
):
    """
    Pretty-print hospital results for testing.
    """

    if not hospitals:

        print(
            "No hospitals found."
        )

        return

    print()
    print(
        "=" * 75
    )

    print(
        "WHEELGUIDE - NEARBY HOSPITALS"
    )

    print(
        "=" * 75
    )

    for index, hospital in enumerate(
        hospitals,
        start=1
    ):

        print(
            f"\n{index}. "
            f"{hospital.get('name', 'Unnamed hospital')}"
        )

        print(
            f"   Distance     : "
            f"{hospital.get('distance_km', 'N/A')} km"
        )

        print(
            f"   Wheelchair   : "
            f"{hospital.get('wheelchair', 'unknown')}"
        )

        print(
            f"   Emergency    : "
            f"{hospital.get('emergency', 'unknown')}"
        )

        print(
            f"   Phone        : "
            f"{hospital.get('phone', 'N/A')}"
        )

        print(
            f"   Address      : "
            f"{hospital.get('address', 'N/A')}"
        )

        print(
            f"   Opening      : "
            f"{hospital.get('opening_hours', 'N/A')}"
        )

        print(
            f"   Source       : "
            f"{hospital.get('source', 'unknown')}"
        )

    print()
    print(
        "=" * 75
    )


# ---------------------------------------------------------------------------
# DIRECT TEST
# ---------------------------------------------------------------------------

def run_demo():
    """
    Run hospital search from a sample Mumbai coordinate.
    """

    latitude = 19.0760
    longitude = 72.8777

    print(
        "\nSearching for hospitals near "
        f"{latitude}, {longitude}..."
    )

    hospitals = find_nearby_hospitals(
        latitude,
        longitude,
        radius_m=5000,
        limit=10,
        prioritize_accessibility=True
    )

    print_hospital_results(
        hospitals
    )

    print(
        "\nNearest hospital:"
    )

    nearest = get_nearest_hospital(
        latitude,
        longitude,
        radius_m=5000,
        wheelchair_friendly=True
    )

    if nearest:

        print(
            hospital_summary(
                nearest
            )
        )

    else:

        print(
            "No suitable hospital found."
        )


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_demo()
