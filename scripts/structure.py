"""Evidence-limited structural controls and independent dimension specimens.

There is deliberately no completed floor schedule, column trajectory, structural
node, or curtain-wall hanging-point array in this module.  Published dimensions
and the placement of a specimen are separate pieces of evidence.  High-core
polygons are display-only topology seeds, not measured building sections.
"""
from collections import Counter
from math import cos, sin, pi, sqrt, isclose


# These are presentation choices, not architectural dimensions. Architectural
# specifications are obtained through ctx.param; placement choices use config.
_DISPLAY = {
    "circle_segments": 64,
    "wall_coupon_length_m": 3.0,
    "wall_coupon_height_m": 3.0,
    "coupon_gap_m": 2.0,
    "label_offset_m": 2.0,
}


def _meta(source_ids, evidence_level, role, formula, uncertainty, **extra):
    result = {
        "source_ids": list(source_ids),
        "evidence_level": evidence_level,
        "geometry_role": role,
        "formula": formula,
        "uncertainty": uncertainty,
        "asbuilt_verified": False,
    }
    result.update(extra)
    return result


def _parameter_meta(parameter, role, formula=None, uncertainty=None, **extra):
    return _meta(
        parameter["source_ids"], parameter["evidence_level"], role,
        parameter["formula_and_assumptions"] if formula is None else formula,
        parameter["uncertainty"] if uncertainty is None else uncertainty,
        source_locator=parameter["source_locator"],
        source_scope=parameter.get("source_scope", "Published design"),
        **extra,
    )


def _closed(points):
    return points + [points[0]]


def _prism_lines(plan, lower, upper):
    lower_loop = [(x, y, lower) for x, y in plan]
    upper_loop = [(x, y, upper) for x, y in plan]
    return [_closed(lower_loop), _closed(upper_loop)] + [
        [a, b] for a, b in zip(lower_loop, upper_loop)
    ]


def _subtract(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def _unit(vector):
    length = sqrt(sum(v*v for v in vector))
    if length <= 0:
        raise ValueError("A specimen axis needs two different endpoints")
    return tuple(v / length for v in vector)


def _circular_mesh(start, end, diameter, wall_thickness=None):
    """Closed ideal cylindrical specimen, with an actual bore for tubes."""
    if diameter <= 0:
        raise ValueError("Specimen outside diameter must be positive")
    if wall_thickness is not None and not (0 < 2*wall_thickness < diameter):
        raise ValueError("Tube wall thickness must leave a positive bore")
    axis = _unit(_subtract(end, start))
    seed = (0, 0, 1) if abs(axis[2]) < 0.9 else (1, 0, 0)
    e1 = _unit(_cross(axis, seed))
    e2 = _cross(axis, e1)
    count = _DISPLAY["circle_segments"]

    def loop(center, radius):
        return [tuple(center[k] + radius*(cos(2*pi*i/count)*e1[k]
                                         + sin(2*pi*i/count)*e2[k])
                      for k in range(3)) for i in range(count)]

    verts = loop(start, diameter/2) + loop(end, diameter/2)
    faces = []
    for i in range(count):
        j = (i + 1) % count
        faces.append((i, j, count+j, count+i))
    if wall_thickness is None:
        faces.extend((tuple(reversed(range(count))),
                      tuple(range(count, 2*count))))
    else:
        inside_radius = diameter/2 - wall_thickness
        verts.extend(loop(start, inside_radius) + loop(end, inside_radius))
        for i in range(count):
            j = (i + 1) % count
            faces.extend(((2*count+i, 3*count+i, 3*count+j, 2*count+j),
                          (j, i, 2*count+i, 2*count+j),
                          (count+i, count+j, 3*count+j, 3*count+i)))
    # Opposite vertices measure the model itself, rather than echoing inputs.
    outside = sqrt(sum(v*v for v in _subtract(verts[0], verts[count//2])))
    inside = None
    if wall_thickness is not None:
        inside = sqrt(sum(v*v for v in _subtract(
            verts[2*count], verts[2*count + count//2])))
    return verts, faces, outside, inside


def build_structure(ctx, geometry_module, anchors):
    """Build controls/specimens using the approved SceneBuilder interface.

    geometry_module is reserved by the shared interface.  No unknown core or
    floor profile is borrowed from the external curtain-wall control curve.
    """
    del geometry_module
    cfg = ctx.config["structure"]
    components = ctx.config["components"]
    display = ctx.config["display"]
    guide_radius = display["guide_radius_m"]
    control_radius = display["control_radius_m"]
    label_size = display["label_size_m"]
    objects = []
    measured = {}
    counts = Counter()
    detail_vertices = []
    unknown = [
        "Core-to-WP1 offset, actual north and common elevation datum unresolved",
        "Core wall/partition/opening coordinates and exact transition floors missing",
        "High-core chamfer dimensions, arm width and top-section limits missing",
        "Complete floor schedule, source-floor crosswalk and slab edges missing",
        "Column axes/sections, belt/outrigger paths and connection nodes missing",
        "CWSS hanging points, radial-member locations and actual nodes missing",
        "Podium plan boundary, roof elevations and tower interface missing",
    ]

    def add(obj):
        objects.append(obj)
        return obj

    width = float(cfg["core_width_m"])
    reference_width = float(ctx.param("core_low_width")["value"])
    boundaries = [float(z) for z in cfg["zone_reference_boundaries_m"]]
    top = float(cfg["core_display_top_m"])
    if width <= 0 or len(boundaries) != 9:
        raise ValueError("Core control needs a positive width and nine reference boundaries")
    if any(b <= a for a, b in zip(boundaries, boundaries[1:])) or top <= boundaries[-1]:
        raise ValueError("Core display reference heights must increase strictly")
    half = width/2
    square = [(-half, -half), (half, -half), (half, half), (-half, half)]
    common_core_uncertainty = (
        "Outer width is a published design dimension. Local center is assumed; "
        "S13 strengthening-floor references are display divisions, not proven "
        "core transition floors. Solid volume is not concrete-wall geometry."
    )
    if not isclose(width, reference_width, abs_tol=1e-9):
        common_core_uncertainty += " Config width overrides the published 30 m value."

    if components.get("core", False):
        for index in range(4):
            lower, upper = boundaries[index:index+2]
            meta = _meta(
                ["S13", "B14_STRUCT"], "推导值", "core_outer_control_volume_not_walls",
                "30m published outer extent; placement at local origin; display "
                "vertical bounds from S13 Fig1b; no wall, opening or room geometry",
                common_core_uncertainty,
                source_locator="B14_STRUCT p34; S13 PDF p6 Fig1b, p7–8 Fig3",
                source_phase="2013 monitoring references + 2014 structural design",
                source_parameter_evidence="已证实",
                zone=f"Z{index+1}", placeholder=True,
                center_placement_evidence="待确认",
                exact_transition_evidence="待确认",
            )
            volume = add(ctx.box(
                f"CORE_Z{index+1:02d}_30M_CONTROL_NOT_WALLS",
                (0, 0, (lower+upper)/2), (width, width, upper-lower),
                "10_CORE_CONTROLS", "core", meta))
            add(ctx.lines(f"CORE_Z{index+1:02d}_OUTER_DESIGN_GUIDE",
                          _prism_lines(square, lower, upper), "10_CORE_CONTROLS",
                          control_radius, "derived", meta))
            # Indexes intentionally have no invented room coordinates.
            for cell in range(9):
                add(ctx.empty(
                    f"CORE_Z{index+1:02d}_CELL_{cell+1:02d}_WALLS_UNRESOLVED",
                    (0, 0, (lower+upper)/2), "11_CORE_PARTITION_INTERFACES",
                    _meta(["S13"], "待确认", "core_partition_interface_no_walls",
                          "Nine-cell topology is published; all cell locations unresolved",
                          "No equal 10m rooms, wall centerlines or openings inferred",
                          cell_id=cell+1, zone=f"Z{index+1}", placeholder=True)))
            counts["low_core_control_zones"] += 1
            if index == 0:
                xs = [v.co[0] for v in volume.data.vertices]
                ys = [v.co[1] for v in volume.data.vertices]
                measured["core_control_width_x_m"] = max(xs)-min(xs)
                measured["core_control_width_y_m"] = max(ys)-min(ys)

        fraction = float(cfg["core_topology_display_arm_fraction"])
        if not (0 < fraction < 1):
            raise ValueError("Display-only core arm fraction must be between zero and one")
        arm_half = half*fraction
        chamfer = [(-half, -arm_half), (-arm_half, -half), (arm_half, -half),
                   (half, -arm_half), (half, arm_half), (arm_half, half),
                   (-arm_half, half), (-half, arm_half)]
        cross = [(-arm_half, -half), (arm_half, -half), (arm_half, -arm_half),
                 (half, -arm_half), (half, arm_half), (arm_half, arm_half),
                 (arm_half, half), (-arm_half, half), (-arm_half, arm_half),
                 (-half, arm_half), (-half, -arm_half), (-arm_half, -arm_half)]
        rectangle = [(-arm_half, -half), (arm_half, -half),
                     (arm_half, half), (-arm_half, half)]
        for zone in range(5, 10):
            lower = boundaries[zone-1]
            upper = boundaries[zone] if zone < 9 else top
            plan = chamfer if zone < 7 else cross if zone < 9 else rectangle
            topology = "CUT_CORNERS" if zone < 7 else "FIVE_CELL_CROSS" if zone < 9 else "THREE_CELL_RECTANGLE"
            meta = _meta(
                ["S13", "B14_STRUCT"], "待确认", "high_core_topology_placeholder",
                f"Display seed only: outer carrier width={width}m; arm fraction "
                f"={fraction}; height limits are diagram grouping references",
                "Only the topology is published. Chamfer/arm coordinates, section "
                "orientation and exact vertical extent are unverified. Top at "
                "F124 573.90m is a display limit, not the real core top.",
                source_locator="S13 PDF p8 Fig3a–e; B14_STRUCT p34",
                topology=topology, zone=f"Z{zone}", placeholder=True,
                source_parameter_evidence="已证实（仅拓扑）",
                display_arm_fraction=fraction,
            )
            add(ctx.lines(f"CORE_Z{zone:02d}_{topology}_UNRESOLVED",
                          _prism_lines(plan, lower, upper), "12_CORE_TOPOLOGY_UNRESOLVED",
                          control_radius, "unknown", meta))
            add(ctx.empty(f"CORE_Z{zone:02d}_REAL_SECTION_INTERFACE", (0, 0, lower),
                          "12_CORE_TOPOLOGY_UNRESOLVED", meta))
            counts["high_core_topology_placeholders"] += 1
        add(ctx.label("CORE_EVIDENCE_LABEL", "30 m CORE CONTROL / HIGH SECTIONS UNRESOLVED",
                      (half+_DISPLAY["label_offset_m"], 0, boundaries[4]),
                      size=label_size/2, meta=_meta(
                          ["S13", "B14_STRUCT"], "待确认", "annotation",
                          "Research-model annotation", common_core_uncertainty)))

    if components.get("floors", False):
        anchor_list = anchors["anchors"] if isinstance(anchors, dict) else anchors
        floor_x = float(display["floor_label_x_m"])
        for anchor in anchor_list:
            floor_id, z = anchor["source_floor_label"], float(anchor["z_m"])
            meta = _meta(
                [anchor["source_id"]], anchor["evidence_level"],
                "published_elevation_guide_not_floor_plate", "z equals source-labelled S13 anchor",
                anchor["uncertainty"] + "; guide length is display-only, slab edge and thickness unknown",
                source_locator=anchor["source_locator"],
                datum=anchor["datum"], source_floor_label=floor_id,
                normalized_floor_id=anchor.get("normalized_floor_id"),
                crosswalk_status=anchor.get("crosswalk_status", "unresolved"),
                floor_profile=None, placeholder=False,
            )
            guide = add(ctx.lines(f"LEVEL_S13_{floor_id}_{z:.2f}M_NOT_SLAB",
                                  [[(-half, 0, z), (floor_x, 0, z)]],
                                  "50_PUBLISHED_LEVEL_GUIDES", guide_radius, "guide", meta))
            actual_z = [p.co[2] for spline in guide.data.splines for p in spline.points]
            measured.setdefault("floor_guide_z_m", {})[floor_id] = actual_z[0]
            add(ctx.label(f"LEVEL_LABEL_S13_{floor_id}", f"{floor_id}  {z:.2f} m  [S13]",
                          (floor_x, 0, z), "50_PUBLISHED_LEVEL_GUIDES", label_size/3,
                          meta=meta))
            interface_meta = dict(meta, evidence_level="待确认",
                                  geometry_role="floor_profile_interface_no_slab",
                                  placeholder=True)
            add(ctx.empty(f"FLOOR_S13_{floor_id}_PROFILE_UNRESOLVED", (0, 0, z),
                          "51_FLOOR_PROFILE_INTERFACES", interface_meta))
            counts["published_floor_guides"] += 1
        measured["floor_schedule_complete"] = False

    if components.get("mega_frame_interfaces", False):
        for p_id, prefix in (("mega_column_count", "MEGACOLUMN"),
                             ("corner_column_count", "CORNER_DIAGONAL")):
            p = ctx.param(p_id)
            for index in range(int(p["value"])):
                add(ctx.empty(f"{prefix}_{index+1:02d}_AXIS_SECTION_UNRESOLVED",
                              (0, 0, boundaries[0]), "20_MEGA_FRAME_INTERFACES",
                              _meta(p["source_ids"], "待确认", "column_interface_no_axis",
                                    p["formula_and_assumptions"],
                                    "Count is published; all markers co-located intentionally. "
                                    "No equally spaced columns, inclinations or section schedule invented.",
                                    source_locator=p["source_locator"], placeholder=True,
                                    source_parameter_evidence="已证实")))
            counts[p_id + "_interfaces"] = int(p["value"])
        belt = ctx.param("belt_truss_groups")
        for index in range(int(belt["value"])):
            for ring in ("A", "B"):
                add(ctx.empty(f"BELT_GROUP_{index+1:02d}_PARALLEL_RING_{ring}_UNRESOLVED",
                              (0, 0, boundaries[index+1]), "30_BELT_TRUSS_INTERFACES",
                              _meta(belt["source_ids"], "待确认", "belt_ring_interface_no_members",
                                    "Eight two-story-high double belts; two parallel rings per group",
                                    "Reference height is for grouping only; true lower/upper chords, "
                                    "ring radii, vertical depth, H sections and nodes missing.",
                                    source_locator=belt["source_locator"], placeholder=True,
                                    belt_group=index+1, parallel_ring=ring,
                                    source_parameter_evidence="已证实")))
        counts["belt_groups"] = int(belt["value"])
        counts["parallel_belt_ring_interfaces"] = 2*int(belt["value"])
        outriggers = ctx.param("outrigger_groups")
        for zone in outriggers["value"]["zones"]:
            add(ctx.empty(f"OUTRIGGER_Z{zone:02d}_MEMBERS_NODES_UNRESOLVED",
                          (0, 0, boundaries[zone]), "31_OUTRIGGER_INTERFACES",
                          _meta(outriggers["source_ids"], "待确认", "outrigger_group_interface",
                                "Six two-story-high groups in source zones 2,4,5,6,7,8",
                                "Scene marker uses the zone-top diagram reference. "
                                "Actual chord levels, directional counts, paths and nodes unknown.",
                                source_locator=outriggers["source_locator"], placeholder=True,
                                source_zone=zone, source_parameter_evidence="已证实")))
        counts["outrigger_group_interfaces"] = len(outriggers["value"]["zones"])

    if components.get("cwss", False):
        p = ctx.param("cwss_scope")
        for zone in p["value"]:
            add(ctx.empty(f"CWSS_Z{zone:02d}_ACTUAL_ATTACHMENT_COORDINATES_UNRESOLVED",
                          (0, 0, boundaries[zone-1]), "40_CWSS_ATTACHMENT_INTERFACES",
                          _meta(p["source_ids"], "待确认", "cwss_attachment_interface",
                                "Source standard system covers Z2–Z8; coordinate tables absent",
                                "No 24/25 equal-angle hanging points or averaged radial spacing generated",
                                source_locator=p["source_locator"], placeholder=True,
                                source_zone=zone, source_parameter_evidence="已证实")))
        counts["cwss_zone_interfaces"] = len(p["value"])

    if components.get("podium_interface", False):
        add(ctx.empty("PODIUM_BOUNDARY_LEVELS_TOWER_JUNCTION_UNRESOLVED", (0, 0, 0),
                      "60_PODIUM_UNRESOLVED", _meta(
                          ["O04", "B14_STRUCT"], "待确认", "podium_boundary_interface",
                          "No inferred podium footprint or uniform-height retail block",
                          "Podium architectural boundary, roof levels, slabs and tower connection missing",
                          placeholder=True)))
        counts["podium_interfaces"] = 1

    if components.get("detail_samples", False):
        sx, sy, sz = cfg["cwss_detail_origin_m"]
        collection = "41_CWSS_INDEPENDENT_SPECIMENS"
        span = float(cfg["cwss_sample_span_display_m"])
        separation = float(cfg["hanger_pair_separation_display_m"])
        if span <= 0 or separation <= 0:
            raise ValueError("CWSS display specimen length and pair separation must be positive")
        pitches = ctx.param("cwss_ring_pitch")["value"]
        ring_d = ctx.param("cwss_ring_diameter")
        ring_t = ctx.param("cwss_ring_thickness")
        radial = ctx.param("cwss_radial_sections")
        hanger = ctx.param("cwss_hanger_diam")
        measured["cwss_hollow_specimens"] = []
        measured["hanger_specimens"] = []

        def specimen(name, start, end, diameter, thickness, source_param, kind):
            verts, faces, outside, inside = _circular_mesh(start, end, diameter, thickness)
            meta = _parameter_meta(
                source_param, "independent_section_specimen_not_building_member",
                formula=f"Ideal circular section OD={diameter}m; wall={thickness}m; "
                        "length and position are display-only; not an installed member",
                uncertainty="Section specification is published; section-to-floor allocation, "
                            "member length, joint shape and real coordinates unknown.",
                evidence_level_note="Specification confirmed; sample placement unverified",
                placeholder_placement=True, sample_kind=kind,
                outer_diameter_m=diameter,
                inner_diameter_m=None if thickness is None else diameter-2*thickness,
                outside_diameter_m=diameter, wall_thickness_m=thickness,
                inside_diameter_m=None if thickness is None else diameter-2*thickness,
                display_length_m=sqrt(sum(v*v for v in _subtract(end, start))),
            )
            obj = add(ctx.mesh(name, verts, faces, collection, "steel", meta))
            actual_verts = [v.co for v in obj.data.vertices]
            count = _DISPLAY["circle_segments"]
            outside = sqrt(sum(v*v for v in _subtract(actual_verts[0], actual_verts[count//2])))
            if thickness is not None:
                inside = sqrt(sum(v*v for v in _subtract(
                    actual_verts[2*count], actual_verts[2*count+count//2])))
            detail_vertices.extend(verts)
            record = {"name": name, "outside_diameter_measured_m": outside,
                      "inside_diameter_measured_m": inside, "asbuilt_verified": False}
            if thickness is None:
                measured["hanger_specimens"].append(record)
            else:
                record["wall_thickness_measured_m"] = (outside-inside)/2
                measured["cwss_hollow_specimens"].append(record)

        for index, thickness in enumerate(ring_t["value"]):
            z = sz + index*(max(pitches) + _DISPLAY["coupon_gap_m"])
            junction_x = sx+span/2
            specimen(f"CWSS_RING_OD{ring_d['value']*1000:.0f}_T{thickness*1000:.0f}_SPECIMEN",
                     (sx, sy, z), (sx+span, sy, z), ring_d["value"], thickness,
                     ring_t, "ring_beam")
            radial_d, radial_t = radial["value"][index % len(radial["value"])]
            specimen(f"CWSS_RADIAL_OD{radial_d*1000:.0f}_T{radial_t*1000:.0f}_SPECIMEN",
                     (junction_x, sy, z), (junction_x, sy+span, z), radial_d,
                     radial_t, radial, "radial_pipe")
            pitch = pitches[index % len(pitches)]
            hanger_d = hanger["value"][index % len(hanger["value"])]
            for side in (-1, 1):
                x = junction_x + side*separation/2
                specimen(f"CWSS_HANGER_D{hanger_d*1000:.0f}_PAIR_{index+1}_{'L' if side < 0 else 'R'}_SPECIMEN",
                         (x, sy, z), (x, sy, z+pitch), hanger_d, None,
                         hanger, "hanger_rod")
            add(ctx.empty(f"CWSS_SAMPLE_{index+1}_JOINT_SLIDE_INTERFACE",
                          (junction_x, sy, z), collection, _meta(
                              ["B14_CWSS"], "待确认", "cwss_node_kinematic_interface",
                              "Double-rod topology and vertical sliding mechanism are design concepts",
                              "Joint plates, bearing box, release direction axes and exact nodes unknown; "
                              "sample intersections are not fabricated connection details.",
                              placeholder=True, display_pair_separation_m=separation)))
            add(ctx.label(f"CWSS_SAMPLE_{index+1}_LABEL",
                          f"DESIGN SECTION SAMPLE / {pitch:.1f} m PITCH\n"
                          f"{span:g} m LENGTH + {separation:g} m PAIR GAP: DISPLAY ONLY",
                          (sx, sy-_DISPLAY["label_offset_m"], z+pitch), collection,
                          label_size/3, meta=_meta(
                              ["B14_CWSS"], "待确认", "annotation",
                              "Independent specimen annotation", "Not a real installation location")))
        counts["cwss_hollow_section_specimens"] = len(measured["cwss_hollow_specimens"])
        counts["hanger_rod_specimens"] = len(measured["hanger_specimens"])
        counts["hanger_pair_specimens"] = len(ring_t["value"])

        measured["core_wall_thickness_specimens"] = []
        for p_id, wall_kind in (("core_wall_ext", "EXTERNAL"), ("core_wall_int", "INTERNAL")):
            p = ctx.param(p_id)
            for index, thickness in enumerate(p["value"]):
                order = len(measured["core_wall_thickness_specimens"])
                x = sx + span + _DISPLAY["coupon_gap_m"] + order*(
                    _DISPLAY["wall_coupon_length_m"] + _DISPLAY["coupon_gap_m"])
                obj = add(ctx.box(f"CORE_{wall_kind}_T{thickness*1000:.0f}_SPECIMEN",
                                  (x, sy, sz+_DISPLAY["wall_coupon_height_m"]/2),
                                  (_DISPLAY["wall_coupon_length_m"], thickness,
                                   _DISPLAY["wall_coupon_height_m"]),
                                  "13_CORE_WALL_THICKNESS_SPECIMENS", "core",
                                  _parameter_meta(
                                      p, "independent_wall_thickness_specimen",
                                      formula="Published endpoint wall thickness; coupon length, "
                                              "height and location are presentation choices",
                                      uncertainty="No wall schedule, transition height, steel plate "
                                                  "configuration or actual wall assignment established",
                                      wall_kind=wall_kind, placeholder_placement=True)))
                ys = [v.co[1] for v in obj.data.vertices]
                measured["core_wall_thickness_specimens"].append({
                    "wall_kind": wall_kind, "thickness_measured_m": max(ys)-min(ys)})
                add(ctx.label(f"CORE_WALL_SAMPLE_LABEL_{wall_kind}_{index}",
                              f"{wall_kind} WALL / {thickness:g} m SPECIFICATION",
                              (x-_DISPLAY["wall_coupon_length_m"]/2, sy,
                               sz+_DISPLAY["wall_coupon_height_m"]+_DISPLAY["label_offset_m"]),
                              "13_CORE_WALL_THICKNESS_SPECIMENS", label_size/4,
                              meta=_parameter_meta(p, "annotation")))

        fx, fy, fz = cfg["floor_diameter_samples_origin_m"]
        diameters = ctx.param("inner_floor_diameters")
        measured["floor_diameter_specimens"] = []
        cursor = 0.0
        for index, diameter in enumerate(diameters["value"]):
            center = (fx+cursor+diameter/2, fy, fz)
            count = _DISPLAY["circle_segments"]
            verts = [(center[0]+diameter/2*cos(2*pi*i/count),
                      center[1]+diameter/2*sin(2*pi*i/count), center[2])
                     for i in range(count)]
            obj = add(ctx.mesh(f"FLOOR_DIAMETER_{diameter:g}M_INDEPENDENT_SPECIMEN", verts,
                              [tuple(range(count))], "52_FLOOR_DIAMETER_SPECIMENS", "derived",
                              _parameter_meta(
                             diameters, "independent_floor_diameter_specimen_not_slab",
                             formula="Flat dimension specimen for published circular-floor diameter; "
                                     "no structural thickness or source floor assigned",
                             uncertainty="82.2/46.5m are published endpoint diameters. "
                                         "Actual floor label, zone radii and slab edge table unknown.",
                             placeholder_placement=True, source_floor_label=None,
                             slab_thickness_m=None)))
            actual_d = sqrt(sum(v*v for v in _subtract(
                obj.data.vertices[0].co, obj.data.vertices[count//2].co)))
            measured["floor_diameter_specimens"].append(actual_d)
            add(ctx.label(f"FLOOR_DIAMETER_{index}_SPEC_LABEL",
                          f"{diameter:g} m DIAMETER SPECIMEN / FLOOR ASSIGNMENT UNKNOWN",
                          (center[0]-diameter/2, center[1]-diameter/2-_DISPLAY["label_offset_m"], fz),
                          "52_FLOOR_DIAMETER_SPECIMENS", label_size/2,
                          meta=_parameter_meta(diameters, "annotation")))
            cursor += diameter+_DISPLAY["coupon_gap_m"]

    detail_bounds = None
    detail_target = None
    if detail_vertices:
        lower = [min(v[i] for v in detail_vertices) for i in range(3)]
        upper = [max(v[i] for v in detail_vertices) for i in range(3)]
        detail_bounds = {"min_m": lower, "max_m": upper}
        detail_target = [(a+b)/2 for a, b in zip(lower, upper)]
    return {
        "object_count": len(objects),
        "component_counts": dict(counts),
        "measured_dimensions": measured,
        "published_core_width_m": reference_width,
        "core_width_matches_published": isclose(width, reference_width, abs_tol=1e-9),
        "completed_floor_slabs": 0,
        "asbuilt_verified": False,
        "unknown_items": unknown,
        "detail_bounds": detail_bounds,
        "detail_target_m": detail_target,
        "collection_counts": dict(Counter(
            collection.name for obj in objects for collection in obj.users_collection)),
        "geometry_roles": ["design control volume", "topology placeholder",
                           "published elevation guide", "unresolved attachment interface",
                           "independent dimension/section specimen"],
    }
