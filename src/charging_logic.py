"""
Charging Logic Module for Optimal EV Transportation Planning.
Calculates required charging energy, charging time, total journey time,
and selects the optimal charging station based on total travel duration.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd

from src.data_loader import DataLoader
from src.energy_logic import VehicleSpecs
from src.route_logic import RouteDetails, calculate_detour_travel_time_min
from src.station_logic import StationCandidate, get_evaluated_candidate_stations


@dataclass
class StationPlanMetrics:
    candidate: StationCandidate
    # Waiting metrics (ML predicted)
    predicted_waiting_time_min: float
    confidence_score: float
    predicted_queue_len: int
    time_window: str
    # Charging energy & time
    required_charging_energy_kwh: float
    departure_energy_kwh: float
    departure_soc_pct: float
    charging_time_min: float
    # Detour & Travel
    detour_distance_km: float
    detour_travel_time_min: float
    total_travel_time_min: float
    # Total Journey Time = Travel Time + Waiting Time + Charging Time
    total_journey_time_min: float
    is_recommended: bool = False

    @property
    def total_journey_time_formatted(self) -> str:
        hours = int(self.total_journey_time_min // 60)
        mins = int(round(self.total_journey_time_min % 60))
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins} min"

    @property
    def charging_time_formatted(self) -> str:
        hours = int(self.charging_time_min // 60)
        mins = int(round(self.charging_time_min % 60))
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins} min"


@dataclass
class CompleteTripPlan:
    route: RouteDetails
    vehicle: VehicleSpecs
    charging_required: bool
    explanation: str
    energy_deficit_kwh: float
    direct_travel_time_min: float
    # Plans for all candidate stations
    all_station_plans: List[StationPlanMetrics]
    feasible_station_plans: List[StationPlanMetrics]
    recommended_plan: Optional[StationPlanMetrics]
    time_window: str


def calculate_required_charging_energy(
    arrival_energy_kwh: float,
    remaining_energy_to_dest_kwh: float,
    desired_destination_energy_kwh: float,
    battery_capacity_kwh: float,
) -> float:
    """
    Formula:
    Target departure energy = remaining energy needed to destination + desired destination reserve buffer.
    Required charging energy = max(0, Target departure energy - arrival energy).
    Capped so departure energy does not exceed total battery capacity.
    """
    target_departure_energy = min(
        remaining_energy_to_dest_kwh + desired_destination_energy_kwh,
        battery_capacity_kwh,
    )
    charge_needed = max(0.0, target_departure_energy - arrival_energy_kwh)
    return round(charge_needed, 2)


def calculate_charging_time_min(charging_energy_kwh: float, charger_power_kw: float) -> float:
    """
    Formula:
    Charging Time (minutes) = (Charging Energy (kWh) / Charger Power (kW)) * 60
    """
    if charger_power_kw <= 0:
        return 0.0
    time_hours = charging_energy_kwh / charger_power_kw
    return round(time_hours * 60.0, 1)


def calculate_total_journey_time_min(
    travel_time_min: float, waiting_time_min: float, charging_time_min: float
) -> float:
    """
    Core Optimization Objective:
    Total Journey Time = Travel Time + Waiting Time + Charging Time
    """
    return round(travel_time_min + waiting_time_min + charging_time_min, 1)


def select_optimal_charging_station(
    feasible_plans: List[StationPlanMetrics],
) -> Optional[StationPlanMetrics]:
    """
    Selects the optimal charging station among feasible candidates.
    IMPORTANT: Recommendation is based strictly on minimum Total Journey Time,
    NOT simply by distance or closest proximity.
    """
    if not feasible_plans:
        return None

    # Sort strictly by total journey time ascending
    sorted_plans = sorted(feasible_plans, key=lambda p: p.total_journey_time_min)
    best_plan = sorted_plans[0]
    best_plan.is_recommended = True
    return best_plan


def compute_station_plan(
    candidate: StationCandidate,
    route: RouteDetails,
    vehicle: VehicleSpecs,
    data_loader: DataLoader,
    time_window: str = "Morning (06:00-12:00)",
) -> StationPlanMetrics:
    """
    Computes all journey metrics for a specific candidate station:
    Waiting Time, Detour, Charging Energy, Charging Time, and Total Journey Time.
    """
    # 1. Fetch predicted waiting time from Mock ML dataset
    wait_info = data_loader.get_waiting_time_info(candidate.station_id, time_window=time_window)
    waiting_time_min = wait_info["predicted_waiting_time_min"]
    confidence = wait_info["confidence_score"]
    queue_len = wait_info["predicted_queue_len"]

    # 2. Detour distance and detour travel time
    detour_dist_total = round(2.0 * candidate.distance_from_route_km, 2)
    detour_time_min = calculate_detour_travel_time_min(candidate.distance_from_route_km, avg_speed_kmh=40.0)
    total_travel_time_min = round(route.base_travel_time_min + detour_time_min, 1)

    if not candidate.is_feasible:
        # Station is unreachable or breaches safety threshold
        return StationPlanMetrics(
            candidate=candidate,
            predicted_waiting_time_min=waiting_time_min,
            confidence_score=confidence,
            predicted_queue_len=queue_len,
            time_window=time_window,
            required_charging_energy_kwh=0.0,
            departure_energy_kwh=0.0,
            departure_soc_pct=0.0,
            charging_time_min=0.0,
            detour_distance_km=detour_dist_total,
            detour_travel_time_min=detour_time_min,
            total_travel_time_min=total_travel_time_min,
            total_journey_time_min=float("inf"),
            is_recommended=False,
        )

    # 3. Required charging energy calculation
    required_charging_energy = calculate_required_charging_energy(
        arrival_energy_kwh=candidate.arrival_energy_kwh,
        remaining_energy_to_dest_kwh=candidate.remaining_energy_to_dest_kwh,
        desired_destination_energy_kwh=vehicle.desired_destination_energy_kwh,
        battery_capacity_kwh=vehicle.battery_capacity_kwh,
    )

    departure_energy = round(candidate.arrival_energy_kwh + required_charging_energy, 2)
    departure_soc = round((departure_energy / vehicle.battery_capacity_kwh) * 100.0, 1)

    # 4. Charging time calculation
    charging_time_min = calculate_charging_time_min(
        charging_energy_kwh=required_charging_energy,
        charger_power_kw=candidate.charging_power_kw,
    )

    # 5. Total Journey Time (Travel Time + Waiting Time + Charging Time)
    total_journey_time_min = calculate_total_journey_time_min(
        travel_time_min=total_travel_time_min,
        waiting_time_min=waiting_time_min,
        charging_time_min=charging_time_min,
    )

    return StationPlanMetrics(
        candidate=candidate,
        predicted_waiting_time_min=waiting_time_min,
        confidence_score=confidence,
        predicted_queue_len=queue_len,
        time_window=time_window,
        required_charging_energy_kwh=required_charging_energy,
        departure_energy_kwh=departure_energy,
        departure_soc_pct=departure_soc,
        charging_time_min=charging_time_min,
        detour_distance_km=detour_dist_total,
        detour_travel_time_min=detour_time_min,
        total_travel_time_min=total_travel_time_min,
        total_journey_time_min=total_journey_time_min,
        is_recommended=False,
    )


def plan_ev_journey(
    route_dict: Dict,
    vehicle: VehicleSpecs,
    data_loader: DataLoader,
    time_window: str = "Morning (06:00-12:00)",
    safety_soc_pct: float = 10.0,
) -> CompleteTripPlan:
    """
    Main orchestration pipeline:
    User Input -> Route -> Energy -> Candidate Stations -> Feasibility -> Waiting Time -> Charging Time -> Total Journey Time -> Recommendation.
    """
    route = RouteDetails(
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

    # Step 1 & 2: Direct Trip Energy Analysis
    energy_required_kwh = round(route.distance_km / vehicle.ev_efficiency_km_per_kwh, 2)
    initial_energy_kwh = round(vehicle.current_energy_kwh, 2)
    desired_dest_energy_kwh = round(vehicle.desired_destination_energy_kwh, 2)
    energy_balance_at_dest = round(initial_energy_kwh - energy_required_kwh, 2)
    final_soc_direct = round((energy_balance_at_dest / vehicle.battery_capacity_kwh) * 100.0, 1)

    charging_required = energy_balance_at_dest < desired_dest_energy_kwh

    if not charging_required:
        energy_deficit_kwh = 0.0
        explanation = (
            f"The vehicle can complete the {route.distance_km:.0f} km trip directly with {final_soc_direct:.1f}% SOC remaining, "
            f"exceeding your desired {vehicle.desired_destination_soc_pct:.0f}% destination buffer. No charging stop is needed."
        )
    else:
        energy_deficit_kwh = round(desired_dest_energy_kwh - energy_balance_at_dest, 2)
        explanation = (
            f"Direct arrival SOC would be {final_soc_direct:.1f}% ({energy_balance_at_dest:.1f} kWh), falling short of "
            f"your target destination buffer of {vehicle.desired_destination_soc_pct:.0f}% ({desired_dest_energy_kwh:.1f} kWh). "
            f"An intermediate charging stop is required."
        )

    # Step 3, 4 & 5: Load stations & evaluate feasibility
    stations_df = data_loader.get_stations_for_route(route.route_id)
    candidates = get_evaluated_candidate_stations(
        stations_df=stations_df,
        route_distance_km=route.distance_km,
        vehicle=vehicle,
        safety_soc_pct=safety_soc_pct,
    )

    # Step 6, 7, 8: Compute journey metrics for each candidate
    all_station_plans: List[StationPlanMetrics] = []
    for cand in candidates:
        plan = compute_station_plan(
            candidate=cand,
            route=route,
            vehicle=vehicle,
            data_loader=data_loader,
            time_window=time_window,
        )
        all_station_plans.append(plan)

    # Keep feasible candidates
    feasible_plans = [p for p in all_station_plans if p.candidate.is_feasible]

    # Step 9 & 10: Station selection by minimum Total Journey Time
    recommended_plan = select_optimal_charging_station(feasible_plans)

    return CompleteTripPlan(
        route=route,
        vehicle=vehicle,
        charging_required=charging_required,
        explanation=explanation,
        energy_deficit_kwh=energy_deficit_kwh,
        direct_travel_time_min=route.base_travel_time_min,
        all_station_plans=all_station_plans,
        feasible_station_plans=feasible_plans,
        recommended_plan=recommended_plan,
        time_window=time_window,
    )
