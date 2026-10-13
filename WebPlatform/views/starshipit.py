"""Administrator-only Starshipit setup, import and writeback controls."""
import json
from datetime import datetime, timedelta, timezone
import pandas as pd
import streamlit as st
from integrations.starshipit import StarshipitSync, StarshipitError


def render(dm):
    sync=StarshipitSync(dm)
    st.header('Starshipit')
    st.caption('Receive orders from Starshipit, dispatch them in Warex and send supported updates back.')
    configured=sync.client.configured
    links=sync.links(); jobs=sync.jobs()
    a,b,c=st.columns(3)
    a.metric('Linked orders',len(links))
    b.metric('Waiting updates',sum(j['state'] in ('queued','retry') for j in jobs))
    c.metric('Needs attention',sum(j['state']=='blocked' for j in jobs))
    if configured:st.success('Credentials configured. Use Test connection to verify account access.')
    else:st.info('Ready for configuration. Add the API key and subscription key later; no credentials are needed to explore this page.')
    setup,imports,updates=st.tabs(['Connection & automation','Receive orders','Send updates'])
    with setup:
        st.markdown('Set these Railway variables on **Dashboard and DriverAPI**:')
        st.code('STARSHIPIT_API_KEY\nSTARSHIPIT_SUBSCRIPTION_KEY\nSTARSHIPIT_ACCOUNT=primary',language=None)
        st.caption('Use a different account label if connecting a different Starshipit account. Never reuse a label for another account.')
        st.markdown('For background processing, set `STARSHIPIT_SYNC_ENABLED=true` on **DriverAPI**. Optional: `STARSHIPIT_SYNC_INTERVAL_SECONDS=300` (minimum 60 seconds).')
        st.link_button('Starshipit API documentation','https://api-docs.starshipit.com')
        if st.button('Test connection',disabled=not configured):
            try:
                sync.client.request('GET','/orders/unshipped',params={'limit':1,'page':1})
                st.success('Starshipit accepted the credentials.')
            except StarshipitError as exc:st.error(str(exc))
        with st.form('starshipit_preferences'):
            carrier=st.text_input('Carrier name or code to import',value=sync.setting('carrier'),help='Exact carrier or carrier_name match, ignoring case. This prevents importing deliveries belonging to other couriers.')
            all_carriers=st.checkbox('Import all carriers when the carrier filter is blank',value=sync.setting('all_carriers','false')=='true')
            statuses=st.multiselect('Starshipit order groups',options=['unshipped','printed','shipped'],default=json.loads(sync.setting('statuses','["unshipped"]')))
            auto=st.checkbox('Automatically receive matching orders',value=sync.setting('auto_import','false')=='true')
            st.caption('Background delivery updates are processed whenever the worker is enabled. Automatic importing also requires the checkbox above.')
            if st.form_submit_button('Save sync preferences'):
                if not statuses or (not carrier.strip() and not all_carriers):st.error('Select at least one order group and choose a carrier filter or all carriers.')
                else:
                    for key,value in {'carrier':carrier.strip(),'all_carriers':str(all_carriers).lower(),'statuses':json.dumps(statuses),'auto_import':str(auto).lower()}.items():sync.save_setting(key,value)
                    st.success('Sync preferences saved.')
        st.caption('Last worker check: '+sync.setting('heartbeat','Not started'))
        st.caption('Last successful import: '+sync.setting('last_import','Never'))
        if sync.setting('last_error'):st.warning(sync.setting('last_error'))
    with imports:
        st.write('Matching orders are imported into Orders with a stable Warex tracking number. Re-imports update unassigned pending orders; allocated orders, outcomes and evidence are preserved.')
        since=st.date_input('Import orders updated since',value=(datetime.now(timezone.utc)-timedelta(days=7)).date(),max_value=datetime.now(timezone.utc).date())
        st.caption('Imports do not send customer emails or push orders to WMS. Archived and return orders are skipped.')
        if st.button('Receive orders now',disabled=not configured,type='primary'):
            try:
                with st.spinner('Receiving Starshipit orders…'):
                    result=sync.import_recent(datetime.combine(since,datetime.min.time(),tzinfo=timezone.utc).isoformat())
                st.success(' · '.join(f'{key}: {value}' for key,value in result.items()))
                links=sync.links()
            except StarshipitError as exc:st.error(str(exc))
        if links:st.dataframe(pd.DataFrame(links),hide_index=True,use_container_width=True)
        else:st.info('No linked orders yet. Imported orders will appear here and on the Orders page.')
    with updates:
        st.write('Delivered orders are queued automatically for Starshipit’s Delivered status. Other dispatch statuses stay in Warex: the public API does not document equivalent writable courier tracking events.')
        st.caption('Delivery photos and signatures remain in Warex. This integration does not buy labels, manifest shipments or overwrite carrier tracking numbers.')
        if st.button('Send queued updates',disabled=not configured,type='primary'):
            try:
                with st.spinner('Sending queued updates…'):result=sync.flush()
                st.success(f"{result['sent']} updates accepted by Starshipit.")
            except StarshipitError as exc:st.error(str(exc))
        if st.button('Retry failed updates',disabled=not configured):
            sync.retry();st.success('Failed updates are queued for the next sync.')
        jobs=sync.jobs()
        if jobs:st.dataframe(pd.DataFrame(jobs),hide_index=True,use_container_width=True)
        else:st.info('No outbound updates yet.')
        st.subheader('Update a delivery address in Starshipit')
        st.caption('Only unshipped/saved orders can be edited. The remote order state is checked again immediately before sending.')
        if links:
            local_id=st.selectbox('Linked Warex order',[r['local_id'] for r in links])
            try:
                payload=sync.details_payload(local_id)
                with st.expander('Review address update'):st.json(payload)
                if st.button('Queue this address update',disabled=not configured):
                    sync.queue(local_id,'details',payload);st.success('Address update queued.')
            except StarshipitError as exc:st.warning(str(exc))
