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
    def mesh(self,name,verts,faces,collection,material,meta,**kwargs):
        self.records.append({'name':name,'verts':verts,'faces':faces,'meta':meta,'kind':'mesh',**kwargs})
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
    def test_roof_recess_is_rectangular_with_separate_full_round_oculus(self):
        hole=crown_v5.roof_slot_polygon(self.p)
        self.assertEqual(len(hole),4)
        self.assertGreater(ray_hole_radius(hole,math.pi/2),8)
        self.assertGreater(ray_hole_radius(hole,3*math.pi/2),6)
        verts,faces=annular_slab(17,hole,601.099,.25,96)
        edge_count={}
        for face in faces:
            for a,b in zip(face,face[1:]+face[:1]):
                edge=tuple(sorted((a,b)));edge_count[edge]=edge_count.get(edge,0)+1
        self.assertTrue(all(n==2 for n in edge_count.values()))
        self.assertGreater(len(faces),300)
        ctx=Recorder(self.config)
        crown_v5.build_detail(ctx,geometry,self.candidate,self.assembly,self.p)
        well=next(r for r in ctx.records if r['name']=='CROWN_V6_RECTANGULAR_WELL_FLOOR_FULL_ROUND_OCULUS')
        center=(0,self.p['deck_aperture_round_center_y_fit_m'])
        def covered(point):
            for face in well['faces']:
                poly=[well['verts'][i] for i in face]
                if len({round(v[2],6) for v in poly})!=1:continue
                signs=[(b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0]) for a,b in zip(poly,poly[1:]+poly[:1])]
                if all(s>1e-7 for s in signs) or all(s< -1e-7 for s in signs):return True
            return False
        for i in range(12):
            a=i*2*math.pi/12;r=self.p['deck_oculus_radius_fit_m']*.8
            self.assertFalse(covered((center[0]+r*math.cos(a),center[1]+r*math.sin(a))))
    def test_dense_collector_endpoint_matches_inside_wide_return(self):
        for station in crown.crown_profile_stations(geometry,self.config,20):
            actual=crown_v5.collector_point(geometry,self.config,station,self.candidate,self.p,601.099,1)
            expected=crown_v5.rim_point(geometry,self.config,station,self.candidate,self.p['return_width_fit_m'])
            self.assertLess(math.dist(actual,expected),1e-9)
            inner=crown_v5.collector_point(geometry,self.config,station,self.candidate,self.p,601.099,0)
            middle=crown_v5.collector_point(geometry,self.config,station,self.candidate,self.p,601.099,.5)
            self.assertLess(math.dist(middle,tuple((a+b)/2 for a,b in zip(inner,expected))),1e-9)
    def test_entities_evidence_and_no_fabricated_helipad(self):
        ctx=Recorder(self.config)
        report=crown_v5.build_detail(ctx,geometry,self.candidate,self.assembly,self.p)
        self.assertTrue(all(row['passed'] for row in report['checks']))
        self.assertFalse(report['equipment']['helipad_generated'])
        self.assertEqual(report['equipment']['cooling_tower_source_level'],'L120')
        self.assertEqual(report['equipment']['cooling_tower_candidate_base_m'],561)
        self.assertEqual(report['equipment']['cooling_tower_source_conflict_old_L128_m'],592.47)
        net=next(r for r in ctx.records if r['name']=='CROWN_V5_STEEP_INNER_NET_CONTINUOUS')
        self.assertGreater(len(net['paths']),180)
        for record in ctx.records:
            self.assertFalse(record['meta']['asbuilt_verified'])
        rim=next(r for r in ctx.records if r['name']=='CROWN_V5_WIDE_RIM_HORIZONTAL_RETURN_CANDIDATE')
        for face in rim['faces'][::3]:
            self.assertAlmostEqual(rim['verts'][face[0]][2],rim['verts'][face[3]][2])
            self.assertAlmostEqual(rim['verts'][face[1]][2],rim['verts'][face[2]][2])
        helipad=[r for r in ctx.records if '_HELIPAD_' in r['name'] and r['kind']!='empty']
        self.assertEqual(len(helipad),2)
        self.assertTrue(all(r['meta']['default_hidden'] and not r['meta']['installed_location_verified'] for r in helipad))
        equipment=[r for r in ctx.records if r['name'].startswith('CROWN_V5_RIM_APPARATUS_')]
        self.assertTrue(all(r['center'][2]+r['size'][2]/2<632 for r in equipment))
        shelf=next(r for r in ctx.records if r['name']=='CROWN_V5_STEPPED_RIM_APPARATUS_SUPPORT_SHELF')
        self.assertGreater(len(shelf['faces']),300)
        self.assertEqual(report['wind_turbines']['generated_units'],270)
        self.assertEqual(report['tmd_hall']['owner_floor_m'],583.4)
        magnet=next(r for r in ctx.records if r['name']=='TMD_V6_MAGNET_ARRAY_BELOW_SUSPENDED_MASS')
        copper=next(r for r in ctx.records if r['name']=='TMD_V6_COPPER_PLATE_FIXED_TO_LOWER_FLOOR')
        mass=next(r for r in ctx.records if r['name']=='TMD_V6_SUSPENDED_STEEL_MASS_1000_TONNE_CANDIDATE')
        self.assertGreater(magnet['center'][2]-magnet['size'][2]/2,max(v[2] for v in copper['verts']))
        self.assertLess(magnet['center'][2]+magnet['size'][2]/2,min(v[2] for v in mass['verts'])+.001)

    def test_wind_apertures_cut_parent_panes_and_frames_keep_lower_grid(self):
        ctx=Recorder(self.config)
        report=crown.build_crown(ctx,geometry,self.candidate)
        self.assertTrue(report['software_checks_passed'])
        self.assertTrue(report['shared_lower_parent_grid'])
        self.assertFalse(any(crown.wind_aperture_at(r['stations'][0] if r['aperture_uv_chart']=='local_shoulder_0_1' else sum(v[0] for v in poly)/len(poly),sum(v[1] for v in poly)/len(poly),self.candidate)
            for r in report['panel_records'] for poly in r['remaining_uv_polygons']))
        frame=next(r for r in ctx.records if r['name']=='CROWN_FRAME_UNCONFIRMED_GRID')
        self.assertTrue(frame['faces']);self.assertEqual(frame['meta']['shared_lower_band_pitch_m'],self.config['curtain']['nominal_band_pitch_m'])

    def test_roof_radial_members_do_not_pierce_deck_top(self):
        ctx=Recorder(self.config)
        crown_v5.build_detail(ctx,geometry,self.candidate,self.assembly,self.p)
        struts=next(r for r in ctx.records if r['name']=='CROWN_RADIAL_CORE_STEEL_FRAME_STRUTS_CANDIDATE')
        roof_z=self.assembly['crown']['roof_z_m']
        highest_member_envelope=max(v[2] for path in struts['paths'] for v in path)+self.p['structural_radial_radius_display_m']
        self.assertLess(highest_member_envelope,roof_z-self.p['deck_thickness_fit_m'])

    def test_upper_radial_beams_clear_public_hall_but_lower_load_paths_remain(self):
        ctx=Recorder(self.config)
        crown_v5.build_detail(ctx,geometry,self.candidate,self.assembly,self.p)
        struts=next(r for r in ctx.records if r['name']=='CROWN_RADIAL_CORE_STEEL_FRAME_STRUTS_CANDIDATE')
        hall_base=self.p['tmd_hall_floor_owner_m']-self.p['tmd_hall_floor_depth_fit_m']
        upper=[path for path in struts['paths'] if path[0][2]>=hall_base]
        lower=[path for path in struts['paths'] if path[0][2]<hall_base]
        self.assertTrue(upper and lower)
        for path in upper:
            for point in path:
                self.assertGreater(math.hypot(point[0],point[1])-self.p['structural_radial_radius_display_m'],self.p['tmd_hall_radius_fit_m'])
        self.assertTrue(any(math.hypot(path[0][0],path[0][1])<self.p['tmd_hall_radius_fit_m'] for path in lower))


if __name__=='__main__':unittest.main()
