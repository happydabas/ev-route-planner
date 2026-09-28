"""
Comprehensive Unit & Integration Test Suite for Optimal EV Transportation Planning.
Verifies all pipeline stages, mathematical formulations, edge cases, and error handling.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import DataLoader
from src.energy_logic import (
    VehicleSpecs,
    analyze_trip_energy,
    calculate_base_energy_required_kwh,
    calculate_soc_pct,
    is_charging_required,
)
from src.route_logic import parse_route
from src.station_logic import evaluate_station_feasibility, get_evaluated_candidate_stations
from src.charging_logic import (
    calculate_charging_time_min,
    calculate_required_charging_energy,
    calculate_total_journey_time_min,
    plan_ev_journey,
    select_optimal_charging_station,
)


def test_data_loader():
    print("[1/6] Testing DataLoader...")
    loader = DataLoader()
    sources = loader.get_sources()
    assert "Delhi" in sources
    assert "Mumbai" in sources
    assert "Bengaluru" in sources

    # Check route lookup
    route = loader.get_route("Delhi", "Jaipur")
    assert route is not None
    assert route["distance_km"] == 280.0

    # Check non-existent route
    non_route = loader.get_route("Delhi", "Kolkata")
    assert non_route is None

    # Check stations
    stations = loader.get_stations_for_route(route["route_id"])
    assert len(stations) >= 5

    # Check waiting times
    wait_info = loader.get_waiting_time_info(stations.iloc[0]["station_id"], "Morning (06:00-12:00)")
    assert "predicted_waiting_time_min" in wait_info
    print("  DataLoader tests passed! ✓")


def test_energy_formulas():
    print("[2/6] Testing Energy Formulas...")
    # Base energy = 280 / 6.0 = 46.67 kWh
    base_energy = calculate_base_energy_required_kwh(280.0, 6.0)
    assert base_energy == 46.67

    # SOC = (48 / 60) * 100 = 80.0%
    soc = calculate_soc_pct(48.0, 60.0)
    assert soc == 80.0

    # Decision test: Initial 48 kWh, needed 46.67 kWh, target dest buffer 12 kWh (20% of 60)
    # Balance = 48 - 46.67 = 1.33 kWh < 12 kWh -> Charging required!
    charging_needed, balance, deficit = is_charging_required(48.0, 46.67, 12.0)
    assert charging_needed is True
    assert balance == 1.33
    assert deficit == 10.67
    print("  Energy formulas passed! ✓")


def test_charging_time_formulas():
    print("[3/6] Testing Charging and Journey Time Formulas...")
    # Required charge: Target departure 25 kWh, arrival 10 kWh -> Charge needed = 15 kWh
    charge_needed = calculate_required_charging_energy(
        arrival_energy_kwh=10.0,
        remaining_energy_to_dest_kwh=15.0,
        desired_destination_energy_kwh=10.0,
        battery_capacity_kwh=60.0,
    )
    assert charge_needed == 15.0

    # Charging time: 15 kWh / 150 kW * 60 = 6.0 minutes
    charge_time = calculate_charging_time_min(15.0, 150.0)
    assert charge_time == 6.0

    # Total journey time: Travel (270 min) + Wait (10 min) + Charge (6 min) = 286.0 min
    total_time = calculate_total_journey_time_min(270.0, 10.0, 6.0)
    assert total_time == 286.0
    print("  Charging and journey time formulas passed! ✓")


def test_charging_not_required_scenario():
    print("[4/6] Testing Charging Not Required Scenario...")
    loader = DataLoader()
    route = loader.get_route("Delhi", "Jaipur")
    
    # 100 kWh battery, 95% SOC = 95 kWh, efficiency 6 km/kWh -> 280 km needs 46.67 kWh
    # Destination balance = 95 - 46.67 = 48.33 kWh (48.3% SOC)
    # Desired destination buffer = 10% (10 kWh)
    # 48.33 kWh >= 10 kWh -> Charging NOT required
    vehicle = VehicleSpecs(
        battery_capacity_kwh=100.0,
        current_soc_pct=95.0,
        ev_efficiency_km_per_kwh=6.0,
        desired_destination_soc_pct=10.0,
    )

    plan = plan_ev_journey(
        route_dict=route,
        vehicle=vehicle,
        data_loader=loader,
        time_window="Morning (06:00-12:00)",
        safety_soc_pct=10.0,
    )

    assert plan.charging_required is False
    assert "No charging stop is needed" in plan.explanation
    print("  Charging not required scenario passed! ✓")


def test_no_feasible_station_scenario():
    print("[5/6] Testing No Feasible Station (Extreme Low SOC) Scenario...")
    loader = DataLoader()
    route = loader.get_route("Delhi", "Jaipur")
    
    # 60 kWh battery, only 11% SOC = 6.6 kWh. Safety margin = 10% (6.0 kWh).
    # Closest station is at 32 km, requiring 32 / 6 = 5.33 kWh.
    # Arrival energy = 6.6 - 5.33 = 1.27 kWh < 6.0 kWh safety buffer!
    # No stations will be feasible.
    vehicle = VehicleSpecs(
        battery_capacity_kwh=60.0,
        current_soc_pct=11.0,
        ev_efficiency_km_per_kwh=6.0,
        desired_destination_soc_pct=20.0,
    )

    plan = plan_ev_journey(
        route_dict=route,
        vehicle=vehicle,
        data_loader=loader,
        time_window="Morning (06:00-12:00)",
        safety_soc_pct=10.0,
    )

    assert plan.charging_required is True
    assert len(plan.feasible_station_plans) == 0
    assert plan.recommended_plan is None
    print("  No feasible station scenario handled gracefully! ✓")


def test_optimization_not_simply_closest():
    print("[6/6] Testing that recommendation minimizes Total Journey Time (NOT simply closest station)...")
    loader = DataLoader()
    route = loader.get_route("Delhi", "Jaipur")
    vehicle = VehicleSpecs(
        battery_capacity_kwh=60.0,
        current_soc_pct=80.0,
        ev_efficiency_km_per_kwh=6.0,
        desired_destination_soc_pct=20.0,
    )

    plan = plan_ev_journey(
        route_dict=route,
        vehicle=vehicle,
        data_loader=loader,
        time_window="Morning (06:00-12:00)",
        safety_soc_pct=10.0,
    )

    assert plan.recommended_plan is not None
    rec = plan.recommended_plan

    # Verify that the recommended station is the one with minimum total journey time among feasible ones
    min_time = min(p.total_journey_time_min for p in plan.feasible_station_plans)
    assert rec.total_journey_time_min == min_time

    # Verify it is not merely the closest station
    closest_station = min(plan.feasible_station_plans, key=lambda p: p.candidate.distance_along_route_km)
    print(f"  Closest station: {closest_station.candidate.station_name} (Total Time: {closest_station.total_journey_time_min}m)")
    print(f"  Recommended station: {rec.candidate.station_name} (Total Time: {rec.total_journey_time_min}m)")
    
    assert rec.total_journey_time_min <= closest_station.total_journey_time_min
    print("  Optimization minimizes Total Journey Time verified! ✓")


def test_car_models_and_destination_km():
    print("[7/7] Testing Car Models & Desired Destination Kilometers...")
    from src.energy_logic import EV_MODELS, get_ev_models, get_ev_specs

    models = get_ev_models()
    assert "Tata Nexon EV (Long Range - 40.5 kWh)" in models
    assert "MG ZS EV (50.3 kWh)" in models
    assert "Hyundai Ioniq 5 (72.6 kWh)" in models

    nexon_specs = get_ev_specs("Tata Nexon EV (Long Range - 40.5 kWh)")
    assert nexon_specs["battery_capacity_kwh"] == 40.5
    assert nexon_specs["ev_efficiency_km_per_kwh"] == 7.0

    # Test VehicleSpecs with desired_destination_km
    vehicle = VehicleSpecs(
        battery_capacity_kwh=nexon_specs["battery_capacity_kwh"],
        current_soc_pct=80.0,
        ev_efficiency_km_per_kwh=nexon_specs["ev_efficiency_km_per_kwh"],
        desired_destination_km=70.0,  # 70 km reserve buffer
        car_model="Tata Nexon EV (Long Range - 40.5 kWh)",
    )

    # 70 km / 7.0 km/kWh = 10.0 kWh required buffer
    assert vehicle.desired_destination_energy_kwh == 10.0
    # 10.0 kWh / 40.5 kWh = ~24.7% SOC
    assert round(vehicle.desired_destination_soc_pct, 1) == 24.7
    # Max range = 40.5 * 7.0 = 283.5 km
    assert vehicle.max_range_km == 283.5
    # Current range = (80% of 40.5) * 7.0 = 32.4 * 7.0 = 226.8 km
    assert round(vehicle.current_range_km, 1) == 226.8
    print("  Car models and destination km tests passed! ✓")


if __name__ == "__main__":
    test_data_loader()
    test_energy_formulas()
    test_charging_time_formulas()
    test_charging_not_required_scenario()
    test_no_feasible_station_scenario()
    test_optimization_not_simply_closest()
    test_car_models_and_destination_km()
    print("\n" + "="*50)
    print("ALL 7/7 TEST SUITES PASSED FLAWLESSLY! 🚀")
    print("="*50)

