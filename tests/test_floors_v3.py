"""Protect source anchor positions and keep the core opening genuinely empty."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('floors_v3', ROOT / 'scripts/floors_v3.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def point_in_polygon(x, y, polygon):
    crossings = 0
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if (a[1] > y) != (b[1] > y):
            intercept = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            crossings += intercept > x
    return bool(crossings % 2)


class SlabGeometryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = json.loads((ROOT / 'parameters/completion.json').read_text())
        cls.anchors = json.loads((ROOT / 'parameters/floor_anchors.json').read_text())

    def test_every_original_anchor_exact(self):
        rows, comparison = f.derive_schedule(self.anchors, self.candidate['crown'], f.DEFAULTS)
        for anchor in self.anchors['anchors']:
            number = f._floor_number(anchor['source_floor_label'])
            row = next(r for r in rows if r['candidate_number'] == number)
            self.assertEqual(row['z_m'], float(anchor['z_m']))
            self.assertEqual(row['floor_crosswalk_status'], 'unresolved')
        self.assertTrue(comparison)

    def test_all_core_holes_and_solids(self):
        for zone in range(1, 10):
            hole = f.core_hole_polygon(self.candidate['core'], zone)
            vertices, faces = f.annular_slab(23.25, hole, 400, .155, 192)
            edges = Counter(tuple(sorted((a, b))) for face in faces
                            for a, b in zip(face, face[1:] + face[:1]))
            self.assertTrue(all(n == 2 for n in edges.values()))
            for face in faces:
                polygon = [vertices[i][:2] for i in face]
                if all(vertices[i][2] == 400 for i in face):
                    self.assertFalse(point_in_polygon(0, 0, polygon))

    def test_ground_slab_stays_below_zero(self):
        hole = f.core_hole_polygon(self.candidate['core'], 1)
        vertices, _ = f.annular_slab(41.1, hole, 0, .225, 192)
        self.assertEqual(max(v[2] for v in vertices), 0)
        self.assertEqual(min(v[2] for v in vertices), -.225)

    def test_core_outside_slab_rejected(self):
        hole = f.core_hole_polygon(self.candidate['core'], 1)
        with self.assertRaises(ValueError):
            f.annular_slab(10, hole, 100, .155, 192)


if __name__ == '__main__':
    unittest.main()
