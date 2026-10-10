"""Analytic research geometry derived from Gensler's published control diagrams.

The six-arc reference omits the actual V-notch. R1/L4's millimetre units,
internal tangency, scale interpretation and orientation remain explicit modeling
conventions, not as-built measurements. No unknown architectural value is filled
by this module. Blender is accessed only through the supplied SceneBuilder.
"""

from bisect import bisect_right
import math


def _number(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _positive(value, name):
    result = _number(value, name)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _count(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _profile_values(config):
    profile = config["profile"]
    radius = _positive(profile["R1_m"], "R1_m")
    offset = _positive(profile["L4_m"], "L4_m")
    angle = _number(profile["A1_deg"], "A1_deg")
    if not 0 < angle < 60:
        raise ValueError("A1_deg must lie strictly between 0 and 60 degrees")
    a = math.radians(angle)
    corner_offset = 2 * offset * math.tan(a) / (math.sqrt(3) - math.tan(a))
    center_distance = (offset + corner_offset / 2) / math.cos(a)
    corner_radius = radius - center_distance
    if corner_radius <= 0:
        raise ValueError("R1/L4/A1 do not produce a positive internally tangent R2")
    return radius, offset, angle, corner_offset, corner_radius


def profile_segments(config):
    """Return six CCW analytic arcs, in the local source-diagram frame.

    Angles describe radius-vector directions in this shared frame, not circle
    center bearings. K2 is an uncut reference corner; its real notch is unknown.
    """
    radius, offset, a, corner_offset, corner_radius = _profile_values(config)
    b = 60 - a
    centers = {
        f"{prefix}{i}": (
            distance * math.cos(math.radians(120 * i)),
            distance * math.sin(math.radians(120 * i)),
        )
        for prefix, distance in (("C", offset), ("K", corner_offset))
        for i in range(3)
    }
    definitions = [
        ("K0", corner_radius, -b, b),
        ("C2", radius, b, 120 - b),
        ("K1", corner_radius, 120 - b, 120 + b),
        ("C0", radius, 120 + b, 240 - b),
        ("K2", corner_radius, 240 - b, 240 + b),
        ("C1", radius, 240 + b, 360 - b),
    ]
    return [
        {
            "id": name,
            "center": centers[name],
            "radius": r,
            "start_deg": start,
            "end_deg": end,
            "length": r * math.radians(end - start),
        }
        for name, r, start, end in definitions
    ]


def _arc_point(segment, angle_deg):
    phi = math.radians(angle_deg)
    x, y = segment["center"]
    r = segment["radius"]
    return (x + r * math.cos(phi), y + r * math.sin(phi))


def _station_data(config):
    segments = profile_segments(config)
    ends = []
    total = 0.0
    origin = None
    for segment in segments:
        if segment["id"] == "C0":
            origin = total + segment["length"] / 2
        total += segment["length"]
        ends.append(total)
    return segments, ends, total, origin


def _point_at_station(station, data):
    segments, ends, total, origin = data
    position = (origin + station) % total
    index = min(bisect_right(ends, position), len(segments) - 1)
    before = ends[index - 1] if index else 0.0
    segment = segments[index]
    angle = segment["start_deg"] + math.degrees(
        (position - before) / segment["radius"]
    )
    return {"xy": _arc_point(segment, angle), "segment_id": segment["id"], "s_m": station}


def point_at_station(config, s_m):
    """Evaluate reference arc length measured CCW from C0's side midpoint.

    Wrapping applies to the six-arc reference, never to the incomplete real wall.
    """
    station = _number(s_m, "s_m")
    return _point_at_station(station, _station_data(config))


def sample_profile(config, count=288, return_details=False):
    """Uniform reference arc-length stations; terminal duplicate is omitted."""
    count = _count(count, "count")
    data = _station_data(config)
    details = [_point_at_station(i * data[2] / count, data) for i in range(count)]
    return details if return_details else [point["xy"] for point in details]


def _interval_ids(s0, s1, data):
    """Arcs overlapped by a forward station interval no longer than one circuit."""
    segments, ends, total, origin = data
    if s1 <= s0 or s1 - s0 > total + 1e-8:
        raise ValueError("Station interval must be positive and at most one perimeter")
    ids = []
    before = 0.0
    for segment, end in zip(segments, ends):
        start = (before - origin) % total
        # Including neighboring periods handles a wrap at the reference origin.
        for turn in (-1, 0, 1, 2):
            lo = start + turn * total
            hi = lo + segment["length"]
            if min(s1, hi) - max(s0, lo) > 1e-9:
                ids.append(segment["id"])
                break
        before = end
    return ids


def standard_grid(config, half_count=23):
    """Six mirrored half-corners, with explicitly derived equal arc-length cells.

    Group counts come from the 2014 design chapter; their geometric boundaries
    are NOT known. Equal widths are convention MC03. An override half_count may
    be used for software sampling, but does not inherit the 2/6/6/6/3 labels.
    """
    half_count = _count(half_count, "half_count")
    data = _station_data(config)
    count = 6 * half_count
    groups = config.get("curtain", {}).get("half_groups")
    valid_groups = (
        isinstance(groups, list)
        and all(isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in groups)
        and sum(groups) == half_count
    )
    excluded = config["profile"]["unresolved_notch_segment"]
    if excluded not in {segment["id"] for segment in data[0]}:
        raise ValueError("unresolved_notch_segment must identify an analytic reference arc")
    result = []
    for i in range(count):
        s0, s1 = i * data[2] / count, (i + 1) * data[2] / count
        point = _point_at_station(s0, data)
        half, within = divmod(i, half_count)
        group_index = None
        if valid_groups:
            ordered = groups if half % 2 == 0 else list(reversed(groups))
            boundary = 0
            for j, n in enumerate(ordered):
                boundary += n
                if within < boundary:
                    group_index = j if half % 2 == 0 else len(groups) - 1 - j
                    break
        interval_ids = _interval_ids(s0, s1, data)
        point.update(
            half_index=half,
            half_point_index=within,
            half_direction="side_to_apex" if half % 2 == 0 else "apex_to_side",
            group_index=group_index,
            span_segment_ids=interval_ids,
            excluded_by_notch_uncertainty=excluded in interval_ids,
        )
        result.append(point)
    return result


def _version(config, version=None):
    name = version if version is not None else config["selected_geometry_version"]
    try:
        record = config["versions"][name]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Unknown or unselected geometry version: {name!r}") from exc
    return name, record


def curve_state(z, config, version=None):
    """Conditional design scale/angle; reject every out-of-range request."""
    z = _number(z, "z")
    name, record = _version(config, version)
    z0 = _number(record["z0_m"], "z0_m")
    z1 = _number(record["z1_m"], "z1_m")
    if z1 <= z0:
        raise ValueError(f"{name}: z1_m must exceed z0_m")
    if not z0 <= z <= z1:
        raise ValueError(f"{name}: z={z} is outside supported control range [{z0}, {z1}]")
    q = _positive(record["remaining_ratio"], "remaining_ratio")
    twist = _number(record["twist_deg"], "twist_deg")
    orientation = config["orientation"]
    theta0 = _number(orientation["theta0_deg"], "theta0_deg")
    direction = _number(orientation["direction"], "direction")
    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or 1; it is a local display convention")
    t = (z - z0) / (z1 - z0)
    return {"scale": math.exp(math.log(q) * t), "theta_deg": theta0 + direction * twist * t}


def transform_profile(points, z, config, version=None):
    """Transform a sequence of local XY coordinates to XYZ control points."""
    state = curve_state(z, config, version)
    angle = math.radians(state["theta_deg"])
    c, s = math.cos(angle), math.sin(angle)
    scale = state["scale"]
    result = []
    for point in points:
        if len(point) != 2:
            raise ValueError("transform_profile requires XY coordinates, not point dictionaries")
        x, y = (_number(value, "XY coordinate") for value in point)
        result.append((scale * (c * x - s * y), scale * (s * x + c * y), float(z)))
    return result


def _tangency_error(segments):
    endpoint_error = 0.0
    tangent_error = 0.0
    for a, b in zip(segments, segments[1:] + segments[:1]):
        p, q = _arc_point(a, a["end_deg"]), _arc_point(b, b["start_deg"])
        endpoint_error = max(endpoint_error, math.dist(p, q))
        pa, pb = math.radians(a["end_deg"]), math.radians(b["start_deg"])
        tangent_error = max(tangent_error, math.hypot(math.sin(pa) - math.sin(pb), math.cos(pa) - math.cos(pb)))
    return endpoint_error, tangent_error


def _arc_polyline(segment, count):
    return [
        _arc_point(segment, segment["start_deg"] + i * (segment["end_deg"] - segment["start_deg"]) / count)
        for i in range(count + 1)
    ]


def build_envelope(ctx):
    """Create reference curves, a hidden diagnostic surface and unknown interfaces.

    No caps. No real-notch reconstruction. Diagnostic faces end at the explicitly
    configured standard-band reference upper bound; the crown is curves only.
    """
    config = ctx.config
    version_name, version = _version(config)
    segments, ends, perimeter, origin = _station_data(config)
    excluded = config["profile"]["unresolved_notch_segment"]
    if excluded not in {segment["id"] for segment in segments}:
        raise ValueError("unresolved_notch_segment must identify an analytic reference arc")
    z0, z1 = float(version["z0_m"]), float(version["z1_m"])
    curve_state(z0, config)
    curve_state(z1, config)
    sampling = config["sampling"]
    count = _count(sampling["profile_points"], "profile_points")
    if count < 6:
        raise ValueError("Diagnostic envelope needs at least six profile points")
    step = _positive(sampling["envelope_z_step_m"], "envelope_z_step_m")
    display = config["display"]
    line_radius = _positive(display["control_radius_m"], "control_radius_m")
    source_ids = sorted(set(["G01", "B14_GEOM"] + list(version["source_ids"])))
    meta = {
        "evidence_level": "推导值",
        "source_ids": source_ids,
        "formula": "R2=R1-(d+k/2)/cos(A1), k=2d*tan(A1)/(sqrt(3)-tan(A1)); scale=exp(ln(q)*t); theta=theta0+direction*twist*t",
        "uncertainty": "R1/L4 mm interpretation, internal tangency, q, axis/orientation and source-version applicability remain conditional; real notch and crown trim unknown",
        "geometry_role": "research_control",
        "asbuilt_verified": False,
        "geometry_version": version_name,
        "convention_ids": ["MC01", "MC02", "MC09"],
        "reference_line_kind": config["profile"]["reference_line_kind"],
    }
    details = sample_profile(config, count, True)
    xy = [point["xy"] for point in details]
    reference_curve_count = 0
    section_heights = list(sampling["section_z_m"])
    for z in section_heights:
        curve_state(z, config)
        tag = f"{z:08.3f}".replace(".", "p")
        if z == z1:
            polylines = [
                transform_profile(_arc_polyline(segment, max(2, math.ceil(count * segment["length"] / perimeter))), z, config)
                for segment in segments if segment["id"] != excluded
            ]
            ctx.lines(
                f"REFERENCE_OPEN_TOP_NO_CROWN_TRIM_Z{tag}_DERIVED",
                polylines, "70_OUTER_ENVELOPE", line_radius, "derived",
                dict(meta, incomplete_region=excluded, closed_profile=False),
            )
        else:
            points = transform_profile(xy, z, config)
            ctx.lines(
                f"REFERENCE_NO_NOTCH_Z{tag}_DERIVED",
                [points + [points[0]]], "70_OUTER_ENVELOPE", line_radius, "guide",
                dict(meta, reference_only=True, actual_notch_reconstructed=False),
            )
        reference_curve_count += 1

    boundaries = config["curtain"]["standard_zone_reference_boundaries_m"]
    for z in boundaries:
        curve_state(z, config)
    surface_top = max(boundaries)
    if surface_top <= z0:
        raise ValueError("Standard diagnostic surface upper boundary must exceed z0")
    row_z = [z0 + i * step for i in range(math.ceil((surface_top - z0) / step))]
    row_z.append(float(surface_top))
    verts = [vertex for z in row_z for vertex in transform_profile(xy, z, config)]
    data = (segments, ends, perimeter, origin)
    usable_edges = [
        i for i in range(count)
        if excluded not in _interval_ids(i * perimeter / count, (i + 1) * perimeter / count, data)
    ]
    faces = [
        (row * count + i, row * count + (i + 1) % count,
         (row + 1) * count + (i + 1) % count, (row + 1) * count + i)
        for row in range(len(row_z) - 1) for i in usable_edges
    ]
    surface = ctx.mesh(
        "DERIVED_DIAGNOSTIC_ENVELOPE_K2_EXCLUDED_NO_CAP",
        verts, faces, "70_OUTER_ENVELOPE", "glass",
        dict(meta, geometry_role="diagnostic_mother_surface", excluded_segment=excluded,
             actual_notch_reconstructed=False, crown_reconstructed=False,
             surface_top_m=surface_top, z_sampling_is_floor_schedule=False),
    )
    show_surface = bool(display.get("show_diagnostic_mother_surface", False))
    surface.hide_render = not show_surface
    surface.hide_viewport = not show_surface

    unknown = dict(
        meta, evidence_level="待确认", geometry_role="unresolved_interface",
        uncertainty="Interface display location only; no actual dimensions, boundary or construction asserted",
    )
    ctx.empty("INTERFACE_BOTTOM_0_TO_45_UNRESOLVED", (0, 0, z0), "70_OUTER_ENVELOPE", dict(unknown, missing_data="Bottom control curves and podium connection"))
    notch_arc = next(segment for segment in segments if segment["id"] == excluded)
    notch_marker = transform_profile([_arc_point(notch_arc, (notch_arc["start_deg"] + notch_arc["end_deg"]) / 2)], z0, config)[0]
    ctx.empty("INTERFACE_V_NOTCH_UNRESOLVED", notch_marker, "70_OUTER_ENVELOPE", dict(unknown, excluded_reference_segment=excluded, exclusion_is_actual_notch_boundary=False))
    ctx.empty("INTERFACE_CROWN_TRIM_UNRESOLVED", (0, 0, z1), "70_OUTER_ENVELOPE", dict(unknown, missing_data="Crown trim, sloping top edge and actual highest-point coordinate"))

    _, _, _, _, r2 = _profile_values(config)
    position_error, tangent_error = _tangency_error(segments)
    result = {
        "geometry_version": version_name,
        "evidence_level": "推导值",
        "asbuilt_verified": False,
        "R2_m": r2,
        "perimeter_m": perimeter,
        "perimeter_kind": "six_arc_reference_without_actual_notch",
        "tangency_error_m": position_error,
        "tangent_vector_error": tangent_error,
        "valid_range": [z0, z1],
        "rows": len(row_z),
        "row_z_m": row_z,
        "surface_range_m": [z0, surface_top],
        "mother_faces": len(faces),
        "mother_surface_hidden": not show_surface,
        "reference_curve_count": reference_curve_count,
        "unknown_notch": True,
        "excluded_reference_segment": excluded,
        "exclusion_is_actual_notch_boundary": False,
        "unknown_crown_trim": True,
        "has_flat_cap": False,
    }
    ctx.component_results["envelope"] = result
    return result
