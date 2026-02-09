import streamlit as st


def render(data_manager):
    st.markdown('<div class="section-header">Inventory Management</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Item Master", "ULD Management", "Stock Adjustments", "Kitting",
    ])

    with tab1:
        _render_item_master(data_manager)

    with tab2:
        _render_uld_management(data_manager)

    with tab3:
        _render_stock_adjustments(data_manager)

    with tab4:
        _render_kitting(data_manager)


def _render_item_master(data_manager):
    st.markdown("### Item Master Data")
    st.caption("Create, update, or delete items in the .wms system.")

    with st.form("upsert_item_form"):
        st.markdown("#### Create / Update Item")
        col1, col2 = st.columns(2)

        with col1:
            item_code = st.text_input("Item Code (SKU) *")
            item_name = st.text_input("Item Name *")
            item_group = st.text_input("Item Group")
            barcode = st.text_input("Barcode / GTIN")

        with col2:
            item_weight = st.number_input("Weight (kg)", min_value=0.0, value=0.0, step=0.01)
            item_length = st.number_input("Length (cm)", min_value=0.0, value=0.0, step=0.1)
            item_width = st.number_input("Width (cm)", min_value=0.0, value=0.0, step=0.1)
            item_height = st.number_input("Height (cm)", min_value=0.0, value=0.0, step=0.1)

        col1, col2 = st.columns(2)
        with col1:
            unit_of_measure = st.selectbox("Unit of Measure", ["Each", "Box", "Carton", "Pallet", "Kg", "Litre"])
            inner_qty = st.number_input("Inner Pack Quantity", min_value=0, value=0)
        with col2:
            outer_qty = st.number_input("Outer Pack Quantity", min_value=0, value=0)
            pallet_qty = st.number_input("Pallet Quantity", min_value=0, value=0)

        submitted = st.form_submit_button("Save Item to WMS", use_container_width=True, type="primary")

        if submitted:
            if not item_code or not item_name:
                st.error("Item Code and Item Name are required")
            else:
                result = data_manager.upsert_item({
                    'item_code': item_code,
                    'item_name': item_name,
                    'item_group': item_group,
                    'barcode': barcode,
                    'weight': item_weight,
                    'length': item_length,
                    'width': item_width,
                    'height': item_height,
                    'unit_of_measure': unit_of_measure,
                    'inner_qty': inner_qty,
                    'outer_qty': outer_qty,
                    'pallet_qty': pallet_qty,
                })
                if result.get('success'):
                    st.success(f"Item {item_code} saved!")
                    if result.get('wms_pushed'):
                        st.info("Pushed to .wms")
                else:
                    st.error(f"Failed: {result.get('error', 'Unknown error')}")

    # Delete item
    st.markdown("---")
    st.markdown("#### Delete Item")
    st.caption("Only possible if the item has no receipts, orders, or stock in .wms.")
    col1, col2 = st.columns([3, 1])
    with col1:
        delete_item_code = st.text_input("Item Code to delete", key="delete_item")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Delete Item", type="secondary"):
            if delete_item_code:
                result = data_manager.delete_item(delete_item_code)
                if result.get('success'):
                    st.success(f"Item {delete_item_code} deleted")
                else:
                    st.error(f"Failed: {result.get('error', 'Unknown error')}")

    # Items list
    items = data_manager.get_items()
    if not items.empty:
        st.markdown("### Items in Local Store")
        st.dataframe(items, use_container_width=True, hide_index=True)


def _render_uld_management(data_manager):
    st.markdown("### Unit Load Device (ULD) Management")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Create ULD")
        with st.form("create_uld_form"):
            uld_barcode = st.text_input("ULD Barcode (optional, auto-generated if empty)")
            bin_code = st.text_input("Bin Location")
            uld_held_reason = st.text_input("Hold Reason (optional)")

            st.markdown("**Initial Stock (optional)**")
            uld_item_code = st.text_input("Item Code", key="uld_item")
            uld_quantity = st.number_input("Quantity", min_value=0, value=0, key="uld_qty")
            uld_batch = st.text_input("Batch Number", key="uld_batch")

            submitted = st.form_submit_button("Create ULD", use_container_width=True, type="primary")

            if submitted:
                uld_data = {
                    'barcode': uld_barcode,
                    'bin_code': bin_code,
                    'held_reason': uld_held_reason,
                }
                if uld_item_code and uld_quantity > 0:
                    uld_data['lines'] = [{
                        'item_code': uld_item_code,
                        'quantity': uld_quantity,
                        'batch_number': uld_batch,
                    }]
                result = data_manager.create_uld(uld_data)
                if result.get('success'):
                    st.success("ULD created!")
                else:
                    st.error(f"Failed: {result.get('error', 'Unknown error')}")

    with col2:
        st.markdown("#### Move ULD")
        with st.form("move_uld_form"):
            move_barcode = st.text_input("ULD Barcode *", key="move_barcode")
            new_location = st.text_input("New Location / Bin Code *")

            submitted = st.form_submit_button("Move ULD", use_container_width=True)

            if submitted:
                if move_barcode and new_location:
                    result = data_manager.move_uld(move_barcode, new_location)
                    if result.get('success'):
                        st.success(f"ULD {move_barcode} moved to {new_location}")
                    else:
                        st.error(f"Failed: {result.get('error', 'Unknown error')}")
                else:
                    st.error("Barcode and new location are required")

        st.markdown("#### Destroy ULD")
        with st.form("destroy_uld_form"):
            destroy_barcode = st.text_input("ULD Barcode *", key="destroy_barcode")
            st.warning("This action is irreversible!")

            submitted = st.form_submit_button("Destroy ULD", use_container_width=True)

            if submitted:
                if destroy_barcode:
                    result = data_manager.destroy_uld(destroy_barcode)
                    if result.get('success'):
                        st.success(f"ULD {destroy_barcode} destroyed")
                    else:
                        st.error(f"Failed: {result.get('error', 'Unknown error')}")


def _render_stock_adjustments(data_manager):
    st.markdown("### Stock Adjustments")
    st.caption("Adjust stock on a specific ULD. Creates an 'Adjustment from API' transaction in .wms.")

    with st.form("adjust_stock_form"):
        col1, col2 = st.columns(2)

        with col1:
            adj_uld_barcode = st.text_input("ULD Barcode *")
            adj_item_code = st.text_input("Item Code *", key="adj_item")
            adj_quantity = st.number_input(
                "Adjust Quantity (positive to add, negative to remove)",
                value=0, step=1,
            )

        with col2:
            adj_batch = st.text_input("Batch Number")
            adj_serial = st.text_input("Serial Number")
            adj_comment = st.text_area("Comment / Reason")
            allow_negatives = st.checkbox("Allow negative stock")

        submitted = st.form_submit_button("Submit Adjustment", use_container_width=True, type="primary")

        if submitted:
            if not adj_uld_barcode or not adj_item_code or adj_quantity == 0:
                st.error("ULD Barcode, Item Code, and a non-zero quantity are required")
            else:
                result = data_manager.adjust_stock({
                    'uld_barcode': adj_uld_barcode,
                    'item_code': adj_item_code,
                    'quantity': adj_quantity,
                    'batch_number': adj_batch,
                    'serial_number': adj_serial,
                    'comment': adj_comment,
                    'allow_negatives': 'Yes' if allow_negatives else 'No',
                })
                if result.get('success'):
                    st.success("Stock adjustment submitted!")
                else:
                    st.error(f"Failed: {result.get('error', 'Unknown error')}")


def _render_kitting(data_manager):
    st.markdown("### Kitting Jobs")
    st.caption("Create kitting or dekitting work orders for composite items.")

    with st.form("kitting_job_form"):
        col1, col2 = st.columns(2)

        with col1:
            kit_type = st.selectbox("Kitting Type", ["Kitting", "Dekitting"])
            pack_slip = st.text_input("Pack Slip Number *")
            order_number = st.text_input("Order Number")
            order_date = st.date_input("Order Date")

        with col2:
            job_priority = st.number_input("Job Priority", min_value=1, value=1)
            packer_message = st.text_area("Packer Message")

        st.markdown("#### Kit Items")
        kit_item_code = st.text_input("Composite Item Code *", key="kit_item")
        kit_quantity = st.number_input("Quantity", min_value=1, value=1, key="kit_qty")

        submitted = st.form_submit_button("Create Kitting Job", use_container_width=True, type="primary")

        if submitted:
            if not pack_slip or not kit_item_code:
                st.error("Pack Slip Number and Item Code are required")
            else:
                result = data_manager.create_kitting_job({
                    'kitting_type': kit_type,
                    'pack_slip_number': pack_slip,
                    'order_number': order_number,
                    'order_date': order_date.strftime('%Y-%m-%d'),
                    'job_priority': job_priority,
                    'packer_message': packer_message,
                    'lines': [{
                        'item_code': kit_item_code,
                        'quantity': kit_quantity,
                    }],
                })
                if result.get('success'):
                    st.success("Kitting job created!")
                else:
                    st.error(f"Failed: {result.get('error', 'Unknown error')}")
