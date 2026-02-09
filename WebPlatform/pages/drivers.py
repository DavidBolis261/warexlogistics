import streamlit as st


def render(drivers_df, data_manager):
    st.markdown('<div class="section-header">Driver Management</div>', unsafe_allow_html=True)

    # Driver stats summary
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        available = len(drivers_df[drivers_df['status'] == 'available'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #10b981;">{available}</div>
            <div class="metric-label">Available</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        on_route = len(drivers_df[drivers_df['status'] == 'on_route'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #3b82f6;">{on_route}</div>
            <div class="metric-label">On Route</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        offline = len(drivers_df[drivers_df['status'] == 'offline'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #6b7280;">{offline}</div>
            <div class="metric-label">Offline</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        total_deliveries = drivers_df['deliveries_today'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_deliveries}</div>
            <div class="metric-label">Total Deliveries</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Driver cards
    col1, col2 = st.columns(2)

    for idx, (_, driver) in enumerate(drivers_df.iterrows()):
        status_class = f"status-{driver['status'].replace('_', '-')}"

        with col1 if idx % 2 == 0 else col2:
            st.markdown(f"""
            <div class="driver-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div class="driver-name">{driver['name']}</div>
                        <div class="driver-vehicle">{driver['driver_id']} &bull; {driver['vehicle_type']} &bull; {driver['plate']}</div>
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
                        <div class="driver-stat-value">{int(driver['success_rate'] * 100)}%</div>
                        <div class="driver-stat-label">Success</div>
                    </div>
                    <div class="driver-stat">
                        <div class="driver-stat-value">{driver['rating']}</div>
                        <div class="driver-stat-label">Rating</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Add new driver section
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Add New Driver</div>', unsafe_allow_html=True)

    with st.form("new_driver_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            new_name = st.text_input("Driver Name")
            new_phone = st.text_input("Phone Number")

        with col2:
            new_vehicle = st.selectbox("Vehicle Type", ["Van", "Truck"])
            new_plate = st.text_input("License Plate")

        with col3:
            new_zone = st.selectbox("Primary Zone", ["Inner West", "Eastern Suburbs", "CBD", "South Sydney", "Inner City"])

        submitted = st.form_submit_button("Add Driver", use_container_width=True)
        if submitted and new_name:
            data_manager.add_driver({
                'name': new_name,
                'phone': new_phone,
                'vehicle_type': new_vehicle,
                'plate': new_plate,
                'current_zone': new_zone,
            })
            st.success(f"Driver {new_name} added successfully!")
            st.rerun()
