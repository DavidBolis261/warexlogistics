"""Build-time only; Shapely is not a runtime dependency. No geometry repairs."""
import json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
from shapely.geometry import Polygon,MultiPolygon,LinearRing
from shapely.ops import unary_union
from shapely.validation import explain_validity
import shapely
ROOT=Path('/tmp/warex-boundary-source')  # Override through the command-line argument.
COUNCILS='Bayside;Blacktown;Blue Mountains;Burwood;Camden;Campbelltown;Canada Bay;Canterbury-Bankstown;Cumberland;Fairfield;Georges River;Hawkesbury;Hornsby;Hunters Hill;Inner West;Ku-ring-gai;Lane Cove;Liverpool;Mosman;North Sydney;Northern Beaches;Parramatta;Penrith;Randwick;Ryde;Strathfield;Sutherland Shire;Sydney;The Hills Shire;Waverley;Willoughby;Wollondilly;Woollahra'.split(';')
def normal(s):return ' '.join(s.upper().split())
def geometry(record):
 rings=record['geometry']['rings']
 shells=[];holes=[]
 for coords in rings:
  ring=LinearRing(coords)
  (holes if ring.is_ccw else shells).append(coords)
 if not shells:raise ValueError('No exterior rings')
 shell_polys=[Polygon(s) for s in shells];assigned=[[] for _ in shells]
 for h in holes:
  hole=Polygon(h)
  owners=[i for i,p in enumerate(shell_polys) if p.covers(hole)]
  if not owners:raise ValueError('Hole has no enclosing exterior')
  owner=min(owners,key=lambda i:shell_polys[i].area);assigned[owner].append(h)
 polys=[Polygon(s,h) for s,h in zip(shells,assigned)]
 result=polys[0] if len(polys)==1 else MultiPolygon(polys)
 if result.is_empty or not result.is_valid:raise ValueError(explain_validity(result))
 return result

def classify(g,region):
 if region.covers(g):return 'inside'
 if not region.intersects(g):return 'outside'
 if region.intersection(g).area==0:return 'outside'
 return 'crossing'

def resolve_name(entries):
 statuses = {entry['classification'] for entry in entries}
 # Every source part must independently establish the same safe decision.
 # Combining names must never hide an invalid geometry or an outside part.
 if statuses == {'inside'}:return 'inside'
 if statuses == {'outside'}:return 'outside'
 if len(entries) == 1:return entries[0]['classification']
 return 'ambiguous'

def build():
 lgas=json.loads((ROOT/'layer1-all.json').read_text())['features']
 localities=json.loads((ROOT/'layer0-all.json').read_text())['features']
 assert len(lgas)==132 and len(localities)==4607
 selected=[];matches=[]
 for wanted in COUNCILS:
  found=[r for r in lgas if normal(r['attributes']['LGANAME'])==normal({'Parramatta':'City of Parramatta'}.get(wanted,wanted))]
  if len(found)!=1:raise ValueError('Council count mismatch '+wanted+': '+str(len(found)))
  matches.append(found[0]['attributes']);selected.append(geometry(found[0]))
 region=unary_union(selected)
 if not region.is_valid:raise ValueError('Invalid council union')
 shapely.prepare(region)
 records=[];names=defaultdict(list)
 for f in localities:
  a=f['attributes'];name=normal(a['SUBURBNAME']);entry=dict(name=name,object_id=a['OBJECTID'],cadid=a['CADID'],lastupdate=a.get('LASTUPDATE'))
  try:
   g=geometry(f);status=classify(g,region)
   entry['classification']=status
   if status=='crossing':
    outside=g.difference(region);entry.update(outside_fraction=outside.area/g.area,outside_bounds=list(outside.bounds),outside_area_square_degrees=outside.area)
  except ValueError as exc:entry.update(classification='ambiguous',issue='invalid_geometry: '+str(exc))
  records.append(entry);names[name].append(entry)
 classifications={n:resolve_name(es) for n,es in names.items()}
 name_resolution=[]
 for name,entries in names.items():
  if len(entries)>1:
   name_resolution.append(dict(name=name,classification=classifications[name],
       source_classifications=[e['classification'] for e in entries],
       object_ids=[e['object_id'] for e in entries],
       reason='all_parts_same_safe_classification' if classifications[name] in ('inside','outside') else 'mixed_or_invalid_parts'))
 report=dict(version='nsw-33-councils-locality-candidate-v2-'+datetime.now(timezone.utc).strftime('%Y%m%d'),
  source_reference='NSW Administrative Boundaries, snapshot hashes in source_manifest',
  activation_status='disabled_candidate_requires_review',crs='EPSG:4283',
  attribution='Adapted from NSW Administrative Boundaries. © Land and Property Information 2015 / State of New South Wales.',
  licence='https://creativecommons.org/licenses/by/3.0/au/',
  licence_evidence='https://www.data.nsw.gov.au/data/en/dataset/nsw-administrative-boundaries/resource/4251704c-586a-4328-8b22-f2fe6d860dc3',
  council_source='https://www.planning.nsw.gov.au/plans-in-nsw/the-sydney-plan/frequently-asked-questions',
  adaptation='Union 33 councils; full-precision whole multipart locality covered by union. No buffer, repair, simplification or postcode data. Invalid geometry ambiguous. Repeated names inside/outside only when every part has that same classification; mixed names ambiguous. Area ratios diagnostic only, never used to admit slivers.',
  shapely_version=shapely.__version__,geos_version=shapely.geos_version_string,
  counts=dict(Counter(classifications.values())),record_counts=dict(Counter(e['classification'] for e in records)),
  council_name_aliases={'Parramatta':'CITY OF PARRAMATTA'},councils=matches,classifications=classifications,records=records,name_resolution=name_resolution,
  source_manifest=json.loads((ROOT/'manifest.json').read_text()))
 path=ROOT/'coverage-candidate.json';path.write_text(json.dumps(report,indent=2,sort_keys=True))
 print(json.dumps(dict(counts=report['counts'],records=len(records),names=len(names),sha256=hashlib.sha256(path.read_bytes()).hexdigest()),indent=2))
 print('Crossing diagnostics:',json.dumps(sorted((e for e in records if e['classification']=='crossing'),key=lambda e:e['outside_fraction'])[:20],indent=2))
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('source_directory',type=Path)
 ROOT=parser.parse_args().source_directory
 build()
