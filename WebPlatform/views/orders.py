import streamlit as st
from datetime import datetime
import os
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from config.constants import ZONE_MAPPING, ZONES
from streamlit_searchbox import st_searchbox
from utils.address_autocomplete import search_addresses, get_place_id_from_description, get_address_details, parse_simple_address

ITEMS_PER_PAGE = 20
SYDNEY_TZ = ZoneInfo("Australia/Sydney")


def _fmt_sydney(ts):
    """Format a timestamp in Sydney local time."""
    if ts is None:
        return ''
    try:
        if hasattr(ts, 'tzinfo') and ts.tzinfo is None:
            ts = ts.replace(tzinfo=ZoneInfo("UTC"))
        return ts.astimezone(SYDNEY_TZ).strftime('%d/%m/%Y %H:%M')
    except Exception:
        return str(ts)

STATUS_OPTIONS = ['pending', 'allocated', 'in_transit', 'delivered', 'failed']
STATUS_LABELS = {
    'pending': 'Pending',
    'allocated': 'Allocated',
    'in_transit': 'In Transit',
    'delivered': 'Delivered',
    'failed': 'Failed',
}


def render(orders_df, drivers_df, data_manager, zone_filter, service_filter, status_filter):
    st.markdown('<div class="section-header">Order Management</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Pending", "In Transit", "Completed", "Inbound Receipts",
    ])

    if not orders_df.empty:
        filtered_df = orders_df.copy()

        # Apply filters from sidebar
        if zone_filter and 'suburb' in filtered_df.columns:
            selected_suburbs = []
            for zone in zone_filter:
                selected_suburbs.extend(ZONE_MAPPING.get(zone, []))
            if selected_suburbs:
                filtered_df = filtered_df[filtered_df['suburb'].isin(selected_suburbs)]

        if service_filter and 'service_level' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['service_level'].isin(service_filter)]

        if status_filter and 'status' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
    else:
        filtered_df = orders_df

    with tab1:
        _render_pending(filtered_df, drivers_df, data_manager)

    with tab2:
        _render_in_transit(filtered_df)

    with tab3:
        _render_completed(filtered_df)

    with tab4:
        _render_inbound_receipts(data_manager)


def _render_all_orders(orders_df, drivers_df, data_manager):
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("Search orders...", placeholder="Order ID, customer name, tracking number, or address")
    with col2:
        sort_by = st.selectbox("Sort by", ["Created (newest)", "Created (oldest)", "Service Level", "Status"])
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("New Order", use_container_width=True):
            st.session_state['show_new_order_form'] = True

    # New order form
    if st.session_state.get('show_new_order_form'):
        _render_new_order_form(data_manager)

    if orders_df.empty:
        st.info("No orders yet. Click 'New Order' to create your first order.")
        return

    # Build driver options list once
    driver_options = []
    if not drivers_df.empty:
        available = drivers_df[drivers_df['status'] == 'available']['name'].tolist()
        driver_options = available if available else drivers_df['name'].tolist()

    # Apply search
    if search:
        mask = (
            orders_df['order_id'].str.contains(search, case=False, na=False) |
            orders_df['customer'].str.contains(search, case=False, na=False) |
            orders_df['address'].str.contains(search, case=False, na=False)
        )
        if 'tracking_number' in orders_df.columns:
            mask = mask | orders_df['tracking_number'].str.contains(search, case=False, na=False)
        orders_df = orders_df[mask]

    # Apply sorting
    if sort_by == "Created (newest)" and 'created_at' in orders_df.columns:
        orders_df = orders_df.sort_values('created_at', ascending=False)
    elif sort_by == "Created (oldest)" and 'created_at' in orders_df.columns:
        orders_df = orders_df.sort_values('created_at', ascending=True)
    elif sort_by == "Service Level" and 'service_level' in orders_df.columns:
        service_order = {'express': 0, 'standard': 1, 'economy': 2}
        orders_df = orders_df.sort_values(
            'service_level', key=lambda x: x.map(service_order).fillna(99)
        )
    elif sort_by == "Status" and 'status' in orders_df.columns:
        status_order = {'pending': 0, 'allocated': 1, 'in_transit': 2, 'delivered': 3, 'failed': 4}
        orders_df = orders_df.sort_values(
            'status', key=lambda x: x.map(status_order).fillna(99)
        )

    # Pagination
    total_orders = len(orders_df)
    total_pages = max(1, (total_orders + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    if total_orders > ITEMS_PER_PAGE:
        col_prev, col_page, col_next = st.columns([1, 2, 1])
        current_page = st.session_state.get('orders_page', 1)
        current_page = min(current_page, total_pages)

        with col_prev:
            if st.button("Previous", disabled=current_page <= 1, use_container_width=True):
                st.session_state['orders_page'] = current_page - 1
                st.rerun()
        with col_page:
            st.markdown(f"<div style='text-align:center; padding:0.5rem;'>Page {current_page} of {total_pages} ({total_orders} orders)</div>", unsafe_allow_html=True)
        with col_next:
            if st.button("Next", disabled=current_page >= total_pages, use_container_width=True):
                st.session_state['orders_page'] = current_page + 1
                st.rerun()

        start_idx = (current_page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_df = orders_df.iloc[start_idx:end_idx]
    else:
        page_df = orders_df

    for _, order in page_df.iterrows():
        status_class = f"status-{order['status'].replace('_', '-')}"
        order_id = order['order_id']
        current_status = order['status']
        current_zone = order.get('zone', '') or ''
        current_driver = order.get('driver_id', '') or ''

        with st.expander(f"{order_id} - {order['customer']} - {order.get('suburb', '')}", expanded=False):
            col1, col2 = st.columns([2, 1])

            with col1:
                if order.get('tracking_number'):
                    st.markdown(f"**Tracking:** `{order['tracking_number']}`")

                created_str = ''
                if hasattr(order.get('created_at'), 'strftime'):
                    created_str = order['created_at'].strftime('%Y-%m-%d %H:%M')

                if order.get('pickup_address'):
                    pickup_line = f"{order['pickup_address']}, {order.get('pickup_suburb', '')} {order.get('pickup_state', '')} {order.get('pickup_postcode', '')}"
                    pickup_contact_line = ""
                    if order.get('pickup_contact'):
                        pickup_contact_line += f" &bull; {order['pickup_contact']}"
                    if order.get('pickup_phone'):
                        pickup_contact_line += f" &bull; {order['pickup_phone']}"
                    st.markdown(f"**Pickup:** {pickup_line}{pickup_contact_line}")

                st.markdown(f"""
                **Customer:** {order['customer']}
                **Deliver to:** {order['address']}, {order.get('suburb', '')} {order.get('postcode', '')}
                **Parcels:** {order.get('parcels', 1)}
                **Created:** {created_str}
                """)

                if current_driver:
                    st.markdown(f"**Assigned Driver:** {current_driver}")
                if current_zone:
                    st.markdown(f"**Zone:** {current_zone}")
                if order.get('eta'):
                    st.markdown(f"**ETA:** {order['eta']}")

            with col2:
                st.markdown(f"""
                <span class="status-badge {status_class}">{current_status.replace('_', ' ')}</span>
                <br><br>
                <span class="status-badge status-{order['service_level']}">{order['service_level']}</span>
                """, unsafe_allow_html=True)

                # Display QR Code
                from utils.qr_code import generate_qr_code
                qr_code_img = generate_qr_code(order_id, size=120)
                st.markdown(f"""
                <div style="text-align: center; margin-top: 15px;">
                    <img src="{qr_code_img}" style="width: 120px; height: 120px;">
                    <p style="font-size: 10px; margin: 5px 0;">Scan to pickup</p>
                </div>
                """, unsafe_allow_html=True)

            # --- Update Controls ---
            st.markdown("---")
            st.markdown("**Update Order**")

            uc1, uc2, uc3 = st.columns(3)

            with uc1:
                status_idx = STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0
                new_status = st.selectbox(
                    "Status",
                    STATUS_OPTIONS,
                    index=status_idx,
                    format_func=lambda s: STATUS_LABELS.get(s, s),
                    key=f"status_{order_id}",
                )

            with uc2:
                zone_options = ["None"] + ZONES
                zone_idx = 0
                if current_zone in ZONES:
                    zone_idx = ZONES.index(current_zone) + 1
                new_zone = st.selectbox(
                    "Zone",
                    zone_options,
                    index=zone_idx,
                    key=f"zone_{order_id}",
                )

            with uc3:
                driver_list = ["None"] + driver_options
                driver_idx = 0
                if current_driver in driver_options:
                    driver_idx = driver_options.index(current_driver) + 1
                new_driver = st.selectbox(
                    "Driver",
                    driver_list,
                    index=driver_idx,
                    key=f"driver_{order_id}",
                )

            # Build update dict from changed fields
            updates = {}
            if new_status != current_status:
                updates['status'] = new_status
            if (new_zone if new_zone != "None" else '') != current_zone:
                updates['zone'] = new_zone if new_zone != "None" else ''
            if (new_driver if new_driver != "None" else '') != current_driver:
                updates['driver_id'] = new_driver if new_driver != "None" else ''

            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                if st.button("💾 Save Changes", key=f"save_{order_id}", use_container_width=True, disabled=not updates):
                    data_manager.update_order(order_id, **updates)
                    st.success("Order updated!")
                    st.rerun()

            with bc2:
                if current_status == 'pending':
                    if st.button("📤 Push to WMS", key=f"push_{order_id}", use_container_width=True):
                        result = data_manager.push_order_to_wms(order.to_dict())
                        if result.get('success'):
                            st.success("Pushed to .wms successfully")
                        elif result.get('mock'):
                            st.info("Demo mode - order saved locally")
                        else:
                            st.error(f"Failed: {result.get('error', 'Unknown error')}")

            with bc3:
                if current_status in ['pending', 'allocated']:
                    if st.button("❌ Cancel Order", key=f"cancel_{order_id}", use_container_width=True):
                        result = data_manager.cancel_order(order_id)
                        if result.get('success'):
                            st.success("Order cancelled")
                            st.rerun()
                        else:
                            st.error(f"Failed: {result.get('error', 'Unknown error')}")


def _render_new_order_form(data_manager):
    st.markdown('<div class="section-header">Create New Order</div>', unsafe_allow_html=True)

    # Address autocomplete OUTSIDE the form (interactive components can't be in forms)
    has_api_key = bool(os.environ.get('GOOGLE_PLACES_API_KEY'))

    if has_api_key:
        st.markdown("### 📍 Address Autocomplete")
        col1, col2 = st.columns(2)

        with col1:
            st.caption("Pickup Address - Start typing to see suggestions")
            selected_pickup = st_searchbox(
                search_addresses,
                key="pickup_address_search",
                placeholder="Search pickup address...",
                clear_on_submit=False,
            )

            if selected_pickup:
                # Try to get full details with postcode from Google API
                place_id = get_place_id_from_description(selected_pickup)
                if place_id:
                    details = get_address_details(place_id)
                    if details:
                        st.session_state['pickup_parsed'] = details
                        st.success("✓ Pickup address selected")
                    else:
                        # Fallback to simple parsing
                        parsed = parse_simple_address(selected_pickup)
                        if parsed:
                            st.session_state['pickup_parsed'] = parsed
                            st.success("✓ Pickup address selected")
                else:
                    # Fallback to simple parsing
                    parsed = parse_simple_address(selected_pickup)
                    if parsed:
                        st.session_state['pickup_parsed'] = parsed
                        st.success("✓ Pickup address selected")

        with col2:
            st.caption("Delivery Address - Start typing to see suggestions")
            selected_delivery = st_searchbox(
                search_addresses,
                key="delivery_address_search",
                placeholder="Search delivery address...",
                clear_on_submit=False,
            )

            if selected_delivery:
                # Try to get full details with postcode from Google API
                place_id = get_place_id_from_description(selected_delivery)
                if place_id:
                    details = get_address_details(place_id)
                    if details:
                        st.session_state['address_parsed'] = details
                        st.success("✓ Delivery address selected")
                    else:
                        # Fallback to simple parsing
                        parsed = parse_simple_address(selected_delivery)
                        if parsed:
                            st.session_state['address_parsed'] = parsed
                            st.success("✓ Delivery address selected")
                else:
                    # Fallback to simple parsing
                    parsed = parse_simple_address(selected_delivery)
                    if parsed:
                        st.session_state['address_parsed'] = parsed
                        st.success("✓ Delivery address selected")

        st.markdown("---")

    with st.form("new_order_form"):
        st.markdown("### Pickup Address")

        col1, col2 = st.columns(2)

        with col1:
            default_pickup_address = st.session_state.get('pickup_parsed', {}).get('address', '')
            pickup_address = st.text_input("Pickup Address *", value=default_pickup_address)

            default_pickup_suburb = st.session_state.get('pickup_parsed', {}).get('suburb', '')
            pickup_suburb = st.text_input("Pickup Suburb *", value=default_pickup_suburb)

            pickup_contact = st.text_input("Pickup Contact Name")

        with col2:
            default_pickup_state = st.session_state.get('pickup_parsed', {}).get('state', 'NSW')
            pickup_state_idx = ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"].index(default_pickup_state) if default_pickup_state in ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"] else 0
            pickup_state = st.selectbox("Pickup State", ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"], index=pickup_state_idx, key="pickup_state")

            default_pickup_postcode = st.session_state.get('pickup_parsed', {}).get('postcode', '')
            pickup_postcode = st.text_input("Pickup Postcode *", value=default_pickup_postcode)

            pickup_phone = st.text_input("Pickup Phone")

        st.markdown("### Delivery Address")

        col1, col2 = st.columns(2)

        with col1:
            customer_name = st.text_input("Customer Name *")
            delivery_company = st.text_input("Company (optional)")

            # Pre-fill if we have parsed address
            default_address = st.session_state.get('address_parsed', {}).get('address', '')
            address1 = st.text_input("Address Line 1 *", value=default_address)
            address2 = st.text_input("Address Line 2")

            default_suburb = st.session_state.get('address_parsed', {}).get('suburb', '')
            suburb = st.text_input("Suburb *", value=default_suburb)

        with col2:
            default_state = st.session_state.get('address_parsed', {}).get('state', 'NSW')
            state_idx = ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"].index(default_state) if default_state in ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"] else 0
            state = st.selectbox("State", ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"], index=state_idx, key="delivery_state")

            default_postcode = st.session_state.get('address_parsed', {}).get('postcode', '')
            postcode = st.text_input("Postcode *", value=default_postcode)

            country = st.text_input("Country", value="Australia")
            email = st.text_input("Email *")
            phone = st.text_input("Phone *")

        st.markdown("### Order Details")
        col1, col2, col3 = st.columns(3)

        with col1:
            service_level = st.selectbox("Service Level", ["standard", "express", "economy"])
        with col2:
            item_code = st.text_input("Item Code / SKU", value="PARCEL")
            quantity = st.number_input("Quantity", min_value=1, value=1)
        with col3:
            carrier_service = st.text_input("Carrier Service Code (optional)")
            zone = st.text_input("Zone (optional)", help="Delivery zone or area")

        st.markdown("### Assignment & Instructions")
        col1, col2 = st.columns(2)

        with col1:
            # Get list of drivers for dropdown
            drivers_list = data_manager.get_drivers()
            driver_options = [""] + [f"{d['name']} ({d['driver_id']})" for _, d in drivers_list.iterrows()]
            selected_driver = st.selectbox("Assign to Driver (optional)", driver_options)
            # Extract driver_id from selection
            driver_id = ""
            if selected_driver and selected_driver != "":
                driver_id = selected_driver.split("(")[1].strip(")")

        with col2:
            special_instructions = st.text_area("Special Instructions", height=100)

        submitted = st.form_submit_button("Create Order", use_container_width=True, type="primary")

        if submitted:
            if not customer_name or not address1 or not suburb or not postcode or not email or not phone:
                st.error("Please fill in all required fields (marked with *)")
            elif not pickup_address or not pickup_suburb or not pickup_postcode:
                st.error("Please fill in all required pickup address fields (marked with *)")
            else:
                order_data = {
                    'customer': customer_name,
                    'delivery_company': delivery_company,
                    'address': address1,
                    'address2': address2,
                    'suburb': suburb,
                    'state': state,
                    'postcode': postcode,
                    'country': country,
                    'email': email,
                    'phone': phone,
                    'service_level': service_level,
                    'item_code': item_code,
                    'parcels': quantity,
                    'carrier_service': carrier_service,
                    'special_instructions': special_instructions,
                    'instructions': special_instructions,  # Map to instructions field
                    'zone': zone,
                    'driver_id': driver_id,
                    'pickup_address': pickup_address,
                    'pickup_suburb': pickup_suburb,
                    'pickup_state': pickup_state,
                    'pickup_postcode': pickup_postcode,
                    'pickup_contact': pickup_contact,
                    'pickup_phone': pickup_phone,
                }
                result = data_manager.create_order(order_data)
                if result.get('success'):
                    tracking = result.get('tracking_number', '')
                    st.success(f"Order {result.get('order_id', '')} created! Tracking: {tracking}")
                    if result.get('wms_pushed'):
                        st.info("Order pushed to .wms")
                    if result.get('email_sent'):
                        st.info(f"📧 Confirmation email sent to {order_data.get('email', '')}")
                    # Clear parsed addresses
                    st.session_state.pop('address_parsed', None)
                    st.session_state.pop('pickup_parsed', None)
                    st.session_state['show_new_order_form'] = False
                    st.rerun()
                else:
                    st.error(f"Failed to create order: {result.get('error', 'Unknown error')}")


def _render_pending(orders_df, drivers_df, data_manager):
    # Add search field and New Order button
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("Search pending orders...", placeholder="Order ID, customer name, tracking number, or address", key="pending_search")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("New Order", use_container_width=True, key="pending_new_order"):
            st.session_state['show_new_order_form'] = True

    # New order form
    if st.session_state.get('show_new_order_form'):
        _render_new_order_form(data_manager)

    if orders_df.empty:
        st.info("No orders to display.")
        return

    # Filter for pending orders (status='pending' or no driver allocated)
    pending = orders_df[(orders_df['status'] == 'pending') | (orders_df['driver_id'].isna()) | (orders_df['driver_id'] == '')]

    # Apply search filter
    if search:
        mask = (
            pending['order_id'].str.contains(search, case=False, na=False) |
            pending['customer'].str.contains(search, case=False, na=False) |
            pending['address'].str.contains(search, case=False, na=False)
        )
        if 'tracking_number' in pending.columns:
            mask = mask | pending['tracking_number'].str.contains(search, case=False, na=False)
        pending = pending[mask]

    st.info(f"{len(pending)} orders awaiting allocation")

    if pending.empty:
        st.success("All orders have been allocated!")
        return

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_orders = st.multiselect(
            "Select orders for bulk allocation",
            pending['order_id'].tolist(),
            key="pending_bulk_select"
        )
    with col2:
        if not drivers_df.empty:
            driver_options = drivers_df[drivers_df['status'] == 'available']['name'].tolist()
            if not driver_options:
                driver_options = drivers_df['name'].tolist()
        else:
            driver_options = []
        assigned_driver = st.selectbox("Assign to driver", ["Select driver..."] + driver_options, key="pending_driver_select")

    if st.button("Allocate Selected Orders", disabled=not selected_orders or assigned_driver == "Select driver...", key="pending_allocate_btn"):
        for oid in selected_orders:
            data_manager.allocate_order(oid, assigned_driver)
        st.success(f"{len(selected_orders)} orders allocated to {assigned_driver}")
        st.rerun()

    for _, order in pending.iterrows():
        order_id = order['order_id']
        current_status = order['status']
        current_zone = order.get('zone', '') or ''
        current_driver = order.get('driver_id', '') or ''
        created_str = _fmt_sydney(order.get('created_at'))

        with st.expander(f"{order_id} — {order['customer']} — {order.get('suburb', '')}  [{order['service_level'].upper()}]", expanded=False):
            col1, col2 = st.columns([2, 1])

            with col1:
                if order.get('tracking_number'):
                    st.markdown(f"**Tracking:** `{order['tracking_number']}`")
                if order.get('pickup_address'):
                    pickup_line = f"{order['pickup_address']}, {order.get('pickup_suburb', '')} {order.get('pickup_state', '')} {order.get('pickup_postcode', '')}"
                    st.markdown(f"**Pickup:** {pickup_line}")
                st.markdown(f"""
**Customer:** {order['customer']}
**Deliver to:** {order['address']}, {order.get('suburb', '')} {order.get('postcode', '')}
**Parcels:** {order.get('parcels', 1)}
**Created:** {created_str}
                """)
                if current_driver:
                    st.markdown(f"**Assigned Driver:** {current_driver}")
                if current_zone:
                    st.markdown(f"**Zone:** {current_zone}")
                if order.get('special_instructions'):
                    st.markdown(f"**Instructions:** {order['special_instructions']}")

            with col2:
                status_class = f"status-{current_status.replace('_', '-')}"
                st.markdown(f"""
<span class="status-badge {status_class}">{current_status.replace('_', ' ')}</span>
<br><br>
<span class="status-badge status-{order['service_level']}">{order['service_level']}</span>
                """, unsafe_allow_html=True)
                from utils.qr_code import generate_qr_code
                qr_code_img = generate_qr_code(order_id, size=120)
                st.markdown(f"""
<div style="text-align: center; margin-top: 15px;">
    <img src="{qr_code_img}" style="width: 120px; height: 120px;">
    <p style="font-size: 10px; margin: 5px 0;">Scan to pickup</p>
</div>
                """, unsafe_allow_html=True)

            # Update controls
            st.markdown("---")
            st.markdown("**Update Order**")
            uc1, uc2, uc3 = st.columns(3)
            with uc1:
                status_idx = STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0
                new_status = st.selectbox(
                    "Status", STATUS_OPTIONS, index=status_idx,
                    format_func=lambda s: STATUS_LABELS.get(s, s),
                    key=f"pend_status_{order_id}",
                )
            with uc2:
                zone_options = ["None"] + ZONES
                zone_idx = ZONES.index(current_zone) + 1 if current_zone in ZONES else 0
                new_zone = st.selectbox("Zone", zone_options, index=zone_idx, key=f"pend_zone_{order_id}")
            with uc3:
                if not drivers_df.empty:
                    drv_opts = drivers_df[drivers_df['status'] == 'available']['name'].tolist() or drivers_df['name'].tolist()
                else:
                    drv_opts = []
                driver_list = ["None"] + drv_opts
                driver_idx = drv_opts.index(current_driver) + 1 if current_driver in drv_opts else 0
                new_driver = st.selectbox("Driver", driver_list, index=driver_idx, key=f"pend_driver_{order_id}")

            updates = {}
            resolved_driver = new_driver if new_driver != "None" else ''
            resolved_zone = new_zone if new_zone != "None" else ''
            if new_status != current_status:
                updates['status'] = new_status
            if resolved_zone != current_zone:
                updates['zone'] = resolved_zone
            if resolved_driver != current_driver:
                updates['driver_id'] = resolved_driver
                # When assigning a driver, move to in_transit automatically
                if resolved_driver and 'status' not in updates:
                    updates['status'] = 'in_transit'

            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                if st.button("💾 Save Changes", key=f"pend_save_{order_id}", use_container_width=True, disabled=not updates):
                    data_manager.update_order(order_id, **updates)
                    st.success("Order updated!")
                    st.rerun()
            with bc2:
                if st.button("📤 Push to WMS", key=f"pend_push_{order_id}", use_container_width=True):
                    result = data_manager.push_order_to_wms(order.to_dict())
                    if result.get('success'):
                        st.success("Pushed to .wms successfully")
                    elif result.get('mock'):
                        st.info("Demo mode - order saved locally")
                    else:
                        st.error(f"Failed: {result.get('error', 'Unknown error')}")
            with bc3:
                if st.button("❌ Cancel Order", key=f"pend_cancel_{order_id}", use_container_width=True):
                    result = data_manager.cancel_order(order_id)
                    if result.get('success'):
                        st.success("Order cancelled")
                        st.rerun()
                    else:
                        st.error(f"Failed: {result.get('error', 'Unknown error')}")


def _render_in_transit(orders_df):
    # Add search field
    search = st.text_input("Search in transit orders...", placeholder="Order ID, customer name, tracking number, or address", key="transit_search")

    if orders_df.empty:
        st.info("No orders in transit.")
        return

    # Show both in_transit AND allocated orders (allocated means assigned to driver but not yet picked up)
    in_transit = orders_df[orders_df['status'].isin(['in_transit', 'allocated'])]

    # Apply search filter
    if search:
        mask = (
            in_transit['order_id'].str.contains(search, case=False, na=False) |
            in_transit['customer'].str.contains(search, case=False, na=False) |
            in_transit['address'].str.contains(search, case=False, na=False)
        )
        if 'tracking_number' in in_transit.columns:
            mask = mask | in_transit['tracking_number'].str.contains(search, case=False, na=False)
        in_transit = in_transit[mask]

    st.info(f"{len(in_transit)} orders assigned / in transit")

    if in_transit.empty:
        st.info("No orders in transit.")
        return

    for _, order in in_transit.iterrows():
        driver_line = f"Driver: {order['driver_id']}" if order.get('driver_id') else ''
        eta_line = f"ETA {order['eta']}" if order.get('eta') else ''
        status_label = "In Transit" if order['status'] == 'in_transit' else "Assigned"
        badge_class = "status-in-transit" if order['status'] == 'in_transit' else "status-allocated"
        tracking = order.get('tracking_number', '')
        tracking_line = f"<div style='font-family: monospace; font-size: 0.75rem; color: rgba(255,255,255,0.4);'>#{tracking}</div>" if tracking else ''
        created_str = _fmt_sydney(order.get('created_at'))

        st.markdown(f"""
<div class="order-card">
<div style="display: flex; justify-content: space-between; align-items: flex-start;">
<div>
<div class="order-id">{order['order_id']}</div>
{tracking_line}
<div class="order-customer">{order['customer']}</div>
<div class="order-address">{order['address']}, {order.get('suburb', '')} {order.get('postcode', '')}</div>
<div style="margin-top: 0.5rem; font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5);">
{order.get('parcels', 1)} parcel(s) &bull; {order['service_level'].upper()} &bull; Created {created_str}
</div>
</div>
<div style="text-align: right;">
<span class="status-badge {badge_class}">{status_label}</span>
<div style="margin-top: 0.5rem; font-family: 'Space Mono', monospace; font-size: 0.9rem; color: #667eea;">{eta_line}</div>
</div>
</div>
<div style="margin-top: 0.75rem; font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5);">{driver_line}</div>
</div>
""", unsafe_allow_html=True)


def _render_completed(orders_df):
    # Add search field
    search = st.text_input("Search completed orders...", placeholder="Order ID, customer name, tracking number, or address", key="completed_search")

    if orders_df.empty:
        st.info("No orders to display.")
        return

    completed = orders_df[orders_df['status'].isin(['delivered', 'failed'])]

    # Apply search filter
    if search:
        mask = (
            completed['order_id'].str.contains(search, case=False, na=False) |
            completed['customer'].str.contains(search, case=False, na=False) |
            completed['address'].str.contains(search, case=False, na=False)
        )
        if 'tracking_number' in completed.columns:
            mask = mask | completed['tracking_number'].str.contains(search, case=False, na=False)
        completed = completed[mask]

    if completed.empty:
        st.info("No completed orders yet.")
        return

    delivered_count = len(completed[completed['status'] == 'delivered'])
    failed_count = len(completed[completed['status'] == 'failed'])

    col1, col2 = st.columns(2)
    with col1:
        st.success(f"{delivered_count} delivered successfully")
    with col2:
        st.error(f"{failed_count} failed deliveries")

    for _, order in completed.iterrows():
        status_class = "status-delivered" if order['status'] == 'delivered' else "status-failed"
        order_id = order['order_id']

        with st.expander(f"{order_id} - {order['customer']} - {order.get('suburb', '')}", expanded=False):
            col1, col2 = st.columns([2, 1])

            with col1:
                if order.get('tracking_number'):
                    st.markdown(f"**Tracking:** `{order['tracking_number']}`")

                delivered_at_str = _fmt_sydney(order.get('delivered_at')) if order.get('delivered_at') else ''
                created_str = _fmt_sydney(order.get('created_at'))

                st.markdown(f"""
**Customer:** {order['customer']}
**Deliver to:** {order['address']}, {order.get('suburb', '')} {order.get('postcode', '')}
**Parcels:** {order.get('parcels', 1)}
**Created:** {created_str}
                """)

                if delivered_at_str:
                    st.markdown(f"**⏱️ Delivered at:** {delivered_at_str}")

                if order.get('driver_id'):
                    st.markdown(f"**Driver:** {order['driver_id']}")

            with col2:
                st.markdown(f"""
                <span class="status-badge {status_class}">{order['status'].replace('_', ' ')}</span>
                <br><br>
                <span class="status-badge status-{order['service_level']}">{order['service_level']}</span>
                """, unsafe_allow_html=True)

            # Proof of Delivery section
            # Columns stored as proof_photo / proof_signature (raw base64 strings).
            # Support both old (data-URL) and new (raw base64) formats.
            def _as_data_url(b64_or_url, mime="image/jpeg"):
                # Guard: None, NaN, empty string, or non-string values
                if not isinstance(b64_or_url, str) or not b64_or_url.strip():
                    return None
                if b64_or_url.startswith("data:"):
                    return b64_or_url  # already a data URL
                return f"data:{mime};base64,{b64_or_url}"

            # Try new column names first, fall back to old names
            def _pod_val(new_key, old_key):
                v = order.get(new_key)
                if isinstance(v, str) and v.strip():
                    return v
                v = order.get(old_key)
                if isinstance(v, str) and v.strip():
                    return v
                return None

            pod_sig = _as_data_url(_pod_val('proof_signature', 'signature'))
            pod_photo = _as_data_url(_pod_val('proof_photo', 'photo'))

            if pod_sig or pod_photo:
                st.markdown("---")
                st.markdown("### 📸 Proof of Delivery")

                pod_col1, pod_col2 = st.columns(2)

                with pod_col1:
                    if pod_sig:
                        st.markdown("**Customer Signature:**")
                        st.markdown(f'<img src="{pod_sig}" style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px; background: white; padding: 10px;">', unsafe_allow_html=True)

                with pod_col2:
                    if pod_photo:
                        st.markdown("**Delivery Photo:**")
                        st.markdown(f'<img src="{pod_photo}" style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px;">', unsafe_allow_html=True)


def _render_inbound_receipts(data_manager):
    st.markdown('<div class="section-header">Inbound Receipts</div>', unsafe_allow_html=True)
    st.info("Create and manage inbound shipment receipts for the warehouse.")

    with st.form("new_receipt_form"):
        st.markdown("### Create ASN Receipt")
        col1, col2 = st.columns(2)

        with col1:
            shipment_number = st.text_input("Shipment Number *")
            supplier_name = st.text_input("Supplier Name")
            receipt_reference = st.text_input("Receipt Reference")
            due_date = st.date_input("Due Date")

        with col2:
            item_code = st.text_input("Item Code *", key="receipt_item_code")
            expected_qty = st.number_input("Expected Quantity", min_value=1, value=1)
            trade_unit = st.selectbox("Trade Unit Level", ["Unit", "Inner", "Outer", "Pallet"])
            container_type = st.text_input("Container Type")

        submitted = st.form_submit_button("Create Receipt", use_container_width=True, type="primary")

        if submitted:
            if not shipment_number or not item_code:
                st.error("Shipment Number and Item Code are required")
            else:
                receipt_data = {
                    'shipment_number': shipment_number,
                    'supplier_name': supplier_name,
                    'receipt_reference': receipt_reference,
                    'due_date': due_date.strftime('%Y-%m-%d') if due_date else None,
                    'container_type': container_type,
                    'lines': [{
                        'item_code': item_code,
                        'expected_quantity': expected_qty,
                        'trade_unit_level': trade_unit,
                    }],
                }
                result = data_manager.create_receipt(receipt_data)
                if result.get('success'):
                    st.success(f"Receipt {shipment_number} created!")
                    if result.get('wms_pushed'):
                        st.info("Receipt pushed to .wms")
                else:
                    st.error(f"Failed: {result.get('error', 'Unknown error')}")

    # Display existing receipts
    receipts = data_manager.get_receipts()
    if not receipts.empty:
        st.markdown("### Recent Receipts")
        for _, receipt in receipts.iterrows():
            st.markdown(f"""
<div class="order-card">
<div style="display: flex; justify-content: space-between;">
<div>
<div class="order-id">{receipt.get('shipment_number', 'N/A')}</div>
<div class="order-customer">{receipt.get('supplier_name', 'Unknown')}</div>
</div>
<span class="status-badge status-pending">{receipt.get('status', 'pending')}</span>
</div>
</div>
""", unsafe_allow_html=True)
    else:
        st.caption("No receipts yet. Create one above.")
