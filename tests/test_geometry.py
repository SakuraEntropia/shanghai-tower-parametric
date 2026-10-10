"""Check analytic constraints and evidence-preserving geometry boundaries."""

import copy
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("shanghai_geometry", ROOT / "scripts" / "geometry.py")
geometry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(geometry)


class RecordingBuilder:
    def __init__(self, config):
        self.config = config
        self.records = []
        self.component_results = {}

    def lines(self, name, polylines, collection, radius, material, meta):
        self.records.append(dict(kind="lines", name=name, polylines=polylines, meta=meta))
        return SimpleNamespace(name=name)

    def mesh(self, name, verts, faces, collection, material, meta):
        obj = SimpleNamespace(name=name, hide_render=False, hide_viewport=False)
        self.records.append(dict(kind="mesh", name=name, verts=verts, faces=faces, meta=meta, obj=obj))
        return obj

    def empty(self, name, location, collection, meta):
        self.records.append(dict(kind="empty", name=name, location=location, meta=meta))
        return SimpleNamespace(name=name)


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "parameters" / "model_config.json").read_text())

    def assertXYAlmostEqual(self, a, b, places=9):
        self.assertAlmostEqual(a[0], b[0], places=places)
        self.assertAlmostEqual(a[1], b[1], places=places)

    def test_source_control_reconstruction(self):
        arcs = geometry.profile_segments(self.config)
        self.assertEqual([a["id"] for a in arcs], ["K0", "C2", "K1", "C0", "K2", "C1"])
        self.assertAlmostEqual(arcs[0]["radius"], 19.25810588662182, places=10)
        self.assertAlmostEqual(sum(a["length"] for a in arcs), 289.5356177577849, places=9)
        # Independently recognizable tangent point from the derived source diagram.
        p = geometry._arc_point(arcs[0], arcs[0]["end_deg"])
        self.assertXYAlmostEqual(p, (46.98834265605079, 11.509128360962514))

    def test_all_six_arc_joins_close_and_are_tangent(self):
        arcs = geometry.profile_segments(self.config)
        for left, right in zip(arcs, arcs[1:] + arcs[:1]):
            p = geometry._arc_point(left, left["end_deg"])
            q = geometry._arc_point(right, right["start_deg"])
            self.assertLess(math.dist(p, q), 1e-10)
            self.assertAlmostEqual(math.dist(p, left["center"]), left["radius"], places=10)
            la, ra = math.radians(left["end_deg"]), math.radians(right["start_deg"])
            self.assertXYAlmostEqual((-math.sin(la), math.cos(la)), (-math.sin(ra), math.cos(ra)))

    def test_station_origin_and_full_reference_wrap(self):
        start = geometry.point_at_station(self.config, 0)
        self.assertEqual(start["segment_id"], "C0")
        self.assertXYAlmostEqual(start["xy"], (-40.665, 0))
        perimeter = sum(a["length"] for a in geometry.profile_segments(self.config))
        self.assertXYAlmostEqual(start["xy"], geometry.point_at_station(self.config, perimeter)["xy"])

    def test_grid_has_equal_arc_stations_and_mirrored_groups(self):
        points = geometry.standard_grid(self.config)
        self.assertEqual(len(points), 138)
        perimeter = sum(a["length"] for a in geometry.profile_segments(self.config))
        for i, point in enumerate(points):
            self.assertAlmostEqual(point["s_m"], i * perimeter / 138, places=10)
        self.assertEqual([points[i]["half_index"] for i in range(0, 138, 23)], list(range(6)))
        self.assertEqual(points[0]["group_index"], 0)
        self.assertEqual(points[23]["group_index"], 4)
        self.assertTrue(any(p["excluded_by_notch_uncertainty"] for p in points))
        for point in points:
            self.assertEqual(point["excluded_by_notch_uncertainty"], "K2" in point["span_segment_ids"])

    def test_sampling_override_does_not_inherit_real_group_claims(self):
        points = geometry.standard_grid(self.config, half_count=7)
        self.assertEqual(len(points), 42)
        self.assertTrue(all(point["group_index"] is None for point in points))

    def test_sample_detail_contract_and_no_duplicate_terminal(self):
        plain = geometry.sample_profile(self.config, 288)
        detailed = geometry.sample_profile(self.config, 288, True)
        self.assertEqual(plain, [point["xy"] for point in detailed])
        self.assertEqual(set(detailed[0]), {"xy", "segment_id", "s_m"})
        self.assertNotEqual(plain[0], plain[-1])

    def test_2014_endpoints_and_transform(self):
        self.assertEqual(geometry.curve_state(45, self.config), {"scale": 1.0, "theta_deg": 0.0})
        end = geometry.curve_state(632, self.config)
        self.assertAlmostEqual(end["scale"], 0.55)
        self.assertEqual(end["theta_deg"], 120)
        self.assertXYAlmostEqual(geometry.transform_profile([(10, 0)], 632, self.config)[0], (-2.75, 5.5 * math.sqrt(3) / 2))

    def test_2010_range_is_independent(self):
        name = "gensler_2010_diagnostic"
        end = geometry.curve_state(605, self.config, name)
        self.assertAlmostEqual(end["scale"], 0.5586)
        self.assertEqual(end["theta_deg"], 120)
        with self.assertRaises(ValueError):
            geometry.curve_state(632, self.config, name)

    def test_rejects_every_outside_control_range(self):
        for z in (0, 44.999999, 632.000001, 700, float("nan"), float("inf")):
            with self.subTest(z=z), self.assertRaises(ValueError):
                geometry.curve_state(z, self.config)

    def test_orientation_is_explicit_and_configurable(self):
        changed = copy.deepcopy(self.config)
        changed["orientation"].update(theta0_deg=30, direction=-1)
        self.assertEqual(geometry.curve_state(632, changed)["theta_deg"], -90)
        changed["orientation"]["direction"] = 0
        with self.assertRaises(ValueError):
            geometry.curve_state(45, changed)

    def test_changed_source_parameters_change_analytic_profile(self):
        changed = copy.deepcopy(self.config)
        changed["profile"]["A1_deg"] = 25
        self.assertNotEqual(geometry.profile_segments(changed)[0]["radius"], geometry.profile_segments(self.config)[0]["radius"])
        position_error, tangent_error = geometry._tangency_error(geometry.profile_segments(changed))
        self.assertLess(position_error, 1e-10)
        self.assertLess(tangent_error, 1e-10)

    def test_invalid_geometry_and_sampling_are_rejected(self):
        for count in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                geometry.sample_profile(self.config, count)
        invalid = copy.deepcopy(self.config)
        invalid["profile"]["R1_m"] = 1
        with self.assertRaises(ValueError):
            geometry.profile_segments(invalid)
        with self.assertRaises(ValueError):
            geometry.transform_profile([{"xy": (1, 2)}], 45, self.config)

    def test_scene_keeps_notch_and_crown_unresolved(self):
        ctx = RecordingBuilder(self.config)
        result = geometry.build_envelope(ctx)
        self.assertTrue(result["unknown_notch"])
        self.assertTrue(result["unknown_crown_trim"])
        self.assertFalse(result["asbuilt_verified"])
        self.assertFalse(result["has_flat_cap"])
        self.assertEqual(result["valid_range"], [45, 632])
        surface = next(record for record in ctx.records if record["kind"] == "mesh")
        self.assertTrue(surface["obj"].hide_render)
        self.assertTrue(surface["obj"].hide_viewport)
        self.assertLessEqual(max(v[2] for v in surface["verts"]), 542)
        # Every quad joins two heights: none is a fabricated horizontal cap.
        self.assertTrue(all(len({surface["verts"][i][2] for i in face}) == 2 for face in surface["faces"]))
        top = next(record for record in ctx.records if record["kind"] == "lines" and "OPEN_TOP" in record["name"])
        self.assertEqual(len(top["polylines"]), 5)
        self.assertTrue(all(p[2] == 632 for line in top["polylines"] for p in line))
        self.assertFalse(top["meta"]["closed_profile"])
        self.assertEqual(len([r for r in ctx.records if r["kind"] == "empty"]), 3)


if __name__ == "__main__":
    unittest.main()
