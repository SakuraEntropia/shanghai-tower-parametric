"""Same parent grid as lower A; openings cut locally without resampling facade."""
import math


def shared_stations(geometry,cfg):
    grid=geometry.standard_grid(cfg,cfg['curtain']['half_panel_count'])
    arcs=geometry.profile_segments(cfg);ids=[a['id'] for a in arcs];k=ids.index('K2')
    ordered=arcs[k+1:]+arcs[:k];length=sum(a['length'] for a in ordered)
    if cfg.get('notch_v4'):
        lo,hi=cfg['notch_v4']['lip_grid_indices'];indices=list(range(hi,len(grid)))+list(range(lo+1))
    else:
        indices=[i for i,r in enumerate(grid) if r['segment_id']!='K2']
        cut=next(i for i in range(len(indices)) if grid[indices[i]]['segment_id']=='C1')
        indices=indices[cut:]+indices[:cut]
    result=[]
    for index in indices:
        r=grid[index];before=0.
        if r['segment_id']=='K2':s=0. if index>=hi else 1.
        else:
            for a in ordered:
                if a['id']==r['segment_id']:break
                before+=a['length']
            angle=math.atan2(r['xy'][1]-a['center'][1],r['xy'][0]-a['center'][0])
            delta=(angle-math.radians(a['start_deg']))%(2*math.pi)
            if delta>2*math.pi-1e-8:delta=0.
            s=(before+min(a['length'],delta*a['radius']))/length
        result.append({'xy':r['xy'],'s':s,'segment_id':r['segment_id'],'grid_index':index})
    return result


def shared_levels(cfg,p):
    bottom=float(p['base_z_m']);pitch=float(cfg['curtain']['nominal_band_pitch_m'])
    top=max(pair[1] for pair in p['implementation_candidate']['station_height_m'])
    if pitch<=0 or bottom>=top:raise ValueError('Invalid shared crown band range')
    return [bottom]+[bottom+i*pitch for i in range(1,math.ceil((top-bottom)/pitch))]+[top]


def cut_pane(poly,openings):
    from crown_v5 import _cut_polygons
    holes=[[(o['s_min'],o['z_min_m']),(o['s_max'],o['z_min_m']),
            (o['s_max'],o['z_max_m']),(o['s_min'],o['z_max_m'])] for o in openings]
    return _cut_polygons([poly],holes)


def _interval(a,b,poly):
    """Clip a segment to a CCW convex polygon, returning its parameter interval."""
    lo,hi=0.,1.;dx,dy=b[0]-a[0],b[1]-a[1]
    for p,q in zip(poly,poly[1:]+poly[:1]):
        ex,ey=q[0]-p[0],q[1]-p[1]
        v=ex*(a[1]-p[1])-ey*(a[0]-p[0]);d=ex*dy-ey*dx
        if abs(d)<1e-12:
            if v < -1e-9:return None
        elif d>0:lo=max(lo,-v/d)
        else:hi=min(hi,-v/d)
        if lo>hi+1e-10:return None
    return (max(0.,lo),min(1.,hi)) if hi-lo>1e-10 else None


def boundary_segments(poly,openings):
    """Only parent edges and true hole borders; no subtraction partition edges."""
    holes=[[(o['s_min'],o['z_min_m']),(o['s_max'],o['z_min_m']),
            (o['s_max'],o['z_max_m']),(o['s_min'],o['z_max_m'])] for o in openings]
    result=[]
    lerp=lambda a,b,t:tuple(a[i]+t*(b[i]-a[i]) for i in range(2))
    for a,b in zip(poly,poly[1:]+poly[:1]):
        parts=[(0.,1.)]
        for hole in holes:
            hit=_interval(a,b,hole)
            if not hit:continue
            new=[]
            for lo,hi in parts:
                if hit[0]>=hi or hit[1]<=lo:new.append((lo,hi));continue
                if hit[0]>lo:new.append((lo,hit[0]))
                if hit[1]<hi:new.append((hit[1],hi))
            parts=new
        result.extend((lerp(a,b,lo),lerp(a,b,hi)) for lo,hi in parts if hi-lo>1e-9)
    for hole in holes:
        for a,b in zip(hole,hole[1:]+hole[:1]):
            hit=_interval(a,b,poly)
            if hit:result.append((lerp(a,b,hit[0]),lerp(a,b,hit[1])))
    return result


def build(ctx,geometry,p):
    from crown_completion import trim_height,_clipped_vertical_chord,_normal
    from transition_v5 import control_profile_at,step_faces
    from curtain_wall import _buffers,_append_member
    if p['base_z_m']>=min(pair[1] for pair in p['implementation_candidate']['station_height_m']) or p.get('horizontal_sample_count_display',160)<5:raise ValueError('Invalid crown control range')
    cfg=ctx.config;stations=shared_stations(geometry,cfg);levels=shared_levels(cfg,p)
    if float(p['band_pitch_display_m'])<=0 or float(p['frame_radius_display_m'])<=0:raise ValueError('Invalid crown display dimensions')
    points=[s['xy'] for s in stations];tops=[trim_height(s['s'],p) for s in stations]
    openings=p.get('wind_openings_candidate',[])+p.get('vent_openings_candidate',[])+p.get('linear_openings_candidate',[])
    meta={'source_ids':[p.get('source_id',p.get('source_id_candidate')),'B14_GEOM','G01','CROWN_GENS_AERIAL_V5','CROWN_GENS_PHOTO_V7'],
          'evidence_level':'推导值','asbuilt_verified':False,'geometry_role':'crown_candidate_panel',
          'source_locator':'B14pp16–18/G01pp15–16 lower-grid rule; Gensler supplied crown010 photo',
          'formula':'Lower A parent stations and upright upper-anchored chord extrusion; local aperture subtraction; last parent clipped by unchanged crown trim.',
          'uncertainty':'Same research parent grid as lower tower; final shop net sizes, aperture coordinates and full crown panel schedule unavailable.',
          'station_mapping_evidence':'待确认','fabrication_pattern_verified':False,
          'shared_lower_grid_indices':[s['grid_index'] for s in stations],
          'shared_lower_band_pitch_m':cfg['curtain']['nominal_band_pitch_m']}
    verts=[];faces=[];face_parents=[];records=[];frames=_buffers();keys=set();steps=[];previous=None;omitted=0
    for band,(lo,hi) in enumerate(zip(levels,levels[1:]),1):
        anchor=control_profile_at(geometry,cfg,points,hi)
        for i in range(len(stations)-1):
            a,b=stations[i:i+2];s0,s1=a['s'],b['s']
            # K2 shoulder rows share trim endpoints but remain distinct parents.
            if abs(s1-s0)<1e-12:
                local_open=[];uv0,uv1=0.,1.
            else:local_open=[o for o in openings if o['s_max']>s0 and o['s_min']<s1 and o['z_max_m']>lo and o['z_min_m']<hi];uv0,uv1=s0,s1
            raw=_clipped_vertical_chord((uv0,0),(uv1,0),lo,hi,tops[i],tops[i+1])
            if not raw:continue
            poly=[(q[0],q[2]) for q in raw];pieces=cut_pane(poly,local_open)
            if local_open:omitted+=1
            def xyz(q):
                f=(q[0]-uv0)/(uv1-uv0)
                return (anchor[i][0]+f*(anchor[i+1][0]-anchor[i][0]),anchor[i][1]+f*(anchor[i+1][1]-anchor[i][1]),q[1])
            parent=len(records);normal=_normal([xyz(q) for q in poly])
            for piece in pieces:
                start=len(verts);verts.extend(xyz(q) for q in piece);faces.append(tuple(range(start,start+len(piece))))
                face_parents.append(parent)
            records.append({'parent_panel_id':parent,'band':band,'grid_indices':[a['grid_index'],b['grid_index']],
                            'stations':[s0,s1],'candidate_band_z_range_m':[lo,hi],'child_mesh_faces':len(pieces),
                            'aperture_uv_chart':'local_shoulder_0_1' if abs(s1-s0)<1e-12 else 'global_open_arc_station',
                            'hole_ids':[o['id'] for o in local_open],'remaining_uv_polygons':pieces,'fabrication_pattern_verified':False})
            for v,w in boundary_segments(poly,local_open):
                x,y=xyz(v),xyz(w);key=tuple(sorted(tuple(round(t,8) for t in q) for q in (x,y)))
                if key not in keys and math.dist(x,y)>1e-8:
                    keys.add(key);_append_member(frames,x,y,cfg['curtain']['frame_face_width_display_m'],
                       cfg['curtain']['horizontal_frame_depth_display_m'],normal,parent)
            if previous is not None and pieces and lo<min(tops[i:i+2])-1e-8:
                # Do not run seam closure material across an open ventilation bay.
                if not any(o['s_min']<(s0+s1)/2<o['s_max'] and o['z_min_m']-1e-8<=lo<=o['z_max_m']+1e-8 for o in openings):
                    steps.extend(step_faces((previous[i],previous[i+1]),(anchor[i],anchor[i+1]),lo))
        previous=anchor
    surface=ctx.mesh('CROWN_OPEN_SPLIT_PARABOLA_FIT_DERIVED',verts,faces,'72_CROWN_DERIVED','glass',meta,face_attributes={'crown_parent_panel_id':face_parents})
    frames['verts']=[(x,y,min(z,max(tops))) for x,y,z in frames['verts']]
    ctx.mesh('CROWN_FRAME_UNCONFIRMED_GRID',frames['verts'],frames['faces'],'73_CROWN_FRAME_DISPLAY','steel',
             {**meta,'geometry_role':'crown_frame_display','formula':'Same frame width/depth as lower A; parent boundaries plus actual aperture borders only; no mesh diagonals.'})
    sv=[];sf=[]
    for q in steps:k=len(sv);sv.extend(q);sf.append(tuple(range(k,k+len(q))))
    ctx.mesh('CROWN_V8_SHARED_PARENT_STEP_CLOSURES',sv,sf,'73_CROWN_FRAME_DISPLAY','guide',
             {**meta,'geometry_role':'crown_step_closure_candidate','formula':'Same simple stepped-chord closure method as lower A; actual joint section unresolved.'})
    for name in ('INNER_CROWN_CORNER_BAYS','CORNER_HANGING_MEMBERS','RADIAL_BRACES','TORSION_FRAME','INNER_COLLECTOR_AND_WINDOW_WASHING_TRACK'):
        ctx.empty('CROWN_INTERFACE_'+name,(0,0,levels[0]),'72_CROWN_DERIVED',{**meta,'geometry_role':'unresolved_interface','evidence_level':'待确认'})
    actual=getattr(surface,'data',None)
    vv=[tuple(v.co) for v in actual.vertices] if actual is not None else verts
    maximum=max(v[2] for v in vv);minimum=min(v[2] for v in vv)
    checks=[{'check':'crown_highest_base_mesh_coordinate','passed':abs(maximum-max(tops))<.001,'measured':maximum},
            {'check':'crown_base_elevation','passed':abs(minimum-levels[0])<.001,'measured':minimum},
            {'check':'v8_crown_uses_lower_parent_grid','passed':len(stations)==133 if cfg.get('notch_v4') else len(stations)>10,'measured':len(stations)},
            {'check':'v8_crown_holes_are_local_not_extra_global_bands','passed':566 not in levels and 575 not in levels and omitted>0,'measured':{'bands':len(levels)-1,'parents_cut':omitted}},
            {'check':'v8_crown_remains_open_at_V_lips','passed':math.dist(points[0],points[-1])>1,'measured':math.dist(points[0],points[-1])}]
    for c in checks:c.update(meaning='Generated parent geometry consistency; not as-built fabrication verification',asbuilt_verified=False)
    report={'component':'open_crown_derived','evidence_level':'推导值','asbuilt_verified':False,'surface_role':'crown_candidate_panel',
            'source_ids':meta['source_ids'],'top_cap_present':False,'base_z_m':levels[0],'highest_m':maximum,
            'station_count_display':len(stations),'panel_records':records,'structural_interfaces':5,
            'shared_lower_parent_grid':True,'checks':checks,'software_checks_passed':all(c['passed'] for c in checks)}
    ctx.component_results['completion_crown']=report
    return report
