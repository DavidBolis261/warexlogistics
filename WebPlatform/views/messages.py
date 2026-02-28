"""
Messages view — admin inbox for driver ↔ admin conversations.
"""
import streamlit as st
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

SYDNEY_TZ = ZoneInfo("Australia/Sydney")


def _fmt_time(ts_str):
    """Parse an ISO timestamp string and return Sydney-local HH:MM DD/MM format."""
    if not ts_str:
        return ''
    try:
        from datetime import datetime, timezone
        # Handle both offset-aware and naive strings
        ts_str_s = str(ts_str).strip()
        if ts_str_s.endswith('+00:00') or ts_str_s.endswith('Z'):
            dt = datetime.fromisoformat(ts_str_s.replace('Z', '+00:00'))
        else:
            # Assume UTC if naive
            dt = datetime.fromisoformat(ts_str_s).replace(tzinfo=timezone.utc)
        sydney = dt.astimezone(SYDNEY_TZ)
        return sydney.strftime('%d/%m %H:%M')
    except Exception:
        return str(ts_str)[:16]


def render(dm):
    st.markdown('<div class="section-header">💬 Messages</div>', unsafe_allow_html=True)
    st.caption("Conversations between admin and drivers. Messages are displayed in Sydney time (AEST/AEDT).")

    # Load all messages
    all_messages = dm.get_all_messages()
    drivers_df = dm.get_drivers()

    if all_messages.empty:
        st.info("No messages yet. Drivers can send messages from the mobile app.")
        return

    # Build per-driver conversation list
    driver_ids = all_messages['driver_id'].unique().tolist()

    # Get unread counts for sidebar badge
    unread_map = dm.get_driver_unread_counts()

    # Build driver name lookup
    driver_name_map = {}
    if not drivers_df.empty and 'driver_id' in drivers_df.columns and 'name' in drivers_df.columns:
        driver_name_map = dict(zip(drivers_df['driver_id'], drivers_df['name']))

    # Sidebar-style driver list + main conversation panel
    col_list, col_chat = st.columns([1, 2])

    with col_list:
        st.markdown("### Drivers")
        selected = st.session_state.get('msg_selected_driver', driver_ids[0] if driver_ids else None)

        for did in driver_ids:
            d_name = driver_name_map.get(did, did)
            unread = unread_map.get(did, 0)
            badge = f" 🔴 {unread}" if unread else ""
            is_active = did == selected
            btn_label = f"{'→ ' if is_active else ''}{d_name}{badge}"
            if st.button(btn_label, key=f"msg_drv_{did}", use_container_width=True):
                st.session_state['msg_selected_driver'] = did
                st.rerun()

    with col_chat:
        if not selected:
            st.info("Select a driver to view conversation.")
        else:
            d_name = driver_name_map.get(selected, selected)
            st.markdown(f"### Chat with {d_name}")

            # Mark messages as read when admin views them
            dm.mark_messages_read(selected)

            # Get thread
            thread = dm.get_messages_for_driver(selected)

            # Display chat bubbles
            for msg in thread:
                direction = msg.get('direction', 'inbound')
                body = msg.get('body', '')
                sent_at = _fmt_time(msg.get('sent_at', ''))

                if direction == 'inbound':
                    # Driver message — left aligned
                    st.markdown(f"""
<div style="display:flex; align-items:flex-end; margin-bottom:12px;">
  <div style="background:rgba(255,255,255,0.08); border-radius:12px 12px 12px 2px;
              padding:10px 14px; max-width:75%; border:1px solid rgba(255,255,255,0.1);">
    <div style="font-size:0.85rem; color:rgba(255,255,255,0.9);">{body}</div>
    <div style="font-size:0.65rem; color:rgba(255,255,255,0.4); margin-top:4px;">
      {d_name} · {sent_at}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
                else:
                    # Admin reply — right aligned
                    st.markdown(f"""
<div style="display:flex; justify-content:flex-end; margin-bottom:12px;">
  <div style="background:linear-gradient(135deg,#667eea,#764ba2); border-radius:12px 12px 2px 12px;
              padding:10px 14px; max-width:75%;">
    <div style="font-size:0.85rem; color:white;">{body}</div>
    <div style="font-size:0.65rem; color:rgba(255,255,255,0.6); margin-top:4px;">
      You · {sent_at}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

            # Reply form
            st.markdown("---")
            st.markdown("**Reply to driver**")
            reply_key = f"reply_text_{selected}"
            reply_text = st.text_area(
                "Message",
                key=reply_key,
                placeholder=f"Type a message to {d_name}...",
                height=80,
                label_visibility="collapsed",
            )
            if st.button("📤 Send Reply", key=f"send_reply_{selected}", use_container_width=True):
                body = (reply_text or '').strip()
                if body:
                    dm.send_admin_reply(selected, d_name, body)
                    st.success("Message sent!")
                    # Clear text area by resetting session state key
                    st.session_state.pop(reply_key, None)
                    st.rerun()
                else:
                    st.warning("Please type a message before sending.")
