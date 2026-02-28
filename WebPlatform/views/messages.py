"""
Messages view — admin inbox for driver ↔ admin conversations.
Admin can view, reply, and also start a new conversation with any driver.
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
        ts_str_s = str(ts_str).strip()
        if ts_str_s.endswith('+00:00') or ts_str_s.endswith('Z'):
            dt = datetime.fromisoformat(ts_str_s.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(ts_str_s).replace(tzinfo=timezone.utc)
        sydney = dt.astimezone(SYDNEY_TZ)
        return sydney.strftime('%d/%m %H:%M')
    except Exception:
        return str(ts_str)[:16]


def render(dm):
    st.markdown('<div class="section-header">💬 Messages</div>', unsafe_allow_html=True)
    st.caption("Conversations between admin and drivers — displayed in Sydney time (AEST/AEDT).")

    # ── Load data ──────────────────────────────────────────────────────────────
    all_messages = dm.get_all_messages()
    drivers_df = dm.get_drivers()

    # Build driver name/id lookup from the drivers table
    driver_name_map = {}  # driver_id → name
    driver_id_list = []   # ordered list of all driver IDs

    if not drivers_df.empty and 'driver_id' in drivers_df.columns:
        for _, row in drivers_df.iterrows():
            did = row['driver_id']
            name = row.get('name', did) or did
            driver_name_map[did] = name
            driver_id_list.append(did)

    # Add any drivers that appear in messages but aren't in the drivers table
    # (edge case for deleted drivers who still have message history)
    if not all_messages.empty and 'driver_id' in all_messages.columns:
        for did in all_messages['driver_id'].unique():
            if did not in driver_name_map:
                # Use driver_name from messages if available
                name_rows = all_messages[all_messages['driver_id'] == did]['driver_name']
                name = name_rows.dropna().iloc[0] if not name_rows.dropna().empty else did
                driver_name_map[did] = name or did
                driver_id_list.append(did)

    if not driver_id_list:
        st.info("No drivers found. Add drivers first, then they can message you from the app.")
        return

    # Get unread counts (drivers who have messaged but admin hasn't read yet)
    unread_map = dm.get_driver_unread_counts()

    # Build a set of driver IDs that have message history
    drivers_with_messages = set()
    if not all_messages.empty and 'driver_id' in all_messages.columns:
        drivers_with_messages = set(all_messages['driver_id'].unique())

    # ── Layout: driver list + conversation panel ───────────────────────────────
    col_list, col_chat = st.columns([1, 2])

    # Default selection — prefer drivers with unread messages first
    if 'msg_selected_driver' not in st.session_state:
        if unread_map:
            st.session_state['msg_selected_driver'] = next(iter(unread_map))
        elif driver_id_list:
            st.session_state['msg_selected_driver'] = driver_id_list[0]

    selected = st.session_state.get('msg_selected_driver')

    with col_list:
        st.markdown("### Drivers")

        # Sort: drivers with unread first, then with messages, then the rest
        def sort_key(did):
            unread = unread_map.get(did, 0)
            has_msgs = did in drivers_with_messages
            return (-unread, 0 if has_msgs else 1, driver_name_map.get(did, did))

        sorted_drivers = sorted(driver_id_list, key=sort_key)

        for did in sorted_drivers:
            d_name = driver_name_map.get(did, did)
            unread = unread_map.get(did, 0)
            has_msgs = did in drivers_with_messages

            # Build label with status indicators
            if unread:
                label = f"🔴 **{d_name}** · {unread} new"
            elif has_msgs:
                label = f"💬 {d_name}"
            else:
                label = f"· {d_name}"

            is_active = did == selected

            # Highlight active driver
            container = st.container()
            with container:
                btn_style = "primary" if is_active else "secondary"
                if st.button(
                    label,
                    key=f"msg_drv_{did}",
                    use_container_width=True,
                    type=btn_style,
                ):
                    st.session_state['msg_selected_driver'] = did
                    st.rerun()

    with col_chat:
        if not selected or selected not in driver_name_map:
            st.info("Select a driver from the list to view their conversation.")
        else:
            d_name = driver_name_map.get(selected, selected)
            has_existing = selected in drivers_with_messages

            st.markdown(f"### {d_name}")

            if has_existing:
                st.caption(f"Driver ID: `{selected}`")
            else:
                st.caption(f"Driver ID: `{selected}` — No messages yet. Send the first one below!")

            # Mark this driver's inbound messages as read
            dm.mark_messages_read(selected)

            # Get thread
            thread = dm.get_messages_for_driver(selected)

            # ── Chat bubbles ──────────────────────────────────────────────
            if thread:
                chat_html = '<div style="display:flex; flex-direction:column; gap:12px; padding:12px 0;">'

                for msg in thread:
                    direction = msg.get('direction', 'inbound')
                    body = msg.get('body', '')
                    # Escape HTML entities
                    body_escaped = (body
                                    .replace('&', '&amp;')
                                    .replace('<', '&lt;')
                                    .replace('>', '&gt;')
                                    .replace('"', '&quot;'))
                    sent_at = _fmt_time(msg.get('sent_at', ''))

                    if direction == 'inbound':
                        # Driver → Admin (left side)
                        chat_html += f"""
<div style="display:flex; align-items:flex-end; gap:8px;">
  <div style="background:rgba(255,255,255,0.07); border-radius:12px 12px 12px 2px;
              padding:10px 14px; max-width:70%;
              border:1px solid rgba(255,255,255,0.08);">
    <div style="font-size:0.7rem; font-weight:600; color:#667eea; margin-bottom:4px;">{d_name}</div>
    <div style="font-size:0.875rem; color:rgba(255,255,255,0.9); white-space:pre-wrap;">{body_escaped}</div>
    <div style="font-size:0.65rem; color:rgba(255,255,255,0.35); margin-top:5px;">{sent_at}</div>
  </div>
  <div style="flex:1;"></div>
</div>"""
                    else:
                        # Admin → Driver (right side)
                        chat_html += f"""
<div style="display:flex; align-items:flex-end; gap:8px; justify-content:flex-end;">
  <div style="flex:1;"></div>
  <div style="background:linear-gradient(135deg,#667eea,#764ba2); border-radius:12px 12px 2px 12px;
              padding:10px 14px; max-width:70%;">
    <div style="font-size:0.7rem; font-weight:600; color:rgba(255,255,255,0.7); margin-bottom:4px;">You (Admin)</div>
    <div style="font-size:0.875rem; color:white; white-space:pre-wrap;">{body_escaped}</div>
    <div style="font-size:0.65rem; color:rgba(255,255,255,0.5); margin-top:5px;">{sent_at}</div>
  </div>
</div>"""

                chat_html += '</div>'
                st.markdown(chat_html, unsafe_allow_html=True)
            else:
                st.markdown("""
<div style="text-align:center; padding:32px; color:rgba(255,255,255,0.35); font-size:0.875rem;">
  No messages yet — send the first message below.
</div>
""", unsafe_allow_html=True)

            # ── Reply / initiate form ─────────────────────────────────────
            st.markdown("---")
            action_label = "**Reply to driver**" if has_existing else "**Start conversation**"
            st.markdown(action_label)

            reply_key = f"reply_text_{selected}"
            placeholder = (
                f"Type a reply to {d_name}..."
                if has_existing
                else f"Type your first message to {d_name}..."
            )
            reply_text = st.text_area(
                "Message",
                key=reply_key,
                placeholder=placeholder,
                height=80,
                label_visibility="collapsed",
            )

            send_label = "📤 Send Reply" if has_existing else "📤 Send Message"
            if st.button(send_label, key=f"send_reply_{selected}", use_container_width=True, type="primary"):
                body = (reply_text or '').strip()
                if body:
                    dm.send_admin_reply(selected, d_name, body)
                    st.success(f"Message sent to {d_name}!")
                    # Clear the text area
                    st.session_state.pop(reply_key, None)
                    st.rerun()
                else:
                    st.warning("Please type a message before sending.")
