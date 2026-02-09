import streamlit as st
import time
from datetime import datetime, timedelta

from config.constants import ZONE_MAPPING


def render(orders_df, drivers_df, runs_df):
    st.markdown('<div class="section-header">Route Planning & Optimization</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Create New Run")

        selected_zone = st.selectbox(
            "Select Zone",
            list(ZONE_MAPPING.keys())
        )

        zone_suburbs = ZONE_MAPPING.get(selected_zone, [])
        zone_orders = orders_df[
            (orders_df['suburb'].isin(zone_suburbs)) &
            (orders_df['status'] == 'pending')
        ]

        st.info(f"{len(zone_orders)} pending orders in {selected_zone}")

        selected_order_ids = st.multiselect(
            "Select orders for this run",
            zone_orders['order_id'].tolist(),
            default=zone_orders['order_id'].tolist()[:5] if len(zone_orders) > 0 else []
        )

        available_drivers = drivers_df[drivers_df['status'] == 'available']

        assigned_driver = st.selectbox(
            "Assign Driver",
            ["Auto-assign (nearest)"] + available_drivers['name'].tolist()
        )

        col_a, col_b = st.columns(2)
        with col_a:
            optimize_for = st.radio("Optimize for", ["Fastest route", "Shortest distance", "Time windows"])
        with col_b:
            priority = st.radio("Priority handling", ["Express first", "Standard order", "Balanced"])

        if st.button("Generate Optimized Route", use_container_width=True, type="primary"):
            with st.spinner("Calculating optimal route..."):
                time.sleep(1.5)
            st.success(f"Route optimized! {len(selected_order_ids)} stops")
            st.balloons()

    with col2:
        st.markdown("### Active Runs")

        active_runs = runs_df[runs_df['status'] == 'active']

        for _, run in active_runs.iterrows():
            progress_color = "#10b981" if run['progress'] > 70 else "#fbbf24" if run['progress'] > 40 else "#3b82f6"
            st.markdown(f"""
            <div class="order-card">
                <div class="order-id">{run['run_id']}</div>
                <div class="order-customer">{run['driver_name']}</div>
                <div class="order-address">{run['zone']} &bull; {run['completed']}/{run['total_stops']} stops</div>
                <div style="margin-top: 0.75rem; background: rgba(255,255,255,0.1); border-radius: 4px; height: 6px; overflow: hidden;">
                    <div style="background: {progress_color}; height: 100%; width: {run['progress']}%;"></div>
                </div>
                <div style="margin-top: 0.5rem; font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5);">
                    ETA completion: {run['estimated_completion']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Route visualization placeholder
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Route Preview")

    st.markdown("""
    <div class="zone-map" style="min-height: 300px;">
        <div style="position: relative; z-index: 1; text-align: center;">
            <div style="font-family: 'DM Sans', sans-serif; font-size: 1.25rem; color: white;">
                Route Visualization
            </div>
            <div style="margin-top: 1rem; font-family: 'Space Mono', monospace; font-size: 0.8rem; color: rgba(255,255,255,0.5);">
                Interactive map with turn-by-turn directions will appear here
            </div>
            <div style="margin-top: 1.5rem; display: flex; gap: 2rem; justify-content: center;">
                <div style="text-align: center;">
                    <div style="font-family: 'Space Mono', monospace; font-size: 1.5rem; color: #667eea;">12</div>
                    <div style="font-family: 'DM Sans', sans-serif; font-size: 0.75rem; color: rgba(255,255,255,0.5);">STOPS</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-family: 'Space Mono', monospace; font-size: 1.5rem; color: #10b981;">24.5 km</div>
                    <div style="font-family: 'DM Sans', sans-serif; font-size: 0.75rem; color: rgba(255,255,255,0.5);">DISTANCE</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-family: 'Space Mono', monospace; font-size: 1.5rem; color: #fbbf24;">2h 45m</div>
                    <div style="font-family: 'DM Sans', sans-serif; font-size: 0.75rem; color: rgba(255,255,255,0.5);">EST. TIME</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
