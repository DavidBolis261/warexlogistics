import streamlit as st

from config.constants import ZONES, VEHICLE_TYPES


def render(drivers_df, data_manager):
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
                    if st.button("Edit", key=f"edit_{driver_id}", use_container_width=True):
                        st.session_state['editing_driver'] = driver_id
                        st.rerun()
                    if st.button("Delete", key=f"del_{driver_id}", use_container_width=True):
                        st.session_state['confirm_delete_driver'] = driver_id
                        st.rerun()

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
