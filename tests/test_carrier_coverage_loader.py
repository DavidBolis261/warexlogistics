"""Pinned real candidate loaded only into isolated synthetic API tests."""
from copy import deepcopy
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from flask import Flask
from sqlalchemy import create_engine,select,func
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'DriverAPI'))
from integrations.carrier_coverage import COVERAGE_VERSION,COVERAGE_PATH,load_coverage,validate_document
from integrations.carrier_setup import configure_carrier_uat
from integrations.carrier_persistence import SQLAlchemyUATStore,migrate_carrier_uat,orders
from test_carrier_setup import TOKEN,RECORDS
from test_carrier_preview import order

class LoaderTests(unittest.TestCase):
 def setUp(self):
  self.guard=patch('socket.socket.connect',side_effect=AssertionError('No network'));self.guard.start()
 def tearDown(self):self.guard.stop()
 def test_pinned_dataset_and_source_review_hash(self):
  policy=load_coverage(COVERAGE_VERSION)
  self.assertEqual(policy.classifications['KATOOMBA'],'inside')
  self.assertEqual(policy.classifications['SYDNEY'],'crossing')
  data=json.loads(COVERAGE_PATH.read_bytes())
  review=Path(__file__).resolve().parents[1]/'docs/coverage-review/coverage-candidate.json'
  self.assertEqual(data['source_review_sha256'],hashlib.sha256(review.read_bytes()).hexdigest())
 def test_missing_corrupt_and_incompatible_fail_closed(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'coverage.json'
   with self.assertRaises(ValueError):load_coverage(COVERAGE_VERSION,path)
   path.write_text('{}')
   with self.assertRaises(ValueError):load_coverage(COVERAGE_VERSION,path)
   with self.assertRaises(ValueError):load_coverage('unsupported')
 def test_schema_validation_rejects_bad_types_counts_names_and_duplicate_keys(self):
  good=json.loads(COVERAGE_PATH.read_bytes())
  for key,value in [('schema_version',True),('version','other'),('counts',{}),('classifications',{'Sydney':'inside'}),
                    ('classifications',{'SYDNEY':'allow'}),('source_review_sha256','invalid')]:
   data=deepcopy(good);data[key]=value
   with self.assertRaises(ValueError):validate_document(data)
  data=dict(good,extra=True)
  with self.assertRaises(ValueError):validate_document(data)
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'duplicate.json';raw=b'{"schema_version":1,"schema_version":1}'
   path.write_bytes(raw)
   with patch('integrations.carrier_coverage.COVERAGE_SHA256',hashlib.sha256(raw).hexdigest()):
    with self.assertRaises(ValueError):load_coverage(COVERAGE_VERSION,path)
 def test_disabled_never_loads_dataset(self):
  with patch('integrations.carrier_coverage.load_coverage',side_effect=AssertionError('Must not load')):
   app=Flask('disabled-version')
   self.assertFalse(configure_carrier_uat(app,object(),{'CARRIER_UAT_COVERAGE_VERSION':'bad'}))
   self.assertEqual(app.test_client().post('/api/v1/uat/rates').status_code,404)
 def test_invalid_enabled_version_registers_nothing(self):
  app=Flask('invalid-version')
  env={'CARRIER_UAT_ENABLED':'true','CARRIER_UAT_CREDENTIALS_JSON':json.dumps(RECORDS),'CARRIER_UAT_COVERAGE_VERSION':'bad'}
  with self.assertRaises(ValueError):configure_carrier_uat(app,object(),env)
  self.assertFalse(any('/uat/' in r.rule for r in app.url_map.iter_rules()))
 def test_real_inside_and_review_locations_via_enabled_wiring(self):
  engine=create_engine('sqlite://');migrate_carrier_uat(engine);store=SQLAlchemyUATStore(engine)
  try:
   app=Flask('local-loaded')
   env={'CARRIER_UAT_ENABLED':'true','CARRIER_UAT_CREDENTIALS_JSON':json.dumps(RECORDS),'CARRIER_UAT_COVERAGE_VERSION':COVERAGE_VERSION}
   fake=SimpleNamespace(engine=SimpleNamespace(dialect=SimpleNamespace(name='postgresql')))
   with patch('integrations.carrier_setup.SQLAlchemyUATStore',return_value=store):configure_carrier_uat(app,fake,env)
   client=app.test_client();headers={'X-API-Key':TOKEN,'Idempotency-Key':'fixture'}
   body=order();body['origin']['suburb']='KATOOMBA';body['destination']['suburb']='WINDSOR'
   quote=lambda b:client.post('/api/v1/uat/rates',json={k:b[k] for k in ('origin','destination','parcels')},headers=headers)
   result=quote(body);self.assertEqual(result.status_code,200);self.assertEqual(result.json['total_aud'],'13.80')
   self.assertEqual(result.json['coverage_version'],COVERAGE_VERSION)
   self.assertEqual(client.post('/api/v1/uat/orders',json=body,headers=headers).status_code,201)
   self.assertEqual(client.post('/api/v1/uat/orders',json=body,headers=headers).status_code,200)
   for side in ('origin','destination'):
    for name,status in [('SYDNEY',409),('THE ROCKS',409),('UNLISTED SYNTHETIC PLACE',409),('GOSFORD',422)]:
     changed=deepcopy(body);changed[side]['suburb']=name
     response=quote(changed);self.assertEqual(response.status_code,status);self.assertNotIn('total_aud',response.json)
     h=dict(headers,**{'Idempotency-Key':side+name.replace(' ','-')})
     self.assertEqual(client.post('/api/v1/uat/orders',json=changed,headers=h).status_code,status)
   with engine.connect() as conn:self.assertEqual(conn.execute(select(func.count()).select_from(orders)).scalar(),1)
  finally:engine.dispose()
