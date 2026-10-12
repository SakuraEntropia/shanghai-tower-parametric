"""Replace v4-8 podium mother with plan trace + tangent composite-arc sweep.
Public contractor topology guides the method; no recovered shop CAD assertion.
"""
import math
from bisect import bisect_left


def plan_xy(p,q):
    a,b=p['ground_scale_bar_px'];s=p['ground_scale_bar_m']/math.dist(a,b);cx,cy=p['tower_center_px']
    x,y=(q[0]-cx)*s,(cy-q[1])*s;t=math.radians(p['rotation_candidate_deg'])
    return (x*math.cos(t)-y*math.sin(t),x*math.sin(t)+y*math.cos(t))


def local_ground_opaque_band(p,mid):
    """Keep the existing candidate PS zoning attached to its plan frame."""
    reference=p.get('ground_band_reference_rotation_candidate_deg',p['rotation_candidate_deg'])
    angle=math.radians(p['rotation_candidate_deg']-reference)
    x=mid[0]*math.cos(angle)+mid[1]*math.sin(angle)
    return x>p.get('ground_band_reference_x_min_candidate_m',-24)


def rounded_poly(poly,radius,steps=8):
    out=[]
    for i,b in enumerate(poly):
        a,c=poly[i-1],poly[(i+1)%len(poly)];da,dc=math.dist(a,b),math.dist(b,c)
        d=min(radius,da*.3,dc*.3)
        q=tuple(b[k]+(a[k]-b[k])*d/da for k in range(2));r=tuple(b[k]+(c[k]-b[k])*d/dc for k in range(2))
        for j in range(steps+1):
            u=j/steps;out.append(tuple((1-u)**2*q[k]+2*u*(1-u)*b[k]+u*u*r[k] for k in range(2)))
    return out


def arc_section(p,samples=24):
    """Tangent-continuous chain of true circular arcs, followed by tangent tail."""
    x,z=p['section_start_candidate_m'];theta=math.radians(p['section_start_tangent_candidate_deg']);pts=[(x,z)]
    for seg in p['section_arc_chain_candidate']:
        turn=math.radians(seg['turn_deg']);signed_r=math.copysign(seg['radius_m'],turn)
        for j in range(1,samples+1):
            phi=theta+turn*j/samples
            pts.append((x+signed_r*(math.sin(phi)-math.sin(theta)),z-signed_r*(math.cos(phi)-math.cos(theta))))
        x,z=pts[-1];theta+=turn
    length=(p['section_end_target_candidate_m']-z)/math.sin(theta)
    for j in range(1,9):pts.append((x+length*j/8*math.cos(theta),z+length*j/8*math.sin(theta)))
    scale=p['section_peak_reported_m']/max(q[1] for q in pts)
    return [(x*scale,z*scale) for x,z in pts]


def _sample(points,fraction):
    lengths=[0.]
    for a,b in zip(points,points[1:]):lengths.append(lengths[-1]+math.dist(a,b))
    target=max(0,min(1,fraction))*lengths[-1];i=max(1,min(len(lengths)-1,bisect_left(lengths,target)))
    u=(target-lengths[i-1])/(lengths[i]-lengths[i-1])
    return tuple(points[i-1][k]+u*(points[i][k]-points[i-1][k]) for k in range(len(points[0])))


def sweep_point(p,t,u):
    path=[plan_xy(p,q) for q in p['sweep_path_px']];c=_sample(path,t)
    a,b=_sample(path,max(0,t-.001)),_sample(path,min(1,t+.001));dx,dy=b[0]-a[0],b[1]-a[1];d=math.hypot(dx,dy)
    rows=p['section_modulation_candidate'];k=max(0,min(len(rows)-2,next((i-1 for i,r in enumerate(rows) if r[0]>=t),len(rows)-2)))
    a0,a1=rows[k],rows[k+1];f=(t-a0[0])/(a1[0]-a0[0]);ws,hs,roll=[a0[j]+f*(a1[j]-a0[j]) for j in (1,2,3)]
    v,z=_sample(arc_section(p),u);v*=ws;z*=hs
    # A spatially varying longitudinal path and cross-section roll create the
    # doubly curved PR surface. Controls are candidate fits, not measured axes.
    z+=v*math.sin(math.radians(roll))
    return (c[0]-dy/d*v,c[1]+dx/d*v,max(0,z)*p.get('roof_global_z_scale_candidate',1.))


def _meta(p,role,**extra):
    return {'source_ids':p['source_ids'],'evidence_level':'推导值','numeric_evidence_level':'待确认','asbuilt_verified':False,
            'geometry_role':role,'source_locator':'Architectural Journal2019|03p31 ground / Lingyun Figs6,8,12,18,22,23 / actual Gensler aerial',
            'formula':'Scaled ground plan20m/102px; composite tangent circular-arc sections lofted along explicit spatial path; east open outer skin; west trimmed at reported4.2m candidate baseline; complete closed soffit/axis9 remains unresolved.',
            'uncertainty':p['uncertainty'],**extra}


def _add(polys,verts,faces):
    for poly in polys:
        k=len(verts);verts.extend(poly);faces.append(tuple(range(k,k+len(poly))))


def _cut3d(poly,holes):
    from crown_v5 import _cut_polygons
    from site_v8 import ccw,contains
    a,b,c=poly[:3];v=[b[i]-a[i] for i in range(3)];w=[c[i]-a[i] for i in range(3)]
    n=(v[1]*w[2]-v[2]*w[1],v[2]*w[0]-v[0]*w[2],v[0]*w[1]-v[1]*w[0])
    if abs(n[2])<1e-9:
        q=tuple(sum(x[i] for x in poly)/len(poly) for i in (0,1))
        return [] if any(contains(h,q) for h in holes) else [poly]
    xy=ccw([q[:2] for q in poly]);pieces=_cut_polygons([xy],holes)
    return [[(x,y,a[2]-(n[0]*(x-a[0])+n[1]*(y-a[1]))/n[2]) for x,y in q] for q in pieces]


def _clip_height(poly,z,above):
    out=[];sign=1 if above else -1;a=poly[-1];da=(a[2]-z)*sign
    for b in poly:
        db=(b[2]-z)*sign
        if (da>=0)!=(db>=0):
            t=da/(da-db);out.append(tuple(a[k]+t*(b[k]-a[k]) for k in range(3)))
        if db>=0:out.append(b)
        a,da=b,db
    return out


def entrance_zone(p,a,b):
    """One explicit candidate region on the existing broad curved facade."""
    e=p.get('entrance_v10')
    if not e or e.get('target_arch_end') is not None or p.get('entrance_v11'):return None
    y0,y1=e['y_span_candidate_m'];x=(a[0]+b[0])/2;y=(a[1]+b[1])/2
    if x<=e['front_x_min_candidate_m'] or not y0<=y<=y1:return None
    return e


def entrance_panels(p,a,b,top):
    """Cut actual facade polygons; do not cover old glass with a white plate."""
    from crown_pattern_v8 import cut_pane
    e=p['entrance_v10'];y0,y1=e['y_span_candidate_m']
    u0,u1=(a[1]-y0)/(y1-y0),(b[1]-y0)/(y1-y0)
    if abs(u1-u0)<1e-9:return [],[],[],[]
    lo,hi=sorted((u0,u1));white_top=min(top,e['white_top_candidate_m'])
    door_top=min(white_top,e['door_top_candidate_m'])
    lower=[(lo,0),(hi,0),(hi,white_top),(lo,white_top)]
    hole={'s_min':e['door_fraction_candidate'][0],'s_max':e['door_fraction_candidate'][1],
          'z_min_m':0,'z_max_m':door_top}
    def xyz(q,depth=0):
        u,z=q;t=(u-u0)/(u1-u0)
        # This broad face is on the east side; recession is toward the interior.
        return (a[0]+(b[0]-a[0])*t-depth,a[1]+(b[1]-a[1])*t,z)
    white=[[xyz(q) for q in poly] for poly in cut_pane(lower,[hole])]
    upper=[]
    if top>white_top:upper=[[xyz(q) for q in [(lo,white_top),(hi,white_top),(hi,top),(lo,top)]]]
    doors=[];reveals=[];left=max(lo,hole['s_min']);right=min(hi,hole['s_max'])
    if right>left:
        door=[(left,0),(right,0),(right,door_top),(left,door_top)]
        doors=[[xyz(q,e['recess_candidate_m']) for q in door]]
        reveals.append([xyz((left,door_top)),xyz((right,door_top)),xyz((right,door_top),e['recess_candidate_m']),xyz((left,door_top),e['recess_candidate_m'])])
        for edge in (hole['s_min'],hole['s_max']):
            if lo<=edge<hi:reveals.append([xyz((edge,0)),xyz((edge,door_top)),xyz((edge,door_top),e['recess_candidate_m']),xyz((edge,0),e['recess_candidate_m'])])
    return white,upper,doors,reveals


def arch_entry_panels(p,end,poly):
    """White cut and glass share one true end-section boundary."""
    from crown_pattern_v8 import cut_pane
    from site_v8 import ccw
    e=p['entrance_v10'];a,b=poly[0],poly[-1];width=math.dist(a[:2],b[:2])
    axis=((b[0]-a[0])/width,(b[1]-a[1])/width)
    uv=ccw([(((q[0]-a[0])*axis[0]+(q[1]-a[1])*axis[1])/width,q[2]) for q in poly])
    path=[plan_xy(p,q) for q in p['sweep_path_px']];inside=_sample(path,.01 if end==0 else .99);rim=_sample(path,end)
    depth_axis=(inside[0]-rim[0],inside[1]-rim[1]);length=math.hypot(*depth_axis);depth_axis=tuple(q/length for q in depth_axis)
    def xyz(q,depth=0):return (a[0]+axis[0]*q[0]*width+depth_axis[0]*depth,a[1]+axis[1]*q[0]*width+depth_axis[1]*depth,q[1])
    def clip(q,z,above):return [(v[0],v[2]) for v in _clip_height([(u,0,v) for u,v in q],z,above)]
    lower=clip(uv,e['white_top_candidate_m'],False)
    hole={'s_min':e['door_fraction_candidate'][0],'s_max':e['door_fraction_candidate'][1],'z_min_m':0,'z_max_m':e['door_top_candidate_m']}
    white=[[xyz(q) for q in piece] for piece in cut_pane(lower,[hole])]
    upper=[]
    pitch=p['PG_horizontal_pitch_candidate_m'];z=e['white_top_candidate_m']
    while z<max(q[1] for q in uv):
        band=clip(clip(uv,z,True),z+pitch,False)
        if len(band)>2:upper.append([xyz(q) for q in band])
        z+=pitch
    door=[(hole['s_min'],0),(hole['s_max'],0),(hole['s_max'],hole['z_max_m']),(hole['s_min'],hole['z_max_m'])]
    doors=[[xyz(q,e['recess_candidate_m']) for q in door]];returns=[]
    for left,right in zip(door[1:],door[2:]+door[:1]):
        returns.append([xyz(left),xyz(right),xyz(right,e['recess_candidate_m']),xyz(left,e['recess_candidate_m'])])
    return white,upper,doors,returns


def arch_endcaps(ctx,p,tower):
    """The glass boundary is the SAME section as the PR curved roof rim."""
    v=[];f=[];cables=[];frames=[]
    for end in (0.,1.):
        poly=[sweep_point(p,end,i/160) for i in range(161)]
        if p.get('open_end_v13',{}).get('end')==end:
            from corrections_v13 import build_open_end
            build_open_end(ctx,p,poly)
            continue
        height=max(q[2] for q in poly);pitch=p['PG_horizontal_pitch_candidate_m']
        entry=p.get('entrance_v10',{}).get('target_arch_end')==end
        if entry:
            white,upper,doors,returns=arch_entry_panels(p,end,poly)
            em=_meta(p,'podium_v10_white_entry_candidate',source_ids=p['source_ids']+['USER_OBSERVATION_V10'],evidence_level='待确认',formula='Wider arch end from same PR mother section; white lower region physically cut for recessed entry, upper glass shares exact arch boundary.',uncertainty=p['entrance_v10']['uncertainty'])
            for name,polys,material,role in [('PODIUM_V10_BROAD_FACE_WHITE_ENTRY_CUT',white,'podium_entry_white','podium_v10_white_entry_candidate'),('PODIUM_V10_GLASS_ABOVE_WHITE_ENTRY',upper,'glass_detail','podium_v10_upper_entry_glass_candidate'),('PODIUM_V10_RECESSED_ENTRY_GLAZING',doors,'glass_detail','podium_v10_recessed_entry_glass_candidate'),('PODIUM_V10_WHITE_ENTRY_RETURNS',returns,'podium_entry_white','podium_v10_entry_return_candidate')]:
                vv=[];ff=[]
                _add(polys,vv,ff);obj=ctx.mesh(name,vv,ff,'66_PODIUM_DETAIL_CANDIDATE',material,{**em,'geometry_role':role})
                if material=='podium_entry_white':mod=obj.modifiers.new('WHITE_CLADDING_CANDIDATE','SOLIDIFY');mod.thickness=.12;mod.offset=-1
            for band in upper:
                for a,b in zip(band,band[1:]+band[:1]):
                    if abs(a[2]-b[2])<1e-6:cables.append([a,b])
            frames.append(poly)
            continue
        for row in range(math.ceil(height/pitch)):
            cut=_clip_height(poly,row*pitch,True)
            if cut:cut=_clip_height(cut,min(height,(row+1)*pitch),False)
            if len(cut)<3:continue
            _add(_cut3d(cut,[tower]),v,f)
            for a,b in zip(cut,cut[1:]+cut[:1]):
                if abs(a[2]-b[2])<1e-6:cables.append([a,b])
        frames.append(poly)
    m=_meta(p,'podium_roof_aligned_PG_arch_glazing_candidate',source_ids=p['source_ids'],open_end_excluded=p.get('open_end_v13',{}).get('end',-1),formula='End-section PG candidates directly clipped from the identical composite-arc roof rim; horizontal point/cable bands; no independent tall perimeter glass box.',source_support='Lingyun PG1/PG3 local point-supported systems and five-arc boundary principle; actual Gensler tall arched opening. Exact shop station mapping remains unverified.')
    ctx.mesh('PODIUM_V9_PG_ARCHES_SHARE_PR_SECTION_BOUNDARY',v,f,'66_PODIUM_DETAIL_CANDIDATE','glass_detail',m)
    ctx.lines('PODIUM_V9_PG_ARCH_RIMS_AND_FINE_HORIZONTAL_CABLES',frames+cables,'66_PODIUM_DETAIL_CANDIDATE',p['PG_cable_radius_candidate_m'],'steel',m)
    return len(f)


def pr_panels(p,tower):
    from podium_panels_v7 import planarize
    from site_v8 import ccw,hull
    path=[plan_xy(p,q) for q in p['sweep_path_px']];length=sum(math.dist(a,b) for a,b in zip(path,path[1:]))
    nc=math.ceil(length/p['PR_nominal_length_reported_m']);section=arc_section(p);arclength=sum(math.dist(a,b) for a,b in zip(section,section[1:]))
    # Equal closed-section fractions avoid a free residual-tooth seam. Their
    # final physical widths depend on the unrecovered loft/axis9 geometry.
    from corrections_v11 import courtyard_points,roof_quadlets
    nr=round(arclength/p['PR_east_width_reported_m']);court=ccw(hull([plan_xy(p,q) for q in courtyard_points(p,p['courtyard_photo_fit_px'])]))
    regions={'EAST':[],'WEST':[]};errors=[];ids=0
    for i in range(nc):
        t0,t1=i/nc,(i+1)/nc;side='WEST' if (t0+t1)/2<p['axis9_candidate_fraction'] else 'EAST'
        for j in range(nr):
            u0,u1=j/nr,(j+1)/nr
            for quad in roof_quadlets(p,t0,t1,u0,u1):
                if side=='WEST' and max(q[2] for q in quad)<p['west_PR_start_reported_m']:continue
                flat,n,error=planarize(quad,p['PR_joint_reported_m'])
                if not flat:continue
                holes=[tower]
                if min(q[2] for q in flat)>p['terrace_candidate_m']-.2:holes.append(court)
                for poly in _cut3d(flat,holes):
                    if p.get('raised_end_v14',{}).get('enabled') and (t0+t1)/2<p['raised_end_v14']['roof_transition_t_candidate']:
                        poly=_clip_height(poly,p['raised_end_v14']['clearance_candidate_m'],True)
                        if len(poly)<3:continue
                    regions[side].append((poly,n,ids));ids+=1;errors.append(error)
    return regions,{'candidate_panels':ids,'max_flattening_error_m':max(errors,default=0),'longitudinal_intervals':nc,'cross_section_intervals':nr,
                    'published_nominal_length_m':1.8,'published_east_width_m':.3,'axis9_coordinates_verified':False,'closed_west_shop_curve_verified':False}


def rain_canopy(ctx,geometry,p):
    if p.get('canopy_v12'):
        from corrections_v12 import fine_canopy
        return fine_canopy(ctx,geometry,p)
    from transition_v5 import outer_reference,control_profile_at
    _,ref=outer_reference(geometry,ctx.config);profile=control_profile_at(geometry,ctx.config,ref,0)
    q=p['south_rain_canopy'];lo,hi=q['profile_fraction_candidate'];n=len(profile);ids=list(range(round(lo*n),round(hi*n)+1))
    quads=[];ribs=[];edges=[]
    for ia,ib in zip(ids,ids[1:]):
        a,b=profile[ia%n],profile[ib%n];pts=[]
        for k,v in ((0,a),(1,b),(1,b),(0,a)):
            width=0 if len(pts)<2 else q['width_candidate_m'];r=math.hypot(v[0],v[1]);pts.append((v[0]*(1+width/r),v[1]*(1+width/r),q['z_candidate_m']+.02*width))
        quads.append(pts)
        aa,bb=pts[0],pts[3];ribs.append([(x,y,z-q['glass_rib_clearance_candidate_m']) for x,y,z in (aa,bb)])
        edges.append([pts[3],pts[2]])
    m=_meta(p,'podium_first_floor_partial_rain_canopy_candidate',source_locator=q['source_locator'],formula='Partial A ground profile segment; outward fan strips and subordinate radial stainless ribs; elevation, width and arc coverage candidates.')
    v=[];f=[];_add(quads,v,f);ctx.mesh('PODIUM_V9_PARTIAL_FIRST_FLOOR_GLASS_RAIN_CANOPY',v,f,'66_PODIUM_DETAIL_CANDIDATE','glass_detail',m)
    ctx.lines('PODIUM_V9_PARTIAL_CANOPY_STAINLESS_RADIAL_RIBS',ribs+edges,'66_PODIUM_DETAIL_CANDIDATE',q['rib_radius_candidate_m'],'steel',m)
    return len(quads)


def build_podium(ctx,geometry,completion,assembly):
    from site_v8 import ccw,hull,contains,_surface,xy as site_xy
    from transition_v5 import outer_reference,control_profile_at
    from raised_end_v14 import floor_allowed,base_allowed
    p=assembly['podium_v9'];site=ctx.config['site_v8'];col='64_PODIUM_PHOTO_DERIVED';roofcol='65_PODIUM_WARM_ROOF_DERIVED';detail='66_PODIUM_DETAIL_CANDIDATE'
    _,ref=outer_reference(geometry,ctx.config);tower=ccw(hull([q[:2] for q in control_profile_at(geometry,ctx.config,ref,0)]))
    body=ccw(rounded_poly([plan_xy(p,q) for q in p['ground_outline_px']],p['corner_fillet_candidate_m']));meta=_meta(p,'podium_plan_derived_floor_candidate')
    from corrections_v11 import courtyard_points,tile_panels,build_side_entry
    court=ccw(hull([plan_xy(p,q) for q in courtyard_points(p,p['courtyard_photo_fit_px'])]))
    regions,report=pr_panels(p,tower)
    for side,panels in regions.items():
        offset=0
        for index,depth in enumerate(p['PR_laminate_reported_m']):
            v=[];f=[];ids=[]
            for poly,n,i in panels:
                _add([[tuple(q[k]-n[k]*offset for k in range(3)) for q in poly]],v,f);ids.append(i)
            obj=ctx.mesh(f'PODIUM_V9_PR_{side}_LAYER_{index+1:02d}',v,f,roofcol,'pr_gold_glass',_meta(p,'podium_PR_composite_arc_panel_candidate',reported_layer_thickness_m=depth,source_panelization='Author nominal1800x300mm and8/1.52/8 layers; physical size depends on candidate loft; not a fabrication schedule'),face_attributes={'PR_panel_id':ids})
            mod=obj.modifiers.new('REPORTED_LAMINATE_LAYER','SOLIDIFY');mod.thickness=depth;mod.offset=-1;offset+=depth
    v=[];f=[]
    for panels in regions.values():
        for poly,n,_ in panels:_add([[tuple(q[k]-n[k]*p['PR_backing_offset_candidate_m'] for k in range(3)) for q in poly]],v,f)
    back=ctx.mesh('PODIUM_V9_PR_PANEL_ALIGNED_WATERPROOF_BACKING',v,f,roofcol,'dark_backing',_meta(p,'podium_PR_composite_waterproof_candidate',source_layers='roof AlMgMn standing seam / wall-soffit black PVDF aluminium; actual seam/node map missing'))
    mod=back.modifiers.new('BACKING_CANDIDATE','SOLIDIFY');mod.thickness=.006;mod.offset=-1
    # Slab cells stop below the swept roof rather than punching through the
    # rolled sides. The published plan defines ground; upper slabs are fits.
    roof_vertices=[q for panels in regions.values() for poly,_,_ in panels for q in poly]
    from mathutils.kdtree import KDTree
    kd=KDTree(len(roof_vertices))
    for index,q in enumerate(roof_vertices):kd.insert((q[0],q[1],0),index)
    kd.balance()
    # Upper floor candidates must stay behind the two end facades and the
    # swept shell. Ground-plan lobes alone cannot define their upper extent.
    mother_xy=ccw([sweep_point(p,i/64,1)[:2] for i in range(65)]+
                  [sweep_point(p,i/64,0)[:2] for i in reversed(range(65))])
    cell=.75;xs=[q[0] for q in body];ys=[q[1] for q in body];cells=[]
    for i in range(math.ceil((max(xs)-min(xs))/cell)):
        x=min(xs)+(i+.5)*cell
        for j in range(math.ceil((max(ys)-min(ys))/cell)):
            y=min(ys)+(j+.5)*cell
            corners=[(x+dx*cell/2,y+dy*cell/2) for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1))]
            if all(contains(body,q) and contains(mother_xy,q) and not contains(tower,q) for q in corners):
                # Nearby mother height is a construction-clearance candidate,
                # not a recovered upper structural footprint.
                nearby=[roof_vertices[index][2] for _,index,_ in kd.find_range((x,y,0),1.5)]
                cells.append((x,y,max(nearby,default=p['terrace_candidate_m'])))
    slabnames=[]
    for level,z in enumerate(p['upper_floor_levels_candidate_m']):
        if z==0:obj=_surface(ctx,'PODIUM_V9_GROUND_PUBLISHED_COMMERCIAL_FLOOR',body,0,'core',col,meta,[tower])
        else:
            v=[];f=[]
            for x,y,top in cells:
                if p.get('raised_end_v15') and z>p['terrace_candidate_m'] and any(contains(court,(x+dx*cell/2,y+dy*cell/2)) for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1))):continue
                if top<z+.35 or not all(floor_allowed(p,x+dx*cell/2,y+dy*cell/2,z,margin=.15) for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1))):continue
                _add([[(x-cell/2,y-cell/2,z),(x+cell/2,y-cell/2,z),(x+cell/2,y+cell/2,z),(x-cell/2,y+cell/2,z)]],v,f)
            obj=ctx.mesh(f'PODIUM_V9_UPPER_SLAB_{level+1:02d}_BOUNDARY_CANDIDATE',v,f,col,'core',_meta(p,'podium_upper_slab_clearance_candidate',level_m=z,formula='0.75m provisional welded cells inside published ground AND swept-shell end/side footprint, below nearby candidate roof; no floor projection beyond end facade. Upper concrete boundaries unresolved.'))
            import bmesh
            bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5);bm.to_mesh(obj.data);bm.free()
        mod=obj.modifiers.new('SLAB_SECTION_CANDIDATE','SOLIDIFY');mod.thickness=p['slab_thickness_candidate_m'];mod.offset=-1;slabnames.append(obj.name)
    terrace=_surface(ctx,'PODIUM_V9_OPEN_PLANTED_TERRACE',court,p['terrace_candidate_m'],'landscape_leaf',detail,_meta(p,'podium_photo_courtyard_candidate'))
    paths=[[(*q,p['terrace_candidate_m']+p['rail_height_candidate_m']) for q in court+court[:1]]]
    ctx.lines('PODIUM_V9_COURTYARD_RAIL',paths,detail,.035,'steel',_meta(p,'podium_court_guard_candidate'))
    for i,q in enumerate(courtyard_points(p,p['white_terrace_pads_candidate_px'])):
        x,y=plan_xy(p,q);s=p['white_terrace_pad_candidate_m'];ctx.box(f'PODIUM_V9_UNIDENTIFIED_WHITE_PAD_{i+1:02d}',(x,y,p['terrace_candidate_m']+.13),(s,s,.16),detail,'ground',_meta(p,'podium_photo_visible_unidentified_pad_candidate',count_location_verified=False))
    for i,poly in enumerate(p['garden_pavilion_candidate_outlines_px']):
        pp=ccw(rounded_poly([plan_xy(p,q) for q in courtyard_points(p,poly)],2));hi=p['terrace_candidate_m']+p['garden_pavilion_height_candidate_m']
        _surface(ctx,f'PODIUM_V9_GARDEN_SKYLIGHT_{i+1:02d}',pp,hi,'glass_detail',detail,_meta(p,'podium_photo_garden_skylight_candidate'))
    # Source curtain systems occupy separate local bands: PS opaque strip
    # instead of a perimeter glass cage, and sparse point/cable PG glazing.
    gv=[];gf=[];sv=[];sf=[];cables=[];ev=[];ef=[];ugv=[];ugf=[];dv=[];df=[];rv=[];rf=[];entry_frames=[]
    for a,b in zip(body,body[1:]+body[:1]):
        mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
        if contains(tower,mid) or not base_allowed(p,*mid):continue
        front=local_ground_opaque_band(p,mid)
        tops_a=[roof_vertices[index][2] for _,index,_ in kd.find_range((a[0],a[1],0),3)]
        tops_b=[roof_vertices[index][2] for _,index,_ in kd.find_range((b[0],b[1],0),3)]
        ha=max(tops_a,default=p['terrace_candidate_m'])-.15;hb=max(tops_b,default=p['terrace_candidate_m'])-.15
        # Only documented ground interface here. Tall arched PG uses the
        # actual roof section below, not an independently guessed rectangle.
        hi=min(p['west_PR_start_reported_m'],max(.2,min(ha,hb)))
        entry=entrance_zone(p,a,b)
        if entry:
            top=min(entry['upper_glass_top_candidate_m'],ha,hb)
            white,upper,doors,reveals=entrance_panels(p,a,b,top)
            _add(white,ev,ef);_add(upper,ugv,ugf);_add(doors,dv,df);_add(reveals,rv,rf)
            for z in [entry['white_top_candidate_m']+p['PG_horizontal_pitch_candidate_m']*i for i in range(1,int(max(0,top-entry['white_top_candidate_m'])/p['PG_horizontal_pitch_candidate_m']))]:entry_frames.append([(a[0],a[1],z),(b[0],b[1],z)])
            continue
        _add([[(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],hi),(a[0],a[1],hi)]],gv,gf)
        if front:
            lo,up=p['PS_opaque_band_candidate_m'];up=min(up,ha,hb)
            if up>lo:_add([[(a[0],a[1],lo),(b[0],b[1],lo),(b[0],b[1],up),(a[0],a[1],up)]],sv,sf)
        if math.dist(a,b)>.5:
            for z in [p['PG_horizontal_pitch_candidate_m']*i for i in range(1,int(hi/p['PG_horizontal_pitch_candidate_m']))]:cables.append([(a[0],a[1],z),(b[0],b[1],z)])
    ctx.mesh('PODIUM_V9_LOCAL_PG_POINT_SUPPORTED_GLASS',gv,gf,detail,'glass_detail',_meta(p,'podium_PG_local_glazing_candidate',source_systems='PG1 cable/PG2 plate truss/PG3 mixed point support; exact final zone limits and joints unresolved'))
    if p.get('opaque_tiles_v11'):
        opaque=tile_panels(p,[[sv[i] for i in face] for face in sf]);sv=[];sf=[];_add(opaque,sv,sf)
    ctx.mesh('PODIUM_V9_LIMITED_PS_OPAQUE_FRONT_BAND',sv,sf,detail,'podium_stone',_meta(p,'podium_PS_local_stone_band_candidate',tile_module_evidence=str(p.get('opaque_tiles_v11',{}))+'; candidate stone module, no PS shop schedule recovered'))
    ctx.lines('PODIUM_V9_PG_FINE_HORIZONTAL_CABLE_GRID',cables,detail,p['PG_cable_radius_candidate_m'],'steel',_meta(p,'podium_PG_cable_candidate'))
    if p.get('entrance_v10') and p['entrance_v10'].get('target_arch_end') is None and not p.get('entrance_v11'):
        em=_meta(p,'podium_v10_white_entry_candidate',source_ids=p['source_ids']+['USER_OBSERVATION_V10'],evidence_level='待确认',uncertainty=p['entrance_v10']['uncertainty'],formula='Local broad-face boundary from published ground trace; existing PS and PG omitted there; white polygon physically cut for recessed entrance, glass retained above.')
        white=ctx.mesh('PODIUM_V10_BROAD_FACE_WHITE_ENTRY_CUT',ev,ef,detail,'podium_entry_white',em)
        mod=white.modifiers.new('WHITE_CLADDING_CANDIDATE','SOLIDIFY');mod.thickness=.12;mod.offset=-1
        ctx.mesh('PODIUM_V10_GLASS_ABOVE_WHITE_ENTRY',ugv,ugf,detail,'glass_detail',{**em,'geometry_role':'podium_v10_upper_entry_glass_candidate'})
        ctx.mesh('PODIUM_V10_RECESSED_ENTRY_GLAZING',dv,df,detail,'glass_detail',{**em,'geometry_role':'podium_v10_recessed_entry_glass_candidate'})
        ctx.mesh('PODIUM_V10_WHITE_ENTRY_RETURNS',rv,rf,detail,'podium_entry_white',{**em,'geometry_role':'podium_v10_entry_return_candidate'})
        ctx.lines('PODIUM_V10_SPARSE_UPPER_ENTRY_CABLES',entry_frames,detail,p['PG_cable_radius_candidate_m'],'steel',em)
    arch_endcaps(ctx,p,tower)
    if p.get('entrance_v11'):build_side_entry(ctx,p)
    steel=[]
    for i in range(0,report['longitudinal_intervals']+1,4):
        t=min(1,i/report['longitudinal_intervals']);path=[]
        for j in range(65):
            if (p.get('side_v12') or p.get('side_v13')) and p['entrance_v11']['t_span'][0]<=t<=p['entrance_v11']['t_span'][1] and j/64>p['entrance_v11']['roof_cut_u']:break
            q=sweep_point(p,t,j/64)
            if not contains(tower,q[:2]) and not (q[2]>=p['terrace_candidate_m'] and contains(court,q[:2])):path.append((q[0],q[1],q[2]-.35))
            elif len(path)>1:steel.append(path);path=[]
        if len(path)>1:steel.append(path)
    ctx.lines('PODIUM_V9_MULTI_ARC_ROOF_STEEL_RIBS',steel,col,p['steel_roof_rib_radius_candidate_m'],'steel',_meta(p,'podium_under_roof_steel_candidate',source_locator='Lingyun Figs22/23 steel framing; candidate topology/sections'))
    grid=p['steel_column_grid_candidate_m'];columns=[]
    for i in range(math.ceil((max(xs)-min(xs))/grid)):
        x=min(xs)+(i+.5)*grid
        for j in range(math.ceil((max(ys)-min(ys))/grid)):
            y=min(ys)+(j+.5)*grid
            if contains(body,(x,y)) and not contains(tower,(x,y)) and not contains(court,(x,y)) and base_allowed(p,x,y):
                tops=[roof_vertices[index][2] for _,index,_ in kd.find_range((x,y,0),2)]
                columns.append([(x,y,0),(x,y,min(max(tops,default=22)-.6,32))])
    ctx.lines('PODIUM_V9_STEEL_FRAME_COLUMNS_CANDIDATE',columns,col,p['steel_column_radius_candidate_m'],'steel',_meta(p,'podium_primary_steel_columns_candidate'))
    ctx.empty('PODIUM_V9_WEST_CLOSED_SOFFIT_UNRESOLVED_INTERFACE',(0,-40,4.2),detail,_meta(p,'podium_unresolved_closed_soffit_interface',evidence_level='待确认',formula='Contractor describes west closed curve; complete lower return and axis9 coordinates unavailable, no fake completed shop closure.'))
    rain=rain_canopy(ctx,geometry,p)
    pavilion=ccw(rounded_poly([site_xy(site,q) for q in site['pavilion_outline_px']],2));hh=p['landscape_pavilion_height_candidate_m']
    _surface(ctx,'PODIUM_V9_SEPARATE_CURVED_PAVILION_ROOF',pavilion,hh,'guide',detail,_meta(p,'podium_landscape_pavilion_candidate'))
    pv=[];pf=[]
    for a,b in zip(pavilion,pavilion[1:]+pavilion[:1]):_add([[(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],hh),(a[0],a[1],hh)]],pv,pf)
    ctx.mesh('PODIUM_V9_SEPARATE_CURVED_PAVILION_OPAQUE_ENVELOPE',pv,pf,detail,'guide',_meta(p,'podium_landscape_pavilion_candidate',glazing_extent_verified=False))
    return {'version':p['version'],'used_parameters':p,'PR_panel_report':report,'slabs':slabnames,'candidate_levels_m':p['upper_floor_levels_candidate_m'],'asbuilt_verified':False,
            'checks':[{'name':'v9_podium_old_mother_retired','passed':not any(o.name.startswith(('PODIUM_V6_','PODIUM_V7_')) for o in ctx.objects),'actual':True},
                      {'name':'v9_podium_seven_candidate_floors','passed':len(slabnames)==7,'actual':len(slabnames)},
                      {'name':'v9_podium_arc_PR_and_partial_canopy','passed':report['candidate_panels']>1000 and rain>10,'actual':{'PR':report['candidate_panels'],'canopy':rain}}]}
