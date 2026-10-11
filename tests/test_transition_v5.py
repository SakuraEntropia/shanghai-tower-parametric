"""Regression checks for full V-shaped transition floors and intersecting seams."""
from collections import Counter
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import floors_v3
import geometry
import notch_v4
import transition_v5 as t


def contains(point, polygon):
    x, y = point
    crossings = 0
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if (a[1] > y) != (b[1] > y):
            crossings += a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]) > x
    return bool(crossings % 2)


def crossing(a, b, c, d):
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return cross(a, b, c) * cross(a, b, d) < -1e-12 and cross(c, d, a) * cross(c, d, b) < -1e-12


class TransitionRegressionTest(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT / 'parameters/model_config.json').read_text())
        self.cfg['notch_v4'] = json.loads((ROOT / 'parameters/notch_v4.json').read_text())
        self.completion = json.loads((ROOT / 'parameters/completion.json').read_text())
        self.anchors = json.loads((ROOT / 'parameters/floor_anchors.json').read_text())
        self.assembly = json.loads((ROOT / 'parameters/assembly_v3.json').read_text())
        self.parameters = json.loads((ROOT / 'parameters/transition_v5.json').read_text())
        t.configure(self.cfg, self.completion, self.anchors, self.assembly, self.parameters)

    def test_eight_interfaces_replace_exactly_sixteen_existing_plates(self):
        rows, _ = floors_v3.derive_schedule(self.anchors, self.completion['crown'], floors_v3.DEFAULTS)
        selected = []
        for region in self.cfg['transition_v5']['regions']:
            self.assertIn(region['source_upper_z_m'], [a['z_m'] for a in self.anchors['anchors']])
            self.assertEqual(region['z_top_m'], region['source_upper_z_m'])
            selected.extend(region['candidate_plate_numbers'])
        self.assertEqual(len(set(selected)), 16)
        self.assertEqual(len(rows), 129)
        self.assertNotIn(10, selected)  # Standard conditioned floor keeps its atrium open.

    def test_one_finite_partition_contains_all_transition_cuts(self):
        bands = t.band_schedule(self.cfg)
        self.assertEqual(bands[0]['z_bottom_m'], 0)
        self.assertEqual(bands[-1]['z_top_m'], 542)
        for a, b in zip(bands, bands[1:]):
            self.assertEqual(a['z_top_m'], b['z_bottom_m'])
        self.assertTrue(all(0 < b['z_top_m'] - b['z_bottom_m'] <= 4.5 + 1e-9 for b in bands))
        boundaries = {b['z_top_m'] for b in bands} | {0}
        for region in self.cfg['transition_v5']['regions']:
            for key in ('z_bottom_m', 'z_middle_m', 'z_top_m'):
                self.assertIn(region[key], boundaries)

    def test_full_floor_reaches_outer_wing_keeps_recess_and_core_void(self):
        _, a, apex, b, _, _ = notch_v4.notch_controls(geometry, self.cfg, self.cfg['notch_v4'])
        _, outline = t.outer_reference(geometry, self.cfg)
        hole = floors_v3.core_hole_polygon(self.completion['core'], 2)
        vertices, faces = floors_v3.polygonal_slab(outline, hole, 99, .225)
        edges = Counter(tuple(sorted((i, j))) for face in faces for i, j in zip(face, face[1:] + face[:1]))
        self.assertTrue(all(count == 2 for count in edges.values()))
        self.assertTrue(any(math.hypot(x, y) > 48 for x, y in outline))
        # Candidate B radius37.9m cannot reach this wing. Full triangular slab does.
        wing = (47, 0)
        top_polygons = [[vertices[i][:2] for i in face] for face in faces
                        if all(vertices[i][2] == 99 for i in face)]
        self.assertTrue(any(contains(wing, p) for p in top_polygons))
        self.assertFalse(any(contains((0, 0), p) for p in top_polygons))
        notch_chord_mid = tuple((x + y) / 2 for x, y in zip(a, b))
        self.assertFalse(contains(notch_chord_mid, outline))
        self.assertFalse(any(contains(notch_chord_mid, p) for p in top_polygons))
        inside_apex = (apex[0] * .99, apex[1] * .99)
        self.assertTrue(contains(inside_apex, outline))
        self.assertTrue(any(contains(inside_apex, p) for p in top_polygons))

    def test_crossing_chords_become_two_simple_wedges(self):
        faces = t.step_faces([(-1, -1, 0), (1, 1, 0)], [(-1, 1, 0), (1, -1, 0)], 12)
        self.assertEqual(len(faces), 2)
        self.assertTrue(all(len(face) == 3 for face in faces))
        self.assertTrue(all(p[2] == 12 for face in faces for p in face))

    def test_entire_actual_facade_seam_schedule_has_no_self_crossing_face(self):
        _, points = t.outer_reference(geometry, self.cfg)
        bands = t.band_schedule(self.cfg)
        raw_crossings = 0
        previous = None
        for band in bands:
            row = t.control_profile_at(geometry, self.cfg, points, band['z_top_m'])
            if previous is not None:
                for i in range(len(points)):
                    j = (i + 1) % len(points)
                    raw = [previous[i], previous[j], row[j], row[i]]
                    raw_crossings += crossing(*raw) or crossing(raw[1], raw[2], raw[3], raw[0])
                    for face in t.step_faces((previous[i], previous[j]), (row[i], row[j]), band['z_bottom_m']):
                        if len(face) == 4:
                            self.assertFalse(crossing(*face))
                            self.assertFalse(crossing(face[1], face[2], face[3], face[0]))
                        area = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(face, face[1:] + face[:1])) / 2
                        self.assertGreater(area, 0)
                        self.assertTrue(all(p[2] == band['z_bottom_m'] for p in face))
            previous = row
        self.assertGreater(raw_crossings, 100)  # Real regression: old arbitrary quad layout crossed.


if __name__ == '__main__':
    unittest.main()
