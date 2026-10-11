"""Source-informed crown interfaces; all layout dimensions remain candidates.

Actual Gensler aerial, published National Geographic2023-06-09, resolves
relationships absent from earlier renders. It does not supply 3D coordinates.
"""
import math
from crown_completion import crown_profile_stations, trim_height
from floors_v3 import annular_slab


def roof_slot_polygon(p, count=48):
    """One connected rectangular recess ending in a semicircular open aperture."""
    r=p['deck_aperture_half_width_fit_m'];y=p['deck_aperture_round_center_y_fit_m']
    top=p['deck_aperture_rect_upper_y_fit_m']
    if not y < 0 < top or r <= 0:
        raise ValueError('Roof slot must enclose origin and have positive width')
    return [(-r,top),(r,top),(r,y)]+[(r*math.cos(-math.pi*i/count),y+r*math.sin(-math.pi*i/count))
           for i in range(1,count+1)]+[(-r,top)]


def rim_point(geometry,config,station,candidate,inset=0,z=None):
    z=trim_height(station['s'],candidate) if z is None else z
    x,y,z=geometry.transform_profile([station['xy']],z,config)[0]
    radius=math.hypot(x,y)
    if inset>=radius:raise ValueError('Crown inset exceeds local radius')
    return (x*(1-inset/radius),y*(1-inset/radius),z)


def collector_point(geometry,config,station,candidate,p,roof_z,u):
    """Same-azimuth inner face; dense ruled grid follows source-visible steep bowl."""
    outer=rim_point(geometry,config,station,candidate,p['return_width_fit_m'])
    phi=math.atan2(outer[1],outer[0]);inner=(p['deck_radius_fit_m']*math.cos(phi),
        p['deck_radius_fit_m']*math.sin(phi),roof_z)
    return (inner[0]+u*(outer[0]-inner[0]),inner[1]+u*(outer[1]-inner[1]),
            roof_z+u*u*(outer[2]-roof_z))


def _quad_mesh(ctx,name,quads,collection,material,meta):
    vertices=[];faces=[]
    for q in quads:
        i=len(vertices);vertices.extend(q);faces.append(tuple(range(i,i+len(q))))
    return ctx.mesh(name,vertices,faces,collection,material,meta)


def _actual(obj, fallback):
    data=getattr(obj,'data',None)
    return ([tuple(float(a) for a in v.co) for v in data.vertices]
            if data is not None and hasattr(data,'vertices') else fallback)


def build_detail(ctx,geometry,candidate,assembly,p):
    legacy=assembly.get('crown',{})
    source_id=candidate.get('source_id',candidate.get('source_id_candidate'))
    meta={'source_ids':[source_id,'B14_GEOM','CROWN_GENS_AERIAL_V5','OWNER_CONSTRUCTION_V5'],
          'source_locator':'NTUA PDFp13/14 Fig8/9; National Geographic2023-06-09 Gensler aerial; owner August2014 crown image',
          'evidence_level':'待确认','approximation':True,'asbuilt_verified':False,
          'geometry_role':'crown_roof_and_trusses_candidate','station_mapping_evidence':'待确认',
          'fabrication_verified':False,'source_topology_confirmed':True,
          'formula':'Shared actual-z rim controls; source-informed steep inner lattice and wide horizontal return; independent central deck apertures',
          'uncertainty':'Actual image is oblique, uncalibrated. Dimensions, azimuth, counts, exact equipment functions and fabrication sections unbounded; NTUA elevation samples approximately±1.5m plus unresolved datum/version.',
          'used_parameters':p}
    anchors={a['id']:a['z_m'] for a in candidate.get('anchors',[])}
    roof_z=float(legacy.get('roof_z_m',anchors.get('main_inner_roof',601.099)))
    base=float(legacy.get('support_z_m',anchors.get('crown_support_base',546.993)))
    lower_z=float(legacy.get('lower_frame_top_candidate_m',542.))
    if not lower_z<base<roof_z<min(trim_height(s,candidate) for s in (0,1)):
        raise ValueError('Crown elevations must order lower frame, base, deck, rim')
    for key in ('return_width_fit_m','return_depth_fit_m','deck_radius_fit_m','deck_thickness_fit_m'):
        if not math.isfinite(float(p[key])) or p[key]<=0:raise ValueError('Positive crown option required: '+key)
    stations=crown_profile_stations(geometry,ctx.config,int(p['collector_net_circumferential_samples']),(.5,))
    # Actual aerial shows a broad stepped rim; a bevelled wire cannot express it.
    return_faces=[];outer=[];inner=[]
    for station in stations:
        outer.append(rim_point(geometry,ctx.config,station,candidate))
        inner.append(rim_point(geometry,ctx.config,station,candidate,p['return_width_fit_m']))
    for i in range(len(stations)-1):
        a,b=outer[i:i+2];c,d=inner[i:i+2];depth=p['return_depth_fit_m']
        return_faces.extend(([a,b,d,c],[(a[0],a[1],a[2]-depth),(b[0],b[1],b[2]-depth),b,a],
              [c,d,(d[0],d[1],d[2]-depth),(c[0],c[1],c[2]-depth)]))
    rim=_quad_mesh(ctx,'CROWN_V5_WIDE_RIM_HORIZONTAL_RETURN_CANDIDATE',return_faces,
         '74_CROWN_ROOF_CANDIDATE','steel',{**meta,'geometry_role':'crown_rim_return_candidate',
         'formula':'Each local rim cross-section is a horizontal radial return with shallow downward fascia; continuous along trim; open at actual V lips'})
    track=[rim_point(geometry,ctx.config,s,candidate,p['return_track_inset_fit_m']) for s in stations]
    ctx.lines('CROWN_V5_RIM_TRACK_CANDIDATE',[track],'74_CROWN_ROOF_CANDIDATE',p['rim_track_radius_display_m'],'steel',
              {**meta,'geometry_role':'crown_washing_track_candidate','function_evidence':'NTUA identifies window-washing track; actual coordinates unavailable'})
    # A connected slot ends in an exposed round aperture. It is a genuine mesh
    # hole; neither a dark rectangle nor a full opening pretending to be a roof.
    hole=roof_slot_polygon(p)
    dv,df=annular_slab(p['deck_radius_fit_m'],hole,roof_z,p['deck_thickness_fit_m'],192)
    deck=ctx.mesh('CROWN_V5_MAIN_DECK_RECT_RECESS_AND_ROUND_APERTURE',dv,df,
         '74_CROWN_ROOF_CANDIDATE','steel',{**meta,'geometry_role':'crown_lower_main_roof_candidate',
         'aperture_function':'Rectangular recess and round aperture visible; ventilation/maintenance function unresolved',
         'formula':'Circular annular slab with one polygonal connected rectangular+semicircular hole'})
    # Recess frame and two separated grating panels stop above the round void.
    r=p['deck_aperture_half_width_fit_m'];y0=p['deck_grate_start_y_fit_m'];y1=p['deck_grate_end_y_fit_m']
    grate_z=roof_z-p['deck_recess_depth_fit_m'];grates=[];frames=[]
    gap=p['recess_grate_panel_separator_fit_m']/2
    for ymin,ymax in ((y0,(y0+y1)/2-gap),((y0+y1)/2+gap,y1)):
        frames.append([(-r,ymin,grate_z),(r,ymin,grate_z),(r,ymax,grate_z),(-r,ymax,grate_z),(-r,ymin,grate_z)])
        for i in range(1,math.ceil((ymax-ymin)/p['deck_grate_pitch_display_m'])):
            y=ymin+i*p['deck_grate_pitch_display_m']
            if y<ymax:grates.append([(-r,y,grate_z),(r,y,grate_z)])
        grates.extend([[(-r/3,ymin,grate_z),(-r/3,ymax,grate_z)],[(r/3,ymin,grate_z),(r/3,ymax,grate_z)]])
    ctx.lines('CROWN_V5_RECT_RECESS_FRAME',frames,'76_CROWN_ROOF_EQUIPMENT',p['recess_frame_radius_display_m'],'steel',meta)
    ctx.lines('CROWN_V5_TWO_RECESSED_GRATE_PANELS',grates,'76_CROWN_ROOF_EQUIPMENT',p['recess_grate_radius_display_m'],'steel',
              {**meta,'geometry_role':'crown_rectangular_recess_grating_candidate','formula':'Two candidate grate panels inside visible rectangular recess; circular aperture remains open'})
    rail=[(p['deck_radius_fit_m']*math.cos(i*2*math.pi/160),p['deck_radius_fit_m']*math.sin(i*2*math.pi/160),roof_z+p['deck_guardrail_height_fit_m'])
          for i in range(161)]
    railposts=[[v,(v[0],v[1],roof_z)] for v in rail[::5]]
    ctx.lines('CROWN_V5_DECK_GUARDRAIL_CANDIDATE',[rail]+railposts,'76_CROWN_ROOF_EQUIPMENT',p['deck_guardrail_radius_display_m'],'steel',meta)
    # Keep the steep collector shape. Replace solid glass-bowl skin with a dense
    # physically separated lattice, matching the open inner screen in the aerial.
    radial_samples=int(p['collector_net_radial_samples']);net=[];ribs=[];bands=[]
    for station in stations:
        net.append([collector_point(geometry,ctx.config,station,candidate,p,roof_z,j/radial_samples)
                    for j in range(radial_samples+1)])
    for j in range(radial_samples+1):
        net.append([collector_point(geometry,ctx.config,s,candidate,p,roof_z,j/radial_samples) for s in stations])
    ctx.lines('CROWN_V5_STEEP_INNER_NET_CONTINUOUS',net,'74_CROWN_ROOF_CANDIDATE',p['collector_net_radius_display_m'],'steel',
              {**meta,'geometry_role':'crown_open_collector_roof_candidate','formula':'Steep radial z(u)=roof_z+u²*(rim_z−roof_z), shared actual rim azimuth; dense curve lattice, count unconfirmed'})
    # Lower support and upper kickers use orderly matched bays. Circumferential
    # rings stay on source-local level candidates, not arbitrary diagonal spokes.
    grid=crown_profile_stations(geometry,ctx.config,int(legacy.get('truss_count_display',24)),(.5,))
    # Shoulder geometry is represented, but omit intermediate zero-length trim
    # station duplicates from structural sampling to avoid clustered extra fins.
    grid=[s for i,s in enumerate(grid) if s['segment_id'] not in ('K2_SHOULDER_LOW','K2_SHOULDER_HIGH') or i in (0,len(grid)-1)]
    depth=float(legacy.get('truss_radial_depth_fit_m',1.2));bay=float(legacy.get('truss_bay_height_display_m',4.5))
    chordrad=float(legacy.get('main_chord_radius_display_m',.15));webrad=float(legacy.get('web_radius_display_m',.08))
    chords=[];webs=[];radials=[];kickers=[];rings=[];corners=[]
    floorlevels=sorted({float(row['z_m']) for row in candidate.get('floor_image_candidates',[]) if base<=row['z_m']<roof_z}|{base,roof_z})
    ringlevels=floorlevels[::2]+([roof_z] if roof_z not in floorlevels[::2] else [])
    upperlevels=[roof_z+j*2*bay for j in range(1,math.ceil((632-roof_z)/(2*bay)))]
    for station in grid:
        top=trim_height(station['s'],candidate)
        levels=sorted(set(floorlevels+[z for z in upperlevels if z<top]+[top]))
        point=lambda z,inset=0:rim_point(geometry,ctx.config,station,candidate,inset,z)
        chords.extend(([point(z) for z in levels],[point(z,depth) for z in levels]))
        for j,(z0,z1) in enumerate(zip(levels,levels[1:])):
            webs.extend(([point(z0,depth if j%2 else 0),point(z1,0 if j%2 else depth)],
                         [point(z0),point(z0,depth)]))
        for z in ringlevels:
            # A beam axis at the slab top made its bevel envelope pierce the
            # photographed roof deck. Keep the candidate roof load path below
            # the deck underside; source floor anchor itself remains unchanged.
            member_z=z
            if abs(z-roof_z)<1e-7:
                member_z-=p['deck_thickness_fit_m']+p['structural_radial_radius_display_m']+p['roof_strut_clearance_display_m']
            x,y,_=point(member_z,depth);rad=math.hypot(x,y)
            radials.append([(x*float(legacy.get('central_steel_frame_radius_fit_m',6))/rad,y*float(legacy.get('central_steel_frame_radius_fit_m',6))/rad,member_z),point(member_z,depth)])
        rib=[collector_point(geometry,ctx.config,station,candidate,p,roof_z,j/int(p['collector_primary_rib_radial_samples_display'])) for j in range(int(p['collector_primary_rib_radial_samples_display'])+1)]
        ribs.append(rib);kickers.append([rib[0],point(min(top,roof_z+float(legacy.get('kicker_height_fit_m',9))),depth)])
    for z in ringlevels+upperlevels:
        for a,b in zip(grid,grid[1:]):
            if z<min(trim_height(a['s'],candidate),trim_height(b['s'],candidate)):
                rings.extend(([rim_point(geometry,ctx.config,a,candidate,0,z),rim_point(geometry,ctx.config,b,candidate,0,z)],
                   [rim_point(geometry,ctx.config,a,candidate,depth,z),rim_point(geometry,ctx.config,b,candidate,depth,z)]))
    for j in range(1,int(p['collector_primary_ring_divisions_display'])):
        bands.append([collector_point(geometry,ctx.config,s,candidate,p,roof_z,j/int(p['collector_primary_ring_divisions_display'])) for s in stations])
    ctx.lines('CROWN_V5_INNER_PRIMARY_RADIAL_RIBS',ribs,'75_CROWN_STEEL_CANDIDATE',p['collector_primary_rib_radius_display_m'],'steel',meta)
    ctx.lines('CROWN_V5_INNER_CONTINUOUS_RING_RIBS',bands,'75_CROWN_STEEL_CANDIDATE',p['collector_ring_rib_radius_display_m'],'steel',meta)
    for proportion in p['structural_corner_proportions_display']:
        i=min(len(grid)-2,max(0,round(proportion*(len(grid)-1))));a,b=grid[i:i+2]
        for z0,z1 in zip(floorlevels,floorlevels[1:]):
            corners.append([rim_point(geometry,ctx.config,a,candidate,0,z0),rim_point(geometry,ctx.config,b,candidate,0,z1)])
    columnaxis=float(legacy.get('lower_frame_radius_candidate_m',23.25))-float(legacy.get('lower_frame_column_inset_candidate_m',2))
    pair=float(legacy.get('lower_frame_pair_offset_candidate_m',4.7))
    columns=[(sign*columnaxis,o,lower_z) for sign in(-1,1) for o in(-pair,pair)]
    columns += [(o,sign*columnaxis,lower_z) for sign in(-1,1) for o in(-pair,pair)]
    columns.sort(key=lambda q:math.atan2(q[1],q[0]));transition=[]
    for station in grid:
        foot=rim_point(geometry,ctx.config,station,candidate,0,base)
        support=min(columns,key=lambda q:math.dist(foot,q));transition.append([support,foot])
    transition.extend((columns+[columns[0]],[rim_point(geometry,ctx.config,s,candidate,0,base) for s in grid]))
    objects=[rim.name,deck.name]
    for name,paths,radius in [('OUTER_DOUBLE_CHORD_TRUSSES',chords,chordrad),('OUTER_TRUSS_WEBS',webs,webrad),
       ('RADIAL_CORE_STEEL_FRAME_STRUTS',radials,p['structural_radial_radius_display_m']),('INNER_KICKER_TRUSSES_ABOVE_ROOF',kickers,chordrad),
       ('ALTERNATE_LEVEL_OPEN_RING_TRUSSES',rings,p['structural_ring_radius_display_m']),('THREE_CORNER_BRACED_BAYS',corners,webrad),
       ('LOWER_542_TO_SUPPORT_TRANSITION',transition,p['structural_radial_radius_display_m'])]:
        obj=ctx.lines('CROWN_'+name+'_CANDIDATE',paths,'75_CROWN_STEEL_CANDIDATE',radius,'steel',
             {**meta,'geometry_role':'crown_steel_candidate','installed_coordinate_verified':False,'member_radius_display_m':radius})
        objects.append(obj.name)
    equipment=_equipment(ctx,geometry,candidate,p,meta,roof_z,stations)
    actual=_actual(deck,dv)
    checks=[{'name':'crown_lower_roof_entity','passed':len(actual)>0 and abs(max(v[2] for v in actual)-roof_z)<.001,'actual':len(actual)},
      {'name':'crown_wide_return_entity','passed':len(return_faces)>200,'actual':len(return_faces)},
      {'name':'crown_dense_steep_net_entity','passed':len(net)>180 and min(v[2] for v in net[0])==roof_z,'actual':len(net)},
      {'name':'crown_rect_recess_and_round_opening','passed':len(hole)>40 and r>0 and len(grates)>10,'actual':{'hole_vertices':len(hole),'grate_paths':len(grates)}},
      {'name':'crown_steel_load_paths_entities','passed':all(bool(paths) for paths in(chords,webs,radials,kickers,rings,corners)),'actual':{'chords':len(chords),'webs':len(webs),'radials':len(radials),'kickers':len(kickers),'ring_members':len(rings),'corner_members':len(corners)}},
      {'name':'crown_lower_transition_entities','passed':len(transition)>3,'actual':len(transition)},
      {'name':'helipad_not_fabricated_without_evidence','passed':not p['helipad_enabled'],'actual':p['helipad_evidence']}]
    return {'objects':objects,'checks':checks,'used_parameters':p,'approximation':True,'evidence_level':'待确认',
            'asbuilt_verified':False,'source_ids':meta['source_ids'],'roof_is_at_601_not_flat_632_cap':True,
            'K2_gap_preserved':False,'actual_reentrant_V_is_separate_component':True,'equipment':equipment,
            'uncertainty':meta['uncertainty']}


def _equipment(ctx,geometry,candidate,p,meta,roof_z,stations):
    units=[];fans=[];guards=[];count=int(p['rim_mechanical_device_count_display'])
    size=p['rim_mechanical_device_size_fit_m']
    shelf=[]
    for a,b in zip(stations,stations[1:]):
        ao=rim_point(geometry,ctx.config,a,candidate,p['rim_equipment_shelf_outer_inset_fit_m'])
        bo=rim_point(geometry,ctx.config,b,candidate,p['rim_equipment_shelf_outer_inset_fit_m'])
        ai=rim_point(geometry,ctx.config,a,candidate,p['rim_equipment_shelf_inner_inset_fit_m'])
        bi=rim_point(geometry,ctx.config,b,candidate,p['rim_equipment_shelf_inner_inset_fit_m'])
        drop=p['rim_equipment_drop_below_trim_fit_m']
        lowered=[(v[0],v[1],v[2]-drop) for v in (ao,bo,bi,ai)]
        shelf.append(lowered)
        uppera=rim_point(geometry,ctx.config,a,candidate,p['return_width_fit_m'])
        upperb=rim_point(geometry,ctx.config,b,candidate,p['return_width_fit_m'])
        shelf.append([uppera,upperb,lowered[1],lowered[0]])
    _quad_mesh(ctx,'CROWN_V5_STEPPED_RIM_APPARATUS_SUPPORT_SHELF',shelf,
        '76_CROWN_ROOF_EQUIPMENT','steel',{**meta,'geometry_role':'crown_equipment_support_shelf_candidate',
        'formula':'Recessed continuous shelf tied to upper return; apparatus top below glass trim; dimensions unconfirmed'})
    # Only positions along the main open rim, no device across the V slit.
    for i in range(count):
        s=(i+.5)/count
        station=min(stations,key=lambda v:abs(v['s']-s))
        center=rim_point(geometry,ctx.config,station,candidate,p['rim_mechanical_device_inset_fit_m'])
        x,y,z=center
        z-=p['rim_equipment_drop_below_trim_fit_m']
        obj=ctx.box(f'CROWN_V5_RIM_APPARATUS_{i+1:03d}_FUNCTION_UNCONFIRMED',(x,y,z+.5*size[2]),size,
             '76_CROWN_ROOF_EQUIPMENT','steel',{**meta,'geometry_role':'crown_rim_mechanical_device_candidate',
             'function':p['rim_mechanical_device_function'],'installed_count_verified':False})
        units.append(obj.name)
        rad=p['rim_mechanical_fan_radius_fit_m'];fan_z=z+size[2]+p['rim_mechanical_fan_pipe_radius_display_m']
        circle=[(x+rad*math.cos(j*2*math.pi/16),y+rad*math.sin(j*2*math.pi/16),fan_z) for j in range(17)]
        fans.append(circle)
        fans.extend([[(x,y,fan_z),(x+rad*math.cos(j*2*math.pi/4),y+rad*math.sin(j*2*math.pi/4),fan_z)] for j in range(4)])
    ctx.lines('CROWN_V5_RIM_FANLIKE_DETAILS_FUNCTION_UNCONFIRMED',fans,'76_CROWN_ROOF_EQUIPMENT',p['rim_mechanical_fan_pipe_radius_display_m'],'steel',meta)
    # L128 cooling towers are described by structural designers. Arrangement,
    # dimensions and current products below are candidates, not shop equipment.
    cooling_z=next((r['z_m'] for r in candidate.get('floor_image_candidates',[]) if r['source_floor_label']=='L128'),592.47)
    tower_size=p['cooling_tower_size_fit_m'];cooling=[]
    for i in range(int(p['cooling_tower_count_display'])):
        a=2*math.pi*i/int(p['cooling_tower_count_display']);r=p['cooling_tower_ring_radius_fit_m']
        x,y=r*math.cos(a),r*math.sin(a)
        obj=ctx.box(f'CROWN_V5_L128_COOLING_TOWER_CANDIDATE_{i+1:02d}',(x,y,cooling_z+tower_size[2]/2),tower_size,
             '76_CROWN_ROOF_EQUIPMENT','steel',{**meta,'geometry_role':'crown_cooling_tower_candidate',
             'function_evidence':'NTUA text explicitly cooling towers at L128 around TMD; coordinates/count/sections unconfirmed'})
        cooling.append(obj.name)
        for j in range(1,int(p['cooling_louver_rows_display'])+1):
            z=cooling_z+j*tower_size[2]/(p['cooling_louver_rows_display']+1)
            guards.append([(x-tower_size[0]/2,y-tower_size[1]/2-.015,z),(x+tower_size[0]/2,y-tower_size[1]/2-.015,z)])
    ctx.lines('CROWN_V5_L128_COOLING_TOWER_LOUVER_PROXY',guards,'76_CROWN_ROOF_EQUIPMENT',p['cooling_louver_radius_display_m'],'steel',meta)
    enclosure_size=p['deck_service_enclosure_size_fit_m'];enclosure_xy=p['deck_service_enclosure_center_xy_fit_m']
    ctx.box('CROWN_V5_DECK_SMALL_SERVICE_ENCLOSURE_CANDIDATE',(*enclosure_xy,roof_z+enclosure_size[2]/2),enclosure_size,
             '76_CROWN_ROOF_EQUIPMENT','steel',{**meta,'geometry_role':'crown_small_service_enclosure_candidate',
             'function_evidence':'Small deck object visible; equipment function unconfirmed'})
    ctx.empty('CROWN_HELIPAD_UNCONFIRMED_PARAMETRIC_INTERFACE',(0,0,roof_z),'77_CROWN_UNCONFIRMED_INTERFACES',
            {**meta,'geometry_role':'unresolved_interface','formula':'Editable helipad interface, enabled=false','source_topology_confirmed':False,
             'uncertainty':p['helipad_evidence']})
    return {'rim_apparatus_candidates':len(units),'cooling_tower_candidates':len(cooling),
            'cooling_tower_source_level':'L128','cooling_tower_candidate_base_m':cooling_z,
            'helipad_generated':False,'helipad_evidence':p['helipad_evidence']}
