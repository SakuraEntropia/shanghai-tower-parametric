"""Photo-informed asymmetric retail podium; no survey precision is claimed."""
import math
from collections import Counter

SOURCE='PODIUM_GENS_V4'
COL='64_PODIUM_PHOTO_DERIVED'
ROOF='65_PODIUM_WARM_ROOF_DERIVED'
DETAIL='66_PODIUM_DETAIL_CANDIDATE'


def _meta(role,p,**extra):
    result={'source_ids':[SOURCE], 'source_locator':'Gensler Shanghai Tower image95597; Retail Podium hero4907/4908',
            'source_version':'Aerial photo undated; retail images are historical design renderings, not construction drawings',
            'evidence_level':'推导值', 'numeric_evidence_level':'待确认', 'asbuilt_verified':False,
            'geometry_role':role, 'formula':'Photo-informed local candidate controls, not calibrated image-to-world measurements',
            'uncertainty':p['uncertainty'], 'orientation_georeferenced':False, 'floor_schedule_verified':False,
            'source_conflict':'D10 early2010 seven floors /38m retained as historical scheme; not used as final podium dimensions'}
    result.update(extra)
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
        t=max(0,min(1,(v+.5)/(back+.5)))
        return p['terrace_top_m']+(crest-p['terrace_top_m'])*math.sin(t*math.pi/2)
    t=max(0,min(1,(v-back)/(.5-back)))
    return crest-p['roof_back_drop_m']*(3*t*t-2*t*t*t)


def roof_xy(p,u,v):
    """Fold edge follows the rounded body corner instead of hanging off it."""
    y=v*p['depth_m'];r=p['corner_radius_m'];d=p['depth_m']/2;w=p['width_m']/2
    if abs(y)>d-r:
        halfwidth=w-r+math.sqrt(max(0,r*r-(abs(y)-d+r)**2))
        u *= halfwidth/w
    return xy(p,u,v)


def roof_mesh(p):
    """One manifold U shell: shared joins, thickness, central terrace opening."""
    us=sorted(set([-.5,.5,-p['roof_side_inner_u'],p['roof_side_inner_u']]+
                  [-.5+i/p['roof_samples_width'] for i in range(p['roof_samples_width']+1)]))
    back=p['roof_back_v_min'];count=p['roof_samples_depth']
    vs=[-.5+(back+.5)*i/count for i in range(count)]+[back+(.5-back)*i/count for i in range(count+1)]
    verts=[];top=[];lookup={}
    def vertex(i,j):
        if (i,j) not in lookup:
            lookup[(i,j)]=len(verts);u,v=us[i],vs[j]
            verts.append((*roof_xy(p,u,v),roof_height(p,u,v)))
        return lookup[(i,j)]
    for j in range(len(vs)-1):
        for i in range(len(us)-1):
            if vs[j]<back-1e-12 and abs((us[i]+us[i+1])/2)<p['roof_side_inner_u']:continue
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


def build_podium(ctx,geometry,completion,assembly):
    p=assembly['podium_v4'];body=outline(p);n=len(body);levels=p['display_slab_levels_m'];slabs=[]
    for i,z in enumerate(levels):
        slabs.append(_slab(ctx,p,f'PODIUM_V4_LEVEL_{i:02d}_CANDIDATE',body,z,p['slab_thickness_display_m'],'core','podium_candidate_slab').name)
    # Glazed low body with independent per-level candidate joints.
    verts=[];faces=[];lines=[]
    for lo,hi in zip(levels,levels[1:]):
        lower=_outline_global(p,body,lo);upper=_outline_global(p,body,hi)
        for i in range(n):
            j=(i+1)%n
            # Replace ground glass within entry bay; doors are not painted on an
            # otherwise unbroken glass wall. Current entrance positions unknown.
            entry=(lo==0 and abs(body[i][1]+p['depth_m']/2)<1e-8 and abs(body[j][1]+p['depth_m']/2)<1e-8 and
                   abs((body[i][0]+body[j][0])/2-p['entrance_offset_u']*p['width_m'])<p['entrance_width_candidate_m']/2)
            spans=[(max(lo,p['entrance_canopy_height_candidate_m']-.35) if entry else lo,hi)]
            if (body[i][1]+body[j][1])/2 <= -p['depth_m']/2+p['corner_radius_m']:
                op_lo,op_hi=p['front_opaque_band_candidate_z_m']
                spans=[(aa,min(bb,op_lo)) for aa,bb in spans if aa<op_lo]+[(max(aa,op_hi),bb) for aa,bb in spans if bb>op_hi]
            for aa,bb in spans:
                if bb<=aa:continue
                k=len(verts);verts.extend(((*lower[i][:2],aa),(*lower[j][:2],aa),(*upper[j][:2],bb),(*upper[i][:2],bb)));faces.append((k,k+1,k+2,k+3))
            lines.extend(([lower[i],upper[i]],[upper[i],upper[j]]))
    ctx.mesh('PODIUM_V4_CURVED_GLAZED_LOW_BODY',verts,faces,COL,'glass_detail',_meta('podium_candidate_glazing',p,pattern_verified=False))
    ctx.lines('PODIUM_V4_FACADE_GRID_DISPLAY',lines,DETAIL,p['frame_radius_display_m'],'steel',_meta('podium_display_grid',p,pattern_verified=False))
    # Joined U envelope: one roof with shared seam vertices and closed thickness.
    roofverts,rooffaces,boundary=roof_mesh(p)
    ctx.mesh('PODIUM_V5_CONTINUOUS_GOLD_U_FOLDED_ROOF',roofverts,rooffaces,ROOF,'derived',
             _meta('podium_photo_derived_roof',p,joined_roof_returns=True,shell_thickness_verified=False))
    ctx.lines('PODIUM_V5_ROOF_EDGE_COPING',[[roofverts[a],roofverts[b]] for a,b in boundary],ROOF,
              p['roof_coping_radius_candidate_m'],'core',_meta('podium_roof_coping_candidate',p))
    # Golden side wrap reaches the low opaque band, rather than detached eaves.
    edge=[];edgefaces=[]
    for sign in (-1,1):
        for k in range(p['roof_samples_depth']+1):
            v=-.5+(p['roof_back_v_min']+.5)*k/p['roof_samples_depth'];x,y=roof_xy(p,sign*.5,v);z=roof_height(p,sign*.5,v);b=len(edge)
            edge.extend(((x,y,z),(x,y,p['side_wrap_bottom_candidate_m'])))
            if k:edgefaces.append((b-2,b,b+1,b-1))
    ctx.mesh('PODIUM_V4_GOLD_CURVED_FASCIA',edge,edgefaces,ROOF,'derived',_meta('podium_candidate_fascia',p))
    # Aerial front edge has an opaque upper band above the lower glazed shop
    # front. Its exact cladding and height remain a photo-informed candidate.
    fascia=[];ff=[];joints=[];lo,hi=p['front_opaque_band_candidate_z_m']
    for i,a in enumerate(body):
        b=body[(i+1)%n]
        if (a[1]+b[1])/2 > -p['depth_m']/2+p['corner_radius_m']:continue
        aa=(*xy(p,a[0]/p['width_m'],a[1]/p['depth_m']),lo)
        bb=(*xy(p,b[0]/p['width_m'],b[1]/p['depth_m']),lo)
        k=len(fascia);fascia.extend((aa,bb,(*bb[:2],hi),(*aa[:2],hi)));ff.append((k,k+1,k+2,k+3))
        joints.append([aa,(*aa[:2],hi)])
    ctx.mesh('PODIUM_V5_FRONT_OPAQUE_UPPER_BAND',fascia,ff,DETAIL,'guide',_meta('podium_front_opaque_band_candidate',p))
    ctx.lines('PODIUM_V5_FRONT_BAND_VERTICAL_JOINTS',joints,DETAIL,.035,'steel',_meta('podium_candidate_cladding_seams',p,shop_pattern_verified=False))
    _terrace_details(ctx,p)
    _entrance(ctx,p)
    # Lamella / equipment zone visible on real photo; material, pitch and exact count unknown.
    lamellas=[]
    for i in range(p['lamella_count_display']):
        u=p['lamella_u_range'][0]+(p['lamella_u_range'][1]-p['lamella_u_range'][0])*i/max(1,p['lamella_count_display']-1)
        path=[]
        for j in range(9):
            v=p['lamella_v_range'][0]+(p['lamella_v_range'][1]-p['lamella_v_range'][0])*j/8
            path.append((*roof_xy(p,u,v),roof_height(p,u,v)+.18))
        lamellas.append(path)
    ctx.lines('PODIUM_V4_ROOF_LAMELLA_REGION_DISPLAY',lamellas,DETAIL,p['lamella_radius_display_m'],'steel',_meta('podium_photo_derived_roof_equipment',p,equipment_type_verified=False,count_verified=False))
    # Separate low landscape pavilion seen on right of aerial: physically separated from primary wing.
    q=dict(p);q.update(p['satellite_pavilion']);sat=satellite_outline(p)
    for z in [0,q['height_m']]:_slab(ctx,q,f'PODIUM_V4_SEPARATE_LOW_PAVILION_Z{z:g}',sat,z,p['slab_thickness_display_m'],'guide','podium_separate_pavilion_candidate')
    st=[];sf=[];low=_outline_global(q,sat,0);high=_outline_global(q,sat,q['height_m'])
    for i in range(len(sat)):
        j=(i+1)%len(sat);k=len(st);st.extend((low[i],low[j],high[j],high[i]));sf.append((k,k+1,k+2,k+3))
    ctx.mesh('PODIUM_V4_SEPARATE_LOW_PAVILION_FACADE',st,sf,DETAIL,'glass_detail',_meta('podium_separate_pavilion_candidate',p))
    frames=[];fins=[]
    for i in range(len(sat)):frames.append([low[i],high[i]])
    for i in range(q['roof_fin_count_candidate']):
        a=math.radians(q['start_angle_candidate_deg']+q['span_candidate_deg']*i/(q['roof_fin_count_candidate']-1))
        pts=[(r*math.cos(a),r*math.sin(a)) for r in [q['inner_radius_candidate_m'],q['outer_radius_candidate_m']]]
        fins.append(_outline_global(q,pts,q['height_m']+.15))
    ctx.lines('PODIUM_V5_CONCAVE_PAVILION_MULLIONS',frames,DETAIL,p['frame_radius_display_m'],'steel',_meta('podium_satellite_display_grid',p,pattern_verified=False))
    ctx.lines('PODIUM_V5_CONCAVE_PAVILION_ROOF_FINS',fins,DETAIL,.08,'core',_meta('podium_satellite_roof_fins_candidate',p,count_verified=False))
    # Candidate entrance connections remain editable interfaces, not guessed structural joints.
    ctx.empty('PODIUM_V4_TOWER_JUNCTION_UNCONFIRMED',(*p['junction_candidate_xy_m'],p['junction_candidate_z_m']),DETAIL,_meta('podium_tower_connection_interface',p,evidence_level='待确认'))
    edgecounts=Counter(tuple(sorted((a,b))) for f in rooffaces for a,b in zip(f,f[1:]+f[:1]))
    return {'source_id':SOURCE,'version':'v5-detail-candidate','slabs':slabs,'candidate_levels_m':levels,'candidate_roof_extents_m':[p['terrace_top_m'],p['roof_high_m']],
            'footprint_verified':False,'asbuilt_verified':False,'orientation_verified':False,'used_parameters':p,
            'historical_conflict':p['historical_conflict'], 'uncertainty':p['uncertainty'],
            'checks':[{'name':'podium_asymmetric_off_axis','passed':math.hypot(*p['center_xy_m'])>30,'actual':p['center_xy_m']},
                      {'name':'podium_golden_returns_and_open_terrace','passed':p['roof_side_inner_u']<.5 and p['roof_back_v_min']>-.5,'actual':True},
                      {'name':'podium_joined_roof_closed_shell','passed':all(v==2 for v in edgecounts.values()),'actual':sorted(set(edgecounts.values()))},
                      {'name':'podium_candidate_reaches_ground','passed':levels[0]==0,'actual':levels[0]}]}
