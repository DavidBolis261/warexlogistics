"""Synthetic access and temporary persistence only; no server import/network."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from flask import Flask
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'DriverAPI'))
from api.carrier_preview import Conflict, create_carrier_preview_blueprint
from integrations.carrier_persistence import SQLAlchemyUATStore, migrate_carrier_uat, orders
from integrations.carrier_setup import configure_carrier_uat, identity_resolver
from test_carrier_preview import POLICY, order

TOKEN = 'synthetic-test-only-token-not-a-real-key'
RECORDS = [{'partner_id': 'fixture', 'token_sha256': hashlib.sha256(TOKEN.encode()).hexdigest()}]

class WiringTests(unittest.TestCase):
    def setUp(self):
        self.guard = patch('socket.socket.connect', side_effect=AssertionError('No network'))
        self.guard.start()
    def tearDown(self):
        self.guard.stop()

    def test_disabled_does_not_touch_store_or_register_routes(self):
        class Forbidden:
            @property
            def engine(self): raise AssertionError('DB touched while disabled')
        app = Flask('disabled')
        app.add_url_rule('/existing', view_func=lambda: 'unchanged')
        self.assertFalse(configure_carrier_uat(app, Forbidden(), {}))
        self.assertEqual(app.test_client().get('/existing').data, b'unchanged')
        self.assertEqual(app.test_client().post('/api/v1/uat/orders').status_code, 404)

    def test_enable_requires_valid_access_and_postgres(self):
        for env in ({'CARRIER_UAT_ENABLED':'true'},
                    {'CARRIER_UAT_ENABLED':'true','CARRIER_UAT_CREDENTIALS_JSON':'[]'}):
            with self.assertRaises(ValueError): configure_carrier_uat(Flask('bad'), object(), env)
        env = {'CARRIER_UAT_ENABLED':'true','CARRIER_UAT_CREDENTIALS_JSON':json.dumps(RECORDS)}
        with self.assertRaises(ValueError): configure_carrier_uat(Flask('bad'), object(), env)
        for records in (RECORDS * 2, [{'partner_id':'fixture','token_sha256':'bad'}]):
            with self.assertRaises(ValueError): identity_resolver(records)

    def test_enabled_wiring_checks_schema_and_fails_closed_without_coverage(self):
        app = Flask('enabled')
        engine = SimpleNamespace(dialect=SimpleNamespace(name='postgresql'))
        store = Mock()
        env = {'CARRIER_UAT_ENABLED':'true','CARRIER_UAT_CREDENTIALS_JSON':json.dumps(RECORDS)}
        with patch('integrations.carrier_setup.SQLAlchemyUATStore', return_value=store) as factory:
            self.assertTrue(configure_carrier_uat(app, SimpleNamespace(engine=engine), env))
            factory.assert_called_once_with(engine)
            store.check_schema.assert_called_once_with()
        client = app.test_client()
        body = {k:order()[k] for k in ('origin','destination','parcels')}
        self.assertEqual(client.post('/api/v1/uat/rates',json=body).status_code,403)
        result = client.post('/api/v1/uat/rates',json=body,headers={'X-API-Key':TOKEN})
        self.assertEqual(result.status_code,409)
        self.assertEqual(result.json['unresolved_rules'],['sydney_boundary_not_configured'])
        store.create.assert_not_called()

    def test_no_startup_migration_and_explicit_additive_schema(self):
        engine = create_engine('sqlite://')
        store = SQLAlchemyUATStore(engine)
        self.assertEqual(inspect(engine).get_table_names(), [])
        with self.assertRaises(Exception): store.check_schema()
        migrate_carrier_uat(engine);migrate_carrier_uat(engine)
        store.check_schema()
        self.assertEqual(inspect(engine).get_table_names(), ['carrier_uat_orders'])
        engine.dispose()

    def test_persistent_atomic_race_restart_and_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            url = 'sqlite:///' + str(Path(directory)/'uat.db')
            engine = create_engine(url);migrate_carrier_uat(engine)
            def create(_): return SQLAlchemyUATStore(engine).create('fixture','key',order(),{'total_aud':'13.80'})
            with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(create, range(2)))
            self.assertEqual(results[0][0],results[1][0])
            self.assertEqual(sum(not x[2] for x in results),1)
            engine.dispose();engine=create_engine(url);store=SQLAlchemyUATStore(engine)
            self.assertEqual(store.replay('fixture','key',order())[0],results[0][0])
            with self.assertRaises(Conflict): store.create('fixture','key',{'changed':True},{})
            self.assertIsNone(store.get('another',results[0][0]))
            with engine.connect() as conn:self.assertEqual(len(conn.execute(select(orders)).all()),1)
            engine.dispose()

    def test_auth_and_real_label_through_sqlalchemy_store(self):
        engine=create_engine('sqlite://');migrate_carrier_uat(engine)
        app=Flask('adapter');app.register_blueprint(create_carrier_preview_blueprint(
            identity_resolver(RECORDS),SQLAlchemyUATStore(engine),POLICY))
        client=app.test_client();headers={'X-API-Key':TOKEN,'Idempotency-Key':'synthetic'}
        for token in ('','operational-key-is-not-an-accepted-test-token','x'*257):
            self.assertEqual(client.post('/api/v1/uat/orders',json=order(),headers={'X-API-Key':token}).status_code,403)
        first=client.post('/api/v1/uat/orders',json=order(),headers=headers)
        self.assertEqual(first.status_code,201)
        self.assertEqual(client.post('/api/v1/uat/orders',json=order(),headers=headers).status_code,200)
        label=client.get('/api/v1/uat/orders/'+first.json['tracking_number']+'/label',headers=headers)
        self.assertEqual(label.status_code,200);self.assertTrue(label.data.startswith(b'%PDF-'))
        engine.dispose()

    def test_postgres_conflict_statement_compiles(self):
        statement=insert(orders).values(partner='fixture',request_key='key',digest='digest',tracking='UAT-test',payload='{}').on_conflict_do_nothing(
            index_elements=['partner','request_key']).returning(orders.c.tracking)
        sql=str(statement.compile(dialect=postgresql.dialect()))
        self.assertIn('ON CONFLICT (partner, request_key) DO NOTHING',sql)
        self.assertIn('RETURNING carrier_uat_orders.tracking',sql)
