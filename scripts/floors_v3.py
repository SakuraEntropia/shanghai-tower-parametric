"""Editable candidate slabs with core voids and a versioned derived level schedule.

S13 floor numbers are source-local identifiers, never a resolved operating
floor crosswalk. Interpolation fills geometry, not missing archival evidence.
"""
import math
import re
from collections import Counter

DEFAULTS = {
    'display_lower_levels_m': [0.0, 5.5, 11.0, 16.5],
    'samples': 192,
    'office_thickness_m': .155,
    'public_thickness_m': .225,
    'lower_thickness_m': .225,
    'radial_beam_radius_display_m': .10,
    'radial_beam_count_display': 16,
    'beam_floor_stride': 12,
    'top_default_radius_m': 23.25,
    'roof_slab_radius_candidate_m': 17.0,
}


def _floor_number(label):
    match = re.search(r'(\d+)$', label)
    if not match:
        raise ValueError(f'No source-local floor number in {label!r}')
    return int(match.group(1))


def derive_schedule(anchors, crown, options):
    original = sorted(anchors['anchors'], key=lambda a: _floor_number(a['source_floor_label']))
    result = {}
    for a, b in zip(original, original[1:]):
        ia, ib = _floor_number(a['source_floor_label']), _floor_number(b['source_floor_label'])
        if ib <= ia or float(b['z_m']) <= float(a['z_m']):
            raise ValueError('Source-local floor anchors must increase in number and height')
        for number in range(ia, ib + 1):
            t = (number - ia) / (ib - ia)
            z = float(a['z_m']) + t * (float(b['z_m']) - float(a['z_m']))
            result[number] = {'candidate_number': number, 'z_m': z,
                              'source_local_label': f'F{number}',
                              'level_method': 'linear_between_S13_source_numbers',
                              'level_evidence_level': '推导值',
                              'level_formula': f'{a["z_m"]} + ({b["z_m"]}-{a["z_m"]})*({number}-{ia})/({ib}-{ia})',
                              'source_ids': ['S13'], 'normalized_floor_id': None,
                              'floor_crosswalk_status': 'unresolved'}
    for a in original:
        number = _floor_number(a['source_floor_label'])
        result[number] = {**result.get(number, {}), 'candidate_number': number,
                          'z_m': float(a['z_m']), 'source_local_label': a['source_floor_label'],
                          'level_method': 'exact_S13_monitoring_anchor',
                          'level_evidence_level': '已证实',
                          'level_formula': 'Published monitoring anchor copied exactly; assignment to slab top is derived.',
                          'source_ids': ['S13'], 'normalized_floor_id': None,
                          'floor_crosswalk_status': 'unresolved'}
    first_number = _floor_number(original[0]['source_floor_label'])
    lower = options['display_lower_levels_m']
    if len(lower) != first_number - 1:
        raise ValueError('Lower display levels must fill only numbers before the first S13 anchor')
    for number, z in enumerate(lower, 1):
        result[number] = {'candidate_number': number, 'z_m': float(z),
                          'source_local_label': None, 'level_method': 'display_lower_level',
                          'level_evidence_level': '待确认',
                          'level_formula': 'assembly.floors.display_lower_levels_m; ground candidate top fixed at0m; no architectural floor crosswalk.',
                          'source_ids': ['B14_STRUCT'], 'normalized_floor_id': None,
                          'floor_crosswalk_status': 'unresolved'}
    last = max(result)
    upper_comparison = []
    for item in crown.get('floor_image_candidates', []):
        number = _floor_number(item['source_floor_label'])
        if number <= last:
            upper_comparison.append({'source_local_label': item['source_floor_label'],
                                     'NTUA_z_m': item['z_m'],
                                     'S13_selected_z_m': result.get(number, {}).get('z_m'),
                                     'action': 'Alternative source version kept as comparison, not duplicate physical slab.'})
            continue
        result[number] = {'candidate_number': number, 'z_m': float(item['z_m']),
                          'source_local_label': item['source_floor_label'],
                          'level_method': 'NTUA_section_image_candidate',
                          'level_evidence_level': '推导值', 'level_error_m': item.get('error_m', 1.5),
                          'level_formula': 'NTUA Fig8 image-derived height; local L counter is not reconciled with S13 F counter.',
                          'source_ids': ['CROWN_NTUA_2014'], 'normalized_floor_id': None,
                          'floor_crosswalk_status': 'unresolved'}
    roof = next(a for a in crown['anchors'] if a['id'] == 'main_inner_roof')
    result[129] = {'candidate_number': 129, 'z_m': float(roof['z_m']),
                   'source_local_label': roof.get('source_floor_label'),
                   'level_method': 'NTUA_section_roof_candidate',
                   'level_evidence_level': '推导值', 'level_error_m': roof.get('error_m', 1.5),
                   'level_formula': 'NTUA Fig8 L129 roof height candidate; circular plan radius remains an independent assumption.',
                   'source_ids': ['CROWN_NTUA_2014'], 'normalized_floor_id': None,
                   'floor_crosswalk_status': 'unresolved'}
    rows = [result[n] for n in sorted(result)]
    if any(a['z_m'] >= b['z_m'] for a, b in zip(rows, rows[1:])):
        raise ValueError('Chosen cross-version candidate schedule has non-increasing heights')
    return rows, upper_comparison


def core_hole_polygon(core, zone):
    h = float(core['outer_width_m']) / 2
    x = max(abs(a) for a in core['inner_axes_x_m'])
    y = max(abs(a) for a in core['inner_axes_y_m'])
    if zone <= 4:
        return [(-h, -h), (h, -h), (h, h), (-h, h)]
    if zone <= 6:
        e = float(core['partial_corner_side_end_m'])
        return [(-e, -h), (e, -h), (h, -e), (h, e), (e, h), (-e, h), (-h, e), (-h, -e)]
    if zone <= 8:
        t = float(core['outer_thickness_m'][zone - 1]) / 2
        x += t
        y += t
        return [(-x, -h), (x, -h), (x, -y), (h, -y), (h, y), (x, y),
                (x, h), (-x, h), (-x, y), (-h, y), (-h, -y), (-x, -y)]
    x += float(core['outer_thickness_m'][8]) / 2
    return [(-x, -h), (x, -h), (x, h), (-x, h)]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def ray_hole_radius(polygon, angle):
    direction = (math.cos(angle), math.sin(angle))
    intersections = []
    for p, q in zip(polygon, polygon[1:] + polygon[:1]):
        edge = (q[0] - p[0], q[1] - p[1])
        den = _cross(direction, edge)
        if abs(den) < 1e-12:
            continue
        radius = _cross(p, edge) / den
        position = _cross(p, direction) / den
        if radius > 0 and -1e-9 <= position <= 1 + 1e-9:
            intersections.append(radius)
    if not intersections:
        raise ValueError('Core polygon does not surround the origin')
    return max(intersections)


def annular_slab(radius, hole, top_z, thickness, samples):
    if radius <= 0 or thickness <= 0 or samples < 16:
        raise ValueError('Invalid slab dimensions or sampling')
    # Include every corner bearing, keeping the polygonal hole sharp.
    angles = sorted({round(2 * math.pi * i / samples, 12) for i in range(samples)} |
                    {round(math.atan2(y, x) % (2 * math.pi), 12) for x, y in hole})
    inner, outer = [], []
    for angle in angles:
        ir = ray_hole_radius(hole, angle)
        if ir >= radius:
            raise ValueError('Core opening lies outside the candidate circular slab')
        c, s = math.cos(angle), math.sin(angle)
        inner.append((ir * c, ir * s))
        outer.append((radius * c, radius * s))
    count = len(angles)
    verts = [(x, y, z) for z in (top_z - thickness, top_z) for ring in (inner, outer) for x, y in ring]
    faces = []
    for i in range(count):
        j = (i + 1) % count
        faces.extend([(i, j, count + j, count + i),
                      (2 * count + i, 3 * count + i, 3 * count + j, 2 * count + j),
                      (count + i, count + j, 3 * count + j, 3 * count + i),
                      (i, 2 * count + i, 2 * count + j, j)])
    return verts, faces


def _zone(z, inner):
    for row in inner['zones']:
        if z < row['z1_m'] - 1e-7:
            return int(row['zone']), float(row['radius_m'])
    return 9, None


def polygonal_slab(outline, hole, top_z, thickness):
    """Closed star-shaped extrusion, with exact outer/V and core corners.

    Rays pair outer contour with core aperture; the concave V is retained,
    unlike a convex hull or circular floor extension. Source contours both
    surround the origin and must be star-shaped in this local convention.
    """
    if len(outline) < 3 or thickness <= 0:
        raise ValueError('Invalid polygonal slab outline or thickness')
    angles = sorted({round(math.atan2(y, x) % (2 * math.pi), 12) for x, y in outline + hole})
    inner, outer = [], []
    for angle in angles:
        ir, radius = ray_hole_radius(hole, angle), ray_hole_radius(outline, angle)
        if ir >= radius:
            raise ValueError('Core opening lies outside the full transition floor')
        c, s = math.cos(angle), math.sin(angle)
        inner.append((ir * c, ir * s)); outer.append((radius * c, radius * s))
    count = len(angles)
    verts = [(x, y, z) for z in (top_z - thickness, top_z) for ring in (inner, outer) for x, y in ring]
    faces = []
    for i in range(count):
        j = (i + 1) % count
        faces.extend([(i, j, count + j, count + i),
                      (2 * count + i, 3 * count + i, 3 * count + j, 2 * count + j),
                      (count + i, count + j, 3 * count + j, 3 * count + i),
                      (i, 2 * count + i, 2 * count + j, j)])
    return verts, faces


def _distance_to_outline(point, outline):
    result = []
    for a, b in zip(outline, outline[1:] + outline[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0., min(1., ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / (dx * dx + dy * dy)))
        result.append(math.hypot(point[0] - a[0] - t * dx, point[1] - a[1] - t * dy))
    return min(result)


def build_floors(ctx, geometry, candidate, anchors, assembly):
    options = {**DEFAULTS, **assembly.get('floors', {})}
    core, inner, crown = candidate['core'], candidate['inner'], candidate['crown']
    rows, comparisons = derive_schedule(anchors, crown, options)
    transition = ctx.config.get('transition_v5', {})
    full_plate_regions = {number: region for region in transition.get('regions', [])
                          for number in region['candidate_plate_numbers']}
    reports, checks, beams, warnings = [], [], [], []
    special_z = [float(a['z1_m']) for a in inner['zones']]
    for row in rows:
        number, top = row['candidate_number'], row['z_m']
        zone, radius = _zone(top, inner)
        radius = float(options['top_default_radius_m']) if radius is None else radius
        if number == 129:
            radius = float(options['roof_slab_radius_candidate_m'])
        full_region = full_plate_regions.get(number)
        is_public = bool(full_region) or any(abs(top - z) < 1e-6 for z in special_z)
        thickness = float(options['lower_thickness_m'] if top < 45 else
                          options['public_thickness_m'] if is_public or zone == 9 else options['office_thickness_m'])
        hole = core_hole_polygon(core, zone)
        outer_outline = None
        if full_region:
            from transition_v5 import outer_reference, control_profile_at
            _, reference = outer_reference(geometry, ctx.config)
            outer = control_profile_at(geometry, ctx.config, reference, top)
            inset = float(transition['outer_plate_inset_candidate_m'])
            outer_outline = [(x * (1 - inset / math.hypot(x, y)),
                              y * (1 - inset / math.hypot(x, y))) for x, y, _ in outer]
            thickness = float(transition['slab_thickness_candidate_m'])
            verts, faces = polygonal_slab(outer_outline, hole, top, thickness)
        else:
            verts, faces = annular_slab(radius, hole, top, thickness, int(options['samples']))
        meta = {'source_ids': list(dict.fromkeys(row['source_ids'] + ['D10', 'B14_STRUCT', 'S13'])),
                'source_locator': 'S13 PDFp12 Fig6; D10 p123 Fig3; B14_STRUCT p32/38; NTUA Fig8 where indicated',
                'evidence_level': '推导值', 'asbuilt_verified': False,
                'geometry_role': 'derived_solid_floor_plate_with_core_void',
                'formula': row['level_formula'] + '; fixed zone circular radius; upper roof radius is a separate editable unconfirmed candidate; star-shaped annular extrusion around derived core envelope.',
                'uncertainty': 'Complete architectural floor schedule/crosswalk unavailable. Monitoring or section-image heights assigned to slab top conditionally. Radius±1.5m candidate; actual core openings and MEP/amenity extensions/terraces unresolved.',
                'candidate_floor_number': number, 'source_local_floor_label': row['source_local_label'],
                'normalized_floor_id': None, 'floor_crosswalk_status': 'unresolved',
                'level_method': row['level_method'], 'level_evidence_level': row['level_evidence_level'],
                'slab_top_z_m': top, 'slab_thickness_m': thickness,
                'zone': zone, 'radius_m': radius, 'core_hole_polygon_m': hole,
                'thickness_evidence': 'Office155mm source p38; public225mm chosen within published200–250mm; lower/hotel/top mapping derived.',
                'mechanical_floor_extension': 'Full A-outline transition plate with concave V retained.' if full_region else 'Standard circular conditioned floor; atrium kept open.',
                'full_outer_transition_plate': bool(full_region),
                'transition_region_id': full_region['id'] if full_region else None}
        if full_region:
            meta.update(source_ids=list(dict.fromkeys(meta['source_ids'] + ['G01', 'B14_GEOM'])),
                        formula=row['level_formula'] + '; same derived A control grid at this z, including closed reentrant95deg V; radial75mm candidate inset; core aperture unchanged.',
                        uncertainty='Full triangular MEP/amenity plate topology supported by G01 Fig12/14 and B14_STRUCT p34. Upper S13 interface exact; preceding candidate plate assignment derived. Final slab edge, inset, refuge/MEP crosswalk and openings unconfirmed.',
                        outer_outline_candidate_m=outer_outline,
                        outer_outline_source_ids=['G01', 'B14_GEOM'],
                        outer_plate_inset_candidate_m=transition['outer_plate_inset_candidate_m'],
                        topology_evidence_level='已证实', placement_evidence_level='推导值')
        obj = ctx.mesh(f'F{number:03d}_DERIVED_SLAB', verts, faces,
                       '50_DERIVED_SOLID_FLOOR_PLATES', 'core', meta)
        notch=None
        if full_region and transition.get('interlayer_notch_v11'):
            from corrections_v11 import cut_transition
            notch=cut_transition(ctx,obj,radius,outer_outline,top,thickness)
            import json
            obj['source_ids']=json.dumps(list(dict.fromkeys(json.loads(obj['source_ids'])+['USER_OBSERVATION_V11'])))
            obj['formula']+='; candidate interlayer notch per user, shared by both transition plates, follows tower twist.'
            obj['uncertainty']+=' Notch placement/width unverified; does not establish final floor opening schedule.'
        actual_top = max(v.co.z for v in obj.data.vertices)
        if full_region:
            if notch:
                radius_error=max(max(0.,math.hypot(v.co.x,v.co.y)-ray_hole_radius(outer_outline,math.atan2(v.co.y,v.co.x))) for v in obj.data.vertices)
            else:
                ring_count = len(verts) // 4
                radius_error = max(_distance_to_outline((v.co.x, v.co.y), outer_outline)
                                   for v in list(obj.data.vertices)[ring_count:2 * ring_count])
        else:
            radius_error = max(abs(math.hypot(v.co.x, v.co.y) - radius)
                               for v in obj.data.vertices if math.hypot(v.co.x, v.co.y) > radius - .1)
        edges = Counter(tuple(sorted((a, b))) for p in obj.data.polygons
                        for a, b in zip(p.vertices, list(p.vertices[1:]) + [p.vertices[0]]))
        passed = all(n == 2 for n in edges.values()) and abs(actual_top - top) < .0001 and radius_error < .0001
        checks.append({'name': f'floor_F{number:03d}_closed_top_and_radius', 'passed': passed,
                       'actual': {'top_z_m': actual_top, 'target_z_m': top,
                                  'radius_error_m': radius_error, 'nonmanifold_edges': sum(n != 2 for n in edges.values())},
                       'scope': 'Software solid / candidate position checks, not as-built floor verification'})
        reports.append({**row, 'zone': zone, 'radius_m': radius, 'thickness_m': thickness,
                        'object': obj.name, 'core_hole_vertices': hole,
                        'full_outer_transition_plate': bool(full_region),
                        'transition_region_id': full_region['id'] if full_region else None,
                        'outer_outline_candidate_m': outer_outline,'interlayer_notch_v11':notch})
        if top >= 45 and not full_region:
            a_min = (ctx.config['profile']['R1_m'] - ctx.config['profile']['L4_m']) * geometry.curve_state(top, ctx.config)['scale']
            if a_min < radius:
                warnings.append({'floor': number, 'z_m': top, 'A_mother_min_radius_m': a_min,
                                 'slab_radius_m': radius, 'nominal_radial_overlap_m': radius - a_min,
                                 'action': 'Source-derived radius retained; no automatic shrink to force A clearance.'})
        if number % int(options['beam_floor_stride']) == 0:
            for i in range(int(options['radial_beam_count_display'])):
                angle = 2 * math.pi * i / int(options['radial_beam_count_display'])
                ir = ray_hole_radius(hole, angle)
                z = top - thickness - float(options['radial_beam_radius_display_m'])
                c, s = math.cos(angle), math.sin(angle)
                beams.append([(ir * c, ir * s, z), (radius * c, radius * s, z)])
    ctx.lines('FLOOR_RADIAL_BEAMS_DISPLAY_SECTION_UNCONFIRMED', beams,
              '51_FLOOR_BEAMS_DISPLAY', float(options['radial_beam_radius_display_m']), 'steel',
              {'source_ids': ['B14_STRUCT', 'D10'], 'source_locator': 'B14_STRUCT p38 gravity system; D10 Fig3',
               'evidence_level': '待确认', 'geometry_role': 'floor_radial_beam_display_not_member_schedule',
               'asbuilt_verified': False, 'formula': 'Display-only radial beam count/section/floor stride from assembly.floors.',
               'uncertainty': 'Actual beam grid, sections, endpoints, elevations and composite deck ribs unknown; topology proxy only.'})
    anchor_errors = []
    for anchor in anchors['anchors']:
        match = next(r for r in reports if r['candidate_number'] == _floor_number(anchor['source_floor_label']))
        anchor_errors.append({'source_label': anchor['source_floor_label'],
                              'error_m': match['z_m'] - float(anchor['z_m'])})
    checks.append({'name': 'all_S13_anchors_retained_exactly',
                   'passed': all(abs(a['error_m']) < 1e-10 for a in anchor_errors),
                   'actual': anchor_errors, 'scope': 'Published nominal z values retained; slab-top assignment remains derived'})
    checks.append({'name': 'ground_candidate_top_zero', 'passed': reports[0]['z_m'] == 0,
                   'actual': reports[0]['z_m'], 'scope': 'User scene datum; surveyed entrance offset unconfirmed'})
    return {'status': 'DERIVED_COMPLETE_GEOMETRY_SCHEDULE_NOT_CONFIRMED_ARCHITECTURAL_SCHEDULE',
            'slab_count': len(reports), 'levels': reports,
            'checks': checks, 'software_checks_passed': all(a['passed'] for a in checks),
            'parameter_inputs': options, 'upper_version_comparisons': comparisons,
            'clearance_warnings': warnings, 'beam_display_segments': len(beams),
            'full_outer_transition_plate_count': len(full_plate_regions),
            'transition_regions': transition.get('regions', []),
            'interpolated_rows': [r for r in reports if r['level_method'] == 'linear_between_S13_source_numbers'],
            'assumptions': ['S13 F and NTUA L counters are source-local; appended numbers are candidate labels, not a resolved floor crosswalk.',
                            'Standard slabs remain fixed concentric circles; two candidate transition plates per published interface use full A/V outline.',
                            'Core void envelopes are derived plan templates; no internal shaft area filled with slab.',
                            'Hotel/top slab thickness .225m is an editable mapping of the public-floor candidate, not a verified hotel schedule.'],
            'asbuilt_verified': False}
