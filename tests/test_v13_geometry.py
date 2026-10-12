import json,sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from corrections_v13 import glass_fragments,frame_fragments,outside_intervals,roof_quadlets,side_openings

class V13GeometryTests(unittest.TestCase):
    def test_slit_is_real_void_and_retains_both_rectangles(self):
        quad=[(2,3,90),(5,7,90),(5,7,100),(2,3,100)]
        holes=[{'z_min_m':94.7,'z_max_m':95.3}]
        pieces=glass_fragments(quad,holes)
        self.assertEqual(len(pieces),2)
        area=sum(5*(max(p[2] for p in q)-min(p[2] for p in q)) for q in pieces)
        self.assertAlmostEqual(area,47)
        for q in pieces:
            self.assertEqual([v[:2] for v in q],[v[:2] for v in quad])
            self.assertTrue(max(v[2] for v in q)<=94.7 or min(v[2] for v in q)>=95.3)
        frames=frame_fragments((2,3,90),(2,3,100),holes,.03)
        self.assertEqual(len(frames),2)
        self.assertAlmostEqual(frames[0][1][2],94.67)
        self.assertAlmostEqual(frames[1][0][2],95.33)
        self.assertEqual(frame_fragments((2,3,95),(5,7,95),holes,.03),[])
    def test_no_floor_notch_parameter_and_separate_end_controls(self):
        p=json.loads((R/'parameters/transition_v5.json').read_text())
        self.assertNotIn('interlayer_notch_v11',p)
        p=json.loads((R/'parameters/podium_v9.json').read_text())
        self.assertEqual(p['open_end_v13']['end'],0)
        self.assertNotIn('side_v12',p)
        holes=side_openings(p);self.assertEqual(len(holes),4)
        self.assertGreater(holes[0]['s_max']-holes[0]['s_min'],.5)
        self.assertLess(holes[1]['s_max'],holes[0]['s_min'])
    def test_roof_trim_only_replaces_external_patch(self):
        p=json.loads((R/'parameters/podium_v9.json').read_text())
        self.assertEqual(roof_quadlets(p,.4,.41,.8,.81),[])
        self.assertTrue(roof_quadlets(p,.4,.41,.2,.21))
        self.assertTrue(roof_quadlets(p,.02,.03,.8,.81))
    def test_aperture_containing_or_crossing_parent_removes_correct_extent(self):
        self.assertEqual(outside_intervals(1,2,[{'z_min_m':0,'z_max_m':3}]),[])
        self.assertEqual(outside_intervals(1,5,[{'z_min_m':0,'z_max_m':2},{'z_min_m':4,'z_max_m':9}]),[(2,4)])

if __name__=='__main__':unittest.main()
