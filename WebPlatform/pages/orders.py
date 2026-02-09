import streamlit as st
from datetime import datetime

from config.constants import ZONE_MAPPING


def render(orders_df, drivers_df, data_manager, zone_filter, service_filter, status_filter):
    st.markdown('<div class="section-header">Order Management</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "All Orders", "Pending Allocation", "In Transit", "Completed", "Inbound Receipts",
    ])

    filtered_df = orders_df.copy()

    # Apply filters from sidebar
    if zone_filter:
        selected_suburbs = []
        for zone in zone_filter:
            selected_suburbs.extend(ZONE_MAPPING.get(zone, []))
        if selected_suburbs:
            filtered_df = filtered_df[filtered_df['suburb'].isin(selected_suburbs)]

    if service_filter:
        filtered_df = filtered_df[filtered_df['service_level'].isin(service_filter)]

    if status_filter:
        filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]

    with tab1:
        _render_all_orders(filtered_df, data_manager)

    with tab2:
        _render_pending(filtered_df, drivers_df, data_manager)

    with tab3:
        _render_in_transit(filtered_df)

    with tab4:
        _render_completed(filtered_df)

    with tab5:
        _render_inbound_receipts(data_manager)


def _render_all_orders(orders_df, data_manager):
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("Search orders...", placeholder="Order ID, customer name, or address")
    with col2:
        sort_by = st.selectbox("Sort by", ["Created (newest)", "Created (oldest)", "Service Level", "Status"])
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("New Order", use_container_width=True):
            st.session_state['show_new_order_form'] = True

    if search:
        orders_df = orders_df[
            orders_df['order_id'].str.contains(search, case=False) |
            orders_df['customer'].str.contains(search, case=False) |
            orders_df['address'].str.contains(search, case=False)
        ]

    # New order form
    if st.session_state.get('show_new_order_form'):
        _render_new_order_form(data_manager)

    for _, order in orders_df.iterrows():
        status_class = f"status-{order['status'].replace('_', '-')}"

        with st.expander(f"{order['order_id']} - {order['customer']} - {order['suburb']}", expanded=False):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"""
                **Customer:** {order['customer']}
                **Address:** {order['address']}, {order['suburb']} {order['postcode']}
                **Parcels:** {order['parcels']}
                **Created:** {order['created_at'].strftime('%Y-%m-%d %H:%M')}
                """)

                if order['driver_id']:
                    st.markdown(f"**Assigned Driver:** {order['driver_id']}")
                if order['eta']:
                    st.markdown(f"**ETA:** {order['eta']}")

            with col2:
                st.markdown(f"""
                <span class="status-badge {status_class}">{order['status'].replace('_', ' ')}</span>
                <br><br>
                <span class="status-badge status-{order['service_level']}">{order['service_level']}</span>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                if order['status'] == 'pending':
                    if st.button("Push to WMS", key=f"push_{order['order_id']}"):
                        result = data_manager.push_order_to_wms(order.to_dict())
                        if result.get('success'):
                            st.success("Pushed to .wms successfully")
                        elif result.get('mock'):
                            st.info("Demo mode - order saved locally")
                        else:
                            st.error(f"Failed: {result.get('error', 'Unknown error')}")

                if order['status'] in ['pending', 'allocated']:
                    if st.button("Cancel Order", key=f"cancel_{order['order_id']}"):
                        result = data_manager.cancel_order(order['order_id'])
                        if result.get('success'):
                            st.success("Order cancelled")
                            st.rerun()
                        else:
                            st.error(f"Failed: {result.get('error', 'Unknown error')}")


def _render_new_order_form(data_manager):
    st.markdown('<div class="section-header">Create New Order</div>', unsafe_allow_html=True)

    with st.form("new_order_form"):
        col1, col2 = st.columns(2)

        with col1:
            customer_name = st.text_input("Customer Name *")
            delivery_company = st.text_input("Company (optional)")
            address1 = st.text_input("Address Line 1 *")
            address2 = st.text_input("Address Line 2")
            suburb = st.text_input("Suburb *")

        with col2:
            state = st.selectbox("State", ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"])
            postcode = st.text_input("Postcode *")
            country = st.text_input("Country", value="Australia")
            email = st.text_input("Email")
            phone = st.text_input("Phone")

        st.markdown("### Order Details")
        col1, col2, col3 = st.columns(3)

        with col1:
            service_level = st.selectbox("Service Level", ["standard", "express", "economy"])
        with col2:
            item_code = st.text_input("Item Code / SKU", value="PARCEL")
            quantity = st.number_input("Quantity", min_value=1, value=1)
        with col3:
            carrier_service = st.text_input("Carrier Service Code (optional)")
            special_instructions = st.text_area("Special Instructions", height=68)

        submitted = st.form_submit_button("Create Order", use_container_width=True, type="primary")

        if submitted:
            if not customer_name or not address1 or not suburb or not postcode:
                st.error("Please fill in all required fields (marked with *)")
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
                }
                result = data_manager.create_order(order_data)
                if result.get('success'):
                    st.success(f"Order {result.get('order_id', '')} created successfully!")
                    if result.get('wms_pushed'):
                        st.info("Order pushed to .wms")
                    st.session_state['show_new_order_form'] = False
                    st.rerun()
                else:
                    st.error(f"Failed to create order: {result.get('error', 'Unknown error')}")


def _render_pending(orders_df, drivers_df, data_manager):
    pending = orders_df[orders_df['status'] == 'pending']
    st.info(f"{len(pending)} orders awaiting allocation")

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_orders = st.multiselect(
            "Select orders for bulk allocation",
            pending['order_id'].tolist()
        )
    with col2:
        driver_options = drivers_df[drivers_df['status'] == 'available']['name'].tolist()
        assigned_driver = st.selectbox("Assign to driver", ["Select driver..."] + driver_options)

    if st.button("Allocate Selected Orders", disabled=not selected_orders or assigned_driver == "Select driver..."):
        for oid in selected_orders:
            data_manager.allocate_order(oid, assigned_driver)
        st.success(f"{len(selected_orders)} orders allocated to {assigned_driver}")
        st.rerun()

    for _, order in pending.iterrows():
        st.markdown(f"""
        <div class="order-card priority-{order['service_level']}">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div class="order-id">{order['order_id']}</div>
                    <div class="order-customer">{order['customer']}</div>
                    <div class="order-address">{order['address']}, {order['suburb']} {order['postcode']}</div>
                    <div style="margin-top: 0.5rem; font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5);">
                        {order['parcels']} parcel(s) &bull; {order['service_level'].upper()}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_in_transit(orders_df):
    in_transit = orders_df[orders_df['status'] == 'in_transit']
    st.info(f"{len(in_transit)} orders currently in transit")

    for _, order in in_transit.iterrows():
        st.markdown(f"""
        <div class="order-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div class="order-id">{order['order_id']}</div>
                    <div class="order-customer">{order['customer']}</div>
                    <div class="order-address">{order['address']}, {order['suburb']} {order['postcode']}</div>
                </div>
                <div style="text-align: right;">
                    <span class="status-badge status-in-transit">In Transit</span>
                    <div style="margin-top: 0.5rem; font-family: 'Space Mono', monospace; font-size: 0.9rem; color: #667eea;">
                        ETA {order['eta']}
                    </div>
                </div>
            </div>
            <div style="margin-top: 0.75rem; display: flex; justify-content: space-between; align-items: center;">
                <div style="font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5);">
                    Driver: {order['driver_id']}
                </div>
                <div class="live-indicator">
                    <div class="live-dot"></div>
                    Live tracking
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_completed(orders_df):
    completed = orders_df[orders_df['status'].isin(['delivered', 'failed'])]
    delivered_count = len(completed[completed['status'] == 'delivered'])
    failed_count = len(completed[completed['status'] == 'failed'])

    col1, col2 = st.columns(2)
    with col1:
        st.success(f"{delivered_count} delivered successfully")
    with col2:
        st.error(f"{failed_count} failed deliveries")

    for _, order in completed.iterrows():
        status_class = "status-delivered" if order['status'] == 'delivered' else "status-failed"
        st.markdown(f"""
        <div class="order-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div class="order-id">{order['order_id']}</div>
                    <div class="order-customer">{order['customer']}</div>
                    <div class="order-address">{order['address']}, {order['suburb']}</div>
                </div>
                <span class="status-badge {status_class}">{order['status']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


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
