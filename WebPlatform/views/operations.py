"""Discoverable operational tools with explicit empty and setup states."""
import base64
import io
import os
import pandas as pd
import streamlit as st
from PIL import Image
from config.settings import wms_config


def tracking(dm):
    st.header('Driver tracking')
    st.caption('Current positions and recorded location history for your fleet.')
    drivers = dm.get_drivers()
    current, history = st.tabs(['Live locations', 'Location history'])
    with current:
        if drivers.empty:
            st.info('No drivers yet. Add a driver in Drivers to begin tracking your fleet.')
        else:
            positions = drivers.dropna(subset=['latitude','longitude']) if {'latitude','longitude'}.issubset(drivers.columns) else pd.DataFrame()
            st.metric('Drivers sharing a position', len(positions))
            if positions.empty:
                st.info('No location reports yet. Drivers must sign in through a location-enabled app and permit location sharing.')
            else:
                st.map(positions.rename(columns={'latitude':'lat','longitude':'lon'})[['lat','lon']])
            fields = [c for c in ['name','status','latitude','longitude','location_updated_at'] if c in drivers]
            st.dataframe(drivers[fields],use_container_width=True,hide_index=True)
    with history:
        if drivers.empty:
            st.info('Location history will be available here after a driver has sent location reports.')
        else:
            chosen = st.selectbox('Driver', drivers['driver_id'].tolist(),format_func=lambda x: drivers.set_index('driver_id').loc[x,'name'])
            from views.drivers import _render_location_history
            _render_location_history(drivers[drivers.driver_id == chosen].iloc[0].to_dict(), dm)
    if st.button('Refresh positions'):
        st.cache_data.clear()
        st.rerun()


def evidence(dm):
    st.header('Delivery evidence')
    st.caption('Find delivery photos, signatures and notes by order or tracking number.')
    orders = dm.get_orders()
    if orders.empty:
        st.info('No deliveries yet. Evidence uploaded by drivers will appear here with its order.')
        return
    query = st.text_input('Search deliveries',placeholder='Tracking number, customer or address')
    if query:
        mask = pd.Series(False,index=orders.index)
        for col in ['order_id','tracking_number','customer','address']:
            if col in orders:
                mask |= orders[col].fillna('').astype(str).str.contains(query,case=False,regex=False)
        orders = orders[mask]
    if orders.empty:
        st.info('No matching deliveries.')
        return
    chosen = st.selectbox('Order',orders.order_id.tolist(),format_func=lambda x: f"{x} · {orders.set_index('order_id').loc[x,'customer']}")
    order = orders[orders.order_id == chosen].iloc[0]
    st.write('Status:',order.get('status','pending'))
    st.write('Delivered:',str(order.get('delivered_at') or 'Not recorded'))
    st.write('Driver notes:',str(order.get('delivery_notes') or 'No notes recorded'))
    for column,title in [('proof_photo','Delivery photo'),('proof_signature','Signature')]:
        st.subheader(title)
        value = order.get(column)
        if not isinstance(value,str) or not value:
            st.info(f'No {title.lower()} uploaded for this order.')
            continue
        try:
            raw = base64.b64decode(value.split(',',1)[-1],validate=True)
            picture = Image.open(io.BytesIO(raw))
            image_format = picture.format.lower()
            picture.verify()
            st.image(raw,width=480)
            st.download_button(f'Download {title.lower()}',raw,file_name=f'{chosen}-{column}.{image_format}',mime=Image.MIME.get(image_format.upper(),'application/octet-stream'))
        except Exception:
            st.warning('This attachment cannot be displayed as an image.')


def partners(dm):
    st.header('Partner accounts')
    st.caption('Approve registrations and choose exactly which orders each partner can see.')
    st.link_button('Open partner sign-in / registration','/?portal=partner')
    accounts = dm.access.partners()
    if not accounts:
        st.info('No partner registrations yet. Share the portal link above with your partners. New accounts must be approved here.')
        return
    table = pd.DataFrame(accounts)
    st.dataframe(table,use_container_width=True,hide_index=True)
    username = st.selectbox('Partner account',table.username.tolist())
    approved = dm.access.approved(username)
    if st.button('Suspend access' if approved else 'Approve account'):
        dm.access.approve(username,not approved)
        st.rerun()
    orders = dm.get_orders()
    assigned = dm.access.execute('SELECT order_id FROM partner_orders WHERE username=:username',{'username':username},True)
    st.caption('Currently assigned: '+(', '.join(r['order_id'] for r in assigned) or 'None'))
    with st.form('assign_partner_orders'):
        selected = st.multiselect('Assign or transfer orders to this partner',orders.order_id.tolist() if not orders.empty else [])
        st.caption('Transferring an order removes access from its previous partner.')
        if st.form_submit_button('Assign selected orders'):
            dm.access.assign(username,selected)
            st.rerun()
    with st.form('remove_partner_orders'):
        remove = st.multiselect('Remove order access',[r['order_id'] for r in assigned])
        if st.form_submit_button('Remove selected access'):
            for order_id in remove:
                dm.access.execute('DELETE FROM partner_orders WHERE order_id=:id AND username=:username',{'id':order_id,'username':username})
            st.rerun()


def driver_access(dm):
    st.header('Driver access')
    st.caption('Set a driver password to enable secure sign-in. Changing it signs out existing sessions.')
    st.link_button('Open driver portal','/?portal=driver')
    drivers=dm.get_drivers()
    if drivers.empty:
        st.info('Add a driver in Drivers first, then set their sign-in password here.')
        return
    rows=dm.access.execute('SELECT driver_id FROM driver_credentials',read=True)
    enabled={r['driver_id'] for r in rows}
    view=drivers[['driver_id','name','phone']].copy()
    view['Sign-in configured']=view.driver_id.isin(enabled)
    st.dataframe(view,hide_index=True,use_container_width=True)
    with st.form('driver_password'):
        driver=st.selectbox('Driver',drivers.driver_id.tolist(),format_func=lambda x: drivers.set_index('driver_id').loc[x,'name'])
        password=st.text_input('New password (12+ characters)',type='password')
        confirm=st.text_input('Confirm password',type='password')
        if st.form_submit_button('Set driver password'):
            if password != confirm:
                st.error('Passwords do not match.')
            else:
                try:
                    dm.access.set_driver_password(driver,password)
                    st.success('Password saved. The driver can now sign in with their phone number and password.')
                except ValueError as exc:
                    st.error(str(exc))


def integrations(dm):
    st.header('Integrations')
    st.caption('Connection status and the remaining configuration for your platform.')
    from utils.email_service import is_email_configured
    configs=[
        ('Transactional email',is_email_configured(dm),'Order confirmations and delivery updates.','RESEND_API_KEY, EMAIL_FROM_ADDRESS'),
        ('Address autocomplete',bool(os.getenv('GOOGLE_PLACES_API_KEY')),'Pickup and delivery address suggestions. Manual entry is always available.','GOOGLE_PLACES_API_KEY'),
        ('Thomax WMS',wms_config.is_configured,'Warehouse orders, receipts, inventory and stock operations.','Configure credentials in Settings → WMS Integration'),
        ('Driver portal',bool(os.getenv('DRIVER_API_URL')),'Phone-and-password sign-in, assigned deliveries and delivery evidence.','DRIVER_API_URL'),
        ('External order API',bool(os.getenv('EXTERNAL_API_KEY')),'Authenticated order integration on DriverAPI. Configure this variable on DriverAPI.','EXTERNAL_API_KEY on DriverAPI'),
        ('Apple push notifications',bool(os.getenv('APNS_KEY_ID') and os.getenv('APNS_TEAM_ID') and os.getenv('APNS_PRIVATE_KEY')),'Notifications to registered iOS devices. Requires the rebuilt iOS app.','APNS_KEY_ID, APNS_TEAM_ID, APNS_BUNDLE_ID, APNS_PRIVATE_KEY, APNS_SANDBOX'),
    ]
    for title,configured,description,variables in configs:
        with st.container(border=True):
            st.subheader(title)
            st.write('Configuration present' if configured else 'Setup required')
            st.caption(description)
            if not configured:
                st.code(variables,language=None)
    st.caption('API-side settings must also be checked on the DriverAPI service; this screen reads Dashboard configuration only.')
    st.info('A configured integration is not necessarily verified. Credentials and provider permissions are checked when the integration is used.')
