import json, math, sys, unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import geometry, raised_end_v14 as end
from podium_v9 import plan_xy
from corrections_v11 import courtyard_points
from transition_v5 import outer_reference, control_profile_at

class PodiumRelationTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads((R/'parameters/podium_v9.json').read_text())
        self.cfg=json.loads((R/'parameters/model_config.json').read_text())
        self.cfg['notch_v4']=json.loads((R/'parameters/notch_v4.json').read_text())

    def test_garden_faces_convex_corner_instead_of_reentrant_v(self):
        court=[plan_xy(self.p,q) for q in courtyard_points(self.p,self.p['courtyard_photo_fit_px'])]
        center=tuple(sum(q[k] for q in court)/len(court) for k in (0,1))
        angle=math.degrees(math.atan2(center[1],center[0]))
        _,base=outer_reference(geometry,self.cfg)
        profiles=control_profile_at(geometry,self.cfg,[(1,0),(-.5,math.sqrt(3)/2),(-.5,-math.sqrt(3)/2)],22)
        angles=[math.degrees(math.atan2(q[1],q[0])) for q in profiles]
        delta=lambda a,b:abs((a-b+180)%360-180)
        self.assertLess(min(delta(angle,q) for q in angles[:2]),18)
        self.assertGreater(delta(angle,angles[2]),90)

    def test_rising_end_is_asymmetric_and_remains_clear_of_grade(self):
        self.assertGreater(end.point(self.p,0,1)[2]-end.point(self.p,1,1)[2],5)
        self.assertGreaterEqual(min(end.point(self.p,i/20,j/40)[2] for i in range(21) for j in range(41)),4.2-1e-8)

    def test_bowed_front_is_shared_by_garden_and_return(self):
        a,b,back=end.frame(self.p);q=end.point(self.p,.5,0)
        self.assertGreater(sum(((a[k]+b[k])/2-q[k])*back[k] for k in (0,1)),3)
        points=[plan_xy(self.p,v) for v in courtyard_points(self.p,self.p['courtyard_photo_fit_px'])]
        self.assertLess(min(math.dist(q[:2],v) for v in points),1e-7)

    def test_each_transition_storey_has_its_own_midheight_slit(self):
        from corrections_v13 import ring_specs
        p=json.loads((R/'parameters/transition_v5.json').read_text())
        p['regions']=[{'id':'TEST','z_bottom_m':90,'z_middle_m':95,'z_top_m':102}]
        holes=ring_specs({'transition_v5':p})
        self.assertEqual(len(holes),2)
        self.assertEqual([(q['z_min_m']+q['z_max_m'])/2 for q in holes],[92.5,98.5])
        self.assertTrue(all(q['z_max_m']<95 or q['z_min_m']>95 for q in holes))

    def test_candidate_ground_cladding_zones_rotate_with_the_plan(self):
        from podium_v9 import local_ground_opaque_band
        original={**self.p,'rotation_candidate_deg':90}
        for q in ((300,400),(300,200),(930,350)):
            self.assertEqual(local_ground_opaque_band(self.p,plan_xy(self.p,q)),
                             local_ground_opaque_band(original,plan_xy(original,q)))

if __name__=='__main__':unittest.main()
