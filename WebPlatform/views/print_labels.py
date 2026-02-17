"""
Print shipping labels view.
"""

import streamlit as st
import streamlit.components.v1 as components
from utils.qr_code import generate_shipping_label_html


def render(data_manager):
    """Render print labels page."""
    st.markdown('<div class="section-header">Print Shipping Labels</div>', unsafe_allow_html=True)

    # Get orders
    orders_df = data_manager.get_orders()

    if orders_df.empty:
        st.info("No orders to print labels for.")
        return

    # Filter options
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.multiselect(
            "Filter by Status",
            options=['pending', 'allocated', 'in_transit', 'delivered', 'failed'],
            default=['pending', 'allocated']
        )

    with col2:
        if 'driver_id' in orders_df.columns:
            drivers = orders_df['driver_id'].dropna().unique().tolist()
            driver_filter = st.multiselect(
                "Filter by Driver",
                options=['All'] + drivers,
                default=['All']
            )
        else:
            driver_filter = ['All']

    with col3:
        zone_filter = st.multiselect(
            "Filter by Zone",
            options=['All', 'Inner West', 'CBD', 'North', 'South', 'West'],
            default=['All']
        )

    # Apply filters
    filtered_df = orders_df.copy()

    if status_filter:
        filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]

    if 'driver_id' in filtered_df.columns and driver_filter and 'All' not in driver_filter:
        filtered_df = filtered_df[filtered_df['driver_id'].isin(driver_filter)]

    if zone_filter and 'All' not in zone_filter and 'zone' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['zone'].isin(zone_filter)]

    st.markdown(f"**{len(filtered_df)} labels to print**")

    if filtered_df.empty:
        st.warning("No orders match the selected filters.")
        return

    # Show ALL labels on screen (not just a single preview)
    st.markdown("### All Labels")

    all_labels_inner_html = ""
    for _, order in filtered_df.iterrows():
        order_dict = order.to_dict()
        all_labels_inner_html += generate_shipping_label_html(order_dict)

    # Render all labels in an iframe with scroll
    label_height = min(800, len(filtered_df) * 350)
    components.html(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin: 0; padding: 20px; background: #f5f5f5; font-family: sans-serif; }}
            .label-count {{ font-size: 14px; color: #555; margin-bottom: 16px; }}
        </style>
    </head>
    <body>
        <div class="label-count">{len(filtered_df)} label(s) shown below</div>
        {all_labels_inner_html}
    </body>
    </html>
    """, height=max(400, label_height), scrolling=True)

    # Print / Download button
    if st.button("🖨️ Print All Labels", type="primary", use_container_width=True):
        # Generate all labels
        all_labels_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Shipping Labels</title>
            <style>
                @media print {
                    @page {
                        size: 4in 6in;
                        margin: 0;
                    }
                    body {
                        margin: 0;
                        padding: 0;
                    }
                }
            </style>
        </head>
        <body>
        """

        for _, order in filtered_df.iterrows():
            order_dict = order.to_dict()
            all_labels_html += generate_shipping_label_html(order_dict)

        all_labels_html += """
        </body>
        </html>
        """

        # Create download button
        st.download_button(
            label="📥 Download Labels as HTML",
            data=all_labels_html,
            file_name="shipping_labels.html",
            mime="text/html",
            use_container_width=True
        )

        st.success(f"✅ Generated {len(filtered_df)} shipping labels! Download the HTML file and open it in your browser, then use Ctrl+P (or Cmd+P) to print.")

        # JavaScript to open print dialog
        st.markdown("""
        <script>
        // Auto-open print dialog when labels are generated
        if (window.labelsGenerated) {
            window.print();
        }
        window.labelsGenerated = true;
        </script>
        """, unsafe_allow_html=True)
