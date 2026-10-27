import unittest
from shapely.geometry import box,Polygon,MultiPolygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from classify import classify,geometry,resolve_name
class GeometryTests(unittest.TestCase):
 def test_internal_council_crossing_inside_union(self):
  self.assertEqual(classify(box(.5,.2,1.5,.8),unary_union([box(0,0,1,1),box(1,0,2,1)])),'inside')
 def test_boundary_touch_inside_and_external_touch_outside(self):
  self.assertEqual(classify(box(0,0,1,1),box(0,0,1,1)),'inside')
  self.assertEqual(classify(box(1,0,2,1),box(0,0,1,1)),'outside')
 def test_tiny_outside_sliver_is_crossing(self):
  self.assertEqual(classify(box(0,0,1.0000000001,1),box(0,0,1,1)),'crossing')
 def test_multipart_islands_and_holes_preserved(self):
  outer=orient(Polygon([(0,0),(4,0),(4,4),(0,4)],holes=[[(1,1),(2,1),(2,2),(1,2)]]),sign=-1)
  island=orient(box(6,6,7,7),sign=-1)
  record={'geometry':{'rings':[list(outer.exterior.coords),list(outer.interiors[0].coords),list(island.exterior.coords)]}}
  result=geometry(record)
  self.assertEqual(result.area,16)
  self.assertEqual(classify(result,box(0,0,4,4)),'crossing')
  self.assertEqual(classify(box(1.2,1.2,1.8,1.8),result),'outside')
 def test_duplicate_name_requires_every_part_safe(self):
  self.assertEqual(resolve_name([{'classification':'inside'},{'classification':'inside'}]),'inside')
  self.assertEqual(resolve_name([{'classification':'outside'},{'classification':'outside'}]),'outside')
  for statuses in [('inside','outside'),('inside','crossing'),('inside','ambiguous'),('outside','ambiguous')]:
   self.assertEqual(resolve_name([{'classification':s} for s in statuses]),'ambiguous')
 def test_invalid_polygon_is_not_repaired(self):
  with self.assertRaises(ValueError):geometry({'geometry':{'rings':[[(0,0),(1,1),(0,1),(1,0),(0,0)]]}})
if __name__=='__main__':unittest.main()
