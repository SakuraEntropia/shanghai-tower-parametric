"""Shared finite facade bands and explicitly candidate full transition plates.

Source strengthening heights are not a complete floor/curtain-wall schedule.
No final intake/exhaust, frit or shop panel map is inferred from these controls.
"""
import math


def transition_regions(rows, parameters):
    """Retain each published interface; map its preceding two candidate spaces."""
    result = []
    for index, z in enumerate(parameters['source_interface_elevations_m'], 1):
        position = next((i for i, r in enumerate(rows) if abs(r['z_m'] - z) < 1e-7), None)
        if position is None or position < 2:
            raise ValueError(f'No floor schedule match for transition interface {z}')
        lower, middle, upper = rows[position - 2:position + 1]
        result.append({'id': f'TRANSITION_{index:02d}', 'source_upper_z_m': float(z),
                       'z_bottom_m': lower['z_m'], 'z_middle_m': middle['z_m'],
                       'z_top_m': upper['z_m'],
                       'candidate_plate_numbers': [middle['candidate_number'], upper['candidate_number']],
                       'source_upper_floor_label': upper['source_local_label'],
                       'lower_mapping_evidence_level': '推导值',
                       'source_ids': ['S13', 'G01', 'B14_STRUCT'],
                       'scope': 'Two full candidate transition plates; source-local floor crosswalk unresolved.'})
    return result


def configure(config, completion, anchors, assembly, parameters):
    from floors_v3 import derive_schedule, DEFAULTS
    rows, _ = derive_schedule(anchors, completion['crown'], {**DEFAULTS, **assembly.get('floors', {})})
    config['transition_v5'] = {**parameters, 'regions': transition_regions(rows, parameters)}
    return config['transition_v5']


def band_schedule(config):
    """One positive non-overlapping partition for A, V, residuals and interfaces."""
    curtain = config['curtain']
    pitch = float(curtain['nominal_band_pitch_m'])
    if not math.isfinite(pitch) or pitch <= 0:
        raise ValueError('Facade nominal pitch must be finite and positive')
    boundaries = list(map(float, curtain['standard_zone_reference_boundaries_m']))
    regions = config.get('transition_v5', {}).get('regions', [])
    cuts = {0.0, *boundaries}
    for region in regions:
        cuts.update(float(region[key]) for key in ('z_bottom_m', 'z_middle_m', 'z_top_m'))
    cuts = sorted(z for z in cuts if 0 <= z <= boundaries[-1])
    rows = []
    for bottom, top in zip(cuts, cuts[1:]):
        z = bottom
        while z < top - 1e-8:
            z1 = min(top, z + pitch)
            midpoint = (z + z1) / 2
            zone = 1 + sum(midpoint >= bound for bound in boundaries[:-1])
            # The 45m analytic start is not the architectural Z1/Z2 interface.
            architectural = config.get('transition_v5', {}).get('source_interface_elevations_m', [])
            if architectural:
                zone = 1 + sum(midpoint >= bound for bound in architectural)
            region = next((r for r in regions if r['z_bottom_m'] <= midpoint < r['z_top_m']), None)
            rows.append({'index': len(rows), 'z_bottom_m': z, 'z_top_m': z1,
                         'zone': zone, 'transition_id': region['id'] if region else None,
                         'kind': 'MEP_REFUGE_REGION_CANDIDATE' if region else 'STANDARD_DERIVED',
                         'is_residual': z1 - z < pitch - 1e-7,
                         'extrapolated_below_45m': z < boundaries[0]})
            z = z1
    return rows


def outer_reference(geometry, config):
    grid = geometry.standard_grid(config, config['curtain']['half_panel_count'])
    points = [row['xy'] for row in grid]
    if 'notch_v4' in config:
        from notch_v4 import recess_points
        points = recess_points(geometry, config, points, config['notch_v4'])
    return grid, points


def control_profile_at(geometry, config, points, z):
    """Same conditional taper/rotation, including labelled below-45 extension."""
    version = config['versions'][config['selected_geometry_version']]
    t = (z - version['z0_m']) / (version['z1_m'] - version['z0_m'])
    scale = math.exp(math.log(version['remaining_ratio']) * t)
    theta = math.radians(config['orientation']['theta0_deg'] +
                        config['orientation']['direction'] * version['twist_deg'] * t)
    c, s = math.cos(theta), math.sin(theta)
    return [(scale * (x * c - y * s), scale * (x * s + y * c), z) for x, y in points]


def step_faces(previous, following, z):
    """Simple horizontal faces between two panel chords; never a bow-tie quad.

    Taper plus twist can make consecutive chords intersect. A four-point face
    then self-intersects. Partition at the intersection into two simple wedges.
    This is topology repair, not a claim about the real extrusion profile.
    """
    a, b = [(p[0], p[1], z) for p in previous]
    d, c = [(p[0], p[1], z) for p in following]

    def cross(u, v):
        return u[0] * v[1] - u[1] * v[0]

    def intersection(p, q, r, s):
        u = (q[0] - p[0], q[1] - p[1])
        v = (s[0] - r[0], s[1] - r[1])
        den = cross(u, v)
        if abs(den) < 1e-13:
            return None
        rp = (r[0] - p[0], r[1] - p[1])
        t, w = cross(rp, v) / den, cross(rp, u) / den
        if 1e-9 < t < 1 - 1e-9 and 1e-9 < w < 1 - 1e-9:
            return (p[0] + t * u[0], p[1] + t * u[1], z)
        return None

    hit = intersection(a, b, c, d)
    if hit is not None:
        faces = [[a, hit, d], [hit, b, c]]
    else:
        hit = intersection(b, c, d, a)
        faces = [[a, b, hit], [hit, c, d]] if hit is not None else [[a, b, c, d]]
    # Winding differs across a chord crossing: orient every simple face up.
    result = []
    for face in faces:
        area = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(face, face[1:] + face[:1])) / 2
        if abs(area) > 1e-12:
            result.append(face if area > 0 else list(reversed(face)))
    return result
