"""
Station Logic Module for Optimal EV Transportation Planning.
Evaluates charging station candidate feasibility, reachable safety margins, and station metadata.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd

from src.energy_logic import VehicleSpecs, calculate_energy_to_station


@dataclass
class StationCandidate:
    station_id: str
    station_name: str
    route_id: str
    distance_along_route_km: float
    distance_from_route_km: float
    charger_type: str
    charging_power_kw: float
    available_slots: int
    total_slots: int
    operator: str
    amenities: str
    latitude: float
    longitude: float
    # Feasibility metrics
    distance_to_station_km: float
    energy_to_station_kwh: float
    arrival_energy_kwh: float
    arrival_soc_pct: float
    is_feasible: bool
    feasibility_reason: str
    remaining_distance_to_dest_km: float
    remaining_energy_to_dest_kwh: float


def evaluate_station_feasibility(
    station_row: pd.Series,
    route_distance_km: float,
    vehicle: VehicleSpecs,
    safety_soc_pct: float = 10.0,
) -> StationCandidate:
    """
    Evaluates whether an EV can reach the candidate station while maintaining safety SOC,
    and whether the remaining journey to destination is achievable.
    """
    dist_along = float(station_row["distance_along_route_km"])
    dist_from = float(station_row["distance_from_route_km"])
    dist_to_station = dist_along + dist_from

    energy_to_station = calculate_energy_to_station(
        dist_along, dist_from, vehicle.ev_efficiency_km_per_kwh
    )

    safety_energy_threshold = vehicle.battery_capacity_kwh * (safety_soc_pct / 100.0)
    current_energy = vehicle.current_energy_kwh
    arrival_energy = round(current_energy - energy_to_station, 2)
    arrival_soc = round((arrival_energy / vehicle.battery_capacity_kwh) * 100.0, 1)

    # Remaining distance from station back to route and onto destination
    remaining_dist = (route_distance_km - dist_along) + dist_from
    remaining_energy_needed = round(remaining_dist / vehicle.ev_efficiency_km_per_kwh, 2)

    # Feasibility checks
    if arrival_energy < safety_energy_threshold:
        is_feasible = False
        if arrival_energy < 0:
            feasibility_reason = (
                f"Unreachable: Battery depletes {abs(arrival_energy):.1f} kWh before reaching station."
            )
        else:
            feasibility_reason = (
                f"Unfeasible: Arrival SOC ({arrival_soc:.1f}%) is below the {safety_soc_pct:.0f}% safety margin."
            )
    else:
        # Check if the battery can hold enough energy to finish the trip
        max_possible_charge = vehicle.battery_capacity_kwh
        max_departure_energy = max_possible_charge
        required_at_departure = remaining_energy_needed + vehicle.desired_destination_energy_kwh

        if required_at_departure > max_departure_energy:
            is_feasible = False
            feasibility_reason = (
                f"Unfeasible: Remaining distance ({remaining_dist:.1f} km) requires more energy ({required_at_departure:.1f} kWh) "
                f"than maximum battery capacity ({vehicle.battery_capacity_kwh:.1f} kWh)."
            )
        else:
            is_feasible = True
            feasibility_reason = f"Feasible: Arrival SOC is {arrival_soc:.1f}% (>= {safety_soc_pct:.0f}% safety margin)."

    return StationCandidate(
        station_id=str(station_row["station_id"]),
        station_name=str(station_row["station_name"]),
        route_id=str(station_row["route_id"]),
        distance_along_route_km=dist_along,
        distance_from_route_km=dist_from,
        charger_type=str(station_row["charger_type"]),
        charging_power_kw=float(station_row["charging_power_kw"]),
        available_slots=int(station_row["available_slots"]),
        total_slots=int(station_row["total_slots"]),
        operator=str(station_row.get("operator", "EV Network")),
        amenities=str(station_row.get("amenities", "Restroom, Cafe")),
        latitude=float(station_row.get("latitude", 0.0)),
        longitude=float(station_row.get("longitude", 0.0)),
        distance_to_station_km=round(dist_to_station, 1),
        energy_to_station_kwh=energy_to_station,
        arrival_energy_kwh=arrival_energy,
        arrival_soc_pct=arrival_soc,
        is_feasible=is_feasible,
        feasibility_reason=feasibility_reason,
        remaining_distance_to_dest_km=round(remaining_dist, 1),
        remaining_energy_to_dest_kwh=remaining_energy_needed,
    )


def get_evaluated_candidate_stations(
    stations_df: pd.DataFrame,
    route_distance_km: float,
    vehicle: VehicleSpecs,
    safety_soc_pct: float = 10.0,
) -> List[StationCandidate]:
    """
    Evaluates all candidate stations along the route and returns sorted list.
    """
    candidates = []
    for _, row in stations_df.iterrows():
        candidate = evaluate_station_feasibility(
            station_row=row,
            route_distance_km=route_distance_km,
            vehicle=vehicle,
            safety_soc_pct=safety_soc_pct,
        )
        candidates.append(candidate)

    # Sort candidates primarily by distance along route
    candidates.sort(key=lambda x: x.distance_along_route_km)
    return candidates
