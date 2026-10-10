"""Crown geometry contract: open topology, clipping and evidence boundaries."""
import copy
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value
geometry, crown = module('geometry'), module('crown_completion')


class Recorder:
    def __init__(self, config):
        self.config, self.component_results, self.records = config, {}, []
    def mesh(self, name, verts, faces, collection, material, meta):
        self.records.append(dict(kind='mesh', verts=verts, faces=faces, meta=meta))
        return SimpleNamespace(name=name)
    def lines(self, name, polylines, collection, radius, material, meta):
        self.records.append(dict(kind='lines', meta=meta, radius=radius))
        return SimpleNamespace(name=name)
    def empty(self, name, location, collection, meta):
        self.records.append(dict(kind='empty', meta=meta))
        return SimpleNamespace(name=name)


class CrownTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT/'parameters/model_config.json').read_text())
        self.candidate = json.loads((ROOT/'research/crown_candidate.json').read_text())
    def test_trim_matches_published_anchor_fit_and_minimum(self):
        controls = self.candidate['implementation_candidate']['station_height_m']
        for s, z in controls:
            self.assertAlmostEqual(crown.trim_height(s, self.candidate), z)
        values = [crown.trim_height(i/1000, self.candidate) for i in range(1001)]
        self.assertAlmostEqual(min(values), controls[1][1])
        self.assertAlmostEqual(max(values), 632)
        self.assertTrue(all(a>=b for a,b in zip(values[:500],values[1:501])))
        self.assertTrue(all(a<=b for a,b in zip(values[500:],values[501:])))
    def test_open_rim_cannot_wrap_or_use_nonfinite_parameters(self):
        for s in [-.1, 1.01, math.inf, math.nan, True]:
            with self.assertRaises(ValueError): crown.trim_height(s, self.candidate)
        bad = copy.deepcopy(self.candidate)
        bad['implementation_candidate']['station_height_m'][1][1] = 700
        with self.assertRaises(ValueError): crown.trim_height(.5, bad)
    def test_open_arc_order_and_source_endpoint_identity(self):
        points = crown.open_profile_stations(geometry,self.config,20,(.5,))
        self.assertEqual(points[0]['segment_id'], 'C1')
        self.assertEqual(points[-1]['segment_id'], 'C0')
        self.assertTrue(all(p['segment_id']!='K2' for p in points))
        self.assertEqual(points[0]['s'],0)
        self.assertEqual(points[-1]['s'],1)
        self.assertGreater(math.dist(points[0]['xy'],points[-1]['xy']),1)
        self.assertIn(.5,[p['s'] for p in points])
        self.assertTrue(all(a['s']<b['s'] for a,b in zip(points,points[1:])))
    def test_upper_triangle_intersection_follows_trim_line(self):
        # Zrim rises from9 to11 while this band starts at10: half of the chord remains.
        poly = crown._clipped_vertical_chord((0,0,0),(2,0,0),10,12,9,11)
        self.assertEqual(poly,[(1,0,10),(2,0,10),(2,0,11)])
        self.assertEqual(crown._clipped_vertical_chord((0,0,0),(2,0,0),12,14,9,11),[])
    def test_actual_generated_surfaces_remain_open_vertical_and_evidence_tagged(self):
        ctx = Recorder(self.config)
        report = crown.build_crown(ctx,geometry,self.candidate)
        self.assertTrue(report['software_checks_passed'])
        mesh = next(r for r in ctx.records if r['kind']=='mesh')
        self.assertEqual(max(p[2] for p in mesh['verts']),632)
        self.assertEqual(min(p[2] for p in mesh['verts']),542)
        self.assertFalse(report['top_cap_present'])
        self.assertTrue(any(len(f)==3 for f in mesh['faces']))
        for record in ctx.records:
            self.assertFalse(record['meta']['asbuilt_verified'])
            self.assertEqual(record['meta']['station_mapping_evidence'],'待确认')
            self.assertFalse(record['meta']['fabrication_pattern_verified'])
        self.assertEqual(mesh['meta']['geometry_role'],'crown_candidate_panel')
        self.assertEqual(sum(r['kind']=='empty' for r in ctx.records),5)
    def test_rejects_inconsistent_base_and_display_pitch(self):
        for update in [{'base_z_m':620},{'band_pitch_display_m':0},
                       {'frame_radius_display_m':-1}, {'horizontal_sample_count_display':2}]:
            with self.assertRaises(ValueError):
                crown.build_crown(Recorder(self.config),geometry,{**self.candidate,**update})


if __name__ == '__main__': unittest.main()
