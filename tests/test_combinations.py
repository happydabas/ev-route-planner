"""
Multi-Scenario Verification Test for Optimal EV Transportation Planning.
Tests multiple combinations of source, destination, battery capacity, SOC, and efficiency.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import DataLoader
from src.energy_logic import VehicleSpecs
from src.charging_logic import plan_ev_journey
from src.ui import format_duration


def run_scenario_tests():
    loader = DataLoader()
    
    scenarios = [
        {
            "name": "Delhi -> Jaipur (Standard EV, Medium SOC, Charging Required)",
            "source": "Delhi",
            "dest": "Jaipur",
            "capacity": 60.0,
            "soc": 80.0,
            "efficiency": 6.0,
            "desired_soc": 20.0,
            "expect_charging": True,
        },
        {
            "name": "Delhi -> Jaipur (Long Range EV, High SOC, Charging NOT Required)",
            "source": "Delhi",
            "dest": "Jaipur",
            "capacity": 100.0,
            "soc": 95.0,
            "efficiency": 6.0,
            "desired_soc": 10.0,
            "expect_charging": False,
        },
        {
            "name": "Mumbai -> Pune (Short Expressway, Standard Battery, Charging NOT Required)",
            "source": "Mumbai",
            "dest": "Pune",
            "capacity": 50.0,
            "soc": 85.0,
            "efficiency": 5.5,
            "desired_soc": 15.0,
            "expect_charging": False,
        },
        {
            "name": "Bengaluru -> Chennai (Long Distance, Standard SOC, Charging Required)",
            "source": "Bengaluru",
            "dest": "Chennai",
            "capacity": 60.0,
            "soc": 70.0,
            "efficiency": 6.0,
            "desired_soc": 20.0,
            "expect_charging": True,
        },
        {
            "name": "Bengaluru -> Mysuru (Medium Distance, Low Battery, Charging Required)",
            "source": "Bengaluru",
            "dest": "Mysuru",
            "capacity": 30.0,
            "soc": 50.0,
            "efficiency": 6.0,
            "desired_soc": 20.0,
            "expect_charging": True,
        },
        {
            "name": "Mumbai -> Surat (Long Coastal Corridor, High Power DC Optimization)",
            "source": "Mumbai",
            "dest": "Surat",
            "capacity": 75.0,
            "soc": 65.0,
            "efficiency": 5.5,
            "desired_soc": 20.0,
            "expect_charging": True,
        },
    ]

    print("=" * 75)
    print("RUNNING MULTI-SCENARIO EV PLANNING VERIFICATION")
    print("=" * 75)

    for i, s in enumerate(scenarios, 1):
        route = loader.get_route(s["source"], s["dest"])
        assert route is not None, f"Route {s['source']} -> {s['dest']} must exist"

        vehicle = VehicleSpecs(
            battery_capacity_kwh=s["capacity"],
            current_soc_pct=s["soc"],
            ev_efficiency_km_per_kwh=s["efficiency"],
            desired_destination_soc_pct=s["desired_soc"],
        )

        plan = plan_ev_journey(
            route_dict=route,
            vehicle=vehicle,
            data_loader=loader,
            time_window="Morning (06:00-12:00)",
            safety_soc_pct=10.0,
        )

        assert plan.charging_required == s["expect_charging"], (
            f"Scenario '{s['name']}': Expected charging_required={s['expect_charging']}, got {plan.charging_required}"
        )

        print(f"\n[{i}/{len(scenarios)}] {s['name']}")
        print(f"  Route: {plan.route.source} -> {plan.route.destination} ({plan.route.distance_km:.0f} km)")
        print(f"  Charging Required: {'YES' if plan.charging_required else 'NO'}")
        
        if plan.charging_required:
            assert plan.recommended_plan is not None, "Feasible station should be found"
            rec = plan.recommended_plan
            print(f"  ⭐ Recommended Station: {rec.candidate.station_name}")
            print(f"  ⚡ Power: {rec.candidate.charging_power_kw:.0f} kW | Detour: {rec.candidate.distance_from_route_km:.1f} km")
            print(f"  ⏳ Waiting Time: {format_duration(rec.predicted_waiting_time_min)}")
            print(f"  ⚡ Charging Time: {format_duration(rec.charging_time_min)} (Energy: {rec.required_charging_energy_kwh:.1f} kWh)")
            print(f"  ⏱️ Total Journey Time: {format_duration(rec.total_journey_time_min)}")
        else:
            print(f"  ⏱️ Direct Journey Time: {format_duration(plan.direct_travel_time_min)}")

    print("\n" + "=" * 75)
    print("ALL SCENARIOS VALIDATED AND VERIFIED SUCCESSFULLY! 🎉")
    print("=" * 75)


if __name__ == "__main__":
    run_scenario_tests()
