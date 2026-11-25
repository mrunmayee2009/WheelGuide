"""
Maps/route.py
-------------

WheelGuide - Wheelchair Accessibility-Aware Routing Engine

Features
--------
1. Real OpenStreetMap walking routes using OSMnx when available.
2. Offline/demo graph fallback.
3. Accessibility-aware route weighting.
4. Avoid stairs.
5. Avoid construction zones.
6. Avoid potentially steep segments when elevation data is available.
7. Compare shortest and wheelchair-friendly routes.
8. Route statistics and warnings.
9. Coordinate-based routing.
10. Place-name geocoding.
11. Compatible with the existing WheelGuide GUI API.

Main functions
--------------
build_demo_graph()
build_graph_from_osm()
find_accessible_route()
compare_shortest_vs_accessible()
find_route_by_coordinates()
find_route_by_place()
calculate_route_statistics()
geocode_place()

The module does NOT require OSMnx for demo/offline operation.
"""

from __future__ import annotations

import math
import os
import sys
import re
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx


# ---------------------------------------------------------------------------
# PROJECT ROOT
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


# ---------------------------------------------------------------------------
# OPTIONAL PROJECT MODULES
# ---------------------------------------------------------------------------

try:
    from AI.construction import get_reported_construction_zones
except Exception:
    get_reported_construction_zones = None


# ---------------------------------------------------------------------------
# OPTIONAL OSMNX
# ---------------------------------------------------------------------------

try:
    import osmnx as ox

    OSMNX_AVAILABLE = True

except ImportError:
    ox = None
    OSMNX_AVAILABLE = False


# ---------------------------------------------------------------------------
# OPTIONAL GEOCODING
# ---------------------------------------------------------------------------

try:
    from geopy.geocoders import Nominatim

    GEOPY_AVAILABLE = True

except ImportError:
    Nominatim = None
    GEOPY_AVAILABLE = False


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

DEFAULT_STAIRS_PENALTY = 20.0
DEFAULT_CONSTRUCTION_PENALTY = 25.0
DEFAULT_STEEP_SLOPE_PENALTY = 15.0
DEFAULT_UNPAVED_PENALTY = 3.0

DEFAULT_WALKING_SPEED_KMH = 4.5

GEOCODER_USER_AGENT = "WheelGuideAccessibilityApp"

# Maximum time allowed for geocoding requests.
GEOCODER_TIMEOUT = 10

# Cache geocoding results during application runtime.
_GEOCODE_CACHE: Dict[str, Tuple[float, float]] = {}


# ---------------------------------------------------------------------------
# BASIC UTILITIES
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
    except (TypeError, ValueError):
        return default


def _safe_bool(
    value: Any,
    default: bool = False
) -> bool:
    """
    Safely convert common values into bool.
    """

    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    text = str(value).strip().lower()

    if text in {
        "true",
        "yes",
        "1",
        "y",
        "accessible",
        "available",
    }:
        return True

    if text in {
        "false",
        "no",
        "0",
        "n",
        "inaccessible",
        "unavailable",
    }:
        return False

    return default


def _normalize_coordinate(
    coordinate: Any
) -> Optional[Tuple[float, float]]:
    """
    Normalize a coordinate into:

        (latitude, longitude)

    Accepted formats:

        (lat, lon)
        [lat, lon]
        {"lat": ..., "lon": ...}
        {"latitude": ..., "longitude": ...}
    """

    if coordinate is None:
        return None

    if isinstance(coordinate, dict):

        lat = coordinate.get(
            "lat",
            coordinate.get("latitude")
        )

        lon = coordinate.get(
            "lon",
            coordinate.get(
                "lng",
                coordinate.get("longitude")
            )
        )

        if lat is None or lon is None:
            return None

        return (
            _safe_float(lat),
            _safe_float(lon)
        )

    if isinstance(coordinate, (list, tuple)):

        if len(coordinate) < 2:
            return None

        return (
            _safe_float(coordinate[0]),
            _safe_float(coordinate[1])
        )

    return None


# ---------------------------------------------------------------------------
# HAVERSINE DISTANCE
# ---------------------------------------------------------------------------

def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculate straight-line distance between two coordinates.
    """

    earth_radius_km = 6371.0088

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(
        lat2 - lat1
    )

    delta_lon = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(delta_lat / 2) ** 2
        +
        math.cos(lat1_rad)
        *
        math.cos(lat2_rad)
        *
        math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius_km * c


# ---------------------------------------------------------------------------
# DEMO GRAPH
# ---------------------------------------------------------------------------

def build_demo_graph() -> nx.Graph:
    """
    Build an offline WheelGuide demonstration graph.

    This graph is useful for:
        - Testing
        - College demonstrations
        - Offline development
        - Unit testing

    It deliberately contains:
        - A short route with stairs
        - A slightly longer accessible route
        - A construction segment
    """

    G = nx.Graph()

    nodes = {
        "A_Start": (19.0760, 72.8777),
        "B_MainRoad": (19.0770, 72.8790),
        "C_RampPath": (19.0785, 72.8800),
        "D_StairsPath": (19.0780, 72.8795),
        "E_Destination": (19.0800, 72.8820),
        "F_Accessible": (19.0790, 72.8810),
    }

    for name, coordinate in nodes.items():

        G.add_node(
            name,
            pos=coordinate,
            latitude=coordinate[0],
            longitude=coordinate[1]
        )

    G.add_edge(
        "A_Start",
        "B_MainRoad",
        distance_km=0.30,
        has_stairs=False,
        under_construction=False,
        steep_slope=False,
        wheelchair_accessible=True
    )

    G.add_edge(
        "B_MainRoad",
        "D_StairsPath",
        distance_km=0.40,
        has_stairs=True,
        under_construction=False,
        steep_slope=False,
        wheelchair_accessible=False
    )

    G.add_edge(
        "D_StairsPath",
        "E_Destination",
        distance_km=0.30,
        has_stairs=False,
        under_construction=False,
        steep_slope=False,
        wheelchair_accessible=True
    )

    G.add_edge(
        "B_MainRoad",
        "C_RampPath",
        distance_km=0.60,
        has_stairs=False,
        under_construction=False,
        steep_slope=False,
        wheelchair_accessible=True
    )

    G.add_edge(
        "C_RampPath",
        "F_Accessible",
        distance_km=0.25,
        has_stairs=False,
        under_construction=False,
        steep_slope=False,
        wheelchair_accessible=True
    )

    G.add_edge(
        "F_Accessible",
        "E_Destination",
        distance_km=0.25,
        has_stairs=False,
        under_construction=False,
        steep_slope=False,
        wheelchair_accessible=True
    )

    return G


# ---------------------------------------------------------------------------
# OSM GRAPH
# ---------------------------------------------------------------------------

def build_graph_from_osm(
    place_name: str,
    network_type: str = "walk"
):
    """
    Download a real walking network from OpenStreetMap.

    Parameters
    ----------
    place_name:
        Example:
            "Bandra, Mumbai, India"

    network_type:
        Usually "walk".

    Returns
    -------
    networkx graph

    Raises
    ------
    RuntimeError
        When OSMnx is unavailable.

    Exception
        When the OSM request fails.
    """

    if not OSMNX_AVAILABLE:

        raise RuntimeError(
            "OSMnx is not installed. "
            "Install osmnx to use real OpenStreetMap routing."
        )

    place_name = str(place_name).strip()

    if not place_name:

        raise ValueError(
            "place_name cannot be empty."
        )

    try:

        G = ox.graph_from_place(
            place_name,
            network_type=network_type,
            simplify=True
        )

    except Exception as exc:

        raise RuntimeError(
            f"Unable to download OpenStreetMap data: {exc}"
        ) from exc

    G = _prepare_osm_graph(G)

    return G


def _prepare_osm_graph(G):
    """
    Normalize an OSMnx graph into the edge format expected by
    WheelGuide.
    """

    # OSMnx graphs are often MultiDiGraphs.
    # Keep them as-is because routing can work with MultiGraphs.
    for node, data in G.nodes(data=True):

        if "y" in data:
            data["latitude"] = _safe_float(
                data["y"]
            )

        if "x" in data:
            data["longitude"] = _safe_float(
                data["x"]
            )

    for u, v, key, data in G.edges(
        keys=True,
        data=True
    ):

        # ---------------------------------------------------
        # Distance
        # ---------------------------------------------------

        length_m = data.get(
            "length",
            data.get("distance", 0)
        )

        distance_km = _safe_float(
            length_m
        ) / 1000.0

        if distance_km <= 0:

            distance_km = _estimate_edge_distance(
                G,
                u,
                v
            )

        data["distance_km"] = distance_km

        # ---------------------------------------------------
        # Stairs
        # ---------------------------------------------------

        highway = data.get(
            "highway",
            ""
        )

        if isinstance(highway, list):
            highway_values = [
                str(x).lower()
                for x in highway
            ]
        else:
            highway_values = [
                str(highway).lower()
            ]

        data["has_stairs"] = (
            "steps" in highway_values
            or
            "stairway" in highway_values
        )

        # ---------------------------------------------------
        # Wheelchair tag
        # ---------------------------------------------------

        wheelchair = str(
            data.get(
                "wheelchair",
                ""
            )
        ).lower()

        if wheelchair == "yes":
            data["wheelchair_accessible"] = True

        elif wheelchair == "no":
            data["wheelchair_accessible"] = False

        else:
            data["wheelchair_accessible"] = None

        # ---------------------------------------------------
        # Surface
        # ---------------------------------------------------

        surface = str(
            data.get(
                "surface",
                ""
            )
        ).lower()

        data["unpaved"] = surface in {
            "unpaved",
            "gravel",
            "ground",
            "dirt",
            "sand",
            "mud"
        }

        # ---------------------------------------------------
        # Incline
        # ---------------------------------------------------

        incline = data.get(
            "incline"
        )

        data["incline_percent"] = _parse_incline(
            incline
        )

        data["steep_slope"] = (
            data["incline_percent"] is not None
            and
            abs(data["incline_percent"]) >= 8
        )

        # ---------------------------------------------------
        # Construction
        # ---------------------------------------------------

        highway_values_string = " ".join(
            highway_values
        )

        data["under_construction"] = (
            "construction" in highway_values_string
            or
            str(
                data.get(
                    "construction",
                    ""
                )
            ).lower()
            in {"yes", "true"}
        )

    return G


# ---------------------------------------------------------------------------
# OSM EDGE DISTANCE ESTIMATION
# ---------------------------------------------------------------------------

def _estimate_edge_distance(
    G,
    u,
    v
) -> float:
    """
    Estimate edge distance from node coordinates.
    """

    u_data = G.nodes[u]
    v_data = G.nodes[v]

    lat1 = u_data.get(
        "y",
        u_data.get("latitude")
    )

    lon1 = u_data.get(
        "x",
        u_data.get("longitude")
    )

    lat2 = v_data.get(
        "y",
        v_data.get("latitude")
    )

    lon2 = v_data.get(
        "x",
        v_data.get("longitude")
    )

    if None in {
        lat1,
        lon1,
        lat2,
        lon2
    }:
        return 0.001

    return haversine_distance_km(
        float(lat1),
        float(lon1),
        float(lat2),
        float(lon2)
    )


# ---------------------------------------------------------------------------
# INCLINE PARSER
# ---------------------------------------------------------------------------

def _parse_incline(
    incline: Any
) -> Optional[float]:
    """
    Convert OSM incline values into percentage.

    Examples:

        "10%" -> 10
        "-8%" -> -8
        "5" -> 5
        12 -> 12

    OSM may also contain values such as:
        "up"
        "down"

    Those are treated as unknown.
    """

    if incline is None:
        return None

    if isinstance(
        incline,
        (int, float)
    ):
        return float(incline)

    text = str(
        incline
    ).strip().lower()

    if text in {
        "",
        "unknown",
        "up",
        "down"
    }:
        return None

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text
    )

    if not match:
        return None

    try:
        return float(
            match.group(0)
        )

    except ValueError:
        return None


# ---------------------------------------------------------------------------
# CONSTRUCTION REPORTS
# ---------------------------------------------------------------------------

def _apply_construction_reports(
    G
):
    """
    Hook for WheelGuide's construction reporting system.

    The construction module may have different return formats,
    so this function is deliberately defensive.
    """

    if get_reported_construction_zones is None:
        return G

    try:

        reports = (
            get_reported_construction_zones()
        )

    except Exception as exc:

        print(
            "[WheelGuide Route] "
            f"Construction report lookup failed: {exc}"
        )

        return G

    if not reports:
        return G

    # At this stage, reports can be used by your existing
    # construction-reporting module to mark nearby graph edges.
    #
    # We intentionally do not guess coordinate formats here.
    # Existing report data remains untouched.

    return G


# ---------------------------------------------------------------------------
# EDGE ACCESSIBILITY
# ---------------------------------------------------------------------------

def _edge_cost(
    u,
    v,
    data,
    avoid_stairs: bool = True,
    stairs_penalty: float = DEFAULT_STAIRS_PENALTY,
    construction_penalty: float = DEFAULT_CONSTRUCTION_PENALTY,
    steep_slope_penalty: float = DEFAULT_STEEP_SLOPE_PENALTY,
    unpaved_penalty: float = DEFAULT_UNPAVED_PENALTY
) -> float:
    """
    Calculate accessibility-aware routing cost.

    Lower cost = preferred route.

    Important:
        This does NOT change the actual distance.
        It changes which route is selected.
    """

    distance = _safe_float(
        data.get(
            "distance_km",
            data.get("length", 1.0)
        )
    )

    if distance <= 0:
        distance = 0.001

    cost = distance

    # -------------------------------------------------------
    # Stairs
    # -------------------------------------------------------

    if (
        avoid_stairs
        and
        _safe_bool(
            data.get("has_stairs"),
            False
        )
    ):
        cost *= (
            1.0 + stairs_penalty
        )

    # -------------------------------------------------------
    # Construction
    # -------------------------------------------------------

    if _safe_bool(
        data.get(
            "under_construction"
        ),
        False
    ):
        cost *= (
            1.0 + construction_penalty
        )

    # -------------------------------------------------------
    # Steep slope
    # -------------------------------------------------------

    if (
        avoid_stairs
        and
        _safe_bool(
            data.get("steep_slope"),
            False
        )
    ):
        cost *= (
            1.0 + steep_slope_penalty
        )

    # -------------------------------------------------------
    # Unpaved surface
    # -------------------------------------------------------

    if (
        avoid_stairs
        and
        _safe_bool(
            data.get("unpaved"),
            False
        )
    ):
        cost *= (
            1.0 + unpaved_penalty
        )

    # -------------------------------------------------------
    # Explicit wheelchair=no
    # -------------------------------------------------------

    wheelchair_accessible = data.get(
        "wheelchair_accessible"
    )

    if (
        avoid_stairs
        and
        wheelchair_accessible is False
    ):
        cost *= 50.0

    return cost


# ---------------------------------------------------------------------------
# MULTIGRAPH EDGE HANDLING
# ---------------------------------------------------------------------------

def _get_edge_data(
    G,
    u,
    v
) -> Dict[str, Any]:
    """
    Get edge data safely for Graph, DiGraph, MultiGraph
    and MultiDiGraph.
    """

    data = G.get_edge_data(
        u,
        v
    )

    if data is None:
        return {}

    # MultiGraph:
    # {key: {attributes}}
    if G.is_multigraph():

        if not isinstance(
            data,
            dict
        ):
            return {}

        candidates = list(
            data.values()
        )

        if not candidates:
            return {}

        # Choose shortest physical edge.
        best = min(
            candidates,
            key=lambda item: _safe_float(
                item.get(
                    "distance_km",
                    item.get(
                        "length",
                        999999
                    )
                )
            )
        )

        return best

    return data


# ---------------------------------------------------------------------------
# ROUTE EDGE ITERATION
# ---------------------------------------------------------------------------

def _iter_route_edges(
    G,
    path: List[Any]
):
    """
    Yield (u, v, data) for every route segment.
    """

    for i in range(
        len(path) - 1
    ):

        u = path[i]
        v = path[i + 1]

        data = _get_edge_data(
            G,
            u,
            v
        )

        yield u, v, data


# ---------------------------------------------------------------------------
# FIND ACCESSIBLE ROUTE
# ---------------------------------------------------------------------------

def find_accessible_route(
    G,
    start_node,
    end_node,
    avoid_stairs: bool = True,
    stairs_penalty: float = DEFAULT_STAIRS_PENALTY,
    construction_penalty: float = DEFAULT_CONSTRUCTION_PENALTY,
    steep_slope_penalty: float = DEFAULT_STEEP_SLOPE_PENALTY
) -> Dict[str, Any]:
    """
    Find the best wheelchair-friendly route.

    Returns
    -------
    dict

    Example result:

    {
        "path": [...],
        "total_distance_km": 2.3,
        "estimated_time_minutes": 31,
        "has_stairs_on_route": False,
        "has_construction_on_route": False,
        "has_steep_slope": False,
        "warnings": [],
        "accessibility": "Good",
        "route_type": "wheelchair_accessible"
    }
    """

    if G is None:

        return {
            "error": "Route graph is not available."
        }

    if start_node not in G:

        return {
            "error": (
                f"Start location '{start_node}' "
                "does not exist in the route graph."
            )
        }

    if end_node not in G:

        return {
            "error": (
                f"Destination '{end_node}' "
                "does not exist in the route graph."
            )
        }

    def weight_fn(
        u,
        v,
        data
    ):

        return _edge_cost(
            u,
            v,
            data,
            avoid_stairs=avoid_stairs,
            stairs_penalty=stairs_penalty,
            construction_penalty=construction_penalty,
            steep_slope_penalty=steep_slope_penalty
        )

    try:

        path = nx.shortest_path(
            G,
            source=start_node,
            target=end_node,
            weight=weight_fn
        )

    except nx.NetworkXNoPath:

        return {
            "error": (
                f"No path found between "
                f"{start_node} and {end_node}."
            )
        }

    except nx.NodeNotFound as exc:

        return {
            "error": str(exc)
        }

    # -------------------------------------------------------
    # Analyze route
    # -------------------------------------------------------

    total_distance = 0.0
    penalized_cost = 0.0

    has_stairs = False
    has_construction = False
    has_steep_slope = False
    has_unpaved = False
    explicit_inaccessible = False

    warnings = []
    accessibility_features = []

    for u, v, data in _iter_route_edges(
        G,
        path
    ):

        distance = _safe_float(
            data.get(
                "distance_km",
                data.get(
                    "length",
                    0
                )
            )
        )

        if (
            distance <= 0
            and
            G.nodes.get(u)
            and
            G.nodes.get(v)
        ):

            u_data = G.nodes[u]
            v_data = G.nodes[v]

            lat1 = u_data.get(
                "latitude",
                u_data.get("y")
            )

            lon1 = u_data.get(
                "longitude",
                u_data.get("x")
            )

            lat2 = v_data.get(
                "latitude",
                v_data.get("y")
            )

            lon2 = v_data.get(
                "longitude",
                v_data.get("x")
            )

            if None not in {
                lat1,
                lon1,
                lat2,
                lon2
            }:

                distance = haversine_distance_km(
                    lat1,
                    lon1,
                    lat2,
                    lon2
                )

        total_distance += distance

        penalized_cost += _edge_cost(
            u,
            v,
            data,
            avoid_stairs=avoid_stairs,
            stairs_penalty=stairs_penalty,
            construction_penalty=construction_penalty,
            steep_slope_penalty=steep_slope_penalty
        )

        # ---------------------------------------------------
        # Stairs
        # ---------------------------------------------------

        if _safe_bool(
            data.get("has_stairs"),
            False
        ):

            has_stairs = True

            warnings.append(
                f"Segment {u} → {v} contains stairs."
            )

        # ---------------------------------------------------
        # Construction
        # ---------------------------------------------------

        if _safe_bool(
            data.get("under_construction"),
            False
        ):

            has_construction = True

            warnings.append(
                f"Segment {u} → {v} is under construction."
            )

        # ---------------------------------------------------
        # Steep slope
        # ---------------------------------------------------

        if _safe_bool(
            data.get("steep_slope"),
            False
        ):

            has_steep_slope = True

            incline = data.get(
                "incline_percent"
            )

            if incline is not None:

                warnings.append(
                    f"Segment {u} → {v} has "
                    f"approximately {incline}% incline."
                )

            else:

                warnings.append(
                    f"Segment {u} → {v} may be steep."
                )

        # ---------------------------------------------------
        # Unpaved
        # -------------------------------------------------------

        if _safe_bool(
            data.get("unpaved"),
            False
        ):

            has_unpaved = True

            warnings.append(
                f"Segment {u} → {v} has an "
                "unpaved surface."
            )

        # ---------------------------------------------------
        # Explicit wheelchair=no
        # -------------------------------------------------------

        if data.get(
            "wheelchair_accessible"
        ) is False:

            explicit_inaccessible = True

            warnings.append(
                f"Segment {u} → {v} is marked "
                "not wheelchair accessible."
            )

        # ---------------------------------------------------
        # Accessibility features
        # ---------------------------------------------------

        if data.get(
            "wheelchair_accessible"
        ) is True:

            accessibility_features.append(
                f"Wheelchair-accessible segment: {u} → {v}"
            )

    # Remove duplicate warnings
    warnings = list(
        dict.fromkeys(warnings)
    )

    # -------------------------------------------------------
    # Estimated travel time
    # -------------------------------------------------------

    estimated_time_minutes = (
        total_distance
        /
        DEFAULT_WALKING_SPEED_KMH
        *
        60
    )

    # -------------------------------------------------------
    # Accessibility classification
    # -------------------------------------------------------

    if explicit_inaccessible:

        accessibility = "Limited"

    elif (
        not has_stairs
        and
        not has_construction
        and
        not has_steep_slope
    ):

        accessibility = "Good"

    elif not has_stairs:

        accessibility = "Moderate"

    else:

        accessibility = "Limited"

    # -------------------------------------------------------
    # Route type
    # -------------------------------------------------------

    if avoid_stairs:

        route_type = (
            "wheelchair_accessible"
        )

    else:

        route_type = "shortest"

    return {
        "path": path,

        "total_distance_km": round(
            total_distance,
            2
        ),

        "estimated_time_minutes": round(
            estimated_time_minutes
        ),

        "penalized_cost": round(
            penalized_cost,
            3
        ),

        "has_stairs_on_route": has_stairs,

        "has_construction_on_route":
            has_construction,

        "has_steep_slope":
            has_steep_slope,

        "has_unpaved_surface":
            has_unpaved,

        "explicitly_inaccessible":
            explicit_inaccessible,

        "accessibility":
            accessibility,

        "accessibility_features":
            accessibility_features,

        "warnings":
            warnings,

        "route_type":
            route_type,

        "start":
            start_node,

        "destination":
            end_node,
    }


# ---------------------------------------------------------------------------
# SHORTEST ROUTE
# ---------------------------------------------------------------------------

def find_shortest_route(
    G,
    start_node,
    end_node
) -> Dict[str, Any]:
    """
    Find the physically shortest route.

    Accessibility penalties are ignored.
    """

    return find_accessible_route(
        G,
        start_node,
        end_node,
        avoid_stairs=False
    )


# ---------------------------------------------------------------------------
# COMPARE ROUTES
# ---------------------------------------------------------------------------

def compare_shortest_vs_accessible(
    G,
    start_node,
    end_node
) -> Dict[str, Any]:
    """
    Compare:
        1. Pure shortest route.
        2. Wheelchair-friendly route.

    This is useful for the WheelGuide GUI.
    """

    shortest = find_shortest_route(
        G,
        start_node,
        end_node
    )

    accessible = find_accessible_route(
        G,
        start_node,
        end_node,
        avoid_stairs=True
    )

    if "error" in shortest:

        return {
            "shortest_route": shortest,
            "accessible_route": accessible,
            "comparison": {
                "available": False,
                "message": shortest["error"]
            }
        }

    if "error" in accessible:

        return {
            "shortest_route": shortest,
            "accessible_route": accessible,
            "comparison": {
                "available": False,
                "message": accessible["error"]
            }
        }

    shortest_distance = shortest[
        "total_distance_km"
    ]

    accessible_distance = accessible[
        "total_distance_km"
    ]

    additional_distance = (
        accessible_distance
        -
        shortest_distance
    )

    if shortest_distance > 0:

        percentage_extra = (
            additional_distance
            /
            shortest_distance
            *
            100
        )

    else:

        percentage_extra = 0

    if additional_distance <= 0.01:

        recommendation = (
            "The wheelchair-friendly route is "
            "approximately the same distance as "
            "the shortest route."
        )

    else:

        recommendation = (
            "The wheelchair-friendly route is "
            f"{additional_distance:.2f} km longer, "
            "but is preferred because it avoids "
            "accessibility barriers."
        )

    return {
        "shortest_route": shortest,

        "accessible_route": accessible,

        "comparison": {
            "available": True,

            "shortest_distance_km":
                round(
                    shortest_distance,
                    2
                ),

            "accessible_distance_km":
                round(
                    accessible_distance,
                    2
                ),

            "additional_distance_km":
                round(
                    max(
                        0,
                        additional_distance
                    ),
                    2
                ),

            "additional_distance_percent":
                round(
                    max(
                        0,
                        percentage_extra
                    ),
                    1
                ),

            "recommendation":
                recommendation,
        }
    }


# ---------------------------------------------------------------------------
# GRAPH NODE FROM COORDINATES
# ---------------------------------------------------------------------------

def get_nearest_node(
    G,
    latitude: float,
    longitude: float
):
    """
    Find the graph node nearest to a coordinate.

    Uses OSMnx's nearest_nodes when available.
    Falls back to a pure Python search.
    """

    if G is None or len(G.nodes) == 0:
        return None

    latitude = _safe_float(
        latitude
    )

    longitude = _safe_float(
        longitude
    )

    # OSMnx optimized version
    if (
        OSMNX_AVAILABLE
        and
        hasattr(
            ox,
            "distance"
        )
    ):

        try:

            return ox.distance.nearest_nodes(
                G,
                X=longitude,
                Y=latitude
            )

        except Exception:
            pass

    # -------------------------------------------------------
    # Python fallback
    # -------------------------------------------------------

    nearest_node = None
    nearest_distance = float(
        "inf"
    )

    for node, data in G.nodes(
        data=True
    ):

        node_lat = data.get(
            "latitude",
            data.get("y")
        )

        node_lon = data.get(
            "longitude",
            data.get("x")
        )

        if (
            node_lat is None
            or
            node_lon is None
        ):
            continue

        distance = haversine_distance_km(
            latitude,
            longitude,
            float(node_lat),
            float(node_lon)
        )

        if distance < nearest_distance:

            nearest_distance = distance
            nearest_node = node

    return nearest_node


# ---------------------------------------------------------------------------
# COORDINATE ROUTING
# ---------------------------------------------------------------------------

def find_route_by_coordinates(
    G,
    start_coordinate,
    destination_coordinate,
    wheelchair_friendly: bool = True
) -> Dict[str, Any]:
    """
    Find a route using latitude/longitude.

    Example:

        start = (19.0760, 72.8777)
        destination = (19.0800, 72.8820)
    """

    start = _normalize_coordinate(
        start_coordinate
    )

    destination = _normalize_coordinate(
        destination_coordinate
    )

    if start is None:

        return {
            "error":
                "Invalid start coordinates."
        }

    if destination is None:

        return {
            "error":
                "Invalid destination coordinates."
        }

    start_node = get_nearest_node(
        G,
        start[0],
        start[1]
    )

    end_node = get_nearest_node(
        G,
        destination[0],
        destination[1]
    )

    if start_node is None:

        return {
            "error":
                "Could not find a route node near the start location."
        }

    if end_node is None:

        return {
            "error":
                "Could not find a route node near the destination."
        }

    return find_accessible_route(
        G,
        start_node,
        end_node,
        avoid_stairs=wheelchair_friendly
    )


# ---------------------------------------------------------------------------
# GEOCODING
# ---------------------------------------------------------------------------

def geocode_place(
    place_name: str
) -> Optional[Tuple[float, float]]:
    """
    Convert a place name/address into coordinates.

    Example:

        geocode_place("Gateway of India, Mumbai")

    Returns:

        (latitude, longitude)

    or None when geocoding fails.
    """

    place_name = str(
        place_name
    ).strip()

    if not place_name:
        return None

    cache_key = place_name.lower()

    if cache_key in _GEOCODE_CACHE:

        return _GEOCODE_CACHE[
            cache_key
        ]

    if not GEOPY_AVAILABLE:

        return None

    try:

        geocoder = Nominatim(
            user_agent=GEOCODER_USER_AGENT
        )

        location = geocoder.geocode(
            place_name,
            timeout=GEOCODER_TIMEOUT
        )

        if location is None:
            return None

        result = (
            float(location.latitude),
            float(location.longitude)
        )

        _GEOCODE_CACHE[
            cache_key
        ] = result

        return result

    except Exception as exc:

        print(
            "[WheelGuide Route] "
            f"Geocoding failed: {exc}"
        )

        return None


# ---------------------------------------------------------------------------
# PLACE-TO-PLACE ROUTING
# ---------------------------------------------------------------------------

def find_route_by_place(
    start_place: str,
    destination_place: str,
    wheelchair_friendly: bool = True,
    network_type: str = "walk"
) -> Dict[str, Any]:
    """
    Full real-world route workflow:

        Place name
            ↓
        Geocoding
            ↓
        OpenStreetMap graph
            ↓
        Nearest graph nodes
            ↓
        Accessibility-aware route

    This requires:
        - OSMnx
        - geopy
        - internet connection
    """

    if not OSMNX_AVAILABLE:

        return {
            "error":
                "Real map routing requires OSMnx. "
                "Use build_demo_graph() for offline testing."
        }

    start_place = str(
        start_place
    ).strip()

    destination_place = str(
        destination_place
    ).strip()

    if not start_place:

        return {
            "error":
                "Start location cannot be empty."
        }

    if not destination_place:

        return {
            "error":
                "Destination cannot be empty."
        }

    # -------------------------------------------------------
    # Geocode
    # -------------------------------------------------------

    start_coordinate = geocode_place(
        start_place
    )

    if start_coordinate is None:

        return {
            "error":
                f"Could not find start location: {start_place}"
        }

    destination_coordinate = geocode_place(
        destination_place
    )

    if destination_coordinate is None:

        return {
            "error":
                "Could not find destination: "
                f"{destination_place}"
        }

    # -------------------------------------------------------
    # Determine a suitable area
    # -------------------------------------------------------

    try:

        mid_lat = (
            start_coordinate[0]
            +
            destination_coordinate[0]
        ) / 2

        mid_lon = (
            start_coordinate[1]
            +
            destination_coordinate[1]
        ) / 2

        # Distance between start and destination
        straight_distance = haversine_distance_km(
            start_coordinate[0],
            start_coordinate[1],
            destination_coordinate[0],
            destination_coordinate[1]
        )

        # Add reasonable buffer around both points.
        radius_km = max(
            1.5,
            min(
                8.0,
                straight_distance * 2.5
            )
        )

        # ---------------------------------------------------
        # OSMnx versions differ in API.
        # Try graph_from_point first.
        # ---------------------------------------------------

        center = (
            mid_lat,
            mid_lon
        )

        try:

            G = ox.graph_from_point(
                center,
                dist=radius_km * 1000,
                network_type=network_type,
                simplify=True
            )

        except Exception:

            # Fallback to place-based graph
            G = ox.graph_from_place(
                start_place,
                network_type=network_type,
                simplify=True
            )

        G = _prepare_osm_graph(
            G
        )

        G = _apply_construction_reports(
            G
        )

        # ---------------------------------------------------
        # Find nearest nodes
        # ---------------------------------------------------

        start_node = get_nearest_node(
            G,
            start_coordinate[0],
            start_coordinate[1]
        )

        end_node = get_nearest_node(
            G,
            destination_coordinate[0],
            destination_coordinate[1]
        )

        if start_node is None:

            return {
                "error":
                    "Could not locate start point on map."
            }

        if end_node is None:

            return {
                "error":
                    "Could not locate destination on map."
            }

        # ---------------------------------------------------
        # Route
        # ---------------------------------------------------

        result = find_accessible_route(
            G,
            start_node,
            end_node,
            avoid_stairs=wheelchair_friendly
        )

        result["start_place"] = start_place
        result["destination_place"] = destination_place
        result["start_coordinate"] = start_coordinate
        result["destination_coordinate"] = destination_coordinate

        return result

    except Exception as exc:

        return {
            "error":
                f"Real-world routing failed: {exc}"
        }


# ---------------------------------------------------------------------------
# ROUTE STATISTICS
# ---------------------------------------------------------------------------

def calculate_route_statistics(
    route_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract clean statistics for the GUI.
    """

    if not route_result:
        return {
            "error": "Empty route result."
        }

    if "error" in route_result:
        return {
            "error":
                route_result["error"]
        }

    distance = _safe_float(
        route_result.get(
            "total_distance_km"
        )
    )

    time_minutes = _safe_float(
        route_result.get(
            "estimated_time_minutes"
        )
    )

    warnings = route_result.get(
        "warnings",
        []
    )

    return {
        "distance_km":
            round(distance, 2),

        "time_minutes":
            round(time_minutes),

        "time_text":
            _format_time(
                time_minutes
            ),

        "warnings_count":
            len(warnings),

        "has_stairs":
            bool(
                route_result.get(
                    "has_stairs_on_route"
                )
            ),

        "has_construction":
            bool(
                route_result.get(
                    "has_construction_on_route"
                )
            ),

        "has_steep_slope":
            bool(
                route_result.get(
                    "has_steep_slope"
                )
            ),

        "accessibility":
            route_result.get(
                "accessibility",
                "Unknown"
            )
    }


def _format_time(
    minutes: float
) -> str:
    """
    Format minutes into a readable duration.
    """

    minutes = max(
        0,
        int(round(minutes))
    )

    if minutes < 60:

        return f"{minutes} min"

    hours = minutes // 60
    remaining = minutes % 60

    if remaining == 0:

        return (
            f"{hours} hr"
            if hours == 1
            else f"{hours} hrs"
        )

    return (
        f"{hours} hr {remaining} min"
        if hours == 1
        else f"{hours} hrs {remaining} min"
    )


# ---------------------------------------------------------------------------
# ROUTE SUMMARY
# ---------------------------------------------------------------------------

def get_route_summary(
    route_result: Dict[str, Any]
) -> str:
    """
    Generate a GUI-friendly route summary.
    """

    if not route_result:

        return "No route information available."

    if "error" in route_result:

        return str(
            route_result["error"]
        )

    distance = route_result.get(
        "total_distance_km",
        0
    )

    time_minutes = route_result.get(
        "estimated_time_minutes",
        0
    )

    accessibility = route_result.get(
        "accessibility",
        "Unknown"
    )

    warnings = route_result.get(
        "warnings",
        []
    )

    summary = (
        f"Route distance: {distance:.2f} km. "
        f"Estimated walking time: "
        f"{_format_time(time_minutes)}. "
        f"Accessibility: {accessibility}."
    )

    if warnings:

        summary += (
            f" {len(warnings)} warning(s) "
            "were detected."
        )

    else:

        summary += (
            " No major accessibility warnings "
            "were detected in the available map data."
        )

    return summary


# ---------------------------------------------------------------------------
# DEMO / TEST
# ---------------------------------------------------------------------------

def run_demo():
    """
    Run a complete offline routing demonstration.
    """

    print("\n")
    print("=" * 70)
    print("WHEELGUIDE ACCESSIBILITY ROUTING DEMO")
    print("=" * 70)

    G = build_demo_graph()

    print("\nAvailable locations:")

    for node in G.nodes:

        print(
            f"  • {node}"
        )

    print("\nFinding routes...\n")

    result = compare_shortest_vs_accessible(
        G,
        "A_Start",
        "E_Destination"
    )

    shortest = result[
        "shortest_route"
    ]

    accessible = result[
        "accessible_route"
    ]

    print("SHORTest route")
    print("-" * 40)

    print(
        "Path:",
        " → ".join(
            str(x)
            for x in shortest["path"]
        )
    )

    print(
        "Distance:",
        shortest["total_distance_km"],
        "km"
    )

    print(
        "Time:",
        shortest["estimated_time_minutes"],
        "minutes"
    )

    print(
        "Stairs:",
        shortest["has_stairs_on_route"]
    )

    print(
        "Warnings:",
        shortest["warnings"]
    )

    print("\nWHEELCHAIR-FRIENDLY ROUTE")
    print("-" * 40)

    print(
        "Path:",
        " → ".join(
            str(x)
            for x in accessible["path"]
        )
    )

    print(
        "Distance:",
        accessible["total_distance_km"],
        "km"
    )

    print(
        "Time:",
        accessible["estimated_time_minutes"],
        "minutes"
    )

    print(
        "Stairs:",
        accessible["has_stairs_on_route"]
    )

    print(
        "Warnings:",
        accessible["warnings"]
    )

    print("\nCOMPARISON")
    print("-" * 40)

    comparison = result[
        "comparison"
    ]

    print(
        comparison["recommendation"]
    )

    print("=" * 70)


# ---------------------------------------------------------------------------
# DIRECT EXECUTION
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_demo()