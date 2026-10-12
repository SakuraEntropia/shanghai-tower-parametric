"""SWA-photo topology: raised return soffit, recessed base, visible pier proxy.

Metric curves/sections remain candidates. Ground commercial floor is retained;
the outer terrace wrapper is not an invented glass wall down to grade.
"""
import math


def frame(p):
    if p.get('raised_end_v15'):
        from raised_end_v15 import frame as current
        return current(p)
    from podium_v9 import plan_xy,_sample
    from corrections_v11 import courtyard_points
    path=[plan_xy(p,q) for q in p['sweep_path_px']]
    a,b=_sample(path,0),_sample(path,.02);dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);back=(dx/length,dy/length)
    court=[plan_xy(p,q) for q in courtyard_points(p,p['courtyard_photo_fit_px'])]
    edges=list(zip(court,court[1:]+court[:1]));a,b=min(edges,key=lambda ab:sum(q[k]*back[k] for q in ab for k in (0,1)))
    return a,b,back


def chart(p,x,y):
    if p.get('raised_end_v15'):
        from raised_end_v15 import chart as current
        return current(p,x,y)
    a,b,back=frame(p);dx,dy=b[0]-a[0],b[1]-a[1];den=dx*back[1]-dy*back[0]
    return (((x-a[0])*back[1]-(y-a[1])*back[0])/den,
            (dx*(y-a[1])-dy*(x-a[0]))/den)


def point(p,s,v):
    if p.get('raised_end_v15'):
        from raised_end_v15 import point as current
        return current(p,s,v)
    a,b,back=frame(p);e=p['raised_end_v14'];top=p['open_end_v13']['terrace_z_candidate_m']
    low=e['clearance_candidate_m']+e['edge_clearance_extra_candidate_m']*(2*s-1)**2
    phi=math.pi*v/2;d=e['return_depth_candidate_m']*(1-math.cos(phi))-e['soffit_front_bulge_candidate_m']*math.sin(math.pi*v)
    return (a[0]+(b[0]-a[0])*s+back[0]*d,a[1]+(b[1]-a[1])*s+back[1]*d,top-(top-low)*math.sin(phi))


def floor_allowed(p,x,y,z,margin=0):
    if not p.get('raised_end_v14',{}).get('enabled') or z<=0:return True
    s,d=chart(p,x,y)
    if not -.3<=s<=1.3:return True
    s=min(1,max(0,s))
    top=p['open_end_v13']['terrace_z_candidate_m'];e=p['raised_end_v14']
    if z>=top:return True
    if p.get('raised_end_v15'):
        from raised_end_v15 import low_lip
        low=low_lip(p,s)
    else:low=e['clearance_candidate_m']+e['edge_clearance_extra_candidate_m']*(2*s-1)**2
    if z<=low:required=e['return_depth_candidate_m']
    else:
        phi=math.asin(min(1,max(0,(top-z)/(top-low))))
        required=e['return_depth_candidate_m']*(1-math.cos(phi))-e['soffit_front_bulge_candidate_m']*math.sin(2*phi)
    return d>=required+margin


def base_allowed(p,x,y):
    if not p.get('raised_end_v14',{}).get('enabled'):return True
    s,d=chart(p,x,y)
    return not (-.3<=s<=1.3 and d<p['raised_end_v14']['return_depth_candidate_m'])


def shell_join(p,s,z):
    """Connect to the existing shell at the same height, without a loose cap."""
    from podium_v9 import sweep_point
    target=p['raised_end_v14']['return_depth_candidate_m']
    limit=p['raised_end_v14']['roof_transition_t_candidate']
    t=min((limit*i/80 for i in range(81)),key=lambda t:abs(chart(p,*sweep_point(p,t,.5)[:2])[1]-target))
    rows=[sweep_point(p,t,i/240) for i in range(241)];hits=[]
    for a,b in zip(rows,rows[1:]):
        if (a[2]-z)*(b[2]-z)<0:
            f=(z-a[2])/(b[2]-a[2]);hits.append(tuple(a[k]+f*(b[k]-a[k]) for k in range(3)))
    if len(hits)!=2:raise ValueError('Raised side cannot meet the existing shell at requested height')
    return hits[0 if s==0 else -1]


def build(ctx,p,unused_poly=None):
    from podium_v9 import _meta,_add
    from podium_panels_v7 import planarize
    from mathutils import Vector
    e=p['raised_end_v14'];a,b,back=frame(p);col='66_PODIUM_DETAIL_CANDIDATE'
    print('V14_CANDIDATE_END_PARAMETERS', {k:e[k] for k in ('clearance_candidate_m','return_depth_candidate_m','display_pier_section_candidate_m','display_pier_foot_depth_candidate_m','display_pier_head_v_candidate')}, e['uncertainty'], flush=True)
    m=_meta(p,'podium_v14_raised_return_soffit_candidate',source_ids=p['source_ids'],evidence_level='待确认',
            source_locator='SWA Shanghai Tower gallery, Jonnu Singleton-0013; source image URL recorded in SOURCES_JSON',
            formula='Terrace front edge and soffit share one published-plan/photo-fit chart; smooth sin/cos return to recessed4.2m candidate lower lip. Surface is panelized geometry, no texture substitute.',
            uncertainty=e['uncertainty'],raised_end_controls_v14=e,front_edge_xy_m=[a,b])
    latest=p.get('raised_end_v15')
    if latest:
        print('V15_CANDIDATE_END_CONTROLS',latest,flush=True)
        m.update(geometry_role='podium_v15_asymmetric_raised_return_candidate',raised_end_controls_v15=latest,
                 formula='One bowed garden rim; smoothstep lateral lower lip, sin/cos return. Front glass physically replaces upper PR/backing; metric controls uncalibrated.',
                 uncertainty=latest['uncertainty'])
    verts=[];faces=[];ids=[];backv=[];backf=[];glazing=[];glass_ids=[];trim=[]
    ns=math.ceil(math.dist(a,b)/e['panel_module_reference_m'][0])
    sample=[point(p,.5,i/e['return_samples']) for i in range(e['return_samples']+1)]
    nv=math.ceil(sum(math.dist(q,r) for q,r in zip(sample,sample[1:]))/e['panel_module_reference_m'][1])
    stations=sorted(set([i/ns for i in range(ns+1)]+(latest['front_glazing_fraction_candidate'] if latest else [])))
    for i,(s0,s1) in enumerate(zip(stations,stations[1:])):
        for j in range(nv):
            quad=[point(p,s,v) for s,v in ((s0,j/nv),(s1,j/nv),(s1,(j+1)/nv),(s0,(j+1)/nv))]
            flat,n,_=planarize(quad,p['PR_joint_reported_m'])
            if not flat:continue
            if latest and latest['front_glazing_fraction_candidate'][0]<(s0+s1)/2<latest['front_glazing_fraction_candidate'][1]:
                from podium_v9 import _clip_height
                cutoff=p['open_end_v13']['terrace_z_candidate_m']-latest['front_glazing_height_candidate_m']
                glass=_clip_height(flat,cutoff,True)
                if len(glass)>2:glazing.append(glass);glass_ids.append(i*nv+j)
                flat=_clip_height(flat,cutoff,False)
                if len(flat)<3:continue
            _add([flat],verts,faces);ids.append(i*nv+j)
            _add([[tuple(q[k]-n[k]*p['PR_backing_offset_candidate_m'] for k in range(3)) for q in flat]],backv,backf)
    obj=ctx.mesh('PODIUM_V14_RAISED_CURVED_RETURN_PR_PANELS',verts,faces,col,'pr_gold_glass',m,face_attributes={'raised_PR_panel_id':ids})
    mod=obj.modifiers.new('LAMINATE_REPORTED_SOURCE_VERSION','SOLIDIFY');mod.thickness=sum(p['PR_laminate_reported_m']);mod.offset=-1
    ctx.mesh('PODIUM_V14_RAISED_RETURN_WATERPROOF_BACKING',backv,backf,col,'dark_backing',m)
    if glazing:
        vv=[];ff=[];_add(glazing,vv,ff)
        gl=ctx.mesh('PODIUM_V15_LOCAL_FRONT_GLAZING',vv,ff,col,'glass_detail',{**m,'geometry_role':'podium_v15_front_glass_candidate'},face_attributes={'front_parent_panel_id':glass_ids})
        mod=gl.modifiers.new('GLASS_THICKNESS_CANDIDATE','SOLIDIFY');mod.thickness=p['side_v13']['glass_thickness_candidate_m'];mod.offset=-1
    if latest:
        for s0,s1 in zip(stations,stations[1:]):
            q,r=point(p,s0,1),point(p,s1,1);w=latest['lower_edge_trim_width_candidate_m']
            trim.append([q,r,(r[0],r[1],r[2]+w),(q[0],q[1],q[2]+w)])
        vv=[];ff=[];_add(trim,vv,ff)
        ctx.mesh('PODIUM_V15_CURVED_LOWER_EDGE_TRIM',vv,ff,col,'podium_entry_white',{**m,'geometry_role':'podium_v15_lower_edge_trim_candidate'})
    # Side returns meet the original shell, instead of leaving a loose cap.
    sides=[]
    for s in (0.,1.):
        for j in range(nv):
            q,r=point(p,s,j/nv),point(p,s,(j+1)/nv)
            u,v=shell_join(p,s,q[2]),shell_join(p,s,r[2])
            n=math.ceil(max(math.dist(q,u),math.dist(r,v))/e['panel_module_reference_m'][0])
            for k in range(n):
                def mix(a,b,f):return tuple(a[i]+(b[i]-a[i])*f for i in range(3))
                flat,_,_=planarize([mix(q,u,k/n),mix(r,v,k/n),mix(r,v,(k+1)/n),mix(q,u,(k+1)/n)],p['PR_joint_reported_m'])
                if flat:sides.append(flat)
    vv=[];ff=[];_add(sides,vv,ff);ctx.mesh('PODIUM_V14_RAISED_SIDE_RETURN_CANDIDATE',vv,ff,col,'pr_gold_glass',m)
    # Base interface behind the overhang, independently controlled.
    glass=[];top=e['setback_glass_top_candidate_m'];pitch=p['PG_horizontal_pitch_candidate_m']
    for i in range(ns):
        q,r=point(p,i/ns,1),point(p,(i+1)/ns,1)
        for j in range(math.ceil(top/pitch)):
            lo=j*pitch;hi=min(top,(j+1)*pitch)
            glass.append([(q[0],q[1],lo),(r[0],r[1],lo),(r[0],r[1],hi),(q[0],q[1],hi)])
    vv=[];ff=[];_add(glass,vv,ff)
    ctx.mesh('PODIUM_V14_RECESSED_GROUND_COMMERCIAL_GLASS',vv,ff,col,'glass_detail',{**m,'geometry_role':'podium_v14_recessed_base_candidate'})
    guard=[];z=p['open_end_v13']['terrace_z_candidate_m'];height=p['open_end_v13']['guard_height_candidate_m']
    guard.append([(q[0],q[1],z+height) for q in (point(p,s,0) for s in stations)])
    for i in range(ns+1):
        q=point(p,i/ns,0);guard.append([q,(q[0],q[1],z+height)])
    ctx.lines('PODIUM_V14_RAISED_TERRACE_FRONT_GUARD',guard,col,.035,'steel',m)
    # One photograph-visible support proxy, with explicit unknown coordinates.
    s=e['display_pier_fraction_candidate'];head=point(p,s,e['display_pier_head_v_candidate']);rim=point(p,s,0)
    foot=(rim[0]+back[0]*e['display_pier_foot_depth_candidate_m'],rim[1]+back[1]*e['display_pier_foot_depth_candidate_m'],0)
    length=math.dist(foot,head);size=e['display_pier_section_candidate_m']
    pier=ctx.box('PODIUM_V14_VISIBLE_INCLINED_PIER_PROXY',tuple((x+y)/2 for x,y in zip(foot,head)),(*size,length),col,'core',
                 {**m,'geometry_role':'podium_v14_visible_inclined_pier_proxy','uncertainty':e['uncertainty']+' Only one visible-support proxy; this is not a total as-built support count.'})
    pivot=Vector(tuple((x+y)/2 for x,y in zip(foot,head)));rotation=(Vector(head)-Vector(foot)).to_track_quat('Z','Y')
    for vertex in pier.data.vertices:vertex.co=pivot+rotation@(vertex.co-pivot)
    import json
    pier['candidate_axis_endpoints_m']=json.dumps([foot,head])


def audit(objects,p):
    from site_v8 import xy
    solids=[o for o in objects if o.type=='MESH' and o.name.startswith(('PODIUM_V14_RAISED_CURVED_RETURN_PR','PODIUM_V14_RAISED_RETURN_WATER','PODIUM_V14_RAISED_SIDE_RETURN'))]
    actual_min=min((o.matrix_world@v.co).z for o in solids for v in o.data.vertices) if solids else None
    legacy=[o.name for o in objects if o.name.startswith(('PODIUM_V13_OPEN_END_LOWER_GLAZING','PODIUM_V13_OPEN_END_STONE_FASCIA'))]
    slab_bad=[]
    for obj in objects:
        if not obj.name.startswith('PODIUM_V9_UPPER_SLAB_'):continue
        for v in obj.data.vertices:
            if not floor_allowed(p,v.co.x,v.co.y,v.co.z,margin=-.005):slab_bad.append(obj.name);break
    import json
    sp=json.loads(next(o['source_ids'] for o in objects if o.name=='PODIUM_V14_RAISED_CURVED_RETURN_PR_PANELS')) if solids else []
    pier=next((o for o in objects if o.name=='PODIUM_V14_VISIBLE_INCLINED_PIER_PROXY'),None);axis_errors=[];caps=[]
    if pier:
        expected=json.loads(pier['candidate_axis_endpoints_m'])
        caps=[tuple(sum((pier.matrix_world@v.co)[k] for v in list(pier.data.vertices)[i:i+4])/4 for k in range(3)) for i in (0,4)]
        axis_errors=[math.dist(a,b) for a,b in zip(expected,caps)]
    return {'raised_wrapper_min_z_m':actual_min,'old_ground_end_glass_or_fascia':legacy,'floor_conflicts':slab_bad,
            'SWA_source_embedded':'SWA_RAISED_END_V14' in sp,'terrace_front_edge_xy_m':frame(p)[:2],
            'pier_actual_cap_centroids_m':caps,'pier_axis_errors_m':axis_errors,
            'passed':actual_min is not None and actual_min>=p['raised_end_v14']['clearance_candidate_m']-.12 and not legacy and not slab_bad and 'SWA_RAISED_END_V14' in sp and bool(axis_errors) and max(axis_errors)<.001 and abs(caps[0][2])<.001,
            'scope':'Candidate clearance and software interface; not surveyed real-world position or clearance.'}
