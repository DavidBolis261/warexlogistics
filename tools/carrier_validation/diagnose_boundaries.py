import json
from classify import geometry,COUNCILS,normal
from pathlib import Path
import argparse
parser=argparse.ArgumentParser();parser.add_argument('source_directory',type=Path)
ROOT=parser.parse_args().source_directory
from shapely.ops import unary_union
lgas=json.loads((ROOT/'layer1-all.json').read_text())['features']
localities=json.loads((ROOT/'layer0-all.json').read_text())['features']
selected={normal({'Parramatta':'City of Parramatta'}.get(n,n)) for n in COUNCILS}
region=unary_union([geometry(r) for r in lgas if normal(r['attributes']['LGANAME']) in selected])
others=[]
for r in lgas:
 if normal(r['attributes']['LGANAME']) not in selected:
  try:others.append((r['attributes']['LGANAME'],geometry(r)))
  except ValueError:pass
results=[]
candidate=json.loads((ROOT/'coverage-candidate.json').read_text())
for name in sorted(n for n,s in candidate['classifications'].items() if s=='crossing'):
 f=next(r for r in localities if r['attributes']['SUBURBNAME']==name);g=geometry(f);outside=g.difference(region)
 matches=[]
 for n,area in others:
  if area.intersects(outside):
   fraction=outside.intersection(area).area/g.area
   if fraction>0:matches.append(dict(lga=n,fraction_of_locality=fraction))
 results.append(dict(name=name,outside_fraction=outside.area/g.area,overlaps=matches,category='harbour_administrative_overlap' if matches and all(m['lga']=='UNINCORPORATED - SYDNEY HARBOUR AREA' for m in matches) else 'other_boundary_overlap',tiny_sliver_candidate=outside.area/g.area<0.000001))
(ROOT/'review-diagnostics.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
