"""
Charging Station Schema & Data Inspection Module.
Provides schema normalization, column mapping, and field validation for EV Charging Station data.
Adheres strictly to dynamic inspection without altering raw dataframe columns.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from src.data_loader import load_charging_stations

# ---------------------------------------------------------------------------
# Internal Field Definitions for EV Route & Charging Planning
# ---------------------------------------------------------------------------

# Normalized fields required or utilized during route planning, power calculations,
# and station ranking.
PLANNING_FIELD_REGISTRY: Dict[str, Dict[str, Any]] = {
    "station_id": {
        "label": "Station ID",
        "description": "Unique identifier for the charging station",
        "category": "Core Planning",
        "required_for_routing": True,
        "aliases": ["id", "station_id", "stationid", "uid", "s_id"],
    },
    "station_name": {
        "label": "Station Name",
        "description": "Human-readable station name / branding",
        "category": "Core Planning",
        "required_for_routing": True,
        "aliases": ["name", "station_name", "stationname", "title", "location_name"],
    },
    "latitude": {
        "label": "Latitude",
        "description": "Geographic latitude coordinate in decimal degrees",
        "category": "Core Planning",
        "required_for_routing": True,
        "aliases": ["latitude", "lat", "geo_lat", "latitude_deg"],
    },
    "longitude": {
        "label": "Longitude",
        "description": "Geographic longitude coordinate in decimal degrees",
        "category": "Core Planning",
        "required_for_routing": True,
        "aliases": ["longitude", "lon", "long", "lng", "geo_lon"],
    },
    "station_address": {
        "label": "Address / Location",
        "description": "Street address and physical landmark description",
        "category": "Core Planning",
        "required_for_routing": False,
        "aliases": ["address", "location", "full_address", "street_address"],
    },
    "city": {
        "label": "City / Region",
        "description": "City or municipal area of the station",
        "category": "Location Details",
        "required_for_routing": False,
        "aliases": ["city", "town", "district", "municipality"],
    },
    "postal_code": {
        "label": "Postal Code",
        "description": "PIN or postal code",
        "category": "Location Details",
        "required_for_routing": False,
        "aliases": ["postal_code", "pincode", "zip", "zipcode", "postalcode"],
    },
    "country": {
        "label": "Country",
        "description": "Country of location",
        "category": "Location Details",
        "required_for_routing": False,
        "aliases": ["country", "nation"],
    },
    "charger_type": {
        "label": "Charger / Connector Type",
        "description": "Plug & standard compatibility (e.g. LEV AC, CCS2, Type 2, CHAdeMO)",
        "category": "Charging Specs",
        "required_for_routing": True,
        "aliases": ["charger_type", "connector_type", "plug_type", "gun_type", "connector"],
    },
    "charging_power_spec": {
        "label": "Power Rating (Text)",
        "description": "Raw power rating string (e.g. 3.3kw, 22kW, 50kW, 180kW)",
        "category": "Charging Specs",
        "required_for_routing": True,
        "aliases": ["capacity", "power", "charging_rate", "kw_rating", "power_kw", "rating"],
    },
    "total_chargers": {
        "label": "Total Chargers Count",
        "description": "Total number of physical charger guns / dockets installed",
        "category": "Capacity & Availability",
        "required_for_routing": True,
        "aliases": ["no_of_chargers", "number_of_chargers", "total_chargers", "chargers_count", "capacity_units"],
    },
    "available_chargers": {
        "label": "Available Chargers Count",
        "description": "Number of currently functional / available charger slots",
        "category": "Capacity & Availability",
        "required_for_routing": True,
        "aliases": ["available", "available_chargers", "free_chargers", "open_slots", "available_slots"],
    },
    "network_vendor": {
        "label": "Operator / Network Vendor",
        "description": "Charging Point Operator (CPO) network (e.g. Tata Power, Statiq, ChargeZone)",
        "category": "Operational Info",
        "required_for_routing": False,
        "aliases": ["vendor", "operator", "cpo", "network", "provider", "brand"],
    },
    "charging_mode": {
        "label": "Charging Mode",
        "description": "Charging category (e.g. Charging, Fast Charging, Battery Swap)",
        "category": "Operational Info",
        "required_for_routing": False,
        "aliases": ["charging_type", "charging_mode", "mode", "service_type"],
    },
    "cost_per_unit": {
        "label": "Cost per Unit (INR/kWh)",
        "description": "Electricity tariff or billing rate per kWh / unit",
        "category": "Pricing & Billing",
        "required_for_routing": False,
        "aliases": ["cost_per_unit", "price_per_unit", "tariff_kwh", "cost", "unit_price", "rate_per_kwh"],
    },
    "operating_hours": {
        "label": "Operating Hours / Timing",
        "description": "Opening schedule (e.g. 24x7 or 08:00 - 21:00)",
        "category": "Operational Info",
        "required_for_routing": False,
        "aliases": ["timing", "operating_hours", "schedule", "working_hours"],
    },
    "opening_time": {
        "label": "Opening Time",
        "description": "Daily opening time",
        "category": "Operational Info",
        "required_for_routing": False,
        "aliases": ["open", "opening_time", "start_time"],
    },
    "closing_time": {
        "label": "Closing Time",
        "description": "Daily closing time",
        "category": "Operational Info",
        "required_for_routing": False,
        "aliases": ["close", "closing_time", "end_time"],
    },
    "payment_modes": {
        "label": "Payment Modes",
        "description": "Accepted payment methods (e.g. Cash, E-Wallet, RFID, UPI)",
        "category": "Pricing & Billing",
        "required_for_routing": False,
        "aliases": ["payment_modes", "payment_mode", "payment_methods", "payment"],
    },
    "staffing_status": {
        "label": "Staffing Status",
        "description": "Whether the station is staffed or automated/unstaffed",
        "category": "Operational Info",
        "required_for_routing": False,
        "aliases": ["staff", "staffed", "staffing", "is_staffed"],
    },
    "battery_swap_info": {
        "label": "Battery Swap & Dockets",
        "description": "Battery swapping support and number of swap dockets",
        "category": "Operational Info",
        "required_for_routing": False,
        "aliases": [
            "if_battery_swap_station,_no._of_dockets",
            "if_battery_swap_station",
            "battery_swap",
            "swap_dockets",
            "no_of_dockets",
        ],
    },
    "contact_phone": {
        "label": "Contact Number",
        "description": "Customer support / station helpline phone number",
        "category": "Operational Info",
        "required_for_routing": False,
        "aliases": ["contact_number", "phone", "contact", "helpline", "mobile"],
    },
    "raw_coordinates": {
        "label": "Raw Coordinates String",
        "description": "Compound string/dictionary containing latitude & longitude",
        "category": "Location Details",
        "required_for_routing": False,
        "aliases": ["coordinates", "coord", "lat_lon"],
    },
    "zone": {
        "label": "Zone / Territory",
        "description": "City zone or administrative region (e.g. South Delhi, Central)",
        "category": "Location Details",
        "required_for_routing": False,
        "aliases": ["zone", "region", "area_zone", "territory", "sector"],
    },
}

# Fields that do NOT exist in the static station Excel file and must be computed / provided
# by dynamic ML models and routing algorithms during planning.
DERIVED_PLANNING_FIELDS: Dict[str, Dict[str, str]] = {
    "distance_from_route_km": {
        "label": "Detour Distance (km)",
        "description": "Orthogonal / road detour distance from active highway corridor",
        "source": "Dynamic Route Engine (OSRM / API)",
        "status": "Derived during Route Matching",
    },
    "predicted_waiting_time_min": {
        "label": "Predicted Waiting Time (min)",
        "description": "Estimated queue and waiting duration at arrival time",
        "source": "ML Inference Model (model_input_demo.csv / live model)",
        "status": "Derived from ML Model",
    },
    "charging_time_min": {
        "label": "Charging Duration (min)",
        "description": "Calculated time required to replenish battery to target destination buffer",
        "source": "Energy & Charger Physics Engine",
        "status": "Calculated dynamically",
    },
    "total_journey_time_min": {
        "label": "Total Journey Time (min)",
        "description": "Objective function: Travel Time + Waiting Time + Charging Time",
        "source": "Optimizer Module",
        "status": "Calculated dynamically",
    },
    "amenities": {
        "label": "Nearby Amenities",
        "description": "Food, washrooms, resting lounge indicators",
        "source": "Future Station Enrichment API / Mock Data",
        "status": "To be enriched",
    },
}


# ---------------------------------------------------------------------------
# Schema Inspection Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SchemaInspectionReport:
    """Complete summary of the charging stations dataset schema and mapping validation."""
    is_loaded: bool
    total_records: int = 0
    total_columns: int = 0
    raw_columns: List[str] = field(default_factory=list)
    raw_dtypes: Dict[str, str] = field(default_factory=dict)
    column_mapping: Dict[str, str] = field(default_factory=dict)         # raw_col -> normalized_key
    normalized_to_raw: Dict[str, str] = field(default_factory=dict)       # normalized_key -> raw_col
    mapped_fields_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    missing_planning_fields_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    unmapped_raw_columns: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def total_mapped_fields(self) -> int:
        return len(self.column_mapping)

    @property
    def total_required_mapped(self) -> int:
        return sum(
            1
            for k in self.normalized_to_raw
            if k in PLANNING_FIELD_REGISTRY and PLANNING_FIELD_REGISTRY[k]["required_for_routing"]
        )

    @property
    def total_required_fields(self) -> int:
        return sum(1 for spec in PLANNING_FIELD_REGISTRY.values() if spec["required_for_routing"])


# ---------------------------------------------------------------------------
# Inspection & Schema Matching Core Functions
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Lowercases, strips, and replaces spaces/hyphens with underscores."""
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


def inspect_charging_station_schema(df: Optional[pd.DataFrame] = None) -> SchemaInspectionReport:
    """
    Performs dynamic inspection of the charging stations dataset.
    Loads data via load_charging_stations() if no dataframe is passed.
    Maps raw Excel column names to internal planning schema fields,
    evaluates data types, null counts, and reports missing/derived fields.
    """
    if df is None:
        try:
            df = load_charging_stations()
        except FileNotFoundError as e:
            return SchemaInspectionReport(
                is_loaded=False,
                error_message=str(e),
                missing_planning_fields_table=_build_missing_table_for_unloaded(),
            )
        except Exception as e:
            return SchemaInspectionReport(
                is_loaded=False,
                error_message=f"Error inspecting charging stations: {e}",
                missing_planning_fields_table=_build_missing_table_for_unloaded(),
            )

    raw_columns = list(df.columns)
    raw_dtypes = {col: str(df[col].dtype) for col in raw_columns}
    total_records = len(df)
    total_columns = len(raw_columns)

    # 1. Match Raw Columns to Internal Field Registry
    raw_to_norm: Dict[str, str] = {}
    norm_to_raw: Dict[str, str] = {}
    normalized_raw_cols = {_normalize_name(c): c for c in raw_columns}

    for norm_key, spec in PLANNING_FIELD_REGISTRY.items():
        matched_raw = None
        # Check all aliases for this normalized field
        for alias in spec["aliases"]:
            clean_alias = _normalize_name(alias)
            if clean_alias in normalized_raw_cols:
                matched_raw = normalized_raw_cols[clean_alias]
                break

        if matched_raw:
            norm_to_raw[norm_key] = matched_raw
            raw_to_norm[matched_raw] = norm_key

    # 2. Identify Unmapped Raw Columns
    unmapped_raw_columns = [c for c in raw_columns if c not in raw_to_norm]

    # 3. Build Mapped Fields Table
    mapped_rows = []
    for norm_key, spec in PLANNING_FIELD_REGISTRY.items():
        if norm_key in norm_to_raw:
            source_col = norm_to_raw[norm_key]
            dtype = raw_dtypes.get(source_col, "unknown")
            non_null_count = int(df[source_col].count())
            null_count = int(df[source_col].isnull().sum())
            
            # Sample value representation
            sample_val = "N/A"
            non_null_series = df[source_col].dropna()
            if not non_null_series.empty:
                first_val = str(non_null_series.iloc[0])
                sample_val = (first_val[:28] + "...") if len(first_val) > 28 else first_val

            completeness = round((non_null_count / total_records) * 100, 1) if total_records > 0 else 0.0

            status_badge = "✅ Available"
            if null_count > 0:
                status_badge = f"⚠️ {completeness}% Populated"

            mapped_rows.append({
                "Normalized Field Name": norm_key,
                "Field Label": spec["label"],
                "Source Excel Column": source_col,
                "Detected Data Type": dtype,
                "Category": spec["category"],
                "Required for Planning": "Yes (Core)" if spec["required_for_routing"] else "No (Enrichment)",
                "Sample Value": sample_val,
                "Availability Status": status_badge,
            })

    df_mapped = pd.DataFrame(mapped_rows)

    # 4. Build Missing / Derived Fields Table
    missing_rows = []
    for norm_key, spec in PLANNING_FIELD_REGISTRY.items():
        if norm_key not in norm_to_raw:
            missing_rows.append({
                "Normalized Field Name": norm_key,
                "Field Label": spec["label"],
                "Planning Requirement": "Core Planning (Missing in Excel)" if spec["required_for_routing"] else "Optional Enrichment",
                "Reason / Resolution": "Not present in raw Excel file. May need fallback or manual specification.",
                "Category": spec["category"],
            })

    # Append dynamic derived fields required for full optimization
    for derived_key, d_spec in DERIVED_PLANNING_FIELDS.items():
        missing_rows.append({
            "Normalized Field Name": derived_key,
            "Field Label": d_spec["label"],
            "Planning Requirement": "Dynamic Pipeline Field",
            "Reason / Resolution": f"{d_spec['status']} ({d_spec['source']})",
            "Category": "Derived Computation",
        })

    df_missing = pd.DataFrame(missing_rows)

    return SchemaInspectionReport(
        is_loaded=True,
        total_records=total_records,
        total_columns=total_columns,
        raw_columns=raw_columns,
        raw_dtypes=raw_dtypes,
        column_mapping=raw_to_norm,
        normalized_to_raw=norm_to_raw,
        mapped_fields_table=df_mapped,
        missing_planning_fields_table=df_missing,
        unmapped_raw_columns=unmapped_raw_columns,
        error_message=None,
    )


def _build_missing_table_for_unloaded() -> pd.DataFrame:
    """Builds missing fields overview when the Excel file has not been provided yet."""
    rows = []
    for norm_key, spec in PLANNING_FIELD_REGISTRY.items():
        rows.append({
            "Normalized Field Name": norm_key,
            "Field Label": spec["label"],
            "Planning Requirement": "Required (Core)" if spec["required_for_routing"] else "Optional Enrichment",
            "Reason / Resolution": "Awaiting 'data/charging_stations.xlsx' placement",
            "Category": spec["category"],
        })
    for derived_key, d_spec in DERIVED_PLANNING_FIELDS.items():
        rows.append({
            "Normalized Field Name": derived_key,
            "Field Label": d_spec["label"],
            "Planning Requirement": "Dynamic Pipeline Field",
            "Reason / Resolution": f"{d_spec['status']} ({d_spec['source']})",
            "Category": "Derived Computation",
        })
    return pd.DataFrame(rows)
