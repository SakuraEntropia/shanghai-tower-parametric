import unittest,json,sys,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import crown_art_v8 as art
import podium_v9 as podium

class GeometryV9Tests(unittest.TestCase):
    def setUp(self):
        self.eye=json.loads((R/'parameters/crown_v5.json').read_text());self.p=json.loads((R/'parameters/podium_v9.json').read_text())
    def test_eye_nested_lower_limbs_keep_direct_arc_without_zero_collapse(self):
        for k in range(5):
            q=art.ribbon_path(self.eye,k,1,1000)
            if k==0:self.assertGreater(q[0][0],1.)
            self.assertTrue(all(b[2]>a[2] for a,b in zip(q,q[1:])))
            # Tangent direction remains continuous at the source-fit join.
            start=0 if k==0 else self.eye['tmd_eye_inner_limb_trim_candidate_fraction']+(k-1)*self.eye['tmd_eye_inner_limb_trim_step_candidate_fraction'];index=round((.23-start)/(1-start)*1000);a,b,c=q[index-1:index+2];v=(b[0]-a[0],b[2]-a[2]);w=(c[0]-b[0],c[2]-b[2]);cos=sum(x*y for x,y in zip(v,w))/math.hypot(*v)/math.hypot(*w)
            self.assertGreater(cos,.999)
    def test_eye_lower_ribbon_width_exceeds_upper_width(self):
        q=art.ribbon_path(self.eye,0,1);v,f=art.ribbon_mesh(q,.3,.035,top_ratio=self.eye['tmd_eye_upper_width_ratio_candidate'])
        self.assertGreater(math.dist(v[0],v[1]),math.dist(v[-4],v[-3])*2)
        self.assertEqual(len(f),4*(len(q)-1)+2)
    def test_p31_scale_bar_is_20m_and_origin_is_documented(self):
        a,b=self.p['ground_scale_bar_px'];self.assertAlmostEqual(math.dist(podium.plan_xy(self.p,a),podium.plan_xy(self.p,b)),20)
        self.assertLess(math.hypot(*podium.plan_xy(self.p,self.p['tower_center_px'])),1e-9)
    def test_multi_arc_section_has_no_sine_mother_and_nonuniform_radii(self):
        pts=podium.arc_section(self.p,240);self.assertEqual(len({a['radius_m'] for a in self.p['section_arc_chain_candidate']}),3)
        self.assertAlmostEqual(max(q[1] for q in pts),37)
        for join in (240,480):
            a,b,c=pts[join-1:join+2];v=(b[0]-a[0],b[1]-a[1]);w=(c[0]-b[0],c[1]-b[1]);cos=sum(x*y for x,y in zip(v,w))/math.hypot(*v)/math.hypot(*w)
            self.assertGreater(cos,.9999)
    def test_candidate_3d_sweep_changes_section_and_path(self):
        a,b,c=[podium.sweep_point(self.p,t,.45) for t in (0,.5,1)]
        self.assertGreater(math.dist(a,c),80)
        self.assertGreater(abs(b[0]-(a[0]+c[0])/2),2)
    def test_local_roof_cut_preserves_hole_in_actual_plane(self):
        poly=[(0,0,0),(4,0,1),(4,4,3),(0,4,2)];hole=[(1,1),(3,1),(3,3),(1,3)]
        for p in podium._cut3d(poly,[hole]):
            for x,y,z in p:self.assertAlmostEqual(z,.25*x+.5*y)

if __name__=='__main__':unittest.main()
