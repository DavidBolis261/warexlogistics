import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from config.constants import ZONE_MAPPING


def render(orders_df, drivers_df, data_manager):
    st.markdown('<div class="section-header">Performance Analytics</div>', unsafe_allow_html=True)

    # ── Date range selector ──────────────────────────────────
    col1, col2, col3 = st.columns([1, 1, 2])
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        quick = st.selectbox(
            "Quick select",
            ["Custom", "Last 7 days", "Last 30 days", "This month", "Last quarter"],
            index=1,
        )

    # Compute default start/end from quick select
    today = datetime.now().date()
    if quick == "Last 7 days":
        default_start = today - timedelta(days=7)
        default_end = today
    elif quick == "Last 30 days":
        default_start = today - timedelta(days=30)
        default_end = today
    elif quick == "This month":
        default_start = today.replace(day=1)
        default_end = today
    elif quick == "Last quarter":
        default_start = today - timedelta(days=90)
        default_end = today
    else:
        default_start = today - timedelta(days=30)
        default_end = today

    with col1:
        start_date = st.date_input("From", default_start)
    with col2:
        end_date = st.date_input("To", default_end)

    # ── Filter orders by date range ──────────────────────────
    filtered_df = orders_df.copy() if not orders_df.empty else pd.DataFrame()

    if not filtered_df.empty and 'created_at' in filtered_df.columns:
        filtered_df['_date'] = pd.to_datetime(filtered_df['created_at'], errors='coerce').dt.date
        filtered_df = filtered_df[
            (filtered_df['_date'] >= start_date) &
            (filtered_df['_date'] <= end_date)
        ]
    elif not filtered_df.empty and 'order_date' in filtered_df.columns:
        filtered_df['_date'] = pd.to_datetime(filtered_df['order_date'], errors='coerce').dt.date
        filtered_df = filtered_df[
            (filtered_df['_date'] >= start_date) &
            (filtered_df['_date'] <= end_date)
        ]

    # ── Key performance metrics ──────────────────────────────
    if not filtered_df.empty and 'status' in filtered_df.columns:
        total_orders = len(filtered_df)
        total_delivered = len(filtered_df[filtered_df['status'] == 'delivered'])
        total_pending = len(filtered_df[filtered_df['status'] == 'pending'])
        failed_count = len(filtered_df[filtered_df['status'] == 'failed'])
        success_rate = round(total_delivered / total_orders * 100, 1) if total_orders > 0 else 0
    else:
        total_orders = total_delivered = total_pending = failed_count = 0
        success_rate = 0

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_orders}</div>
            <div class="metric-label">Total Orders</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{success_rate}%</div>
            <div class="metric-label">Success Rate</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_delivered}</div>
            <div class="metric-label">Delivered</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        avg_rating = round(drivers_df['rating'].mean(), 1) if not drivers_df.empty and 'rating' in drivers_df.columns else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{avg_rating}</div>
            <div class="metric-label">Avg Driver Rating</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{failed_count}</div>
            <div class="metric-label">Failed</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts ───────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Orders Over Time")

        if not filtered_df.empty and '_date' in filtered_df.columns:
            daily = (
                filtered_df
                .groupby('_date')
                .size()
                .reset_index(name='Orders')
            )
            daily.columns = ['Date', 'Orders']
            daily['Date'] = pd.to_datetime(daily['Date'])
            daily = daily.sort_values('Date')
            st.line_chart(daily.set_index('Date'), use_container_width=True)
        else:
            st.info("No order data in the selected date range.")

    with col2:
        st.markdown("### Orders by Zone")

        if not filtered_df.empty and 'suburb' in filtered_df.columns:
            # Map each order's suburb back to its zone
            suburb_to_zone = {}
            for zone, suburbs in ZONE_MAPPING.items():
                for suburb in suburbs:
                    suburb_to_zone[suburb] = zone

            filtered_df['_zone'] = filtered_df['suburb'].map(suburb_to_zone).fillna('Other')
            zone_counts = (
                filtered_df
                .groupby('_zone')
                .size()
                .reset_index(name='Orders')
            )
            zone_counts.columns = ['Zone', 'Orders']
            zone_counts = zone_counts.sort_values('Orders', ascending=False)
            st.bar_chart(zone_counts.set_index('Zone'), use_container_width=True)
        else:
            st.info("No order data to display zone breakdown.")

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Service Level Distribution")

        if not filtered_df.empty and 'service_level' in filtered_df.columns:
            service_counts = filtered_df['service_level'].value_counts()
            service_data = pd.DataFrame({
                'Service': service_counts.index.str.capitalize(),
                'Count': service_counts.values
            })
            st.bar_chart(service_data.set_index('Service'), use_container_width=True)
        else:
            st.info("No order data for service level breakdown.")

    with col2:
        st.markdown("### Order Status Breakdown")

        if not filtered_df.empty and 'status' in filtered_df.columns:
            status_counts = filtered_df['status'].value_counts()
            status_data = pd.DataFrame({
                'Status': status_counts.index.str.replace('_', ' ').str.capitalize(),
                'Count': status_counts.values
            })
            st.bar_chart(status_data.set_index('Status'), use_container_width=True)
        else:
            st.info("No order data for status breakdown.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Driver Performance ───────────────────────────────────
    st.markdown("### Driver Performance")

    if not drivers_df.empty:
        perf_cols = ['name']
        display_cols = ['Driver']

        if 'deliveries_today' in drivers_df.columns:
            perf_cols.append('deliveries_today')
            display_cols.append('Deliveries')
        if 'active_orders' in drivers_df.columns:
            perf_cols.append('active_orders')
            display_cols.append('Active')
        if 'success_rate' in drivers_df.columns:
            perf_cols.append('success_rate')
            display_cols.append('Success %')
        if 'rating' in drivers_df.columns:
            perf_cols.append('rating')
            display_cols.append('Rating')
        if 'status' in drivers_df.columns:
            perf_cols.append('status')
            display_cols.append('Status')

        driver_perf = drivers_df[perf_cols].copy()
        driver_perf.columns = display_cols

        if 'Success %' in driver_perf.columns:
            driver_perf['Success %'] = driver_perf['Success %'].apply(
                lambda x: round(x * 100, 1) if x <= 1 else round(x, 1)
            )

        sort_col = 'Deliveries' if 'Deliveries' in driver_perf.columns else 'Driver'
        st.dataframe(
            driver_perf.sort_values(sort_col, ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No drivers registered yet. Add drivers in the Drivers tab.")

    # ── API Log ──────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)

    api_log = data_manager.get_api_log()
    if not api_log.empty:
        st.markdown("### API Operation Log")
        st.dataframe(api_log.tail(20), use_container_width=True, hide_index=True)
