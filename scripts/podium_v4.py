"""Photo-informed asymmetric retail podium; no survey precision is claimed."""
import math

SOURCE='PODIUM_GENS_V4'
COL='64_PODIUM_PHOTO_DERIVED'
ROOF='65_PODIUM_WARM_ROOF_DERIVED'
DETAIL='66_PODIUM_DETAIL_CANDIDATE'


def _meta(role,p,**extra):
    result={'source_ids':[SOURCE], 'source_locator':'Gensler Shanghai Tower image95597; Retail Podium hero4907/4908',
            'source_version':'Aerial photo undated; retail images are historical design renderings, not construction drawings',
            'evidence_level':'推导值', 'numeric_evidence_level':'待确认', 'asbuilt_verified':False,
            'geometry_role':role, 'formula':'Photo-informed local candidate; dimensions normalized by82.2m source tower diameter, without orthorectification',
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
    return points


def xy(p,u,v):
    x,y=u*p['width_m'],v*p['depth_m'];a=math.radians(p['local_azimuth_deg'])
    return (p['center_xy_m'][0]+x*math.cos(a)-y*math.sin(a),p['center_xy_m'][1]+x*math.sin(a)+y*math.cos(a))


def _outline_global(p,points,z):
    return [(*xy(p,x/p['width_m'],y/p['depth_m']),z) for x,y in points]


def _slab(ctx,p,name,points,z,thickness,material,role):
    n=len(points);top=_outline_global(p,points,z);verts=top+[(x,y,z-thickness) for x,y,_ in top]
    faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
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


def build_podium(ctx,geometry,completion,assembly):
    p=assembly['podium_v4'];body=outline(p);n=len(body);levels=p['display_slab_levels_m'];slabs=[]
    for i,z in enumerate(levels):
        slabs.append(_slab(ctx,p,f'PODIUM_V4_LEVEL_{i:02d}_CANDIDATE',body,z,p['slab_thickness_display_m'],'core','podium_candidate_slab').name)
    # Glazed low body with independent per-level candidate joints.
    verts=[];faces=[];lines=[]
    for lo,hi in zip(levels,levels[1:]):
        lower=_outline_global(p,body,lo);upper=_outline_global(p,body,hi)
        for i in range(n):
            j=(i+1)%n;k=len(verts);verts.extend((lower[i],lower[j],upper[j],upper[i]));faces.append((k,k+1,k+2,k+3))
            lines.extend(([lower[i],upper[i]],[upper[i],upper[j]]))
    ctx.mesh('PODIUM_V4_CURVED_GLAZED_LOW_BODY',verts,faces,COL,'glass_detail',_meta('podium_candidate_glazing',p,pattern_verified=False))
    ctx.lines('PODIUM_V4_FACADE_GRID_DISPLAY',lines,DETAIL,p['frame_radius_display_m'],'steel',_meta('podium_display_grid',p,pattern_verified=False))
    # Golden main roof rises across its span; two curved returns wrap terrace sides.
    # Open terrace deliberately remains visible in front half, as in the aerial source.
    def backheight(u,v):
        t=(v-p['roof_back_v_min'])/(.5-p['roof_back_v_min'])
        return p['roof_high_m']-p['roof_arch_drop_m']*(2*u)**2-p['roof_back_drop_m']*t
    _grid_patch(ctx,p,'PODIUM_V4_GOLD_MAIN_CURVED_ROOF',-.5,.5,p['roof_back_v_min'],.5,backheight,'derived','podium_photo_derived_roof')
    def sideheight(u,v):
        t=(v+.5)/(p['roof_back_v_min']+.5)
        edge=max(0,min(1,(abs(u)-p['roof_side_inner_u'])/(.5-p['roof_side_inner_u'])))
        return p['terrace_top_m']+(p['roof_high_m']-p['roof_arch_drop_m']-p['terrace_top_m'])*math.sin(t*math.pi/2)-p['roof_edge_drop_m']*edge*edge
    for sign in (-1,1):
        a,b=sorted((sign*.5,sign*p['roof_side_inner_u']))
        _grid_patch(ctx,p,f'PODIUM_V4_GOLD_RETURN_{sign:+d}',a,b,-.5,p['roof_back_v_min'],sideheight,'derived','podium_photo_derived_roof_return')
    # Curved downturned golden eave fascia, as broad source form rather than exact cladding joints.
    edge=[];edgefaces=[]
    for sign in (-1,1):
        for k in range(p['roof_samples_depth']+1):
            v=-.5+(p['roof_back_v_min']+.5)*k/p['roof_samples_depth'];x,y=xy(p,sign*.5,v);z=sideheight(sign*.5,v);b=len(edge)
            edge.extend(((x,y,z),(x,y,z-p['roof_fascia_depth_display_m'])))
            if k:edgefaces.append((b-2,b,b+1,b-1))
    ctx.mesh('PODIUM_V4_GOLD_CURVED_FASCIA',edge,edgefaces,ROOF,'derived',_meta('podium_candidate_fascia',p))
    # Terrace garden occupies exposed centre; two glazed pavilions are photo-derived proxies.
    garden=[(-.33,-.43),(.30,-.43),(.30,-.04),(-.33,-.04)]
    gp=[(u*p['width_m'],v*p['depth_m']) for u,v in garden]
    _slab(ctx,p,'PODIUM_V4_OPEN_TERRACE_GARDEN_CANDIDATE',gp,p['terrace_top_m']+.08,.15,'confirmed','podium_photo_derived_garden')
    for index,(u,v) in enumerate(p['pavilion_centres_uv']):
        x,y=xy(p,u,v);w,d=p['pavilion_size_m'];z=p['terrace_top_m'];ctx.box(f'PODIUM_V4_TERRACE_PAVILION_{index+1:02d}_CANDIDATE',(x,y,z+p['pavilion_height_m']/2),(w,d,p['pavilion_height_m']),DETAIL,'glass_detail',_meta('podium_photo_derived_pavilion',p,dimensions_verified=False))
    # Lamella / equipment zone visible on real photo; material, pitch and exact count unknown.
    lamellas=[]
    for i in range(p['lamella_count_display']):
        u=p['lamella_u_range'][0]+(p['lamella_u_range'][1]-p['lamella_u_range'][0])*i/max(1,p['lamella_count_display']-1)
        path=[]
        for j in range(9):
            v=p['lamella_v_range'][0]+(p['lamella_v_range'][1]-p['lamella_v_range'][0])*j/8
            path.append((*xy(p,u,v),backheight(u,v)+.18))
        lamellas.append(path)
    ctx.lines('PODIUM_V4_ROOF_LAMELLA_REGION_DISPLAY',lamellas,DETAIL,p['lamella_radius_display_m'],'steel',_meta('podium_photo_derived_roof_equipment',p,equipment_type_verified=False,count_verified=False))
    # Separate low landscape pavilion seen on right of aerial: physically separated from primary wing.
    q=dict(p);q.update(p['satellite_pavilion']);sat=outline(q)
    for z in [0,q['height_m']]:_slab(ctx,q,f'PODIUM_V4_SEPARATE_LOW_PAVILION_Z{z:g}',sat,z,p['slab_thickness_display_m'],'guide','podium_separate_pavilion_candidate')
    st=[];sf=[];low=_outline_global(q,sat,0);high=_outline_global(q,sat,q['height_m'])
    for i in range(len(sat)):
        j=(i+1)%len(sat);k=len(st);st.extend((low[i],low[j],high[j],high[i]));sf.append((k,k+1,k+2,k+3))
    ctx.mesh('PODIUM_V4_SEPARATE_LOW_PAVILION_FACADE',st,sf,DETAIL,'glass_detail',_meta('podium_separate_pavilion_candidate',p))
    # Candidate entrance connections remain editable interfaces, not guessed structural joints.
    ctx.empty('PODIUM_V4_TOWER_JUNCTION_UNCONFIRMED',(*p['junction_candidate_xy_m'],p['junction_candidate_z_m']),DETAIL,_meta('podium_tower_connection_interface',p,evidence_level='待确认'))
    return {'source_id':SOURCE,'slabs':slabs,'candidate_levels_m':levels,'candidate_roof_extents_m':[p['terrace_top_m'],p['roof_high_m']],
            'footprint_verified':False,'asbuilt_verified':False,'orientation_verified':False,'used_parameters':p,
            'historical_conflict':p['historical_conflict'], 'uncertainty':p['uncertainty'],
            'checks':[{'name':'podium_asymmetric_off_axis','passed':math.hypot(*p['center_xy_m'])>30,'actual':p['center_xy_m']},
                      {'name':'podium_golden_returns_and_open_terrace','passed':p['roof_side_inner_u']<.5 and p['roof_back_v_min']>-.5,'actual':True},
                      {'name':'podium_candidate_reaches_ground','passed':levels[0]==0,'actual':levels[0]}]}
