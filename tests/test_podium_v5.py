"""Meaningful podium contracts: closed folded roof and evidence boundaries."""
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('podium_v4',ROOT/'scripts/podium_v4.py')
podium=importlib.util.module_from_spec(spec);spec.loader.exec_module(podium)


class Recorder:
    def __init__(self):self.records=[]
    def mesh(self,name,verts,faces,collection,material,meta):
        self.records.append(dict(name=name,kind='mesh',verts=verts,faces=faces,meta=meta))
        return SimpleNamespace(name=name)
    def lines(self,name,points,collection,radius,material,meta):
        self.records.append(dict(name=name,kind='lines',points=points,meta=meta))
        return SimpleNamespace(name=name)
    def empty(self,name,location,collection,meta):
        self.records.append(dict(name=name,kind='empty',meta=meta))
        return SimpleNamespace(name=name)


class PodiumTests(unittest.TestCase):
    def setUp(self):self.p=json.loads((ROOT/'parameters/podium_v4.json').read_text())
    def test_folded_roof_is_closed_oriented_shell_without_duplicate_join_vertices(self):
        verts,faces,_=podium.roof_mesh(self.p)
        edges=Counter((a,b) for f in faces for a,b in zip(f,f[1:]+f[:1]))
        self.assertTrue(all(edges[(b,a)]==1 and count==1 for (a,b),count in edges.items()))
        self.assertEqual(len(verts),len(set(tuple(round(v,8) for v in point) for point in verts)))
        self.assertAlmostEqual(max(p[2] for p in verts),self.p['roof_high_m'])
    def test_fold_join_height_and_tangent_are_continuous(self):
        v=self.p['roof_back_v_min'];eps=1e-6
        for u in [-.5,-self.p['roof_side_inner_u_left'],self.p['roof_side_inner_u_right'],.5]:
            h=podium.roof_height(self.p,u,v)
            left=(h-podium.roof_height(self.p,u,v-eps))/eps
            right=(podium.roof_height(self.p,u,v+eps)-h)/eps
            self.assertAlmostEqual(left,right,places=3)
    def test_roof_follows_rounded_base_and_facade_has_regular_subdivisions(self):
        p=self.p;x,y=podium.roof_xy(p,.5,-.5)
        ex,ey=podium.xy(p,(p['width_m']/2-p['corner_radius_m'])/p['width_m'],-.5)
        self.assertAlmostEqual(x,ex)
        self.assertAlmostEqual(y,ey)
        points=podium.outline(p)
        self.assertLessEqual(max(math.dist(a,b) for a,b in zip(points,points[1:]+points[:1])),p['facade_module_candidate_m']+1e-9)
    def test_secondary_pavilion_has_real_concavity(self):
        points=podium.satellite_outline(self.p)
        turns=[]
        for a,b,c in zip(points,points[1:]+points[:1],points[2:]+points[:2]):
            cross=(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
            if abs(cross)>1e-8:turns.append(cross)
        self.assertLess(min(turns),0);self.assertGreater(max(turns),0)
    def test_complete_assembly_keeps_uncertainty_and_does_not_hide_glass_behind_front_band(self):
        ctx=Recorder();report=podium.build_podium(ctx,None,None,{'podium_v4':self.p})
        self.assertTrue(all(c['passed'] for c in report['checks']))
        for record in ctx.records:
            self.assertFalse(record['meta']['asbuilt_verified'])
            self.assertEqual(record['meta']['numeric_evidence_level'],'待确认')
            self.assertTrue(record['meta']['source_ids'])
            self.assertTrue(set(record['meta']['source_ids']) <= {'PODIUM_GENS_V4','PODIUM_GENS_GROUND_V6','PODIUM_LINGYUN_BIM_V7','GENSLER_ARCHJOURNAL_V8'})
        body=next(r for r in ctx.records if r['name']=='PODIUM_V6_LIMITED_LOW_FRONT_GLAZING')
        front=self.p['center_xy_m'][1]-self.p['depth_m']/2+self.p['corner_radius_m']
        lo,hi=self.p['front_opaque_band_candidate_z_m']
        for face in body['faces']:
            points=[body['verts'][i] for i in face]
            if sum(p[1] for p in points)/len(points)<=front:
                zlo=min(p[2] for p in points);zhi=max(p[2] for p in points)
                self.assertTrue(zhi<=lo or zlo>=hi)

    def test_actual_mouth_is_horizontal_dominant_not_a_perimeter_glass_cage(self):
        ctx=Recorder();podium.build_podium(ctx,None,None,{'podium_v4':self.p})
        names={r['name'] for r in ctx.records}
        self.assertNotIn('PODIUM_V4_GOLD_CURVED_FASCIA',names)
        self.assertNotIn('PODIUM_V4_FACADE_GRID_DISPLAY',names)
        self.assertNotIn('PODIUM_V5_ROOF_EDGE_COPING',names)
        self.assertNotIn('PODIUM_V5_RETAIL_ENTRANCE_CANOPY',names)
        self.assertNotIn('PODIUM_V5_CONCAVE_PAVILION_MULLIONS',names)
        horizontal=next(r for r in ctx.records if r['name']=='PODIUM_V6_MOUTH_FINE_HORIZONTAL_JOINTS')
        vertical=next(r for r in ctx.records if r['name']=='PODIUM_V6_MOUTH_LIMITED_VERTICAL_DIVISIONS')
        self.assertGreater(len(horizontal['points']),len(vertical['points'])*4)
        mouth=next(r for r in ctx.records if r['name']=='PODIUM_V6_TALL_ARCHED_GLASS_MOUTH')
        self.assertEqual(mouth['meta']['source_ids'],['PODIUM_GENS_GROUND_V6'])
        self.assertTrue(any(len(f)==3 for f in mouth['faces']))
        self.assertTrue(all(len(f)>=3 for f in mouth['faces']))
        for face in mouth['faces']:
            points=[mouth['verts'][i] for i in face]
            self.assertGreater(max(p[2] for p in points)-min(p[2] for p in points),0)
        self.assertGreater(max(p[2] for p in mouth['verts']),self.p['terrace_top_m']+8)

    def test_candidate_slab_ends_no_longer_punch_through_descending_fold(self):
        p=self.p;body=podium.outline(p)
        previous=0
        for z in p['display_slab_levels_m']:
            points=podium.cropped_floor_outline(p,body,z)
            # At front the roll descends toward ground; positive slab edge must
            # retreat as floors rise. Test actual polygon, not configured flags.
            front=[x for x,y in points if abs(y+p['depth_m']/2)<1e-8]
            retreat=max(x for x,y in body if abs(y+p['depth_m']/2)<1e-8)-max(front)
            self.assertGreaterEqual(retreat,previous-1e-8);previous=retreat
        self.assertGreater(previous,3)
        start=p['left_fold_front_v_candidate']
        self.assertAlmostEqual(podium.roof_height(p,-.5,start),p['terrace_top_m']+p['left_end_clearance_candidate_m'])


if __name__=='__main__':unittest.main()
