import os,json,subprocess,tempfile,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'DriverAPI'))
sys.path.insert(0,str(PROJECT/'tests'))
from sqlalchemy import create_engine,select,text,inspect
from sqlalchemy.engine import URL
from integrations.carrier_persistence import SQLAlchemyUATStore,migrate_carrier_uat,orders
from api.carrier_preview import Conflict
from test_carrier_preview import order
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--pg-bin',required=True,type=Path)
bin=parser.parse_args().pg_bin
report={}
with tempfile.TemporaryDirectory(prefix='warex-pg18-',dir='/tmp') as folder:
 root=Path(folder);data=root/'db';sock=root/'socket';sock.mkdir(mode=0o700)
 subprocess.run([str(bin/'initdb'),'-D',str(data),'-L',str(bin.parent/'share/postgresql'),'--auth-local=peer','--auth-host=reject','--encoding=UTF8','--locale=C'],check=True,stdout=subprocess.DEVNULL)
 started=False;engine=None
 try:
  subprocess.run([str(bin/'pg_ctl'),'-D',str(data),'-l',str(root/'postgres.log'),'-o',"-h '' -k "+str(sock)+" -c unix_socket_permissions=0700",'-w','start'],check=True,stdout=subprocess.DEVNULL)
  started=True
  engine=create_engine(URL.create('postgresql+psycopg2',database='postgres',query={'host':str(sock)}))
  with engine.connect() as c:
   report['server_version']=c.execute(text('SHOW server_version')).scalar()
   assert c.execute(text('SHOW listen_addresses')).scalar()==''
  store=SQLAlchemyUATStore(engine)
  assert inspect(engine).get_table_names()==[]
  migrate_carrier_uat(engine);migrate_carrier_uat(engine);store.check_schema()
  assert inspect(engine).get_table_names()==['carrier_uat_orders']
  def create(_):return SQLAlchemyUATStore(engine).create('synthetic','race',order(),{'test':True})
  with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(create,range(8)))
  assert len({r[0] for r in results})==1 and sum(not r[2] for r in results)==1
  try:store.create('synthetic','race',{'different':True},{})
  except Conflict:pass
  else:raise AssertionError('conflict not detected')
  assert store.get('another',results[0][0]) is None
  engine.dispose()
  subprocess.run([str(bin/'pg_ctl'),'-D',str(data),'-m','fast','-w','restart','-l',str(root/'postgres.log')],check=True,stdout=subprocess.DEVNULL)
  assert store.replay('synthetic','race',order())[0]==results[0][0]
  with engine.connect() as c:assert len(c.execute(select(orders)).all())==1
  # Real production-compatible enabled wiring, synthetic access, fixture geography.
  from flask import Flask
  from types import SimpleNamespace
  import hashlib
  from integrations.carrier_setup import configure_carrier_uat
  from test_carrier_preview import POLICY
  app=Flask('pg-test');app.add_url_rule('/existing',view_func=lambda:'unchanged')
  token='synthetic-only-not-an-issued-key-12345'
  env={'CARRIER_UAT_ENABLED':'true','CARRIER_UAT_CREDENTIALS_JSON':json.dumps([{'partner_id':'synthetic','token_sha256':hashlib.sha256(token.encode()).hexdigest()}])}
  configure_carrier_uat(app,SimpleNamespace(engine=engine),env,POLICY)
  client=app.test_client();headers={'X-API-Key':token,'Idempotency-Key':'api'}
  assert client.get('/existing').data==b'unchanged'
  assert client.post('/api/v1/uat/orders',json=order()).status_code==403
  created=client.post('/api/v1/uat/orders',json=order(),headers=headers);assert created.status_code==201
  assert client.post('/api/v1/uat/orders',json=order(),headers=headers).status_code==200
  label=client.get('/api/v1/uat/orders/'+created.json['tracking_number']+'/label',headers=headers)
  assert label.status_code==200 and label.data.startswith(b'%PDF-')
  report.update(migration='additive and repeatable',race='8 writers, one record',conflict='rejected without overwrite',partner_scope='isolated',restart='persisted',api='auth/create/replay/PDF passed',existing_route='unchanged',tcp='disabled')
 finally:
  if engine:engine.dispose()
  if started:subprocess.run([str(bin/'pg_ctl'),'-D',str(data),'-m','fast','-w','stop'],check=True,stdout=subprocess.DEVNULL)
report['temporary_cluster']='stopped and removed'
Path('/tmp/warex-pg18-validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
