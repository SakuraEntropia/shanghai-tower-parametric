"""Shared bowed garden rim and asymmetric rising return; unmeasured candidates."""
import math


def affine_points(p, points):
    controls=p['courtyard_photo_fit_px'];c=[sum(q[k] for q in controls)/len(controls) for k in (0,1)]
    scale=p.get('terrace_scale_v11',[1,1])
    return [[c[k]+(q[k]-c[k])*scale[k] for k in (0,1)] for q in points]


def frame(p):
    from podium_v9 import plan_xy, _sample
    path=[plan_xy(p,q) for q in p['sweep_path_px']]
    a,b=_sample(path,0),_sample(path,.02)
    length=math.dist(a,b);back=((b[0]-a[0])/length,(b[1]-a[1])/length)
    court=[plan_xy(p,q) for q in affine_points(p,p['courtyard_photo_fit_px'])]
    edges=list(zip(court,court[1:]+court[:1]))
    a,b=min(edges,key=lambda ab:sum(q[k]*back[k] for q in ab for k in (0,1)))
    return a,b,back


def bow(p,s):
    return p['raised_end_v15']['front_bow_candidate_m']*math.sin(math.pi*min(1,max(0,s)))


def chart(p,x,y):
    a,b,back=frame(p);dx,dy=b[0]-a[0],b[1]-a[1];den=dx*back[1]-dy*back[0]
    s=((x-a[0])*back[1]-(y-a[1])*back[0])/den
    d=(dx*(y-a[1])-dy*(x-a[0]))/den
    return s,d+bow(p,s)


def low_lip(p,s):
    a,b=p['raised_end_v15']['lower_lip_candidate_m'];s=min(1,max(0,s))
    return a+(b-a)*s*s*(3-2*s)


def point(p,s,v):
    a,b,back=frame(p);e=p['raised_end_v14'];top=p['open_end_v13']['terrace_z_candidate_m']
    phi=math.pi*v/2
    d=e['return_depth_candidate_m']*(1-math.cos(phi))-e['soffit_front_bulge_candidate_m']*math.sin(math.pi*v)-bow(p,s)
    return (a[0]+(b[0]-a[0])*s+back[0]*d,a[1]+(b[1]-a[1])*s+back[1]*d,top-(top-low_lip(p,s))*math.sin(phi))


def courtyard_points(p,points):
    """Keep all other garden features affine; densify only the shared front rim."""
    from podium_v9 import plan_xy
    controls=p['courtyard_photo_fit_px'];out=affine_points(p,points)
    if points!=controls:return out
    a,b,back=frame(p)
    idx=next(i for i,q in enumerate(out) if math.dist(plan_xy(p,q),a)<1e-7)
    # Inverse of the same pixel-to-local-metre mapping, not a second registration.
    scale=p['ground_scale_bar_m']/math.dist(*p['ground_scale_bar_px'])
    angle=math.radians(p['rotation_candidate_deg']);c,s=math.cos(angle),math.sin(angle)
    def pixel(q):
        x,y=q[:2];return [p['tower_center_px'][0]+(x*c+y*s)/scale,p['tower_center_px'][1]-(-x*s+y*c)/scale]
    samples=p['raised_end_v15']['front_samples']
    extra=[pixel(point(p,j/samples,0)) for j in range(1,samples)]
    return out[:idx+1]+extra+out[idx+1:]


def relation(p,cfg):
    from podium_v9 import plan_xy
    import geometry
    from transition_v5 import control_profile_at
    # Raw control centroid gives a stable garden axis independent of tessellation.
    court=[plan_xy(p,q) for q in affine_points(p,p['courtyard_photo_fit_px'])]
    center=tuple(sum(q[k] for q in court)/len(court) for k in (0,1))
    axis=math.degrees(math.atan2(center[1],center[0]))
    points=control_profile_at(geometry,cfg,[(1,0),(-.5,math.sqrt(3)/2),(-.5,-math.sqrt(3)/2)],22)
    angles=[math.degrees(math.atan2(q[1],q[0])) for q in points]
    delta=lambda q:abs((axis-q+180)%360-180)
    return {'garden_axis_candidate_deg':axis,'convex_corner_angle_error_deg':min(delta(q) for q in angles[:2]),
            'reentrant_V_angle_error_deg':delta(angles[2]),'shared_plan_rotation_candidate_deg':p['rotation_candidate_deg'],
            'passed':min(delta(q) for q in angles[:2])<18 and delta(angles[2])>90,
            'scope':'Relative convex-corner phase in candidate local coordinates; not surveyed north/alignment.'}


def audit(objects,p,cfg):
    """Read saved garden/glass vertices; model tolerances are not survey errors."""
    r=relation(p,cfg)
    garden=next((o for o in objects if o.name=='PODIUM_V9_OPEN_PLANTED_TERRACE'),None)
    glass=next((o for o in objects if o.name=='PODIUM_V15_LOCAL_FRONT_GLAZING'),None)
    trim=next((o for o in objects if o.name=='PODIUM_V15_CURVED_LOWER_EDGE_TRIM'),None)
    if not garden or not glass or not trim:return {**r,'passed':False,'missing_v15_end_objects':True}
    center=[sum((garden.matrix_world@v.co)[k] for v in garden.data.vertices)/len(garden.data.vertices) for k in (0,1)]
    angle=math.degrees(math.atan2(center[1],center[0]))
    import geometry
    from transition_v5 import control_profile_at
    q=control_profile_at(geometry,cfg,[(-.5,math.sqrt(3)/2)],22)[0]
    actual_delta=abs((angle-math.degrees(math.atan2(q[1],q[0]))+180)%360-180)
    actual_glass=[(glass.matrix_world@v.co).z for v in glass.data.vertices]
    top=p['open_end_v13']['terrace_z_candidate_m'];bottom=top-p['raised_end_v15']['front_glazing_height_candidate_m']
    blocked=[];lo,hi=p['raised_end_v15']['front_glazing_fraction_candidate']
    from site_v8 import contains,ccw,hull
    from podium_v9 import plan_xy
    court=ccw(hull([plan_xy(p,q) for q in courtyard_points(p,p['courtyard_photo_fit_px'])]))
    upper_court=[]
    for o in objects:
        if o.name.startswith('PODIUM_V9_UPPER_SLAB_'):
            if any(v.co.z>top+.001 and contains(court,(v.co.x,v.co.y)) for v in o.data.vertices):upper_court.append(o.name)
        if o.name not in ('PODIUM_V14_RAISED_CURVED_RETURN_PR_PANELS','PODIUM_V14_RAISED_RETURN_WATERPROOF_BACKING'):continue
        for face in o.data.polygons:
            vs=[o.matrix_world@o.data.vertices[i].co for i in face.vertices]
            s,_=chart(p,sum(v.x for v in vs)/len(vs),sum(v.y for v in vs)/len(vs))
            if lo+.002<s<hi-.002 and min(v.z for v in vs)>bottom+.005:blocked.append([o.name,face.index])
    r.update(actual_garden_axis_candidate_deg=angle,actual_garden_convex_angle_error_deg=actual_delta,
             actual_front_glass_z_range_m=[min(actual_glass),max(actual_glass)],gold_or_backing_covering_front_glass=blocked[:10],
             actual_lower_trim_z_range_m=[min(v.co.z for v in trim.data.vertices),max(v.co.z for v in trim.data.vertices)],
             upper_slabs_occupying_open_garden=upper_court)
    r['passed']=r['passed'] and actual_delta<18 and min(actual_glass)>=bottom-.03 and max(actual_glass)<=top+.03 and not blocked and not upper_court
    return r
