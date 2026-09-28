"""
Energy Logic Module for Optimal EV Transportation Planning.
Calculates trip energy requirements, battery states of charge (SOC),
and determines whether charging is required.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Predefined EV Models with realistic battery capacities (kWh) and driving efficiencies (km/kWh)
EV_MODELS: Dict[str, Dict[str, float]] = {
    "Tata Nexon EV (Long Range - 40.5 kWh)": {
        "battery_capacity_kwh": 40.5,
        "ev_efficiency_km_per_kwh": 7.0,
        "segment": "Compact SUV",
    },
    "Tata Punch EV (Empowered+ - 35 kWh)": {
        "battery_capacity_kwh": 35.0,
        "ev_efficiency_km_per_kwh": 7.5,
        "segment": "Micro SUV",
    },
    "Tata Curvv EV (55 kWh)": {
        "battery_capacity_kwh": 55.0,
        "ev_efficiency_km_per_kwh": 7.2,
        "segment": "Coupe SUV",
    },
    "Tata Tiago EV (Long Range - 24 kWh)": {
        "battery_capacity_kwh": 24.0,
        "ev_efficiency_km_per_kwh": 8.0,
        "segment": "Hatchback",
    },
    "Mahindra XUV400 EL Pro (39.4 kWh)": {
        "battery_capacity_kwh": 39.4,
        "ev_efficiency_km_per_kwh": 6.5,
        "segment": "Compact SUV",
    },
    "MG ZS EV (50.3 kWh)": {
        "battery_capacity_kwh": 50.3,
        "ev_efficiency_km_per_kwh": 6.2,
        "segment": "Midsize SUV",
    },
    "MG Windsor EV (38 kWh)": {
        "battery_capacity_kwh": 38.0,
        "ev_efficiency_km_per_kwh": 7.0,
        "segment": "Crossover",
    },
    "Hyundai Ioniq 5 (72.6 kWh)": {
        "battery_capacity_kwh": 72.6,
        "ev_efficiency_km_per_kwh": 6.0,
        "segment": "Premium Crossover",
    },
    "Kia EV6 GT-Line (77.4 kWh)": {
        "battery_capacity_kwh": 77.4,
        "ev_efficiency_km_per_kwh": 6.2,
        "segment": "Premium Crossover",
    },
    "BYD Atto 3 (60.5 kWh)": {
        "battery_capacity_kwh": 60.5,
        "ev_efficiency_km_per_kwh": 6.4,
        "segment": "Midsize SUV",
    },
    "BYD Seal (Premium - 82.5 kWh)": {
        "battery_capacity_kwh": 82.5,
        "ev_efficiency_km_per_kwh": 6.8,
        "segment": "Sedan",
    },
    "Tesla Model 3 (Standard RWD - 60 kWh)": {
        "battery_capacity_kwh": 60.0,
        "ev_efficiency_km_per_kwh": 7.0,
        "segment": "Sedan",
    },
    "Tesla Model Y (Long Range - 75 kWh)": {
        "battery_capacity_kwh": 75.0,
        "ev_efficiency_km_per_kwh": 6.0,
        "segment": "SUV",
    },
    "BMW i4 eDrive40 (83.9 kWh)": {
        "battery_capacity_kwh": 83.9,
        "ev_efficiency_km_per_kwh": 6.5,
        "segment": "Luxury Sedan",
    },
    "Generic EV (60 kWh)": {
        "battery_capacity_kwh": 60.0,
        "ev_efficiency_km_per_kwh": 6.0,
        "segment": "Standard",
    },
}


def get_ev_models() -> List[str]:
    """Returns list of available car models."""
    return list(EV_MODELS.keys())


def get_ev_specs(car_model: str) -> Dict[str, float]:
    """Retrieves specs for a car model, with fallback."""
    return EV_MODELS.get(
        car_model,
        {"battery_capacity_kwh": 60.0, "ev_efficiency_km_per_kwh": 6.0, "segment": "Standard"},
    )


@dataclass
class VehicleSpecs:
    """EV Vehicle Specifications and battery state."""
    battery_capacity_kwh: float
    current_soc_pct: float
    ev_efficiency_km_per_kwh: float
    desired_destination_km: float = 50.0
    desired_destination_soc_pct: Optional[float] = None
    car_model: Optional[str] = None

    def __post_init__(self):
        # Support both desired_destination_km and legacy desired_destination_soc_pct
        if self.desired_destination_soc_pct is not None and self.desired_destination_km == 50.0:
            target_energy = self.battery_capacity_kwh * (self.desired_destination_soc_pct / 100.0)
            self.desired_destination_km = round(target_energy * self.ev_efficiency_km_per_kwh, 1)
        elif self.desired_destination_soc_pct is None:
            target_energy = self.desired_destination_km / self.ev_efficiency_km_per_kwh
            self.desired_destination_soc_pct = round((target_energy / self.battery_capacity_kwh) * 100.0, 1)

    @property
    def current_energy_kwh(self) -> float:
        """Energy currently stored in the battery (kWh)."""
        return self.battery_capacity_kwh * (self.current_soc_pct / 100.0)

    @property
    def desired_destination_energy_kwh(self) -> float:
        """Target energy buffer required upon arrival at destination (kWh)."""
        return self.desired_destination_km / self.ev_efficiency_km_per_kwh

    @property
    def max_range_km(self) -> float:
        """Theoretical maximum range on 100% battery (km)."""
        return self.battery_capacity_kwh * self.ev_efficiency_km_per_kwh

    @property
    def current_range_km(self) -> float:
        """Current estimated driving range (km)."""
        return self.current_energy_kwh * self.ev_efficiency_km_per_kwh


@dataclass
class EnergyTripAnalysis:
    """Direct trip energy analysis result."""
    total_distance_km: float
    energy_required_kwh: float
    initial_energy_kwh: float
    desired_destination_energy_kwh: float
    energy_balance_at_dest_kwh: float
    final_soc_without_charging_pct: float
    charging_required: bool
    explanation: str
    energy_deficit_kwh: float


def calculate_base_energy_required_kwh(distance_km: float, ev_efficiency_km_per_kwh: float) -> float:
    """
    Formula: Base Energy Required (kWh) = Distance (km) / EV Efficiency (km/kWh)
    """
    if ev_efficiency_km_per_kwh <= 0:
        raise ValueError("EV efficiency must be strictly positive.")
    return round(distance_km / ev_efficiency_km_per_kwh, 2)


def calculate_soc_pct(energy_kwh: float, battery_capacity_kwh: float) -> float:
    """
    Formula: SOC (%) = (Energy kWh / Battery Capacity kWh) * 100
    """
    if battery_capacity_kwh <= 0:
        raise ValueError("Battery capacity must be strictly positive.")
    return round((energy_kwh / battery_capacity_kwh) * 100.0, 1)


def is_charging_required(
    initial_energy_kwh: float,
    energy_required_kwh: float,
    desired_destination_energy_kwh: float,
) -> Tuple[bool, float, float]:
    """
    Determines whether the EV requires intermediate charging.
    Returns (charging_required, energy_balance_at_dest, energy_deficit).
    """
    energy_balance_at_dest = round(initial_energy_kwh - energy_required_kwh, 2)
    charging_needed = energy_balance_at_dest < desired_destination_energy_kwh
    energy_deficit = round(max(0.0, desired_destination_energy_kwh - energy_balance_at_dest), 2)
    return charging_needed, energy_balance_at_dest, energy_deficit


def analyze_trip_energy(distance_km: float, vehicle: VehicleSpecs) -> EnergyTripAnalysis:
    """
    Complete analysis of direct trip energy requirements and charging necessity.
    """
    energy_required_kwh = calculate_base_energy_required_kwh(
        distance_km=distance_km,
        ev_efficiency_km_per_kwh=vehicle.ev_efficiency_km_per_kwh,
    )
    initial_energy_kwh = round(vehicle.current_energy_kwh, 2)
    desired_dest_energy_kwh = round(vehicle.desired_destination_energy_kwh, 2)

    charging_needed, energy_balance_at_dest_kwh, energy_deficit_kwh = is_charging_required(
        initial_energy_kwh=initial_energy_kwh,
        energy_required_kwh=energy_required_kwh,
        desired_destination_energy_kwh=desired_dest_energy_kwh,
    )

    final_soc_without_charging_pct = calculate_soc_pct(
        energy_kwh=energy_balance_at_dest_kwh,
        battery_capacity_kwh=vehicle.battery_capacity_kwh,
    )

    final_range_km = max(0.0, round(energy_balance_at_dest_kwh * vehicle.ev_efficiency_km_per_kwh, 1))
    deficit_km = round(energy_deficit_kwh * vehicle.ev_efficiency_km_per_kwh, 1)

    if not charging_needed:
        explanation = (
            f"The vehicle can complete the {distance_km:.0f} km trip directly with ~{final_range_km:.0f} km range ({final_soc_without_charging_pct:.1f}% SOC) remaining, "
            f"comfortably meeting your desired {vehicle.desired_destination_km:.0f} km destination buffer. "
            f"No charging stop is required."
        )
    else:
        if energy_balance_at_dest_kwh < 0:
            deficit_str = (
                f"Battery would deplete {abs(energy_balance_at_dest_kwh):.1f} kWh before destination "
                f"(total deficit to target {vehicle.desired_destination_km:.0f} km buffer: {energy_deficit_kwh:.1f} kWh / ~{deficit_km:.0f} km)."
            )
        else:
            deficit_str = (
                f"Vehicle would arrive with only ~{final_range_km:.0f} km range ({final_soc_without_charging_pct:.1f}% SOC), falling short of your "
                f"{vehicle.desired_destination_km:.0f} km destination buffer by {energy_deficit_kwh:.1f} kWh (~{deficit_km:.0f} km)."
            )

        explanation = (
            f"Charging is required: {deficit_str} An optimal intermediate charging stop is recommended."
        )

    return EnergyTripAnalysis(
        total_distance_km=distance_km,
        energy_required_kwh=energy_required_kwh,
        initial_energy_kwh=initial_energy_kwh,
        desired_destination_energy_kwh=desired_dest_energy_kwh,
        energy_balance_at_dest_kwh=energy_balance_at_dest_kwh,
        final_soc_without_charging_pct=final_soc_without_charging_pct,
        charging_required=charging_needed,
        explanation=explanation,
        energy_deficit_kwh=energy_deficit_kwh,
    )


def calculate_energy_to_station(
    distance_along_route_km: float,
    distance_from_route_km: float,
    ev_efficiency_km_per_kwh: float,
) -> float:
    """
    Calculates energy required to drive from trip origin to the charging station.
    Formula: Total Travel Dist = Dist Along Route + Dist From Route
             Energy = Total Travel Dist / Efficiency
    """
    total_dist = distance_along_route_km + distance_from_route_km
    return calculate_base_energy_required_kwh(total_dist, ev_efficiency_km_per_kwh)
