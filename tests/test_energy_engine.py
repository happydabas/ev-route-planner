"""
Unit Test Suite for EV Energy & Charging Calculation Engine.
Tests all deterministic energy calculations, lookups, power parsing,
feasibility checks, charging stop computations, and input validations.
"""

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.energy_engine import (
    EVSpecifications,
    calculate_battery_energy_kwh,
    calculate_charging_energy_required,
    calculate_charging_stop,
    calculate_charging_time_minutes,
    calculate_energy_consumed_kwh,
    calculate_remaining_energy_and_soc,
    calculate_route_feasibility,
    calculate_soc_from_energy,
    get_available_ev_models,
    lookup_ev_specifications,
    parse_charging_power_kw,
)


class TestEnergyEngine(unittest.TestCase):

    # -----------------------------------------------------------------------
    # 1. EV Lookup Tests
    # -----------------------------------------------------------------------
    def test_ev_lookup_valid(self):
        ev = lookup_ev_specifications("Tata Nexon EV (Long Range)")
        self.assertEqual(ev.manufacturer, "Tata")
        self.assertEqual(ev.model, "Nexon EV (Long Range)")
        self.assertEqual(ev.battery_capacity_kwh, 40.5)
        self.assertEqual(ev.energy_consumption_kwh_per_km, 0.143)
        self.assertAlmostEqual(ev.max_range_km, 283.2, places=1)

    def test_ev_lookup_by_model_name(self):
        ev = lookup_ev_specifications("Ioniq 5")
        self.assertEqual(ev.manufacturer, "Hyundai")
        self.assertEqual(ev.battery_capacity_kwh, 72.6)

    def test_ev_lookup_invalid_raises(self):
        with self.assertRaises(ValueError):
            lookup_ev_specifications("NonExistent EV Model 9000")

    def test_ev_lookup_empty_raises(self):
        with self.assertRaises(ValueError):
            lookup_ev_specifications("")

    def test_get_available_ev_models(self):
        models = get_available_ev_models()
        self.assertGreaterEqual(len(models), 10)
        self.assertIn("Tata Nexon EV (Long Range)", models)

    # -----------------------------------------------------------------------
    # 2. Battery & Consumption Calculations
    # -----------------------------------------------------------------------
    def test_battery_energy_calculation(self):
        # 40.5 kWh @ 80% = 32.4 kWh
        energy = calculate_battery_energy_kwh(40.5, 80.0)
        self.assertEqual(energy, 32.4)

        # 60 kWh @ 0% = 0 kWh
        self.assertEqual(calculate_battery_energy_kwh(60.0, 0.0), 0.0)

        # 60 kWh @ 100% = 60.0 kWh
        self.assertEqual(calculate_battery_energy_kwh(60.0, 100.0), 60.0)

    def test_battery_energy_invalid_inputs(self):
        with self.assertRaises(ValueError):
            calculate_battery_energy_kwh(-40.0, 50.0)  # Negative capacity
        with self.assertRaises(ValueError):
            calculate_battery_energy_kwh(40.0, -10.0)  # Negative SOC
        with self.assertRaises(ValueError):
            calculate_battery_energy_kwh(40.0, 110.0)  # SOC > 100

    def test_energy_consumed_calculation(self):
        # 100 km * 0.150 kWh/km = 15.0 kWh
        consumed = calculate_energy_consumed_kwh(100.0, 0.150)
        self.assertEqual(consumed, 15.0)

        # 0 km = 0 kWh
        self.assertEqual(calculate_energy_consumed_kwh(0.0, 0.143), 0.0)

    def test_energy_consumed_invalid_inputs(self):
        with self.assertRaises(ValueError):
            calculate_energy_consumed_kwh(-50.0, 0.15)  # Negative distance
        with self.assertRaises(ValueError):
            calculate_energy_consumed_kwh(50.0, 0.0)    # Zero consumption
        with self.assertRaises(ValueError):
            calculate_energy_consumed_kwh(50.0, -0.15)  # Negative consumption

    def test_soc_from_energy(self):
        # 30 kWh / 60 kWh = 50.0%
        self.assertEqual(calculate_soc_from_energy(30.0, 60.0), 50.0)

    def test_remaining_energy_and_soc(self):
        # Battery 40.0 kWh, SOC 80% (32.0 kWh).
        # Travel 100 km @ 0.15 kWh/km = 15.0 kWh consumed.
        # Remaining energy = 32.0 - 15.0 = 17.0 kWh.
        # Remaining SOC = 17.0 / 40.0 * 100 = 42.5%.
        rem_energy, rem_soc = calculate_remaining_energy_and_soc(40.0, 80.0, 100.0, 0.15)
        self.assertEqual(rem_energy, 17.0)
        self.assertEqual(rem_soc, 42.5)

    # -----------------------------------------------------------------------
    # 3. Charging Requirement Calculations
    # -----------------------------------------------------------------------
    def test_charging_energy_required(self):
        # Battery 60 kWh, Current 20%, Target 80%
        # Increase = 60%, Energy = 60 * 0.60 = 36.0 kWh
        energy_req, soc_inc = calculate_charging_energy_required(60.0, 20.0, 80.0)
        self.assertEqual(soc_inc, 60.0)
        self.assertEqual(energy_req, 36.0)

    def test_charging_energy_same_soc(self):
        energy_req, soc_inc = calculate_charging_energy_required(60.0, 80.0, 80.0)
        self.assertEqual(soc_inc, 0.0)
        self.assertEqual(energy_req, 0.0)

    def test_charging_energy_invalid(self):
        with self.assertRaises(ValueError):
            calculate_charging_energy_required(60.0, 80.0, 50.0)  # Target < Current
        with self.assertRaises(ValueError):
            calculate_charging_energy_required(60.0, -10.0, 80.0) # Current < 0
        with self.assertRaises(ValueError):
            calculate_charging_energy_required(60.0, 20.0, 110.0) # Target > 100

    # -----------------------------------------------------------------------
    # 4. Charging Time Calculations
    # -----------------------------------------------------------------------
    def test_charging_time_calculation(self):
        # 30 kWh @ 60 kW = 0.5 hours = 30.0 minutes
        self.assertEqual(calculate_charging_time_minutes(30.0, 60.0), 30.0)

        # 15 kWh @ 150 kW = 0.1 hours = 6.0 minutes
        self.assertEqual(calculate_charging_time_minutes(15.0, 150.0), 6.0)

        # 0 kWh = 0.0 minutes
        self.assertEqual(calculate_charging_time_minutes(0.0, 100.0), 0.0)

    def test_charging_time_invalid(self):
        with self.assertRaises(ValueError):
            calculate_charging_time_minutes(-10.0, 50.0)  # Negative energy
        with self.assertRaises(ValueError):
            calculate_charging_time_minutes(20.0, 0.0)    # Zero power
        with self.assertRaises(ValueError):
            calculate_charging_time_minutes(20.0, -50.0)  # Negative power

    # -----------------------------------------------------------------------
    # 5. Station Charging-Power Parsing
    # -----------------------------------------------------------------------
    def test_parse_charging_power(self):
        self.assertEqual(parse_charging_power_kw("3.3kw"), 3.3)
        self.assertEqual(parse_charging_power_kw("50kW"), 50.0)
        self.assertEqual(parse_charging_power_kw("50 kW"), 50.0)
        self.assertEqual(parse_charging_power_kw("150 KW"), 150.0)
        self.assertEqual(parse_charging_power_kw("22.5"), 22.5)
        self.assertEqual(parse_charging_power_kw(60), 60.0)
        self.assertEqual(parse_charging_power_kw(120.0), 120.0)

    def test_parse_charging_power_unparseable(self):
        self.assertIsNone(parse_charging_power_kw("nil"))
        self.assertIsNone(parse_charging_power_kw(None))
        self.assertIsNone(parse_charging_power_kw(""))
        self.assertIsNone(parse_charging_power_kw("unknown"))
        self.assertIsNone(parse_charging_power_kw(-50.0))

    # -----------------------------------------------------------------------
    # 6. Route Feasibility Tests
    # -----------------------------------------------------------------------
    def test_route_feasibility_feasible(self):
        # 40.5 kWh @ 80% SOC = 32.4 kWh available.
        # Distance 100 km @ 0.143 kWh/km = 14.3 kWh required.
        # Feasible! Remaining = 18.1 kWh (44.69% SOC).
        res = calculate_route_feasibility(
            battery_capacity_kwh=40.5,
            energy_consumption_kwh_per_km=0.143,
            current_soc_pct=80.0,
            distance_km=100.0,
        )
        self.assertTrue(res.is_feasible)
        self.assertEqual(res.energy_required_kwh, 14.3)
        self.assertEqual(res.available_energy_kwh, 32.4)
        self.assertEqual(res.remaining_energy_kwh, 18.1)
        self.assertEqual(res.deficit_kwh, 0.0)

    def test_route_feasibility_infeasible(self):
        # Distance 300 km @ 0.143 = 42.9 kWh required > 32.4 kWh available.
        res = calculate_route_feasibility(
            battery_capacity_kwh=40.5,
            energy_consumption_kwh_per_km=0.143,
            current_soc_pct=80.0,
            distance_km=300.0,
        )
        self.assertFalse(res.is_feasible)
        self.assertEqual(res.deficit_kwh, 10.5)

    # -----------------------------------------------------------------------
    # 7. Intermediate Charging-Stop Calculation
    # -----------------------------------------------------------------------
    def test_charging_stop_feasible(self):
        # Tata Nexon EV (40.5 kWh, 0.143 kWh/km)
        # Starting SOC 80% (32.4 kWh)
        # Drive 100 km to station -> Consumes 14.3 kWh -> Arrival energy 18.1 kWh (44.69% SOC)
        # Target SOC 90% (36.45 kWh) -> Energy to charge = 36.45 - 18.1 = 18.35 kWh
        # Charger power 50 kW -> Charging time = 18.35 / 50 * 60 = 22.02 mins
        res = calculate_charging_stop(
            ev_model_name="Tata Nexon EV (Long Range)",
            current_soc_pct=80.0,
            distance_to_station_km=100.0,
            target_soc_pct=90.0,
            charging_power_input="50kW",
        )
        self.assertTrue(res.is_station_reachable)
        self.assertTrue(res.is_charging_valid)
        self.assertEqual(res.battery_capacity_kwh, 40.5)
        self.assertEqual(res.energy_required_to_station_kwh, 14.3)
        self.assertEqual(res.energy_on_arrival_kwh, 18.1)
        self.assertEqual(res.soc_on_arrival_pct, 44.69)
        self.assertEqual(res.charging_power_kw, 50.0)
        self.assertAlmostEqual(res.energy_to_charge_kwh, 18.35, places=2)
        self.assertAlmostEqual(res.charging_time_minutes, 22.02, places=1)

    def test_charging_stop_infeasible(self):
        # Starting SOC 10% (4.05 kWh) -> Station is at 100 km (needs 14.3 kWh)
        res = calculate_charging_stop(
            ev_model_name="Tata Nexon EV (Long Range)",
            current_soc_pct=10.0,
            distance_to_station_km=100.0,
            target_soc_pct=80.0,
            charging_power_input="50kW",
        )
        self.assertFalse(res.is_station_reachable)
        self.assertEqual(res.energy_to_charge_kwh, 0.0)
        self.assertEqual(res.charging_time_minutes, 0.0)
        self.assertGreater(res.deficit_kwh, 0.0)

    def test_charging_stop_invalid_power(self):
        with self.assertRaises(ValueError):
            calculate_charging_stop(
                ev_model_name="Tata Nexon EV (Long Range)",
                current_soc_pct=80.0,
                distance_to_station_km=50.0,
                target_soc_pct=90.0,
                charging_power_input="invalid_power",
            )


if __name__ == "__main__":
    unittest.main()
