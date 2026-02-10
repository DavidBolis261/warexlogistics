"""
Sydney Metro Courier Dashboard
A comprehensive logistics management interface integrated with Thomax .wms API
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from datetime import datetime

from components.styles import apply_styles
from config.settings import wms_config
from data.data_manager import DataManager

# Page configuration
st.set_page_config(
    page_title="Sydney Metro Courier",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom CSS
apply_styles()

# Initialize data manager (singleton per session)
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()

dm = st.session_state.data_manager

# Initialize data mode (persist across refreshes by defaulting to Local)
if 'data_mode' not in st.session_state:
    if wms_config.is_configured:
        st.session_state['data_mode'] = 'Live (push to .wms + local store)'
    else:
        st.session_state['data_mode'] = 'Local Only (SQLite)'

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem 0;">
        <div style="font-size: 2.5rem;">📦</div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 1.25rem; font-weight: 700; color: white; margin-top: 0.5rem;">
            Sydney Metro
        </div>
        <div style="font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 2px;">
            Courier System
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "📋 Orders",
            "🚚 Drivers",
            "🗺️ Route Planning",
            "📦 Inventory",
            "📈 Analytics",
            "⚙️ Settings",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Quick filters
    st.markdown("### Quick Filters")

    zone_filter = st.multiselect(
        "Zones",
        ["Inner West", "Eastern Suburbs", "CBD", "South Sydney", "Inner City"],
        default=[],
    )

    service_filter = st.multiselect(
        "Service Level",
        ["express", "standard", "economy"],
        default=[],
    )

    status_filter = st.multiselect(
        "Status",
        ["pending", "allocated", "in_transit", "delivered", "failed"],
        default=[],
    )

    st.markdown("---")

    # Connection status
    if wms_config.is_configured:
        mode = dm.data_mode
        if mode == 'live':
            dot_color = "#10b981"
            label = "Live - WMS Connected"
        elif mode == 'local':
            dot_color = "#fbbf24"
            label = "Local Only"
        else:
            dot_color = "#6b7280"
            label = "Demo Mode"
    else:
        dot_color = "#6b7280"
        label = "Demo Mode"

    st.markdown(f"""
    <div class="live-indicator" style="color: {dot_color};">
        <div class="live-dot" style="background: {dot_color};"></div>
        {label}
    </div>
    """, unsafe_allow_html=True)

    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()


# ============================================
# LOAD DATA
# ============================================

orders_df = dm.get_orders()
drivers_df = dm.get_drivers()
runs_df = dm.get_runs()


# ============================================
# HEADER
# ============================================

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"""
    <div class="dashboard-header">
        <div>
            <h1 class="dashboard-title">Sydney Metro Courier</h1>
            <p class="dashboard-subtitle">{datetime.now().strftime('%A, %d %B %Y')} &bull; Operations Dashboard</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================
# PAGE ROUTING
# ============================================

if page == "📊 Dashboard":
    from pages.dashboard import render
    render(orders_df, drivers_df, runs_df, dm)

elif page == "📋 Orders":
    from pages.orders import render
    render(orders_df, drivers_df, dm, zone_filter, service_filter, status_filter)

elif page == "🚚 Drivers":
    from pages.drivers import render
    render(drivers_df, dm)

elif page == "🗺️ Route Planning":
    from pages.route_planning import render
    render(orders_df, drivers_df, runs_df, dm)

elif page == "📦 Inventory":
    from pages.inventory import render
    render(dm)

elif page == "📈 Analytics":
    from pages.analytics import render
    render(orders_df, drivers_df, dm)

elif page == "⚙️ Settings":
    from pages.settings_page import render
    render(dm)


# ============================================
# FOOTER
# ============================================

st.markdown("""
<div style="text-align: center; padding: 2rem; margin-top: 2rem; border-top: 1px solid rgba(255,255,255,0.1);">
    <div style="font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.3);">
        Sydney Metro Courier Dashboard v2.0 &bull; Powered by Thomax .wms API &bull; Built with Streamlit
    </div>
</div>
""", unsafe_allow_html=True)
