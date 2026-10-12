"""User correction interfaces; all unmeasured coordinates remain candidates."""
import math


def courtyard_points(p,points):
    controls=p['courtyard_photo_fit_px'];c=[sum(q[k] for q in controls)/len(controls) for k in (0,1)]
    scale=p.get('terrace_scale_v11',[1,1])
    return [[c[k]+(q[k]-c[k])*scale[k] for k in (0,1)] for q in points]


def side_entry_segment(p,t):
    from podium_v9 import sweep_point
    e=p['entrance_v11'];a=sweep_point(p,t,e['roof_cut_u']);z=a[2]
    return a,z


def roof_quadlets(p,t0,t1,u0,u1):
    if p.get('side_v13'):
        from corrections_v13 import roof_quadlets as current
        return current(p,t0,t1,u0,u1)
    from podium_v9 import sweep_point
    e=p.get('entrance_v11')
    if not e:return [[sweep_point(p,t,u) for t,u in ((t0,u0),(t1,u0),(t1,u1),(t0,u1))]]
    start,end=e['t_span'];ts=sorted({t0,t1,*[t for t in (start,end) if t0<t<t1]});out=[]
    for a,b in zip(ts,ts[1:]):
        inside=start<(a+b)/2<end;us=sorted({u0,u1,*([e['roof_cut_u']] if inside and u0<e['roof_cut_u']<u1 else [])})
        for c,d in zip(us,us[1:]):
            if inside and (c+d)/2>=e['roof_cut_u']:continue
            out.append([sweep_point(p,t,u) for t,u in ((a,c),(b,c),(b,d),(a,d))])
    return out


def tile_panels(p,polygons):
    """Clip vertical polygons into actual flat horizontal rectangles with joints."""
    from podium_v9 import _clip_height
    size=p['opaque_tiles_v11'];width,height=size['module_candidate_m'];gap=size['joint_candidate_m'];out=[]
    for poly in polygons:
        if len(poly)<3:continue
        a=poly[0];b=max(poly,key=lambda q:math.dist(a[:2],q[:2]));length=math.dist(a[:2],b[:2])
        if length<gap:continue
        axis=((b[0]-a[0])/length,(b[1]-a[1])/length)
        coords=[((q[0]-a[0])*axis[0]+(q[1]-a[1])*axis[1]) for q in poly]
        def clip(q,value,above):
            result=[];aa=q[-1];da=(((aa[0]-a[0])*axis[0]+(aa[1]-a[1])*axis[1])-value)*(1 if above else -1)
            for bb in q:
                db=(((bb[0]-a[0])*axis[0]+(bb[1]-a[1])*axis[1])-value)*(1 if above else -1)
                if (da>=0)!=(db>=0):
                    f=da/(da-db);result.append(tuple(aa[k]+f*(bb[k]-aa[k]) for k in range(3)))
                if db>=0:result.append(bb)
                aa,da=bb,db
            return result
        z0,z1=min(q[2] for q in poly),max(q[2] for q in poly)
        for i in range(math.ceil((max(coords)-min(coords))/width)):
            left=min(coords)+i*width+gap/2;right=min(max(coords)-gap/2,min(coords)+(i+1)*width-gap/2)
            strip=clip(clip(poly,left,True),right,False)
            if len(strip)<3:continue
            for j in range(math.floor(z0/height),math.ceil(z1/height)):
                band=_clip_height(strip,max(z0,j*height)+gap/2,True)
                if band:band=_clip_height(band,min(z1,(j+1)*height)-gap/2,False)
                if len(band)>2:out.append(band)
    return out


def build_side_entry(ctx,p):
    if p.get('side_v13'):
        from corrections_v13 import build_side
        return build_side(ctx,p)
    if p.get('side_v12'):
        from corrections_v12 import build_side
        return build_side(ctx,p)
    from podium_v9 import _add,_meta,entrance_panels
    e=p['entrance_v11'];start,end=e['t_span'];steps=e['samples'];white=[];glass=[];doors=[];returns=[];cables=[]
    # Local planar charts use full-side accumulated station for the opening.
    points=[side_entry_segment(p,start+(end-start)*i/steps)[0] for i in range(steps+1)]
    lengths=[0.]
    for a,b in zip(points,points[1:]):lengths.append(lengths[-1]+math.dist(a[:2],b[:2]))
    from crown_pattern_v8 import cut_pane
    for index,(a,b) in enumerate(zip(points,points[1:])):
        lo,hi=lengths[index]/lengths[-1],lengths[index+1]/lengths[-1];top=min(a[2],b[2]);white_top=min(e['white_top_candidate_m'],top)
        hole={'s_min':e['door_fraction_candidate'][0],'s_max':e['door_fraction_candidate'][1],'z_min_m':0,'z_max_m':e['door_top_candidate_m']}
        # Recession points toward tower (positive X on the long west side).
        def xyz(q,depth=0):
            f=(q[0]-lo)/(hi-lo);return (a[0]+(b[0]-a[0])*f+depth,a[1]+(b[1]-a[1])*f,q[1])
        white.extend([[xyz(q) for q in poly] for poly in cut_pane([(lo,0),(hi,0),(hi,white_top),(lo,white_top)],[hole])])
        pitch=p['PG_horizontal_pitch_candidate_m'];z=white_top
        while z<top-1e-8:
            upper=min(top,z+pitch);glass.append([xyz(q) for q in [(lo,z),(hi,z),(hi,upper),(lo,upper)]]);cables.append([xyz((lo,z)),xyz((hi,z))]);z=upper
        left,right=max(lo,hole['s_min']),min(hi,hole['s_max'])
        if right>left:
            zz=min(hole['z_max_m'],white_top);doors.append([xyz(q,e['recess_candidate_m']) for q in [(left,0),(right,0),(right,zz),(left,zz)]])
            returns.append([xyz((left,zz)),xyz((right,zz)),xyz((right,zz),e['recess_candidate_m']),xyz((left,zz),e['recess_candidate_m'])])
            for edge in (hole['s_min'],hole['s_max']):
                if lo<=edge<hi:returns.append([xyz((edge,0)),xyz((edge,zz)),xyz((edge,zz),e['recess_candidate_m']),xyz((edge,0),e['recess_candidate_m'])])
    meta=_meta(p,'podium_v11_side_entry_candidate',source_ids=p['source_ids']+['USER_OBSERVATION_V11'],evidence_level='待确认',formula='Long west-side PR mother locally removed at explicit t/u bounds; upper glazing and white recessed entrance share same cut rim; genuine horizontal tile gaps.',uncertainty=e['uncertainty'])
    for name,polys,mat,role in [('PODIUM_V10_BROAD_FACE_WHITE_ENTRY_CUT',tile_panels(p,white),'podium_entry_white','podium_v11_side_entry_candidate'),('PODIUM_V10_GLASS_ABOVE_WHITE_ENTRY',glass,'glass_detail','podium_v11_side_upper_glass_candidate'),('PODIUM_V10_RECESSED_ENTRY_GLAZING',doors,'glass_detail','podium_v11_side_recess_candidate'),('PODIUM_V10_WHITE_ENTRY_RETURNS',returns,'podium_entry_white','podium_v11_side_return_candidate')]:
        v=[];f=[];_add(polys,v,f);o=ctx.mesh(name,v,f,'66_PODIUM_DETAIL_CANDIDATE',mat,{**meta,'geometry_role':role})
        if mat=='podium_entry_white':mod=o.modifiers.new('CLADDING_CANDIDATE','SOLIDIFY');mod.thickness=.12;mod.offset=-1
    ctx.lines('PODIUM_V11_SIDE_GLASS_CABLES',cables,'66_PODIUM_DETAIL_CANDIDATE',p['PG_cable_radius_candidate_m'],'steel',meta)


def cut_transition(ctx,obj,radius,outline,z,thickness):
    import bpy
    from floors_v3 import ray_hole_radius
    p=ctx.config['transition_v5']['interlayer_notch_v11'];v=ctx.config['versions'][ctx.config['selected_geometry_version']]
    angle=math.radians(p['azimuth_relative_candidate_deg']+ctx.config['orientation']['theta0_deg']+ctx.config['orientation']['direction']*v['twist_deg']*(z-v['z0_m'])/(v['z1_m']-v['z0_m']))
    inner=radius+p['inner_clearance_candidate_m'];outer=max(math.hypot(*q) for q in outline)+2
    if outer<=inner:raise ValueError('No A/B annulus for requested transition notch')
    bpy.ops.mesh.primitive_cube_add(size=1,location=((inner+outer)/2*math.cos(angle),(inner+outer)/2*math.sin(angle),z-thickness/2))
    cutter=bpy.context.object;cutter.name='TEMP_V11_TRANSITION_NOTCH';cutter.dimensions=(outer-inner,p['width_candidate_m'],thickness+2);cutter.rotation_euler.z=angle
    bpy.context.view_layer.update();mod=obj.modifiers.new('V11_INTERLAYER_NOTCH','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.context.view_layer.objects.active=obj;obj.select_set(True);bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True);obj.select_set(False)
    obj['interlayer_notch_v11']=True;obj['notch_width_candidate_m']=p['width_candidate_m'];obj['notch_inner_radius_candidate_m']=inner;obj['notch_angle_candidate_deg']=math.degrees(angle)
    return {'width_candidate_m':p['width_candidate_m'],'inner_radius_m':inner,'outer_radius_m':outer,'angle_deg':math.degrees(angle),'evidence_level':'待确认'}


def audit_saved_notches(objects):
    from crown_pattern_v8 import cut_pane
    area=lambda q:abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(q,q[1:]+q[:1])))/2
    rows=[]
    for obj in objects:
        if not obj.get('interlayer_notch_v11'):continue
        angle=math.radians(obj['notch_angle_candidate_deg']);c,s=math.cos(angle),math.sin(angle);top=obj['slab_top_z_m']
        hole={'s_min':obj['notch_inner_radius_candidate_m'],'s_max':max(math.hypot(v.co.x,v.co.y) for v in obj.data.vertices)+2,'z_min_m':-obj['notch_width_candidate_m']/2,'z_max_m':obj['notch_width_candidate_m']/2}
        obj.data.calc_loop_triangles();remaining=0.
        for tri in obj.data.loop_triangles:
            vertices=[obj.data.vertices[i].co for i in tri.vertices]
            if not all(abs(v.z-top)<1e-4 for v in vertices):continue
            q=[(v.x*c+v.y*s,-v.x*s+v.y*c) for v in vertices]
            if sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(q,q[1:]+q[:1]))<0:q.reverse()
            remaining+=max(0.,area(q)-sum(area(poly) for poly in cut_pane(q,[hole])))
        rows.append({'object':obj.name,'remaining_top_slab_area_in_notch_m2':remaining,'passed':remaining<1e-3,'tolerance_basis':'Software float mesh arithmetic; not as-built measurement tolerance'})
    return rows
