import streamlit as st
from datetime import datetime


TRACKING_STATUSES = ['pending', 'allocated', 'in_transit', 'delivered']
STATUS_LABELS = {
    'pending': 'Order Placed',
    'allocated': 'Allocated',
    'in_transit': 'In Transit',
    'delivered': 'Delivered',
}


def render_tracking_page(dm, company_name):
    """Public-facing tracking page for customers."""

    # Admin login button in top right
    col_spacer, col_login = st.columns([5, 1])
    with col_login:
        if st.button("Admin Login", use_container_width=True):
            st.session_state.show_login = True
            st.rerun()

    # Header
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0 1rem;">
        <div style="font-size: 3rem;">📦</div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 2rem; font-weight: 700; color: white; margin-top: 0.5rem;">
            {company_name}
        </div>
        <div style="font-family: 'Space Mono', monospace; font-size: 0.85rem; color: rgba(255,255,255,0.5); margin-top: 0.5rem; text-transform: uppercase; letter-spacing: 2px;">
            Track Your Delivery
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Search box centered
    col_pad_l, col_search, col_pad_r = st.columns([1, 2, 1])
    with col_search:
        tracking_input = st.text_input(
            "Tracking Number",
            placeholder="e.g. WRX-2602-A3F7B1",
            label_visibility="collapsed",
        )
        track_btn = st.button("Track Order", use_container_width=True, type="primary")

    # Search logic
    if track_btn and tracking_input:
        tracking_input = tracking_input.strip().upper()
        order = dm.get_order_by_tracking(tracking_input)

        if order:
            _render_tracking_result(order, company_name)
        else:
            st.markdown("<br>", unsafe_allow_html=True)
            col_pad_l2, col_msg, col_pad_r2 = st.columns([1, 2, 1])
            with col_msg:
                st.error("No order found with that tracking number. Please check and try again.")

    elif track_btn and not tracking_input:
        col_pad_l2, col_msg, col_pad_r2 = st.columns([1, 2, 1])
        with col_msg:
            st.warning("Please enter a tracking number.")

    # Footer
    st.markdown(f"""
    <div style="text-align: center; padding: 3rem 0 1rem; margin-top: 3rem;">
        <div style="font-family: 'Space Mono', monospace; font-size: 0.7rem; color: rgba(255,255,255,0.2);">
            {company_name} &bull; Powered by Warex Logistics
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_tracking_result(order, company_name):
    """Display the tracking result card with status timeline."""
    status = order.get('status', 'pending')

    st.markdown("<br>", unsafe_allow_html=True)

    col_pad_l, col_result, col_pad_r = st.columns([1, 2, 1])
    with col_result:
        # Tracking number header
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <div style="font-family: 'Space Mono', monospace; font-size: 0.8rem; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1px;">
                Tracking Number
            </div>
            <div style="font-family: 'Space Mono', monospace; font-size: 1.5rem; font-weight: 700; color: #667eea; margin-top: 0.25rem;">
                {order.get('tracking_number', 'N/A')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Build status timeline HTML inline (avoids Streamlit nested unsafe_allow_html issues)
        if status == 'failed':
            timeline_html = (
                '<div style="text-align: center; padding: 1.5rem; background: rgba(239, 68, 68, 0.1); '
                'border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 12px; margin-bottom: 1.5rem;">'
                '<div style="font-family: DM Sans, sans-serif; font-size: 1.25rem; font-weight: 700; color: #ef4444;">'
                'Delivery Failed</div>'
                '<div style="font-family: DM Sans, sans-serif; font-size: 0.9rem; color: rgba(255,255,255,0.6); margin-top: 0.5rem;">'
                'Please contact us for assistance.</div></div>'
            )
        else:
            status_index = TRACKING_STATUSES.index(status) if status in TRACKING_STATUSES else 0
            timeline_html = '<div class="tracking-timeline">'
            for i, s in enumerate(TRACKING_STATUSES):
                is_active = i <= status_index
                is_current = i == status_index
                active_class = 'active' if is_active else ''
                current_class = 'current' if is_current else ''
                line_class = 'active' if i < status_index else ''
                line_div = f'<div class="timeline-line {line_class}"></div>' if i > 0 else ''
                timeline_html += (
                    f'<div class="timeline-step">'
                    f'{line_div}'
                    f'<div class="timeline-dot {active_class} {current_class}"></div>'
                    f'<div class="timeline-label {active_class}">{STATUS_LABELS[s]}</div>'
                    f'</div>'
                )
            timeline_html += '</div>'

        st.markdown(timeline_html, unsafe_allow_html=True)

        # Order details card
        created_str = ''
        if order.get('created_at'):
            try:
                dt = datetime.fromisoformat(str(order['created_at']))
                created_str = dt.strftime('%d %b %Y, %I:%M %p')
            except (ValueError, TypeError):
                created_str = str(order['created_at'])

        destination = ''
        if order.get('suburb'):
            destination = order['suburb']
            if order.get('state'):
                destination += f", {order['state']}"
            if order.get('postcode'):
                destination += f" {order['postcode']}"

        service = order.get('service_level', 'standard').capitalize()
        parcels = order.get('parcels', 1)
        status_label = STATUS_LABELS.get(status, status.replace('_', ' ').capitalize())
        result_class = 'tracking-failed' if status == 'failed' else ''

        eta_html = ''
        if order.get('eta'):
            eta_val = str(order['eta'])
            eta_html = (
                '<div>'
                '<div style="font-family: Space Mono, monospace; font-size: 0.7rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 1px;">ETA</div>'
                f'<div style="font-family: DM Sans, sans-serif; font-size: 1rem; color: white; font-weight: 600; margin-top: 0.25rem;">{eta_val}</div>'
                '</div>'
            )

        st.markdown(f"""
        <div class="tracking-result {result_class}">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;">
                <div>
                    <div style="font-family: Space Mono, monospace; font-size: 0.7rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 1px;">Status</div>
                    <div style="font-family: DM Sans, sans-serif; font-size: 1rem; color: white; font-weight: 600; margin-top: 0.25rem;">{status_label}</div>
                </div>
                <div>
                    <div style="font-family: Space Mono, monospace; font-size: 0.7rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 1px;">Service</div>
                    <div style="font-family: DM Sans, sans-serif; font-size: 1rem; color: white; font-weight: 600; margin-top: 0.25rem;">{service}</div>
                </div>
                <div>
                    <div style="font-family: Space Mono, monospace; font-size: 0.7rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 1px;">Destination</div>
                    <div style="font-family: DM Sans, sans-serif; font-size: 1rem; color: white; font-weight: 600; margin-top: 0.25rem;">{destination or 'N/A'}</div>
                </div>
                <div>
                    <div style="font-family: Space Mono, monospace; font-size: 0.7rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 1px;">Parcels</div>
                    <div style="font-family: DM Sans, sans-serif; font-size: 1rem; color: white; font-weight: 600; margin-top: 0.25rem;">{parcels}</div>
                </div>
                <div>
                    <div style="font-family: Space Mono, monospace; font-size: 0.7rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 1px;">Order Placed</div>
                    <div style="font-family: DM Sans, sans-serif; font-size: 1rem; color: white; font-weight: 600; margin-top: 0.25rem;">{created_str or 'N/A'}</div>
                </div>
                {eta_html}
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_login_page(dm, company_name):
    """Admin login form."""

    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0 1rem;">
        <div style="font-size: 2.5rem;">🔐</div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 1.5rem; font-weight: 700; color: white; margin-top: 0.5rem;">
            Admin Login
        </div>
        <div style="font-family: 'Space Mono', monospace; font-size: 0.8rem; color: rgba(255,255,255,0.5); margin-top: 0.25rem;">
            {company_name}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_pad_l, col_form, col_pad_r = st.columns([1, 1.5, 1])
    with col_form:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                elif dm.authenticate(username, password):
                    st.session_state.authenticated = True
                    st.session_state.show_login = False
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        if st.button("Back to Tracking", use_container_width=True):
            st.session_state.show_login = False
            st.rerun()


def render_first_run_setup(dm):
    """First-run setup — create the initial admin account."""

    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 1rem;">
        <div style="font-size: 2.5rem;">🚀</div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 1.75rem; font-weight: 700; color: white; margin-top: 0.5rem;">
            Welcome! Let's set up your admin account
        </div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 0.95rem; color: rgba(255,255,255,0.6); margin-top: 0.5rem;">
            This account will be used to access the admin dashboard.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_pad_l, col_form, col_pad_r = st.columns([1, 1.5, 1])
    with col_form:
        with st.form("setup_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create Admin Account", use_container_width=True, type="primary")

            if submitted:
                if not username or len(username) < 3:
                    st.error("Username must be at least 3 characters.")
                elif not password or len(password) < 8:
                    st.error("Password must be at least 8 characters.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                else:
                    result = dm.create_admin(username, password)
                    if result['success']:
                        st.session_state.authenticated = True
                        st.session_state.show_login = False
                        st.rerun()
                    else:
                        st.error(result.get('error', 'Failed to create account.'))
