import json,math,sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import aperture_layout_v10 as apertures,geometry,crown_pattern_v8 as crown,crown_completion
import podium_v9 as podium,site_details_v9 as site
from test_crown_v5 import Recorder

class CorrectionsV10Tests(unittest.TestCase):
    def setUp(self):
        self.cfg=json.loads((R/'parameters/model_config.json').read_text())
        self.cfg['notch_v4']=json.loads((R/'parameters/notch_v4.json').read_text())
        self.p=json.loads((R/'parameters/completion.json').read_text())['crown']
        apertures.configure(geometry,self.cfg,self.p)
    def test_three_distinct_faces_have_22_22_33_separated_vents(self):
        holes=self.p['vent_openings_candidate'];self.assertEqual(len(holes),77)
        self.assertEqual([sum(h['face']==i for h in holes) for i in (1,2,3)],[22,22,33])
        for face in (1,2,3):
            row=[h for h in holes if h['face']==face and h['row']==1]
            self.assertEqual(len(row),11)
            self.assertTrue(all(a['s_max']<b['s_min'] for a,b in zip(row,row[1:])))
        for h in holes:self.assertLess(h['z_max_m'],min(crown_completion.trim_height(h[k],self.p) for k in ('s_min','s_max')))
    def test_wind_bay_width_equals_group_envelope_and_spans_three_parent_bands(self):
        for g,w in zip(self.p['aperture_groups_v10'],self.p['wind_openings_candidate']):
            self.assertEqual((g['s_min'],g['s_max']),(w['s_min'],w['s_max']))
            self.assertAlmostEqual(w['z_max_m']-w['z_min_m'],3*self.cfg['curtain']['nominal_band_pitch_m'])
    def test_all_80_apertures_actually_cut_parent_geometry(self):
        report=crown.build(Recorder(self.cfg),geometry,self.p)
        self.assertEqual(len(report['aperture_audit_v10']),80)
        self.assertTrue(all(r['passed'] for r in report['aperture_audit_v10']))
    def test_white_entry_is_cut_with_recess_and_glass_only_above_white(self):
        p=json.loads((R/'parameters/podium_v9.json').read_text())
        end=p['entrance_v10']['target_arch_end'];poly=[podium.sweep_point(p,end,i/160) for i in range(161)];white,upper,doors,returns=podium.arch_entry_panels(p,end,poly)
        self.assertTrue(white and upper and doors and returns)
        self.assertTrue(all(min(q[2] for q in poly)>=10.5 for poly in upper))
        self.assertAlmostEqual(max(q[2] for piece in doors for q in piece),4.2)
        self.assertEqual(len(returns),3)
        self.assertGreater(math.dist(poly[0][:2],poly[-1][:2]),math.dist(podium.sweep_point(p,1,0)[:2],podium.sweep_point(p,1,1)[:2]))
        for piece in white:
            mid=tuple(sum(q[k] for q in piece)/len(piece) for k in range(3))
            a,b=poly[0],poly[-1];d=math.dist(a[:2],b[:2]);u=((mid[0]-a[0])*(b[0]-a[0])+(mid[1]-a[1])*(b[1]-a[1]))/(d*d)
            self.assertFalse(.18+1e-7<u<.82-1e-7 and mid[2]<4.2-1e-7)
    def test_candidate_road_curve_preserves_endpoints_and_has_no_reversals(self):
        q=[(0,0),(30,0),(50,25)];p=site.smooth_route(q,18)
        self.assertEqual(p[0],q[0]);self.assertEqual(p[-1],q[-1])
        self.assertTrue(all(b[0]>a[0] and b[1]>=a[1] for a,b in zip(p,p[1:])))
        self.assertGreater(len(p),10);self.assertTrue(any(x<30 and y>0 for x,y in p))

if __name__=='__main__':unittest.main()
