import unittest,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'scripts'))
from core_completion import wall_regions,contains_wall,union_prism
ROOT=Path(__file__).resolve().parent.parent
C=json.loads((ROOT/'research/core_candidate.json').read_text())
class CoreTests(unittest.TestCase):
 def test_nine_voids(self):
  r=wall_regions(C,1)
  for x in [-9.85,0,9.85]:
   for y in [-10,0,10]:self.assertFalse(contains_wall(r,x,y))
 def test_cross_corners_removed(self):
  r=wall_regions(C,7)
  for x in [-14,14]:
   for y in [-14,14]:self.assertFalse(contains_wall(r,x,y))
  self.assertTrue(contains_wall(r,4.7,12))
 def test_top_three_cells(self):
  r=wall_regions(C,9)
  for y in [-10,0,10]:self.assertFalse(contains_wall(r,0,y))
  self.assertTrue(contains_wall(r,4.7,10))
  self.assertFalse(contains_wall(r,14,10))
 def test_closed_mesh_all_sections(self):
  for z in range(1,10):
   vs,fs=union_prism(wall_regions(C,z),0,3);edges={}
   for f in fs:
    for a,b in zip(f,f[1:]+f[:1]):
     k=tuple(sorted((a,b)));edges[k]=edges.get(k,0)+1
   self.assertTrue(all(v==2 for v in edges.values()))
   self.assertTrue(all(v[2] in [0,3] for v in vs))
if __name__=='__main__':unittest.main()
