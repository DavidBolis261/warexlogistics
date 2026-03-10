"""
Warex Logistics Dashboard
A comprehensive logistics management interface integrated with Thomax .wms API
"""

import sys
import os
import base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from datetime import datetime
from PIL import Image

from components.styles import apply_styles
from config.settings import wms_config
from data.data_manager import DataManager

# ── Logo helpers ──────────────────────────────────────────────────────────────
_LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'warex_logo.png')

def _load_logo_b64():
    """Return an inline base64 data-URI for the Warex logo, or None."""
    try:
        with open(_LOGO_PATH, 'rb') as f:
            return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

def _load_logo_pil():
    """Return PIL Image for page_icon, or fallback emoji string."""
    try:
        return Image.open(_LOGO_PATH)
    except Exception:
        return "📦"

_logo_b64  = _load_logo_b64()   # inline HTML/CSS use
_logo_pil  = _load_logo_pil()   # st.set_page_config page_icon

# Page configuration
st.set_page_config(
    page_title="Warex Logistics",
    page_icon=_logo_pil,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom CSS
apply_styles()

# Inject OG / social-sharing meta tags and strip residual Streamlit branding
st.markdown("""
<script>
(function () {
    var metas = [
        ['property', 'og:title',        'Warex Logistics'],
        ['property', 'og:description',  'Warex Logistics — Courier & Delivery Management Dashboard'],
        ['property', 'og:type',         'website'],
        ['property', 'og:site_name',    'Warex Logistics'],
        ['name',     'description',     'Warex Logistics — Courier & Delivery Management Dashboard'],
        ['name',     'application-name','Warex Logistics'],
        ['name',     'theme-color',     '#f59e0b'],
        ['name',     'twitter:card',    'summary'],
        ['name',     'twitter:title',   'Warex Logistics'],
        ['name',     'twitter:description', 'Warex Logistics — Courier & Delivery Management Dashboard'],
    ];
    metas.forEach(function (m) {
        var sel = 'meta[' + m[0] + '="' + m[1] + '"]';
        var el  = document.querySelector(sel);
        if (!el) {
            el = document.createElement('meta');
            el.setAttribute(m[0], m[1]);
            document.head.appendChild(el);
        }
        el.setAttribute('content', m[2]);
    });
    // Override title so shared links / browser tabs show the correct name
    document.title = 'Warex Logistics';
})();
</script>
""", unsafe_allow_html=True)

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

# Push the selected mode into DataManager so it never needs to read session_state itself
_raw_mode = st.session_state.get('data_mode', '')
if 'Live' in _raw_mode and wms_config.is_configured:
    dm.set_mode('live')
elif 'Demo' in _raw_mode:
    dm.set_mode('demo')
else:
    dm.set_mode('local')


# Hide the sidebar and its expand/collapse toggle on all public-facing pages.
# The authenticated dashboard re-adds the sidebar naturally via "with st.sidebar".
if not st.session_state.authenticated:
    st.markdown("""
    <style>
    /* Hide sidebar chevron/toggle button and the sidebar panel itself
       for any page that isn't the authenticated admin dashboard */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================
# AUTH GATE
# ============================================

from views.tracking import render_tracking_page, render_login_page, render_first_run_setup

# Admin reset via environment variable (set RESET_ADMIN=true on Railway to wipe admin accounts)
if os.environ.get('RESET_ADMIN', '').lower() == 'true':
    try:
        if hasattr(dm.store, 'conn'):
            # SQLite (LocalStore)
            dm.store.conn.execute("DELETE FROM admin_users")
            dm.store.conn.execute("DELETE FROM session_tokens")
            dm.store.conn.commit()
        elif hasattr(dm.store, 'engine'):
            # PostgreSQL (PostgresStore)
            from sqlalchemy import text as _text
            with dm.store.engine.connect() as _conn:
                _conn.execute(_text("DELETE FROM admin_users"))
                _conn.execute(_text("DELETE FROM session_tokens"))
                _conn.commit()
    except Exception as _e:
        print(f"⚠️ Admin reset failed: {_e}")

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
    _logo_tag = (
        f'<img src="{_logo_b64}" style="width:130px;height:auto;border-radius:12px;" />'
        if _logo_b64 else '<div style="font-size:2.5rem;">📦</div>'
    )
    st.markdown(f"""
    <div style="text-align: center; padding: 1.2rem 0 0.6rem;">
        {_logo_tag}
        <div style="font-family: 'Space Mono', monospace; font-size: 0.7rem; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 2px; margin-top: 0.5rem;">
            Dashboard
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Navigation
    # Show unread message count badge
    try:
        unread_msgs = dm.get_unread_count()
    except Exception:
        unread_msgs = 0
    msg_label = f"💬 Messages ({unread_msgs})" if unread_msgs else "💬 Messages"

    page = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "📋 Orders",
            "🚚 Drivers",
            "🗺️ Route Planning",
            "🖨️ Print Labels",
            "📈 Analytics",
            msg_label,
            "⚙️ Settings",
        ],
        label_visibility="collapsed",
    )

    # st.markdown("---")

    # # Quick filters
    # st.markdown("### Quick Filters")

    # zone_filter = st.multiselect(
    #     "Zones",
    #     ["Inner West", "Eastern Suburbs", "CBD", "South Sydney", "Inner City"],
    #     default=[],
    # )

    # service_filter = st.multiselect(
    #     "Service Level",
    #     ["express", "standard", "economy"],
    #     default=[],
    # )

    # status_filter = st.multiselect(
    #     "Status",
    #     ["pending", "allocated", "in_transit", "delivered", "failed"],
    #     default=[],
    # )

    # st.markdown("---")

    # # Connection status
    # if wms_config.is_configured:
    #     mode = dm.data_mode
    #     if mode == 'live':
    #         dot_color = "#10b981"
    #         label = "Live - WMS Connected"
    #     elif mode == 'local':
    #         dot_color = "#fbbf24"
    #         label = "Local Only"
    #     else:
    #         dot_color = "#6b7280"
    #         label = "Demo Mode"
    # else:
    #     dot_color = "#6b7280"
    #     label = "Demo Mode"

    # st.markdown(f"""
    # <div class="live-indicator" style="color: {dot_color};">
    #     <div class="live-dot" style="background: {dot_color};"></div>
    #     {label}
    # </div>
    # """, unsafe_allow_html=True)

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
@st.cache_data(ttl=300, show_spinner=False)
def _cached_get_orders(_dm_id):
    return dm.get_orders()

@st.cache_data(ttl=300, show_spinner=False)
def _cached_get_drivers(_dm_id):
    return dm.get_drivers()

@st.cache_data(ttl=300, show_spinner=False)
def _cached_get_runs(_dm_id):
    return dm.get_runs()

_dm_id = id(dm)
orders_df = _cached_get_orders(_dm_id)
drivers_df = _cached_get_drivers(_dm_id)
runs_df = _cached_get_runs(_dm_id)


# HEADER
col1, col2 = st.columns([3, 1])
with col1:
    _hdr_logo = (
        f'<img src="{_logo_b64}" style="height:56px;width:auto;border-radius:10px;margin-right:1rem;flex-shrink:0;" />'
        if _logo_b64 else ''
    )
    st.markdown(f"""
    <div class="dashboard-header">
        <div style="display:flex;align-items:center;">
            {_hdr_logo}
            <div>
                <h1 class="dashboard-title">{company_name}</h1>
                <p class="dashboard-subtitle">{datetime.now().strftime('%A, %d %B %Y')} &bull; Operations Dashboard</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# Sidebar filters are currently disabled — default to empty (no filtering)
zone_filter = []
service_filter = []
status_filter = []

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

elif page.startswith("💬 Messages"):
    from views.messages import render
    render(dm)

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
