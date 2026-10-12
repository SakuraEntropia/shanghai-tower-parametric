import json,sys,math,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import corrections_v11 as v,geometry,crown_pattern_v8 as c,aperture_layout_v10 as a

class CorrectionsV11Tests(unittest.TestCase):
    def test_exactly_two_intact_parent_columns_between_adjacent_holes(self):
        cfg=json.loads((R/'parameters/model_config.json').read_text());cfg['notch_v4']=json.loads((R/'parameters/notch_v4.json').read_text());p=json.loads((R/'parameters/completion.json').read_text())['crown'];a.configure(geometry,cfg,p);st=c.shared_stations(geometry,cfg)
        for face in (1,2,3):
            q=[h for h in p['vent_openings_candidate'] if h['face']==face and h['row']==1]
            for left,right in zip(q,q[1:]):
                ia=next(i for i,s in enumerate(st) if abs(s['s']-left['s_max'])<1e-9);ib=next(i for i,s in enumerate(st) if abs(s['s']-right['s_min'])<1e-9);self.assertEqual(ib-ia,2)
        self.assertTrue(all(g['parent_column_count_including_separators']==31 for g in p['aperture_groups_v10']))
    def test_tiles_have_physical_joint_and_flat_horizontal_proportion(self):
        p=json.loads((R/'parameters/podium_v9.json').read_text());polys=v.tile_panels(p,[[(0,0,0),(5.4,0,0),(5.4,0,1.2),(0,0,1.2)]])
        self.assertEqual(len(polys),12)
        for q in polys:
            width=max(a[0] for a in q)-min(a[0] for a in q);height=max(a[2] for a in q)-min(a[2] for a in q)
            self.assertGreater(width/height,5);self.assertAlmostEqual(width,1.79);self.assertAlmostEqual(height,.29)
    def test_courtyard_area_changes_while_published_trace_is_retained(self):
        p=json.loads((R/'parameters/podium_v9.json').read_text());q=p['courtyard_photo_fit_px'];r=v.courtyard_points(p,q);area=lambda ps:abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(ps,ps[1:]+ps[:1])))/2
        self.assertAlmostEqual(area(r)/area(q),1.62)
    def test_roof_is_really_removed_on_selected_side_only(self):
        p=json.loads((R/'parameters/podium_v9.json').read_text())
        self.assertFalse(v.roof_quadlets(p,.4,.41,.7,.71))
        self.assertTrue(v.roof_quadlets(p,.4,.41,.2,.21))
        self.assertTrue(v.roof_quadlets(p,.1,.11,.7,.71))

if __name__=='__main__':unittest.main()
