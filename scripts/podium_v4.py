"""Photo-informed asymmetric retail podium; no survey precision is claimed."""
import math
from collections import Counter

SOURCE='PODIUM_GENS_V4'
COL='64_PODIUM_PHOTO_DERIVED'
ROOF='65_PODIUM_WARM_ROOF_DERIVED'
DETAIL='66_PODIUM_DETAIL_CANDIDATE'


def _meta(role,p,**extra):
    source_ids=[SOURCE,'PODIUM_LINGYUN_BIM_V7']
    if role.startswith('podium_arch_') or role=='podium_ground_photo_arched_glazing':source_ids=['PODIUM_GENS_GROUND_V6']
    if role=='podium_photo_derived_roof':source_ids=[SOURCE,'PODIUM_GENS_GROUND_V6']
    result={'source_ids':source_ids, 'source_locator':'Gensler aerial image95597 and actual podium ground image95598; historical Retail Podium hero4907/4908 kept separate',
            'source_version':'Actual aerial/ground photos undated; retail renderings historical, not construction drawings',
            'evidence_level':'推导值', 'numeric_evidence_level':'待确认', 'asbuilt_verified':False,
            'geometry_role':role, 'formula':'Photo-informed local candidate controls, not calibrated image-to-world measurements',
            'uncertainty':p['uncertainty'], 'orientation_georeferenced':False, 'floor_schedule_verified':False,
            'material_specification_verified':False,
            'source_conflict':'D10 7/38m; contractor article7/37m vs tender5/38.245m. Public original and final revision missing; candidate37m chosen without as-built assertion'}
    result.update(extra)
    if str(p.get('parameter_version','')).startswith('v8') and 'pavilion' in role:
        result['source_ids']=list(dict.fromkeys(result['source_ids']+['GENSLER_ARCHJOURNAL_V8']))
        result['source_locator']+='; publishedp29 scale-bar pavilion trace; registration/height candidate'
    return result


def outline(p, inset=0):
    """Rounded rectangle of single off-axis wing, not a tower-centred annulus."""
    w=p['width_m']/2-inset;d=p['depth_m']/2-inset;r=max(1,p['corner_radius_m']-inset)
    r=min(r,w,d);points=[]
    for x,y,ang in [(w-r,d-r,0),(-w+r,d-r,90),(-w+r,-d+r,180),(w-r,-d+r,270)]:
        for k in range(p['corner_samples']+1):
            a=math.radians(ang+90*k/p['corner_samples']);points.append((x+r*math.cos(a),y+r*math.sin(a)))
    return resample(points,p['facade_module_candidate_m'])


def resample(points,pitch):
    result=[]
    for a,b in zip(points,points[1:]+points[:1]):
        count=max(1,math.ceil(math.dist(a,b)/pitch))
        result.extend((a[0]+(b[0]-a[0])*i/count,a[1]+(b[1]-a[1])*i/count) for i in range(count))
    return result


def xy(p,u,v):
    x,y=u*p['width_m'],v*p['depth_m'];a=math.radians(p['local_azimuth_deg'])
    return (p['center_xy_m'][0]+x*math.cos(a)-y*math.sin(a),p['center_xy_m'][1]+x*math.sin(a)+y*math.cos(a))


def _outline_global(p,points,z):
    return [(*xy(p,x/p['width_m'],y/p['depth_m']),z) for x,y in points]


def _slab(ctx,p,name,points,z,thickness,material,role):
    n=len(points);top=_outline_global(p,points,z);verts=top+[(x,y,z-thickness) for x,y,_ in top]
    faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[((i+1)%n,i,i+n,(i+1)%n+n) for i in range(n)]
    return ctx.mesh(name,verts,faces,COL,material,_meta(role,p,level_m=z,thickness_display_m=thickness))


def _grid_patch(ctx,p,name,umin,umax,vmin,vmax,height,material,role):
    nu=p['roof_samples_width'];nv=p['roof_samples_depth'];verts=[];faces=[]
    for j in range(nv+1):
        v=vmin+(vmax-vmin)*j/nv
        for i in range(nu+1):
            u=umin+(umax-umin)*i/nu;verts.append((*xy(p,u,v),height(u,v)))
    for j in range(nv):
        for i in range(nu):
            k=j*(nu+1)+i;faces.append((k,k+1,k+nu+2,k+nu+1))
    return ctx.mesh(name,verts,faces,ROOF,material,_meta(role,p,roof_surface_display_only=True))


def roof_height(p,u,v):
    """C1 join at shared row: main arch and folded wings cannot drift apart."""
    back=p['roof_back_v_min'];crest=p['roof_high_m']-p['roof_arch_drop_m']*(2*u)**2
    if v<=back:
        start=p['left_fold_front_v_candidate'] if u<=-p['roof_side_inner_u_left'] else -.5
        bottom=p['terrace_top_m']+p['left_end_clearance_candidate_m'] if start!=-.5 else p['terrace_top_m']
        t=max(0,min(1,(v-start)/(back-start)))
        base=bottom+(crest-bottom)*math.sin(t*math.pi/2)
    else:
        t=max(0,min(1,(v-back)/(.5-back)))
        base=crest-p['roof_back_drop_m']*(3*t*t-2*t*t*t)
    # Actual side cladding rolls locally down to ground beside the glass arch;
    # it is not a large rectangular gold wall underneath a flat U-plan slab.
    edge=p['roof_side_inner_u_right'];weight=max(0,min(1,(u-edge)/(.5-edge)))
    weight=weight*weight*(3-2*weight)
    rim=mouth_top(p,v+.5)+p['mouth_dark_return_width_candidate_m']
    return base*(1-weight)+rim*weight


def mouth_top(p,t):
    """Asymmetric curved mouth; all controls remain photo-informed candidates."""
    q=p['arched_mouth'];t=max(0,min(1,t))
    return q['height_candidate_m']*math.sin(math.pi*q['angular_fraction_candidate']*t)**q['power_candidate']


def roof_xy(p,u,v):
    """Fold edge follows the rounded body corner instead of hanging off it."""
    y=v*p['depth_m'];r=p['corner_radius_m'];d=p['depth_m']/2;w=p['width_m']/2
    if abs(y)>d-r:
        halfwidth=w-r+math.sqrt(max(0,r*r-(abs(y)-d+r)**2))
        u *= halfwidth/w
    return xy(p,u,v)


def cropped_floor_outline(p,points,z):
    """Local candidate floor ends stay inside the descending gold skin.

    The old rectangular floor must not punch through the rolling facade. This
    crop is an assembly repair, not an asserted surveyed slab boundary.
    """
    result=[];w=p['width_m']/2;d=p['depth_m']/2;r=p['corner_radius_m']
    for x,y in points:
        v=y/p['depth_m'];half=w
        if abs(y)>d-r:half=w-r+math.sqrt(max(0,r*r-(abs(y)-d+r)**2))
        if x>0 and roof_height(p,.5,v)<z+p['roof_shell_thickness_candidate_m']+p['floor_fold_clearance_candidate_m']:
            low=p['roof_side_inner_u_right'];high=.5;target=z+p['roof_shell_thickness_candidate_m']+p['floor_fold_clearance_candidate_m']
            if roof_height(p,low,v)<target:
                limit=low-p['floor_inner_setback_candidate_u']
            else:
                for _ in range(28):
                    mid=(low+high)/2
                    if roof_height(p,mid,v)>=target:low=mid
                    else:high=mid
                limit=low
            x=min(x,2*half*limit)
        point=(x,y)
        if not result or math.dist(point,result[-1])>1e-8:result.append(point)
    if len(result)>1 and math.dist(result[0],result[-1])<1e-8:result.pop()
    return result


def roof_mesh(p):
    """One manifold U shell: shared joins, thickness, central terrace opening."""
    us=sorted(set([-.5,.5,-p['roof_side_inner_u_left'],p['roof_side_inner_u_right']]+
                  [-.5+i/p['roof_samples_width'] for i in range(p['roof_samples_width']+1)]))
    back=p['roof_back_v_min'];count=p['roof_samples_depth']
    vs=sorted(set([-.5+(back+.5)*i/count for i in range(count)]+[back+(.5-back)*i/count for i in range(count+1)]+[p['left_fold_front_v_candidate']]))
    verts=[];top=[];lookup={}
    def vertex(i,j):
        if (i,j) not in lookup:
            lookup[(i,j)]=len(verts);u,v=us[i],vs[j]
            verts.append((*roof_xy(p,u,v),roof_height(p,u,v)))
        return lookup[(i,j)]
    for j in range(len(vs)-1):
        for i in range(len(us)-1):
            mid=(us[i]+us[i+1])/2
            if vs[j]<back-1e-12 and -p['roof_side_inner_u_left']<mid<p['roof_side_inner_u_right']:continue
            if mid<0 and vs[j]<p['left_fold_front_v_candidate']:continue
            top.append((vertex(i,j),vertex(i+1,j),vertex(i+1,j+1),vertex(i,j+1)))
    edges=Counter(tuple(sorted((a,b))) for face in top for a,b in zip(face,face[1:]+face[:1]))
    boundary=[(a,b) for face in top for a,b in zip(face,face[1:]+face[:1]) if edges[tuple(sorted((a,b)))]==1]
    n=len(verts);verts += [(x,y,z-p['roof_shell_thickness_candidate_m']) for x,y,z in verts[:n]]
    faces=top+[tuple(i+n for i in reversed(face)) for face in top]+[(b,a,a+n,b+n) for a,b in boundary]
    return verts,faces,boundary


def _glazed_pavilion(ctx,p,name,points,lo,hi):
    verts=[];faces=[];frames=[];lower=_outline_global(p,points,lo);upper=_outline_global(p,points,hi)
    for i in range(len(points)):
        j=(i+1)%len(points);k=len(verts);verts.extend((lower[i],lower[j],upper[j],upper[i]));faces.append((k,k+1,k+2,k+3))
        frames.extend(([lower[i],upper[i]],[upper[i],upper[j]]))
    ctx.mesh(name+'_GLAZING',verts,faces,DETAIL,'glass_detail',_meta('podium_photo_derived_pavilion',p))
    if p.get('pavilion_frames_enabled',False):
        ctx.lines(name+'_FRAMES',frames,DETAIL,p['frame_radius_display_m'],'steel',_meta('podium_pavilion_grid_candidate',p,pattern_verified=False))
    _slab(ctx,p,name+'_ROOF',points,hi,.18,'glass_detail','podium_pavilion_roof_candidate')


def lobe_outline(p,sign):
    q=p['garden_pavilions'];cu,cv=sign*q['centre_u_abs'],q['centre_v'];ru,rv=q['half_size_uv'];points=[]
    for i in range(q['samples']):
        a=2*math.pi*i/q['samples'];taper=1-q['tip_taper_candidate']*(1-math.sin(a))/2
        points.append(((cu+ru*math.cos(a)*taper)*p['width_m'],(cv+rv*math.sin(a))*p['depth_m']))
    return resample(points,p['facade_module_candidate_m'])


def satellite_outline(p):
    q=p['satellite_pavilion'];points=[]
    if q.get('plan_outline_local_m'):
        return resample(q['plan_outline_local_m'],p['facade_module_candidate_m'])
    for radius,reverse in [(q['outer_radius_candidate_m'],False),(q['inner_radius_candidate_m'],True)]:
        indices=list(range(q['arc_samples']+1))
        if reverse:indices.reverse()
        for i in indices:
            a=math.radians(q['start_angle_candidate_deg']+q['span_candidate_deg']*i/q['arc_samples'])
            points.append((radius*math.cos(a),radius*math.sin(a)))
    return resample(points,p['facade_module_candidate_m'])


def _terrace_details(ctx,p):
    g=p['garden'];z=p['terrace_top_m']+.10
    points=[((g['centre_uv'][0]+g['radii_uv'][0]*math.cos(2*math.pi*i/g['samples']))*p['width_m'],
             (g['centre_uv'][1]+g['radii_uv'][1]*math.sin(2*math.pi*i/g['samples']))*p['depth_m']) for i in range(g['samples'])]
    _slab(ctx,p,'PODIUM_V5_CURVED_TERRACE_GARDEN',points,z,.1,'confirmed','podium_photo_derived_garden')
    path=_outline_global(p,points,z+.04)
    ctx.lines('PODIUM_V5_GARDEN_PERIMETER_PATH',[path+path[:1]],DETAIL,g['path_half_width_candidate_m'],'core',_meta('podium_garden_path_candidate',p))
    for i,(u,v) in enumerate(g['shade_pads_uv']):
        w=g['shade_pad_width_candidate_m'];x=u*p['width_m'];y=v*p['depth_m']
        pad=[(x-w/2,y-w/2),(x+w/2,y-w/2),(x+w/2,y+w/2),(x-w/2,y+w/2)]
        _slab(ctx,p,f'PODIUM_V5_WHITE_TERRACE_ELEMENT_{i+1:02d}',pad,z+.35,.1,'ground','podium_unidentified_terrace_element')
    for sign in (-1,1):
        _glazed_pavilion(ctx,p,f'PODIUM_V5_CURVED_GARDEN_PAVILION_{sign:+d}',lobe_outline(p,sign),p['terrace_top_m'],p['terrace_top_m']+p['garden_pavilions']['height_candidate_m'])
    rail=_outline_global(p,outline(p,p['terrace_rail_inset_candidate_m']),p['terrace_top_m']+p['railing_height_candidate_m'])
    ctx.lines('PODIUM_V5_TERRACE_RAIL_AND_POSTS',[rail+rail[:1]]+[[(*a[:2],p['terrace_top_m']),a] for a in rail[::3]],DETAIL,p['railing_radius_display_m'],'steel',_meta('podium_terrace_rail_candidate',p))


def _entrance(ctx,p):
    """Historical rendering provides entrance cue; current layout unconfirmed."""
    width=p['entrance_width_candidate_m'];u=p['entrance_offset_u'];v=-.5;z=p['entrance_canopy_height_candidate_m'];d=p['entrance_canopy_depth_candidate_m']
    x=u*p['width_m'];y=v*p['depth_m'];canopy=[(x-width*.65,y-d),(x+width*.65,y-d),(x+width*.65,y+.25),(x-width*.65,y+.25)]
    _slab(ctx,p,'PODIUM_V5_RETAIL_ENTRANCE_CANOPY',canopy,z,p['entrance_canopy_thickness_candidate_m'],'guide','podium_historical_entrance_candidate')
    paths=[];verts=[];faces=[]
    count=p['entrance_door_leaf_count_candidate']
    for i in range(count):
        a=x-width/2+width*i/count;b=x-width/2+width*(i+1)/count;k=len(verts)
        verts.extend((*xy(p,xx/p['width_m'],v-.002),zz) for xx,zz in [(a,0),(b,0),(b,z-.35),(a,z-.35)])
        faces.append((k,k+1,k+2,k+3));paths.append([verts[k],verts[k+3]])
    ctx.mesh('PODIUM_V5_RETAIL_ENTRY_DOORS',verts,faces,DETAIL,'glass_detail',_meta('podium_historical_entrance_candidate',p,source_support='Historical rendering only; exact current doorway unknown'))
    for xx in [x-width*.65,x+width*.65]:
        a=(*xy(p,xx/p['width_m'],v-d/p['depth_m']),0);paths.append([a,(*a[:2],z)])
    ctx.lines('PODIUM_V5_ENTRY_PORTAL_FRAMES',paths,DETAIL,.09,'steel',_meta('podium_historical_entrance_candidate',p))


def _mouth_point(p,t,z):
    x,y=roof_xy(p,.5,t-.5);h=mouth_top(p,t)
    bow=p['arched_mouth']['glass_bow_candidate_m']*math.sin(math.pi*t)*math.sin(math.pi*z/h) if h else 0
    offset=bow-.04;a=math.radians(p['local_azimuth_deg'])
    return x+offset*math.cos(a),y+offset*math.sin(a),z


def _mouth_band(p,a,b,lo,hi):
    ha,hb=mouth_top(p,a),mouth_top(p,b)
    if max(ha,hb)<=lo:return []
    if ha<lo:
        a=a+(b-a)*(lo-ha)/(hb-ha);ha=lo
    if hb<lo:
        b=b+(a-b)*(lo-hb)/(ha-hb);hb=lo
    result=[(a,lo),(b,lo),(b,min(hi,hb)),(a,min(hi,ha))]
    points=[]
    for t,z in result:
        point=_mouth_point(p,t,z)
        if not points or math.dist(point,points[-1])>1e-9:points.append(point)
    if len(points)>1 and math.dist(points[0],points[-1])<1e-9:points.pop()
    return points if len(points)>=3 else []


def _arched_mouth(ctx,p):
    q=p['arched_mouth'];count=q['curve_samples'];rows=q['horizontal_row_count_candidate'];height=q['height_candidate_m']
    verts=[];faces=[];stripes=[];divisions=[]
    for row in range(rows):
        lo=height*row/rows;hi=height*(row+1)/rows
        for i in range(count):
            points=_mouth_band(p,i/count,(i+1)/count,lo,hi)
            if points:
                k=len(verts);verts.extend(points);faces.append(tuple(range(k,k+len(points))))
        if row:
            path=[_mouth_point(p,i/count,lo) for i in range(count+1) if mouth_top(p,i/count)>=lo]
            if len(path)>1:stripes.append(path)
    for i in range(1,q['vertical_divisions_candidate']):
        t=i/q['vertical_divisions_candidate'];divisions.append([_mouth_point(p,t,0),_mouth_point(p,t,mouth_top(p,t))])
    ctx.mesh('PODIUM_V6_TALL_ARCHED_GLASS_MOUTH',verts,faces,DETAIL,'glass_detail',
             _meta('podium_ground_photo_arched_glazing',p,pattern_verified=False,source_support='Actual Gensler95598: horizontal-dominant glazing, limited vertical divisions'))
    ctx.lines('PODIUM_V6_MOUTH_FINE_HORIZONTAL_JOINTS',stripes,DETAIL,q['frame_radius_display_m'],'steel',
              _meta('podium_arch_horizontal_joint_candidate',p,count_verified=False))
    ctx.lines('PODIUM_V6_MOUTH_LIMITED_VERTICAL_DIVISIONS',divisions,DETAIL,q['frame_radius_display_m'],'steel',
              _meta('podium_arch_vertical_joint_candidate',p,count_verified=False))
    rim=[];rf=[]
    for i in range(count+1):
        t=i/count;x,y=roof_xy(p,.5,t-.5);z=mouth_top(p,t);k=len(rim)
        rim.extend(((x,y,z),(x,y,z+p['mouth_dark_return_width_candidate_m'])))
        if i:rf.append((k-2,k,k+1,k-1))
    ctx.mesh('PODIUM_V7_PG1_CURVED_ALUMINUM_RETURN',rim,rf,DETAIL,'dark_backing',
             _meta('podium_arch_dark_return_candidate',p,dimension_verified=False))
    # PG1 perimeter: individually modelled grilles, distinct from glass/cable net.
    grilles=[]
    for j in range(count*3+1):
        t=j/(count*3);x,y=roof_xy(p,.5,t-.5);z=mouth_top(p,t)
        grilles.append([(x,y,z+.08),(x,y,z+p['mouth_dark_return_width_candidate_m']-.08)])
    ctx.lines('PODIUM_V7_PG1_PERIMETER_LOUVER_GRILLE',grilles,DETAIL,.018,'steel',_meta('podium_PG1_grille_candidate',p,source_ids=['PODIUM_LINGYUN_BIM_V7'],section_spacing_verified=False))
    # Glass joints/cable net are thin; five larger vertical lines remain an
    # image-fit support convention, rather than full-height heavy glazing bars.
    cables=[]
    for j in range(1,round(p['depth_m']/1.8)):
        t=j/round(p['depth_m']/1.8);a=_mouth_point(p,t,0);cables.append([a,(*a[:2],mouth_top(p,t))])
    ctx.lines('PODIUM_V7_PG1_SINGLE_CABLE_NET_VERTICAL_CANDIDATE',cables,DETAIL,.006,'steel',_meta('podium_PG1_point_support_cable_candidate',p,source_ids=['PODIUM_LINGYUN_BIM_V7'],candidate_spacing_m=1.8,spacing_verified=False))
    # Pale cylindrical element visible at one side of the real mouth. Axis,
    # radius, finish and relation to structural system are still candidates.
    x,y=roof_xy(p,.5,.5);radius=q['column_radius_candidate_m'];n=q['column_samples'];h=mouth_top(p,1)
    column=[]
    for z in [0,h]:
        column.extend((x+radius*math.cos(2*math.pi*i/n),y+radius*math.sin(2*math.pi*i/n),z) for i in range(n))
    cf=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    ctx.mesh('PODIUM_V6_PALE_COLUMN_PHOTO_CANDIDATE',column,cf,DETAIL,'core',
             _meta('podium_arch_pale_column_candidate',p,structural_function_verified=False))


def build_podium(ctx,geometry,completion,assembly):
    p=assembly['podium_v4'];body=outline(p);n=len(body);levels=p['display_slab_levels_m'];slabs=[]
    for i,z in enumerate(levels):
        cropped=cropped_floor_outline(p,body,z)
        if z>p['terrace_top_m']:
            from crown_v5 import _cut_polygons,_extruded_polygons
            hole=[(-p['roof_side_inner_u_left']*p['width_m'],-p['depth_m']/2),(p['roof_side_inner_u_right']*p['width_m'],-p['depth_m']/2),(p['roof_side_inner_u_right']*p['width_m'],p['roof_back_v_min']*p['depth_m']),(-p['roof_side_inner_u_left']*p['width_m'],p['roof_back_v_min']*p['depth_m'])]
            pieces=_cut_polygons([cropped],[hole]);verts,faces=_extruded_polygons(pieces,z,p['slab_thickness_display_m'])
            verts=[(*xy(p,x/p['width_m'],y/p['depth_m']),zz) for x,y,zz in verts]
            obj=ctx.mesh(f'PODIUM_V7_UPPER_LEVEL_{i:02d}_WITH_TERRACE_VOID',verts,faces,COL,'core',_meta('podium_candidate_slab',p,level_m=z))
            slabs.append(obj.name)
        else:slabs.append(_slab(ctx,p,f'PODIUM_V7_LEVEL_{i:02d}_CANDIDATE',cropped,z,p['slab_thickness_display_m'],'core','podium_candidate_slab').name)
    # A front low shop window strip and one tall side mouth replace the v5
    # full-height perimeter glass cage. Occluded walls remain unconfirmed.
    glass=[];gf=[];opaque=[];of=[];band=p['front_opaque_band_candidate_z_m'];front_limit=-p['depth_m']/2+p['corner_radius_m']
    for i,a in enumerate(body):
        b=body[(i+1)%n];mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
        if mid[0]>=p['width_m']/2-p['corner_radius_m']:continue
        front=mid[1]<=front_limit
        spans=[(0,band[0],True),(band[0],levels[-1],False)] if front else [(0,levels[-1],False)]
        for lo,hi,transparent in spans:
            lower=cropped_floor_outline(p,[a,b],lo);upper=cropped_floor_outline(p,[a,b],hi)
            if len(lower)<2 or len(upper)<2:continue
            pts=_outline_global(p,lower,lo)+list(reversed(_outline_global(p,upper,hi)))
            target,faces=(glass,gf) if transparent else (opaque,of);k=len(target);target.extend(pts);faces.append((k,k+1,k+2,k+3))
    ctx.mesh('PODIUM_V6_LIMITED_LOW_FRONT_GLAZING',glass,gf,COL,'glass_detail',_meta('podium_candidate_glazing',p,placement_verified=False))
    ctx.mesh('PODIUM_V6_FRONT_OPAQUE_AND_OCCLUDED_WALL_CANDIDATES',opaque,of,COL,'podium_stone',
             _meta('podium_unconfirmed_opaque_envelope',p,evidence_level='待确认',source_support='Aerial front band visible; occluded sides not reconstructed as verified glass'))
    frames=[];front_y=-p['depth_m']/2;half=p['width_m']/2-p['corner_radius_m']
    for i in range(p['front_vertical_divisions_candidate']+1):
        x=-half+2*half*i/p['front_vertical_divisions_candidate'];a=(*xy(p,x/p['width_m'],-.5),0);frames.append([a,(*a[:2],band[0])])
    ctx.lines('PODIUM_V6_SPARSE_FRONT_SHOP_DIVISIONS',frames,DETAIL,p['frame_radius_display_m'],'steel',_meta('podium_front_grid_candidate',p,pattern_verified=False))
    roofverts,rooffaces,boundary=roof_mesh(p)
    archived=ctx.mesh('PODIUM_V7_PR_CONTINUOUS_WATERPROOF_BACKING',[(x,y,z-.065) for x,y,z in roofverts],rooffaces,ROOF,'dark_backing',
             _meta('podium_archived_coarse_mother_shell',p,joined_roof_returns=True,local_sweep_only=True,rectangular_hanging_gold_wall=False,shell_thickness_verified=False,superseded_by='PODIUM_V7_PANEL_ALIGNED_WATERPROOF_BACKING'))
    archived.hide_render=True;archived.hide_viewport=True
    import podium_panels_v7
    pr_report=podium_panels_v7.build(ctx,p,_meta('podium_PR_gold_textured_glass_candidate',p))
    # Short left folded tip returns directly to the terrace. It no longer ends
    # five metres above an unsupported gap, and gets only a local thin end face.
    v=p['left_fold_front_v_candidate'];end=[]
    for u in [-.5,-p['roof_side_inner_u_left']]:
        x,y=roof_xy(p,u,v);end.extend(((x,y,p['terrace_top_m']),(x,y,roof_height(p,u,v))))
    ctx.mesh('PODIUM_V6_LOCAL_LEFT_FOLD_END_RETURN',end,[(0,2,3,1)],ROOF,'podium_cladding',
             _meta('podium_candidate_local_end_return',p,evidence_level='待确认',connection_verified=False))
    _arched_mouth(ctx,p)
    _terrace_details(ctx,p)
    if p.get('entrance_enabled',False):_entrance(ctx,p)
    else:ctx.empty('PODIUM_V6_HISTORICAL_ENTRANCE_INTERFACE',(*xy(p,p['entrance_offset_u'],-.5),0),DETAIL,
                   _meta('podium_historical_entrance_interface',p,evidence_level='待确认',display_disabled_reason='Historical rendering not confirmed by current actual photos'))
    # Photo roof texture field gets a thin local surface; v5 massive tubular
    # bars were unsupported equipment. No equipment specification is claimed.
    if p.get('roof_striped_surface_enabled',False):
        field=[];ff=[];rows=p['roof_field_display_rows'];width=p['lamella_u_range'];depth=p['lamella_v_range']
        for i in range(rows):
            u=width[0]+(width[1]-width[0])*i/rows;du=(width[1]-width[0])*.45/rows;k=len(field)
            for uu,v in [(u,depth[0]),(u+du,depth[0]),(u+du,depth[1]),(u,depth[1])]:field.append((*roof_xy(p,uu,v),roof_height(p,uu,v)+.025))
            ff.append((k,k+1,k+2,k+3))
        ctx.mesh('PODIUM_V6_LOCAL_THIN_ROOF_TEXTURE_FIELD',field,ff,DETAIL,'dark_backing',
                 _meta('podium_photo_visible_roof_striped_field',p,equipment_type_verified=False,count_verified=False,display_surface_only=True))
    q=dict(p);q.update(p['satellite_pavilion']);sat=satellite_outline(p)
    _slab(ctx,q,'PODIUM_V6_LANDSCAPE_PAVILION_BASE',sat,0,.20,'core','podium_separate_pavilion_candidate')
    _slab(ctx,q,'PODIUM_V6_LANDSCAPE_PAVILION_ROOF',sat,q['height_m'],.18,'guide','podium_separate_pavilion_candidate')
    low=_outline_global(q,sat,0);high=_outline_global(q,sat,q['height_m']);sv=[];sf=[]
    for i in range(len(sat)):
        j=(i+1)%len(sat);k=len(sv);sv.extend((low[i],low[j],high[j],high[i]));sf.append((k,k+1,k+2,k+3))
    ctx.mesh('PODIUM_V6_LANDSCAPE_PAVILION_CURVED_ENVELOPE_CANDIDATE',sv,sf,DETAIL,'guide',
             _meta('podium_separate_pavilion_candidate',p,evidence_level='待确认',glazing_extent_verified=False))
    # Geometric curve tessellation is never reused as an alleged frame pitch.
    ctx.empty('PODIUM_V6_TOWER_JUNCTION_UNCONFIRMED',(*p['junction_candidate_xy_m'],p['junction_candidate_z_m']),DETAIL,_meta('podium_tower_connection_interface',p,evidence_level='待确认'))
    edgecounts=Counter(tuple(sorted((a,b))) for f in rooffaces for a,b in zip(f,f[1:]+f[:1]))
    return {'source_id':SOURCE,'source_ids':[SOURCE,'PODIUM_GENS_GROUND_V6'],'version':'v7-reported-PR-physical-panels-candidate','PR_panel_report':pr_report,'slabs':slabs,'candidate_levels_m':levels,
            'candidate_roof_extents_m':[0,max(v[2] for v in roofverts)],'footprint_verified':False,'asbuilt_verified':False,'orientation_verified':False,
            'used_parameters':p,'historical_conflict':p['historical_conflict'],'uncertainty':p['uncertainty'],
            'checks':[{'name':'podium_asymmetric_off_axis','passed':math.hypot(*p['center_xy_m'])>30,'actual':p['center_xy_m']},
                      {'name':'podium_joined_roof_closed_shell','passed':all(v==2 for v in edgecounts.values()),'actual':sorted(set(edgecounts.values()))},
                      {'name':'podium_no_rectangular_gold_wrap','passed':not p.get('rectangular_gold_wrap_enabled',False),'actual':False},
                      {'name':'podium_historical_entry_disabled','passed':not p['entrance_enabled'],'actual':p['entrance_enabled']},
                      {'name':'podium_candidate_reaches_ground','passed':levels[0]==0,'actual':levels[0]}]}
