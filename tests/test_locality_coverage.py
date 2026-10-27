"""Synthetic classification only; no real Sydney coverage is asserted."""
from copy import deepcopy
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch
from flask import Flask
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'DriverAPI'))
from integrations.draft_rates import LocalityCoveragePolicy, calculate_rate
from api.carrier_preview import UATStore, TestIdentity, create_carrier_preview_blueprint
from test_carrier_preview import order

CLASSIFICATIONS={'Fixture Locality':'inside','Fixture Outside':'outside',
                 'Fixture Ambiguous':'ambiguous','Fixture Crossing':'crossing'}
POLICY=LocalityCoveragePolicy('SYNTHETIC-v1','synthetic fixtures; not geographic evidence',CLASSIFICATIONS)

class LocalityTests(unittest.TestCase):
    def setUp(self):
        self.guard=patch('socket.socket.connect',side_effect=AssertionError('No network'))
        self.guard.start()
        self.db=sqlite3.connect(':memory:');self.store=UATStore(self.db)
        app=Flask('locality');app.register_blueprint(create_carrier_preview_blueprint(
            lambda request:TestIdentity('fixture',True),self.store,POLICY))
        self.client=app.test_client()
    def tearDown(self):
        self.db.close();self.guard.stop()
    def quote(self,body):
        return self.client.post('/api/v1/uat/rates',json={k:body[k] for k in ('origin','destination','parcels')})
    def create(self,body):
        return self.client.post('/api/v1/uat/orders',json=body,headers={'Idempotency-Key':'fixture'})

    def test_inside_both_ends_and_postcode_is_not_validated(self):
        body=order();body['origin']['suburb']='  fixture   locality '
        body['destination']['postcode']='9999'
        quote=self.quote(body)
        self.assertEqual(quote.status_code,200)
        self.assertEqual(quote.json['coverage_classification'],{'origin':'inside','destination':'inside'})
        self.assertEqual(quote.json['postcode_validation'],'format_only_not_matched_to_locality')
        self.assertEqual(quote.json['coverage_version'],'SYNTHETIC-v1')
        created=self.create(body);self.assertEqual(created.status_code,201)
        self.assertEqual(created.json['rate']['coverage_basis'],'gazetted_locality_name_state_country')
        body['destination']['postcode']='invalid'
        self.assertEqual(self.quote(body).status_code,400)

    def test_each_end_outside_ambiguous_crossing_unknown_blocks_both_routes(self):
        for side in ('origin','destination'):
            for name,status in [('Fixture Outside','outside'),('Fixture Ambiguous','ambiguous'),
                                ('Fixture Crossing','crossing'),('Fixture Unknown','unknown')]:
                with self.subTest(side=side,status=status):
                    body=order();body[side]['suburb']=name
                    quote=self.quote(body);created=self.create(body)
                    expected=422 if status=='outside' else 409
                    self.assertEqual(quote.status_code,expected);self.assertEqual(created.status_code,expected)
                    self.assertEqual(quote.json['coverage_classification'][side],status)
                    self.assertFalse(quote.json['quote_ready']);self.assertNotIn('total_aud',quote.json)
                    self.assertEqual(created.json['rate'],{k:v for k,v in quote.json.items() if k!='test'})
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM carrier_uat_orders').fetchone()[0],0)

    def test_state_country_and_mixed_blockers(self):
        for side in ('origin','destination'):
            for field,value in [('state','VIC'),('country','NZ')]:
                body=order();body[side][field]=value
                self.assertEqual(self.quote(body).status_code,422)
                self.assertEqual(self.create(body).status_code,422)
        body=order();body['origin']['suburb']='Fixture Outside';body['destination']['suburb']='Fixture Crossing'
        result=self.quote(body)
        self.assertEqual(result.status_code,422)
        self.assertEqual(result.json['unresolved_rules'],['origin_or_destination_outside_configured_coverage','locality_coverage_review_required'])

    def test_policy_provenance_duplicates_and_immutability(self):
        for version,source,data in [('', 'source',CLASSIFICATIONS),('v','',CLASSIFICATIONS),
                ('v','source',{}),('v','source',{'Foo':'inside',' foo ':'outside'}),
                ('v','source',{'Foo':'guess'})]:
            with self.assertRaises(ValueError):LocalityCoveragePolicy(version,source,data)
        data={'Fixture Locality':'inside'};policy=LocalityCoveragePolicy('v','synthetic',data)
        data['Fixture Locality']='outside'
        self.assertEqual(policy.classifications['FIXTURE LOCALITY'],'inside')
        with self.assertRaises(TypeError):policy.classifications['FIXTURE LOCALITY']='outside'

    def test_client_cannot_select_classification_or_policy(self):
        for field in ('coverage_version','classifications','coverage_basis'):
            body=order();body[field]='inside'
            self.assertEqual(self.create(body).status_code,400)
        body=order();body['origin']['classification']='inside'
        self.assertEqual(self.quote(body).status_code,400)

    def test_absent_policy_still_blocks(self):
        body=order();result=calculate_rate({k:body[k] for k in ('origin','destination','parcels')})
        self.assertEqual(result['unresolved_rules'],['sydney_boundary_not_configured'])
        self.assertEqual(result['coverage_basis'],'not_configured')
        self.assertNotIn('total_aud',result)
