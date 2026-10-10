"""Regression checks for physical mistakes: twisting B and fabricated floor fits."""
import importlib.util
import math
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'inner_completion.py'
spec = importlib.util.spec_from_file_location('inner_completion', MODULE)
inner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inner)


class InnerGeometryTest(unittest.TestCase):
    def setUp(self):
        self.options = {'nominal_band_height_m': 4.5, 'vertical_module_m': 1.0,
                        'entity_start_m': 45, 'entity_stop_m': 542}

    def test_zone_clipping_preserves_residual(self):
        result = inner.zone_layout({'radius_m': 35.3, 'z0_m': 99, 'z1_m': 173.7}, self.options)
        self.assertEqual(result['bands'], 16)
        self.assertAlmostEqual(result['last_band_top_m'], 171)
        self.assertAlmostEqual(result['unmodelled_residual_m'], 2.7)

    def test_actual_panels_are_concentric_and_untwisted(self):
        layout = inner.zone_layout({'radius_m': 23.25, 'z0_m': 465.4, 'z1_m': 542}, self.options)
        verts, faces, bands, modules = inner.zone_panel_mesh(layout, 4.5, azimuth_deg=17)
        for face in faces:
            p = [verts[i] for i in face]
            self.assertEqual(p[0][:2], p[3][:2])
            self.assertEqual(p[1][:2], p[2][:2])
            self.assertAlmostEqual(p[2][2] - p[1][2], 4.5)
            for v in p:
                self.assertAlmostEqual(math.hypot(v[0], v[1]), 23.25)
        self.assertEqual(len(faces), layout['bands'] * layout['facets'])

    def test_equal_circumferential_chords_within_a_zone(self):
        pts = inner.circle_points(30.1, 239.4, 189)
        lengths = [math.dist(p, pts[(i + 1) % len(pts)]) for i, p in enumerate(pts)]
        self.assertLess(max(lengths) - min(lengths), 1e-10)
        self.assertAlmostEqual(sum(lengths), 2 * 189 * 30.1 * math.sin(math.pi / 189))

    def test_invalid_input_rejected(self):
        for radius in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                inner.zone_layout({'radius_m': radius, 'z0_m': 99, 'z1_m': 173.7}, self.options)


if __name__ == '__main__':
    unittest.main()
