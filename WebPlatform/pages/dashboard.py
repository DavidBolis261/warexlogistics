import streamlit as st
from datetime import datetime


def render(orders_df, drivers_df, runs_df):
    # Key Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total_orders = len(orders_df)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_orders}</div>
            <div class="metric-label">Total Orders</div>
            <div class="metric-change positive">Today's orders</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        pending = len(orders_df[orders_df['status'] == 'pending'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{pending}</div>
            <div class="metric-label">Pending</div>
            <div class="metric-change negative">Needs attention</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        in_transit = len(orders_df[orders_df['status'] == 'in_transit'])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{in_transit}</div>
            <div class="metric-label">In Transit</div>
            <div class="metric-change positive">On track</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        delivered = len(orders_df[orders_df['status'] == 'delivered'])
        delivery_rate = round(delivered / total_orders * 100) if total_orders > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{delivery_rate}%</div>
            <div class="metric-label">Delivered</div>
            <div class="metric-change positive">{delivered} completed</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        active_drivers = len(drivers_df[drivers_df['status'].isin(['available', 'on_route'])])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{active_drivers}</div>
            <div class="metric-label">Active Drivers</div>
            <div class="metric-change positive">Online now</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Main content area
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown('<div class="section-header">Live Delivery Map</div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="zone-map">
            <div style="position: relative; z-index: 1; text-align: center;">
                <div style="font-family: 'DM Sans', sans-serif; font-size: 1.5rem; color: white; margin-bottom: 1rem;">
                    Sydney Metro Zones
                </div>
                <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                    <div style="background: rgba(102, 126, 234, 0.2); padding: 0.75rem 1.25rem; border-radius: 8px; border: 1px solid rgba(102, 126, 234, 0.3);">
                        <div style="font-family: 'Space Mono', monospace; color: #667eea; font-weight: 700;">CBD</div>
                        <div style="font-family: 'DM Sans', sans-serif; color: rgba(255,255,255,0.6); font-size: 0.8rem;">12 active</div>
                    </div>
                    <div style="background: rgba(16, 185, 129, 0.2); padding: 0.75rem 1.25rem; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.3);">
                        <div style="font-family: 'Space Mono', monospace; color: #10b981; font-weight: 700;">Inner West</div>
                        <div style="font-family: 'DM Sans', sans-serif; color: rgba(255,255,255,0.6); font-size: 0.8rem;">8 active</div>
                    </div>
                    <div style="background: rgba(251, 191, 36, 0.2); padding: 0.75rem 1.25rem; border-radius: 8px; border: 1px solid rgba(251, 191, 36, 0.3);">
                        <div style="font-family: 'Space Mono', monospace; color: #fbbf24; font-weight: 700;">Eastern</div>
                        <div style="font-family: 'DM Sans', sans-serif; color: rgba(255,255,255,0.6); font-size: 0.8rem;">15 active</div>
                    </div>
                    <div style="background: rgba(239, 68, 68, 0.2); padding: 0.75rem 1.25rem; border-radius: 8px; border: 1px solid rgba(239, 68, 68, 0.3);">
                        <div style="font-family: 'Space Mono', monospace; color: #ef4444; font-weight: 700;">South</div>
                        <div style="font-family: 'DM Sans', sans-serif; color: rgba(255,255,255,0.6); font-size: 0.8rem;">10 active</div>
                    </div>
                </div>
                <div style="margin-top: 1.5rem; font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.4);">
                    Map integration pending
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Active Runs
        st.markdown('<div class="section-header">Active Delivery Runs</div>', unsafe_allow_html=True)

        active_runs = runs_df[runs_df['status'] == 'active'].head(5)

        for _, run in active_runs.iterrows():
            progress_color = "#10b981" if run['progress'] > 70 else "#fbbf24" if run['progress'] > 40 else "#3b82f6"
            st.markdown(f"""
            <div class="order-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div class="order-id">{run['run_id']}</div>
                        <div class="order-customer">{run['driver_name']} &bull; {run['zone']}</div>
                        <div class="order-address">{run['completed']}/{run['total_stops']} stops &bull; ETA {run['estimated_completion']}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-family: 'Space Mono', monospace; font-size: 1.5rem; color: {progress_color}; font-weight: 700;">{run['progress']}%</div>
                    </div>
                </div>
                <div style="margin-top: 0.75rem; background: rgba(255,255,255,0.1); border-radius: 4px; height: 6px; overflow: hidden;">
                    <div style="background: {progress_color}; height: 100%; width: {run['progress']}%; border-radius: 4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-header">Pending Orders</div>', unsafe_allow_html=True)

        pending_orders = orders_df[orders_df['status'] == 'pending'].head(6)

        for _, order in pending_orders.iterrows():
            priority_class = f"priority-{order['service_level']}"
            st.markdown(f"""
            <div class="order-card {priority_class}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div class="order-id">{order['order_id']}</div>
                        <div class="order-customer">{order['customer']}</div>
                        <div class="order-address">{order['address']}, {order['suburb']} {order['postcode']}</div>
                    </div>
                    <span class="status-badge status-pending">{order['service_level']}</span>
                </div>
                <div style="margin-top: 0.75rem; font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5);">
                    {order['parcels']} parcel(s) &bull; {order['created_at'].strftime('%H:%M')}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Driver Status</div>', unsafe_allow_html=True)

        for _, driver in drivers_df.head(5).iterrows():
            status_class = f"status-{driver['status'].replace('_', '-')}"
            st.markdown(f"""
            <div class="driver-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div class="driver-name">{driver['name']}</div>
                        <div class="driver-vehicle">{driver['vehicle_type']} &bull; {driver['plate']}</div>
                    </div>
                    <span class="status-badge {status_class}">{driver['status'].replace('_', ' ')}</span>
                </div>
                <div class="driver-stats">
                    <div class="driver-stat">
                        <div class="driver-stat-value">{driver['deliveries_today']}</div>
                        <div class="driver-stat-label">Today</div>
                    </div>
                    <div class="driver-stat">
                        <div class="driver-stat-value">{driver['active_orders']}</div>
                        <div class="driver-stat-label">Active</div>
                    </div>
                    <div class="driver-stat">
                        <div class="driver-stat-value">{driver['rating']}</div>
                        <div class="driver-stat-label">Rating</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
