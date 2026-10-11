"""Actual-aerial crown regression: geometry integrity, no source overclaims."""
import json
import math
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import geometry
import crown_completion as crown
import crown_v5
from floors_v3 import annular_slab, ray_hole_radius


class Recorder:
    def __init__(self,config):self.config=config;self.component_results={};self.records=[]
    def mesh(self,name,verts,faces,collection,material,meta):
        self.records.append({'name':name,'verts':verts,'faces':faces,'meta':meta,'kind':'mesh'})
        return SimpleNamespace(name=name)
    def lines(self,name,paths,collection,radius,material,meta):
        self.records.append({'name':name,'paths':paths,'meta':meta,'kind':'lines'})
        return SimpleNamespace(name=name)
    def box(self,name,center,size,collection,material,meta):
        self.records.append({'name':name,'center':center,'size':size,'meta':meta,'kind':'box'})
        return SimpleNamespace(name=name)
    def empty(self,name,position,collection,meta):
        self.records.append({'name':name,'position':position,'meta':meta,'kind':'empty'})
        return SimpleNamespace(name=name)


class CrownV5Tests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((ROOT/'parameters/model_config.json').read_text())
        self.config['notch_v4']=json.loads((ROOT/'parameters/notch_v4.json').read_text())
        self.candidate=json.loads((ROOT/'parameters/completion.json').read_text())['crown']
        self.p=json.loads((ROOT/'parameters/crown_v5.json').read_text())
        self.assembly=json.loads((ROOT/'parameters/assembly_v3.json').read_text())
    def test_actual_aerial_rim_high_lip_is_endpoint_and_monotone(self):
        heights=[crown.trim_height(i/500,self.candidate) for i in range(501)]
        self.assertEqual(heights[-1],632)
        self.assertEqual(heights[0],610.194)
        self.assertTrue(all(a<=b for a,b in zip(heights,heights[1:])))
        stations=crown.crown_profile_stations(geometry,self.config,20)
        grid=geometry.standard_grid(self.config,self.config['curtain']['half_panel_count'])
        self.assertEqual(stations[0]['xy'],grid[26]['xy'])
        self.assertEqual(stations[-1]['xy'],grid[20]['xy'])
    def test_roof_recess_is_mesh_hole_manifold_and_round_end_stays_open(self):
        hole=crown_v5.roof_slot_polygon(self.p)
        self.assertGreater(ray_hole_radius(hole,math.pi/2),8)
        self.assertGreater(ray_hole_radius(hole,3*math.pi/2),6)
        verts,faces=annular_slab(17,hole,601.099,.25,96)
        edge_count={}
        for face in faces:
            for a,b in zip(face,face[1:]+face[:1]):
                edge=tuple(sorted((a,b)));edge_count[edge]=edge_count.get(edge,0)+1
        self.assertTrue(all(n==2 for n in edge_count.values()))
        self.assertGreater(len(faces),300)
    def test_dense_collector_endpoint_matches_inside_wide_return(self):
        for station in crown.crown_profile_stations(geometry,self.config,20):
            actual=crown_v5.collector_point(geometry,self.config,station,self.candidate,self.p,601.099,1)
            expected=crown_v5.rim_point(geometry,self.config,station,self.candidate,self.p['return_width_fit_m'])
            self.assertLess(math.dist(actual,expected),1e-9)
    def test_entities_evidence_and_no_fabricated_helipad(self):
        ctx=Recorder(self.config)
        report=crown_v5.build_detail(ctx,geometry,self.candidate,self.assembly,self.p)
        self.assertTrue(all(row['passed'] for row in report['checks']))
        self.assertFalse(report['equipment']['helipad_generated'])
        self.assertEqual(report['equipment']['cooling_tower_source_level'],'L128')
        net=next(r for r in ctx.records if r['name']=='CROWN_V5_STEEP_INNER_NET_CONTINUOUS')
        self.assertGreater(len(net['paths']),180)
        for record in ctx.records:
            self.assertFalse(record['meta']['asbuilt_verified'])
        rim=next(r for r in ctx.records if r['name']=='CROWN_V5_WIDE_RIM_HORIZONTAL_RETURN_CANDIDATE')
        for face in rim['faces'][::3]:
            self.assertAlmostEqual(rim['verts'][face[0]][2],rim['verts'][face[3]][2])
            self.assertAlmostEqual(rim['verts'][face[1]][2],rim['verts'][face[2]][2])
        self.assertFalse(any('_HELIPAD_' in r['name'] and r['kind']!='empty' for r in ctx.records))
        equipment=[r for r in ctx.records if r['name'].startswith('CROWN_V5_RIM_APPARATUS_')]
        self.assertTrue(all(r['center'][2]+r['size'][2]/2<632 for r in equipment))
        shelf=next(r for r in ctx.records if r['name']=='CROWN_V5_STEPPED_RIM_APPARATUS_SUPPORT_SHELF')
        self.assertGreater(len(shelf['faces']),300)

    def test_roof_radial_members_do_not_pierce_deck_top(self):
        ctx=Recorder(self.config)
        crown_v5.build_detail(ctx,geometry,self.candidate,self.assembly,self.p)
        struts=next(r for r in ctx.records if r['name']=='CROWN_RADIAL_CORE_STEEL_FRAME_STRUTS_CANDIDATE')
        roof_z=self.assembly['crown']['roof_z_m']
        highest_member_envelope=max(v[2] for path in struts['paths'] for v in path)+self.p['structural_radial_radius_display_m']
        self.assertLess(highest_member_envelope,roof_z-self.p['deck_thickness_fit_m'])


if __name__=='__main__':unittest.main()
