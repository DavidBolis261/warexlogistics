"""
Warex Logistics Dashboard
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
    page_title="Warex Logistics",
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

# Load company name from settings
company_name = dm.get_setting('company_name', 'Warex Logistics')

# Initialize auth state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'show_login' not in st.session_state:
    st.session_state.show_login = False
if 'session_token' not in st.session_state:
    st.session_state.session_token = None

# Restore session from query param token (survives page refresh)
if not st.session_state.authenticated:
    token_from_url = st.query_params.get('token')
    if token_from_url and dm.validate_session_token(token_from_url):
        st.session_state.authenticated = True
        st.session_state.session_token = token_from_url

# Initialize data mode (persist across refreshes by defaulting to Local)
if 'data_mode' not in st.session_state:
    if wms_config.is_configured:
        st.session_state['data_mode'] = 'Live (push to .wms + local store)'
    else:
        st.session_state['data_mode'] = 'Local Only (SQLite)'


# ============================================
# AUTH GATE
# ============================================

from views.tracking import render_tracking_page, render_login_page, render_first_run_setup

# Admin reset via environment variable (set RESET_ADMIN=true on Railway to wipe admin accounts)
if os.environ.get('RESET_ADMIN', '').lower() == 'true':
    dm.store.conn.execute("DELETE FROM admin_users")
    dm.store.conn.execute("DELETE FROM session_tokens")
    dm.store.conn.commit()

# First-run setup — no admin exists yet
if not dm.admin_exists():
    render_first_run_setup(dm)
    st.stop()

# Authenticated — show admin dashboard
if st.session_state.authenticated:
    pass  # Fall through to admin dashboard below

# Login page
elif st.session_state.show_login:
    render_login_page(dm, company_name)
    st.stop()

# Public tracking page (default)
else:
    render_tracking_page(dm, company_name)
    st.stop()


# ============================================
# ADMIN DASHBOARD (authenticated only)
# ============================================

# SIDEBAR
with st.sidebar:
    st.markdown(f"""
    <div style="text-align: center; padding: 1.5rem 0;">
        <div style="font-size: 2.5rem;">📦</div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 1.25rem; font-weight: 700; color: white; margin-top: 0.5rem;">
            {company_name}
        </div>
        <div style="font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 2px;">
            Dashboard
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
            "🖨️ Print Labels",
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
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    if st.button("🚪 Logout", use_container_width=True):
        dm.logout_token(st.session_state.get('session_token'))
        st.session_state.authenticated = False
        st.session_state.show_login = False
        st.session_state.session_token = None
        st.query_params.clear()
        st.rerun()


# LOAD DATA — cached with 30-second TTL to avoid redundant DB queries on every rerun
@st.cache_data(ttl=30, show_spinner=False)
def _cached_get_orders(_dm_id):
    return dm.get_orders()

@st.cache_data(ttl=30, show_spinner=False)
def _cached_get_drivers(_dm_id):
    return dm.get_drivers()

@st.cache_data(ttl=30, show_spinner=False)
def _cached_get_runs(_dm_id):
    return dm.get_runs()

_dm_id = id(dm)
orders_df = _cached_get_orders(_dm_id)
drivers_df = _cached_get_drivers(_dm_id)
runs_df = _cached_get_runs(_dm_id)


# HEADER
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"""
    <div class="dashboard-header">
        <div>
            <h1 class="dashboard-title">{company_name}</h1>
            <p class="dashboard-subtitle">{datetime.now().strftime('%A, %d %B %Y')} &bull; Operations Dashboard</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


# PAGE ROUTING
if page == "📊 Dashboard":
    from views.dashboard import render
    render(orders_df, drivers_df, runs_df, dm)

elif page == "📋 Orders":
    from views.orders import render
    render(orders_df, drivers_df, dm, zone_filter, service_filter, status_filter)

elif page == "🚚 Drivers":
    from views.drivers import render
    render(drivers_df, dm, orders_df)

elif page == "🗺️ Route Planning":
    from views.route_planning import render
    render(orders_df, drivers_df, runs_df, dm)

elif page == "🖨️ Print Labels":
    from views.print_labels import render
    render(dm)

elif page == "📦 Inventory":
    from views.inventory import render
    render(dm)

elif page == "📈 Analytics":
    from views.analytics import render
    render(orders_df, drivers_df, dm)

elif page == "⚙️ Settings":
    from views.settings_page import render
    render(dm)


# FOOTER
st.markdown(f"""
<div style="text-align: center; padding: 2rem; margin-top: 2rem; border-top: 1px solid rgba(255,255,255,0.1);">
    <div style="font-family: 'Space Mono', monospace; font-size: 0.75rem; color: rgba(255,255,255,0.3);">
        {company_name}
    </div>
</div>
""", unsafe_allow_html=True)
