import json,sys,math,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import raised_end_v14 as r
from podium_v9 import plan_xy
from site_v8 import xy

class RaisedEndTests(unittest.TestCase):
    def setUp(self):self.p=json.loads((R/'parameters/podium_v9.json').read_text())
    def test_soffit_is_above_grade_and_returns_behind_shared_front_edge(self):
        a,b,_=r.frame(self.p)
        self.assertEqual(r.point(self.p,0,0)[:2],a);self.assertEqual(r.point(self.p,1,0)[:2],b)
        pts=[r.point(self.p,i/10,j/20) for i in range(11) for j in range(21)]
        self.assertGreaterEqual(min(q[2] for q in pts),4.2-1e-8)
        self.assertAlmostEqual(r.chart(self.p,*r.point(self.p,.5,1)[:2])[1],12)
    def test_low_floor_cannot_occupy_open_space_but_ground_paving_survives(self):
        q=r.point(self.p,.5,0)
        self.assertTrue(r.floor_allowed(self.p,*q[:2],0));self.assertFalse(r.floor_allowed(self.p,*q[:2],4.2));self.assertFalse(r.base_allowed(self.p,*q[:2]))
        a,b,back=r.frame(self.p);q=r.point(self.p,.5,1)
        self.assertTrue(r.floor_allowed(self.p,q[0]+back[0]*.2,q[1]+back[1]*.2,4.2))
    def test_affine_chart_handles_nonperpendicular_front_and_back_axes(self):
        for s in (.1,.5,.9):
            for v in (.2,.5,.8):
                q=r.point(self.p,s,v);actual,_=r.chart(self.p,*q[:2]);self.assertAlmostEqual(actual,s)
                _,_,back=r.frame(self.p)
                self.assertTrue(r.floor_allowed(self.p,q[0]+back[0]*.01,q[1]+back[1]*.01,q[2]))
                self.assertFalse(r.floor_allowed(self.p,q[0]-back[0]*.3,q[1]-back[1]*.3,q[2]))
    def test_two_published_plan_centers_share_one_model_origin(self):
        p=json.loads((R/'parameters/site_v8.json').read_text())
        self.assertEqual(plan_xy(self.p,self.p['tower_center_px']),(0.,0.))
        self.assertEqual(xy(p,p['tower_center_px']),(0.,0.))
        self.assertEqual(p['rotation_candidate_deg'],self.p['rotation_candidate_deg'])

if __name__=='__main__':unittest.main()
