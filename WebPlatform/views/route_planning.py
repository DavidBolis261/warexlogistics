import streamlit as st
import pandas as pd
import pydeck as pdk
from datetime import datetime

from config.constants import ZONE_MAPPING, SUBURB_COORDS
from utils.google_maps import geocode_address, get_route_polyline, decode_polyline


def render(orders_df, drivers_df, runs_df, data_manager):
    st.markdown('<div class="section-header">Route Planning & Runs</div>', unsafe_allow_html=True)

    # Route Visualization Section
    if not runs_df.empty:
        active_runs = runs_df[runs_df['status'] == 'active'] if 'status' in runs_df.columns else runs_df

        if not active_runs.empty:
            st.markdown("### Active Routes Map")

            # Select a run to visualize
            run_options = (
                active_runs['run_id'].astype(str) + ' - ' +
                active_runs['driver_name'].fillna('Unassigned') + ' (' +
                active_runs['zone'].fillna('') + ')'
            ).tolist()

            selected_run_display = st.selectbox("Select Run to Visualize", run_options, key="route_viz_select")

            if selected_run_display:
                # Extract run_id from selection
                selected_run_id = selected_run_display.split(' - ')[0]
                run_row = active_runs[active_runs['run_id'] == selected_run_id].iloc[0]

                # Get orders for this run
                run_orders = orders_df[
                    (orders_df['status'].isin(['allocated', 'in_transit'])) &
                    (orders_df['driver_id'] == run_row['driver_id'])
                ] if not orders_df.empty else pd.DataFrame()

                if not run_orders.empty:
                    # Geocode all stops
                    waypoints = []
                    map_markers = []

                    for idx, order in run_orders.iterrows():
                        address = order.get('address', '')
                        suburb = order.get('suburb', '')
                        state = order.get('state', 'NSW')
                        postcode = order.get('postcode', '')

                        # Geocode
                        coords = geocode_address(address, suburb, state, postcode)

                        # Fallback to suburb coords
                        if not coords and suburb in SUBURB_COORDS:
                            coords = SUBURB_COORDS[suburb]

                        if coords:
                            lat, lng = coords
                            waypoints.append({'lat': lat, 'lng': lng})

                            # Add marker
                            map_markers.append({
                                'lat': lat,
                                'lng': lng,
                                'order_id': order.get('order_id', ''),
                                'customer': order.get('customer', ''),
                                'address': f"{address}, {suburb} {postcode}",
                                'stop_number': len(waypoints),
                                'color': [16, 185, 129, 200],  # Green
                                'size': 120
                            })

                    if waypoints and len(waypoints) >= 2:
                        # Get route polyline from Google
                        polyline = get_route_polyline(waypoints)
                        route_coords = []

                        if polyline:
                            # Decode polyline into coordinates
                            route_coords = decode_polyline(polyline)

                        # Create map layers
                        layers = []

                        # Route line layer
                        if route_coords:
                            route_df = pd.DataFrame([
                                {'lat': lat, 'lng': lng} for lat, lng in route_coords
                            ])

                            # Create path layer
                            path_layer = pdk.Layer(
                                'PathLayer',
                                data=[{'path': [[lng, lat] for lat, lng in route_coords]}],
                                get_path='path',
                                get_color=[59, 130, 246, 200],  # Blue
                                width_scale=20,
                                width_min_pixels=3,
                                pickable=False,
                            )
                            layers.append(path_layer)

                        # Markers layer
                        if map_markers:
                            markers_df = pd.DataFrame(map_markers)

                            marker_layer = pdk.Layer(
                                'ScatterplotLayer',
                                data=markers_df,
                                get_position='[lng, lat]',
                                get_color='color',
                                get_radius='size',
                                pickable=True,
                                auto_highlight=True,
                            )
                            layers.append(marker_layer)

                            # Text layer for stop numbers
                            text_layer = pdk.Layer(
                                'TextLayer',
                                data=markers_df,
                                get_position='[lng, lat]',
                                get_text='stop_number',
                                get_color=[255, 255, 255, 255],
                                get_size=16,
                                get_alignment_baseline="'center'",
                                pickable=False,
                            )
                            layers.append(text_layer)

                            # Calculate center
                            center_lat = markers_df['lat'].mean()
                            center_lng = markers_df['lng'].mean()

                            # View state
                            view_state = pdk.ViewState(
                                latitude=center_lat,
                                longitude=center_lng,
                                zoom=12,
                                pitch=0,
                            )

                            # Tooltip
                            tooltip = {
                                "html": "<b>Stop #{stop_number}</b><br/><b>{order_id}</b><br/>{customer}<br/>{address}",
                                "style": {
                                    "backgroundColor": "rgba(0,0,0,0.8)",
                                    "color": "white",
                                    "fontSize": "12px",
                                    "padding": "10px"
                                }
                            }

                            # Render map (without mapbox to avoid token requirement)
                            r = pdk.Deck(
                                layers=layers,
                                initial_view_state=view_state,
                                tooltip=tooltip,
                                map_style=pdk.map_styles.CARTO_DARK,
                            )

                            st.pydeck_chart(r, use_container_width=True)

                            # Route summary
                            st.markdown(f"""
                            <div style="margin-top: 0.5rem; padding: 1rem; background: rgba(16, 185, 129, 0.1); border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.3);">
                                <strong>Route Summary:</strong> {len(waypoints)} stops for {run_row.get('driver_name', 'Driver')} in {run_row.get('zone', 'Unknown Zone')}
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.warning("Unable to geocode addresses for this run.")
                    else:
                        st.info(f"No valid stops found for this run. Make sure orders have valid addresses.")
                else:
                    st.info("No orders allocated to this run yet.")

            st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Create New Run")

        selected_zone = st.selectbox(
            "Select Zone",
            list(ZONE_MAPPING.keys())
        )

        zone_suburbs = ZONE_MAPPING.get(selected_zone, [])

        if not orders_df.empty and 'suburb' in orders_df.columns:
            zone_orders = orders_df[
                (orders_df['suburb'].isin(zone_suburbs)) &
                (orders_df['status'] == 'pending')
            ]
        else:
            zone_orders = orders_df.iloc[0:0]  # empty DataFrame

        st.info(f"{len(zone_orders)} pending orders in {selected_zone}")

        if zone_orders.empty:
            st.warning("No pending orders in this zone. Create orders first or select a different zone.")
        else:
            selected_order_ids = st.multiselect(
                "Select orders for this run",
                zone_orders['order_id'].tolist(),
                default=zone_orders['order_id'].tolist()[:5] if len(zone_orders) > 0 else []
            )

            # Driver selection
            if not drivers_df.empty:
                available_drivers = drivers_df[drivers_df['status'] == 'available']
                if available_drivers.empty:
                    st.warning("No available drivers. Update driver status first.")
                    driver_options = drivers_df['name'].tolist()
                else:
                    driver_options = available_drivers['name'].tolist()
            else:
                driver_options = []
                st.warning("No drivers registered. Add drivers first.")

            if driver_options:
                assigned_driver = st.selectbox("Assign Driver", driver_options)

                # Show selected orders summary
                if selected_order_ids:
                    st.markdown(f"**Run Summary:** {len(selected_order_ids)} stops for {assigned_driver} in {selected_zone}")

                    # Show the selected orders
                    selected_details = zone_orders[zone_orders['order_id'].isin(selected_order_ids)]
                    for _, order in selected_details.iterrows():
                        st.markdown(f"""
                        <div style="padding: 0.5rem; margin: 0.25rem 0; background: rgba(255,255,255,0.05); border-radius: 6px; font-size: 0.85rem;">
                            <strong>{order['order_id']}</strong> &bull; {order['customer']} &bull; {order['address']}, {order['suburb']}
                        </div>
                        """, unsafe_allow_html=True)

                if st.button("Create Run", use_container_width=True, type="primary",
                             disabled=not selected_order_ids):
                    if not selected_order_ids:
                        st.error("Select at least one order for the run.")
                    else:
                        # Get driver_id
                        driver_row = drivers_df[drivers_df['name'] == assigned_driver]
                        driver_id = driver_row.iloc[0]['driver_id'] if not driver_row.empty else assigned_driver

                        result = data_manager.create_run(
                            zone=selected_zone,
                            driver_id=driver_id,
                            driver_name=assigned_driver,
                            order_ids=selected_order_ids,
                        )
                        if result.get('success'):
                            st.success(f"Run {result['run_id']} created with {len(selected_order_ids)} stops assigned to {assigned_driver}")
                            st.rerun()
                        else:
                            st.error("Failed to create run.")

    with col2:
        st.markdown("### Active Runs")

        if runs_df.empty:
            st.info("No runs yet. Create your first run.")
        else:
            active_runs = runs_df[runs_df['status'] == 'active'] if 'status' in runs_df.columns else runs_df

            if active_runs.empty:
                st.info("No active runs.")
            else:
                for _, run in active_runs.iterrows():
                    progress = run.get('progress', 0)
                    progress_color = "#10b981" if progress > 70 else "#fbbf24" if progress > 40 else "#3b82f6"
                    completed = run.get('completed', 0)
                    total_stops = run.get('total_stops', 0)

                    st.markdown(f"""
                    <div class="order-card">
                        <div class="order-id">{run['run_id']}</div>
                        <div class="order-customer">{run.get('driver_name', 'Unassigned')}</div>
                        <div class="order-address">{run.get('zone', '')} &bull; {completed}/{total_stops} stops</div>
                        <div style="margin-top: 0.75rem; background: rgba(255,255,255,0.1); border-radius: 4px; height: 6px; overflow: hidden;">
                            <div style="background: {progress_color}; height: 100%; width: {progress}%;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Action buttons per run
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button("+ Stop", key=f"stop_{run['run_id']}",
                                     use_container_width=True,
                                     disabled=completed >= total_stops):
                            data_manager.update_run_progress(run['run_id'], completed + 1)
                            st.rerun()
                    with col_b:
                        if st.button("Complete", key=f"complete_{run['run_id']}",
                                     use_container_width=True):
                            data_manager.complete_run(run['run_id'])
                            st.success(f"Run {run['run_id']} completed!")
                            st.rerun()
                    with col_c:
                        if st.button("Cancel", key=f"cancel_run_{run['run_id']}",
                                     use_container_width=True):
                            data_manager.cancel_run(run['run_id'])
                            st.info(f"Run {run['run_id']} cancelled. Orders reverted to pending.")
                            st.rerun()

    # Completed / Cancelled Runs
    if not runs_df.empty and 'status' in runs_df.columns:
        past_runs = runs_df[runs_df['status'].isin(['completed', 'cancelled'])]
        if not past_runs.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### Past Runs")

            for _, run in past_runs.head(10).iterrows():
                status_color = "#10b981" if run['status'] == 'completed' else "#ef4444"
                st.markdown(f"""
                <div class="order-card">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <div class="order-id">{run['run_id']}</div>
                            <div class="order-customer">{run.get('driver_name', '')} &bull; {run.get('zone', '')}</div>
                            <div class="order-address">{run.get('completed', 0)}/{run.get('total_stops', 0)} stops</div>
                        </div>
                        <span class="status-badge" style="color: {status_color};">{run['status']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
