import json,hashlib,urllib.request,urllib.parse
from pathlib import Path
from datetime import datetime,timezone
import argparse
parser=argparse.ArgumentParser();parser.add_argument('output_directory',type=Path)
root=parser.parse_args().output_directory
root.mkdir(parents=True,exist_ok=True)
base='https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/EDP/Administrative_Boundaries/MapServer'
manifest=[]
def get(layer,params):
 url=base+'/'+str(layer)+'/query?'+urllib.parse.urlencode(params)
 with urllib.request.urlopen(url,timeout=30) as r:raw=r.read()
 data=json.loads(raw)
 if 'error' in data:raise ValueError(data['error'])
 return data,raw,url
for layer,where,fields,expected in [(1,'1=1','OBJECTID,CADID,LGANAME,COUNCILNAME,ABSCODE,LASTUPDATE',132),(0,'STATE=2','OBJECTID,CADID,SUBURBNAME,STATE,LASTUPDATE',4607)]:
 ids=sorted(get(layer,dict(where=where,returnIdsOnly='true',f='json'))[0]['objectIds']);assert len(ids)==expected
 features=[]
 for offset in range(0,len(ids),25):
  path=root/('layer%d-ids%d.json'%(layer,offset))
  params=dict(objectIds=','.join(map(str,ids[offset:offset+25])),outFields=fields,returnGeometry='true',outSR=4283,f='json')
  url=base+'/'+str(layer)+'/query?'+urllib.parse.urlencode(params)
  if path.exists():raw=path.read_bytes();data=json.loads(raw)
  else:
   data,raw,url=get(layer,params);path.write_bytes(raw)
  assert {x['attributes']['OBJECTID'] for x in data['features']}==set(ids[offset:offset+25])
  manifest.append(dict(file=path.name,url=url,sha256=hashlib.sha256(raw).hexdigest(),retrieved_at=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),count=len(data['features'])))
  features.extend(data['features'])
  print(layer,offset,len(features),flush=True)
 assert len(features)==expected
 (root/('layer%d-all.json'%layer)).write_text(json.dumps(dict(features=features)))
(root/'manifest.json').write_text(json.dumps(manifest,indent=2))
