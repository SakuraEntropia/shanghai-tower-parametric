"""Open crown form fit, with an explicit, replaceable station-height hypothesis.

This is not the standard curtain-wall pattern.  Published section samples do
not determine the circumferential clipping coordinates or fabrication panels.
No Blender dependency: the builder and analytic geometry module are supplied.
"""
import math


def _finite(value, name):
    if isinstance(value, bool):
        raise ValueError(f'{name} must be finite')
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f'{name} must be finite')
    return result


def _trim_controls(candidate):
    implementation = candidate.get('implementation_candidate', candidate)
    controls = implementation['station_height_m']
    if len(controls) != 3:
        raise ValueError('Crown fit requires three station-height controls')
    (s0, high), (mid, low), (s1, end) = [
        tuple(_finite(v, 'station/height') for v in pair) for pair in controls]
    if s0 != 0 or s1 != 1 or not 0 < mid < 1:
        raise ValueError('Crown controls must start at 0, end at 1, and have an interior minimum')
    mode = implementation.get('rim_mode', 'split_valley_parabola')
    if mode == 'split_crest_parabola':
        if not low > max(high, end):
            raise ValueError('Interior crown crest must exceed both open lips')
    elif mode != 'split_valley_parabola' or not low < min(high, end):
        raise ValueError('Interior valley control must be lower than both open ends')
    return mid, high, low, end


def trim_height(s, candidate):
    """Evaluate the two explicit quadratic branches; never wrap the open rim."""
    s = _finite(s, 's')
    if not 0 <= s <= 1:
        raise ValueError('Open crown station must be in [0, 1]')
    mid, high, low, end = _trim_controls(candidate)
    if candidate.get('implementation_candidate', candidate).get('rim_mode') == 'split_crest_parabola':
        if s <= mid:
            return low-(low-high)*(1-s/mid)**2
        return low-(low-end)*((s-mid)/(1-mid))**2
    if s <= mid:
        return low + (high-low)*(1-s/mid)**2
    return low + (end-low)*((s-mid)/(1-mid))**2


def open_profile_stations(geometry, config, count=160, extra_stations=()):
    """Sample C1/K0/C2/K1/C0 after the excluded K2, preserving all arc joins."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 5:
        raise ValueError('Crown sampling count must be an integer >= 5')
    arcs = geometry.profile_segments(config)
    ids = [a['id'] for a in arcs]
    if config['profile']['unresolved_notch_segment'] != 'K2' or 'K2' not in ids:
        raise ValueError('This candidate mapping is defined only after K2 exclusion')
    index = ids.index('K2')
    selected = arcs[index+1:] + arcs[:index]
    if [a['id'] for a in selected] != ['C1', 'K0', 'C2', 'K1', 'C0']:
        raise ValueError('Unexpected analytic arc order for the crown mapping')
    length = sum(a['length'] for a in selected)
    stations = {i/count for i in range(count+1)}
    before = 0.0
    for arc in selected[:-1]:
        before += arc['length']
        stations.add(before/length)
    for value in extra_stations:
        value = _finite(value, 'extra station')
        if not 0 <= value <= 1:
            raise ValueError('Extra crown station must be in [0, 1]')
        stations.add(value)
    result = []
    for s in sorted(stations):
        distance, before = s*length, 0.0
        arc = selected[-1]
        for possible in selected:
            arc = possible
            if distance <= before+arc['length']+1e-10:
                break
            before += arc['length']
        angle = math.radians(arc['start_deg']) + (distance-before)/arc['radius']
        cx, cy = arc['center']
        result.append({'s': s, 'segment_id': arc['id'],
                       'xy': (cx+arc['radius']*math.cos(angle),
                              cy+arc['radius']*math.sin(angle))})
    return result


def _clipped_vertical_chord(p, q, bottom, upper, trim0, trim1):
    """Clip one vertical plane to a linearly sampled sloping top boundary."""
    h0, h1 = min(upper, trim0), min(upper, trim1)
    if max(h0, h1) <= bottom+1e-10:
        return []
    if min(h0, h1) > bottom+1e-10:
        return [(p[0], p[1], bottom), (q[0], q[1], bottom),
                (q[0], q[1], h1), (p[0], p[1], h0)]
    # At the last sample band one end can terminate below its lower datum.
    # Interpolate the intersection in the same vertical plane, not a fake cap.
    t = (bottom-trim0)/(trim1-trim0)
    x, y = p[0]+t*(q[0]-p[0]), p[1]+t*(q[1]-p[1])
    if h0 <= bottom+1e-10:
        return [(x, y, bottom), (q[0], q[1], bottom), (q[0], q[1], h1)]
    return [(p[0], p[1], bottom), (x, y, bottom), (p[0], p[1], h0)]


def _normal(points):
    a = [points[1][i]-points[0][i] for i in range(3)]
    b = [points[2][i]-points[0][i] for i in range(3)]
    n = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    length = math.sqrt(sum(x*x for x in n))
    return tuple(x/length for x in n) if length > 1e-12 else (0, 0, 0)


def build_crown(ctx, geometry, candidate):
    """Build independent crown candidate surfaces and unknown frame proxies.

    Band XY is anchored to its upper gross-control chord and extended vertically
    downward, like the existing research shell.  Top cells are planar trapezoids
    or triangles.  Demonstration bands create small steps; no sealing/cap faces
    are added.  Neither the 4.5m pitch nor sampling count is a crown shop schedule.
    """
    config = ctx.config
    mid, high, low, end = _trim_controls(candidate)
    bottom = _finite(candidate.get('base_z_m', 542.0), 'base_z_m')
    pitch = _finite(candidate.get('band_pitch_display_m', 4.5), 'band_pitch_display_m')
    radius = _finite(candidate.get('frame_radius_display_m', .05), 'frame_radius_display_m')
    if bottom >= min(high,low,end) or pitch <= 0 or radius <= 0:
        raise ValueError('Crown base must be below its trim, and display pitch/radius positive')
    stations = open_profile_stations(geometry, config,
                candidate.get('horizontal_sample_count_display', 160), (mid,))
    tops = [trim_height(a['s'], candidate) for a in stations]
    source_id = candidate.get('source_id', candidate.get('source_id_candidate'))
    if not source_id:
        raise ValueError('Crown candidate must retain its evidence source ID')
    source_locator = candidate.get('source', {}).get('locator', 'PDFp13 Fig8; PDFp14 Fig9')
    uncertainty = ('Section anchors about ±1.5m; station-to-section mapping, geographic '
                   'orientation and interpolation are underdetermined. Entire K2 exclusion '
                   'is a conservative gap, not the actual V boundary. Crown fabrication '
                   'panels, grid and frames are unconfirmed. No as-built coordinates.')
    meta = {'source_ids': [source_id, 'B14_GEOM', 'CROWN_PHOTO_V4'], 'source_locator': source_locator,
            'evidence_level': '推导值', 'geometry_role': 'crown_candidate_panel',
            'formula': 'Open C1/K0/C2/K1/C0 arc length s; two explicit quadratic '
                       'trim branches; vertical planes at upper-band reference chords',
            'uncertainty': uncertainty, 'asbuilt_verified': False,
            'station_mapping_evidence': '待确认', 'fabrication_pattern_verified': False,
            'band_pitch_display_m': pitch, 'frame_radius_display_m': radius,
            'frame_dimension_evidence': '待确认', 'top_cap_present': False,
            'trim_controls_station_height': [[0, high], [mid, low], [1, end]]}
    verts, faces, frame_lines, edge_keys = [], [], [], set()
    panel_records = []
    maximum_control = max(high,low,end)
    number_bands = math.ceil((maximum_control-bottom)/pitch)
    for band in range(number_bands):
        lower, upper = bottom+band*pitch, min(bottom+(band+1)*pitch, maximum_control)
        xy = geometry.transform_profile([a['xy'] for a in stations], upper, config)
        for i in range(len(stations)-1):
            polygon = _clipped_vertical_chord(xy[i], xy[i+1], lower, upper, tops[i], tops[i+1])
            if not polygon:
                continue
            start = len(verts)
            faces.append(tuple(range(start, start+len(polygon))))
            verts.extend(polygon)
            panel_records.append({'face': len(faces)-1, 'band': band+1,
                                  'stations': [stations[i]['s'], stations[i+1]['s']],
                                  'kind': 'CROWN_FIT_TRIANGLE' if len(polygon)==3 else 'CROWN_FIT_PLANAR_POLYGON',
                                  'fabrication_pattern_verified': False})
            for a, b in zip(polygon, polygon[1:]+polygon[:1]):
                key = tuple(sorted(tuple(round(x, 8) for x in p) for p in (a, b)))
                if key not in edge_keys and math.dist(a, b)>1e-8:
                    edge_keys.add(key)
                    frame_lines.append([a, b])
    surface = ctx.mesh('CROWN_OPEN_SPLIT_PARABOLA_FIT_DERIVED', verts, faces,
                       '72_CROWN_DERIVED', 'glass', meta)
    frame_meta = {**meta, 'evidence_level': '待确认',
                  'geometry_role': 'crown_frame_display',
                  'formula': 'Candidate panel edge paths; tube radius is display only'}
    ctx.lines('CROWN_FRAME_UNCONFIRMED_GRID', frame_lines,
              '73_CROWN_FRAME_DISPLAY', radius, 'steel', frame_meta)
    interfaces = []
    for name, logic in [
        ('OUTER_VERTICAL_TRUSSES_TO_L118', 'Published load path; actual truss coordinates/sections absent'),
        ('RADIAL_STRUTS_TO_CORE', 'Published wind-load path; actual radial endpoints absent'),
        ('INNER_KICKER_TRUSSES_ABOVE_L129', 'Published inner support scheme; actual kicker members absent'),
        ('THREE_CORNER_BRACED_BAYS_AND_ALTERNATE_FLOOR_TRUSSES',
         'Published torsion scheme; exact corner bays and floor counter crosswalk absent'),
        ('INNER_COLLECTOR_AND_WINDOW_WASHING_TRACK', 'Published inner crown/track function; CAD surfaces absent')]:
        ctx.empty('CROWN_INTERFACE_'+name, (0, 0, bottom), '72_CROWN_DERIVED',
                  {**meta, 'evidence_level': '待确认', 'geometry_role': 'unresolved_interface',
                   'formula': logic, 'uncertainty': logic+'; '+uncertainty})
        interfaces.append(name)
    # SceneBuilder returns the real bpy object. Read the actual float32 mesh
    # after from_pydata/update; source buffers are only a pure-function test
    # fallback and are explicitly identified in the report.
    data = getattr(surface, 'data', None)
    actual_mesh = data is not None and hasattr(data, 'vertices') and hasattr(data, 'polygons')
    measured_verts = ([tuple(float(x) for x in v.co) for v in data.vertices]
                      if actual_mesh else verts)
    measured_faces = ([tuple(int(j) for j in f.vertices) for f in data.polygons]
                      if actual_mesh else faces)
    measurement_source = ('generated_bpy_base_mesh' if actual_mesh
                          else 'construction_buffers_pure_test_only')
    normals = [_normal([measured_verts[j] for j in face]) for face in measured_faces]
    maximum = max(p[2] for p in measured_verts)
    # The first band samples both unconnected rim boundaries. Read its actual
    # outer edge endpoints; no polygon is generated across the excluded corner.
    first_face = measured_faces[0]
    last_face_first_band = measured_faces[len(stations)-2]
    open_gap = math.dist(measured_verts[first_face[0]], measured_verts[last_face_first_band[1]])
    max_plane_error = 0.0
    for face, normal in zip(measured_faces, normals):
        first = measured_verts[face[0]]
        max_plane_error = max(max_plane_error, *(abs(sum((measured_verts[j][i]-first[i])*normal[i]
                                     for i in range(3))) for j in face))
    checks = [
        {'check': 'crown_highest_base_mesh_coordinate', 'passed': abs(maximum-maximum_control)<1e-3,
         'measured': maximum, 'meaning': 'Matches chosen crown endpoint; not surveyed crown accuracy'},
        {'check': 'crown_open_K2_guard', 'passed': open_gap>1 and all(a['segment_id']!='K2' for a in stations),
         'measured': {'actual_first_band_gap_m': open_gap, 'closing_face_count': 0},
         'meaning': 'Five arc path remains open; its gap is not the verified V groove'},
        {'check': 'crown_no_horizontal_cap_faces',
         'passed': all(abs(n[2])<1e-4 and sum(x*x for x in n)>.99 for n in normals),
         'measured': {'face_count': len(measured_faces), 'maximum_normal_z': max(abs(n[2]) for n in normals)},
         'meaning': 'Measured mesh faces are vertical side cells only'},
        {'check': 'crown_candidate_cells_coplanar', 'passed': max_plane_error<1e-3,
         'measured': max_plane_error, 'meaning': 'Planarity of candidate cells, not fabrication approval'},
        {'check': 'crown_base_elevation', 'passed': abs(min(p[2] for p in measured_verts)-bottom)<1e-3,
         'measured': min(p[2] for p in measured_verts), 'meaning': 'Crown coverage starts at configured reference datum'}]
    for check in checks:
        check['asbuilt_verified'] = False
        check['measurement_source'] = measurement_source
    report = {'component': 'open_crown_derived', 'source_ids': [source_id, 'B14_GEOM', 'CROWN_PHOTO_V4'],
              'evidence_level': '推导值', 'asbuilt_verified': False,
              'surface_role': 'crown_candidate_panel', 'station_mapping_evidence': '待确认',
              'checks': checks, 'software_checks_passed': all(a['passed'] for a in checks),
              'measurement_source': measurement_source,
              'software_coordinate_tolerance_m': 1e-3, 'software_normal_z_tolerance': 1e-4,
              'base_z_m': bottom, 'trim_controls_station_height': [[0,high],[mid,low],[1,end]],
              'candidate_cell_count': len(faces), 'band_count_display': number_bands,
              'station_count_display': len(stations), 'open_path_arc_order': ['C1','K0','C2','K1','C0'],
              'band_pitch_display_m': pitch, 'frame_radius_display_m': radius,
              'grid_evidence': '待确认：sampling and band pitch are display conventions, not the crown pattern',
              'upper_chord_anchor': 'Upper nominal band reference; stepped vertical approximation',
              'panel_records': panel_records, 'structural_interfaces': interfaces,
              'uncertainty': uncertainty, 'top_cap_present': False}
    ctx.component_results['crown_completion'] = report
    return report
