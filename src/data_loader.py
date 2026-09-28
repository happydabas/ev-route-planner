"""
Data Loader Module for Optimal EV Transportation Planning.
Provides robust, cached functions to load:
1. Real Charging Station Excel dataset (data/charging_stations.xlsx)
2. ML Demo Dataset (data/model_input_demo.csv)
3. EV Car Models Dataset (data/ev_car_models.csv)
"""

from pathlib import Path
from typing import Optional, Union
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

EXPECTED_STATION_FIELDS = [
    "address",
    "postal_code",
    "capacity",
    "city",
    "close",
    "cost_per_unit",
    "country",
    "latitude",
    "longitude",
    "open",
    "payment_modes",
    "staff",
    "available",
    "charger_type",
    "if_battery_swap_station",
    "no_of_dockets",
    "id",
    "vendor",
    "charging_type",
    "contact_number",
    "name",
    "coordinates",
    "timing",
    "no_of_chargers",
    "Zone",
]


@st.cache_data(show_spinner="Loading charging station records from Excel...")
def load_charging_stations(file_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """
    Dynamically loads real charging stations from an Excel (.xlsx) file.
    Tolerant of extra whitespace in column names, minor formatting quirks,
    and preserves original dataframe columns.

    Raises:
        FileNotFoundError: If the Excel file is missing, explaining that
                           data/charging_stations.xlsx must be added.
    """
    target_path = Path(file_path) if file_path else (DATA_DIR / "charging_stations.xlsx")

    if not target_path.exists():
        raise FileNotFoundError(
            f"Charging stations dataset not found at '{target_path}'. "
            "Please place your real 'charging_stations.xlsx' file inside the 'data/' directory."
        )

    try:
        # Load Excel with openpyxl engine
        df = pd.read_excel(target_path, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"Error reading Excel file at '{target_path}': {e}")

    # Strip accidental leading/trailing whitespace from column names
    df.columns = [str(col).strip() if isinstance(col, str) else col for col in df.columns]

    return df


@st.cache_data(show_spinner="Loading charging station records...")
def load_available_charging_stations() -> pd.DataFrame:
    """
    Loads available charging stations for UI presentation:
    Checks in order:
    1. data/charging_stations.xlsx
    2. data/charging_stations.csv
    3. data/switch_delhi_charging_stations.csv
    """
    xlsx_path = DATA_DIR / "charging_stations.xlsx"
    csv_path = DATA_DIR / "charging_stations.csv"
    switch_path = DATA_DIR / "switch_delhi_charging_stations.csv"

    if xlsx_path.exists():
        return load_charging_stations(xlsx_path)
    elif csv_path.exists():
        df = pd.read_csv(csv_path)
        df.columns = [str(col).strip() if isinstance(col, str) else col for col in df.columns]
        return df
    elif switch_path.exists():
        df = pd.read_csv(switch_path)
        df.columns = [str(col).strip() if isinstance(col, str) else col for col in df.columns]
        return df
    else:
        raise FileNotFoundError("No charging station dataset found in data/ directory.")


@st.cache_data(show_spinner="Loading ML demo records...")
def load_model_input_demo(file_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """
    Loads mock ML input demo records from CSV.
    Expected fields:
    hour, weekday, is_weekend, Station_Capacity_EV, Charging_Rate_kW,
    Time_Spent_Charging_mins, Fleet_Size, occupancy_ratio
    """
    target_path = Path(file_path) if file_path else (DATA_DIR / "model_input_demo.csv")

    if not target_path.exists():
        raise FileNotFoundError(
            f"ML demo dataset not found at '{target_path}'. "
            "Please ensure 'data/model_input_demo.csv' is present."
        )

    df = pd.read_csv(target_path)
    df.columns = [str(col).strip() if isinstance(col, str) else col for col in df.columns]
    return df


@st.cache_data(show_spinner="Loading EV car models...")
def load_ev_car_models(file_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """
    Loads EV car models dataset from CSV.
    Expected fields:
    manufacturer, model, battery_capacity_kwh, energy_consumption_kwh_per_km
    """
    target_path = Path(file_path) if file_path else (DATA_DIR / "ev_car_models.csv")

    if not target_path.exists():
        raise FileNotFoundError(
            f"EV car models dataset not found at '{target_path}'. "
            "Please ensure 'data/ev_car_models.csv' is present."
        )

    df = pd.read_csv(target_path)
    df.columns = [str(col).strip() if isinstance(col, str) else col for col in df.columns]
    return df


def get_data_summary(data_dir: Path = DATA_DIR) -> dict:
    """
    Helper function to inspect and summarize availability and row counts
    of all project datasets.
    """
    summary = {
        "stations_loaded": False,
        "stations_count": 0,
        "stations_error": None,
        "models_loaded": False,
        "models_count": 0,
        "models_error": None,
        "ml_demo_loaded": False,
        "ml_demo_count": 0,
        "ml_demo_error": None,
    }

    # 1. Charging stations
    try:
        df_stations = load_charging_stations(data_dir / "charging_stations.xlsx")
        summary["stations_loaded"] = True
        summary["stations_count"] = len(df_stations)
    except Exception as e:
        summary["stations_error"] = str(e)

    # 2. EV Models
    try:
        df_models = load_ev_car_models(data_dir / "ev_car_models.csv")
        summary["models_loaded"] = True
        summary["models_count"] = len(df_models)
    except Exception as e:
        summary["models_error"] = str(e)

    # 3. ML Demo
    try:
        df_ml = load_model_input_demo(data_dir / "model_input_demo.csv")
        summary["ml_demo_loaded"] = True
        summary["ml_demo_count"] = len(df_ml)
    except Exception as e:
        summary["ml_demo_error"] = str(e)

    return summary
