"""Scale-bar tracing of published site/ground plan; landscape/fixtures candidates."""
import math


def xy(p,q):
    a,b=p['scale_bar_px'];scale=p['scale_bar_m']/math.dist(a,b);cx,cy=p['tower_center_px']
    x,y=(q[0]-cx)*scale,(cy-q[1])*scale;phi=math.radians(p['rotation_candidate_deg'])
    return (x*math.cos(phi)-y*math.sin(phi),x*math.sin(phi)+y*math.cos(phi))


def ccw(points):
    area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))
    return points if area>0 else list(reversed(points))


def contains(poly,q):
    odd=False;x,y=q
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:odd=not odd
    return odd


def hull(points):
    cross=lambda a,b,c:(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    pts=sorted(set(points));low=[];high=[]
    for out,seq in ((low,pts),(high,pts[::-1])):
        for q in seq:
            while len(out)>=2 and cross(out[-2],out[-1],q)<=0:out.pop()
            out.append(q)
    return low[:-1]+high[:-1]


def _surface(ctx,name,poly,z,material,col,meta,holes=()):
    from mathutils import Vector
    from mathutils.geometry import tessellate_polygon
    from crown_v5 import _cut_polygons
    points=ccw(poly);raw=tessellate_polygon([[Vector((x,y,0)) for x,y in points]])
    # Blender5.2 returns vertex indices; older installed versions returned Vectors.
    triangles=[[points[v] if isinstance(v,int) else tuple(v)[:2] for v in t] for t in raw]
    pieces=_cut_polygons(triangles,list(holes));v=[];f=[]
    for q in pieces:k=len(v);v.extend((x,y,z) for x,y in q);f.append(tuple(range(k,k+len(q))))
    return ctx.mesh(name,v,f,col,material,meta)


def _strip(points,width,z):
    v=[];f=[]
    for i,q in enumerate(points):
        a,b=points[max(0,i-1)],points[min(len(points)-1,i+1)];dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        nx,ny=-dy/length*width/2,dx/length*width/2
        v.extend(((q[0]+nx,q[1]+ny,z),(q[0]-nx,q[1]-ny,z)))
        if i:k=2*i;f.append((k-2,k-1,k+1,k))
    return v,f


def ground(ctx,p,size):
    hole=ccw([xy(p,q) for q in p['sunken_entrance_polygon_px']]);s=size/2
    holes=[hole]
    if p.get('levels_v12'):
        from crown_v5 import _circle
        holes.append(_circle(xy(p,p['water_garden_center_px']),p['levels_v12']['east_sunken_radius_candidate_m'],96))
    return _surface(ctx,'ST_DISPLAY_GROUND',[(-s,-s),(s,-s),(s,s),(-s,s)],-.025,'ground','90_VALIDATION',
            {'source_ids':p['source_ids'],'geometry_role':'presentation','uncertainty':'Display ground, cut at published-plan sunken entrance and candidate lowered water garden; no surveyed terrain.'},holes)


def build(ctx,geometry,p):
    from transition_v5 import outer_reference,control_profile_at
    from crown_v5 import _circle
    col='60_SITE_PLAN_DERIVED';green_col='61_LANDSCAPE_CANDIDATES';road_col='62_STREETS_DERIVED';retail_col='67_PODIUM_GROUND_PLAN_WING';detail_col='68_SUNKEN_PUBLIC_SPACE_CANDIDATE'
    meta={'source_ids':p['source_ids'],'source_locator':p['source_locator'],'evidence_level':'推导值','asbuilt_verified':False,
          'geometry_role':'site_plan_trace_candidate','formula':'p29 pixel trace ×100/291m per pixel, origin at published tower centre, local90deg registration candidate.',
          'uncertainty':p['uncertainty'],'pixel_error_estimate_m':p['pixel_pick_error_px']*100/291}
    from podium_v9 import rounded_poly
    meta['formula']+=' v10 quadratic Bezier corner fits at source trace controls; candidate radii, no surveying claim.'
    floor=p['ground_paving_z_m'];outline=ccw(rounded_poly([xy(p,q) for q in p['plot_sidewalk_outline_px']],p.get('contour_rounding_candidate_m',0),16)) if p.get('contour_rounding_candidate_m') else ccw([xy(p,q) for q in p['plot_sidewalk_outline_px']])
    _,ref=outer_reference(geometry,ctx.config);tower=hull([q[:2] for q in control_profile_at(geometry,ctx.config,ref,0)])
    retail=ccw([xy(p,q) for q in p['retail_wing_outline_px']]);sunken=ccw([xy(p,q) for q in p['sunken_entrance_polygon_px']]);pavilion=ccw([xy(p,q) for q in p['pavilion_outline_px']])
    if ctx.config.get('podium_v9'):
        from podium_v9 import plan_xy,rounded_poly
        q=ctx.config['podium_v9'];retail=ccw(rounded_poly([plan_xy(q,v) for v in q['ground_outline_px']],q['corner_fillet_candidate_m']))
    holes=[tower,retail,sunken,pavilion]
    if p.get('levels_v12'):holes.append(_circle(xy(p,p['water_garden_center_px']),p['levels_v12']['east_sunken_radius_candidate_m'],96))
    _surface(ctx,'SITE_V8_PUBLISHED_SIDEWALK_PLAZA',outline,floor,'paving',col,meta,holes)
    ctx.lines('SITE_V8_ACTUAL_DERIVED_TOWER_GROUND_PROFILE',[[(*q[:2],floor+.06) for q in control_profile_at(geometry,ctx.config,ref,0)+control_profile_at(geometry,ctx.config,ref[:1],0)]],col,.06,'steel',meta)
    green=[]
    path_holes=[]
    if p.get('levels_v12'):
        from site_details_v9 import smooth_route
        for path in p['paths_px']:
            vv,ff=_strip(smooth_route([xy(p,q) for q in path],p['path_rounding_candidate_m']),p['path_width_candidate_m'],0)
            path_holes.extend(ccw([vv[i][:2] for i in face]) for face in ff)
    for i,poly in enumerate(p['green_polygons_px']):
        pts=ccw(rounded_poly([xy(p,q) for q in poly],p.get('contour_rounding_candidate_m',0),16)) if p.get('contour_rounding_candidate_m') else ccw([xy(p,q) for q in poly]);green.append(pts)
        _surface(ctx,f'SITE_V8_GREEN_BAND_{i+1:02d}',pts,floor+.035,'landscape_leaf',green_col,{**meta,'geometry_role':'landscape_plan_band_candidate'},holes+path_holes)
        ctx.lines(f'SITE_V10_GREEN_CURVE_CURB_{i+1:02d}',[[(*q,floor+.075) for q in pts+pts[:1]]],green_col,.045,'core',{**meta,'geometry_role':'landscape_curve_curb_candidate'})
    for i,path in enumerate(p['paths_px']):
        from site_details_v9 import smooth_route
        pts=smooth_route([xy(p,q) for q in path],p.get('path_rounding_candidate_m',3));v,f=_strip(pts,p['path_width_candidate_m'],floor+.055)
        ctx.mesh(f'SITE_V8_PARK_PATH_{i+1:02d}',v,f,col,'paving',{**meta,'geometry_role':'landscape_path_candidate','path_width_evidence':'待确认；published route topology, candidate width'})
    for road in p['roads']:
        from site_details_v9 import smooth_route
        v,f=_strip(smooth_route([xy(p,q) for q in road['points_px']],p.get('path_rounding_candidate_m',3)),road['width_candidate_m'],-.018)
        ctx.mesh('SITE_V8_'+road['name'],v,f,road_col,'asphalt',{**meta,'geometry_role':'street_plan_candidate','street_name':road['name_zh'],'width_evidence':'Raster/registration candidate, not road engineering survey'})
    ctx.lines('SITE_V8_PARCEL_SIDEWALK_CURB_CANDIDATE',[[(*q,floor+.09) for q in outline+[outline[0]]]],col,.055,'core',meta)
    # The published first floor establishes a retail wing, not its full upper
    # concrete floor schedule. Only this explicitly candidate ground volume.
    if not ctx.config.get('podium_v9'):
        height=p['retail_ground_height_candidate_m'];roof=_surface(ctx,'PODIUM_V8_PUBLISHED_GROUND_WING_ROOF_CANDIDATE',retail,height,'core',retail_col,
                     {**meta,'geometry_role':'podium_ground_plan_retail_wing_candidate','height_evidence':'待确认；ground plan has no story elevation'},[tower])
        _surface(ctx,'PODIUM_V8_PUBLISHED_GROUND_RETAIL_FLOOR',retail,0,'core',retail_col,meta,[tower])
        v=[];f=[];frames=[]
        for a,b in zip(retail,retail[1:]+retail[:1]):
            count=max(1,round(math.dist(a,b)/p['retail_glass_module_candidate_m']))
            for i in range(count):
                x=tuple(a[j]+(b[j]-a[j])*i/count for j in range(2));y=tuple(a[j]+(b[j]-a[j])*(i+1)/count for j in range(2))
                if contains(tower,((x[0]+y[0])/2,(x[1]+y[1])/2)):continue
                k=len(v);v.extend(((*x,0),(*y,0),(*y,height),(*x,height)));f.append((k,k+1,k+2,k+3));frames.append([(*x,0),(*x,height)])
        ctx.mesh('PODIUM_V8_GROUND_RETAIL_GLAZING_CANDIDATE',v,f,retail_col,'glass_detail',
                 {**meta,'geometry_role':'podium_plan_derived_ground_glazing_candidate','uncertainty':p['uncertainty']+' Ground façade glass extent/module unresolved; published PG system categories do not provide a complete panel map.'})
        ctx.lines('PODIUM_V8_GROUND_RETAIL_SHARED_FRAMES',frames,retail_col,p['retail_frame_radius_candidate_m'],'steel',meta)
    # Actual ground cut, descending steps and guard; no painted dark opening.
    _surface(ctx,'SITE_V8_SUNKEN_PUBLIC_SPACE_FLOOR',sunken,-p['sunken_depth_candidate_m'],'paving',detail_col,{**meta,'geometry_role':'sunken_public_space_candidate'})
    n=p['sunken_steps_candidate'];v=[];f=[]
    for i in range(n):
        k=len(v);z=-p['sunken_depth_candidate_m']*(i+1)/n
        for u,t in ((0,i/n),(1,i/n),(1,(i+1)/n),(0,(i+1)/n)):
            a=tuple(sunken[0][j]+(sunken[1][j]-sunken[0][j])*u for j in range(2));b=tuple(sunken[3][j]+(sunken[2][j]-sunken[3][j])*u for j in range(2));v.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,z))
        f.append((k,k+1,k+2,k+3))
    ctx.mesh('SITE_V8_DESCENDING_STAIR_TREAD_CANDIDATES',v,f,detail_col,'core',{**meta,'geometry_role':'sunken_entry_stair_candidate','step_count_evidence':'待确认；photo confirms descending connection, exact risers and B1 datum absent'})
    ctx.lines('SITE_V8_SUNKEN_RAIL_CANDIDATE',[[(*q,p['sunken_guard_height_candidate_m']) for q in sunken+[sunken[0]]]],detail_col,.035,'steel',meta)
    center=xy(p,p['water_garden_center_px']);pool=_circle(center,p['water_garden_radius_candidate_m'],64)
    _surface(ctx,'SITE_V8_BAMBOO_WATER_GARDEN_CANDIDATE',pool,floor+.075,'water',green_col,{**meta,'geometry_role':'landscape_water_garden_candidate','location_evidence':p['water_garden_function_location_evidence']})
    island=_circle(center,p['water_garden_island_radius_candidate_m'],48)
    _surface(ctx,'SITE_V8_BAMBOO_ISLAND_CANDIDATE',island,floor+.10,'landscape_leaf',green_col,meta)
    bamboo=[]
    for i in range(p['bamboo_count_candidate']):
        phi=i*2.399963;r=p['water_garden_island_radius_candidate_m']*.8*math.sqrt((i+1)/p['bamboo_count_candidate']);x,y=center[0]+r*math.cos(phi),center[1]+r*math.sin(phi)
        bamboo.append([(x,y,floor+.1),(x,y,floor+p['bamboo_height_candidate_m'])])
    ctx.lines('SITE_V8_BAMBOO_STEMS_CANDIDATE',bamboo,green_col,.025,'landscape_leaf',{**meta,'geometry_role':'landscape_plant_candidate','count_verified':False})
    tree_points=[];spacing=p['tree_spacing_candidate_m']
    for poly in green:
        x0,x1=min(q[0] for q in poly),max(q[0] for q in poly);y0,y1=min(q[1] for q in poly),max(q[1] for q in poly)
        for i in range(math.ceil((x1-x0)/spacing)):
            for j in range(math.ceil((y1-y0)/spacing)):
                q=(x0+(i+.5)*spacing,y0+(j+.5)*spacing)
                if contains(poly,q) and not any(contains(o,q) for o in (tower,retail,sunken,pavilion)):tree_points.append(q)
    tv=[];tf=[];trunks=[]
    for x,y in tree_points:
        trunks.append([(x,y,floor),(x,y,p['tree_trunk_height_candidate_m'])]);k=len(tv);n=12
        for j in range(7):
            phi=math.pi*j/6;r=p['tree_canopy_radius_candidate_m']*math.sin(phi);z=(p['tree_trunk_height_candidate_m']+p['tree_height_candidate_m'])/2+(p['tree_height_candidate_m']-p['tree_trunk_height_candidate_m'])*math.cos(phi)/2
            tv.extend((x+r*math.cos(i*2*math.pi/n),y+r*math.sin(i*2*math.pi/n),z) for i in range(n))
        for j in range(6):
            for i in range(n):
                a=k+j*n+i;b=k+j*n+(i+1)%n
                tf.append((a,b+n,a+n) if j==0 else (a,b,b+n) if j==5 else (a,b,b+n,a+n))
    ctx.mesh('SITE_V8_PARK_TREE_CROWN_PLACEHOLDERS',tv,tf,green_col,'landscape_leaf',{**meta,'geometry_role':'landscape_plant_placeholder','count_verified':False,'count_candidate':len(tree_points)})
    ctx.lines('SITE_V8_TREE_TRUNK_PLACEHOLDERS',trunks,green_col,p['tree_trunk_radius_candidate_m'],'podium_stone',meta)
    lamps=[]
    for i in range(p['lamps_candidate_count']):
        q=outline[i%len(outline)];r=outline[(i+1)%len(outline)];t=(i/len(outline))%1;a=(q[0]*(1-t)+r[0]*t,q[1]*(1-t)+r[1]*t)
        lamps.append([(*a,0),(*a,p['lamp_height_candidate_m']),(a[0]+.8,a[1],p['lamp_height_candidate_m'])])
    ctx.lines('SITE_V8_STREET_LAMP_PLACEHOLDERS',lamps,road_col,p['lamp_radius_candidate_m'],'steel',{**meta,'geometry_role':'street_fixture_placeholder','count_verified':False})
    for i,q in enumerate(tree_points[:p['bench_candidate_count']]):ctx.box(f'SITE_V8_BENCH_PLACEHOLDER_{i+1:02d}',(q[0]+3,q[1],p['bench_size_candidate_m'][2]/2),p['bench_size_candidate_m'],green_col,'podium_stone',{**meta,'geometry_role':'street_furniture_placeholder','dimensions_verified':False})
    if p.get('street_detail_enabled',False):
        from site_details_v9 import build_details
        build_details(ctx,p,meta)
    if p.get('levels_v12'):
        from corrections_v12 import landscape_levels
        landscape_levels(ctx,p)
    return {'source_ids':p['source_ids'],'published_scale_m_per_px':100/291,'trees_candidate':len(tree_points),'roads':4,
            'sunken_entry_has_ground_cut':True,'retail_upper_RC_schedule_verified':False,'asbuilt_verified':False,
            'checks':[{'name':'v8_site_scale_and_four_streets_present','passed':len(p['roads'])==4 and abs(math.dist(xy(p,p['scale_bar_px'][0]),xy(p,p['scale_bar_px'][1]))-100)<1e-8,'actual':100}]}
