"""Regression contracts for shared parent panes and local aperture cutting."""
import json,math,sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import geometry
import crown_pattern_v8 as c
import crown_art_v8 as art
import inner_completion as inner
import site_v8 as site

class SharedCrownTests(unittest.TestCase):
    def setUp(self):
        self.cfg=json.loads((R/'parameters/model_config.json').read_text())
        self.cfg['notch_v4']=json.loads((R/'parameters/notch_v4.json').read_text())
        self.p=json.loads((R/'parameters/completion.json').read_text())['crown']
    def test_crown_columns_are_lower_grid_points_not_a_second_sampling_grid(self):
        grid=geometry.standard_grid(self.cfg,self.cfg['curtain']['half_panel_count'])
        st=c.shared_stations(geometry,self.cfg)
        for s in st:self.assertEqual(tuple(s['xy']),tuple(grid[s['grid_index']]['xy']))
        self.assertEqual(st[0]['grid_index'],26);self.assertEqual(st[-1]['grid_index'],20)
    def test_aperture_edges_do_not_create_additional_global_glass_bands(self):
        levels=c.shared_levels(self.cfg,self.p)
        self.assertNotIn(566,levels);self.assertNotIn(575,levels)
        self.assertTrue(all(abs(b-a-4.5)<1e-8 for a,b in zip(levels,levels[1:])))
        self.assertEqual(levels[0],542);self.assertEqual(levels[-1],632)
    def test_cutting_uses_one_original_parent_pane_and_retains_open_void(self):
        pane=[(0,0),(2,0),(2,4.5),(0,4.5)];hole={'s_min':.5,'s_max':1.5,'z_min_m':1,'z_max_m':4}
        pieces=c.cut_pane(pane,[hole]);area=lambda q:abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(q,q[1:]+q[:1])))/2
        self.assertAlmostEqual(sum(map(area,pieces)),6)
        edges=c.boundary_segments(pane,[hole])
        self.assertTrue(any(abs(a[0]-.5)<1e-8 and abs(b[0]-.5)<1e-8 for a,b in edges))
        self.assertFalse(any(abs(a[0]-1)<1e-8 and abs(b[0]-1)<1e-8 for a,b in edges))
    def test_artist_nominal_bounds_and_519_candidate_tiles(self):
        p=json.loads((R/'parameters/crown_v5.json').read_text());v,f,ids,n=art.sculpture_buffers(p)
        bound=[max(q[i] for q in v)-min(q[i] for q in v) for i in range(3)]
        self.assertEqual(n,519);self.assertEqual(len(set(ids)),519)
        self.assertAlmostEqual(bound[2],7.7);self.assertAlmostEqual(max(bound[:2]),3.89)
    def test_B_first_zone_band_is_open_and_upper_bands_stay(self):
        d=json.loads((R/'parameters/completion.json').read_text())['inner'];zone=d['zones'][3];layout=inner.zone_layout(zone,d['modelling'])
        v,f,bands,modules=inner.zone_panel_mesh(layout,d['modelling']['nominal_band_height_m'])
        self.assertEqual(layout['open_bottom_band_count'],1);self.assertNotIn(0,bands);self.assertIn(1,bands)
        self.assertAlmostEqual(min(q[2] for q in v),zone['z0_m']+4.5)
    def test_site_trace_retains_published_100m_scale(self):
        p=json.loads((R/'parameters/site_v8.json').read_text());a,b=p['scale_bar_px']
        self.assertAlmostEqual(math.dist(site.xy(p,a),site.xy(p,b)),100)
        self.assertLess(math.hypot(*site.xy(p,p['tower_center_px'])),1e-9)
    def test_each_upper_vent_removes_one_parent_column_across_two_bands(self):
        st=c.shared_stations(geometry,self.cfg)
        for hole in self.p['vent_openings_candidate']:
            self.assertTrue(any(abs(a['s']-hole['s_min'])<1e-10 and abs(b['s']-hole['s_max'])<1e-10 for a,b in zip(st,st[1:])))
            self.assertAlmostEqual(hole['z_max_m']-hole['z_min_m'],9)

if __name__=='__main__':unittest.main()
