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


if __name__=='__main__':unittest.main()
