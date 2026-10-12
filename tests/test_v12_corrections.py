import unittest,json,sys,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import corrections_v12 as v,corrections_v11 as old,site_v8 as site

class V12Tests(unittest.TestCase):
    def test_grade_has_true_positive_heights_but_offsite_returns_to_zero(self):
        p=json.loads((R/'parameters/site_v8.json').read_text());samples=[]
        for poly in p['green_polygons_px']:
            ps=[site.xy(p,q) for q in poly];xs=[q[0] for q in ps];ys=[q[1] for q in ps]
            samples.extend(v.grade_at(p,min(xs)+(max(xs)-min(xs))*i/10,min(ys)+(max(ys)-min(ys))*j/10) for i in range(11) for j in range(11))
        self.assertGreater(max(samples),.5);self.assertLessEqual(max(samples),1.5);self.assertEqual(v.grade_at(p,500,500),0)
        for poly in p['green_polygons_px']:
            for q in poly:
                x,y=site.xy(p,q);self.assertAlmostEqual(v.grade_at(p,x,y),0)
    def test_roof_disc_reduced_without_shrinking_nominal_hall_or_oculus(self):
        p=json.loads((R/'parameters/crown_v5.json').read_text());self.assertEqual(p['deck_radius_fit_m'],15.3);self.assertEqual(p['tmd_hall_radius_fit_m'],17.5);self.assertEqual(p['deck_oculus_radius_fit_m'],2)
    def test_stone_blocks_are_independent_with_real_joints(self):
        p=json.loads((R/'parameters/podium_v9.json').read_text());pieces=old.tile_panels(p,[[(0,0,0),(3.6,0,0),(3.6,0,1.2),(0,0,1.2)]])
        self.assertEqual(len(pieces),6)
        area=sum((max(q[0] for q in ps)-min(q[0] for q in ps))*(max(q[2] for q in ps)-min(q[2] for q in ps)) for ps in pieces);self.assertLess(area,3.6*1.2);self.assertGreater(area,4)

if __name__=='__main__':unittest.main()
