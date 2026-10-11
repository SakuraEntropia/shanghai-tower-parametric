"""Regression checks of aperture topology and near-identical station input."""
import json,sys,math,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import crown_art_v7 as art
import crown_completion as crown
import geometry

class RegressionTests(unittest.TestCase):
    def test_near_identical_added_stations_do_not_create_zero_width_crown_cells(self):
        cfg=json.loads((R/'parameters/model_config.json').read_text())
        stations=crown.open_profile_stations(geometry,cfg,160,[.165,.16500000000000003,.50,.5])
        self.assertTrue(all(math.dist(a['xy'],b['xy'])>1e-8 for a,b in zip(stations,stations[1:])))
    def test_canopy_backing_and_flat_blades_both_have_actual_capsule_voids(self):
        p=json.loads((R/'parameters/crown_v5.json').read_text())
        # Hole is removed independently from both layers. Reduce tessellation
        # only for this topology check; retain the actual six slot parameters.
        p['tmd_canopy_rib_count_display']=36
        def inside(poly,x,y):
            return all((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0])>=-1e-10 for a,b in zip(poly,poly[1:]+poly[:1]))
        for lamella in (False,True):
            polys,holes=art.canopy_polygons(p,lamella)
            for hole in holes[:6]:
                x,y=[sum(v[i] for v in hole)/len(hole) for i in range(2)]
                self.assertFalse(any(inside(q,x,y) for q in polys))
    def test_sculpture_uses_open_crossed_flat_ended_blades_with_outer_flared_feet(self):
        p=json.loads((R/'parameters/crown_v5.json').read_text());path=art.ribbon_path(p,0,1)
        self.assertGreater(path[0][0],0);self.assertGreater(path[-1][0],0)
        self.assertLess(min(v[0] for v in path),-p['tmd_eye_width_fit_m']*.4)
        self.assertGreater(math.dist(path[0],path[-1]),6)
        v,f=art.ribbon_mesh(path,.32,.42,(0,-4),583.4)
        edges={}
        for face in f:
            for a,b in zip(face,face[1:]+face[:1]):
                key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1
        self.assertTrue(all(n==2 for n in edges.values()))

if __name__=='__main__':unittest.main()
