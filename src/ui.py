"""
UI Module for Optimal EV Transportation Planning.
Provides theme-adaptive styling, high-contrast typography, prominent metrics,
interactive comparison tables, stacked breakdown charts, and route maps.
"""

from typing import Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from src.charging_logic import CompleteTripPlan, StationPlanMetrics
from src.energy_logic import VehicleSpecs
from src.route_logic import RouteDetails


def format_duration(minutes: float) -> str:
    """
    Formats duration in minutes into a clean, human-readable string.
    Examples:
        48.0 -> '48 min'
        72.0 -> '1 hr 12 min'
        270.0 -> '4 hr 30 min'
        60.0 -> '1 hr'
    """
    if minutes is None or minutes == float("inf"):
        return "N/A"
    total_mins = int(round(minutes))
    if total_mins < 60:
        return f"{total_mins} min"
    hrs = total_mins // 60
    rem_mins = total_mins % 60
    if rem_mins == 0:
        return f"{hrs} hr"
    return f"{hrs} hr {rem_mins} min"


def inject_custom_css():
    """Injects modern, clean, light-mode EV styling with crisp high-contrast elements and strict Streamlit overrides."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        /* Force Root Light Mode Variables & Color Scheme */
        :root, [data-theme="dark"], [data-theme="light"] {
            --primary-color: #0284c7 !important;
            --background-color: #f8fafc !important;
            --secondary-background-color: #ffffff !important;
            --text-color: #0f172a !important;
            color-scheme: light !important;
        }

        /* Force Root Streamlit App Background & Text */
        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"], [data-testid="stMainBlockContainer"], .main, section.main, [data-testid="stVerticalBlock"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            background-color: #f8fafc !important;
            color: #0f172a !important;
        }

        header[data-testid="stHeader"] {
            background-color: #f8fafc !important;
        }

        /* General Typography */
        h1, h2, h3, h4, h5, h6, p, span, label, div {
            color: #0f172a;
        }

        /* Widget Labels & Subheaders */
        [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label, label[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] span {
            color: #1e293b !important;
            font-weight: 600 !important;
            font-size: 0.92rem !important;
        }

        h5, .stMarkdown h5 {
            color: #0f172a !important;
            font-weight: 700 !important;
            font-size: 1.1rem !important;
            margin-bottom: 0.75rem !important;
        }

        /* Dropdown Popover Menus (Mounted directly on body outside .stApp) */
        div[data-baseweb="popover"],
        div[data-baseweb="popover"] > div,
        div[data-baseweb="popover"] ul,
        ul[role="listbox"],
        ul[data-baseweb="menu"] {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1) !important;
        }

        li[role="option"],
        li[data-baseweb="menu-item"],
        li[role="option"] > div,
        li[data-baseweb="menu-item"] > div {
            background-color: #ffffff !important;
            color: #0f172a !important;
            font-size: 0.95rem !important;
        }

        li[role="option"]:hover,
        li[role="option"][aria-selected="true"],
        li[data-baseweb="menu-item"]:hover {
            background-color: #f1f5f9 !important;
            color: #0284c7 !important;
        }

        li[role="option"] *,
        li[data-baseweb="menu-item"] * {
            color: #0f172a !important;
        }

        li[role="option"]:hover *,
        li[data-baseweb="menu-item"]:hover * {
            color: #0284c7 !important;
        }

        /* Closed Select Boxes */
        div[data-baseweb="select"],
        div[data-baseweb="select"] > div,
        div[data-testid="stSelectbox"] > div,
        div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
        }

        div[data-baseweb="select"] div,
        div[data-baseweb="select"] span,
        div[data-baseweb="select"] p,
        div[data-testid="stSelectbox"] * {
            color: #0f172a !important;
        }

        div[data-baseweb="select"] svg {
            fill: #475569 !important;
            color: #475569 !important;
        }

        /* Number Inputs & Text Inputs */
        div[data-baseweb="input"],
        div[data-baseweb="input"] > div,
        div[data-baseweb="base-input"],
        div[data-testid="stNumberInput"] > div,
        div[data-testid="stNumberInputContainer"],
        input[type="number"],
        input[type="text"],
        input {
            background-color: #ffffff !important;
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }

        /* Number Input Step Buttons (+ and -) */
        button[data-testid="stNumberInputStepDown"],
        button[data-testid="stNumberInputStepUp"] {
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
        }

        button[data-testid="stNumberInputStepDown"] svg,
        button[data-testid="stNumberInputStepUp"] svg {
            fill: #0f172a !important;
            color: #0f172a !important;
        }

        button[data-testid="stNumberInputStepDown"]:hover,
        button[data-testid="stNumberInputStepUp"]:hover {
            background-color: #e2e8f0 !important;
        }

        /* Help Icons & Tooltips */
        div[data-testid="stTooltipHoverTarget"] svg,
        [data-testid="stWidgetLabel"] svg {
            fill: #64748b !important;
            color: #64748b !important;
        }

        div[data-baseweb="tooltip"],
        div[data-baseweb="tooltip"] > div {
            background-color: #1e293b !important;
            color: #ffffff !important;
            border-radius: 6px !important;
            font-size: 0.85rem !important;
        }

        /* Sliders */
        div[data-testid="stSlider"] {
            color: #0f172a !important;
        }

        div[data-testid="stSlider"] [data-testid="stThumbValue"] {
            color: #0284c7 !important;
            font-weight: 700 !important;
        }

        div[data-testid="stSlider"] [data-testid="stTickBarMin"],
        div[data-testid="stSlider"] [data-testid="stTickBarMax"],
        div[data-testid="stSlider"] span,
        div[data-testid="stSlider"] p {
            color: #64748b !important;
        }

        div[data-testid="stSlider"] div[role="slider"] {
            background-color: #0284c7 !important;
        }

        /* Dataframe / Tables */
        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
        }

        [data-testid="stDataFrame"] * {
            color: #0f172a !important;
        }

        /* Alerts & Banners */
        [data-testid="stAlert"] {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
            color: #0f172a !important;
        }

        [data-testid="stAlert"] p,
        [data-testid="stAlert"] span,
        [data-testid="stAlert"] div,
        [data-testid="stAlert"] strong {
            color: #0f172a !important;
        }

        [data-testid="stAlert"] code {
            background-color: #f1f5f9 !important;
            color: #0284c7 !important;
            padding: 0.15rem 0.4rem !important;
            border-radius: 4px !important;
            font-size: 0.9em !important;
        }

        /* Dividers */
        hr {
            border-color: #e2e8f0 !important;
            margin: 1.8rem 0 !important;
        }

        /* Top Header */
        .btp-header {
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 55%, #075985 100%);
            padding: 2rem 2.4rem;
            border-radius: 14px;
            color: #ffffff;
            margin-bottom: 1.6rem;
            box-shadow: 0 8px 24px -4px rgba(2, 132, 199, 0.25);
            border: 1px solid rgba(2, 132, 199, 0.2);
        }

        .btp-title {
            font-size: 2.1rem;
            font-weight: 800;
            color: #ffffff !important;
            margin: 0;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }

        .btp-subtitle {
            font-size: 1.05rem;
            color: #e0f2fe !important;
            margin-top: 0.4rem;
            margin-bottom: 0;
            font-weight: 400;
        }

        /* High-contrast Section Headings */
        .step-heading {
            font-size: 1.35rem;
            font-weight: 700;
            color: #0369a1 !important;
            margin-top: 1.6rem;
            margin-bottom: 0.9rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 0.4rem;
        }

        /* Light Mode Metric Cards */
        .metric-card-box {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.5rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03);
        }

        .metric-card-label {
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            margin-bottom: 0.25rem;
        }

        .metric-card-val {
            font-size: 1.45rem;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.2;
        }

        .metric-card-sub {
            font-size: 0.8rem;
            color: #0284c7;
            margin-top: 0.25rem;
            font-weight: 500;
        }

        /* Recommendation Highlight Container */
        .rec-hero-container {
            background: linear-gradient(145deg, #ecfdf5 0%, #f0fdf4 100%);
            border: 2px solid #10b981;
            border-radius: 14px;
            padding: 1.5rem 1.8rem;
            margin: 1.2rem 0;
            box-shadow: 0 10px 25px -5px rgba(16, 185, 129, 0.15);
        }

        .rec-hero-badge {
            display: inline-block;
            background: #10b981;
            color: #ffffff;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            padding: 0.25rem 0.85rem;
            border-radius: 9999px;
            margin-bottom: 0.6rem;
        }

        .rec-hero-title {
            font-size: 1.6rem;
            font-weight: 800;
            color: #065f46;
            margin: 0;
        }

        .rec-hero-sub {
            font-size: 0.95rem;
            color: #047857;
            font-weight: 500;
            margin-top: 0.25rem;
            margin-bottom: 1.2rem;
        }

        .formula-highlight-box {
            background: #ffffff;
            border: 1px solid #a7f3d0;
            border-radius: 8px;
            padding: 0.85rem 1.1rem;
            margin-top: 1.2rem;
            font-size: 0.92rem;
            color: #0f172a;
        }

        .formula-highlight-box code {
            color: #065f46;
            background: #f0fdf4;
            padding: 0.15rem 0.35rem;
            border-radius: 4px;
            font-size: 0.9em;
        }

        /* Action Button */
        div.stButton > button {
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            font-size: 1.05rem !important;
            padding: 0.65rem 2rem !important;
            border-radius: 8px !important;
            border: none !important;
            box-shadow: 0 4px 14px rgba(2, 132, 199, 0.25) !important;
            width: 100% !important;
        }

        div.stButton > button:hover {
            background: linear-gradient(135deg, #0369a1 0%, #075985 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 6px 18px rgba(2, 132, 199, 0.35) !important;
        }

        /* Footer */
        .btp-footer {
            text-align: center;
            font-size: 0.88rem;
            color: #64748b;
            padding: 2rem 0 1rem 0;
            border-top: 1px solid #e2e8f0;
            margin-top: 2.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    """Renders the clean application title and subtitle without Phase 1 badge."""
    st.markdown(
        """
        <div class="btp-header">
            <h1 class="btp-title">Optimal EV Transportation Planning</h1>
            <p class="btp-subtitle">Smart corridor routing, ML waiting-time estimation, and total journey time optimization</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_route_and_energy_analysis(
    route: RouteDetails, vehicle: VehicleSpecs, plan: CompleteTripPlan
):
    """
    Step 2: Route & Energy Analysis
    Displays clear cards for distance, travel time, SOC, energy required, and charging necessity.
    """
    st.markdown('<div class="step-heading">📊 2. Route & Energy Analysis</div>', unsafe_allow_html=True)

    energy_req_kwh = round(route.distance_km / vehicle.ev_efficiency_km_per_kwh, 2)
    travel_time_str = format_duration(route.base_travel_time_min)

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-label">🛣️ Route Corridor</div>
                <div class="metric-card-val" style="font-size: 1.15rem;">{route.source} → {route.destination}</div>
                <div class="metric-card-sub">{route.highway_name}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-label">📏 Total Distance</div>
                <div class="metric-card-val">{route.distance_km:.0f} <span style="font-size:0.85rem; font-weight:600;">km</span></div>
                <div class="metric-card-sub">Highway Corridor</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-label">⏱️ Travel Time</div>
                <div class="metric-card-val">{travel_time_str}</div>
                <div class="metric-card-sub">@ {route.avg_speed_kmh:.0f} km/h avg speed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-label">🔋 Initial Energy</div>
                <div class="metric-card-val">{vehicle.current_energy_kwh:.1f} <span style="font-size:0.85rem; font-weight:600;">kWh</span></div>
                <div class="metric-card-sub">~{vehicle.current_range_km:.0f} km ({vehicle.current_soc_pct:.0f}% SOC)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c5:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-label">⚡ Energy Required</div>
                <div class="metric-card-val">{energy_req_kwh:.1f} <span style="font-size:0.85rem; font-weight:600;">kWh</span></div>
                <div class="metric-card-sub">@ {vehicle.ev_efficiency_km_per_kwh:.1f} km/kWh</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Decision Banner
    if not plan.charging_required:
        arrival_range_km = max(0.0, (vehicle.current_energy_kwh - energy_req_kwh) * vehicle.ev_efficiency_km_per_kwh)
        st.success(
            f"✅ **Charging Required: NO**\n\n"
            f"{plan.explanation}\n\n"
            f"• Desired Destination Buffer: **{vehicle.desired_destination_km:.0f} km ({vehicle.desired_destination_soc_pct:.0f}% / {vehicle.desired_destination_energy_kwh:.1f} kWh)** | "
            f"Direct Arrival Range: **~{arrival_range_km:.0f} km ({vehicle.current_energy_kwh - energy_req_kwh:.1f} kWh)**"
        )
    else:
        req_charge_val = (
            plan.recommended_plan.required_charging_energy_kwh
            if plan.recommended_plan
            else plan.energy_deficit_kwh
        )
        req_charge_str = f"{req_charge_val:.1f} kWh (~{req_charge_val * vehicle.ev_efficiency_km_per_kwh:.0f} km)"
        est_time_str = (
            format_duration(plan.recommended_plan.charging_time_min)
            if plan.recommended_plan
            else "N/A"
        )
        st.info(
            f"⚠️ **Charging Required: YES**\n\n"
            f"{plan.explanation}\n\n"
            f"⚡ **Required Charging Energy:** `{req_charge_str}` | "
            f"⏱️ **Estimated Optimal Charging Time:** `{est_time_str}`"
        )


def render_station_comparison_section(plan: CompleteTripPlan):
    """
    Step 3: Charging Station Comparison
    Shows candidate stations sorted by Total Journey Time with the recommended station highlighted.
    Includes a clean Plotly stacked bar chart.
    """
    st.markdown('<div class="step-heading">🏢 3. Charging Station Comparison</div>', unsafe_allow_html=True)

    if not plan.all_station_plans:
        st.info("No charging stations configured along this corridor.")
        return

    # Sort candidates by Total Journey Time ascending (feasible first)
    sorted_all = sorted(
        plan.all_station_plans,
        key=lambda p: (not p.candidate.is_feasible, p.total_journey_time_min),
    )

    rec_id = plan.recommended_plan.candidate.station_id if plan.recommended_plan else None

    # Comparison Table
    table_rows = []
    for rank, p in enumerate(sorted_all, 1):
        c = p.candidate
        is_rec = (c.station_id == rec_id)

        if is_rec:
            rank_display = "⭐ BEST"
            station_display = f"⭐ {c.station_name} ({c.operator})"
        else:
            rank_display = f"#{rank}" if c.is_feasible else "—"
            station_display = f"{c.station_name} ({c.operator})"

        if c.is_feasible:
            j_time_display = format_duration(p.total_journey_time_min)
            c_time_display = format_duration(p.charging_time_min)
            w_time_display = format_duration(p.predicted_waiting_time_min)
            feasibility_display = "✅ Feasible"
        else:
            j_time_display = "Unreachable"
            c_time_display = "N/A"
            w_time_display = format_duration(p.predicted_waiting_time_min)
            feasibility_display = "❌ Safety SOC Breach"

        table_rows.append(
            {
                "Rank": rank_display,
                "Station Name & Network": station_display,
                "Charger Power": f"{c.charging_power_kw:.0f} kW",
                "Detour": f"{c.distance_from_route_km:.1f} km",
                "Available Slots": f"{c.available_slots} / {c.total_slots}",
                "Waiting Time": w_time_display,
                "Charging Time": c_time_display,
                "Total Journey Time": j_time_display,
                "Status": feasibility_display,
            }
        )

    df_comp = pd.DataFrame(table_rows)

    col_tbl, col_chart = st.columns([1.15, 0.85], gap="medium")

    with col_tbl:
        st.markdown("##### 📋 Candidate Station Rankings (Sorted by Total Journey Time)")
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

    with col_chart:
        st.markdown("##### ⏱️ Journey Time Breakdown (Stacked)")
        feasible_candidates = [p for p in sorted_all if p.candidate.is_feasible]

        if feasible_candidates:
            labels = [
                f"⭐ {p.candidate.station_name[:14]}..." if p.candidate.station_id == rec_id else f"{p.candidate.station_name[:14]}..."
                for p in feasible_candidates
            ]
            t_travel = [round(p.total_travel_time_min, 1) for p in feasible_candidates]
            t_wait = [round(p.predicted_waiting_time_min, 1) for p in feasible_candidates]
            t_charge = [round(p.charging_time_min, 1) for p in feasible_candidates]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=labels,
                x=t_travel,
                name="Travel Time",
                orientation="h",
                marker=dict(color="#0284c7"),
            ))
            fig.add_trace(go.Bar(
                y=labels,
                x=t_wait,
                name="Waiting Time",
                orientation="h",
                marker=dict(color="#f59e0b"),
            ))
            fig.add_trace(go.Bar(
                y=labels,
                x=t_charge,
                name="Charging Time",
                orientation="h",
                marker=dict(color="#10b981"),
            ))

            fig.update_layout(
                barmode="stack",
                margin=dict(l=10, r=10, t=10, b=10),
                height=300,
                xaxis_title="Minutes",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#334155")),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#334155"),
                xaxis=dict(gridcolor="#e2e8f0", zerolinecolor="#cbd5e1", title_font=dict(color="#334155")),
                yaxis=dict(gridcolor="#e2e8f0"),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.warning("No feasible stations to chart.")


def render_recommended_plan_section(plan: CompleteTripPlan):
    """
    Step 4: Recommended Charging Plan
    Displays the prominent recommended plan card with metrics and optimization formula.
    """
    st.markdown('<div class="step-heading">🎯 4. Recommended Charging Plan</div>', unsafe_allow_html=True)

    if not plan.charging_required:
        direct_time_str = format_duration(plan.direct_travel_time_min)
        st.success(
            f"💡 **Direct Route Recommended**: No intermediate charging stop is required for "
            f"**{plan.route.source} to {plan.route.destination}**.\n\n"
            f"Your total journey time is equal to direct travel time: **{direct_time_str}**."
        )
        return

    rec = plan.recommended_plan
    if not rec:
        st.error(
            "⚠️ **No Feasible Station Found**: Current battery SOC is insufficient to reach any candidate station "
            "with the required 10% safety buffer. Please start with a higher initial SOC."
        )
        return

    c = rec.candidate
    travel_time_str = format_duration(rec.total_travel_time_min)
    wait_time_str = format_duration(rec.predicted_waiting_time_min)
    charge_time_str = format_duration(rec.charging_time_min)
    total_journey_str = format_duration(rec.total_journey_time_min)

    # Hero card container
    st.markdown(
        f"""
        <div class="rec-hero-container">
            <span class="rec-hero-badge">★ Recommended Optimal Station</span>
            <div class="rec-hero-title">{c.station_name}</div>
            <div class="rec-hero-sub">Operated by {c.operator} &bull; {c.amenities}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 6 Metrics Columns
    m1, m2, m3, m4, m5, m6 = st.columns(6)

    with m1:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-label">⚡ Charger Spec</div>
                <div class="metric-card-val" style="font-size: 1.25rem;">{c.charging_power_kw:.0f} kW</div>
                <div class="metric-card-sub">{c.charger_type}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m2:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-label">🅿️ Available Slots</div>
                <div class="metric-card-val" style="font-size: 1.25rem;">{c.available_slots} <span style="font-size:0.8rem; font-weight:600;">/ {c.total_slots}</span></div>
                <div class="metric-card-sub">{c.distance_from_route_km:.1f} km off route</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m3:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-label">⏳ ML Waiting Time</div>
                <div class="metric-card-val" style="font-size: 1.25rem;">{wait_time_str}</div>
                <div class="metric-card-sub">Predicted Queue</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m4:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-label">🔋 Required Energy</div>
                <div class="metric-card-val" style="font-size: 1.25rem;">{rec.required_charging_energy_kwh:.1f} <span style="font-size:0.8rem; font-weight:600;">kWh</span></div>
                <div class="metric-card-sub">Charge to {rec.departure_soc_pct:.0f}% SOC</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m5:
        st.markdown(
            f"""
            <div class="metric-card-box">
                <div class="metric-card-label">⚡ Charging Time</div>
                <div class="metric-card-val" style="font-size: 1.25rem;">{charge_time_str}</div>
                <div class="metric-card-sub">@ {c.charging_power_kw:.0f} kW DC</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m6:
        st.markdown(
            f"""
            <div class="metric-card-box" style="border: 2px solid #10b981; background: #ecfdf5;">
                <div class="metric-card-label" style="color: #047857; font-weight: 700;">🏆 Total Journey Time</div>
                <div class="metric-card-val" style="color: #065f46; font-size: 1.25rem;">{total_journey_str}</div>
                <div class="metric-card-sub" style="color: #059669; font-weight: 600;">Minimum Total Duration</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Formula Breakdown
    st.markdown(
        f"""
        <div class="formula-highlight-box">
            <strong>Optimization Formula:</strong>
            <code>Total Journey Time = Travel Time ({travel_time_str}) + Waiting Time ({wait_time_str}) + Charging Time ({charge_time_str}) = <strong>{total_journey_str} ({rec.total_journey_time_min:.1f} min)</strong></code>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_map_section(plan: CompleteTripPlan):
    """
    Renders an interactive route map with source, destination, candidate stations, and recommendation.
    """
    st.markdown('<div class="step-heading">🗺️ Corridor & Station Map</div>', unsafe_allow_html=True)

    route = plan.route
    rec_id = plan.recommended_plan.candidate.station_id if plan.recommended_plan else None

    station_data = []
    for p in plan.all_station_plans:
        c = p.candidate
        is_rec = (c.station_id == rec_id)

        if is_rec:
            color = [16, 185, 129, 255]   # Vibrant Emerald
            radius = 2200
            status_text = "★ RECOMMENDED STATION"
        elif c.is_feasible:
            color = [2, 132, 199, 230]   # Sky Blue
            radius = 1400
            status_text = "Feasible Station"
        else:
            color = [239, 68, 68, 200]   # Rose Red
            radius = 1000
            status_text = "Safety SOC Breach"

        station_data.append({
            "name": c.station_name,
            "operator": c.operator,
            "power": f"{c.charging_power_kw:.0f} kW",
            "lat": c.latitude,
            "lon": c.longitude,
            "status": status_text,
            "journey_time": format_duration(p.total_journey_time_min) if c.is_feasible else "N/A",
            "color": color,
            "radius": radius,
        })

    endpoints = [
        {"name": f"Origin: {route.source}", "lat": route.source_lat, "lon": route.source_lon, "color": [15, 23, 42, 255], "radius": 2400},
        {"name": f"Destination: {route.destination}", "lat": route.dest_lat, "lon": route.dest_lon, "color": [225, 29, 72, 255], "radius": 2400},
    ]

    route_path = [
        {
            "path": [[route.source_lon, route.source_lat], [route.dest_lon, route.dest_lat]],
            "name": f"{route.source} to {route.destination}",
        }
    ]

    mid_lat = (route.source_lat + route.dest_lat) / 2.0
    mid_lon = (route.source_lon + route.dest_lon) / 2.0

    view_state = pdk.ViewState(
        latitude=mid_lat,
        longitude=mid_lon,
        zoom=7,
        pitch=15,
    )

    route_layer = pdk.Layer(
        "PathLayer",
        data=route_path,
        get_path="path",
        get_color=[2, 132, 199, 230],
        width_min_pixels=3,
        get_width=80,
    )

    stations_layer = pdk.Layer(
        "ScatterplotLayer",
        data=station_data,
        get_position=["lon", "lat"],
        get_color="color",
        get_radius="radius",
        pickable=True,
    )

    endpoints_layer = pdk.Layer(
        "ScatterplotLayer",
        data=endpoints,
        get_position=["lon", "lat"],
        get_color="color",
        get_radius="radius",
        pickable=True,
    )

    deck = pdk.Deck(
        layers=[route_layer, stations_layer, endpoints_layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>{name}</b><br/>{status}<br/>Operator: {operator}<br/>Power: {power}<br/>Total Time: {journey_time}",
            "style": {
                "backgroundColor": "#ffffff",
                "color": "#0f172a",
                "fontSize": "12px",
                "padding": "8px 10px",
                "borderRadius": "8px",
                "border": "1px solid #cbd5e1",
                "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.1)",
            },
        },
        map_style="light",
    )

    st.pydeck_chart(deck)


def render_footer():
    """Renders simple college BTP footer without Phase 1."""
    st.markdown(
        """
        <div class="btp-footer">
            <strong>Optimal EV Transportation Planning</strong> — BTP Prototype
        </div>
        """,
        unsafe_allow_html=True,
    )
