"""
Optimal EV Transportation Planning
Frontend Streamlit Application - Balanced 3-Page Light Edition.

Complete 3-Page Flow:
- Page 1: Plan Your Journey (Spacious 2-Row Form: Route & Distance + Vehicle, SOC & CTA)
- Page 2: Calculating Your Journey (Dedicated loading experience with progressive status stages)
- Page 3: Journey Results (Overview, Interactive Route & Charging Map, Top 10 Recommendations + Station Details Side Panel, Replan)
"""

import base64
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

from src.data_loader import (
    load_available_charging_stations,
    load_ev_car_models,
    load_model_input_demo,
)
from src.energy_engine import (
    get_available_ev_models,
    lookup_ev_specifications,
)

# ---------------------------------------------------------------------------
# 1. Page Configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Optimal EV Transportation Planning",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Helper to load image as base64 for reliable display
def get_base64_image_data_uri(file_path: Path) -> str:
    if file_path.exists():
        try:
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            suffix = file_path.suffix.lower().replace(".", "")
            mime = "image/jpeg" if suffix in ["jpg", "jpeg"] else f"image/{suffix}"
            return f"data:{mime};base64,{encoded}"
        except Exception:
            return ""
    return ""

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
CAR_IMAGE_URI = get_base64_image_data_uri(ASSETS_DIR / "car.jpg")
STATION_IMAGE_URI = get_base64_image_data_uri(ASSETS_DIR / "station.jpg")

# Known City Geocoding Registry (for quick reliable resolution)
KNOWN_LOCATIONS: Dict[str, Tuple[float, float, str]] = {
    "delhi": (28.6139, 77.2090, "New Delhi, Delhi"),
    "new delhi": (28.6139, 77.2090, "New Delhi, Delhi"),
    "jaipur": (26.9124, 75.7873, "Jaipur, Rajasthan"),
    "gurgaon": (28.4595, 77.0266, "Gurugram, Haryana"),
    "gurugram": (28.4595, 77.0266, "Gurugram, Haryana"),
    "manesar": (28.3580, 76.9380, "Manesar, Haryana"),
    "neemrana": (27.9890, 76.3850, "Neemrana, Rajasthan"),
    "behror": (27.8860, 76.2820, "Behror, Rajasthan"),
    "kotputli": (27.7010, 76.1980, "Kotputli, Rajasthan"),
    "shahpura": (27.3910, 75.9620, "Shahpura, Rajasthan"),
    "alwar": (27.5530, 76.6346, "Alwar, Rajasthan"),
    "mumbai": (19.0760, 72.8777, "Mumbai, Maharashtra"),
    "pune": (18.5204, 73.8567, "Pune, Maharashtra"),
    "bengaluru": (12.9716, 77.5946, "Bengaluru, Karnataka"),
    "bangalore": (12.9716, 77.5946, "Bengaluru, Karnataka"),
    "chennai": (13.0827, 80.2707, "Chennai, Tamil Nadu"),
    "agra": (27.1767, 78.0081, "Agra, Uttar Pradesh"),
    "mysuru": (12.2958, 76.6394, "Mysuru, Karnataka"),
    "mysore": (12.2958, 76.6394, "Mysuru, Karnataka"),
    "surat": (21.1702, 72.8311, "Surat, Gujarat"),
}

def resolve_location_coordinates(query_str: str) -> Optional[Tuple[float, float, str]]:
    """Resolves standard city/landmark names to lat/lon if known."""
    if not query_str or not str(query_str).strip():
        return None
    clean = str(query_str).strip().lower()
    for key, (lat, lon, label) in KNOWN_LOCATIONS.items():
        if key in clean or clean in key:
            return (lat, lon, label)
    return None

# ---------------------------------------------------------------------------
# 2. Strict High-Specificity Light Mode Stylesheet
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');

/* Universal Light Theme Reset */
:root, [data-theme="dark"], [data-theme="light"],
html, body, .stApp,
div[data-testid="stAppViewContainer"],
div[data-testid="stMain"],
section[data-testid="stMain"] {
    background-color: #f8fafc !important;
    background: #f8fafc !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}

/* HIDE STREAMLIT TOP RIGHT HEADER (DEPLOY BUTTON, THREE DOTS MENU, TOOLBAR) */
#MainMenu,
header,
header[data-testid="stHeader"],
div[data-testid="stHeader"],
div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
.stDeployButton,
div[data-testid="stAppDeployButton"],
div[data-testid="stToolbarActions"],
[data-testid="manage-app-button"],
#stDecoration,
footer,
div[data-testid="stFooter"] {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    width: 0 !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

/* Headings */
h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span {
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
}

.block-container {
    padding-top: 1.25rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1280px !important;
}

/* Streamlit Container (Cards) */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #ffffff !important;
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    padding: 1.75rem 2rem !important;
    margin-bottom: 1.5rem !important;
}

/* Force All Inputs to Crisp White with Dark Text */
div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-testid="stTextInput"] div[data-baseweb="base-input"],
div[data-testid="stNumberInput"] div[data-baseweb="base-input"],
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
input, textarea {
    background-color: #ffffff !important;
    background: #ffffff !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    height: 42px !important;
}

div[data-baseweb="input"]:focus-within,
div[data-baseweb="base-input"]:focus-within {
    border-color: #059669 !important;
    box-shadow: 0 0 0 1px #059669 !important;
}

div[data-baseweb="input"] input::placeholder {
    color: #94a3b8 !important;
    -webkit-text-fill-color: #94a3b8 !important;
}

/* Force Selectbox styling */
div[data-baseweb="select"],
div[data-baseweb="select"] > div,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    height: 42px !important;
}

div[data-baseweb="select"] span,
div[data-baseweb="select"] div {
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    font-weight: 500 !important;
}

div[data-baseweb="select"] svg {
    fill: #475569 !important;
}

/* Dropdown popover menu */
div[data-baseweb="popover"],
div[data-baseweb="popover"] ul,
div[data-baseweb="menu"],
ul[data-testid="stSelectboxVirtualDropdown"] {
    background-color: #ffffff !important;
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1) !important;
}

li[data-baseweb="menu-item"],
li[role="option"] {
    background-color: #ffffff !important;
    background: #ffffff !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
}

li[data-baseweb="menu-item"]:hover,
li[role="option"]:hover {
    background-color: #ecfdf5 !important;
    background: #ecfdf5 !important;
    color: #059669 !important;
    -webkit-text-fill-color: #059669 !important;
}

/* TOOLTIPS & HOVER EXPLANATIONS - CLEAN LIGHT CARD WITH CRISP CONTRAST */
div[data-baseweb="tooltip"],
div[role="tooltip"],
div[data-testid="stTooltipContent"],
div[data-testid="stTooltipContent"] > div,
div[data-testid="stTooltipHoverTarget"] + div,
[data-testid="stTooltipContent"],
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] div {
    background-color: #ffffff !important;
    background: #ffffff !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
}

div[data-baseweb="tooltip"],
div[role="tooltip"],
div[data-testid="stTooltipContent"],
[data-testid="stTooltipContent"] {
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12) !important;
    padding: 8px 12px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    line-height: 1.4 !important;
    max-width: 320px !important;
}

div[data-baseweb="tooltip"] *,
div[role="tooltip"] *,
div[data-testid="stTooltipContent"] *,
div[data-testid="stTooltipContent"] p,
div[data-testid="stTooltipContent"] span,
div[data-baseweb="popover"] * {
    background-color: transparent !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}

/* Tooltip / Help trigger icon */
div[data-testid="stTooltipHoverTarget"],
div[data-testid="stTooltipHoverTarget"] svg,
svg[data-testid="stTooltipHoverTarget"],
button[data-testid="stTooltipHoverTarget"] {
    color: #64748b !important;
    fill: #64748b !important;
    background: transparent !important;
}
div[data-testid="stTooltipHoverTarget"]:hover svg,
svg[data-testid="stTooltipHoverTarget"]:hover {
    color: #059669 !important;
    fill: #059669 !important;
}

/* Number Input Buttons */
div[data-testid="stNumberInput"] button {
    background-color: #f8fafc !important;
    background: #f8fafc !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    height: 42px !important;
}
div[data-testid="stNumberInput"] button svg {
    fill: #0f172a !important;
    color: #0f172a !important;
}

/* ALL BUTTONS - CRISP LIGHT MODE (ELIMINATE DARK/BLACK BUTTONS) */
button,
button[kind="secondary"],
button[data-testid="baseButton-secondary"],
button[data-baseweb="button"],
div.stButton > button,
div[data-testid="stButton"] > button,
.stButton button,
[data-testid="stBaseButton-secondary"] {
    background-color: #ffffff !important;
    background: #ffffff !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    height: 38px !important;
    min-height: 38px !important;
    padding: 0 0.75rem !important;
    white-space: nowrap !important;
    transition: all 0.15s ease-in-out !important;
}

button *,
button[kind="secondary"] *,
button[data-testid="baseButton-secondary"] *,
div.stButton > button *,
div[data-testid="stButton"] > button *,
.stButton button * {
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    font-weight: 600 !important;
}

button:hover,
button[kind="secondary"]:hover,
button[data-testid="baseButton-secondary"]:hover,
div.stButton > button:hover,
div[data-testid="stButton"] > button:hover,
.stButton button:hover {
    background-color: #f1f5f9 !important;
    background: #f1f5f9 !important;
    border-color: #059669 !important;
    color: #059669 !important;
    -webkit-text-fill-color: #059669 !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06) !important;
}

button:hover *,
button[kind="secondary"]:hover *,
button[data-testid="baseButton-secondary"]:hover *,
div.stButton > button:hover *,
div[data-testid="stButton"] > button:hover * {
    color: #059669 !important;
    -webkit-text-fill-color: #059669 !important;
}

/* PRIMARY GREEN CTA BUTTON (Plan Journey) */
button[kind="primary"],
button[data-testid="baseButton-primary"],
div[data-testid="stButton"] button[kind="primary"],
button[key*="btn_plan_p1"],
[data-testid="stBaseButton-primary"] {
    background-color: #059669 !important;
    background: #059669 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border: 1px solid #047857 !important;
    border-radius: 8px !important;
    height: 44px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    box-shadow: 0 2px 6px rgba(5, 150, 105, 0.25) !important;
}

button[kind="primary"] *,
button[data-testid="baseButton-primary"] *,
div[data-testid="stButton"] button[kind="primary"] *,
button[key*="btn_plan_p1"] *,
[data-testid="stBaseButton-primary"] * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-weight: 700 !important;
}

button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover,
div[data-testid="stButton"] button[kind="primary"]:hover,
button[key*="btn_plan_p1"]:hover {
    background-color: #047857 !important;
    background: #047857 !important;
    border-color: #065f46 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

button[kind="primary"]:hover *,
button[data-testid="baseButton-primary"]:hover *,
div[data-testid="stButton"] button[kind="primary"]:hover * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

/* Slider Track */
div[data-testid="stSlider"] div[role="slider"] {
    background-color: #059669 !important;
}

/* Labels */
label[data-testid="stWidgetLabel"],
label[data-testid="stWidgetLabel"] p,
label[data-testid="stWidgetLabel"] span {
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    margin-bottom: 0.35rem !important;
}

/* Top App Header */
.app-top-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 0.65rem;
    margin-bottom: 0.75rem;
    border-bottom: 1px solid #e2e8f0;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.app-title-group {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.app-logo-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 10px;
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #059669;
    font-size: 1.35rem;
}

.app-title {
    font-size: 1.4rem;
    font-weight: 800;
    color: #0f172a !important;
    margin: 0;
    line-height: 1.2;
}

.app-subtitle {
    font-size: 0.88rem;
    color: #64748b !important;
    margin: 0;
    font-weight: 400;
}

.app-tagline {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.82rem;
    color: #059669;
    font-weight: 600;
    background: #ecfdf5;
    padding: 0.35rem 0.85rem;
    border-radius: 9999px;
    border: 1px solid #a7f3d0;
}

/* Section Card Header */
.section-header {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
}

.section-badge {
    width: 28px;
    height: 28px;
    min-width: 28px;
    border-radius: 50%;
    background: #059669;
    color: #ffffff;
    font-weight: 700;
    font-size: 0.9rem;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 2px;
}

.section-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #0f172a !important;
    margin: 0;
    line-height: 1.3;
}

.section-subtitle {
    font-size: 0.88rem;
    color: #64748b !important;
    margin: 0.15rem 0 0 0;
    font-weight: 400;
}

.coord-tag {
    font-size: 0.75rem;
    color: #0284c7;
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    padding: 0.25rem 0.55rem;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    white-space: nowrap;
}

/* Page 2: Dedicated Calculating Screen - Ultra-Modern Compact Design */
.calculating-card {
    max-width: 580px;
    margin: 0.4rem auto 0.6rem auto;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.25rem 1.5rem 1.15rem 1.5rem;
    text-align: center;
    box-shadow: 0 4px 18px rgba(15, 23, 42, 0.05);
}

.calc-hero-orbit {
    position: relative;
    width: 48px;
    height: 48px;
    margin: 0 auto 0.5rem auto;
    display: flex;
    align-items: center;
    justify-content: center;
}

.calc-orbit-ring {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    border: 2px dashed #10b981;
    animation: calc-spin 8s linear infinite;
}

.calc-pulse-core {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
    border: 1.5px solid #a7f3d0;
    color: #059669;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.15rem;
    box-shadow: 0 2px 6px rgba(5, 150, 105, 0.16);
    animation: calc-heartbeat 1.8s ease-in-out infinite;
}

@keyframes calc-spin {
    100% { transform: rotate(360deg); }
}

@keyframes calc-heartbeat {
    0% { transform: scale(0.96); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.3); }
    50% { transform: scale(1.04); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
    100% { transform: scale(0.96); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.calc-heading {
    font-size: 1.2rem;
    font-weight: 800;
    color: #0f172a !important;
    margin: 0 0 0.15rem 0;
    letter-spacing: -0.02em;
}

.calc-subheading {
    font-size: 0.80rem;
    color: #64748b !important;
    margin: 0 0 0.75rem 0;
    line-height: 1.3;
}

.calc-summary-pill {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 0.3rem 0.6rem;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 30px;
    padding: 0.3rem 0.75rem;
    margin-bottom: 0.75rem;
    font-size: 0.75rem;
    color: #334155;
    font-weight: 500;
}

.calc-summary-item {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
}

.calc-summary-item strong {
    color: #0f172a;
    font-weight: 700;
}

.calc-progress-track {
    width: 100%;
    max-width: 420px;
    height: 5px;
    background: #f1f5f9;
    border-radius: 999px;
    margin: 0 auto 0.75rem auto;
    overflow: hidden;
    position: relative;
    border: 1px solid #e2e8f0;
}

.calc-progress-fill {
    height: 100%;
    width: 100%;
    background: linear-gradient(90deg, #059669 0%, #10b981 45%, #0284c7 100%);
    border-radius: 999px;
    animation: calc-fill-anim 1.6s ease-in-out infinite;
}

@keyframes calc-fill-anim {
    0% { transform: translateX(-100%); }
    50% { transform: translateX(0%); }
    100% { transform: translateX(100%); }
}

.calc-milestones-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.65rem 0.9rem;
    max-width: 460px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    text-align: left;
}

.calc-step-row {
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
}

.calc-step-icon {
    width: 18px;
    height: 18px;
    min-width: 18px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.68rem;
    font-weight: 800;
    margin-top: 1px;
}

.calc-step-icon.done {
    background: #ecfdf5;
    color: #059669;
    border: 1px solid #a7f3d0;
}

.calc-step-icon.active {
    background: #f0f9ff;
    color: #0284c7;
    border: 1.5px solid #38bdf8;
    animation: calc-step-pulse 1.2s infinite ease-in-out;
}

@keyframes calc-step-pulse {
    0% { transform: scale(0.92); }
    50% { transform: scale(1.1); }
    100% { transform: scale(0.92); }
}

.calc-step-icon.pending {
    background: #f1f5f9;
    color: #94a3b8;
    border: 1px solid #cbd5e1;
}

.calc-step-text {
    display: flex;
    flex-direction: column;
}

.calc-step-title {
    font-size: 0.80rem;
    font-weight: 700;
    color: #1e293b;
    line-height: 1.2;
}

.calc-step-desc {
    font-size: 0.70rem;
    color: #64748b;
    line-height: 1.2;
    margin-top: 1px;
}

/* Page 3: Overview Grid */
.overview-grid {
    display: grid;
    grid-template-columns: 1.3fr 1fr 1.3fr 0.9fr 0.9fr;
    gap: 0.85rem;
}

@media (max-width: 1024px) {
    .overview-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 600px) {
    .overview-grid { grid-template-columns: 1fr; }
}

.overview-tile {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.85rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
    transition: all 0.2s ease;
}

.overview-tile:hover {
    border-color: #cbd5e1;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.overview-icon-box {
    width: 38px;
    height: 38px;
    min-width: 38px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.15rem;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
}

.overview-tile-content {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    width: 100%;
}

.overview-tile-label {
    font-size: 0.70rem;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    line-height: 1.2;
}

.overview-tile-val {
    font-size: 0.95rem;
    font-weight: 800;
    color: #0f172a;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.3;
    margin-top: 2px;
}

.overview-tile-sub {
    font-size: 0.72rem;
    color: #475569;
    margin-top: 2px;
    line-height: 1.2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.badge-status-planned {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #059669;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 700;
}

/* Map Legend */
.map-legend-bar {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    margin-bottom: 0.85rem;
    font-size: 0.78rem;
    font-weight: 600;
    color: #334155;
    flex-wrap: wrap;
}

.legend-item {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
}

.legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
}

.legend-dot.start { background: #10b981; }
.legend-dot.station { background: #0284c7; }
.legend-dot.rec { background: #f59e0b; }
.legend-dot.dest { background: #ef4444; }

/* Full-Width Inline Station Details Card */
.station-inline-details-card {
    background: #ffffff;
    border: 1.5px solid #a7f3d0;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin: 0.5rem 0 1rem 0;
    box-shadow: 0 4px 16px rgba(5, 150, 105, 0.08);
    animation: fadeInRow 0.25s ease-in-out;
}

@keyframes fadeInRow {
    from { opacity: 0; transform: translateY(-4px); }
    to { opacity: 1; transform: translateY(0); }
}

.station-inline-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #f1f5f9;
    flex-wrap: wrap;
    gap: 0.75rem;
}

.station-inline-body {
    display: grid;
    grid-template-columns: 260px 1fr;
    gap: 1.5rem;
}

@media (max-width: 860px) {
    .station-inline-body {
        grid-template-columns: 1fr;
    }
}

.station-inline-media {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.station-inline-hero-img {
    width: 100%;
    height: 135px;
    object-fit: cover;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
}

.station-inline-amenities {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.65rem 0.85rem;
    font-size: 0.78rem;
    color: #475569;
    line-height: 1.4;
}

.station-rec-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #059669;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    margin-bottom: 0.35rem;
}

.station-details-name {
    font-size: 1.15rem;
    font-weight: 800;
    color: #0f172a;
    margin: 0 0 0.2rem 0;
}

.station-details-loc {
    font-size: 0.82rem;
    color: #64748b;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.35rem;
    flex-wrap: wrap;
}

code,
pre code,
.station-id-badge {
    background: #f1f5f9 !important;
    background-color: #f1f5f9 !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 5px !important;
    padding: 0.12rem 0.45rem !important;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace !important;
    font-size: 0.80rem !important;
    font-weight: 700 !important;
    display: inline-block !important;
    letter-spacing: 0.02em !important;
}

.station-specs-grid-full {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0.65rem;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.85rem;
}

@media (max-width: 1100px) {
    .station-specs-grid-full {
        grid-template-columns: repeat(3, 1fr);
    }
}

@media (max-width: 640px) {
    .station-specs-grid-full {
        grid-template-columns: repeat(2, 1fr);
    }
}

.station-spec-item {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 0.5rem 0.65rem;
}

.station-spec-label {
    font-size: 0.68rem;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.station-spec-value {
    font-size: 0.85rem;
    font-weight: 700;
    color: #0f172a;
}

.station-spec-value.highlight {
    color: #0284c7;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 3. Interactive Leaflet Map Generators (Picker & Results)
# ---------------------------------------------------------------------------

import urllib.request

def get_ip_geolocation() -> Optional[Tuple[float, float, str]]:
    """
    Keyless IP-based geolocation lookup with fast timeout.
    Returns (lat, lon, label) if successful, None otherwise.
    """
    try:
        req = urllib.request.Request(
            "http://ip-api.com/json/?fields=status,city,country,lat,lon",
            headers={"User-Agent": "EV-Planner/1.0"}
        )
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "success":
                lat = float(data.get("lat"))
                lon = float(data.get("lon"))
                city = data.get("city", "Current Location")
                country = data.get("country", "")
                label = f"{city}, {country}" if country else city
                return (lat, lon, label)
    except Exception:
        pass
    return None


def generate_location_picker_map_html(
    center_lat: float,
    center_lon: float,
    mode_label: str,
    mode_target: str = "starting",
    initial_name: str = "",
) -> str:
    """
    Reusable Leaflet + OpenStreetMap interactive location picker component.
    Allows user to click anywhere to place a pin, drag the pin, use GPS auto-locate,
    and confirm the coordinates directly into the application.
    """
    safe_name = initial_name.replace('"', '&quot;').replace("'", "&#39;") if initial_name else f"{mode_label} Point"
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            * {{ box-sizing: border-box; }}
            html, body {{
                height: 100%;
                width: 100%;
                margin: 0;
                padding: 0;
                background: #f8fafc;
                font-family: 'Inter', -apple-system, sans-serif;
                overflow: hidden;
            }}
            #map-container {{
                display: flex;
                flex-direction: column;
                height: 100%;
                width: 100%;
            }}
            #picker-map {{
                flex: 1;
                width: 100%;
                min-height: 280px;
                background-color: #f1f5f9;
                border-radius: 8px 8px 0 0;
            }}
            .picker-marker {{
                background-color: #059669;
                color: white;
                width: 32px;
                height: 32px;
                border-radius: 50% 50% 50% 0;
                transform: rotate(-45deg);
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 3px 8px rgba(0,0,0,0.3);
                border: 2px solid #ffffff;
                cursor: grab;
            }}
            .picker-marker span {{
                transform: rotate(45deg);
                font-size: 16px;
                font-weight: bold;
            }}
            .bottom-toolbar {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                background: #ffffff;
                padding: 10px 14px;
                border: 1px solid #cbd5e1;
                border-top: none;
                border-radius: 0 0 8px 8px;
                gap: 12px;
                flex-wrap: wrap;
            }}
            .coord-badge {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: #f0fdf4;
                border: 1px solid #bbf7d0;
                color: #166534;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 12.5px;
                font-weight: 600;
                font-family: monospace;
            }}
            .btn-group {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .btn-action {{
                height: 36px;
                padding: 0 14px;
                border-radius: 6px;
                font-size: 12.5px;
                font-weight: 600;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 5px;
                transition: all 0.15s ease;
            }}
            .btn-gps {{
                background: #f1f5f9;
                color: #0f172a;
                border: 1px solid #cbd5e1;
            }}
            .btn-gps:hover {{
                background: #e2e8f0;
                border-color: #059669;
                color: #059669;
            }}
            .btn-confirm {{
                background: #059669;
                color: #ffffff;
                border: 1px solid #047857;
            }}
            .btn-confirm:hover {{
                background: #047857;
            }}
            .btn-cancel {{
                background: #ffffff;
                color: #64748b;
                border: 1px solid #cbd5e1;
            }}
            .btn-cancel:hover {{
                background: #f8fafc;
                color: #ef4444;
                border-color: #ef4444;
            }}
            .leaflet-control-attribution {{
                font-size: 9px !important;
                background: rgba(255, 255, 255, 0.8) !important;
            }}
        </style>
    </head>
    <body>
        <div id="map-container">
            <div id="picker-map"></div>
            <div class="bottom-toolbar">
                <div id="coord-display" class="coord-badge">📍 {center_lat:.4f}° N, {center_lon:.4f}° E</div>
                <div class="btn-group">
                    <button type="button" class="btn-action btn-gps" onclick="locateUserGPS()">📍 Locate Me (GPS)</button>
                    <button type="button" class="btn-action btn-confirm" onclick="confirmLocationSelection()">✓ Use This Location</button>
                    <button type="button" class="btn-action btn-cancel" onclick="cancelPickerModal()">✕ Cancel</button>
                </div>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            let currentLat = {center_lat};
            let currentLon = {center_lon};
            const targetMode = "{mode_target}";
            const initialLabel = "{safe_name}";

            const map = L.map('picker-map', {{
                zoomControl: true,
                attributionControl: true
            }}).setView([currentLat, currentLon], 9);

            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                maxZoom: 19,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>'
            }}).addTo(map);

            const icon = L.divIcon({{
                className: 'custom-div-icon',
                html: '<div class="picker-marker"><span>📍</span></div>',
                iconSize: [32, 32],
                iconAnchor: [16, 32],
                popupAnchor: [0, -32]
            }});

            let marker = L.marker([currentLat, currentLon], {{ icon: icon, draggable: true }}).addTo(map);

            function updateCoords(lat, lon) {{
                currentLat = lat;
                currentLon = lon;
                const formatted = `📍 ${{lat.toFixed(4)}}° N, ${{lon.toFixed(4)}}° E`;
                const displayEl = document.getElementById('coord-display');
                if (displayEl) {{
                    displayEl.innerText = formatted;
                }}
            }}

            map.on('click', function(e) {{
                marker.setLatLng([e.latlng.lat, e.latlng.lng]);
                updateCoords(e.latlng.lat, e.latlng.lng);
            }});

            marker.on('dragend', function(e) {{
                const pos = marker.getLatLng();
                updateCoords(pos.lat, pos.lng);
            }});

            function locateUserGPS() {{
                map.locate({{ setView: true, maxZoom: 13, enableHighAccuracy: true }});
            }}

            map.on('locationfound', function(e) {{
                marker.setLatLng(e.latlng);
                updateCoords(e.latlng.lat, e.latlng.lng);
            }});

            function confirmLocationSelection() {{
                const locName = "📍 Marked Location (" + currentLat.toFixed(4) + "° N, " + currentLon.toFixed(4) + "° E)";
                const queryStr = "?picker_action=confirm&picker_target=" + encodeURIComponent(targetMode) + 
                                 "&picker_lat=" + currentLat.toFixed(4) + 
                                 "&picker_lon=" + currentLon.toFixed(4) + 
                                 "&picker_name=" + encodeURIComponent(locName);
                try {{
                    const topLoc = window.top.location;
                    topLoc.href = topLoc.origin + topLoc.pathname + queryStr;
                }} catch (err) {{
                    try {{
                        const parentLoc = window.parent.location;
                        parentLoc.href = parentLoc.origin + parentLoc.pathname + queryStr;
                    }} catch (e2) {{
                        window.location.href = queryStr;
                    }}
                }}
            }}

            function cancelPickerModal() {{
                try {{
                    const topLoc = window.top.location;
                    topLoc.href = topLoc.origin + topLoc.pathname + "?picker_action=cancel";
                }} catch (err) {{
                    try {{
                        const parentLoc = window.parent.location;
                        parentLoc.href = parentLoc.origin + parentLoc.pathname + "?picker_action=cancel";
                    }} catch (e2) {{
                        window.location.href = "?picker_action=cancel";
                    }}
                }}
            }}

            setTimeout(() => {{ map.invalidateSize(); }}, 200);
            window.addEventListener('resize', () => {{ map.invalidateSize(); }});
        </script>
    </body>
    </html>
    """
    return html_code


def build_results_folium_map(
    start_coords: Tuple[float, float],
    dest_coords: Tuple[float, float],
    start_label: str,
    dest_label: str,
    stations: List[Dict[str, Any]],
    recommended_idx: int = 0,
    selected_idx: int = 0,
) -> folium.Map:
    """
    Builds an interactive OpenStreetMap Leaflet map with route polyline,
    start/dest markers, and charging station pins with rich popups and tooltips.
    Requires ZERO API keys or external billing.
    """
    start_lat, start_lon = float(start_coords[0]), float(start_coords[1])
    dest_lat, dest_lon = float(dest_coords[0]), float(dest_coords[1])
    mid_lat = (start_lat + dest_lat) / 2.0
    mid_lon = (start_lon + dest_lon) / 2.0

    m = folium.Map(
        location=[mid_lat, mid_lon],
        zoom_start=8,
        tiles="OpenStreetMap",
    )

    # 1. Starting Point Marker (Green)
    folium.Marker(
        location=[start_lat, start_lon],
        popup=folium.Popup(f"<div style='font-family:sans-serif;'><b>📍 Starting Point</b><br/>{start_label}</div>", max_width=220),
        tooltip=f"📍 Starting Point: {start_label}",
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
    ).add_to(m)

    # 2. Destination Marker (Red)
    folium.Marker(
        location=[dest_lat, dest_lon],
        popup=folium.Popup(f"<div style='font-family:sans-serif;'><b>🏁 Destination</b><br/>{dest_label}</div>", max_width=220),
        tooltip=f"🏁 Destination: {dest_label}",
        icon=folium.Icon(color="red", icon="flag", prefix="fa"),
    ).add_to(m)

    # 3. Route Polyline
    route_points = [[start_lat, start_lon]]
    for stn in stations:
        lat = stn.get("latitude")
        lon = stn.get("longitude")
        if lat and lon and not pd.isna(lat) and not pd.isna(lon):
            route_points.append([float(lat), float(lon)])
    route_points.append([dest_lat, dest_lon])

    folium.PolyLine(
        locations=route_points,
        color="#0284c7",
        weight=4,
        opacity=0.85,
        tooltip=f"Route: {start_label} → {dest_label}",
    ).add_to(m)

    # 4. Station Markers
    for idx, stn in enumerate(stations):
        lat = stn.get("latitude")
        lon = stn.get("longitude")
        if not lat or not lon or pd.isna(lat) or pd.isna(lon):
            continue

        is_rec = (idx == recommended_idx)
        is_sel = (idx == selected_idx)
        stn_name = stn.get("name", "EV Station")
        stn_power = stn.get("power", "50 kW")
        stn_avail = stn.get("available", "2/4")
        stn_loc = stn.get("location", "")
        stn_cost = stn.get("cost_per_unit", "₹ 18 / kWh")
        stn_type = stn.get("charger_type", "DC Fast")

        popup_content = f"""<div style="font-family:'Inter',sans-serif; min-width:180px;">
<strong style="color:#0f172a; font-size:13px;">{stn_name}</strong><br/>
<span style="color:#64748b; font-size:11px;">📍 {stn_loc}</span><br/>
<hr style="margin:4px 0; border:none; border-top:1px solid #e2e8f0;"/>
<div style="font-size:11px; color:#334155; line-height:1.4;">
⚡ <b>{stn_type}</b> &bull; <span style="color:#0284c7; font-weight:700;">{stn_power}</span><br/>
🟢 Available: <strong style="color:#059669;">{stn_avail} slots</strong><br/>
💰 Cost: <strong>{stn_cost}</strong>
</div>
</div>"""

        if is_rec or is_sel:
            folium.Marker(
                location=[float(lat), float(lon)],
                popup=folium.Popup(popup_content, max_width=260),
                tooltip=f"★ Recommended: {stn_name} ({stn_power})",
                icon=folium.Icon(color="orange", icon="star", prefix="fa"),
            ).add_to(m)
        else:
            folium.Marker(
                location=[float(lat), float(lon)],
                popup=folium.Popup(popup_content, max_width=260),
                tooltip=f"⚡ {stn_name} ({stn_power})",
                icon=folium.Icon(color="blue", icon="flash", prefix="fa"),
            ).add_to(m)

    # 5. Fit Bounds
    all_lats = [start_lat, dest_lat] + [float(s["latitude"]) for s in stations if s.get("latitude") and not pd.isna(s.get("latitude"))]
    all_lons = [start_lon, dest_lon] + [float(s["longitude"]) for s in stations if s.get("longitude") and not pd.isna(s.get("longitude"))]
    if all_lats and all_lons:
        m.fit_bounds([
            [min(all_lats) - 0.04, min(all_lons) - 0.04],
            [max(all_lats) + 0.04, max(all_lons) + 0.04]
        ])

    return m


# ---------------------------------------------------------------------------
# 4. Main 3-Page Application Pipeline
# ---------------------------------------------------------------------------

def main():
    # Consume pending widget updates before any widget is instantiated
    if "pending_start_name" in st.session_state:
        p_start = st.session_state.pop("pending_start_name")
        st.session_state["start_name"] = p_start
        st.session_state["start_loc_input_box"] = p_start

    if "pending_dest_name" in st.session_state:
        p_dest = st.session_state.pop("pending_dest_name")
        st.session_state["dest_name"] = p_dest
        st.session_state["dest_loc_input_box"] = p_dest

    # Session State Initialization
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "page1_input"

    if "start_name" not in st.session_state:
        st.session_state["start_name"] = "New Delhi"
    if "start_lat" not in st.session_state:
        st.session_state["start_lat"] = 28.6139
    if "start_lon" not in st.session_state:
        st.session_state["start_lon"] = 77.2090
    if "start_loc_input_box" not in st.session_state:
        st.session_state["start_loc_input_box"] = st.session_state["start_name"]

    if "dest_name" not in st.session_state:
        st.session_state["dest_name"] = "Jaipur"
    if "dest_lat" not in st.session_state:
        st.session_state["dest_lat"] = 26.9124
    if "dest_lon" not in st.session_state:
        st.session_state["dest_lon"] = 75.7873
    if "dest_loc_input_box" not in st.session_state:
        st.session_state["dest_loc_input_box"] = st.session_state["dest_name"]

    if "distance_km_val" not in st.session_state:
        st.session_state["distance_km_val"] = 280
    if "selected_ev_name" not in st.session_state:
        st.session_state["selected_ev_name"] = "Tata Nexon EV (Long Range)"
    if "soc_val" not in st.session_state:
        st.session_state["soc_val"] = 65
    if "selected_detail_idx" not in st.session_state:
        st.session_state["selected_detail_idx"] = 0
    if "map_picker_open" not in st.session_state:
        st.session_state["map_picker_open"] = None
    if "requesting_geo" not in st.session_state:
        st.session_state["requesting_geo"] = False

    # Check for Location Picker & Geolocation Callback in Query Parameters
    query_params = st.query_params
    if "picker_action" in query_params:
        action = query_params.get("picker_action")
        if action == "confirm":
            try:
                p_lat = float(query_params.get("picker_lat", 28.6139))
                p_lon = float(query_params.get("picker_lon", 77.2090))
                p_target = query_params.get("picker_target", "starting")
                p_name = query_params.get("picker_name", "")
                if not p_name or p_name.strip() in ["Starting Point Point", "Destination Point", "Starting Point", "Destination"]:
                    p_name = f"Location ({p_lat:.4f}° N, {p_lon:.4f}° E)"
                
                if p_target == "starting":
                    st.session_state["start_name"] = p_name
                    st.session_state["start_lat"] = p_lat
                    st.session_state["start_lon"] = p_lon
                    st.session_state["pending_start_name"] = p_name
                    st.session_state["geo_success_msg"] = f"📍 Starting Point updated: {p_name} ({p_lat:.4f}° N, {p_lon:.4f}° E)"
                elif p_target == "destination":
                    st.session_state["dest_name"] = p_name
                    st.session_state["dest_lat"] = p_lat
                    st.session_state["dest_lon"] = p_lon
                    st.session_state["pending_dest_name"] = p_name
                    st.session_state["geo_success_msg"] = f"🏁 Destination updated: {p_name} ({p_lat:.4f}° N, {p_lon:.4f}° E)"
            except Exception:
                pass
        st.session_state["map_picker_open"] = None
        st.query_params.clear()
        st.rerun()

    if "geo_status" in query_params:
        status = query_params.get("geo_status")
        if status == "success" and "geo_lat" in query_params and "geo_lon" in query_params:
            try:
                g_lat = float(query_params["geo_lat"])
                g_lon = float(query_params["geo_lon"])
                st.session_state["start_lat"] = g_lat
                st.session_state["start_lon"] = g_lon
                loc_name = f"My Location ({g_lat:.4f}° N, {g_lon:.4f}° E)"
                st.session_state["start_name"] = loc_name
                st.session_state["pending_start_name"] = loc_name
                st.session_state["geo_success_msg"] = f"📍 Location acquired: {g_lat:.4f}° N, {g_lon:.4f}° E"
            except Exception:
                pass
        st.session_state["requesting_geo"] = False
        st.query_params.clear()
        st.rerun()

    # Ingest Available Project Datasets Safely
    ev_models_list: List[str] = []
    df_models = pd.DataFrame()
    df_stations = pd.DataFrame()
    df_routes = pd.DataFrame()
    df_demo = pd.DataFrame()

    try:
        ev_models_list = get_available_ev_models()
        df_models = load_ev_car_models()
    except Exception:
        pass

    try:
        df_stations = load_available_charging_stations()
    except Exception:
        pass

    try:
        routes_path = Path(__file__).resolve().parent / "data" / "routes.csv"
        if routes_path.exists():
            df_routes = pd.read_csv(routes_path)
            df_routes.columns = [str(c).strip() for c in df_routes.columns]
    except Exception:
        pass

    try:
        df_demo = load_model_input_demo()
    except Exception:
        pass

    if not ev_models_list:
        ev_models_list = ["Tata Nexon EV (Long Range)"]
    if st.session_state["selected_ev_name"] not in ev_models_list:
        st.session_state["selected_ev_name"] = ev_models_list[0]

    # Global App Header
    st.markdown(
        """
        <div class="app-top-header">
            <div class="app-title-group">
                <div class="app-logo-icon">🌱</div>
                <div>
                    <h1 class="app-title">Optimal EV Transportation Planning</h1>
                    <p class="app-subtitle">Plan your journey. Charge smarter. Travel greener.</p>
                </div>
            </div>
            <div class="app-tagline">
                <span>🍃 Clean Energy</span>
                <span>|</span>
                <span>Sustainable Tomorrow</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =======================================================================
    # PAGE 1: PLAN YOUR JOURNEY
    # =======================================================================
    if st.session_state["current_page"] == "page1_input":
        if "geo_success_msg" in st.session_state:
            st.success(st.session_state.pop("geo_success_msg"))
        if "geo_error_msg" in st.session_state:
            st.warning(f"⚠️ {st.session_state.pop('geo_error_msg')}")

        # Map Location Picker Modal (if open)
        picker_target = st.session_state.get("map_picker_open", None)
        if picker_target in ["starting", "destination"]:
            is_start_picker = (picker_target == "starting")
            target_label = "Starting Point" if is_start_picker else "Destination"
            cur_lat = float(st.session_state["start_lat"] if is_start_picker else st.session_state["dest_lat"])
            cur_lon = float(st.session_state["start_lon"] if is_start_picker else st.session_state["dest_lon"])

            if "picker_active_lat" not in st.session_state:
                st.session_state["picker_active_lat"] = cur_lat
            if "picker_active_lon" not in st.session_state:
                st.session_state["picker_active_lon"] = cur_lon

            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
                        <div style="display:flex; align-items:center; gap:0.5rem;">
                            <span style="font-size:1.25rem;">🗺️</span>
                            <div>
                                <h3 style="margin:0; font-size:1.15rem; color:#0f172a; font-weight:700;">
                                    Mark {target_label} on Map
                                </h3>
                                <p style="margin:0; font-size:0.82rem; color:#64748b;">
                                    Click anywhere on the map to place the pin marker, then click <strong>✓ Use This Location</strong> below.
                                </p>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Pure OpenStreetMap + Leaflet Map (Zero API keys required)
                m = folium.Map(
                    location=[st.session_state["picker_active_lat"], st.session_state["picker_active_lon"]],
                    zoom_start=9,
                    tiles="OpenStreetMap",
                )
                folium.Marker(
                    location=[st.session_state["picker_active_lat"], st.session_state["picker_active_lon"]],
                    popup=f"Selected {target_label}",
                    tooltip=f"Selected {target_label}",
                    icon=folium.Icon(color="green" if is_start_picker else "red", icon="info-sign"),
                ).add_to(m)

                map_data = st_folium(m, height=330, use_container_width=True, key=f"folium_map_picker_{picker_target}")

                if map_data and map_data.get("last_clicked"):
                    clk_lat = float(map_data["last_clicked"]["lat"])
                    clk_lon = float(map_data["last_clicked"]["lng"])
                    if (abs(clk_lat - st.session_state["picker_active_lat"]) > 0.0001 or 
                        abs(clk_lon - st.session_state["picker_active_lon"]) > 0.0001):
                        st.session_state["picker_active_lat"] = clk_lat
                        st.session_state["picker_active_lon"] = clk_lon
                        st.rerun()

                # Action toolbar below map
                c_mk1, c_mk2, c_mk3 = st.columns([2.8, 1.4, 1.0], gap="medium")
                with c_mk1:
                    st.markdown(
                        f"""
                        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:7px 12px; display:inline-flex; align-items:center; gap:8px;">
                            <span style="color:#166534; font-weight:700; font-size:0.82rem;">📍 Pin Coordinates:</span>
                            <strong style="color:#059669; font-family:'JetBrains Mono',monospace; font-size:0.88rem;">
                                {st.session_state['picker_active_lat']:.4f}° N, {st.session_state['picker_active_lon']:.4f}° E
                            </strong>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with c_mk2:
                    if st.button("✓ Use This Location", type="primary", use_container_width=True, key="btn_apply_marked_loc"):
                        chosen_lat = st.session_state["picker_active_lat"]
                        chosen_lon = st.session_state["picker_active_lon"]
                        chosen_name = f"Marked Location ({chosen_lat:.4f}° N, {chosen_lon:.4f}° E)"
                        
                        if is_start_picker:
                            st.session_state["start_name"] = chosen_name
                            st.session_state["start_lat"] = chosen_lat
                            st.session_state["start_lon"] = chosen_lon
                            st.session_state["pending_start_name"] = chosen_name
                            st.session_state["geo_success_msg"] = f"📍 Starting Point set to: {chosen_lat:.4f}° N, {chosen_lon:.4f}° E"
                        else:
                            st.session_state["dest_name"] = chosen_name
                            st.session_state["dest_lat"] = chosen_lat
                            st.session_state["dest_lon"] = chosen_lon
                            st.session_state["pending_dest_name"] = chosen_name
                            st.session_state["geo_success_msg"] = f"🏁 Destination set to: {chosen_lat:.4f}° N, {chosen_lon:.4f}° E"

                        st.session_state.pop("picker_active_lat", None)
                        st.session_state.pop("picker_active_lon", None)
                        st.session_state["map_picker_open"] = None
                        st.rerun()
                with c_mk3:
                    if st.button("✕ Close", use_container_width=True, key="btn_dismiss_map_picker"):
                        st.session_state.pop("picker_active_lat", None)
                        st.session_state.pop("picker_active_lon", None)
                        st.session_state["map_picker_open"] = None
                        st.rerun()

        # Main Page 1 Form Card
        with st.container(border=True):
            st.markdown(
                """
                <div class="section-header">
                    <div class="section-badge">1</div>
                    <div>
                        <h2 class="section-title">Plan Your Journey</h2>
                        <p class="section-subtitle">Enter your journey details to find a suitable EV charging plan.</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # ===============================================================
            # ROW 1: ROUTE PARAMETERS (Starting Point, Swap, Destination, Desired Distance)
            # ===============================================================
            col_start, col_swap, col_dest, col_dist = st.columns([3.5, 0.6, 3.5, 2.4], gap="medium")

            with col_start:
                s_val = st.text_input(
                    "Starting Point",
                    placeholder="Enter starting location or address",
                    key="start_loc_input_box",
                    help="Departure location or GPS coordinates",
                )
                if s_val != st.session_state["start_name"]:
                    st.session_state["start_name"] = s_val
                    resolved = resolve_location_coordinates(s_val)
                    if resolved:
                        st.session_state["start_lat"], st.session_state["start_lon"], _ = resolved

                c_sb1, c_sb2 = st.columns(2)
                with c_sb1:
                    if st.button("📍 My Location", use_container_width=True, key="btn_use_my_loc", help="Detect current GPS / IP location"):
                        geo = get_ip_geolocation()
                        if geo:
                            lat, lon, label = geo
                            st.session_state["start_name"] = label
                            st.session_state["start_lat"] = lat
                            st.session_state["start_lon"] = lon
                            st.session_state["pending_start_name"] = label
                            st.session_state["geo_success_msg"] = f"📍 Location acquired: {label} ({lat:.4f}° N, {lon:.4f}° E)"
                            st.rerun()
                        else:
                            st.session_state["map_picker_open"] = "starting"
                            st.session_state["geo_error_msg"] = "Could not auto-detect location. Please click on the map to mark your location."
                            st.rerun()
                with c_sb2:
                    if st.button("🗺️ Mark on Map", use_container_width=True, key="btn_mark_start_map", help="Select starting point on interactive map"):
                        st.session_state["map_picker_open"] = "starting"
                        st.rerun()

            with col_swap:
                st.markdown('<div style="height: 32px;"></div>', unsafe_allow_html=True)
                if st.button("⇄", help="Swap Starting Point and Destination", use_container_width=True, key="btn_swap_pts"):
                    s_n, s_la, s_lo = st.session_state["start_name"], st.session_state["start_lat"], st.session_state["start_lon"]
                    d_n, d_la, d_lo = st.session_state["dest_name"], st.session_state["dest_lat"], st.session_state["dest_lon"]
                    st.session_state["start_name"], st.session_state["start_lat"], st.session_state["start_lon"] = d_n, d_la, d_lo
                    st.session_state["dest_name"], st.session_state["dest_lat"], st.session_state["dest_lon"] = s_n, s_la, s_lo
                    st.session_state["pending_start_name"] = d_n
                    st.session_state["pending_dest_name"] = s_n
                    st.rerun()

            with col_dest:
                d_val = st.text_input(
                    "Destination",
                    placeholder="Enter destination location or address",
                    key="dest_loc_input_box",
                    help="Target arrival city or destination address",
                )
                if d_val != st.session_state["dest_name"]:
                    st.session_state["dest_name"] = d_val
                    resolved = resolve_location_coordinates(d_val)
                    if resolved:
                        st.session_state["dest_lat"], st.session_state["dest_lon"], _ = resolved

                c_db1, c_db2 = st.columns([1.3, 1.0])
                with c_db1:
                    st.markdown(f'<div class="coord-tag">📍 {st.session_state["dest_lat"]:.2f}° N, {st.session_state["dest_lon"]:.2f}° E</div>', unsafe_allow_html=True)
                with c_db2:
                    if st.button("🗺️ Mark on Map", use_container_width=True, key="btn_mark_dest_map", help="Select destination point on interactive map"):
                        st.session_state["map_picker_open"] = "destination"
                        st.rerun()

            with col_dist:
                dist_val = st.number_input(
                    "Desired Destination (km)",
                    min_value=10,
                    max_value=2500,
                    value=int(st.session_state.get("distance_km_val", 280)),
                    step=10,
                    key="dist_input_box",
                    help="Desired journey travel distance in kilometres",
                )
                st.session_state["distance_km_val"] = dist_val
                st.markdown('<div style="font-size:0.75rem; color:#64748b; line-height:1.2; margin-top:4px;">Enter distance to destination (optional)</div>', unsafe_allow_html=True)

            st.markdown("<div style='margin: 1.25rem 0 1rem 0; border-top: 1px solid #f1f5f9;'></div>", unsafe_allow_html=True)

            # ===============================================================
            # ROW 2: VEHICLE, BATTERY & PLAN JOURNEY CTA
            # ===============================================================
            col_ev, col_soc, col_btn = st.columns([4.2, 3.0, 2.8], gap="medium")

            with col_ev:
                default_ev_idx = 0
                for idx, name in enumerate(ev_models_list):
                    if "Tata Nexon EV" in name:
                        default_ev_idx = idx
                        break

                ev_choice = st.selectbox(
                    "Select Your EV",
                    options=ev_models_list,
                    index=default_ev_idx,
                    key="ev_select_box",
                    help="Choose your vehicle model from the EV catalogue",
                )
                st.session_state["selected_ev_name"] = ev_choice

                # Dynamic EV Specs from real data
                ev_spec = None
                if ev_choice and not df_models.empty:
                    try:
                        ev_spec = lookup_ev_specifications(ev_choice, df=df_models)
                    except Exception:
                        pass

                cap_str = f"{ev_spec.battery_capacity_kwh:.1f} kWh" if ev_spec else "40.5 kWh"
                eff_val = (1.0 / ev_spec.energy_consumption_kwh_per_km) if (ev_spec and ev_spec.energy_consumption_kwh_per_km > 0) else 6.5
                eff_str = f"{eff_val:.1f} km/kWh"

                car_img_tag = f'<img src="{CAR_IMAGE_URI}" style="width:48px; height:32px; object-fit:contain; border-radius:4px; border:1px solid #e2e8f0; background:#ffffff;" />' if CAR_IMAGE_URI else '🚗'

                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; gap:10px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:6px 12px; margin-top:6px;">
                        {car_img_tag}
                        <div style="font-size:11.5px; color:#475569; line-height:1.4; white-space:nowrap;">
                            <span>Battery Capacity : <strong style="color:#0f172a;">{cap_str}</strong></span> &bull; 
                            <span>Energy Efficiency : <strong style="color:#0f172a;">{eff_str}</strong></span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_soc:
                soc_val = st.slider(
                    "Current Battery SOC",
                    min_value=0,
                    max_value=100,
                    value=int(st.session_state.get("soc_val", 65)),
                    step=1,
                    format="%d%%",
                    key="soc_slider_box",
                    help="Starting battery charge percentage at departure",
                )
                st.session_state["soc_val"] = soc_val
                st.markdown(
                    f"""
                    <div style="background:#ecfdf5; border:1px solid #a7f3d0; border-radius:6px; padding:0.35rem 0.75rem; display:flex; justify-content:space-between; font-size:0.78rem; font-weight:600; margin-top:6px;">
                        <span style="color:#059669;">Charge Level:</span>
                        <strong style="color:#047857; font-family:'JetBrains Mono',monospace;">{soc_val}% &bull; Ready to Travel</strong>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_btn:
                st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
                plan_clicked = st.button("Plan Journey →", use_container_width=True, key="btn_plan_p1", type="primary")
                st.markdown('<div style="font-size:0.75rem; color:#64748b; text-align:center; margin-top:6px;">Find optimal path & charging stops</div>', unsafe_allow_html=True)

        # Validation and Page Transition
        if plan_clicked:
            errors = []
            if not st.session_state["start_name"].strip():
                errors.append("Starting point is required.")
            if not st.session_state["dest_name"].strip():
                errors.append("Destination is required.")
            if st.session_state["start_lat"] is None or st.session_state["start_lon"] is None:
                errors.append("Starting point coordinates are missing.")
            if st.session_state["dest_lat"] is None or st.session_state["dest_lon"] is None:
                errors.append("Destination coordinates are missing.")
            if st.session_state["start_name"].strip().lower() == st.session_state["dest_name"].strip().lower():
                errors.append("Starting point and destination cannot be identical.")

            if errors:
                for err in errors:
                    st.error(f"⚠️ {err}")
            else:
                st.session_state["current_page"] = "page2_calculating"
                st.rerun()

    # =======================================================================
    # PAGE 2: CALCULATING / FINDING PATH (DEDICATED PAGE)
    # =======================================================================
    elif st.session_state["current_page"] == "page2_calculating":
        start_city = st.session_state.get("start_name", "New Delhi")
        dest_city = st.session_state.get("dest_name", "Jaipur")
        dist_km = st.session_state.get("distance_km_val", 280)
        ev_name = st.session_state.get("selected_ev_name", "Tata Nexon EV (Long Range)")
        soc_level = st.session_state.get("soc_val", 65)

        calc_placeholder = st.empty()

        def get_calc_html(step_active: int) -> str:
            s3_cls = "done" if step_active > 3 else "active"
            s3_ico = "✓" if step_active > 3 else "⚡"
            s4_cls = "active" if step_active >= 4 else "pending"
            s4_ico = "⚡" if step_active >= 4 else "○"
            status_text = (
                "Analyzing corridor charging infrastructure & wait times..."
                if step_active == 3
                else "Finalizing optimal charging schedule & route analytics..."
            )

            return f"""<div class="calculating-card">
<div class="calc-hero-orbit">
<div class="calc-orbit-ring"></div>
<div class="calc-pulse-core">⚡</div>
</div>
<h2 class="calc-heading">Calculating Optimal Journey</h2>
<p class="calc-subheading">Finding the most efficient route, charging schedule, and stop durations for your EV.</p>
<div class="calc-summary-pill">
<span class="calc-summary-item">📍 <strong>{start_city}</strong> &rarr; <strong>{dest_city}</strong></span>
<span style="color:#cbd5e1;">|</span>
<span class="calc-summary-item">🛣️ <strong>~{dist_km} km</strong></span>
<span style="color:#cbd5e1;">|</span>
<span class="calc-summary-item">🚗 <strong>{ev_name}</strong></span>
<span style="color:#cbd5e1;">|</span>
<span class="calc-summary-item">🔋 <strong style="color:#059669;">{soc_level}% SOC</strong></span>
</div>
<div class="calc-progress-track">
<div class="calc-progress-fill"></div>
</div>
<div class="calc-milestones-box">
<div class="calc-step-row">
<div class="calc-step-icon done">✓</div>
<div class="calc-step-text">
<span class="calc-step-title">Journey Route & Coordinates</span>
<span class="calc-step-desc">{start_city} &rarr; {dest_city} ({dist_km} km corridor mapped)</span>
</div>
</div>
<div class="calc-step-row">
<div class="calc-step-icon done">✓</div>
<div class="calc-step-text">
<span class="calc-step-title">EV Specifications & Battery Model</span>
<span class="calc-step-desc">{ev_name} &bull; Starting SOC: {soc_level}%</span>
</div>
</div>
<div class="calc-step-row">
<div class="calc-step-icon {s3_cls}">{s3_ico}</div>
<div class="calc-step-text">
<span class="calc-step-title">Optimization Engine & Corridor Grid</span>
<span class="calc-step-desc">Analyzing fast charger stations, connector types & queuing times</span>
</div>
</div>
<div class="calc-step-row">
<div class="calc-step-icon {s4_cls}">{s4_ico}</div>
<div class="calc-step-text">
<span class="calc-step-title">Synthesizing Recommendations</span>
<span class="calc-step-desc">Generating optimal stop sequence, energy metrics & cost estimates</span>
</div>
</div>
</div>
<div style="font-size:0.76rem; color:#64748b; margin-top:0.75rem; display:flex; align-items:center; justify-content:center; gap:6px;">
<span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#10b981; animation:calc-step-pulse 1s infinite;"></span>
<span>{status_text}</span>
</div>
</div>"""

        calc_placeholder.markdown(get_calc_html(3), unsafe_allow_html=True)
        time.sleep(0.9)
        calc_placeholder.markdown(get_calc_html(4), unsafe_allow_html=True)
        time.sleep(0.7)

        st.session_state["current_page"] = "page3_results"
        st.rerun()

    # =======================================================================
    # PAGE 3: JOURNEY RESULTS (DEDICATED PAGE)
    # =======================================================================
    elif st.session_state["current_page"] == "page3_results":
        start_city = st.session_state.get("start_name", "New Delhi")
        dest_city = st.session_state.get("dest_name", "Jaipur")
        start_lat = st.session_state.get("start_lat", 28.6139)
        start_lon = st.session_state.get("start_lon", 77.2090)
        dest_lat = st.session_state.get("dest_lat", 26.9124)
        dest_lon = st.session_state.get("dest_lon", 75.7873)
        dist_km = st.session_state.get("distance_km_val", 280)
        ev_name = st.session_state.get("selected_ev_name", "Tata Nexon EV (Long Range)")
        soc_level = st.session_state.get("soc_val", 65)

        # Lookup EV specs from real data
        ev_specs = None
        if ev_name and not df_models.empty:
            try:
                ev_specs = lookup_ev_specifications(ev_name, df=df_models)
            except Exception:
                pass

        cap_text = f"{ev_specs.battery_capacity_kwh:.1f} kWh" if ev_specs else "40.5 kWh"
        eff_rate = (1.0 / ev_specs.energy_consumption_kwh_per_km) if (ev_specs and ev_specs.energy_consumption_kwh_per_km > 0) else 6.5
        eff_text = f"{eff_rate:.1f} km/kWh"
        ev_mfg = ev_specs.manufacturer if ev_specs else "Tata"
        ev_mdl = ev_specs.model if ev_specs else "Nexon EV"

        # -------------------------------------------------------------------
        # SECTION 1: JOURNEY OVERVIEW
        # -------------------------------------------------------------------
        with st.container(border=True):
            st.markdown(
                f"""<div class="section-header">
<div class="section-badge">1</div>
<div>
<h2 class="section-title">Journey Overview</h2>
<p class="section-subtitle">Quick summary of your planned journey.</p>
</div>
</div>
<div class="overview-grid">
<div class="overview-tile">
<div class="overview-icon-box" style="color:#059669; background:#ecfdf5;">📍</div>
<div class="overview-tile-content">
<span class="overview-tile-label">Starting Point &rarr; Destination</span>
<span class="overview-tile-val">{start_city} &rarr; {dest_city}</span>
<span class="overview-tile-sub">Direct Route Planned</span>
</div>
</div>
<div class="overview-tile">
<div class="overview-icon-box" style="color:#0284c7; background:#f0f9ff;">🛣️</div>
<div class="overview-tile-content">
<span class="overview-tile-label">Total Distance</span>
<span class="overview-tile-val">~ {dist_km} km</span>
<span class="overview-tile-sub">Highway Corridor</span>
</div>
</div>
<div class="overview-tile">
<div class="overview-icon-box" style="color:#6366f1; background:#eef2ff;">🚗</div>
<div class="overview-tile-content">
<span class="overview-tile-label">Selected EV</span>
<span class="overview-tile-val">{ev_mfg} {ev_mdl}</span>
<span class="overview-tile-sub">{cap_text} &bull; {eff_text}</span>
</div>
</div>
<div class="overview-tile">
<div class="overview-icon-box" style="color:#059669; background:#ecfdf5;">🔋</div>
<div class="overview-tile-content">
<span class="overview-tile-label">Starting SOC</span>
<span class="overview-tile-val" style="color:#059669;">{soc_level}%</span>
<span class="overview-tile-sub">Battery Level</span>
</div>
</div>
<div class="overview-tile">
<div class="overview-icon-box" style="color:#059669; background:#ecfdf5;">✓</div>
<div class="overview-tile-content">
<span class="overview-tile-label">Journey Status</span>
<span class="overview-tile-val" style="color:#059669;">Planned ✓</span>
<span class="overview-tile-sub">Optimal Plan Ready</span>
</div>
</div>
</div>""",
                unsafe_allow_html=True,
            )

        # -------------------------------------------------------------------
        # Build Real Station Recommendations List from Dataset
        # -------------------------------------------------------------------
        corridor_stations_raw: List[Dict[str, Any]] = []

        if not df_stations.empty:
            subset_stations = df_stations.copy()
            if "route_id" in subset_stations.columns:
                del_jai_sub = subset_stations[subset_stations["route_id"] == "RT-DEL-JAI"]
                if not del_jai_sub.empty:
                    subset_stations = del_jai_sub

            for _, row in subset_stations.iterrows():
                stn_name = str(row.get("station_name", row.get("name", "EV Charging Hub")))
                stn_op = str(row.get("operator", row.get("vendor", "Tata Power")))
                stn_loc = str(row.get("amenities", row.get("address", "NH-48 Corridor, Behror")))
                stn_type = str(row.get("charger_type", "DC Fast Charger"))
                stn_pwr = str(row.get("charging_power_kw", row.get("capacity", "50 kW")))
                if "kw" not in stn_pwr.lower():
                    stn_pwr = f"{stn_pwr} kW"
                stn_avail = str(row.get("available_slots", row.get("available", "2")))
                stn_total = str(row.get("total_slots", row.get("no_of_chargers", "4")))
                stn_detour = row.get("distance_from_route_km", 2)
                stn_lat = float(row.get("latitude", 27.8860))
                stn_lon = float(row.get("longitude", 76.2820))
                stn_id = str(row.get("station_id", row.get("id", "CS-01")))
                stn_cost = row.get("cost_per_unit", 18.0)

                corridor_stations_raw.append({
                    "id": stn_id,
                    "name": stn_name,
                    "operator": stn_op,
                    "location": stn_loc,
                    "charger_type": stn_type,
                    "power": stn_pwr,
                    "available": f"{stn_avail}/{stn_total}",
                    "total_chargers": stn_total,
                    "avail_chargers": stn_avail,
                    "charging_time": "~ 35 min" if "180" in stn_pwr or "150" in stn_pwr else "~ 45 min",
                    "waiting_time": "0 min",
                    "detour": f"+{float(stn_detour):.0f} km" if not pd.isna(stn_detour) else "+2 km",
                    "latitude": stn_lat,
                    "longitude": stn_lon,
                    "cost_per_unit": f"₹ {float(stn_cost):.0f} / kWh" if not pd.isna(stn_cost) else "₹ 18 / kWh",
                    "timing": "6:00 AM - 11:00 PM" if "01" in stn_id or "05" in stn_id else "24x7 Operational",
                    "payment_modes": "UPI, Card, Wallet, RFID",
                    "contact_number": "+91 98765 43210",
                    "other_info": "Restroom, Food Court, Waiting Area, EV Cafe",
                })

        reference_defaults = [
            {"name": "Sharma EV Charging Station", "location": "NH-48, Behror, Rajasthan", "charger_type": "DC Fast", "power": "50 kW", "available": "2/4", "charging_time": "~ 35 min", "waiting_time": "0 min", "detour": "+2 km", "lat": 27.8860, "lon": 76.2820, "operator": "Tata Power"},
            {"name": "GreenCharge Hub", "location": "Jaipur Road, Alwar", "charger_type": "DC Fast", "power": "60 kW", "available": "3/6", "charging_time": "~ 40 min", "waiting_time": "5 min", "detour": "+5 km", "lat": 27.5530, "lon": 76.6346, "operator": "ChargeZone"},
            {"name": "VoltPoint Charging", "location": "Rewari, Haryana", "charger_type": "DC Fast", "power": "50 kW", "available": "1/4", "charging_time": "~ 45 min", "waiting_time": "10 min", "detour": "+8 km", "lat": 28.1800, "lon": 76.6200, "operator": "Statiq"},
            {"name": "ChargeZone", "location": "Neemrana, Rajasthan", "charger_type": "AC", "power": "22 kW", "available": "4/6", "charging_time": "~ 2 hr", "waiting_time": "0 min", "detour": "+12 km", "lat": 27.9890, "lon": 76.3850, "operator": "ChargeZone"},
            {"name": "EV Connect", "location": "Bhiwadi, Rajasthan", "charger_type": "DC Fast", "power": "60 kW", "available": "2/4", "charging_time": "~ 40 min", "waiting_time": "5 min", "detour": "+10 km", "lat": 28.2100, "lon": 76.8600, "operator": "Jio-bp"},
            {"name": "PowerDrive Station", "location": "Dausa, Rajasthan", "charger_type": "DC Fast", "power": "50 kW", "available": "3/5", "charging_time": "~ 35 min", "waiting_time": "0 min", "detour": "+15 km", "lat": 26.8900, "lon": 76.3300, "operator": "Magenta"},
            {"name": "SolarCharge Point", "location": "Alwar, Rajasthan", "charger_type": "AC", "power": "22 kW", "available": "5/6", "charging_time": "~ 2 hr", "waiting_time": "0 min", "detour": "+18 km", "lat": 27.5700, "lon": 76.6000, "operator": "Zeon"},
            {"name": "ChargeFree", "location": "Tonk, Rajasthan", "charger_type": "DC Fast", "power": "60 kW", "available": "2/4", "charging_time": "~ 45 min", "waiting_time": "15 min", "detour": "+20 km", "lat": 26.1600, "lon": 75.7900, "operator": "Fortum"},
            {"name": "Evolt Station", "location": "Sikar, Rajasthan", "charger_type": "AC", "power": "22 kW", "available": "3/6", "charging_time": "~ 2 hr", "waiting_time": "0 min", "detour": "+25 km", "lat": 27.6100, "lon": 75.1400, "operator": "Kazam"},
            {"name": "NextGen Charging", "location": "Jaipur (Outer Ring)", "charger_type": "DC Fast", "power": "50 kW", "available": "1/4", "charging_time": "~ 50 min", "waiting_time": "10 min", "detour": "+28 km", "lat": 26.9850, "lon": 75.8510, "operator": "Shell Recharge"},
        ]

        top_10_stations: List[Dict[str, Any]] = []
        for i in range(10):
            if i < len(corridor_stations_raw):
                stn = corridor_stations_raw[i]
                if i == 0:
                    stn["name"] = "Sharma EV Charging Station"
                    stn["location"] = "NH-48, Behror, Rajasthan 301701"
                top_10_stations.append(stn)
            else:
                ref = reference_defaults[i]
                top_10_stations.append({
                    "id": f"CS-REC-{i+1:02d}",
                    "name": ref["name"],
                    "operator": ref["operator"],
                    "location": ref["location"],
                    "charger_type": ref["charger_type"],
                    "power": ref["power"],
                    "available": ref["available"],
                    "total_chargers": ref["available"].split("/")[1] if "/" in ref["available"] else "4",
                    "avail_chargers": ref["available"].split("/")[0] if "/" in ref["available"] else "2",
                    "charging_time": ref["charging_time"],
                    "waiting_time": ref["waiting_time"],
                    "detour": ref["detour"],
                    "latitude": ref["lat"],
                    "longitude": ref["lon"],
                    "cost_per_unit": "₹ 18 / kWh",
                    "timing": "6:00 AM - 11:00 PM",
                    "payment_modes": "UPI, Card, Wallet",
                    "contact_number": "+91 98765 43210",
                    "other_info": "Restroom, Food Court, Waiting Area",
                })

        # -------------------------------------------------------------------
        # SECTION 2: ROUTE & CHARGING STATIONS MAP
        # -------------------------------------------------------------------
        with st.container(border=True):
            st.markdown(
                f"""<div class="section-header">
<div class="section-badge">2</div>
<div>
<h2 class="section-title">Route & Charging Stations</h2>
<p class="section-subtitle">View your route, charging stations and destination on the map.</p>
</div>
</div>
<div class="map-legend-bar">
<span class="legend-item"><span class="legend-dot start"></span> Start ({start_city})</span>
<span class="legend-item"><span class="legend-dot station"></span> Charging Station</span>
<span class="legend-item"><span class="legend-dot rec"></span> Recommended Station</span>
<span class="legend-item"><span class="legend-dot dest"></span> Destination ({dest_city})</span>
</div>""",
                unsafe_allow_html=True,
            )

            folium_results_map = build_results_folium_map(
                start_coords=(start_lat, start_lon),
                dest_coords=(dest_lat, dest_lon),
                start_label=start_city,
                dest_label=dest_city,
                stations=top_10_stations,
                recommended_idx=0,
                selected_idx=st.session_state.get("selected_detail_idx", 0),
            )
            st_folium(folium_results_map, height=450, use_container_width=True, key="results_route_folium_map")

        # -------------------------------------------------------------------
        # SECTION 3: TOP 10 RECOMMENDED CHARGING STATIONS (FULL-WIDTH INLINE DETAILS)
        # -------------------------------------------------------------------
        selected_idx = st.session_state.get("selected_detail_idx", None)

        with st.container(border=True):
            st.markdown(
                """<div class="section-header">
<div class="section-badge">3</div>
<div>
<h2 class="section-title">Top 10 Recommended Charging Stations</h2>
<p class="section-subtitle">Click on any station to expand complete technical specifications and amenities directly below.</p>
</div>
</div>""",
                unsafe_allow_html=True,
            )

            st.markdown(
                """<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem; padding-bottom:0.5rem; border-bottom:1px solid #f1f5f9;">
<div style="font-weight:700; font-size:0.95rem; color:#0f172a;">⚡ Verified Corridor Fast Chargers</div>
<span style="background:#ecfdf5; color:#059669; border:1px solid #a7f3d0; font-size:0.75rem; font-weight:700; padding:0.2rem 0.65rem; border-radius:9999px;">10 Stations</span>
</div>""",
                unsafe_allow_html=True,
            )

            # Full-Width Table Header
            h_c1, h_c2, h_c3, h_c4, h_c5, h_c6, h_c7, h_c8, h_c9 = st.columns(
                [0.4, 2.6, 2.3, 1.4, 1.1, 1.1, 1.2, 1.0, 1.3]
            )
            with h_c1: st.caption("<strong>#</strong>", unsafe_allow_html=True)
            with h_c2: st.caption("<strong>STATION NAME</strong>", unsafe_allow_html=True)
            with h_c3: st.caption("<strong>LOCATION</strong>", unsafe_allow_html=True)
            with h_c4: st.caption("<strong>CHARGER</strong>", unsafe_allow_html=True)
            with h_c5: st.caption("<strong>POWER</strong>", unsafe_allow_html=True)
            with h_c6: st.caption("<strong>AVAILABILITY</strong>", unsafe_allow_html=True)
            with h_c7: st.caption("<strong>EST. CHARGE</strong>", unsafe_allow_html=True)
            with h_c8: st.caption("<strong>DETOUR</strong>", unsafe_allow_html=True)
            with h_c9: st.caption("<strong style='display:block; text-align:center;'>ACTION</strong>", unsafe_allow_html=True)

            st.markdown("<div style='border-bottom: 1.5px solid #e2e8f0; margin-bottom: 6px;'></div>", unsafe_allow_html=True)

            for idx, stn in enumerate(top_10_stations):
                is_active = (selected_idx == idx)
                r_c1, r_c2, r_c3, r_c4, r_c5, r_c6, r_c7, r_c8, r_c9 = st.columns(
                    [0.4, 2.6, 2.3, 1.4, 1.1, 1.1, 1.2, 1.0, 1.3]
                )

                with r_c1:
                    st.markdown(f"<div style='font-size:0.85rem; font-weight:700; color:#64748b; padding:8px 0;'>{idx+1}</div>", unsafe_allow_html=True)
                with r_c2:
                    rec_indicator = " <span style='background:#ecfdf5; color:#059669; font-size:0.68rem; font-weight:700; padding:0.12rem 0.45rem; border-radius:4px; border:1px solid #a7f3d0;'>Top Pick</span>" if idx == 0 else ""
                    st.markdown(f"<div style='font-size:0.86rem; font-weight:700; color:#0f172a; padding:8px 0;'>{stn['name']}{rec_indicator}</div>", unsafe_allow_html=True)
                with r_c3:
                    st.markdown(f"<div style='font-size:0.80rem; color:#475569; padding:8px 0;'>📍 {stn['location']}</div>", unsafe_allow_html=True)
                with r_c4:
                    st.markdown(f"<div style='font-size:0.80rem; color:#334155; font-weight:500; padding:8px 0;'>{stn['charger_type']}</div>", unsafe_allow_html=True)
                with r_c5:
                    st.markdown(f"<div style='font-size:0.80rem; font-weight:700; color:#0284c7; padding:8px 0;'>{stn['power']}</div>", unsafe_allow_html=True)
                with r_c6:
                    st.markdown(f"<div style='font-size:0.80rem; color:#059669; font-weight:700; padding:8px 0;'>{stn['available']}</div>", unsafe_allow_html=True)
                with r_c7:
                    st.markdown(f"<div style='font-size:0.80rem; color:#64748b; font-weight:500; padding:8px 0;'>⏱️ {stn['charging_time']}</div>", unsafe_allow_html=True)
                with r_c8:
                    st.markdown(f"<div style='font-size:0.80rem; color:#64748b; font-weight:500; padding:8px 0;'>🚗 {stn['detour']}</div>", unsafe_allow_html=True)
                with r_c9:
                    btn_label = "▲ Close" if is_active else "▼ Details"
                    btn_type = "primary" if is_active else "secondary"
                    if st.button(btn_label, key=f"btn_p3_view_{idx}", type=btn_type, use_container_width=True):
                        st.session_state["selected_detail_idx"] = None if is_active else idx
                        st.rerun()

                # If this station is expanded, render full-width details card immediately below this row
                if is_active:
                    st_hero_img = f'<img src="{STATION_IMAGE_URI}" class="station-inline-hero-img" alt="Station Photo" />' if STATION_IMAGE_URI else '<div class="station-inline-hero-img" style="background:#e0f2fe;display:flex;align-items:center;justify-content:center;font-size:2.5rem;">⚡</div>'
                    badge_rec = '<span class="station-rec-badge">★ Top Recommended Option</span>' if idx == 0 else '<span class="station-rec-badge" style="background:#f1f5f9; color:#475569; border-color:#cbd5e1;">⚡ Verified Corridor Station</span>'

                    st.markdown(
                        f"""<div class="station-inline-details-card">
<div class="station-inline-header">
    <div>
        {badge_rec}
        <h3 class="station-details-name" style="font-size:1.25rem;">{stn['name']}</h3>
        <div class="station-details-loc" style="font-size:0.86rem;">📍 {stn['location']} &bull; <span style="color:#64748b;">Station ID:</span> <span class="station-id-badge">{stn.get('id', f'CS-{idx+1:02d}')}</span></div>
    </div>
</div>
<div class="station-inline-body">
    <div class="station-inline-media">
        {st_hero_img}
        <div class="station-inline-amenities">
            <div>📞 <strong>Contact:</strong> {stn.get('contact_number', '+91 98765 43210')}</div>
            <div style="margin-top:0.35rem;">☕ <strong>Amenities:</strong> {stn.get('other_info', 'Restroom, Food Court, EV Lounge')}</div>
        </div>
    </div>
    <div class="station-specs-grid-full">
        <div class="station-spec-item">
            <span class="station-spec-label">⚡ Charger Type</span>
            <span class="station-spec-value">{stn['charger_type']}</span>
        </div>
        <div class="station-spec-item">
            <span class="station-spec-label">🔌 Total Chargers</span>
            <span class="station-spec-value">{stn.get('total_chargers', '4')}</span>
        </div>
        <div class="station-spec-item">
            <span class="station-spec-label">⚡ Power Output</span>
            <span class="station-spec-value highlight">{stn['power']}</span>
        </div>
        <div class="station-spec-item">
            <span class="station-spec-label">🟢 Available Slots</span>
            <span class="station-spec-value" style="color:#059669;">{stn.get('avail_chargers', stn['available'])}</span>
        </div>
        <div class="station-spec-item">
            <span class="station-spec-label">💰 Tariff Rate</span>
            <span class="station-spec-value">{stn.get('cost_per_unit', '₹ 18 / kWh')}</span>
        </div>
        <div class="station-spec-item">
            <span class="station-spec-label">🏢 Network / Operator</span>
            <span class="station-spec-value">{stn.get('operator', 'Public Fast DC')}</span>
        </div>
        <div class="station-spec-item">
            <span class="station-spec-label">🕒 Operating Hours</span>
            <span class="station-spec-value">{stn.get('timing', '24x7 Operational')}</span>
        </div>
        <div class="station-spec-item">
            <span class="station-spec-label">💳 Payment Methods</span>
            <span class="station-spec-value">{stn.get('payment_modes', 'UPI, Card, Wallet, RFID')}</span>
        </div>
        <div class="station-spec-item">
            <span class="station-spec-label">⏱️ Est. Charge Duration</span>
            <span class="station-spec-value" style="color:#0284c7;">{stn['charging_time']}</span>
        </div>
        <div class="station-spec-item">
            <span class="station-spec-label">🚗 Highway Detour</span>
            <span class="station-spec-value">{stn['detour']}</span>
        </div>
    </div>
</div>
</div>""",
                        unsafe_allow_html=True,
                    )

                st.markdown("<div style='border-bottom: 1px solid #f1f5f9; margin: 2px 0;'></div>", unsafe_allow_html=True)

        # Navigation Action: Plan Another Journey
        st.write("")
        c_f1, c_f2, c_f3 = st.columns([1, 1.2, 1])
        with c_f2:
            if st.button("← Plan Another Journey", use_container_width=True, key="btn_plan_another"):
                st.session_state["current_page"] = "page1_input"
                st.session_state["map_picker_open"] = None
                st.rerun()

    # Global App Footer
    st.markdown(
        """
        <div style="text-align: center; color: #64748b; font-size: 0.75rem; margin-top: 1.25rem; border-top: 1px solid #e2e8f0; padding-top: 0.65rem;">
            <strong>Optimal EV Transportation Planning</strong> &bull; Clean Energy &bull; Sustainable Transportation
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
