"""
Route Logic Module for Optimal EV Transportation Planning.
Handles route metrics, travel time estimations, detour calculations, and spatial coordinates.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class RouteDetails:
    route_id: str
    source: str
    destination: str
    distance_km: float
    base_travel_time_min: float
    avg_speed_kmh: float
    source_lat: float
    source_lon: float
    dest_lat: float
    dest_lon: float
    highway_name: str
    description: str

    @property
    def base_travel_time_hours(self) -> float:
        return round(self.base_travel_time_min / 60.0, 2)


def parse_route(route_dict: Dict) -> RouteDetails:
    """Parses a route dictionary into a typed RouteDetails object."""
    return RouteDetails(
        route_id=str(route_dict["route_id"]),
        source=str(route_dict["source"]),
        destination=str(route_dict["destination"]),
        distance_km=float(route_dict["distance_km"]),
        base_travel_time_min=float(route_dict["base_travel_time_min"]),
        avg_speed_kmh=float(route_dict.get("avg_speed_kmh", 60.0)),
        source_lat=float(route_dict.get("source_lat", 0.0)),
        source_lon=float(route_dict.get("source_lon", 0.0)),
        dest_lat=float(route_dict.get("dest_lat", 0.0)),
        dest_lon=float(route_dict.get("dest_lon", 0.0)),
        highway_name=str(route_dict.get("highway_name", "National Highway")),
        description=str(route_dict.get("description", "")),
    )


def calculate_detour_travel_time_min(
    distance_from_route_km: float, avg_speed_kmh: float = 40.0
) -> float:
    """
    Calculates extra round-trip detour travel time (minutes) to visit a station.
    Round-trip detour distance = 2 * distance_from_route_km.
    Detour driving is typically on arterial/service roads, so default speed is 40 km/h.
    """
    if distance_from_route_km <= 0:
        return 0.0
    detour_dist_total = 2.0 * distance_from_route_km
    detour_time_hours = detour_dist_total / avg_speed_kmh
    return round(detour_time_hours * 60.0, 1)


def generate_route_corridor_coordinates(
    route: RouteDetails, num_points: int = 20
) -> List[Tuple[float, float]]:
    """
    Generates interpolated coordinates between source and destination for map visualization.
    """
    points = []
    for i in range(num_points + 1):
        ratio = i / num_points
        lat = route.source_lat + ratio * (route.dest_lat - route.source_lat)
        lon = route.source_lon + ratio * (route.dest_lon - route.source_lon)
        points.append((lat, lon))
    return points
