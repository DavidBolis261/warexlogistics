import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import requests

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'DriverAPI'))
from data.local_store import LocalStore
from data.access import AccessStore
from integrations.starshipit import StarshipitSync, StarshipitClient, StarshipitError


def order(remote_id=123):
    return {'order_id':remote_id,'order_number':'SHOP-1','status':'Unshipped','order_date':'2026-10-13T00:00:00Z',
            'carrier':'PlainLabel','carrier_name':'Warex','type':'Outgoing',
            'destination':{'name':'Test Recipient','street':'1 Example Street','suburb':'Sydney','state':'NSW','post_code':'2000','country':'Australia','delivery_instructions':'Reception'},
            'sender_details':{'street':'2 Warehouse Street','name':'Test Sender'},'packages':[{'weight':2}],'items':[{'sku':'TEST','quantity':3}]}


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=LocalStore(str(Path(self.tmp.name)/'test.db'))
        self.dm=SimpleNamespace(store=self.store,access=AccessStore(self.store))
        self.client=Mock(configured=True)
        self.client.request.return_value={'success':True,'order':order()}
        self.sync=StarshipitSync(self.dm,self.client)
        self.sync.save_setting('carrier','Warex')

    def tearDown(self):
        self.store.conn.close();self.tmp.cleanup()

    def imported(self):
        self.sync.import_order(order())
        return self.sync.links()[0]['local_id']

    def test_idempotent_import_preserves_dispatch_evidence_and_origin(self):
        local=self.imported()
        self.assertEqual(self.store.get_order_by_id(local)['pickup_address'],'2 Warehouse Street')
        self.assertEqual(self.store.get_order_by_id(local)['special_instructions'],'Reception')
        self.store.update_order_fields(local,status='allocated',driver_id='driver-1',proof_photo='proof')
        changed=order();changed['destination']['street']='Changed upstream'
        self.assertEqual(self.sync.import_order(changed),'preserved')
        row=self.store.get_order_by_id(local)
        self.assertEqual(row['address'],'1 Example Street');self.assertEqual(row['driver_id'],'driver-1')
        self.assertEqual(row['proof_photo'],'proof');self.assertEqual(len(self.store.get_orders()),1)
        self.assertEqual(len(self.sync.links()),1)

    def test_pending_refresh_and_account_namespace(self):
        local=self.imported();changed=order();changed['destination']['street']='New address'
        self.assertEqual(self.sync.import_order(changed),'refreshed')
        self.assertEqual(self.store.get_order_by_id(local)['address'],'New address')
        with patch.dict(os.environ,{'STARSHIPIT_ACCOUNT':'second'}):
            other=StarshipitSync(self.dm,self.client);other.import_order(order())
        self.assertEqual(len(self.store.get_orders()),2)

    def test_pagination_filter_and_partial_failure_does_not_advance_cursor(self):
        wrong=order(555);wrong['carrier_name']='Other';wrong['carrier']='Other'
        self.client.list_orders.side_effect=[{'orders':[order(),wrong],'total_pages':2},{'orders':[order(124)],'total_pages':2}]
        counts=self.sync.import_recent('2026-01-01T00:00:00Z')
        self.assertEqual(counts['imported'],2);self.assertEqual(counts['skipped'],1)
        cursor=self.sync.setting('cursor')
        self.client.list_orders.side_effect=StarshipitError('Temporary unavailable')
        with self.assertRaises(StarshipitError):self.sync.import_recent()
        self.assertEqual(self.sync.setting('cursor'),cursor)

    def test_printed_summary_hydrates_and_filter_required(self):
        self.client.list_orders.return_value={'orders':[{'order_id':123,'carrier_name':'Warex'}],'total_pages':1}
        self.client.get_order.return_value=order()
        self.sync.import_recent(statuses=['printed'])
        self.client.get_order.assert_called_once_with(123)
        self.sync.save_setting('carrier','')
        with self.assertRaises(StarshipitError):self.sync.import_recent()

    def test_delivery_queue_retry_survives_restart_no_duplicate_after_success(self):
        local=self.imported();self.store.update_order_fields(local,status='delivered')
        self.client.request.side_effect=StarshipitError('Rate limited',retry_after=120)
        self.sync.flush();self.assertEqual(self.sync.jobs()[0]['state'],'retry')
        restarted=StarshipitSync(self.dm,self.client)
        self.assertEqual(len(restarted.jobs()),1)
        restarted.retry();self.client.request.side_effect=None
        restarted.flush();self.assertEqual(restarted.jobs()[0]['state'],'done')
        payload=self.client.request.call_args.kwargs['json']
        self.assertEqual(payload,{'order':{'order_id':123,'status':'Delivered'}})
        calls=self.client.request.call_count;restarted.flush()
        self.assertEqual(self.client.request.call_count,calls)

    def test_post_print_address_update_blocked_and_state_change_guard(self):
        local=self.imported();payload=self.sync.details_payload(local)
        self.sync.queue(local,'details',payload)
        self.client.get_order.return_value=dict(order(),status='Printed')
        self.sync.flush()
        self.assertEqual(self.sync.jobs()[0]['state'],'blocked')
        self.client.request.assert_not_called()
        self.store.update_order_fields(local,status='delivered');self.sync.reconcile_deliveries()
        self.store.update_order_fields(local,status='pending');self.sync.flush()
        self.assertTrue(all(x['state']=='blocked' for x in self.sync.jobs()))

    def test_unshipped_address_write_preserves_remote_fields(self):
        local=self.imported();self.store.update_order_fields(local,address='New street')
        self.sync.queue(local,'details',self.sync.details_payload(local))
        remote=order();remote['destination']['tax_numbers']=[{'tax_type':'test','tax_number':'preserve'}]
        self.client.get_order.return_value=remote;self.sync.flush()
        payload=self.client.request.call_args.kwargs['json']['order']
        self.assertEqual(payload['destination']['street'],'New street')
        self.assertEqual(payload['destination']['country'],'Australia')
        self.assertNotIn('packages',payload);self.assertNotIn('status',payload)
        self.assertEqual(payload['destination']['tax_numbers'],remote['destination']['tax_numbers'])

    def test_import_does_not_erase_queued_address_correction(self):
        local=self.imported();self.store.update_order_fields(local,address='Dispatch correction')
        self.sync.queue(local,'details',self.sync.details_payload(local))
        self.assertEqual(self.sync.import_order(order()),'preserved')
        self.assertEqual(self.store.get_order_by_id(local)['address'],'Dispatch correction')

    def test_sync_lock_and_invalid_orders(self):
        other=StarshipitSync(self.dm,self.client)
        with self.sync.lock():
            with self.assertRaises(StarshipitError):
                with other.lock():pass
        with self.assertRaises(StarshipitError):self.sync.import_order({'order_id':1})
        self.assertEqual(self.sync.import_order(dict(order(),archived=True)),'skipped')

    def test_shared_modules_identical(self):
        base=Path(__file__).resolve().parents[1]
        self.assertEqual((base/'DriverAPI/integrations/starshipit.py').read_bytes(),(base/'WebPlatform/integrations/starshipit.py').read_bytes())


class ClientTests(unittest.TestCase):
    @patch.dict(os.environ,{'STARSHIPIT_API_KEY':'test-api-secret','STARSHIPIT_SUBSCRIPTION_KEY':'test-sub-secret'})
    def test_headers_envelopes_and_rate_limit(self):
        session=Mock();client=StarshipitClient(session)
        session.request.return_value=Mock(status_code=200,json=lambda:{'success':True,'order':order()})
        self.assertEqual(client.get_order(123)['order_id'],123)
        args=session.request.call_args
        self.assertEqual(args.args[1],'https://api.starshipit.com/api/orders')
        self.assertEqual(args.kwargs['headers']['StarShipIT-Api-Key'],'test-api-secret')
        self.assertFalse(args.kwargs['allow_redirects'])
        session.request.return_value=Mock(status_code=429,headers={'Retry-After':'120'})
        client.last_request=0
        with self.assertRaises(StarshipitError) as result:client.request('PUT','/orders',json={})
        self.assertEqual(result.exception.retry_after,120)
        session.request.return_value=Mock(status_code=200,json=lambda:{'success':False,'errors':[{'message':'test-api-secret'}]})
        client.last_request=0
        with self.assertRaises(StarshipitError) as result:client.request('PUT','/orders',json={})
        self.assertNotIn('test-api-secret',str(result.exception))

    @patch.dict(os.environ,{'STARSHIPIT_API_KEY':'','STARSHIPIT_SUBSCRIPTION_KEY':''})
    def test_missing_credentials_make_no_network_call(self):
        session=Mock()
        with self.assertRaises(StarshipitError):StarshipitClient(session).request('GET','/orders')
        session.request.assert_not_called()
