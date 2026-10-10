"""Editable crown roof and steel load-path approximation from NTUA Fig8/9.

The source establishes the open crown and structural topology. Published image
samples establish candidate elevations only. Circumferential mapping, members,
section sizes, roof radius and apertures below remain explicitly unconfirmed.
"""
import math
from crown_completion import open_profile_stations, trim_height


def build_crown_detail(ctx, geometry, candidate, assembly):
    given = assembly.get('crown', {})
    anchors = {v['id']: v['z_m'] for v in candidate.get('anchors', [])}
    p = {'roof_z_m': anchors.get('main_inner_roof', 601.099),
         'support_z_m': anchors.get('crown_support_base', 546.993),
         'roof_radius_fit_m': 17.0, 'roof_core_aperture_half_x_fit_m': 5.5,
         'roof_core_aperture_half_y_fit_m': 15.5,
         'collector_radial_divisions_display': 8, 'roof_arc_samples_display': 120,
         'truss_count_display': 24, 'truss_bay_height_display_m': 4.5,
         'truss_radial_depth_fit_m': 1.2, 'main_chord_radius_display_m': .15,
         'web_radius_display_m': .08, 'radial_radius_display_m': .10,
         'ring_radius_display_m': .12, 'central_steel_frame_radius_fit_m': 6.0,
         'kicker_height_fit_m': 9.0, 'lower_frame_top_candidate_m': 542.0,
         'lower_frame_radius_candidate_m': 23.25,
         'lower_frame_column_inset_candidate_m': 2.0,
         'lower_frame_pair_offset_candidate_m': 4.7,
         'rim_coping_radius_display_m': .12}
    p.update({key:given[key] for key in p if key in given})
    for key, value in p.items():
        if isinstance(value, bool) or not math.isfinite(float(value)) or float(value) <= 0:
            raise ValueError('Positive finite crown candidate parameter required: '+key)
    for key in ('collector_radial_divisions_display','roof_arc_samples_display','truss_count_display'):
        if int(p[key]) != p[key] or p[key] < 2:
            raise ValueError('Integer crown sampling count required: '+key)
    if p['roof_radius_fit_m'] <= math.hypot(p['roof_core_aperture_half_x_fit_m'],
                                         p['roof_core_aperture_half_y_fit_m']):
        raise ValueError('Central aperture must fit inside candidate roof circle')
    source_id = candidate.get('source_id', candidate.get('source_id_candidate'))
    if not source_id:
        raise ValueError('Crown evidence source ID required')
    meta = {'source_ids': [source_id, 'B14_GEOM', 'CROWN_PHOTO_V4'], 'source_locator':
            'NTUA author稿 PDFp13 Fig8 Gensler剖面 / PDFp14 Fig9 current scheme; B14 p19',
            'evidence_level': '待确认', 'approximation': True, 'asbuilt_verified': False,
            'geometry_role': 'crown_roof_and_trusses_candidate',
            'formula': 'Source load paths + image-normalized elevations; replaceable roof/radial member layout',
            'uncertainty': 'Roof radius, opening, circumferential mapping, chord/web sections, '
                           'truss count, deployment and joints are unconfirmed candidate geometry. '
                           'Elevation samples ±1.5m with unbounded drawing/version systematic error.',
            'fabrication_verified': False, 'source_topology_confirmed': True,
            'used_parameters': p, 'station_mapping_evidence': '待确认'}
    stations = open_profile_stations(geometry, ctx.config, int(p['roof_arc_samples_display']), (.5,))
    roof_z = float(p['roof_z_m'])
    outer, inner, hole = [], [], []
    for station in stations:
        top = trim_height(station['s'], candidate)
        out = geometry.transform_profile([station['xy']], top, ctx.config)[0]
        ref = geometry.transform_profile([station['xy']], roof_z, ctx.config)[0]
        # Radial roof loft stays in the rim's current azimuth. Using the whole
        # mother's roof-level angle at the inner end introduced another angular
        # shear along each loft, which the aerial photo does not establish.
        phi = math.atan2(out[1], out[0])
        c, s = math.cos(phi), math.sin(phi)
        r = min(p['roof_core_aperture_half_x_fit_m']/max(abs(c),1e-10),
                p['roof_core_aperture_half_y_fit_m']/max(abs(s),1e-10))
        outer.append(out)
        inner.append((p['roof_radius_fit_m']*c,p['roof_radius_fit_m']*s,roof_z))
        hole.append((r*c,r*s,roof_z))
    # Central roof and curved collector keep both the core aperture and K2 gap.
    # There is no surface covering the crown at632m.
    deck_verts, deck_faces = [], []
    collector_verts, collector_faces = [], []
    divisions = int(p['collector_radial_divisions_display'])
    for i in range(len(stations)-1):
        q = len(deck_verts)
        deck_verts.extend((hole[i],inner[i],inner[i+1],hole[i+1]))
        deck_faces.extend(((q,q+1,q+2),(q,q+2,q+3)))
        for j in range(divisions):
            cell = []
            for k,u in ((i,j/divisions),(i+1,j/divisions),
                        (i+1,(j+1)/divisions),(i,(j+1)/divisions)):
                a,b = inner[k],outer[k]
                cell.append((a[0]+u*(b[0]-a[0]), a[1]+u*(b[1]-a[1]),
                             roof_z+u*u*(b[2]-roof_z)))
            q = len(collector_verts)
            collector_verts.extend(cell)
            collector_faces.extend(((q,q+1,q+2),(q,q+2,q+3)))
    roof_obj = ctx.mesh('CROWN_MAIN_ROOF_601_CANDIDATE_WITH_CORE_APERTURE',
                       deck_verts,deck_faces,'74_CROWN_ROOF_CANDIDATE','steel',
                       {**meta,'geometry_role':'crown_lower_main_roof_candidate'})
    collector_obj = ctx.mesh('CROWN_OPEN_CURVED_COLLECTOR_TO_RIM_CANDIDATE',
                       collector_verts,collector_faces,'74_CROWN_ROOF_CANDIDATE','glass',
                       {**meta,'geometry_role':'crown_open_collector_roof_candidate',
                        'formula':'Radial quadratic z(u)=roof_z+u²*(rim_z(s)-roof_z); mapping unconfirmed'})
    grid = open_profile_stations(geometry,ctx.config,int(p['truss_count_display']),(.5,))
    def point(station,z,inset=0):
        x,y,z = geometry.transform_profile([station['xy']],z,ctx.config)[0]
        r = math.hypot(x,y)
        return (x*(1-inset/r),y*(1-inset/r),z)
    def central(station,z):
        x,y,z = point(station,z)
        r = math.hypot(x,y)
        return (x*p['central_steel_frame_radius_fit_m']/r,
                y*p['central_steel_frame_radius_fit_m']/r,z)
    chords,webs,radials,kickers,rings,corners = [],[],[],[],[],[]
    bay = p['truss_bay_height_display_m']
    depth = p['truss_radial_depth_fit_m']
    base = p['support_z_m']
    crest_station = candidate.get('implementation_candidate',candidate)['station_height_m'][1][0]
    maximum = max(trim_height(s,candidate) for s in (0,crest_station,1))
    if not base < roof_z < min(trim_height(s,candidate) for s in (0,crest_station,1)):
        raise ValueError('Support, roof and crown trim elevations are inconsistent')
    for station in grid:
        top = trim_height(station['s'],candidate)
        levels = [base+j*bay for j in range(math.ceil((top-base)/bay))]+[top]
        chords.extend(([point(station,z) for z in levels],
                       [point(station,z,depth) for z in levels]))
        for j,(z0,z1) in enumerate(zip(levels,levels[1:])):
            webs.append([point(station,z0,depth if j%2 else 0),
                         point(station,z1,0 if j%2 else depth)])
            webs.append([point(station,z0),point(station,z0,depth)])
            if j%2==0 and z0<=roof_z:
                radials.append([central(station,z0),point(station,z0,depth)])
        upper = min(top,roof_z+p['kicker_height_fit_m'])
        kickers.extend(([central(station,roof_z),point(station,upper,depth)],
                        [point(station,roof_z,depth),point(station,upper,depth)]))
    for j in range(math.ceil((maximum-base)/(2*bay))):
        z = base+j*2*bay
        # Consecutive surviving stations only: no ring bridges the K2 gap.
        for a,b in zip(grid,grid[1:]):
            if z < min(trim_height(a['s'],candidate),trim_height(b['s'],candidate)):
                rings.extend(([point(a,z),point(b,z)],
                              [point(a,z,depth),point(b,z,depth)],
                              [point(a,z),point(b,z,depth)]))
    for bearing in (0,120,240):
        angle = math.radians(bearing)
        selected = min(range(len(grid)),key=lambda i:
                       abs(math.atan2(math.sin(math.atan2(grid[i]['xy'][1],grid[i]['xy'][0])-angle),
                                      math.cos(math.atan2(grid[i]['xy'][1],grid[i]['xy'][0])-angle))))
        a,b = grid[max(0,selected-1)],grid[min(len(grid)-1,selected+1)]
        top = min(trim_height(a['s'],candidate),trim_height(b['s'],candidate))
        for j in range(math.ceil((top-base)/bay)):
            z0,z1 = base+j*bay,min(base+(j+1)*bay,top)
            corners.append([point(a,z0),point(b,z1)])
    # The two source-local boundary assignments do not share a published node
    # crosswalk. Explicit transition members fill the candidate gap; they are
    # editable approximations, never claimed installation coordinates.
    lower_z = p['lower_frame_top_candidate_m']
    column_axis = p['lower_frame_radius_candidate_m']-p['lower_frame_column_inset_candidate_m']
    pair = p['lower_frame_pair_offset_candidate_m']
    if not lower_z < base or column_axis <= 0:
        raise ValueError('Lower candidate frame must lie below the crown support')
    column_tops = [(sign*column_axis,offset,lower_z)
                   for sign in (-1,1) for offset in (-pair,pair)]
    column_tops += [(offset,sign*column_axis,lower_z)
                    for sign in (-1,1) for offset in (-pair,pair)]
    column_tops.sort(key=lambda q:math.atan2(q[1],q[0]))
    transition=[]
    for station in grid:
        foot=point(station,base)
        support=min(column_tops,key=lambda q:math.dist(foot,q))
        transition.append([support,foot])
        transition.append([support,point(station,base,depth)])
    # Non-rotating eight-column belt and open crown base ring are tied by the
    # radial/diagonal members; only the column belt closes, never the K2 crown.
    transition.append(column_tops+[column_tops[0]])
    transition.append([point(station,base) for station in grid])
    transition.append([point(station,base,depth) for station in grid])
    objects=[roof_obj.name,collector_obj.name]
    coping=ctx.lines('CROWN_OPEN_RIM_COPING_CANDIDATE',[outer],
                    '74_CROWN_ROOF_CANDIDATE',p['rim_coping_radius_display_m'],'steel',
                    {**meta,'geometry_role':'crown_open_rim_coping_candidate',
                     'formula':'Open lip-to-crest-to-lip outline; coping radius is display only'})
    objects.append(coping.name)
    for name,paths,radius,logic in [
        ('OUTER_DOUBLE_CHORD_TRUSSES',chords,p['main_chord_radius_display_m'],'Outer trusses carry gravity to L118'),
        ('OUTER_TRUSS_WEBS',webs,p['web_radius_display_m'],'Approximate web deployment; no node dimensions'),
        ('RADIAL_CORE_STEEL_FRAME_STRUTS',radials,p['radial_radius_display_m'],'Wind loads transfer to central frame'),
        ('INNER_KICKER_TRUSSES_ABOVE_ROOF',kickers,p['main_chord_radius_display_m'],'Kicker support above L129 roof'),
        ('ALTERNATE_LEVEL_OPEN_RING_TRUSSES',rings,p['ring_radius_display_m'],'Source says every other floor; nominal9m display'),
        ('LOWER_542_TO_SUPPORT_TRANSITION',transition,p['radial_radius_display_m'],
         'Candidate bridge from non-rotating eight-column frame at542m to crown support; nodes unconfirmed'),
        ('THREE_CORNER_BRACED_BAYS',corners,p['web_radius_display_m'],'Three corner torsional bays; local placement approximate')]:
        obj=ctx.lines('CROWN_'+name+'_CANDIDATE',paths,'75_CROWN_STEEL_CANDIDATE',radius,'steel',
                      {**meta,'geometry_role':'crown_steel_candidate','load_path':logic,
                       'member_radius_display_m':radius,'installed_coordinate_verified':False})
        objects.append(obj.name)
    actual_deck=[tuple(float(x) for x in v.co) for v in roof_obj.data.vertices]
    actual_collector=[tuple(float(x) for x in v.co) for v in collector_obj.data.vertices]
    checks=[{'name':'crown_lower_roof_entity','passed':len(actual_deck)>0 and
             all(abs(v[2]-roof_z)<.001 for v in actual_deck),'actual':len(actual_deck)},
            {'name':'crown_curved_collector_entity','passed':len(actual_collector)>0 and
             max(v[2] for v in actual_collector)>roof_z+1,'actual':len(actual_collector)},
            {'name':'crown_steel_load_paths_entities','passed':all(len(v)>0 for v in
             (chords,webs,radials,kickers,rings,corners)),
             'actual':{'chords':len(chords),'webs':len(webs),'radials':len(radials),
                       'kickers':len(kickers),'ring_members':len(rings),'corner_members':len(corners)}},
            {'name':'crown_lower_transition_entities','passed':len(transition)>3 and
             all(abs(paths[0][2]-lower_z)<1e-8 and abs(paths[-1][2]-base)<1e-8
                 for paths in transition[:-3]),
             'actual':{'member_paths':len(transition),'bottom_candidate_m':lower_z,
                       'top_candidate_m':base,'gap_bridged_m':base-lower_z}}]
    return {'objects':objects,'checks':checks,'used_parameters':p,'approximation':True,
            'evidence_level':'待确认','asbuilt_verified':False,'source_ids':meta['source_ids'],
            'roof_is_at_601_not_flat_632_cap':True,'K2_gap_preserved':True,
            'uncertainty':meta['uncertainty']}
