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


def _render_client_portal(dm, company_name):
    """Read-only order status portal for partner/client accounts."""
    from views.orders import render_client_view

    # Minimal sidebar — just logout
    with st.sidebar:
        _logo_tag = (
            f'<img src="{_load_logo_b64()}" style="width:88px;height:auto;border-radius:12px;" />'
            if _load_logo_b64() else '<div style="font-size:2.5rem;">📦</div>'
        )
        st.markdown(f"""
        <div style="text-align: center; padding: 0.3rem 0 0.2rem;">
            {_logo_tag}
            <div style="font-family: 'Space Mono', monospace; font-size: 0.7rem;
                        color: rgba(255,255,255,0.45); text-transform: uppercase;
                        letter-spacing: 2px; margin-top: 0.5rem;">
                Partner Portal
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            dm.logout_token(st.session_state.get('session_token'))
            st.session_state.authenticated = False
            st.session_state.show_login = False
            st.session_state.session_token = None
            st.session_state.user_role = 'admin'
            st.query_params.clear()
            st.rerun()

    session = dm.store.get_session_token(st.session_state.get('session_token'))
    if not session or not dm.access.approved(session['username']):
        st.title('Partner portal')
        st.info('Your registration is awaiting approval by Warex. Orders will appear here once dispatch approves your account and assigns them to you.')
        return
    orders_df = dm.access.partner_orders(st.session_state.get('session_token'))
    render_client_view(orders_df, company_name)

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
if 'user_role' not in st.session_state:
    st.session_state.user_role = 'admin'

# Restore session from query param token (survives page refresh)
if not st.session_state.authenticated:
    token_from_url = st.query_params.get('token')
    if token_from_url and dm.validate_session_token(token_from_url):
        st.session_state.authenticated = True
        st.session_state.session_token = token_from_url
        # Restore role — important for clients refreshing the page
        st.session_state.user_role = dm.get_role_for_token(token_from_url)

# Revalidate server-side role on every rerun, never grant admin on lookup failure.
if st.session_state.authenticated:
    role = dm.get_role_for_token(st.session_state.get('session_token'))
    if role not in ('admin', 'client'):
        st.session_state.authenticated = False
        st.session_state.session_token = None
        st.query_params.pop('token', None)
    else:
        st.session_state.user_role = role

# Apply custom CSS — pass auth state so sidebar toggle is only injected for admins
apply_styles(authenticated=st.session_state.authenticated)

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

# Public portal entry points are separate from administrator navigation.
if not st.session_state.authenticated and st.query_params.get('portal') == 'driver':
    from views.driver_portal import render as render_driver_portal
    render_driver_portal()
    st.stop()
if not st.session_state.authenticated and st.query_params.get('portal') == 'partner':
    st.session_state.show_login = True

# First-run setup — no admin exists yet
if not dm.admin_exists():
    render_first_run_setup(dm)
    st.stop()

# Authenticated — route by role
if st.session_state.authenticated:
    if st.session_state.get('user_role') == 'client':
        _render_client_portal(dm, company_name)
        st.stop()
    # else fall through to admin dashboard below

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
        f'<img src="{_logo_b64}" style="width:88px;height:auto;border-radius:12px;" />'
        if _logo_b64 else '<div style="font-size:2.5rem;">📦</div>'
    )
    st.markdown(f"""
    <div style="text-align: center; padding: 0.3rem 0 0.2rem;">
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
            "📍 Driver Tracking",
            "🔑 Driver Access",
            "🗺️ Route Planning",
            "🖨️ Print Labels",
            "📷 Delivery Evidence",
            "🤝 Partners",
            "📦 Inventory",
            "📈 Analytics",
            msg_label,
            "🔌 Integrations",
            "⚙️ Settings",
        ],
        label_visibility="collapsed",
    )

    with st.expander("Quick filters"):
        zone_filter = st.multiselect("Zones", dm.store.get_zones()['zone_name'].tolist())
        service_filter = st.multiselect("Service level", ["express", "standard", "economy"])
        status_filter = st.multiselect("Order status", ["pending", "allocated", "in_transit", "delivered", "failed"])
    st.caption("WMS connected" if wms_config.is_configured else "Warehouse integration not connected")

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
        st.session_state.user_role = 'admin'
        st.query_params.clear()
        st.rerun()


# Read fresh operational data after every action/rerun.
orders_df = dm.get_orders()
drivers_df = dm.get_drivers()
runs_df = dm.get_runs()


# HEADER
with st.container():
    _hdr_logo = (
        f'<img src="{_logo_b64}" style="height:56px;width:auto;border-radius:10px;margin-right:1rem;flex-shrink:0;" />'
        if _logo_b64 else ''
    )
    st.markdown(f"""
    <div class="dashboard-header">
        <div style="display:flex;align-items:center;">
            {_hdr_logo}
            <div>
                <h1 class="dashboard-title">WAREX LOGISTICS</h1>
                <p class="dashboard-subtitle">{datetime.now().strftime('%A, %d %B %Y')} &bull; Operations Dashboard</p>
            </div>
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

elif page.startswith("💬 Messages"):
    from views.messages import render
    render(dm)

elif page in ["📍 Driver Tracking", "📷 Delivery Evidence", "🤝 Partners", "🔑 Driver Access", "🔌 Integrations"]:
    from views import operations
    {"📍 Driver Tracking": operations.tracking, "📷 Delivery Evidence": operations.evidence,
     "🤝 Partners": operations.partners, "🔑 Driver Access": operations.driver_access,
     "🔌 Integrations": operations.integrations}[page](dm)

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
