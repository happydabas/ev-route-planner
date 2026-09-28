"""
EV Energy & Charging Calculation Engine Module.
Provides deterministic, testable functions for:
1. EV specification lookup from data/ev_car_models.csv
2. Battery energy and consumption calculations
3. Target SOC charging energy requirement
4. Constant-power charging duration calculation
5. Station charging-power string parsing (e.g., '3.3kw', '50 kW', 150)
6. Direct route reachability / energy feasibility analysis
7. Comprehensive intermediate charging-stop computation
8. Robust input validation
"""

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from src.data_loader import load_ev_car_models


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class EVSpecifications:
    """EV Vehicle Technical Specifications."""
    manufacturer: str
    model: str
    battery_capacity_kwh: float
    energy_consumption_kwh_per_km: float

    @property
    def display_name(self) -> str:
        return f"{self.manufacturer} {self.model}"

    @property
    def max_range_km(self) -> float:
        """Theoretical maximum range at 100% SOC in km."""
        if self.energy_consumption_kwh_per_km <= 0:
            return 0.0
        return round(self.battery_capacity_kwh / self.energy_consumption_kwh_per_km, 1)

    @property
    def efficiency_km_per_kwh(self) -> float:
        """Inverse efficiency in km per kWh."""
        if self.energy_consumption_kwh_per_km <= 0:
            return 0.0
        return round(1.0 / self.energy_consumption_kwh_per_km, 2)


@dataclass
class RouteFeasibilityResult:
    """Direct route travel feasibility outcome."""
    distance_km: float
    energy_required_kwh: float
    available_energy_kwh: float
    remaining_energy_kwh: float
    remaining_soc_pct: float
    is_feasible: bool
    deficit_kwh: float


@dataclass
class ChargingStopResult:
    """Complete summary of an EV driving to a charging station and replenishing battery."""
    ev_model_name: str
    manufacturer: str
    battery_capacity_kwh: float
    energy_consumption_kwh_per_km: float
    starting_soc_pct: float
    energy_before_travel_kwh: float
    distance_to_station_km: float
    energy_required_to_station_kwh: float
    energy_on_arrival_kwh: float
    soc_on_arrival_pct: float
    target_soc_pct: float
    energy_to_charge_kwh: float
    charging_power_kw: float
    charging_time_minutes: float
    charging_time_hours: float
    is_station_reachable: bool
    is_charging_valid: bool
    deficit_kwh: float


# ---------------------------------------------------------------------------
# 1. EV Lookup
# ---------------------------------------------------------------------------

def get_available_ev_models(df: Optional[pd.DataFrame] = None) -> List[str]:
    """
    Returns a sorted list of unique EV display names ('Manufacturer Model')
    from data/ev_car_models.csv.
    """
    if df is None:
        df = load_ev_car_models()
    
    names = [
        f"{row['manufacturer']} {row['model']}"
        for _, row in df.iterrows()
    ]
    return sorted(names)


def lookup_ev_specifications(
    model_identifier: str, df: Optional[pd.DataFrame] = None
) -> EVSpecifications:
    """
    Retrieves EV specifications from data/ev_car_models.csv matching either:
    1. Full 'Manufacturer Model' string (e.g., 'Tata Nexon EV (Long Range)')
    2. Model name directly (e.g., 'Nexon EV (Long Range)')

    Raises:
        ValueError: If model_identifier cannot be found.
    """
    if not model_identifier or not str(model_identifier).strip():
        raise ValueError("EV model identifier cannot be empty.")

    if df is None:
        df = load_ev_car_models()

    clean_target = str(model_identifier).strip().lower()

    # Search by combined 'Manufacturer Model' or 'Model'
    for _, row in df.iterrows():
        mfg = str(row["manufacturer"]).strip()
        mdl = str(row["model"]).strip()
        combined = f"{mfg} {mdl}".lower()

        if clean_target in (combined, mdl.lower()):
            cap = float(row["battery_capacity_kwh"])
            cons = float(row["energy_consumption_kwh_per_km"])
            if cap <= 0:
                raise ValueError(f"Invalid battery capacity ({cap} kWh) in dataset for '{mdl}'.")
            if cons <= 0:
                raise ValueError(f"Invalid energy consumption ({cons} kWh/km) in dataset for '{mdl}'.")

            return EVSpecifications(
                manufacturer=mfg,
                model=mdl,
                battery_capacity_kwh=cap,
                energy_consumption_kwh_per_km=cons,
            )

    raise ValueError(
        f"Unknown EV model '{model_identifier}'. Please select a valid vehicle from 'data/ev_car_models.csv'."
    )


# ---------------------------------------------------------------------------
# 2. Battery Energy Calculations
# ---------------------------------------------------------------------------

def calculate_battery_energy_kwh(battery_capacity_kwh: float, soc_pct: float) -> float:
    """
    Formula: Energy (kWh) = Battery Capacity (kWh) * (SOC / 100)
    """
    if battery_capacity_kwh <= 0:
        raise ValueError(f"Battery capacity must be strictly positive, got {battery_capacity_kwh}.")
    if not (0.0 <= soc_pct <= 100.0):
        raise ValueError(f"SOC must be between 0 and 100%, got {soc_pct}.")

    return round(battery_capacity_kwh * (soc_pct / 100.0), 3)


def calculate_energy_consumed_kwh(
    distance_km: float, energy_consumption_kwh_per_km: float
) -> float:
    """
    Formula: Energy Consumed (kWh) = Distance (km) * Energy Consumption (kWh/km)
    """
    if distance_km < 0:
        raise ValueError(f"Distance cannot be negative, got {distance_km} km.")
    if energy_consumption_kwh_per_km <= 0:
        raise ValueError(
            f"Energy consumption rate must be strictly positive, got {energy_consumption_kwh_per_km} kWh/km."
        )

    return round(distance_km * energy_consumption_kwh_per_km, 3)


def calculate_soc_from_energy(energy_kwh: float, battery_capacity_kwh: float) -> float:
    """
    Formula: SOC (%) = (Energy kWh / Battery Capacity kWh) * 100
    Clamped to 0.0% - 100.0% for physical consistency.
    """
    if battery_capacity_kwh <= 0:
        raise ValueError(f"Battery capacity must be strictly positive, got {battery_capacity_kwh}.")

    raw_soc = (energy_kwh / battery_capacity_kwh) * 100.0
    return round(raw_soc, 2)


def calculate_remaining_energy_and_soc(
    battery_capacity_kwh: float,
    current_soc_pct: float,
    distance_km: float,
    energy_consumption_kwh_per_km: float,
) -> Tuple[float, float]:
    """
    Calculates remaining battery energy and SOC after traveling distance_km.
    Returns: (remaining_energy_kwh, remaining_soc_pct)
    Note: Energy and SOC can be negative if travel distance exceeds stored energy.
    """
    initial_energy = calculate_battery_energy_kwh(battery_capacity_kwh, current_soc_pct)
    consumed_energy = calculate_energy_consumed_kwh(distance_km, energy_consumption_kwh_per_km)
    remaining_energy = round(initial_energy - consumed_energy, 3)
    remaining_soc = calculate_soc_from_energy(remaining_energy, battery_capacity_kwh)

    return remaining_energy, remaining_soc


# ---------------------------------------------------------------------------
# 3. Charging Requirement
# ---------------------------------------------------------------------------

def calculate_charging_energy_required(
    battery_capacity_kwh: float, current_soc_pct: float, target_soc_pct: float
) -> Tuple[float, float]:
    """
    Determines how much energy (kWh) and SOC increase (%) are needed to reach target SOC.

    Validations:
        - 0 <= current_soc_pct <= 100
        - 0 <= target_soc_pct <= 100
        - target_soc_pct >= current_soc_pct
        - battery_capacity_kwh > 0

    Returns:
        (energy_required_kwh, soc_increase_pct)
    """
    if battery_capacity_kwh <= 0:
        raise ValueError(f"Battery capacity must be strictly positive, got {battery_capacity_kwh}.")
    if not (0.0 <= current_soc_pct <= 100.0):
        raise ValueError(f"Current SOC must be between 0 and 100%, got {current_soc_pct}.")
    if not (0.0 <= target_soc_pct <= 100.0):
        raise ValueError(f"Target SOC must be between 0 and 100%, got {target_soc_pct}.")
    if target_soc_pct < current_soc_pct:
        raise ValueError(
            f"Target SOC ({target_soc_pct}%) cannot be less than current SOC ({current_soc_pct}%)."
        )

    soc_increase_pct = round(target_soc_pct - current_soc_pct, 2)
    energy_required_kwh = round(battery_capacity_kwh * (soc_increase_pct / 100.0), 3)

    return energy_required_kwh, soc_increase_pct


# ---------------------------------------------------------------------------
# 4. Charging Time
# ---------------------------------------------------------------------------

def calculate_charging_time_minutes(
    energy_required_kwh: float, charging_power_kw: float
) -> float:
    """
    Estimates charging duration under constant power:
    Formula: Charging Time (hours) = Energy (kWh) / Power (kW)
             Charging Time (minutes) = Time (hours) * 60

    Returns:
        charging_time_minutes (float, rounded to 2 decimal places)
    """
    if energy_required_kwh < 0:
        raise ValueError(f"Energy required cannot be negative, got {energy_required_kwh} kWh.")
    if charging_power_kw <= 0:
        raise ValueError(f"Charging power must be strictly positive, got {charging_power_kw} kW.")

    if energy_required_kwh == 0:
        return 0.0

    time_hours = energy_required_kwh / charging_power_kw
    time_minutes = time_hours * 60.0
    return round(time_minutes, 2)


# ---------------------------------------------------------------------------
# 5. Station Charging-Power Parsing
# ---------------------------------------------------------------------------

def parse_charging_power_kw(power_spec: Any) -> Optional[float]:
    """
    Extracts numeric charging power in kW from varied raw strings or numbers.
    Examples:
        '3.3kw'   -> 3.3
        '50kW'    -> 50.0
        '50 kW'   -> 50.0
        '150 KW'  -> 150.0
        '22.5'    -> 22.5
        50        -> 50.0
        50.0      -> 50.0
        None / '' -> None
        'nil'     -> None

    Returns:
        float power in kW if valid and > 0, else None.
    """
    if power_spec is None:
        return None

    # Handle direct numeric input
    if isinstance(power_spec, (int, float)):
        val = float(power_spec)
        return val if (val > 0 and not pd.isna(val)) else None

    # Convert string to lowercase stripped
    str_val = str(power_spec).strip().lower()
    if not str_val or str_val in ("nil", "null", "nan", "none", "unknown"):
        return None

    # Extract digits with optional decimal point followed by optional 'kw'
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kw|kwh)?", str_val)
    if match:
        try:
            num = float(match.group(1))
            return num if num > 0 else None
        except ValueError:
            return None

    return None


# ---------------------------------------------------------------------------
# 6. Route Feasibility
# ---------------------------------------------------------------------------

def calculate_route_feasibility(
    battery_capacity_kwh: float,
    energy_consumption_kwh_per_km: float,
    current_soc_pct: float,
    distance_km: float,
) -> RouteFeasibilityResult:
    """
    Determines whether an EV can complete a direct travel distance without charging.
    """
    available_energy = calculate_battery_energy_kwh(battery_capacity_kwh, current_soc_pct)
    energy_required = calculate_energy_consumed_kwh(distance_km, energy_consumption_kwh_per_km)

    remaining_energy = round(available_energy - energy_required, 3)
    remaining_soc = calculate_soc_from_energy(remaining_energy, battery_capacity_kwh)

    is_feasible = remaining_energy >= 0.0
    deficit_kwh = round(max(0.0, energy_required - available_energy), 3)

    return RouteFeasibilityResult(
        distance_km=distance_km,
        energy_required_kwh=energy_required,
        available_energy_kwh=available_energy,
        remaining_energy_kwh=remaining_energy,
        remaining_soc_pct=remaining_soc,
        is_feasible=is_feasible,
        deficit_kwh=deficit_kwh,
    )


# ---------------------------------------------------------------------------
# 7. Intermediate Charging-Stop Calculation
# ---------------------------------------------------------------------------

def calculate_charging_stop(
    ev_model_name: str,
    current_soc_pct: float,
    distance_to_station_km: float,
    target_soc_pct: float,
    charging_power_input: Any,
    ev_df: Optional[pd.DataFrame] = None,
) -> ChargingStopResult:
    """
    Comprehensive intermediate charging stop computation:
    1. Looks up EV specifications
    2. Checks reachability to the candidate charging station
    3. Calculates SOC & energy on arrival at station
    4. Parses station charging power
    5. Calculates energy to charge from arrival SOC to target SOC
    6. Computes charging duration in minutes and hours
    """
    # 1. Lookup EV
    ev = lookup_ev_specifications(ev_model_name, df=ev_df)

    # 2. Parse charging power
    power_kw = parse_charging_power_kw(charging_power_input)
    if power_kw is None or power_kw <= 0:
        raise ValueError(
            f"Invalid charging power '{charging_power_input}'. Must be parseable to a positive kW value."
        )

    # 3. Energy before travel
    energy_before = calculate_battery_energy_kwh(ev.battery_capacity_kwh, current_soc_pct)
    energy_to_station = calculate_energy_consumed_kwh(
        distance_to_station_km, ev.energy_consumption_kwh_per_km
    )

    energy_on_arrival = round(energy_before - energy_to_station, 3)
    soc_on_arrival = calculate_soc_from_energy(energy_on_arrival, ev.battery_capacity_kwh)

    is_reachable = energy_on_arrival >= 0.0
    deficit = round(max(0.0, energy_to_station - energy_before), 3)

    # 4. Energy to charge to target SOC
    if is_reachable:
        clamped_arrival_soc = max(0.0, min(100.0, soc_on_arrival))
        if target_soc_pct < clamped_arrival_soc:
            # Vehicle already arrived with more than target SOC
            energy_to_charge = 0.0
            charge_time_mins = 0.0
            is_charge_valid = True
        else:
            energy_to_charge, _ = calculate_charging_energy_required(
                battery_capacity_kwh=ev.battery_capacity_kwh,
                current_soc_pct=clamped_arrival_soc,
                target_soc_pct=target_soc_pct,
            )
            charge_time_mins = calculate_charging_time_minutes(energy_to_charge, power_kw)
            is_charge_valid = True
    else:
        # Station unreachable with starting SOC
        energy_to_charge = 0.0
        charge_time_mins = 0.0
        is_charge_valid = False

    charge_time_hours = round(charge_time_mins / 60.0, 3)

    return ChargingStopResult(
        ev_model_name=ev.model,
        manufacturer=ev.manufacturer,
        battery_capacity_kwh=ev.battery_capacity_kwh,
        energy_consumption_kwh_per_km=ev.energy_consumption_kwh_per_km,
        starting_soc_pct=current_soc_pct,
        energy_before_travel_kwh=energy_before,
        distance_to_station_km=distance_to_station_km,
        energy_required_to_station_kwh=energy_to_station,
        energy_on_arrival_kwh=energy_on_arrival,
        soc_on_arrival_pct=soc_on_arrival,
        target_soc_pct=target_soc_pct,
        energy_to_charge_kwh=energy_to_charge,
        charging_power_kw=power_kw,
        charging_time_minutes=charge_time_mins,
        charging_time_hours=charge_time_hours,
        is_station_reachable=is_reachable,
        is_charging_valid=is_charge_valid,
        deficit_kwh=deficit,
    )
