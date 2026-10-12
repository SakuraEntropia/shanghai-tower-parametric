"""Concentric, stepped B-wall reconstruction with explicit source-version limits.

This module deliberately does not create a twisting ninth inner cylinder, a
complete floor schedule, final B1/B8 mapping, or shop-sized aluminum sections.
The geometry helpers need no Blender installation; the builder accepts the
existing SceneBuilder and records checks of its actual generated coordinates.
"""
import math


def zone_layout(zone, modelling):
    """Build finite nominal bands, without stretching a residual gap to fit."""
    radius = float(zone['radius_m'])
    pitch = float(modelling['nominal_band_height_m'])
    module = float(modelling['vertical_module_m'])
    lower = max(float(zone['z0_m']), float(modelling['entity_start_m']))
    upper = min(float(zone['z1_m']), float(modelling['entity_stop_m']))
    if not all(math.isfinite(v) for v in (radius, pitch, module, lower, upper)):
        raise ValueError('Inner geometry parameters must be finite')
    if radius <= 0 or pitch <= 0 or module <= 0:
        raise ValueError('Inner radius and nominal modules must be positive')
    count = max(3, round(2 * math.pi * radius / module))
    bands = max(0, math.floor((upper - lower + 1e-9) / pitch))
    return {'radius_m': radius, 'facets': count, 'bands': bands,
            'open_bottom_band_count':int(modelling.get('open_bottom_band_count',0)) if float(zone['z0_m'])>=float(modelling['entity_start_m']) else 0,
            'z0_m': lower, 'z1_m': upper,
            'last_band_top_m': lower + bands * pitch,
            'unmodelled_residual_m': max(0, upper - lower - bands * pitch),
            'chord_module_m': 2 * radius * math.sin(math.pi / count),
            'sagitta_m': radius * (1 - math.cos(math.pi / count))}


def circle_points(radius, z, count, azimuth_deg=0):
    if count < 3:
        raise ValueError('A circle needs at least three samples')
    angle0 = math.radians(azimuth_deg)
    return [(radius * math.cos(angle0 + 2 * math.pi * i / count),
             radius * math.sin(angle0 + 2 * math.pi * i / count), float(z))
            for i in range(count)]


def zone_panel_mesh(layout, pitch, azimuth_deg=0):
    """Vertical planar rectangles; module azimuth is fixed at all heights."""
    vertices, faces, band_ids, module_ids = [], [], [], []
    xy = circle_points(layout['radius_m'], 0, layout['facets'], azimuth_deg)
    for band in range(layout.get('open_bottom_band_count',0),layout['bands']):
        z0 = layout['z0_m'] + band * pitch
        z1 = z0 + pitch
        for i, p0 in enumerate(xy):
            p1 = xy[(i + 1) % len(xy)]
            base = len(vertices)
            vertices.extend([(p0[0], p0[1], z0), (p1[0], p1[1], z0),
                             (p1[0], p1[1], z1), (p0[0], p0[1], z1)])
            faces.append((base, base + 1, base + 2, base + 3))
            band_ids.append(band)
            module_ids.append(i)
    return vertices, faces, band_ids, module_ids


def _meta(zone=None):
    return {'source_ids': ['D10', 'B14_STRUCT', 'S13', 'G01', 'B14_GREEN'],
            'source_locator': 'D10 printed p124 Fig5; S13 PDFp6 Fig1b; G01 p16/17; B14_GREEN p24/25',
            'evidence_level': '推导值', 'asbuilt_verified': False,
            'geometry_role': 'inner_candidate_panel',
            'zone': zone,
            'formula': 'Concentric fixed-radius zone; radius from calibrated D10 Fig5 / B14 endpoint transfer; N=round(2*pi*r/1m); nominal 4.5m demonstration bands.',
            'uncertainty': 'Radius±1.5m candidate bound; schematic/version system error unbounded. Zone levels are structural S13 anchors. Actual atrium boundaries, B termination, panel index, seam azimuth and final nodes unconfirmed.',
            'band_is_true_floor': False,
            'panel_module_is_asbuilt': False,
            'reference_wall': 'B; independent from A panel_surface_role',
            'source_versions': 'D10/G01:2010; B14_STRUCT/B14_GREEN:2014; S13:2013'}


def build_inner(ctx, geometry, candidate):
    modelling = candidate['modelling']
    pitch = float(modelling['nominal_band_height_m'])
    frame_radius = float(modelling['frame_curve_radius_m'])
    thickness = float(modelling['glass_assembly_candidate_thickness_m'])
    azimuth = float(modelling['azimuth_deg'])
    checks, rows, warnings = [], [], []
    objects, vertices_total, panels_total = 0, 0, 0

    def check(name, passed, measured, meaning):
        checks.append({'check': name, 'passed': bool(passed),
                       'measured': measured, 'meaning': meaning,
                       'asbuilt_verified': False})

    ctx.collection('83_CURTAIN_B_DERIVED')
    ctx.collection('84_CURTAIN_B_FRAME_DISPLAY')
    interface_collection = '85_INNER_UNCONFIRMED_INTERFACES'
    for zone in candidate['zones']:
        number = int(zone['zone'])
        radius = float(zone['radius_m'])
        if number == 1:
            points = circle_points(radius, float(zone['z1_m']), 288, azimuth)
            ctx.lines('ST_B_Z01_CONTROL_ONLY', [points + [points[0]]],
                      interface_collection, frame_radius, 'derived',
                      {**_meta(number), 'geometry_role': 'inner_zone1_control_not_installed_facade',
                       'uncertainty': 'Z1 circle is an endpoint-transfer control only. Ground/podium/B opening contours are not established.'})
            continue
        layout = zone_layout(zone, modelling)
        if not layout['bands']:
            continue
        verts, faces, band_ids, module_ids = zone_panel_mesh(layout, pitch, azimuth)
        glass_lower=layout['z0_m']+layout.get('open_bottom_band_count',0)*pitch
        meta = {**_meta(number), 'radius_m': radius,
                'radius_candidate_error_bound_m': zone['radius_error_bound_m'],
                'sampling_facets': layout['facets'],
                'nominal_band_height_m': pitch,
                'nominal_band_count': layout['bands'],
                'actual_mesh_z0_m': glass_lower,
                'open_bottom_band_count':layout.get('open_bottom_band_count',0),
                'open_base_rule_evidence':'User-observed atrium access correction; architectural floor crosswalk and opening sector extent remain unconfirmed',
                'actual_mesh_z1_m': layout['last_band_top_m'],
                'glass_assembly_candidate_thickness_m': thickness,
                'glass_assembly_source': modelling['glass_assembly_source'],
                'B1_B8_assignment': 'Unknown; interface only, no automatic bottom-three-band material assignment'}
        obj = ctx.mesh(f'ST_B_Z{number:02d}_DERIVED_PANELS', verts, faces,
                       '83_CURTAIN_B_DERIVED', 'glass_detail', meta,
                       face_attributes={'inner_candidate_panel': [1] * len(faces),
                                        'inner_band_id': band_ids,
                                        'inner_module_id': module_ids})
        modifier = obj.modifiers.new('B14_26MM_TOTAL_IGU_PROXY_NOT_LAYERED_DETAIL', 'SOLIDIFY')
        modifier.thickness = thickness
        modifier.offset = 0.0
        objects += 1
        panels_total += len(faces)
        vertices_total += len(verts)

        # Shared seam geometry avoids a doubled frame on every adjacent panel.
        lines = []
        endpoints = circle_points(radius, glass_lower, layout['facets'], azimuth)
        lines.extend([[p, (p[0], p[1], layout['last_band_top_m'])] for p in endpoints])
        for band in range(layout.get('open_bottom_band_count',0),layout['bands'] + 1):
            pts = circle_points(radius, layout['z0_m'] + band * pitch,
                                layout['facets'], azimuth)
            lines.append(pts + [pts[0]])
        ctx.lines(f'ST_B_Z{number:02d}_DISPLAY_FRAMES', lines,
                  '84_CURTAIN_B_FRAME_DISPLAY', frame_radius, 'steel',
                  {**meta, 'evidence_level': '待确认',
                   'geometry_role': 'inner_frame_display_section_unknown',
                   'frame_radius_m': frame_radius,
                   'formula': 'Shared lines along derived B mesh boundaries, circular bevel display proxy.',
                   'uncertainty': modelling['frame_section_evidence'] + '; location inherits derived circle/module/nominal bands.'})
        ctx.empty(f'ST_B_Z{number:02d}_B8_ATRIUM_START_INTERFACE',
                  (radius, 0, layout['z0_m']), interface_collection,
                  {**_meta(number), 'evidence_level': '待确认',
                   'geometry_role': 'inner_B8_B1_transition_interface',
                   'formula': 'G01 Fig37/B14 fire chapter: bottom three atrium floors B8, then B1; no known atrium floor levels to assign actual bands.',
                   'uncertainty': 'Interface position is candidate zone control, not verified atrium entrance. B8 top and exact mapping await architectural level schedule.'})

        # Inspect actual saved base-mesh coordinates, including Blender float32.
        actual_vertices = [tuple(v.co) for v in obj.data.vertices]
        actual_faces = [tuple(p.vertices) for p in obj.data.polygons]
        radius_error = max(abs(math.hypot(p[0], p[1]) - radius) for p in actual_vertices)
        twist_error = max(math.hypot(actual_vertices[f[0]][0] - actual_vertices[f[3]][0],
                                     actual_vertices[f[0]][1] - actual_vertices[f[3]][1]) for f in actual_faces)
        check(f'inner_Z{number}_radius', radius_error < .0001,
              {'max_vertex_radius_error_m': radius_error, 'target_m': radius},
              'Base-mesh vertices use the selected candidate radius; source radius error remains separate.')
        check(f'inner_Z{number}_does_not_twist', twist_error < 1e-9,
              {'max_vertical_edge_xy_error_m': twist_error, 'seam_azimuth_deg': azimuth},
              'B panel seams stay fixed with height; local seam azimuth is unconfirmed.')
        if layout.get('open_bottom_band_count',0):
            check(f'inner_Z{number}_base_atrium_band_has_no_glass',abs(min(v[2] for v in actual_vertices)-glass_lower)<.0001,
                  {'glass_starts_m':min(v[2] for v in actual_vertices),'open_lower_m':layout['z0_m'],'open_top_m':glass_lower},
                  'User-observed candidate base opening; support steel and slabs kept separately, not proof of full as-built opening sector.')

        # Six-arc mother profile excludes actual V-notch. A clearance is a
        # geometry/version diagnostic, never a claimed actual atrium clearance.
        a_min = (ctx.config['profile']['R1_m'] - ctx.config['profile']['L4_m']) * geometry.curve_state(layout['z1_m'], ctx.config)['scale']
        gap = a_min - radius
        uncertainty = float(zone['radius_error_bound_m'])
        clearance = {'A_mother_min_radius_m': a_min, 'B_candidate_radius_m': radius,
                     'nominal_radial_gap_m': gap,
                     'B_radius_uncertainty_m': uncertainty,
                     'gap_range_B_error_only_m': [gap - uncertainty, gap + uncertainty],
                     'z_evaluated_m': layout['z1_m'],
                     'scope': 'A six-arc mother profile vs B circle; actual V-notch / glass-slab offset / A curve uncertainty not included.'}
        if gap - uncertainty <= 0:
            warnings.append(f'Zone{number}: A/B nominal mother-profile gap {gap:.3f}m crosses zero with B±{uncertainty}m; dimensions retained unchanged.')
        if gap < 0:
            warnings.append(f'Zone{number}: nominal A/B overlap; no automatic radius shrink applied.')
        rows.append({'zone': number, **layout, 'panel_count': len(faces),
                     'evidence_level': '推导值', 'clearance_diagnostic': clearance})

    ctx.empty('ST_B_TERMINATION_UNCONFIRMED_542_TO_580M',
              (0, 0, float(modelling['entity_stop_m'])), interface_collection,
              {**_meta(), 'evidence_level': '待确认',
               'geometry_role': 'inner_upper_termination_interface',
               'formula': candidate['inner_top']['basis'],
               'uncertainty': candidate['inner_top']['conflict']})
    check('inner_candidate_segment_count', objects == 7,
          {'meshed_zone_count': objects, 'panels': panels_total},
          'Z2–8 ordinary candidate B; Z1 control only, no unsupported Z9 cylinder.')
    return {'status': 'DERIVED_SOURCE_CALIBRATED_B_CYLINDERS',
            'asbuilt_verified': False, 'software_checks_passed': all(c['passed'] for c in checks),
            'checks': checks, 'zones': rows, 'panel_count': panels_total,
            'base_vertices': vertices_total, 'uncertainty_warnings': warnings,
            'B8_assignment': 'Interface only; actual atrium floor levels missing',
            'upper_termination': candidate['inner_top'],
            'slabs': 'No complete floor schedule created; existing source anchors retained.'}
