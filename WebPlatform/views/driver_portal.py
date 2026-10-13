"""Browser access for drivers, using the same authenticated API as the iOS app."""
import base64
import os
from urllib.parse import quote
import requests
import streamlit as st


def render():
    st.title('Driver portal')
    st.caption('Your deliveries, proof of delivery and messages with dispatch.')
    st.link_button('Back to customer tracking','/')
    api=os.getenv('DRIVER_API_URL','').rstrip('/')
    if not api:
        st.info('Driver access is being configured. Contact dispatch for assistance.')
        return

    def call(method,path,body=None):
        try:
            r=requests.request(method,api+path,json=body,headers={'Authorization':'Bearer '+st.session_state.get('driver_token','')},timeout=20)
            if r.status_code==401 and st.session_state.get('driver_token'):
                st.session_state.pop('driver_token',None)
                st.warning('Your session expired. Sign in again.')
                st.stop()
            data=r.json()
            if not r.ok:
                st.error(data.get('error','Unable to complete this request.'))
                return None
            return data
        except (requests.RequestException,ValueError):
            st.error('The driver service could not be reached. Please try again shortly.')
            return None

    if not st.session_state.get('driver_token'):
        with st.form('driver_signin'):
            phone=st.text_input('Phone number')
            password=st.text_input('Password',type='password')
            st.caption('Use the phone number and password provided by dispatch.')
            if st.form_submit_button('Sign in',type='primary'):
                result=call('POST','/api/driver/login',{'phone':phone.strip(),'password':password})
                if result:
                    st.session_state.driver_token=result['token']
                    st.rerun()
        return
    if st.button('Sign out'):
        call('POST','/api/driver/logout',{})
        st.session_state.pop('driver_token',None)
        st.rerun()
    deliveries,messages=st.tabs(['My deliveries','Messages'])
    with deliveries:
        result=call('GET','/api/driver/runs/current/stops')
        if result is not None:
            if not result.get('stops'):
                st.info('No deliveries assigned. Your next allocated orders will appear here.')
            for stop in result.get('stops',[]):
                order=stop['order']
                with st.expander(f"{order['orderNumber']} · {order['customer']['name']}"):
                    st.write(order['address']['street'],order['address']['suburb'],order['address']['postcode'])
                    st.caption(f"{order['parcels']} parcels · {stop['status']}")
                    st.write(order.get('specialInstructions') or 'No special instructions.')
                    with st.form('stop_'+stop['id']):
                        status=st.selectbox('Update status',['inProgress','delivered','failed'],format_func=lambda x:{'inProgress':'Out for delivery','delivered':'Delivered','failed':'Delivery failed'}[x])
                        notes=st.text_area('Delivery notes')
                        photo=st.file_uploader('Delivery photo',type=['jpg','jpeg','png'])
                        signature=st.file_uploader('Signature image (optional)',type=['png','jpg','jpeg'])
                        if st.form_submit_button('Save delivery update'):
                            media=[file for file in [photo,signature] if file is not None]
                            if any(file.size > 4*1024*1024 for file in media):
                                st.error('Please use images smaller than 4 MB each.')
                            else:
                                payload={'status':status,'notes':notes}
                                if photo:payload['photo']=base64.b64encode(photo.getvalue()).decode()
                                if signature:payload['signature']=base64.b64encode(signature.getvalue()).decode()
                                saved=call('POST','/api/driver/stops/'+quote(stop['id'],safe='')+'/update',payload)
                                if saved:
                                    if status=='delivered':
                                        notification=call('POST','/api/driver/stops/'+quote(stop['id'],safe='')+'/notify',{'status':'delivered'})
                                        if not notification or not notification.get('success'):
                                            st.warning('Delivery saved, but its email notification needs checking by dispatch.')
                                    st.success('Delivery update saved.')
        st.caption('Automatic GPS reporting and Apple push notifications require the iOS app. This web portal does not track your location in the background.')
    with messages:
        result=call('GET','/api/driver/messages')
        if result is not None:
            if not result.get('messages'):st.info('No messages yet. Contact dispatch below.')
            for message in result.get('messages',[]):
                with st.chat_message('user' if message['direction']=='inbound' else 'assistant'):
                    st.write(message['body'])
                    st.caption(message['sentAt'])
        with st.form('driver_message'):
            message=st.text_area('Message to dispatch')
            if st.form_submit_button('Send message') and message.strip():
                if call('POST','/api/driver/messages',{'body':message.strip()}):st.rerun()
