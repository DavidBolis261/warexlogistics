import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def render(orders_df, drivers_df, data_manager):
    st.markdown('<div class="section-header">Performance Analytics</div>', unsafe_allow_html=True)

    # Date range selector
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        start_date = st.date_input("From", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("To", datetime.now())
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        time_period = st.selectbox("Quick select", ["Last 7 days", "Last 30 days", "This month", "Last quarter"])

    # Key performance metrics from local store or computed
    total_delivered = len(orders_df[orders_df['status'] == 'delivered'])
    total_orders = len(orders_df)
    success_rate = round(total_delivered / total_orders * 100, 1) if total_orders > 0 else 0
    failed_count = len(orders_df[orders_df['status'] == 'failed'])

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
        avg_rating = round(drivers_df['rating'].mean(), 1) if not drivers_df.empty else 0
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
            <div class="metric-change negative">Needs review</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Deliveries Over Time")

        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=30, freq='D')
        deliveries = np.random.randint(30, 60, 30) + np.sin(np.arange(30) * 0.3) * 10

        chart_data = pd.DataFrame({
            'Date': dates,
            'Deliveries': deliveries.astype(int)
        })

        st.line_chart(chart_data.set_index('Date'), use_container_width=True)

    with col2:
        st.markdown("### Deliveries by Zone")

        zone_data = pd.DataFrame({
            'Zone': ['Inner West', 'Eastern Suburbs', 'CBD', 'South Sydney', 'Inner City'],
            'Deliveries': [312, 428, 287, 156, 64]
        })

        st.bar_chart(zone_data.set_index('Zone'), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Service Level Distribution")

        if not orders_df.empty:
            service_counts = orders_df['service_level'].value_counts()
            service_data = pd.DataFrame({
                'Service': service_counts.index.str.capitalize(),
                'Count': service_counts.values
            })
        else:
            service_data = pd.DataFrame({
                'Service': ['Express', 'Standard', 'Economy'],
                'Count': [0, 0, 0]
            })

        st.bar_chart(service_data.set_index('Service'), use_container_width=True)

    with col2:
        st.markdown("### Driver Performance")

        driver_perf = drivers_df[['name', 'deliveries_today', 'success_rate', 'rating']].copy()
        driver_perf.columns = ['Driver', 'Deliveries', 'Success %', 'Rating']
        driver_perf['Success %'] = (driver_perf['Success %'] * 100).round(1)

        st.dataframe(
            driver_perf.sort_values('Deliveries', ascending=False),
            use_container_width=True,
            hide_index=True,
        )

    # Export options
    st.markdown("<br>", unsafe_allow_html=True)

    # API Log
    api_log = data_manager.get_api_log()
    if not api_log.empty:
        st.markdown("### API Operation Log")
        st.dataframe(api_log.tail(20), use_container_width=True, hide_index=True)
