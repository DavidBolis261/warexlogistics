"""Review candidate only; does not register or activate real coverage."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'DriverAPI'))
from integrations.draft_rates import LocalityCoveragePolicy,calculate_rate
ROOT=Path(__file__).resolve().parents[1]
class CandidateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data=json.loads((ROOT/'docs/coverage-review/coverage-candidate.json').read_text())
  cls.policy=LocalityCoveragePolicy(cls.data['version'],cls.data['source_reference'],cls.data['classifications'])
 def quote(self,name,side='origin'):
  place=dict(suburb='KATOOMBA',postcode='0000',state='NSW',country='AU')
  body=dict(origin=dict(place),destination=dict(place),parcels=[{'actual_weight_kg':'1'}])
  body[side]['suburb']=name
  return calculate_rate(body,self.policy)
 def test_source_counts_provenance_and_no_postcode_data(self):
  self.assertEqual(len(self.data['records']),4607);self.assertEqual(len(self.data['councils']),33)
  self.assertEqual(self.data['counts'],dict(inside=755,outside=3697,crossing=46,ambiguous=18))
  self.assertEqual(self.data['activation_status'],'disabled_candidate_requires_review')
  for page in self.data['source_manifest']:
   self.assertEqual(len(page['sha256']),64)
   self.assertNotIn('POSTCODE',page['url'].upper())
 def test_duplicate_resolution_admits_no_new_locations(self):
  resolved=self.data['name_resolution']
  self.assertEqual(sum(e['classification']=='outside' for e in resolved),62)
  self.assertEqual(sum(e['classification']=='ambiguous' for e in resolved),17)
  self.assertFalse(any(e['classification']=='inside' for e in resolved))
  for name in ('THE ROCKS','ENMORE','KINGSWOOD','DURAL'):
   self.assertIn('locality_coverage_review_required',self.quote(name)['unresolved_rules'])
 def test_inside_sample_across_approved_outer_councils(self):
  for name in ('KATOOMBA','WINDSOR','PICTON','PARRAMATTA'):
   for side in ('origin','destination'):
    result=self.quote(name,side);self.assertTrue(result['quote_ready'])
    self.assertEqual(result['postcode_validation'],'format_only_not_matched_to_locality')
 def test_real_crossings_and_slivers_stay_blocked(self):
  for name in ('SYDNEY','MANLY','MOUNT WILSON','NORTHBRIDGE','WISEMANS FERRY','BARGO'):
   for side in ('origin','destination'):
    result=self.quote(name,side);self.assertFalse(result['quote_ready'])
    self.assertIn('locality_coverage_review_required',result['unresolved_rules'])
    self.assertNotIn('total_aud',result)
 def test_outside_and_all_ambiguous_names_stay_blocked(self):
  for name in ('GOSFORD','WOLLONGONG'):
   self.assertIn('origin_or_destination_outside_configured_coverage',self.quote(name)['unresolved_rules'])
  for name,status in self.data['classifications'].items():
   if status=='ambiguous':self.assertFalse(self.quote(name)['quote_ready'])
