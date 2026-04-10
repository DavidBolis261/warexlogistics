import streamlit as st
import pandas as pd

from config.constants import ZONES, VEHICLE_TYPES


def render(drivers_df, data_manager, orders_df=None):
    st.markdown('<div class="section-header">Driver Management</div>', unsafe_allow_html=True)

    # Driver stats summary
    col1, col2, col3, col4 = st.columns(4)

    if not drivers_df.empty:
        available = len(drivers_df[drivers_df['status'] == 'available'])
        on_route = len(drivers_df[drivers_df['status'] == 'on_route'])
        offline = len(drivers_df[drivers_df['status'] == 'offline'])
        total_deliveries = int(drivers_df['deliveries_today'].sum())
    else:
        available = on_route = offline = total_deliveries = 0

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #10b981;">{available}</div>
            <div class="metric-label">Available</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #3b82f6;">{on_route}</div>
            <div class="metric-label">On Route</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #6b7280;">{offline}</div>
            <div class="metric-label">Offline</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_deliveries}</div>
            <div class="metric-label">Total Deliveries</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Driver cards with edit/delete
    if drivers_df.empty:
        st.info("No drivers registered yet. Add your first driver below.")
    else:
        editing_driver = st.session_state.get('editing_driver', None)

        for idx, (_, driver) in enumerate(drivers_df.iterrows()):
            driver_id = driver['driver_id']
            status_class = f"status-{driver['status'].replace('_', '-')}"

            # Check if we're editing this driver
            if editing_driver == driver_id:
                _render_edit_form(driver, data_manager)
                continue

            with st.container():
                col_info, col_actions = st.columns([5, 1])

                with col_info:
                    success_pct = int(driver['success_rate'] * 100) if driver['success_rate'] <= 1 else int(driver['success_rate'])
                    st.markdown(f"""
                    <div class="driver-card">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <div class="driver-name">{driver['name']}</div>
                                <div class="driver-vehicle">{driver_id} &bull; {driver['vehicle_type']} &bull; {driver['plate']}</div>
                                <div style="font-family: 'DM Sans', sans-serif; font-size: 0.85rem; color: rgba(255,255,255,0.5); margin-top: 0.25rem;">
                                    {driver['current_zone']} &bull; {driver['phone']}
                                </div>
                            </div>
                            <span class="status-badge {status_class}">{driver['status'].replace('_', ' ')}</span>
                        </div>
                        <div class="driver-stats">
                            <div class="driver-stat">
                                <div class="driver-stat-value">{driver['deliveries_today']}</div>
                                <div class="driver-stat-label">Deliveries</div>
                            </div>
                            <div class="driver-stat">
                                <div class="driver-stat-value">{driver['active_orders']}</div>
                                <div class="driver-stat-label">Active</div>
                            </div>
                            <div class="driver-stat">
                                <div class="driver-stat-value">{success_pct}%</div>
                                <div class="driver-stat-label">Success</div>
                            </div>
                            <div class="driver-stat">
                                <div class="driver-stat-value">{driver['rating']}</div>
                                <div class="driver-stat-label">Rating</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_actions:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("View Orders", key=f"view_{driver_id}", use_container_width=True):
                        current_view = st.session_state.get('viewing_driver_orders', None)
                        if current_view == driver_id:
                            st.session_state.pop('viewing_driver_orders', None)
                        else:
                            st.session_state['viewing_driver_orders'] = driver_id
                            st.session_state.pop('viewing_driver_history', None)
                        st.rerun()
                    if st.button("📍 Location History", key=f"hist_{driver_id}", use_container_width=True):
                        current_hist = st.session_state.get('viewing_driver_history', None)
                        if current_hist == driver_id:
                            st.session_state.pop('viewing_driver_history', None)
                        else:
                            st.session_state['viewing_driver_history'] = driver_id
                            st.session_state.pop('viewing_driver_orders', None)
                        st.rerun()
                    if st.button("Edit", key=f"edit_{driver_id}", use_container_width=True):
                        st.session_state['editing_driver'] = driver_id
                        st.rerun()
                    if st.button("Delete", key=f"del_{driver_id}", use_container_width=True):
                        st.session_state['confirm_delete_driver'] = driver_id
                        st.rerun()

            # Show driver's orders if viewing
            if st.session_state.get('viewing_driver_orders') == driver_id and orders_df is not None:
                _render_driver_orders(driver, orders_df)

            # Show driver's location history if requested
            if st.session_state.get('viewing_driver_history') == driver_id:
                _render_location_history(driver, data_manager)

            # Confirm delete dialog
            if st.session_state.get('confirm_delete_driver') == driver_id:
                st.warning(f"Are you sure you want to delete driver **{driver['name']}** ({driver_id})?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("Yes, Delete", key=f"confirm_del_{driver_id}", type="primary", use_container_width=True):
                        data_manager.delete_driver(driver_id)
                        st.session_state.pop('confirm_delete_driver', None)
                        st.success(f"Driver {driver['name']} deleted.")
                        st.rerun()
                with col_no:
                    if st.button("Cancel", key=f"cancel_del_{driver_id}", use_container_width=True):
                        st.session_state.pop('confirm_delete_driver', None)
                        st.rerun()

    # Add new driver section
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Add New Driver</div>', unsafe_allow_html=True)

    with st.form("new_driver_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            new_name = st.text_input("Driver Name *")
            new_phone = st.text_input("Phone Number")

        with col2:
            new_vehicle = st.selectbox("Vehicle Type", VEHICLE_TYPES)
            new_plate = st.text_input("License Plate")

        with col3:
            new_zone = st.selectbox("Primary Zone", ZONES)
            new_status = st.selectbox("Status", ["available", "on_route", "offline"])

        submitted = st.form_submit_button("Add Driver", use_container_width=True, type="primary")
        if submitted:
            if not new_name:
                st.error("Driver name is required.")
            else:
                result = data_manager.add_driver({
                    'name': new_name,
                    'phone': new_phone,
                    'vehicle_type': new_vehicle,
                    'plate': new_plate,
                    'current_zone': new_zone,
                    'status': new_status,
                })
                st.success(f"Driver {new_name} added as {result.get('driver_id', '')}!")
                st.rerun()


def _render_edit_form(driver, data_manager):
    """Render an inline edit form for a driver."""
    driver_id = driver['driver_id']

    st.markdown(f"### Editing: {driver['name']} ({driver_id})")

    with st.form(f"edit_driver_form_{driver_id}"):
        col1, col2, col3 = st.columns(3)

        with col1:
            edit_name = st.text_input("Driver Name", value=driver['name'])
            edit_phone = st.text_input("Phone Number", value=driver.get('phone', ''))

        with col2:
            vt_options = VEHICLE_TYPES
            vt_index = vt_options.index(driver['vehicle_type']) if driver['vehicle_type'] in vt_options else 0
            edit_vehicle = st.selectbox("Vehicle Type", vt_options, index=vt_index)
            edit_plate = st.text_input("License Plate", value=driver.get('plate', ''))

        with col3:
            zone_index = ZONES.index(driver['current_zone']) if driver['current_zone'] in ZONES else 0
            edit_zone = st.selectbox("Primary Zone", ZONES, index=zone_index)
            status_options = ["available", "on_route", "offline"]
            status_index = status_options.index(driver['status']) if driver['status'] in status_options else 0
            edit_status = st.selectbox("Status", status_options, index=status_index)

        col_save, col_cancel = st.columns(2)
        with col_save:
            save_btn = st.form_submit_button("Save Changes", use_container_width=True, type="primary")
        with col_cancel:
            cancel_btn = st.form_submit_button("Cancel", use_container_width=True)

        if save_btn:
            data_manager.update_driver(driver_id, {
                'name': edit_name,
                'phone': edit_phone,
                'vehicle_type': edit_vehicle,
                'plate': edit_plate,
                'current_zone': edit_zone,
                'status': edit_status,
            })
            st.session_state.pop('editing_driver', None)
            st.success(f"Driver {edit_name} updated!")
            st.rerun()

        if cancel_btn:
            st.session_state.pop('editing_driver', None)
            st.rerun()


def _render_driver_orders(driver, orders_df):
    """Render all orders for a specific driver."""
    driver_id = driver['driver_id']
    driver_name = driver['name']

    # Get all orders for this driver
    driver_orders = orders_df[orders_df['driver_id'] == driver_id] if not orders_df.empty else pd.DataFrame()

    with st.container():
        st.markdown(f"""
        <div style="margin: 1rem 0; padding: 1.25rem; background: rgba(59, 130, 246, 0.1); border-radius: 12px; border: 1px solid rgba(59, 130, 246, 0.3);">
            <div style="font-family: 'Space Mono', monospace; font-size: 1rem; font-weight: 700; color: #3b82f6; margin-bottom: 0.75rem;">
                📦 Orders for {driver_name}
            </div>
        """, unsafe_allow_html=True)

        if driver_orders.empty:
            st.info(f"No orders assigned to {driver_name} yet.")
        else:
            # Group orders by status
            status_groups = {
                'pending': driver_orders[driver_orders['status'] == 'pending'],
                'allocated': driver_orders[driver_orders['status'] == 'allocated'],
                'in_transit': driver_orders[driver_orders['status'] == 'in_transit'],
                'delivered': driver_orders[driver_orders['status'] == 'delivered'],
                'failed': driver_orders[driver_orders['status'] == 'failed']
            }

            # Summary stats
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total", len(driver_orders))
            with col2:
                st.metric("Pending", len(status_groups['pending']))
            with col3:
                st.metric("Allocated", len(status_groups['allocated']))
            with col4:
                st.metric("In Transit", len(status_groups['in_transit']))
            with col5:
                st.metric("Delivered", len(status_groups['delivered']))

            st.markdown("<br>", unsafe_allow_html=True)

            # Create tabs for each status
            tab_labels = []
            tab_data = []

            if not status_groups['in_transit'].empty:
                tab_labels.append(f"🚚 In Transit ({len(status_groups['in_transit'])})")
                tab_data.append(status_groups['in_transit'])

            if not status_groups['allocated'].empty:
                tab_labels.append(f"📋 Allocated ({len(status_groups['allocated'])})")
                tab_data.append(status_groups['allocated'])

            if not status_groups['pending'].empty:
                tab_labels.append(f"⏳ Pending ({len(status_groups['pending'])})")
                tab_data.append(status_groups['pending'])

            if not status_groups['delivered'].empty:
                tab_labels.append(f"✅ Delivered ({len(status_groups['delivered'])})")
                tab_data.append(status_groups['delivered'])

            if not status_groups['failed'].empty:
                tab_labels.append(f"❌ Failed ({len(status_groups['failed'])})")
                tab_data.append(status_groups['failed'])

            if tab_labels:
                tabs = st.tabs(tab_labels)

                for tab, orders in zip(tabs, tab_data):
                    with tab:
                        for _, order in orders.iterrows():
                            # Status colors
                            status_colors = {
                                'pending': '#fbbf24',
                                'allocated': '#3b82f6',
                                'in_transit': '#10b981',
                                'delivered': '#10b981',
                                'failed': '#ef4444'
                            }
                            status_color = status_colors.get(order['status'], '#667eea')

                            # Format timestamps
                            created_at = ''
                            if hasattr(order.get('created_at'), 'strftime'):
                                created_at = order['created_at'].strftime('%Y-%m-%d %H:%M')

                            st.markdown(f"""
                            <div style="margin-bottom: 0.75rem; padding: 1rem; background: rgba(255,255,255,0.03); border-radius: 8px; border-left: 4px solid {status_color};">
                                <div style="display: flex; justify-content: space-between; align-items: start;">
                                    <div style="flex: 1;">
                                        <div style="font-family: 'Space Mono', monospace; font-weight: 700; font-size: 0.95rem; color: {status_color};">
                                            {order['order_id']}
                                        </div>
                                        <div style="font-family: 'DM Sans', sans-serif; font-size: 0.9rem; color: rgba(255,255,255,0.9); margin-top: 0.25rem;">
                                            <strong>{order['customer']}</strong>
                                        </div>
                                        <div style="font-family: 'DM Sans', sans-serif; font-size: 0.85rem; color: rgba(255,255,255,0.6); margin-top: 0.25rem;">
                                            📍 {order['address']}, {order['suburb']} {order['postcode']}
                                        </div>
                                        <div style="font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.4); margin-top: 0.5rem;">
                                            {order['parcels']} parcel(s) • {order['service_level']} • Created: {created_at}
                                        </div>
                                    </div>
                                    <div style="text-align: right;">
                                        <span style="background: {status_color}; color: white; padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase;">
                                            {order['status']}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # Close button
        if st.button("Close", key=f"close_orders_{driver_id}", use_container_width=True):
            st.session_state.pop('viewing_driver_orders', None)
            st.rerun()


def _render_location_history(driver, data_manager):
    """Show a map of the driver's location history for a chosen date."""
    from datetime import date as date_type
    import pydeck as pdk

    driver_id = driver['driver_id']
    driver_name = driver['name']

    st.markdown(f"#### 📍 Location History — {driver_name}")

    col_date, col_close = st.columns([2, 1])
    with col_date:
        selected_date = st.date_input(
            "Select date",
            value=date_type.today(),
            key=f"hist_date_{driver_id}",
        )
    with col_close:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Close", key=f"close_hist_{driver_id}", use_container_width=True):
            st.session_state.pop('viewing_driver_history', None)
            st.rerun()

    history_df = data_manager.get_driver_location_history(
        driver_id, date=selected_date.strftime('%Y-%m-%d')
    )

    if history_df.empty:
        st.info(f"No location data recorded for {driver_name} on {selected_date.strftime('%d/%m/%Y')}.")
        return

    # Format timestamps for display
    # Timestamps are stored as UTC — convert to Sydney local time for display
    history_df['recorded_at'] = (
        pd.to_datetime(history_df['recorded_at'], utc=True)
        .dt.tz_convert('Australia/Sydney')
    )
    history_df['time_label'] = history_df['recorded_at'].dt.strftime('%H:%M:%S')

    st.caption(f"{len(history_df)} location points recorded on {selected_date.strftime('%d/%m/%Y')}")

    # Time range filter
    times = history_df['recorded_at'].tolist()
    if len(times) > 1:
        min_t = times[0].strftime('%H:%M')
        max_t = times[-1].strftime('%H:%M')
        st.caption(f"Active from **{min_t}** to **{max_t}**")

    # Build pydeck map — path layer + scatter layer
    path_data = [{
        'path': list(zip(history_df['longitude'].tolist(), history_df['latitude'].tolist())),
        'name': driver_name,
    }]

    points_data = history_df[['latitude', 'longitude', 'time_label']].to_dict('records')

    midlat = history_df['latitude'].mean()
    midlng = history_df['longitude'].mean()

    path_layer = pdk.Layer(
        'PathLayer',
        data=path_data,
        get_path='path',
        get_color=[102, 126, 234],
        width_min_pixels=3,
        pickable=False,
    )

    scatter_layer = pdk.Layer(
        'ScatterplotLayer',
        data=points_data,
        get_position='[longitude, latitude]',
        get_fill_color=[102, 126, 234, 200],
        get_radius=30,
        pickable=True,
    )

    # Mark the first point green and last point red
    start_end = [
        {'latitude': history_df.iloc[0]['latitude'],  'longitude': history_df.iloc[0]['longitude'],  'color': [16, 185, 129], 'label': 'Start'},
        {'latitude': history_df.iloc[-1]['latitude'], 'longitude': history_df.iloc[-1]['longitude'], 'color': [239, 68, 68],  'label': 'End'},
    ]
    start_end_layer = pdk.Layer(
        'ScatterplotLayer',
        data=start_end,
        get_position='[longitude, latitude]',
        get_fill_color='color',
        get_radius=60,
        pickable=True,
    )

    view = pdk.ViewState(latitude=midlat, longitude=midlng, zoom=13, pitch=0)
    deck = pdk.Deck(
        layers=[path_layer, scatter_layer, start_end_layer],
        initial_view_state=view,
        tooltip={'text': '{time_label}'},
        map_style='https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
    )
    st.pydeck_chart(deck)

    # Timeline table
    with st.expander("View full timeline"):
        display_df = history_df[['time_label', 'latitude', 'longitude']].copy()
        display_df.columns = ['Time', 'Latitude', 'Longitude']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
