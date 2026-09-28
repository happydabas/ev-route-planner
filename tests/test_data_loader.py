"""
Test Suite for Data Loader Module.
Validates loading functions, column integrity, and missing file error handling.
"""

import sys
from pathlib import Path
import unittest
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import (
    get_data_summary,
    load_charging_stations,
    load_ev_car_models,
    load_model_input_demo,
)


class TestDataLoader(unittest.TestCase):

    def test_ev_car_models_loaded(self):
        df = load_ev_car_models()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        expected_cols = [
            "manufacturer",
            "model",
            "battery_capacity_kwh",
            "energy_consumption_kwh_per_km",
        ]
        for col in expected_cols:
            self.assertIn(col, df.columns, f"Missing expected column '{col}' in ev_car_models.csv")

    def test_model_input_demo_loaded(self):
        df = load_model_input_demo()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        expected_cols = [
            "hour",
            "weekday",
            "is_weekend",
            "Station_Capacity_EV",
            "Charging_Rate_kW",
            "Time_Spent_Charging_mins",
            "Fleet_Size",
            "occupancy_ratio",
        ]
        for col in expected_cols:
            self.assertIn(col, df.columns, f"Missing expected column '{col}' in model_input_demo.csv")

    def test_charging_stations_missing_handling(self):
        summary = get_data_summary()
        self.assertIn("stations_loaded", summary)
        self.assertIn("models_loaded", summary)
        self.assertTrue(summary["models_loaded"])
        self.assertTrue(summary["ml_demo_loaded"])

    def test_station_schema_inspection(self):
        from src.station_schema import inspect_charging_station_schema, PLANNING_FIELD_REGISTRY

        # 1. Test when Excel file is missing
        report_unloaded = inspect_charging_station_schema(None)
        self.assertFalse(report_unloaded.is_loaded)
        self.assertIsNotNone(report_unloaded.error_message)
        self.assertGreater(len(report_unloaded.missing_planning_fields_table), 0)

        # 2. Test with sample charging stations DataFrame
        sample_data = {
            "address": ["Connaught Place, New Delhi", "Cyber City, Gurugram"],
            "postal_code": [110001, 122002],
            "capacity": ["50kw", "150kw"],
            "city": ["New Delhi", "Gurugram"],
            "close": ["22:00:00", "23:00:00"],
            "cost_per_unit": [18.5, 20.0],
            "country": ["India", "India"],
            "latitude": [28.6315, 28.4950],
            "longitude": [77.2167, 77.0895],
            "open": ["06:00:00", "05:00:00"],
            "payment_modes": ["UPI/RFID", "Credit Card/UPI"],
            "staff": ["Staffed", "Staffed"],
            "available": [3, 6],
            "charger_type": ["CCS2", "CCS2"],
            "id": ["DEL-01", "GUR-01"],
            "vendor": ["Tata Power", "ChargeZone"],
            "charging_type": ["Fast Charging", "DC Fast"],
            "name": ["Tata Power CP Hub", "ChargeZone CyberHub"],
            "no_of_chargers": [4, 8],
        }
        df_sample = pd.DataFrame(sample_data)
        report_sample = inspect_charging_station_schema(df_sample)
        self.assertTrue(report_sample.is_loaded)
        self.assertEqual(report_sample.total_records, 2)
        self.assertEqual(report_sample.total_columns, 19)
        self.assertGreaterEqual(report_sample.total_mapped_fields, 18)
        self.assertIn("station_id", report_sample.normalized_to_raw)
        self.assertIn("latitude", report_sample.normalized_to_raw)
        self.assertIn("longitude", report_sample.normalized_to_raw)
        self.assertIn("charger_type", report_sample.normalized_to_raw)
        self.assertIn("total_chargers", report_sample.normalized_to_raw)


if __name__ == "__main__":
    unittest.main()
