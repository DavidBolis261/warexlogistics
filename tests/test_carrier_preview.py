"""In-process test client; temporary stores, synthetic identities, no outbound I/O."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask
from pypdf import PdfReader
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'DriverAPI'))
from api.carrier_preview import UATStore,TestIdentity,create_carrier_preview_blueprint
from integrations.draft_rates import CoveragePolicy,calculate_rate

ROOT=Path(__file__).resolve().parents[1]
POLICY=CoveragePolicy('TEST-FIXTURE-NOT-SYDNEY',frozenset({('Fixture Locality','0000')}))


def order():
    place={'suburb':'Fixture Locality','postcode':'0000','state':'NSW','country':'AU'}
    return {'origin':dict(place),'destination':dict(place),
            'parcels':[{'actual_weight_kg':'1'},{'actual_weight_kg':'5.1'}],
            'sender':{'name':'Test Sender','address':'1 Fixture Street'},
            'recipient':{'name':'Test Recipient','address':'2 Fixture Street','email':'test@example.invalid','phone':'000'},
            'instructions':'SYNTHETIC DATA - DO NOT DISPATCH'}


class CarrierTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.store=UATStore(self.db)
        # Decoy operational tables prove test records are never inserted there.
        for table in ('orders','runs','drivers'):self.db.execute('CREATE TABLE '+table+' (id TEXT)')
        self.db.commit();self.identity=TestIdentity('fixture-one',True)
        self.app=Flask('isolated');self.app.register_blueprint(create_carrier_preview_blueprint(lambda r:self.identity,self.store,POLICY))
        self.client=self.app.test_client();self.body=order()
        self.patches=[patch('socket.socket.connect',side_effect=AssertionError('No network')),
                      patch('requests.sessions.Session.request',side_effect=AssertionError('No HTTP'))]
        for p in self.patches:p.start()

    def tearDown(self):
        for p in self.patches:p.stop()
        for table in ('orders','runs','drivers'):
            self.assertEqual(self.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
        self.db.close()

    def create(self,body=None,key='test-request'):
        return self.client.post('/api/v1/uat/orders',json=self.body if body is None else body,headers={'Idempotency-Key':key})

    def test_rate_contract_success_and_invalid_data(self):
        body={k:self.body[k] for k in ('origin','destination','parcels')}
        r=self.client.post('/api/v1/uat/rates',json=body)
        self.assertEqual(r.status_code,200);self.assertEqual(r.json['total_aud'],'13.80')
        self.assertTrue(r.json['test'])
        body['parcels'][0]['actual_weight_kg']='23'
        self.assertEqual(self.client.post('/api/v1/uat/rates',json=body).status_code,400)

    def test_idempotency_canonicalisation_conflict_and_retrieval(self):
        first=self.create();self.assertEqual(first.status_code,201)
        body=deepcopy(self.body);body['parcels'][0]['actual_weight_kg']='1.00'
        replay=self.create(body);self.assertEqual(replay.status_code,200)
        tracking=first.json['tracking_number'];self.assertEqual(replay.json['tracking_number'],tracking)
        self.assertEqual(replay.json['created_at'],first.json['created_at'])
        body['recipient']['address']='Changed';self.assertEqual(self.create(body).status_code,409)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM carrier_uat_orders').fetchone()[0],1)
        r=self.client.get('/api/v1/uat/orders/'+tracking);self.assertEqual(r.status_code,200)
        self.assertEqual(r.json['status'],'test_pending');self.assertEqual(len(r.json['parcel_ids']),2)
        tracking_response=self.client.get('/api/v1/uat/orders/'+tracking+'/track')
        self.assertEqual(tracking_response.json['events'][0]['occurred_at'],first.json['created_at'])

    def test_denial_and_no_client_selected_identity(self):
        for identity in (None,TestIdentity('fixture-one',False),TestIdentity('',True)):
            self.identity=identity;self.assertEqual(self.create().status_code,403)
        self.identity=TestIdentity('fixture-one',True)
        for field in ('test','partner_id','quote_ready'):
            body=dict(self.body,**{field:True});self.assertEqual(self.create(body).status_code,400)

    def test_partner_scoping_all_read_routes_and_keys(self):
        tracking=self.create().json['tracking_number'];self.identity=TestIdentity('fixture-two',True)
        for suffix in ('','/track','/label'):
            self.assertEqual(self.client.get('/api/v1/uat/orders/'+tracking+suffix).status_code,404)
        other=self.create();self.assertEqual(other.status_code,201);self.assertNotEqual(other.json['tracking_number'],tracking)

    def test_actual_pdf_labels_page_size_ids_and_test_watermark(self):
        created=self.create().json;tracking=created['tracking_number']
        r=self.client.get('/api/v1/uat/orders/'+tracking+'/label')
        self.assertEqual(r.status_code,200);self.assertEqual(r.mimetype,'application/pdf')
        pdf=PdfReader(BytesIO(r.data));self.assertEqual(len(pdf.pages),2)
        for page,identifier in zip(pdf.pages,created['parcel_ids']):
            self.assertEqual((float(page.mediabox.width),float(page.mediabox.height)),(288,432))
            self.assertIn(identifier,page.extract_text());self.assertIn('TEST ONLY - NOT FOR DELIVERY',page.extract_text())
        self.assertEqual(r.headers['Cache-Control'],'no-store')

    def test_actual_html_labels_escape_input_and_embed_qr(self):
        body=deepcopy(self.body);body['recipient']['name']='<script>alert(1)</script>'
        tracking=self.create(body).json['tracking_number']
        r=self.client.get('/api/v1/uat/orders/'+tracking+'/label?format=html')
        self.assertEqual(r.status_code,200);self.assertEqual(r.mimetype,'text/html')
        self.assertNotIn(b'<script>',r.data);self.assertIn(b'&lt;script&gt;',r.data)
        self.assertEqual(r.data.count(b'data:image/svg+xml;base64,'),2)
        self.assertEqual(self.client.get('/api/v1/uat/orders/'+tracking+'/label?format=zpl').status_code,400)

    def test_coverage_still_blocks_orders_with_or_without_cover(self):
        app=Flask('no-coverage');app.register_blueprint(create_carrier_preview_blueprint(lambda r:self.identity,self.store))
        r=app.test_client().post('/api/v1/uat/orders',json=self.body,headers={'Idempotency-Key':'unset'})
        self.assertEqual(r.status_code,409)
        body=deepcopy(self.body);body['parcels'][0].update(cover_selected=True,declared_value_aud='5000')
        r=app.test_client().post('/api/v1/uat/orders',json=body,headers={'Idempotency-Key':'covered-unset'})
        self.assertEqual(r.status_code,409)
        self.assertEqual(r.json['rate']['cover_charge_aud'],'50.00')
        self.assertEqual(r.json['rate']['unresolved_rules'],['sydney_boundary_not_configured'])
        body=deepcopy(self.body);body['origin']['suburb']='Unknown'
        self.assertEqual(self.create(body).status_code,422)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM carrier_uat_orders').fetchone()[0],0)

    def test_selected_cover_rate_order_and_replay(self):
        body=deepcopy(self.body)
        body['parcels'][0].update(cover_selected=True,declared_value_aud='5000')
        quote=self.client.post('/api/v1/uat/rates',json={k:body[k] for k in ('origin','destination','parcels')})
        self.assertEqual(quote.status_code,200)
        self.assertEqual(quote.json['cover_charge_aud'],'50.00')
        self.assertTrue(quote.json['cover_gst_included'])
        self.assertEqual(quote.json['total_aud'],'63.80')
        first=self.create(body);replay=self.create(body)
        self.assertEqual(first.status_code,201);self.assertEqual(replay.status_code,200)
        self.assertEqual(first.json['rate']['total_aud'],'63.80')
        self.assertEqual(first.json['tracking_number'],replay.json['tracking_number'])
        self.assertEqual(first.json['rate'],replay.json['rate'])

    def test_invalid_input_missing_key_and_size(self):
        for body in ([],{},dict(self.body,parcels=[]),dict(self.body,recipient=None)):
            self.assertEqual(self.create(body).status_code,400)
        self.assertEqual(self.create(key='').status_code,400)
        self.assertEqual(self.client.post('/api/v1/uat/orders',data='x'*65537).status_code,413)

    def test_live_server_untouched_and_no_operational_dependency(self):
        self.assertIn('configure_carrier_uat(app, data_manager.store, os.environ)',(ROOT/'DriverAPI/driver_api_server.py').read_text())
        source=(ROOT/'DriverAPI/api/carrier_preview.py').read_text()
        self.assertNotIn('from data.data_manager',source)

    def test_persistence_replay_and_two_connection_race(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=str(Path(tmp)/'only-test.db')
            db=sqlite3.connect(path);UATStore(db);db.close()
            def worker(_):
                db=sqlite3.connect(path,timeout=10);store=UATStore(db)
                result=store.create('fixture','concurrent-key',self.body,{'test':True})
                db.close();return result
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(worker,range(2)))
            self.assertEqual(results[0][0],results[1][0]);self.assertEqual(sum(not r[2] for r in results),1)
            db=sqlite3.connect(path);store=UATStore(db)
            self.assertEqual(store.replay('fixture','concurrent-key',self.body)[0],results[0][0]);db.close()


if __name__=='__main__':unittest.main()
