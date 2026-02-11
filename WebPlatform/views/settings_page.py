import json
import streamlit as st
from datetime import datetime

from config.settings import wms_config


def render(data_manager):
    st.markdown('<div class="section-header">System Settings</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "General", "Email Notifications", "WMS Integration", "Zones & Routing", "API Log",
    ])

    with tab1:
        _render_general(data_manager)

    with tab2:
        _render_email_settings(data_manager)

    with tab3:
        _render_wms_integration(data_manager)

    with tab4:
        _render_zones(data_manager)

    with tab5:
        _render_api_log(data_manager)


def _render_general(data_manager):
    st.markdown("### General Settings")

    with st.form("general_settings_form"):
        col1, col2 = st.columns(2)

        with col1:
            company_name = st.text_input(
                "Company Name",
                value=data_manager.get_setting('company_name', 'Sydney Metro Courier'),
            )
            contact_email = st.text_input(
                "Primary Contact Email",
                value=data_manager.get_setting('contact_email', 'ops@sydneymetrocourier.com.au'),
            )
            support_phone = st.text_input(
                "Support Phone",
                value=data_manager.get_setting('support_phone', '1300 DELIVER'),
            )

        with col2:
            timezone_options = ["Australia/Sydney", "Australia/Melbourne", "Australia/Brisbane"]
            current_tz = data_manager.get_setting('timezone', 'Australia/Sydney')
            tz_index = timezone_options.index(current_tz) if current_tz in timezone_options else 0
            timezone = st.selectbox("Timezone", timezone_options, index=tz_index)

            date_format_options = ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"]
            current_df = data_manager.get_setting('date_format', 'DD/MM/YYYY')
            df_index = date_format_options.index(current_df) if current_df in date_format_options else 0
            date_format = st.selectbox("Date Format", date_format_options, index=df_index)

            service_options = ["standard", "express", "economy"]
            current_sl = data_manager.get_setting('default_service_level', 'standard')
            sl_index = service_options.index(current_sl) if current_sl in service_options else 0
            default_service = st.selectbox("Default Service Level", service_options, index=sl_index)

        st.markdown("### Operating Hours")
        col1, col2 = st.columns(2)
        with col1:
            saved_start = data_manager.get_setting('operating_start_time', '06:00')
            start_time = st.time_input("Start Time", datetime.strptime(saved_start, "%H:%M"))
        with col2:
            saved_end = data_manager.get_setting('operating_end_time', '21:00')
            end_time = st.time_input("End Time", datetime.strptime(saved_end, "%H:%M"))

        all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        saved_days = data_manager.get_setting('operating_days', None)
        if saved_days:
            try:
                default_days = json.loads(saved_days)
            except (json.JSONDecodeError, TypeError):
                default_days = all_days[:6]
        else:
            default_days = all_days[:6]

        operating_days = st.multiselect("Operating Days", all_days, default=default_days)

        submitted = st.form_submit_button("Save Settings", use_container_width=True, type="primary")

        if submitted:
            data_manager.save_settings({
                'company_name': company_name,
                'contact_email': contact_email,
                'support_phone': support_phone,
                'timezone': timezone,
                'date_format': date_format,
                'default_service_level': default_service,
                'operating_start_time': start_time.strftime('%H:%M'),
                'operating_end_time': end_time.strftime('%H:%M'),
                'operating_days': json.dumps(operating_days),
            })
            st.success("Settings saved!")


def _render_email_settings(data_manager):
    st.markdown("### Email Notifications")
    st.caption("Send automated emails to customers when orders are created or status changes. Powered by Resend.")

    from utils.email_service import is_email_configured, test_email_connection

    if is_email_configured(data_manager):
        st.success("Email notifications are enabled")
    else:
        st.warning("Email notifications are disabled. Configure your settings below.")

    with st.form("email_settings_form"):
        enabled = st.toggle(
            "Enable email notifications",
            value=data_manager.get_setting('email_notifications_enabled', 'false').lower() == 'true',
        )

        st.markdown("### Resend API")
        st.caption("Sign up at [resend.com](https://resend.com), add your domain, and get your API key.")

        import os
        api_key_env = os.environ.get('RESEND_API_KEY', '')

        col1, col2 = st.columns(2)
        with col1:
            if api_key_env:
                st.text_input(
                    "Resend API Key",
                    value="Set via RESEND_API_KEY environment variable",
                    disabled=True,
                )
                resend_api_key = ''
            else:
                resend_api_key = st.text_input(
                    "Resend API Key",
                    value=data_manager.get_setting('resend_api_key', ''),
                    type="password",
                    placeholder="re_xxxxxxxxx",
                )

        with col2:
            from_email = st.text_input(
                "From Email Address",
                value=data_manager.get_setting('email_from_address', ''),
                placeholder="info@warexlogistics.com.au",
                help="Must match a verified domain in your Resend account",
            )

        st.markdown("### Website")
        site_domain = st.text_input(
            "Your Website Domain (for tracking links in emails)",
            value=data_manager.get_setting('site_domain', ''),
            placeholder="warexlogistics.com.au",
        )

        submitted = st.form_submit_button("Save Email Settings", use_container_width=True, type="primary")

        if submitted:
            settings = {
                'email_notifications_enabled': str(enabled).lower(),
                'email_from_address': from_email,
                'site_domain': site_domain,
            }
            if resend_api_key:
                settings['resend_api_key'] = resend_api_key
            data_manager.save_settings(settings)
            st.success("Email settings saved!")

    # Test connection
    st.markdown("### Test Connection")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔌 Test Resend Connection", use_container_width=True):
            result = test_email_connection(data_manager)
            if result.get('success'):
                domains = result.get('domains', [])
                if domains:
                    st.success(f"Connected! Verified domains: {', '.join(domains)}")
                else:
                    st.warning(result.get('warning', 'API key works but no verified domains.'))
            else:
                st.error(f"Connection failed: {result.get('error', 'Unknown error')}")
    with col2:
        test_email = st.text_input("Send test email to", placeholder="your@email.com", key="test_email_addr")
        if st.button("📧 Send Test Email", use_container_width=True):
            if not test_email:
                st.warning("Enter an email address above to send a test.")
            elif not is_email_configured(data_manager):
                st.error("Please save your email settings and enable notifications first.")
            else:
                from utils.email_service import send_order_confirmation
                test_order = {
                    'email': test_email,
                    'customer': 'Test Customer',
                    'tracking_number': 'WRX-TEST-000000',
                    'suburb': 'Sydney',
                    'postcode': '2000',
                    'service_level': 'express',
                    'parcels': 1,
                }
                result = send_order_confirmation(data_manager, test_order)
                if result.get('success'):
                    st.success(f"Test email sent to {test_email}!")
                else:
                    st.error(f"Failed: {result.get('error', 'Unknown error')}")

    st.markdown("---")
    st.markdown("### Setup Guide")
    st.markdown("""
    **Step 1:** Sign up at [resend.com](https://resend.com) (free — 100 emails/day)

    **Step 2:** Go to **Domains** → **Add Domain** → enter `warexlogistics.com.au`

    **Step 3:** Add the DNS records Resend gives you on GoDaddy (2 TXT records)

    **Step 4:** Click **Verify** in Resend once DNS has propagated

    **Step 5:** Go to **API Keys** → **Create API Key** → copy the key (starts with `re_`)

    **Step 6:** Add `RESEND_API_KEY` as an environment variable on Railway, OR paste it above

    **Step 7:** Set the **From Email** above to `info@warexlogistics.com.au` and **Enable** notifications

    **Step 8:** Click **Test Resend Connection** to verify, then send yourself a test email!

    ---

    **When enabled, the system automatically sends:**

    1. **Order Confirmation** — When a new order is created with a customer email
    2. **Status Updates** — When you change an order status (Allocated → In Transit → Delivered)
    """)


def _render_wms_integration(data_manager):
    st.markdown("### Data Mode")
    data_mode = st.radio(
        "Select how the dashboard operates",
        ["Demo Mode (mock data)", "Local Only (SQLite)", "Live (push to .wms + local store)"],
        index=2 if wms_config.is_configured else 1,
    )
    st.session_state['data_mode'] = data_mode

    st.markdown("---")

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


def _render_zones(data_manager):
    st.markdown("### Delivery Zones")

    zones_df = data_manager.get_zones()

    if zones_df.empty:
        st.info("No zones configured. Default zones will be created.")
        return

    for _, zone in zones_df.iterrows():
        zone_name = zone['zone_name']
        try:
            suburbs = json.loads(zone['suburbs']) if zone['suburbs'] else []
        except (json.JSONDecodeError, TypeError):
            suburbs = []

        with st.expander(f"{zone_name} ({len(suburbs)} suburbs)"):
            with st.form(f"zone_form_{zone_name}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    postcodes = st.text_input(
                        "Postcodes",
                        value=zone.get('postcodes', ''),
                        key=f"pc_{zone_name}",
                    )
                    suburbs_text = st.text_input(
                        "Suburbs (comma-separated)",
                        value=', '.join(suburbs),
                        key=f"sub_{zone_name}",
                    )
                with col2:
                    surcharge = st.number_input(
                        "Surcharge ($)",
                        value=float(zone.get('surcharge', 0)),
                        key=f"sc_{zone_name}",
                    )
                    max_stops = st.number_input(
                        "Max stops per run",
                        value=int(zone.get('max_stops', 15)),
                        min_value=1,
                        max_value=50,
                        key=f"ms_{zone_name}",
                    )

                col_save, col_delete = st.columns(2)
                with col_save:
                    save_btn = st.form_submit_button("Save Zone", use_container_width=True)
                with col_delete:
                    delete_btn = st.form_submit_button("Delete Zone", use_container_width=True)

                if save_btn:
                    parsed_suburbs = [s.strip() for s in suburbs_text.split(',') if s.strip()]
                    data_manager.save_zone({
                        'zone_name': zone_name,
                        'suburbs': parsed_suburbs,
                        'postcodes': postcodes,
                        'surcharge': surcharge,
                        'max_stops': max_stops,
                    })
                    st.success(f"Zone '{zone_name}' saved!")
                    st.rerun()

                if delete_btn:
                    data_manager.delete_zone(zone_name)
                    st.success(f"Zone '{zone_name}' deleted!")
                    st.rerun()

    # Add new zone
    st.markdown("---")
    st.markdown("### Add New Zone")

    with st.form("new_zone_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_zone_name = st.text_input("Zone Name")
            new_suburbs = st.text_input("Suburbs (comma-separated)")
            new_postcodes = st.text_input("Postcodes (comma-separated)")
        with col2:
            new_surcharge = st.number_input("Surcharge ($)", value=0.0, key="new_zone_surcharge")
            new_max_stops = st.number_input("Max stops per run", value=15, min_value=1, max_value=50, key="new_zone_max_stops")

        submitted = st.form_submit_button("Create Zone", use_container_width=True, type="primary")

        if submitted:
            if not new_zone_name:
                st.error("Zone name is required")
            else:
                parsed_suburbs = [s.strip() for s in new_suburbs.split(',') if s.strip()]
                data_manager.save_zone({
                    'zone_name': new_zone_name,
                    'suburbs': parsed_suburbs,
                    'postcodes': new_postcodes,
                    'surcharge': new_surcharge,
                    'max_stops': new_max_stops,
                })
                st.success(f"Zone '{new_zone_name}' created!")
                st.rerun()

    st.markdown("---")
    st.markdown("### Routing Preferences")

    with st.form("routing_prefs_form"):
        max_stops = st.slider(
            "Default max stops per run",
            5, 30,
            int(data_manager.get_setting('max_stops_per_run', '15')),
        )
        max_duration = st.slider(
            "Max run duration (hours)",
            2, 8,
            int(data_manager.get_setting('max_run_duration', '4')),
        )
        avoid_tolls = st.checkbox(
            "Avoid toll roads",
            value=data_manager.get_setting('avoid_tolls', 'False') == 'True',
        )
        express_priority = st.checkbox(
            "Prioritize express deliveries",
            value=data_manager.get_setting('express_priority', 'True') == 'True',
        )

        submitted = st.form_submit_button("Save Routing Preferences", use_container_width=True)

        if submitted:
            data_manager.save_settings({
                'max_stops_per_run': str(max_stops),
                'max_run_duration': str(max_duration),
                'avoid_tolls': str(avoid_tolls),
                'express_priority': str(express_priority),
            })
            st.success("Routing preferences saved!")


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
