"""Regression checks for restored partner isolation and driver authentication."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from flask import Flask
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'DriverAPI'))
from data.local_store import LocalStore
from data.access import AccessStore
from api.driver_api import create_driver_api
import pandas as pd


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=LocalStore(str(Path(self.tmp.name)/'test.db'))
        self.access=AccessStore(self.store)
        self.access.execute("INSERT INTO drivers(driver_id,name,phone) VALUES ('d1','Driver One','0400000001'),('d2','Driver Two','0400000002')")
        self.access.execute("INSERT INTO orders(order_id,tracking_number,driver_id,customer,status,parcels) VALUES ('o1','t1','d1','One','allocated',1),('o2','t2','d2','Two','allocated',1)")
        class Manager:
            pass
        self.dm=Manager();self.dm.store=self.store;self.dm.access=self.access
        self.dm.get_drivers=self.store.get_drivers
        self.dm.update_order=lambda order_id,**kwargs:self.store.update_order_fields(order_id,**{k:v for k,v in kwargs.items() if k!='skip_email'})
        self.app=Flask(__name__);create_driver_api(self.app,self.dm)
        self.client=self.app.test_client()
        self.env=patch.dict(os.environ,{'ENABLE_DRIVER_LOGIN':'true'});self.env.start()

    def tearDown(self):
        self.env.stop();self.store.conn.close();self.tmp.cleanup()

    def login(self,password='long-test-password'):
        return self.client.post('/api/driver/login',json={'phone':'0400000001','password':password})

    def test_driver_password_required_and_revocation(self):
        self.assertEqual(self.login().status_code,401)
        self.access.set_driver_password('d1','long-test-password')
        self.assertEqual(self.login('wrong').status_code,401)
        result=self.login();self.assertEqual(result.status_code,200)
        headers={'Authorization':'Bearer '+result.json['token']}
        stops=self.client.get('/api/driver/runs/current/stops',headers=headers)
        self.assertEqual([s['id'] for s in stops.json['stops']],['o1'])
        self.assertEqual(self.client.post('/api/driver/stops/o2/update',headers=headers,json={'status':'delivered'}).status_code,404)
        self.assertEqual(self.client.post('/api/driver/stops/o2/notify',headers=headers,json={}).status_code,404)
        self.assertEqual(self.client.post('/api/driver/stops/o1/update',headers=headers,json={'status':'invalid'}).status_code,400)
        self.assertEqual(self.client.post('/api/driver/stops/o1/update',headers=headers,json={'status':'delivered','notes':'Left at reception'}).status_code,200)
        self.assertEqual(self.store.get_order_by_id('o1')['status'],'delivered')
        self.access.set_driver_password('d1','new-test-password')
        self.assertEqual(self.client.get('/api/driver/runs',headers=headers).status_code,401)

    def test_driver_lockout(self):
        self.access.set_driver_password('d1','long-test-password')
        for _ in range(5):self.assertEqual(self.login('incorrect').status_code,401)
        self.assertEqual(self.login().status_code,401)

    def test_partner_pending_isolation_transfer_and_suspend(self):
        future=(datetime.now()+timedelta(days=1)).isoformat()
        self.store.create_session_token('token1','partner1',future)
        self.store.create_session_token('token2','partner2',future)
        self.access.assign('partner1',['o1'])
        self.assertTrue(self.access.partner_orders('token1').empty)
        self.access.approve('partner1',True);self.access.approve('partner2',True)
        self.assertEqual(self.access.partner_orders('token1').order_id.tolist(),['o1'])
        self.assertTrue(self.access.partner_orders('token2').empty)
        self.access.assign('partner2',['o1'])
        self.assertTrue(self.access.partner_orders('token1').empty)
        self.assertEqual(self.access.partner_orders('token2').order_id.tolist(),['o1'])
        self.access.approve('partner2',False)
        self.assertTrue(self.access.partner_orders('token2').empty)
        self.assertTrue(self.access.partner_orders('unknown').empty)

    def test_dispatch_run_delivery_evidence_and_driver_workflow(self):
        from data.data_manager import DataManager
        manager=DataManager.__new__(DataManager)
        manager.store=self.store;manager.access=self.access
        manager._mode_override='local';manager._client=None
        app=Flask('workflow');create_driver_api(app,manager)
        client=app.test_client()
        self.access.set_driver_password('d1','long-test-password')
        login=client.post('/api/driver/login',json={'phone':'0400000001','password':'long-test-password'})
        headers={'Authorization':'Bearer '+login.json['token']}
        with patch('data.data_manager.is_email_configured',return_value=False):
            run=manager.create_run('CBD','d1','Driver One',['o1'])['run_id']
            listed=client.get('/api/driver/runs',headers=headers)
            self.assertEqual(listed.json['runs'][0]['id'],run)
            stops=client.get('/api/driver/runs/'+run+'/stops',headers=headers)
            self.assertEqual([x['id'] for x in stops.json['stops']],['o1'])
            self.assertEqual(client.get('/api/driver/runs/unknown/stops',headers=headers).json['stops'],[])
            import base64
            photo=base64.b64encode(b'local-test-media').decode()
            result=client.post('/api/driver/stops/o1/update',headers=headers,json={'status':'delivered','photo':photo,'signature':photo,'notes':'At reception'})
            self.assertEqual(result.status_code,200)
            saved=self.store.get_order_by_id('o1')
            self.assertEqual(saved['proof_photo'],photo)
            self.assertEqual(saved['proof_signature'],photo)
            runs=manager.get_runs()
            self.assertEqual(runs.iloc[0]['status'],'completed')
            self.assertEqual(runs.iloc[0]['progress'],100)
            self.assertEqual(client.get('/api/driver/runs?status=active',headers=headers).json['runs'],[])
        self.assertEqual(client.get('/api/driver/profile',headers=headers).status_code,200)
        self.assertEqual(client.post('/api/driver/go-online',headers=headers,json={}).status_code,200)
        self.assertEqual(client.post('/api/driver/request-offline',headers=headers,json={}).status_code,200)
        self.assertEqual(client.get('/api/driver/profile',headers=headers).json['driver']['pendingStatus'],'offline')
        self.assertEqual(client.post('/api/driver/location',headers=headers,json={'latitude':-33.86,'longitude':151.2}).status_code,200)
        self.assertEqual(float(self.store.get_drivers().set_index('driver_id').loc['d1','latitude']),-33.86)
        self.assertEqual(client.post('/api/driver/messages',headers=headers,json={'body':'Local workflow test'}).status_code,200)
        self.store.save_message('d1','Driver One','Dispatch reply',direction='outbound')
        messages=client.get('/api/driver/messages',headers=headers)
        self.assertEqual([m['body'] for m in messages.json['messages']],['Local workflow test','Dispatch reply'])

    def test_run_cancellation_preserves_deliveries_and_releases_unfinished(self):
        self.store.save_run({'run_id':'r1','driver_id':'d1','driver_name':'Driver One','zone':'CBD','total_stops':2})
        self.store.save_run_orders('r1',['o1','o2'])
        self.access.execute("UPDATE orders SET driver_id='d1'")
        self.access.execute("UPDATE orders SET status='delivered', proof_photo='saved' WHERE order_id='o1'")
        self.access.cancel_run('r1')
        self.assertEqual(self.store.get_order_by_id('o1')['status'],'delivered')
        self.assertEqual(self.store.get_order_by_id('o1')['proof_photo'],'saved')
        self.assertEqual(self.store.get_order_by_id('o2')['status'],'pending')
        self.assertIsNone(self.store.get_order_by_id('o2')['driver_id'])
        self.assertTrue(self.access.driver_run_orders('d1','r1').empty)


if __name__=='__main__':unittest.main()
