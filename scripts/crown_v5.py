"""Source-informed crown interfaces; all layout dimensions remain candidates.

Actual Gensler aerial, published National Geographic2023-06-09, resolves
relationships absent from earlier renders. It does not supply 3D coordinates.
"""
import math
from crown_completion import crown_profile_stations, trim_height


def roof_slot_polygon(p, count=48):
    """Rectangular well boundary; the full circular oculus is separate below."""
    r=p['deck_aperture_half_width_fit_m'];y=p['deck_well_lower_y_fit_m']
    top=p['deck_aperture_rect_upper_y_fit_m']
    if not y < 0 < top or r <= 0:
        raise ValueError('Roof slot must enclose origin and have positive width')
    return [(-r,y),(r,y),(r,top),(-r,top)]


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
            roof_z+u*(outer[2]-roof_z))


def _circle(center,radius,count=64):
    return [(center[0]+radius*math.cos(i*2*math.pi/count),
             center[1]+radius*math.sin(i*2*math.pi/count)) for i in range(count)]


def _clip(poly,a,b,inside=True):
    """Convex half-plane clipping; no external dependency or Blender boolean."""
    if not poly:return []
    sign=1 if inside else -1
    distance=lambda v:sign*((b[0]-a[0])*(v[1]-a[1])-(b[1]-a[1])*(v[0]-a[0]))
    result=[];previous=poly[-1];dp=distance(previous)
    for current in poly:
        dc=distance(current)
        if (dp>=-1e-10)!=(dc>=-1e-10):
            t=dp/(dp-dc)
            result.append(tuple(previous[j]+t*(current[j]-previous[j]) for j in range(2)))
        if dc>=-1e-10:result.append(current)
        previous,dp=current,dc
    clean=[]
    for v in result:
        if not clean or math.dist(v,clean[-1])>1e-8:clean.append(v)
    if len(clean)>1 and math.dist(clean[0],clean[-1])<1e-8:clean.pop()
    area=abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(clean,clean[1:]+clean[:1])))
    return clean if len(clean)>=3 and area>1e-9 else []


def _subtract(poly,hole):
    """Partition a convex polygon outside a convex CCW hole."""
    result=[];remaining=poly
    for a,b in zip(hole,hole[1:]+hole[:1]):
        outside=_clip(remaining,a,b,False)
        if outside:result.append(outside)
        remaining=_clip(remaining,a,b)
        if not remaining:break
    return result


def _cut_polygons(polygons,holes):
    for hole in holes:
        bounds=(min(v[0] for v in hole),max(v[0] for v in hole),
                min(v[1] for v in hole),max(v[1] for v in hole))
        pieces=[]
        for poly in polygons:
            if max(v[0] for v in poly)<bounds[0] or min(v[0] for v in poly)>bounds[1] or max(v[1] for v in poly)<bounds[2] or min(v[1] for v in poly)>bounds[3]:
                pieces.append(poly)
            else:pieces.extend(_subtract(poly,hole))
        polygons=pieces
    return polygons


def _extruded_polygons(polys,z,thickness):
    verts=[];faces=[]
    for poly in polys:
        n=len(poly);start=len(verts)
        verts.extend([(x,y,z) for x,y in poly]+[(x,y,z-thickness) for x,y in poly])
        faces.extend((tuple(start+i for i in range(n)),tuple(start+n+i for i in reversed(range(n)))))
        faces.extend((start+i,start+(i+1)%n,start+n+(i+1)%n,start+n+i) for i in range(n))
    return verts,faces


def roof_holes(p):
    holes=[roof_slot_polygon(p)]
    for hatch in p['deck_scattered_apertures_fit']:
        x,y=hatch['center_xy_m']
        if hatch['kind']=='round':holes.append(_circle((x,y),hatch['radius_m']))
        else:
            w,h=hatch['size_m'];holes.append([(x-w/2,y-h/2),(x+w/2,y-h/2),(x+w/2,y+h/2),(x-w/2,y+h/2)])
    return holes


def roof_grating_mesh(p,z):
    """Physical open metal grating; all main/scattered openings cut every bar."""
    radius=p['deck_radius_fit_m'];boundary=_circle((0,0),radius,96)
    pitch=p['deck_grate_pitch_display_m'];width=p['deck_grating_bar_width_fit_m']
    bars=[]
    for axis in range(2):
        for i in range(-math.floor(radius/pitch),math.floor(radius/pitch)+1):
            low,high=i*pitch-width/2,i*pitch+width/2
            poly=[(low,-radius),(high,-radius),(high,radius),(low,radius)] if axis==0 else [(-radius,low),(radius,low),(radius,high),(-radius,high)]
            for a,b in zip(boundary,boundary[1:]+boundary[:1]):poly=_clip(poly,a,b)
            if poly:bars.extend(_cut_polygons([poly],roof_holes(p)))
    return _extruded_polygons(bars,z,p['deck_grating_bar_depth_fit_m'])


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
    meta={'source_ids':[source_id,'B14_GEOM','CROWN_GENS_AERIAL_V5','OWNER_CONSTRUCTION_V5','OWNER_TMD_WIND_V6','TURBINE_ATTEY_V6','TMD_MOTIONEERING_V6','OWNER_MEP_BUILD_V6'],
          'source_locator':'NTUA PDFp13/14 Fig8/9; National Geographic2023-06-09 Gensler aerial; owner August2014 crown image',
          'evidence_level':'待确认','approximation':True,'asbuilt_verified':False,
          'geometry_role':'crown_roof_and_trusses_candidate','station_mapping_evidence':'待确认',
          'fabrication_verified':False,'source_topology_confirmed':True,
          'steel_axis_clearance_candidate_m':p['crown_glass_steel_clearance_display_m'],
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
    # A full circle lies below a rectangular well; v5's semicircular slot was
    # an incorrect interpretation. Grated walkway and scattered apertures are
    # actual removed geometry, with image-fit positions explicitly unresolved.
    hole=roof_slot_polygon(p)
    dv,df=roof_grating_mesh(p,roof_z)
    deck=ctx.mesh('CROWN_V5_MAIN_DECK_RECT_RECESS_AND_ROUND_APERTURE',dv,df,
         '74_CROWN_ROOF_CANDIDATE','steel',{**meta,'geometry_role':'crown_lower_main_roof_candidate',
         'aperture_function':'Rectangular recess and round aperture visible; ventilation/maintenance function unresolved',
         'formula':'Crossed physical grating bars clipped to circular perimeter, rectangular well and separately positioned hatch/circular holes; no continuous opaque slab'})
    r=p['deck_aperture_half_width_fit_m']
    grate_z=roof_z-p['deck_recess_depth_fit_m'];grates=[];frames=[]
    oculus=_circle((0,p['deck_aperture_round_center_y_fit_m']),p['deck_oculus_radius_fit_m'],96)
    well_pieces=_cut_polygons([hole],[oculus])
    wv,wf=_extruded_polygons(well_pieces,grate_z,p['deck_well_service_plate_depth_fit_m'])
    ctx.mesh('CROWN_V6_RECTANGULAR_WELL_FLOOR_FULL_ROUND_OCULUS',wv,wf,'74_CROWN_ROOF_CANDIDATE','steel',
             {**meta,'geometry_role':'crown_recess_service_floor_candidate','formula':'Rectangular lowered service platform minus full circular opening; hole continues to TMD hall below'})
    # Independent bridge/grate panels lie outside the full round opening.
    for ymin,ymax in p['deck_bridge_grate_y_ranges_fit_m']:
        frames.append([(-r,ymin,grate_z),(r,ymin,grate_z),(r,ymax,grate_z),(-r,ymax,grate_z),(-r,ymin,grate_z)])
        for i in range(1,math.ceil((ymax-ymin)/p['deck_grate_pitch_display_m'])):
            y=ymin+i*p['deck_grate_pitch_display_m']
            if y<ymax:grates.append([(-r,y,grate_z),(r,y,grate_z)])
        grates.extend([[(-r/3,ymin,grate_z),(-r/3,ymax,grate_z)],[(r/3,ymin,grate_z),(r/3,ymax,grate_z)]])
    ctx.lines('CROWN_V5_RECT_RECESS_FRAME',frames,'76_CROWN_ROOF_EQUIPMENT',p['recess_frame_radius_display_m'],'steel',meta)
    ctx.lines('CROWN_V5_TWO_RECESSED_GRATE_PANELS',grates,'76_CROWN_ROOF_EQUIPMENT',p['recess_grate_radius_display_m'],'steel',
              {**meta,'geometry_role':'crown_rectangular_recess_grating_candidate','formula':'Two candidate bridge panels at opposite ends of rectangular recess, outside full circular oculus'})
    oculus_ring=[(x,y,grate_z) for x,y in oculus+[oculus[0]]]
    ctx.lines('CROWN_V6_FULL_ROUND_OCULUS_CONTINUOUS_RING',[oculus_ring],'74_CROWN_ROOF_CANDIDATE',p['deck_oculus_ring_radius_display_m'],'steel',meta)
    for index,aperture in enumerate(p['deck_scattered_apertures_fit']):
        poly=roof_holes(p)[index+1]
        ctx.lines(f'CROWN_V6_SCATTERED_APERTURE_CURB_{index+1:02d}',[[(x,y,roof_z+p['deck_scattered_curb_height_fit_m']) for x,y in poly+[poly[0]]]],
                  '76_CROWN_ROOF_EQUIPMENT',p['deck_scattered_curb_radius_display_m'],'steel',
                  {**meta,'geometry_role':'crown_roof_aperture_candidate','image_fit_aperture':aperture,'function_evidence':'Openings visible in actual aerial; dimensions, position, function unconfirmed'})
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
              {**meta,'geometry_role':'crown_open_collector_roof_candidate','formula':'Straight radial z(u)=roof_z+u*(rim_z−roof_z), shared actual rim azimuth; dense horizontal lattice, count unconfirmed'})
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
        point=lambda z,inset=0:rim_point(geometry,ctx.config,station,candidate,inset+p['crown_glass_steel_clearance_display_m'],z)
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
            inner_radius=float(legacy.get('central_steel_frame_radius_fit_m',6))
            # Generic NTUA radial core paths cannot run across the newly
            # source-observed open public hall or its roof oculus. Their actual
            # endpoints are unknown: terminate the candidate at the hall's
            # outer support interface, retaining all below-hall load paths.
            if p['tmd_hall_floor_owner_m']-p['tmd_hall_floor_depth_fit_m']<=member_z<roof_z:
                inner_radius=max(inner_radius,p['tmd_hall_radius_fit_m']+p['tmd_hall_steel_clearance_display_m'])
            if inner_radius>=rad:raise ValueError('Crown radial bay has no space outside TMD hall')
            radials.append([(x*inner_radius/rad,y*inner_radius/rad,member_z),point(member_z,depth)])
        rib=[collector_point(geometry,ctx.config,station,candidate,p,roof_z,j/int(p['collector_primary_rib_radial_samples_display'])) for j in range(int(p['collector_primary_rib_radial_samples_display'])+1)]
        ribs.append(rib);kickers.append([rib[0],point(min(top,roof_z+float(legacy.get('kicker_height_fit_m',9))),depth)])
    for z in ringlevels+upperlevels:
        for a,b in zip(grid,grid[1:]):
            if z<min(trim_height(a['s'],candidate),trim_height(b['s'],candidate)):
                rings.extend(([rim_point(geometry,ctx.config,a,candidate,p['crown_glass_steel_clearance_display_m'],z),rim_point(geometry,ctx.config,b,candidate,p['crown_glass_steel_clearance_display_m'],z)],
                   [rim_point(geometry,ctx.config,a,candidate,depth+p['crown_glass_steel_clearance_display_m'],z),rim_point(geometry,ctx.config,b,candidate,depth+p['crown_glass_steel_clearance_display_m'],z)]))
    for j in range(1,int(p['collector_primary_ring_divisions_display'])):
        bands.append([collector_point(geometry,ctx.config,s,candidate,p,roof_z,j/int(p['collector_primary_ring_divisions_display'])) for s in stations])
    ctx.lines('CROWN_V5_INNER_PRIMARY_RADIAL_RIBS',ribs,'75_CROWN_STEEL_CANDIDATE',p['collector_primary_rib_radius_display_m'],'steel',meta)
    ctx.lines('CROWN_V5_INNER_CONTINUOUS_RING_RIBS',bands,'75_CROWN_STEEL_CANDIDATE',p['collector_ring_rib_radius_display_m'],'steel',meta)
    for proportion in p['structural_corner_proportions_display']:
        i=min(len(grid)-2,max(0,round(proportion*(len(grid)-1))));a,b=grid[i:i+2]
        for z0,z1 in zip(floorlevels,floorlevels[1:]):
            corners.append([rim_point(geometry,ctx.config,a,candidate,p['crown_glass_steel_clearance_display_m'],z0),rim_point(geometry,ctx.config,b,candidate,p['crown_glass_steel_clearance_display_m'],z1)])
    columnaxis=float(legacy.get('lower_frame_radius_candidate_m',23.25))-float(legacy.get('lower_frame_column_inset_candidate_m',2))
    pair=float(legacy.get('lower_frame_pair_offset_candidate_m',4.7))
    columns=[(sign*columnaxis,o,lower_z) for sign in(-1,1) for o in(-pair,pair)]
    columns += [(o,sign*columnaxis,lower_z) for sign in(-1,1) for o in(-pair,pair)]
    columns.sort(key=lambda q:math.atan2(q[1],q[0]));transition=[]
    for station in grid:
        foot=rim_point(geometry,ctx.config,station,candidate,p['crown_glass_steel_clearance_display_m'],base)
        support=min(columns,key=lambda q:math.dist(foot,q));transition.append([support,foot])
    transition.extend((columns+[columns[0]],[rim_point(geometry,ctx.config,s,candidate,p['crown_glass_steel_clearance_display_m'],base) for s in grid]))
    objects=[rim.name,deck.name]
    for name,paths,radius in [('OUTER_DOUBLE_CHORD_TRUSSES',chords,chordrad),('OUTER_TRUSS_WEBS',webs,webrad),
       ('RADIAL_CORE_STEEL_FRAME_STRUTS',radials,p['structural_radial_radius_display_m']),('INNER_KICKER_TRUSSES_ABOVE_ROOF',kickers,chordrad),
       ('ALTERNATE_LEVEL_OPEN_RING_TRUSSES',rings,p['structural_ring_radius_display_m']),('THREE_CORNER_BRACED_BAYS',corners,webrad),
       ('LOWER_542_TO_SUPPORT_TRANSITION',transition,p['structural_radial_radius_display_m'])]:
        obj=ctx.lines('CROWN_'+name+'_CANDIDATE',paths,'75_CROWN_STEEL_CANDIDATE',radius,'steel',
             {**meta,'geometry_role':'crown_steel_candidate','installed_coordinate_verified':False,'member_radius_display_m':radius})
        objects.append(obj.name)
    equipment=_equipment(ctx,geometry,candidate,p,meta,roof_z,stations)
    hall=_tmd_hall(ctx,p,meta,roof_z)
    turbines=_turbines(ctx,geometry,candidate,p,meta)
    actual=_actual(deck,dv)
    hall_radials=[path for path in radials if p['tmd_hall_floor_owner_m']-p['tmd_hall_floor_depth_fit_m']<=path[0][2]<roof_z]
    hall_clearance=min(math.hypot(v[0],v[1])-p['structural_radial_radius_display_m']-p['tmd_hall_radius_fit_m']
                       for path in hall_radials for v in path)
    checks=[{'name':'crown_lower_roof_entity','passed':len(actual)>0 and abs(max(v[2] for v in actual)-roof_z)<.001,'actual':len(actual)},
      {'name':'crown_wide_return_entity','passed':len(return_faces)>200,'actual':len(return_faces)},
      {'name':'crown_dense_steep_net_entity','passed':len(net)>180 and min(v[2] for v in net[0])==roof_z,'actual':len(net)},
      {'name':'crown_rect_recess_and_round_opening','passed':len(hole)==4 and len(oculus)==96 and len(grates)>10,'actual':{'well_boundary_vertices':len(hole),'full_oculus_vertices':len(oculus),'scattered_openings':len(p['deck_scattered_apertures_fit']),'grate_paths':len(grates)}},
      {'name':'crown_steel_load_paths_entities','passed':all(bool(paths) for paths in(chords,webs,radials,kickers,rings,corners)),'actual':{'chords':len(chords),'webs':len(webs),'radials':len(radials),'kickers':len(kickers),'ring_members':len(rings),'corner_members':len(corners)}},
      {'name':'crown_lower_transition_entities','passed':len(transition)>3,'actual':len(transition)},
      {'name':'crown_radials_clear_public_hall_and_oculus','passed':hall_clearance>0,
       'actual':{'minimum_member_envelope_hall_clearance_m':hall_clearance,'members':len(hall_radials)},
       'meaning':'Candidate radial members stop at outer hall interface rather than occupying public hall or sky opening; fabrication endpoints remain unconfirmed'},
      {'name':'helipad_not_fabricated_without_evidence','passed':not p['helipad_enabled'],'actual':p['helipad_evidence']}]
    return {'objects':objects,'checks':checks,'used_parameters':p,'approximation':True,'evidence_level':'待确认',
            'asbuilt_verified':False,'source_ids':meta['source_ids'],'roof_is_at_601_not_flat_632_cap':True,
            'K2_gap_preserved':False,'actual_reentrant_V_is_separate_component':True,'equipment':equipment,'tmd_hall':hall,'wind_turbines':turbines,
            'uncertainty':meta['uncertainty']}


def _tmd_hall(ctx,p,meta,roof_z):
    """Source-observed art hall and TMD relationships, replaceable dimensions."""
    collection='78_TMD_ART_HALL_CANDIDATE';hall_z=p['tmd_hall_floor_owner_m']
    radius=p['tmd_hall_radius_fit_m'];center=(0,p['deck_aperture_round_center_y_fit_m'])
    local={**meta,'geometry_role':'tmd_art_hall_candidate','source_topology_confirmed':True,
           'confirmed_attributes':{'public_levels':[125,126],'L126_owner_m':583.4,'steel_mass_tonnes':1000,'device_spans_floors':5},
           'source_locator':'Owner2016-04-22 article and first two hall photographs; Motioneering2023-04-26',
           'formula':'Cylindrical art hall below grating deck; full sky oculus; sculpture above suspended steel mass; magnet below mass over fixed copper plate',
           'uncertainty':'Hall/device dimensions, suspension count, sculpture form and coordinates photo-fit only. Owner30m Eye extent unresolved, not assigned as sculpture height.'}
    floor_poly=_circle((0,0),radius,128);masshole=_circle(center,p['tmd_mass_radius_fit_m']+p['tmd_movement_clearance_fit_m'])
    fv,ff=_extruded_polygons(_cut_polygons([floor_poly],[masshole]),hall_z,p['tmd_hall_floor_depth_fit_m'])
    ctx.mesh('TMD_V6_HALL_126_VISITOR_FLOOR',fv,ff,collection,'core',local)
    if p.get('version','').startswith('crown-v8'):
        from crown_art_v8 import build_hall_enclosure
        build_hall_enclosure(ctx,p,local)
    else:
        wall_quads=[];seams=[]
        for i in range(128):
            a,b=2*math.pi*i/128,2*math.pi*(i+1)/128
            x,y=radius*math.cos(a),radius*math.sin(a);u,v=radius*math.cos(b),radius*math.sin(b)
            wall_quads.append([(x,y,hall_z),(u,v,hall_z),(u,v,roof_z-p['deck_thickness_fit_m']),(x,y,roof_z-p['deck_thickness_fit_m'])])
            if i%2==0:seams.append([(x,y,hall_z),(x,y,roof_z-p['deck_thickness_fit_m'])])
        _quad_mesh(ctx,'TMD_V6_HALL_CYLINDRICAL_ENCLOSURE',wall_quads,collection,'tmd_hall',local)
        ctx.lines('TMD_V6_HALL_VERTICAL_CLADDING_SEAMS',seams,collection,p['tmd_cladding_seam_radius_display_m'],'steel',local)
    # Mechanical mass geometry is a cylinder proxy, not a fabricated shop body.
    mass_radius=p['tmd_mass_radius_fit_m'];mass_thickness=p['tmd_mass_thickness_fit_m']
    mv,mf=_extruded_polygons([_circle(center,mass_radius,96)],hall_z,mass_thickness)
    ctx.mesh('TMD_V6_SUSPENDED_STEEL_MASS_1000_TONNE_CANDIDATE',mv,mf,collection,'steel',
             {**local,'geometry_role':'tmd_suspended_mass_candidate','physical_mass_tonnes':1000,'mass_evidence_level':'已证实','dimensions_evidence_level':'待确认'})
    copper_z=hall_z-mass_thickness-p['tmd_magnet_clearance_fit_m']-p['tmd_magnet_depth_fit_m']
    cv,cf=_extruded_polygons([_circle(center,p['tmd_copper_plate_radius_fit_m'])],copper_z,p['tmd_copper_plate_depth_fit_m'])
    ctx.mesh('TMD_V6_COPPER_PLATE_FIXED_TO_LOWER_FLOOR',cv,cf,collection,'copper',local)
    magnet=p['tmd_magnet_array_size_fit_m']
    ctx.box('TMD_V6_MAGNET_ARRAY_BELOW_SUSPENDED_MASS',(center[0],center[1],hall_z-mass_thickness-magnet[2]/2),magnet,collection,'steel',local)
    cables=[]
    for i in range(int(p['tmd_suspension_cable_count_display'])):
        angle=2*math.pi*i/p['tmd_suspension_cable_count_display']
        r0=p['tmd_suspension_bottom_radius_fit_m'];r1=p['tmd_suspension_top_radius_fit_m']
        cables.append([(center[0]+r0*math.cos(angle),center[1]+r0*math.sin(angle),hall_z),
                       (center[0]+r1*math.cos(angle),center[1]+r1*math.sin(angle),roof_z-p['deck_thickness_fit_m'])])
    ctx.lines('TMD_V6_HEAVY_SUSPENSION_CABLES',cables,collection,p['tmd_suspension_cable_radius_display_m'],'steel',local)
    rail_radius=mass_radius+p['tmd_visitor_guard_offset_fit_m'];rail_z=hall_z+p['tmd_visitor_guard_height_fit_m']
    ring=[(center[0]+rail_radius*math.cos(i*2*math.pi/96),center[1]+rail_radius*math.sin(i*2*math.pi/96),rail_z) for i in range(97)]
    ctx.lines('TMD_V6_VISITOR_GUARDRAIL_RING',[ring]+[[(x,y,hall_z),(x,y,rail_z)] for x,y,z in ring[::4]],collection,p['tmd_visitor_guard_radius_display_m'],'steel',local)
    from crown_art_v7 import build_art
    art=build_art(ctx,p,local,roof_z,center)
    return {'owner_floor_m':hall_z,'design_floor_candidate_m':583.258,'difference_m':hall_z-583.258,
            'physical_mass_tonnes':1000,'floor_span_confirmed':5,'sculpture_30m_statement_extent':'unresolved; not used as height',
            'art_topology_fit':art,'asbuilt_coordinates_verified':False,'camera_candidate':{'position':(0,-13,hall_z+3.2),'target':(0,center[1],hall_z+5)}}


def _turbines(ctx,geometry,candidate,p,meta):
    """270 source-confirmed units; modified product, row/column layout unknown."""
    groups=candidate.get('wind_openings_candidate',[]);units=[];shafts=[];frames=[]
    ncol=int(p['wind_turbine_columns_display']);nrow=int(p['wind_turbine_rows_display'])
    length=p['wind_turbine_length_generic_candidate_m'];radius=p['wind_turbine_radius_generic_candidate_m']
    source={**meta,'source_ids':['OWNER_TMD_WIND_V6','OWNER_MEP_BUILD_V6','TURBINE_ATTEY_V6','WINDPODS_PRODUCT_V6'],
            'geometry_role':'crown_horizontal_axis_wind_turbines_candidate','installed_count_evidence_level':'已证实',
            'installed_count_confirmed':270,'groups_confirmed':3,'units_per_group_confirmed':90,
            'generic_product_size_not_tower_shop_dimension':True,'row_column_layout_evidence':'待确认',
            'source_locator':'Owner2016-04-22; owner2016-04-27 L124574m; Attey actual installed photo',
            'formula':'Three groups, nine candidate rows by ten candidate columns; horizontal tangent axes with three phase-offset open rotor shells, independently fitted to true-z crown curve'}
    for g,opening in enumerate(groups):
        for row in range(nrow):
            z=opening['z_min_m']+radius+(opening['z_max_m']-opening['z_min_m']-2*radius)*row/max(1,nrow-1)
            for col in range(ncol):
                s=opening['s_min']+(col+.5)/ncol*(opening['s_max']-opening['s_min'])
                station=crown_profile_stations(geometry,ctx.config,160,(s,s-.001,s+.001))
                selected={round(t['s'],8):t for t in station}
                center=rim_point(geometry,ctx.config,selected[round(s,8)],candidate,p['wind_turbine_inset_fit_m'],z)
                a=rim_point(geometry,ctx.config,selected[round(s-.001,8)],candidate,p['wind_turbine_inset_fit_m'],z)
                b=rim_point(geometry,ctx.config,selected[round(s+.001,8)],candidate,p['wind_turbine_inset_fit_m'],z)
                d=math.hypot(b[0]-a[0],b[1]-a[1]);axis=((b[0]-a[0])/d,(b[1]-a[1])/d,0);normal=(-axis[1],axis[0],0)
                at=lambda x,angle:(center[0]+axis[0]*x+normal[0]*radius*math.cos(angle),center[1]+axis[1]*x+normal[1]*radius*math.cos(angle),z+radius*math.sin(angle))
                for segment in range(3):
                    x0=-length/2+length*segment/3;x1=x0+length/3-p['wind_rotor_segment_gap_fit_m']
                    for j in range(8):
                        angle0=math.radians(segment*60+j*210/8);angle1=math.radians(segment*60+(j+1)*210/8)
                        units.append([at(x0,angle0),at(x1,angle0),at(x1,angle1),at(x0,angle1)])
                shafts.append([(center[0]-axis[0]*length/2,center[1]-axis[1]*length/2,z),(center[0]+axis[0]*length/2,center[1]+axis[1]*length/2,z)])
                for end in (-length/2,length/2):
                    pt=(center[0]+axis[0]*end,center[1]+axis[1]*end,z)
                    frames.append([(pt[0],pt[1],z-radius-p['wind_turbine_support_drop_fit_m']),(pt[0],pt[1],z+radius+p['wind_turbine_support_drop_fit_m'])])
    _quad_mesh(ctx,'CROWN_V6_270_WINDPODS_OPEN_ROTOR_SHELLS_CANDIDATE',units,'79_CROWN_WIND_TURBINES_CANDIDATE','steel',source)
    ctx.lines('CROWN_V6_270_HORIZONTAL_TURBINE_SHAFTS',shafts,'79_CROWN_WIND_TURBINES_CANDIDATE',p['wind_turbine_shaft_radius_display_m'],'steel',source)
    ctx.lines('CROWN_V6_TURBINE_FRAME_SUPPORTS',frames,'79_CROWN_WIND_TURBINES_CANDIDATE',p['wind_turbine_support_radius_display_m'],'steel',source)
    return {'generated_units':len(shafts),'confirmed_historical_count':270,'groups':len(groups),
            'row_column_layout_candidate':[nrow,ncol],'owner_L124_height_m':574,'coordinates_confirmed':False}


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
    # Owner construction report explicitly L120561m. NTUA's earlier L128 design
    # remains a named unresolved interface, not silently treated as installed.
    cooling_z=p['cooling_tower_base_owner_m']
    tower_size=p['cooling_tower_size_fit_m'];cooling=[]
    for i in range(int(p['cooling_tower_count_display'])):
        a=2*math.pi*i/int(p['cooling_tower_count_display']);r=p['cooling_tower_ring_radius_fit_m']
        x,y=r*math.cos(a),r*math.sin(a)
        obj=ctx.box(f'CROWN_V6_L120_COOLING_TOWER_CANDIDATE_{i+1:02d}',(x,y,cooling_z+tower_size[2]/2),tower_size,
             '76_CROWN_ROOF_EQUIPMENT','steel',{**meta,'geometry_role':'crown_cooling_tower_candidate',
             'source_ids':['OWNER_MEP_BUILD_V6'],'function_evidence':'Owner2016-04-27 BIM construction report explicitly cooling towers L120561m; coordinates/count/sections unconfirmed',
             'source_conflict':'Earlier NTUA design depicts cooling at L128592.47m; current adoption owner construction report, no claim all other cooling groups absent'})
        cooling.append(obj.name)
        for j in range(1,int(p['cooling_louver_rows_display'])+1):
            z=cooling_z+j*tower_size[2]/(p['cooling_louver_rows_display']+1)
            guards.append([(x-tower_size[0]/2,y-tower_size[1]/2-.015,z),(x+tower_size[0]/2,y-tower_size[1]/2-.015,z)])
    ctx.lines('CROWN_V6_L120_COOLING_TOWER_LOUVER_PROXY',guards,'76_CROWN_ROOF_EQUIPMENT',p['cooling_louver_radius_display_m'],'steel',meta)
    ctx.empty('CROWN_V6_L128_COOLING_OLD_DESIGN_UNRESOLVED_INTERFACE',(0,0,p['cooling_tower_old_design_base_m']),
              '77_CROWN_UNCONFIRMED_INTERFACES',{**meta,'geometry_role':'archived_design_interface','source_ids':['CROWN_NTUA_2014'],
              'uncertainty':'NTUA L128592.47 design conflicts owner construction L120561m. Old layout not displayed; existence of additional installed group unresolved'})
    enclosure_size=p['deck_service_enclosure_size_fit_m'];enclosure_xy=p['deck_service_enclosure_center_xy_fit_m']
    ctx.box('CROWN_V5_DECK_SMALL_SERVICE_ENCLOSURE_CANDIDATE',(*enclosure_xy,roof_z+enclosure_size[2]/2),enclosure_size,
             '76_CROWN_ROOF_EQUIPMENT','steel',{**meta,'geometry_role':'crown_small_service_enclosure_candidate',
             'function_evidence':'Small deck object visible; equipment function unconfirmed'})
    ctx.empty('CROWN_HELIPAD_UNCONFIRMED_PARAMETRIC_INTERFACE',(0,0,roof_z),'77_CROWN_UNCONFIRMED_INTERFACES',
            {**meta,'geometry_role':'unresolved_interface','formula':'Editable helipad interface, enabled=false','source_topology_confirmed':False,
             'uncertainty':p['helipad_evidence']})
    # Requested editable geometry is retained as a hidden asset library object.
    # It is deliberately outside the tower and cannot cover the actual oculus.
    helipad_center=p['helipad_asset_center_candidate_m'];hr=p['helipad_radius_candidate_m']
    hv,hf=_extruded_polygons([_circle(helipad_center,hr,64)],helipad_center[2],p['helipad_plate_depth_candidate_m'])
    hm={**meta,'geometry_role':'helipad_unverified_hidden_asset','source_topology_confirmed':False,
        'installed_location_verified':False,'default_hidden':True,'uncertainty':p['helipad_evidence'],
        'formula':'Standalone editable helipad asset, parked outside tower by library convention; no asserted installed location'}
    platform=ctx.mesh('CROWN_V6_HELIPAD_UNVERIFIED_HIDDEN_ASSET',hv,hf,'77_CROWN_UNCONFIRMED_INTERFACES','unknown',hm)
    hx,hy,hz=helipad_center;hw=p['helipad_H_half_width_candidate_m'];hh=p['helipad_H_half_height_candidate_m']
    mark=ctx.lines('CROWN_V6_HELIPAD_H_UNVERIFIED_HIDDEN_ASSET',[[ (hx-hw,hy-hh,hz+.02),(hx-hw,hy+hh,hz+.02)],
          [(hx+hw,hy-hh,hz+.02),(hx+hw,hy+hh,hz+.02)],[(hx-hw,hy,hz+.02),(hx+hw,hy,hz+.02)]],
          '77_CROWN_UNCONFIRMED_INTERFACES',p['helipad_mark_radius_candidate_m'],'unknown',hm)
    for obj in (platform,mark):
        obj.hide_render=not p['helipad_enabled'];obj.hide_viewport=not p['helipad_enabled']
    return {'rim_apparatus_candidates':len(units),'cooling_tower_candidates':len(cooling),
            'cooling_tower_source_level':'L120','cooling_tower_candidate_base_m':cooling_z,
            'cooling_tower_source_conflict_old_L128_m':p['cooling_tower_old_design_base_m'],
            'helipad_generated':p['helipad_enabled'],'helipad_hidden_editable_asset':True,'helipad_evidence':p['helipad_evidence']}
