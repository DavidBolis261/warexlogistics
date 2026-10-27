"""Exercise actual server wiring with synthetic managers and all startup effects mocked."""
import ast,os,runpy,subprocess,sys,types,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'DriverAPI'))
class DisabledServerTests(unittest.TestCase):
 def test_real_server_disabled_keeps_existing_routes_and_auth(self):
  import api.external_api as external
  manager=Mock();manager.get_setting.return_value=''
  # Health checks a fake engine; never opens an actual DB.
  manager.store.engine.connect.return_value.__enter__=Mock(return_value=Mock())
  manager.store.engine.connect.return_value.__exit__=Mock(return_value=False)
  data=types.ModuleType('data.data_manager');data.DataManager=Mock(return_value=manager)
  worker=types.ModuleType('integrations.starshipit_worker');worker.start_worker=Mock()
  email=types.ModuleType('utils.email_service');email.is_email_configured=lambda dm:False;email._get_email_config=lambda dm:{}
  with patch.dict(os.environ,{},clear=True),patch.dict(sys.modules,{
    'data.data_manager':data,'integrations.starshipit_worker':worker,'utils.email_service':email}),patch.object(external,'_EXTERNAL_API_KEY',''),patch('socket.socket.connect',side_effect=AssertionError('No network')):
   namespace=runpy.run_path(str(ROOT/'DriverAPI/driver_api_server.py'),run_name='isolated_server_test')
   app=namespace['app'];client=app.test_client()
   rules={r.rule for r in app.url_map.iter_rules()}
   self.assertIn('/api/v1/orders',rules);self.assertIn('/api/driver/login',rules)
   self.assertIn('/health',rules);self.assertIn('/api/driver/docs',rules)
   self.assertFalse(any('/uat/' in rule for rule in rules))
   self.assertEqual(client.get('/health').status_code,200)
   # Existing docs defect: compare unchanged function with HEAD, do not
   # misreport its pre-existing serialization error as a UAT regression.
   baseline=subprocess.check_output(['git','show','HEAD:DriverAPI/driver_api_server.py'],cwd=ROOT,text=True)
   def docs_ast(source):
    return ast.dump(next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='api_docs'))
   self.assertEqual(docs_ast(baseline),docs_ast((ROOT/'DriverAPI/driver_api_server.py').read_text()))
   with self.assertRaises(TypeError): app.json.dumps(namespace['api_docs']()[0])
   self.assertEqual(client.post('/api/v1/orders',json={}).status_code,503)
   self.assertEqual(client.post('/api/v1/uat/orders',json={}).status_code,404)
   with patch.object(external,'_EXTERNAL_API_KEY','synthetic-existing-key'):
    self.assertEqual(client.post('/api/v1/orders',json={}).status_code,401)
    self.assertEqual(client.post('/api/v1/orders',json={},headers={'X-API-Key':'wrong'}).status_code,403)
    self.assertEqual(client.post('/api/v1/orders',json={},headers={'X-API-Key':'synthetic-existing-key'}).status_code,400)
   manager.create_order.assert_not_called()
   worker.start_worker.assert_called_once_with()  # Mocked; no thread starts.
