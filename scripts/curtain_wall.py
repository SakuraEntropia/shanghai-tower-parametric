"""Evidence-limited curtain wall geometry, independent of Blender imports.

The standard bands are a 2014 research derivation, not a floor or fabrication
schedule.  Each glass base-mesh face is a strictly vertical rectangle.  Frame
sections and horizontal closure surfaces are independent display proxies.
"""
from math import floor, sqrt


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def _mul(a, scalar):
    return tuple(x*scalar for x in a)


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def _length(a):
    return sqrt(_dot(a, a))


def _unit(a):
    length = _length(a)
    if length <= 1e-12:
        raise ValueError('Zero-length curtain-wall edge')
    return _mul(a, 1.0/length)


def rectangle_metrics(quad):
    """Check the actual proposed panel, not a best-fit replacement surface."""
    if len(quad) != 4:
        raise ValueError('A glass rectangle must have four vertices')
    edges = [_sub(quad[(i+1) % 4], quad[i]) for i in range(4)]
    lengths = [_length(edge) for edge in edges]
    if min(lengths) <= 1e-12:
        raise ValueError('Degenerate glass rectangle')
    normal = _unit(_cross(edges[0], edges[1]))
    return {
        'coplanarity_error_m': abs(_dot(_sub(quad[3], quad[0]), normal)),
        'vertical_normal_abs_z': abs(normal[2]),
        'vertical_edge_xy_error_m': max(_length(edge[:2]) for edge in (edges[1], edges[3])),
        'horizontal_edge_z_error_m': max(abs(edge[2]) for edge in (edges[0], edges[2])),
        'orthogonality_abs_cos': max(abs(_dot(edges[i], edges[(i+1) % 4])) /
                                     (lengths[i]*lengths[(i+1) % 4]) for i in range(4)),
        'opposite_edge_length_error_m': max(abs(lengths[0]-lengths[2]),
                                            abs(lengths[1]-lengths[3])),
        'width_m': lengths[0], 'height_m': lengths[1],
    }


def _rectangle(p0, p1, bottom_z, top_z):
    return [(p0[0], p0[1], bottom_z), (p1[0], p1[1], bottom_z),
            (p1[0], p1[1], top_z), (p0[0], p0[1], top_z)]


def _outward_normal(quad):
    tangent = _unit(_sub(quad[1], quad[0]))
    normal = _unit(_cross(tangent, (0.0, 0.0, 1.0)))
    midpoint = _mul(_add(quad[0], quad[1]), 0.5)
    return _mul(normal, -1.0) if _dot(normal, midpoint) < 0 else normal


def _buffers():
    return {'verts': [], 'faces': [], 'panel_ids': []}


def _append_face(buf, vertices, panel_index):
    start = len(buf['verts'])
    buf['verts'].extend(vertices)
    buf['faces'].append(tuple(range(start, start+len(vertices))))
    buf['panel_ids'].append(panel_index)


def _append_member(buf, p0, p1, width, depth, normal, panel_index):
    """A section proxy; its width/depth must never be labelled as verified."""
    axis = _unit(_sub(p1, p0))
    face_axis = _unit(_cross(normal, axis))
    half_width, half_depth = width/2.0, depth/2.0
    start = len(buf['verts'])
    for endpoint in (p0, p1):
        for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            buf['verts'].append(_add(endpoint, _add(_mul(face_axis, a*half_width),
                                                    _mul(normal, b*half_depth))))
    for face in ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
                 (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        buf['faces'].append(tuple(start+i for i in face))
        buf['panel_ids'].append(panel_index)


def _append_frame(buf, quad, face_width, horizontal_depth, vertical_depth,
                  normal, panel_index):
    for i in range(4):
        depth = horizontal_depth if i % 2 == 0 else vertical_depth
        _append_member(buf, quad[i], quad[(i+1) % 4], face_width, depth,
                       normal, panel_index)


def _emit(ctx, name, buf, collection, material, meta, glass_thickness=None):
    if not buf['faces']:
        return None
    attributes = {'panel_id': buf['panel_ids']}
    if glass_thickness is not None:
        attributes['panel_surface_role'] = [1]*len(buf['faces'])
    obj = ctx.mesh(name, buf['verts'], buf['faces'], collection, material, meta,
                   face_attributes=attributes)
    # Base faces stay traceable rectangles. Solidify is editable and separate
    # from the source geometry; evaluated sealing faces are not glass fronts.
    if glass_thickness is not None and hasattr(obj, 'modifiers'):
        modifier = obj.modifiers.new('NOMINAL_GLASS_THICKNESS_SOURCE_K16_Y19', 'SOLIDIFY')
        modifier.thickness = glass_thickness
        modifier.offset = 0.0
    return obj


def _meta(source_ids, role, formula, uncertainty, **extra):
    value = {'source_ids': source_ids, 'evidence_level': '推导值',
             'geometry_role': role, 'formula': formula, 'uncertainty': uncertainty,
             'asbuilt_verified': False, 'panel_index_attribute': 'panel_id',
             'panel_records_return_key': 'panel_records'}
    value.update(extra)
    return value


def _exclusion_markers(geometry, config, grid, excluded):
    """Sample segment membership conservatively, including endpoint tests."""
    details = geometry.sample_profile(config, count=max(552, len(grid)*8), return_details=True)
    if len(details) < 2:
        raise ValueError('The reference profile has insufficient control points')
    spacing = details[1]['s_m']-details[0]['s_m']
    perimeter = spacing*len(details)
    if spacing <= 0 or perimeter <= 0:
        raise ValueError('Profile arc-length order is invalid')
    markers = [point['s_m'] for point in details if point['segment_id'] == excluded]
    if not markers:
        raise ValueError('Unknown notch exclusion segment is absent from the profile')
    return markers, perimeter


def _excluded_edge(start, end, markers, perimeter, excluded):
    if excluded in start.get('span_segment_ids', []):
        return True
    if start['segment_id'] == excluded or end['segment_id'] == excluded:
        return True
    lo, hi = start['s_m'], end['s_m']
    if hi <= lo:
        hi += perimeter
    return any(lo <= mark <= hi or lo <= mark+perimeter <= hi for mark in markers)


def _interface(ctx, name, location, sources, reason, records, collection='80_CURTAIN_A_INTERFACES', **extra):
    meta = _meta(sources, 'unresolved_interface', '', reason,
                 evidence_level='待确认', **extra)
    ctx.empty(name, location, collection, meta)
    records.append({'name': name, 'location_m': list(location),
                    'source_ids': sources, 'evidence_level': '待确认',
                    'uncertainty': reason, **extra})


def _step_metrics(quad, next_quad, normal):
    shifts = [_sub(next_quad[i], quad[i+3 if i == 0 else 2]) for i in (0, 1)]
    tangent = _unit(_sub(quad[1], quad[0]))
    return {'step_width_normal_m': max(abs(_dot(shift, normal)) for shift in shifts),
            'step_shear_tangent_m': max(abs(_dot(shift, tangent)) for shift in shifts),
            'step_endpoint_displacement_m': max(_length(shift) for shift in shifts)}


def _build_standard(ctx, geometry, records, interfaces, checks, glass_thickness):
    config, curtain = ctx.config, ctx.config['curtain']
    count = int(curtain['half_panel_count'])
    groups = list(curtain['half_groups'])
    if sum(groups) != count:
        raise ValueError('Curtain-wall half groups do not sum to the half-panel count')
    if curtain['create_glass_fins_main']:
        raise ValueError('Main-tower glass-fin mapping is unresolved; use the historical sample')
    if curtain['anchor_line'] != 'upper_gross_control_chord':
        raise ValueError('Only the documented upper-control-line convention is implemented')
    grid = geometry.standard_grid(config, half_count=count)
    if len(grid) != count*6:
        raise ValueError('Standard grid must contain six half-segments')
    excluded = curtain['excluded_segment']
    markers, perimeter = _exclusion_markers(geometry, config, grid, excluded)
    valid_edges = [i for i in range(len(grid)) if not _excluded_edge(
        grid[i], grid[(i+1) % len(grid)], markers, perimeter, excluded)]
    pitch = float(curtain['nominal_band_pitch_m'])
    if pitch <= 0:
        raise ValueError('Curtain-wall demonstration pitch must be positive')
    boundaries = curtain['standard_zone_reference_boundaries_m']
    zones = []
    for zone_index, (bottom, top) in enumerate(zip(boundaries, boundaries[1:]), 2):
        band_count = floor((top-bottom+1e-9)/pitch)
        zone_glass, zone_frames, zone_steps = _buffers(), _buffers(), _buffers()
        anchor_points = [geometry.transform_profile([point['xy'] for point in grid],
                         bottom+(band+1)*pitch, config) for band in range(band_count)]
        for band in range(band_count):
            lower_z, upper_z = bottom+band*pitch, bottom+(band+1)*pitch
            for i in valid_edges:
                j = (i+1) % len(grid)
                quad = _rectangle(anchor_points[band][i], anchor_points[band][j], lower_z, upper_z)
                normal = _outward_normal(quad)
                metrics = rectangle_metrics(quad)
                panel_index = len(records)
                panel_id = f'CWA_2014RESEARCH_Z{zone_index:02d}_B{band+1:03d}_P{i+1:03d}'
                record = {'panel_index': panel_index, 'panel_id': panel_id,
                          'zone': zone_index, 'band_id': band+1, 'floor_id': None,
                          'band_is_true_floor': False,
                          'geometry_version': config['selected_geometry_version'],
                          'rule_id': 'MC03_MC04', 'type_id': 'STANDARD_RECTANGLE_DERIVED',
                          'evidence_level': '推导值', 'source_ids': ['B14_GEOM', 'Y19'],
                          'source_locator': 'B14_GEOM pp16–18; Y19 standard rectangular glass',
                          'grid_index': i,
                          'half': grid[i].get('half_index', grid[i].get('half')),
                          'half_direction': grid[i].get('half_direction'),
                          'group': grid[i].get('group_index', grid[i].get('group')),
                          'segment_ids': grid[i].get('span_segment_ids',
                                                     [grid[i]['segment_id'], grid[j]['segment_id']]),
                          'source_arc_positions_m': [grid[i]['s_m'], grid[j]['s_m']],
                          'z_bottom_m': lower_z, 'z_top_m': upper_z,
                          'vertices_control_plane_m': [list(point) for point in quad],
                          'anchor_line': 'upper_gross_control_chord',
                          'nominal_glass_thickness_m': glass_thickness,
                          'thickness_reference': 'control plane at mid-thickness; derived placement',
                          'width_kind': 'gross control chord; clear fabrication width unresolved',
                          'frame_dimension_evidence': 'DISPLAY_UNKNOWN',
                          'frame_face_width_display_m': curtain['frame_face_width_display_m'],
                          'frame_depth_display_m': curtain['horizontal_frame_depth_display_m'],
                          'asbuilt_verified': False,
                          'uncertainty': 'Equal arc spacing, nominal demonstration bands and upper '
                          'anchoring are derivations; true floor/panel schedule, net edges and V notch missing',
                          **metrics}
                _append_face(zone_glass, quad, panel_index)
                _append_frame(zone_frames, quad, curtain['frame_face_width_display_m'],
                              curtain['horizontal_frame_depth_display_m'],
                              curtain['horizontal_frame_depth_display_m'], normal, panel_index)
                if band+1 < band_count:
                    next_quad = _rectangle(anchor_points[band+1][i], anchor_points[band+1][j],
                                           upper_z, upper_z+pitch)
                    record.update(_step_metrics(quad, next_quad, normal))
                    _append_face(zone_steps, [quad[3], quad[2], next_quad[1], next_quad[0]], panel_index)
                else:
                    record['step_width_normal_m'] = None
                records.append(record)
                checks.append(metrics)
        common = _meta(['B14_GEOM', 'Y19'], 'glass_panel_derived',
                       '6 half profiles × 23 equal-arc subdivisions; upper chord extruded vertically downward',
                       'MC03/MC04: no actual floor schedule, net glass edges or final panel mapping',
                       zone=zone_index, band_pitch_m=pitch, true_floor_schedule=False,
                       geometry_version=config['selected_geometry_version'],
                       nominal_glass_thickness_m=glass_thickness,
                       thickness_source_ids=['K16', 'Y19'], reference_line_kind=config['profile']['reference_line_kind'])
        _emit(ctx, f'CWA_Z{zone_index:02d}_GLASS_DERIVED', zone_glass, '80_CURTAIN_A_GLASS',
              'glass', common, glass_thickness)
        frame_meta = dict(common, geometry_role='frame_display_unknown', evidence_level='待确认',
                          section_dimension_evidence='DISPLAY_UNKNOWN', section_source_ids=[],
                          face_width_display_m=curtain['frame_face_width_display_m'],
                          horizontal_and_vertical_depth_display_m=curtain['horizontal_frame_depth_display_m'],
                          formula='Unknown sections displayed as rectangular bars on derived panel edges',
                          uncertainty='50mm face / 100mm depth are display proxies; no extrusion profile or gasket schedule')
        _emit(ctx, f'CWA_Z{zone_index:02d}_FRAME_DISPLAY_UNKNOWN', zone_frames,
              '80_CURTAIN_A_FRAMES_UNKNOWN', 'steel', frame_meta)
        step_meta = dict(common, geometry_role='horizontal_step_closure_proxy', evidence_level='待确认',
                         formula='Coplanar horizontal surface between adjacent derived vertical bands',
                         closure_thickness_m=None,
                         uncertainty='Step geometry derives from bands; actual closure profile, plate thickness and joints unavailable')
        _emit(ctx, f'CWA_Z{zone_index:02d}_STEP_CLOSURE_UNKNOWN', zone_steps,
              '80_CURTAIN_A_STEPS_UNKNOWN', 'guide', step_meta)
        remainder_bottom = bottom+band_count*pitch
        if top-remainder_bottom > 1e-8:
            _interface(ctx, f'CWA_Z{zone_index:02d}_REMAINDER_UNRESOLVED',
                       (0, 0, (remainder_bottom+top)/2), ['B14_GEOM'],
                       'Reference-zone remainder left empty; not interpreted as a real equipment/floor interval',
                       interfaces, z_range_m=[remainder_bottom, top], gap_kind='nominal_band_remainder')
        zones.append({'zone': zone_index, 'reference_z_range_m': [bottom, top],
                      'nominal_band_count': band_count, 'panels_per_complete_band': len(valid_edges),
                      'unresolved_remainder_m': top-remainder_bottom,
                      'skipped_grid_edges_per_band': len(grid)-len(valid_edges)})
    return zones, len(grid)-len(valid_edges)


def _build_historical_detail(ctx, geometry, records, checks, glass_thickness):
    config, curtain = ctx.config, ctx.config['curtain']
    detail = curtain['detail_sample']
    version = detail['source_version']
    grid = geometry.sample_profile(config, count=144, return_details=True)
    excluded = curtain['excluded_segment']
    markers, perimeter = _exclusion_markers(geometry, config, grid, excluded)
    panel_count, bands = int(detail['sample_panel_count']), int(detail['bands'])
    pitch, source_bottom = float(detail['band_pitch_m']), float(detail['z_bottom_m'])
    if min(panel_count, bands) <= 0 or pitch <= 0:
        raise ValueError('Invalid historical sample size')
    start = next((i for i in range(len(grid)-panel_count) if all(not _excluded_edge(
        grid[j], grid[j+1], markers, perimeter, excluded) for j in range(i, i+panel_count))), None)
    if start is None:
        raise ValueError('No safe historical sample outside the unresolved notch')
    selected = grid[start:start+panel_count+1]
    anchors = [geometry.transform_profile([point['xy'] for point in selected],
               source_bottom+(band+1)*pitch, config, version=version) for band in range(bands)]
    centroid = tuple(sum(point[axis] for anchor in anchors for point in anchor) /
                     (len(anchors)*len(selected)) for axis in (0, 1))
    location = detail['location_m']
    translation = (location[0]-centroid[0], location[1]-centroid[1], location[2]-source_bottom)
    glass, frames, fins, steps = _buffers(), _buffers(), _buffers(), _buffers()
    bounds_points = []
    for band in range(bands):
        for i in range(panel_count):
            source_quad = _rectangle(anchors[band][i], anchors[band][i+1],
                                     source_bottom+band*pitch, source_bottom+(band+1)*pitch)
            normal = _outward_normal(source_quad)
            quad = [_add(point, translation) for point in source_quad]
            panel_index = len(records)
            metrics = rectangle_metrics(quad)
            _append_face(glass, quad, panel_index)
            _append_frame(frames, quad, curtain['frame_face_width_display_m'],
                          curtain['horizontal_frame_depth_display_m'], curtain['mullion_depth_m'],
                          normal, panel_index)
            for edge_index in ([0, 1] if i == panel_count-1 else [0]):
                p0, p1 = quad[edge_index], quad[3 if edge_index == 0 else 2]
                fin_center_offset = _mul(normal, -(curtain['mullion_depth_m']+curtain['fin_depth_m'])/2)
                _append_member(fins, _add(p0, fin_center_offset), _add(p1, fin_center_offset),
                               curtain['fin_thickness_m'], curtain['fin_depth_m'], normal, panel_index)
            record = {'panel_index': panel_index,
                      'panel_id': f'CWA_HIST2010_DISPLAY_B{band+1:02d}_P{i+1:02d}',
                      'zone': None, 'band_id': band+1, 'floor_id': None,
                      'band_is_true_floor': False, 'geometry_version': version,
                      'rule_id': 'MC05_MC09_HISTORICAL_SAMPLE',
                      'type_id': 'LOCAL_RECTANGLE_DERIVED_NOT_FINAL_A1_A2',
                      'evidence_level': '推导值', 'source_ids': ['G01'], 'source_locator': 'G01 pp11,15',
                      'grid_index': start+i, 'segment_ids': [selected[i]['segment_id'], selected[i+1]['segment_id']],
                      'source_arc_positions_m': [selected[i]['s_m'], selected[i+1]['s_m']],
                      'source_z_bottom_m': source_bottom+band*pitch,
                      'source_z_top_m': source_bottom+(band+1)*pitch,
                      'z_bottom_m': quad[0][2], 'z_top_m': quad[2][2],
                      'vertices_control_plane_m': [list(point) for point in quad],
                      'source_vertices_control_plane_m': [list(point) for point in source_quad],
                      'display_translation_m': list(translation), 'crossversion_sample': True,
                      'asbuilt_verified': False, 'nominal_glass_thickness_m': glass_thickness,
                      'frame_dimension_evidence': 'G01 depth; DISPLAY_UNKNOWN face/horizontal section',
                      'uncertainty': '144 equal-arc sampling is derived; not verified original point coordinates; '
                      'independent translated history sample, unknown net glass edges and frame profiles',
                      **metrics}
            if band+1 < bands:
                next_quad = [_add(point, translation) for point in _rectangle(
                    anchors[band+1][i], anchors[band+1][i+1],
                    source_bottom+(band+1)*pitch, source_bottom+(band+2)*pitch)]
                record.update(_step_metrics(quad, next_quad, normal))
                _append_face(steps, [quad[3], quad[2], next_quad[1], next_quad[0]], panel_index)
            else:
                record['step_width_normal_m'] = None
            records.append(record)
            checks.append(metrics)
            bounds_points.extend(quad)
    collection = '82_HISTORICAL_CWA_2010_SAMPLE'
    meta = _meta(['G01'], 'glass_panel_historical_derived',
                 '2010 curve state; six derived 144-grid chords × three vertical bands; DISPLAY translation',
                 'Cross-version historical sample; equal arc control points and net glass edges unverified',
                 geometry_version=version, display_translation_m=list(translation),
                 crossversion_sample=True, source_z_bottom_m=source_bottom,
                 nominal_glass_thickness_m=glass_thickness, thickness_source_ids=['K16', 'Y19'])
    _emit(ctx, 'HIST2010_GLASS_DERIVED', glass, collection, 'glass_detail', meta, glass_thickness)
    _emit(ctx, 'HIST2010_FRAME_SECTION_UNKNOWN', frames, collection, 'steel',
          dict(meta, geometry_role='historical_frame_section_proxy', evidence_level='待确认',
               vertical_depth_source_m=curtain['mullion_depth_m'], section_source_ids=['G01'],
               face_width_dimension_evidence='DISPLAY_UNKNOWN',
               horizontal_depth_dimension_evidence='DISPLAY_UNKNOWN'))
    _emit(ctx, 'HIST2010_GLASS_FINS_SOURCE_RANGE_MAX_SAMPLE', fins, collection, 'glass_detail',
          dict(meta, geometry_role='historical_glass_fin_sample',
               fin_thickness_source_m=curtain['fin_thickness_m'],
               fin_depth_m=curtain['fin_depth_m'], fin_depth_kind='source maximum selected for display',
               uncertainty='26mm thickness / up to 300mm depth from G01; sample depth and node positions not an as-built assignment'))
    _emit(ctx, 'HIST2010_STEP_CLOSURE_UNKNOWN', steps, collection, 'guide',
          dict(meta, geometry_role='historical_step_closure_proxy', evidence_level='待确认',
               uncertainty='Independent horizontal closure surface; profile and thickness unavailable'))
    bounds = {'min_m': [min(point[a] for point in bounds_points) for a in range(3)],
              'max_m': [max(point[a] for point in bounds_points) for a in range(3)]}
    target = [(lo+hi)/2 for lo, hi in zip(bounds['min_m'], bounds['max_m'])]
    return bounds, target


def build_curtain_wall(ctx, geometry_module):
    """Create A research bands, unresolved B/exception interfaces and sample."""
    config, curtain = ctx.config, ctx.config['curtain']
    records, interfaces, checks = [], [], []
    glass_layers = ctx.param('cw_glass_outer')['value']
    if not glass_layers or any(layer is None for layer in glass_layers):
        raise ValueError('Nominal outer glass layers must remain explicit')
    glass_thickness = sum(float(layer) for layer in glass_layers)/1000.0
    zones, skipped = [], 0
    if config['components']['curtain_A']:
        zones, skipped = _build_standard(ctx, geometry_module, records, interfaces, checks, glass_thickness)
        display_middle_z = sum((curtain['standard_zone_reference_boundaries_m'][0],
                                curtain['standard_zone_reference_boundaries_m'][-1]))/2.0
        _interface(ctx, 'CWA_V_NOTCH_K2_UNRESOLVED', (0, 0, display_middle_z), ['G01', 'B14_GEOM', 'Y19'],
                   'Whole K2 mother-arc exclusion is conservative; actual V cut, panel types and LED mullions unverified',
                   interfaces, excluded_segment=curtain['excluded_segment'],
                   exclusion_is_actual_notch_boundary=False)
        _interface(ctx, 'CWA_Z1_ENTRANCE_UNRESOLVED', (0, 0, curtain['standard_zone_reference_boundaries_m'][0]),
                   ['G01', 'Y19'], 'Z1 entrance, base geometry and local panels need a separate schedule', interfaces)
        _interface(ctx, 'CWA_Z9_CROWN_UNRESOLVED', (0, 0, curtain['standard_zone_reference_boundaries_m'][-1]),
                   ['G01', 'B14_GEOM'], 'No standard bands above 542m; crown cut, panels and final fins/mullions unverified', interfaces)
        _interface(ctx, 'CWA_FRIT_PANEL_TYPES_OPENINGS_UNRESOLVED', (0, 0, 0), ['G01', 'Y19'],
                   'No frit mask, 1125/600mm band assignment, eight-type map or equipment/BMU opening schedule', interfaces)
        _interface(ctx, 'CWA_141_COUNT_ONLY_VERSION_INTERFACE', (0, 0, 0), ['C12'],
                   '141 panels/level reported; source control points and complete algorithm not obtained', interfaces,
                   candidate_panel_count=141, geometry_version='yuanda_2012_count_only')
    if config['components']['curtain_B_interfaces']:
        for zone in range(2, 9):
            bottom, top = curtain['standard_zone_reference_boundaries_m'][zone-2:zone]
            _interface(ctx, f'CWB_Z{zone:02d}_RADIUS_GRID_FIRE_UNRESOLVED', (0, 0, (bottom+top)/2),
                       ['G01', 'Y19'], 'Vertical cylinder per zone; radius, closure grid, tab and fire-glass '
                       'mapping unknown. Early 1m module is not net glass width; 1.5m is office planning.',
                       interfaces, collection='81_CURTAIN_B_INTERFACES', early_module_candidate_m=1.0)
    detail_bounds, detail_target = None, None
    if config['components']['detail_samples']:
        detail_bounds, detail_target = _build_historical_detail(ctx, geometry_module, records, checks, glass_thickness)
    numeric = {'panel_count': len(records),
               'main_panel_count': sum(not record.get('crossversion_sample', False) for record in records),
               'historical_sample_panel_count': sum(record.get('crossversion_sample', False) for record in records),
               'checks_are_generation_checks_not_asbuilt_validation': True}
    if checks:
        for key in ('coplanarity_error_m', 'vertical_normal_abs_z', 'vertical_edge_xy_error_m',
                    'horizontal_edge_z_error_m', 'orthogonality_abs_cos', 'opposite_edge_length_error_m'):
            numeric['max_'+key] = max(check[key] for check in checks)
        for key in ('width_m', 'height_m'):
            numeric['min_'+key] = min(check[key] for check in checks)
            numeric['max_'+key] = max(check[key] for check in checks)
        step_widths = [record['step_width_normal_m'] for record in records
                       if record.get('step_width_normal_m') is not None]
        numeric['min_step_width_normal_m'] = min(step_widths) if step_widths else None
        numeric['max_step_width_normal_m'] = max(step_widths) if step_widths else None
    return {'panel_records': records, 'numeric_checks': numeric, 'zone_records': zones,
            'gap_interfaces': interfaces, 'excluded_edges_per_band': skipped,
            'detail_bounds': detail_bounds, 'detail_target': detail_target,
            'uncertainty': 'Research standard bands plus independent history sample; final floor, '
            'glass/frame fabrication, V notch, crown, B grid and frit maps remain unverified'}
