import streamlit as st
from datetime import datetime

from config.settings import wms_config


def render(data_manager):
    st.markdown('<div class="section-header">System Settings</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "General", "WMS Integration", "Zones & Routing", "Users", "API Log",
    ])

    with tab1:
        _render_general()

    with tab2:
        _render_wms_integration(data_manager)

    with tab3:
        _render_zones()

    with tab4:
        _render_users()

    with tab5:
        _render_api_log(data_manager)


def _render_general():
    st.markdown("### General Settings")

    col1, col2 = st.columns(2)

    with col1:
        st.text_input("Company Name", value="Sydney Metro Courier")
        st.text_input("Primary Contact Email", value="ops@sydneymetrocourier.com.au")
        st.text_input("Support Phone", value="1300 DELIVER")

    with col2:
        st.selectbox("Timezone", ["Australia/Sydney", "Australia/Melbourne", "Australia/Brisbane"])
        st.selectbox("Date Format", ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"])
        st.selectbox("Default Service Level", ["standard", "express", "economy"])

    st.markdown("### Operating Hours")

    col1, col2 = st.columns(2)
    with col1:
        st.time_input("Start Time", datetime.strptime("06:00", "%H:%M"))
    with col2:
        st.time_input("End Time", datetime.strptime("21:00", "%H:%M"))

    st.multiselect(
        "Operating Days",
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    )


def _render_wms_integration(data_manager):
    st.markdown("### Thomax .wms Connection")

    if wms_config.is_configured:
        st.success("WMS credentials are configured")
    else:
        st.warning("WMS credentials are not configured. Enter your details below.")
        st.caption("Contact Thomax to obtain your InstanceCode, TenantCode, WarehouseCode, and APIKey.")

    with st.form("wms_credentials_form"):
        col1, col2 = st.columns(2)

        with col1:
            cluster = st.text_input(
                "Cluster Name",
                value=wms_config.cluster,
                help="The subdomain for your .wms instance (e.g., 'au1' for https://au1.dotwms.com)",
            )
            instance_code = st.text_input(
                "Instance Code",
                value=wms_config.instance_code,
                help="Provided by Thomax",
            )
            tenant_code = st.text_input(
                "Tenant Code",
                value=wms_config.tenant_code,
                help="Provided by Thomax",
            )

        with col2:
            warehouse_code = st.text_input(
                "Warehouse Code",
                value=wms_config.warehouse_code,
                help="The warehouse to operate against",
            )
            api_key = st.text_input(
                "API Key",
                value=wms_config.api_key,
                type="password",
                help="Provided by Thomax",
            )

        if cluster:
            st.caption(f"API Endpoint: https://{cluster}.dotwms.com/api/1.0/")

        col1, col2 = st.columns(2)
        with col1:
            save_to_env = st.checkbox("Save to .env file (persists across restarts)", value=True)
        with col2:
            pass

        submitted = st.form_submit_button("Save WMS Credentials", use_container_width=True, type="primary")

        if submitted:
            wms_config.save_to_session(cluster, instance_code, tenant_code, warehouse_code, api_key)
            if save_to_env:
                wms_config.save_to_env_file(cluster, instance_code, tenant_code, warehouse_code, api_key)
            st.success("Credentials saved!")
            st.rerun()

    # Test Connection
    st.markdown("### Connection Test")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Test Connection", use_container_width=True):
            if not wms_config.is_configured:
                st.error("Please configure your WMS credentials first")
            else:
                result = data_manager.test_wms_connection()
                if result.get('success'):
                    st.success(f"Connection successful! Endpoint: {wms_config.base_url}")
                else:
                    st.error(f"Connection failed: {result.get('error', 'Unknown error')}")
    with col2:
        if st.button("Force Sync Now", use_container_width=True):
            if not wms_config.is_configured:
                st.error("WMS not configured")
            else:
                st.info("Sync initiated. Note: .wms API is push-only. "
                        "Ask Thomax about outbound/webhook APIs for pull data.")

    st.markdown("---")

    st.markdown("### Data Mode")
    data_mode = st.radio(
        "Select how the dashboard operates",
        ["Demo Mode (mock data)", "Local Only (SQLite)", "Live (push to .wms + local store)"],
        index=2 if wms_config.is_configured else 0,
    )
    st.session_state['data_mode'] = data_mode

    st.markdown("---")

    st.markdown("### Notification Services")
    st.checkbox("SMS notifications (Twilio)", value=False)
    st.checkbox("Email notifications (SendGrid)", value=False)
    st.checkbox("Push notifications (Firebase)", value=False)


def _render_zones():
    st.markdown("### Delivery Zones")

    zones = [
        {"name": "CBD", "postcodes": "2000, 2010, 2011", "surcharge": 0},
        {"name": "Inner West", "postcodes": "2037, 2040, 2041, 2042, 2043, 2044", "surcharge": 0},
        {"name": "Eastern Suburbs", "postcodes": "2021, 2022, 2024, 2025, 2026", "surcharge": 5},
        {"name": "South Sydney", "postcodes": "2015, 2016, 2017, 2018, 2020", "surcharge": 0},
        {"name": "Inner City", "postcodes": "2039, 2041", "surcharge": 0},
    ]

    for zone in zones:
        with st.expander(f"{zone['name']}"):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.text_input("Postcodes", value=zone['postcodes'], key=f"pc_{zone['name']}")
            with col2:
                st.number_input("Surcharge ($)", value=zone['surcharge'], key=f"sc_{zone['name']}")

    if st.button("Add New Zone"):
        st.info("Zone creation dialog would open")

    st.markdown("### Routing Preferences")

    st.slider("Max stops per run", 5, 30, 15)
    st.slider("Max run duration (hours)", 2, 8, 4)
    st.checkbox("Avoid toll roads", value=False)
    st.checkbox("Prioritize express deliveries", value=True)


def _render_users():
    st.markdown("### User Management")

    users = [
        {"name": "Admin User", "email": "admin@smc.com.au", "role": "Administrator", "status": "Active"},
        {"name": "Dispatch Manager", "email": "dispatch@smc.com.au", "role": "Dispatcher", "status": "Active"},
        {"name": "Operations Lead", "email": "ops@smc.com.au", "role": "Manager", "status": "Active"},
    ]

    for user in users:
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        with col1:
            st.text(user['name'])
        with col2:
            st.text(user['email'])
        with col3:
            st.text(user['role'])
        with col4:
            st.button("Edit", key=f"edit_{user['email']}")

    st.markdown("---")

    if st.button("Add New User"):
        st.info("User creation dialog would open")


def _render_api_log(data_manager):
    st.markdown("### API Operation Log")
    st.caption("Shows all API calls made to the .wms system")

    api_log = data_manager.get_api_log()
    if not api_log.empty:
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            op_filter = st.multiselect(
                "Filter by operation",
                api_log['operation'].unique().tolist() if 'operation' in api_log.columns else []
            )
        with col2:
            success_filter = st.selectbox("Filter by result", ["All", "Success", "Failed"])

        filtered = api_log.copy()
        if op_filter:
            filtered = filtered[filtered['operation'].isin(op_filter)]
        if success_filter == "Success":
            filtered = filtered[filtered['success'] == True]
        elif success_filter == "Failed":
            filtered = filtered[filtered['success'] == False]

        st.dataframe(filtered.tail(50), use_container_width=True, hide_index=True)

        if st.button("Clear Log"):
            data_manager.clear_api_log()
            st.success("Log cleared")
            st.rerun()
    else:
        st.info("No API operations logged yet. Operations will appear here when you interact with the .wms API.")
