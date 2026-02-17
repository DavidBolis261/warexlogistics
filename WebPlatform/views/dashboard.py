import streamlit as st
import pandas as pd
import pydeck as pdk
from datetime import datetime

from config.constants import ZONE_MAPPING, SUBURB_COORDS
from utils.google_maps import geocode_address, get_route_polyline, decode_polyline


def render(orders_df, drivers_df, runs_df, data_manager=None):
    # Key Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)

    total_orders = len(orders_df) if not orders_df.empty else 0
    pending = len(orders_df[orders_df['status'] == 'pending']) if not orders_df.empty else 0
    in_transit = len(orders_df[orders_df['status'] == 'in_transit']) if not orders_df.empty else 0
    delivered = len(orders_df[orders_df['status'] == 'delivered']) if not orders_df.empty else 0
    delivery_rate = round(delivered / total_orders * 100) if total_orders > 0 else 0
    active_drivers = len(drivers_df[drivers_df['status'].isin(['available', 'on_route'])]) if not drivers_df.empty else 0

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_orders}</div>
            <div class="metric-label">Total Orders</div>
            <div class="metric-change positive">Today's orders</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{pending}</div>
            <div class="metric-label">Pending</div>
            <div class="metric-change negative">Needs attention</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{in_transit}</div>
            <div class="metric-label">In Transit</div>
            <div class="metric-change positive">On track</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{delivery_rate}%</div>
            <div class="metric-label">Delivered</div>
            <div class="metric-change positive">{delivered} completed</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{active_drivers}</div>
            <div class="metric-label">Active Drivers</div>
            <div class="metric-change positive">Online now</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Main content area
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown('<div class="section-header">Driver Location Map</div>', unsafe_allow_html=True)

        # Build map data from driver locations instead of orders
        if not drivers_df.empty:
            # Filter drivers with location data
            drivers_with_location = drivers_df[
                (drivers_df['latitude'].notna()) &
                (drivers_df['longitude'].notna())
            ]

            if not drivers_with_location.empty:
                map_data = []

                # Add each driver's location to the map
                for _, driver in drivers_with_location.iterrows():
                    lat = driver.get('latitude')
                    lng = driver.get('longitude')

                    if lat and lng:
                        # Color code by driver status
                        status = driver.get('status', 'available')
                        if status == 'available':
                            color = [16, 185, 129, 200]  # Green - available
                        elif status == 'on_route':
                            color = [59, 130, 246, 200]  # Blue - on route
                        elif status == 'busy':
                            color = [255, 165, 0, 200]  # Orange - busy
                        else:
                            color = [156, 163, 175, 200]  # Gray - offline

                        # Get driver stats
                        active_orders = driver.get('active_orders', 0)
                        deliveries_today = driver.get('deliveries_today', 0)

                        map_data.append({
                            'lat': lat,
                            'lng': lng,
                            'driver_id': driver.get('driver_id', ''),
                            'driver_name': driver.get('name', 'Unknown'),
                            'vehicle': f"{driver.get('vehicle_type', '')} - {driver.get('plate', '')}",
                            'status': status,
                            'active_orders': active_orders,
                            'deliveries_today': deliveries_today,
                            'color': color,
                            'size': 150
                        })

                if map_data:
                    # Create DataFrame
                    map_df = pd.DataFrame(map_data)

                    # Calculate center point
                    center_lat = map_df['lat'].mean()
                    center_lng = map_df['lng'].mean()

                    # Create pydeck layer for markers
                    layer = pdk.Layer(
                        'ScatterplotLayer',
                        data=map_df,
                        get_position='[lng, lat]',
                        get_color='color',
                        get_radius='size',
                        pickable=True,
                        auto_highlight=True,
                    )

                    # Define view state
                    view_state = pdk.ViewState(
                        latitude=center_lat,
                        longitude=center_lng,
                        zoom=11,
                        pitch=0,
                    )

                    # Tooltip for drivers
                    tooltip = {
                        "html": "<b>🚚 {driver_name}</b><br/>{vehicle}<br/>Status: {status}<br/>Active Orders: {active_orders}<br/>Deliveries Today: {deliveries_today}",
                        "style": {
                            "backgroundColor": "rgba(0,0,0,0.8)",
                            "color": "white",
                            "fontSize": "12px",
                            "padding": "10px"
                        }
                    }

                    # Render the map (without mapbox to avoid token requirement)
                    r = pdk.Deck(
                        layers=[layer],
                        initial_view_state=view_state,
                        tooltip=tooltip,
                        map_style=pdk.map_styles.CARTO_DARK,
                    )

                    st.pydeck_chart(r, use_container_width=True)

                    # Legend
                    st.markdown("""
                    <div style="display: flex; gap: 1rem; margin-top: 0.5rem; font-size: 0.85rem;">
                        <div><span style="color: #10b981;">●</span> Available</div>
                        <div><span style="color: #3b82f6;">●</span> On Route</div>
                        <div><span style="color: #ffa500;">●</span> Busy</div>
                        <div><span style="color: #9ca3af;">●</span> Offline</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Driver location detail — click a driver to see their location
                    st.markdown("---")
                    st.markdown("**📍 View Driver Location**")
                    driver_names = [d['driver_name'] for d in map_data]
                    selected_driver_name = st.selectbox(
                        "Select a driver to view their location",
                        ["— select —"] + driver_names,
                        key="dashboard_driver_select",
                        label_visibility="collapsed",
                    )
                    if selected_driver_name and selected_driver_name != "— select —":
                        selected = next((d for d in map_data if d['driver_name'] == selected_driver_name), None)
                        if selected:
                            lat = selected['lat']
                            lng = selected['lng']
                            maps_url = f"https://www.google.com/maps?q={lat},{lng}"
                            updated_at = drivers_with_location[
                                drivers_with_location['name'] == selected_driver_name
                            ]['location_updated_at'].values
                            updated_str = str(updated_at[0])[:19].replace('T', ' ') if len(updated_at) > 0 else 'Unknown'
                            st.markdown(f"""
<div style="background: rgba(255,255,255,0.05); border-radius: 10px; padding: 14px; margin-top: 8px;">
    <b>🚚 {selected['driver_name']}</b><br>
    <span style="color: rgba(255,255,255,0.6);">{selected['vehicle']}</span><br><br>
    📍 <b>Coordinates:</b> {lat:.5f}, {lng:.5f}<br>
    🕐 <b>Last updated:</b> {updated_str}<br><br>
    <a href="{maps_url}" target="_blank" style="background:#667eea; color:white; padding:6px 14px; border-radius:6px; text-decoration:none; font-size:0.85rem;">
        Open in Google Maps →
    </a>
</div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No driver location data available.")
            else:
                st.info("No drivers currently sharing their location.")
        else:
            st.info("No drivers registered. Add drivers to see their locations on the map.")

        # Zone summary cards with real data
        zone_colors = {
            "Inner West": ("#10b981", "rgba(16, 185, 129, 0.2)", "rgba(16, 185, 129, 0.3)"),
            "Eastern Suburbs": ("#fbbf24", "rgba(251, 191, 36, 0.2)", "rgba(251, 191, 36, 0.3)"),
            "CBD": ("#667eea", "rgba(102, 126, 234, 0.2)", "rgba(102, 126, 234, 0.3)"),
            "South Sydney": ("#ef4444", "rgba(239, 68, 68, 0.2)", "rgba(239, 68, 68, 0.3)"),
            "Inner City": ("#8b5cf6", "rgba(139, 92, 246, 0.2)", "rgba(139, 92, 246, 0.3)"),
        }

        # zone_names = list(ZONE_MAPPING.keys())
        # zone_cols = st.columns(len(zone_names))
        # for idx, zone_name in enumerate(zone_names):
        #     suburbs = ZONE_MAPPING[zone_name]
        #     active_count = 0
        #     if not orders_df.empty and 'suburb' in orders_df.columns:
        #         active_count = len(orders_df[
        #             (orders_df['suburb'].isin(suburbs)) &
        #             (orders_df['status'].isin(['pending', 'allocated', 'in_transit']))
        #         ])
        #     color, bg, border = zone_colors.get(zone_name, ("#667eea", "rgba(102, 126, 234, 0.2)", "rgba(102, 126, 234, 0.3)"))
        #     with zone_cols[idx]:
        #         st.markdown(f"""
        #         <div style="background: {bg}; padding: 0.75rem 1.25rem; border-radius: 8px; border: 1px solid {border}; text-align: center;">
        #             <div style="font-family: 'Space Mono', monospace; color: {color}; font-weight: 700; font-size: 0.85rem;">{zone_name}</div>
        #             <div style="font-family: 'DM Sans', sans-serif; color: rgba(255,255,255,0.6); font-size: 0.8rem;">{active_count} active</div>
        #         </div>
        #         """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Active Runs
        st.markdown('<div class="section-header">Active Delivery Runs</div>', unsafe_allow_html=True)

        if runs_df.empty:
            st.info("No active runs. Create one in Route Planning.")
        else:
            active_runs = runs_df[runs_df['status'] == 'active'].head(5) if 'status' in runs_df.columns else runs_df.head(5)

            if active_runs.empty:
                st.info("No active runs at the moment.")
            else:
                for _, run in active_runs.iterrows():
                    progress = run.get('progress', 0)
                    progress_color = "#10b981" if progress > 70 else "#fbbf24" if progress > 40 else "#3b82f6"
                    completed = run.get('completed', 0)
                    total_stops = run.get('total_stops', 0)
                    st.markdown(f"""
                    <div class="order-card">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <div class="order-id">{run['run_id']}</div>
                                <div class="order-customer">{run.get('driver_name', 'Unassigned')} &bull; {run.get('zone', '')}</div>
                                <div class="order-address">{completed}/{total_stops} stops</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-family: 'Space Mono', monospace; font-size: 1.5rem; color: {progress_color}; font-weight: 700;">{int(progress)}%</div>
                            </div>
                        </div>
                        <div style="margin-top: 0.75rem; background: rgba(255,255,255,0.1); border-radius: 4px; height: 6px; overflow: hidden;">
                            <div style="background: {progress_color}; height: 100%; width: {progress}%; border-radius: 4px;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-header">Pending Orders</div>', unsafe_allow_html=True)

        if orders_df.empty:
            st.info("No orders yet. Create your first order.")
        else:
            pending_orders = orders_df[orders_df['status'] == 'pending'].head(6)

            if pending_orders.empty:
                st.info("No pending orders.")
            else:
                for _, order in pending_orders.iterrows():
                    priority_class = f"priority-{order['service_level']}"
                    created_str = ''
                    if hasattr(order.get('created_at'), 'strftime'):
                        created_str = order['created_at'].strftime('%H:%M')
                    st.markdown(f"""
                    <div class="order-card {priority_class}">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <div class="order-id">{order['order_id']}</div>
                                <div class="order-customer">{order['customer']}</div>
                                <div class="order-address">{order['address']}, {order['suburb']} {order['postcode']}</div>
                            </div>
                            <span class="status-badge status-pending">{order['service_level']}</span>
                        </div>
                        <div style="margin-top: 0.75rem; font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5);">
                            {order['parcels']} parcel(s) {('&bull; ' + created_str) if created_str else ''}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Driver Status</div>', unsafe_allow_html=True)

        if drivers_df.empty:
            st.info("No drivers registered. Add drivers in the Drivers page.")
        else:
            for _, driver in drivers_df.head(5).iterrows():
                status_class = f"status-{driver['status'].replace('_', '-')}"
                st.markdown(f"""
                <div class="driver-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div class="driver-name">{driver['name']}</div>
                            <div class="driver-vehicle">{driver['vehicle_type']} &bull; {driver['plate']}</div>
                        </div>
                        <span class="status-badge {status_class}">{driver['status'].replace('_', ' ')}</span>
                    </div>
                    <div class="driver-stats">
                        <div class="driver-stat">
                            <div class="driver-stat-value">{driver['deliveries_today']}</div>
                            <div class="driver-stat-label">Today</div>
                        </div>
                        <div class="driver-stat">
                            <div class="driver-stat-value">{driver['active_orders']}</div>
                            <div class="driver-stat-label">Active</div>
                        </div>
                        <div class="driver-stat">
                            <div class="driver-stat-value">{driver['rating']}</div>
                            <div class="driver-stat-label">Rating</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
