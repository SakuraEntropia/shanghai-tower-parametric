"""Open balcony, inset entry and source-topology landscape; metric fits explicit."""
import math


def grade_at(p,x,y):
    from site_v8 import xy,contains
    heights=p['levels_v12']['green_mound_heights_candidate_m'];best=0.
    for poly,height in zip(p['green_polygons_px'],heights):
        points=[xy(p,q) for q in poly]
        if not contains(points,(x,y)):continue
        xs=[q[0] for q in points];ys=[q[1] for q in points];cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
        r2=((x-cx)/((max(xs)-min(xs))/2))**2+((y-cy)/((max(ys)-min(ys))/2))**2
        distance=1e9
        for a,b in zip(points,points[1:]+points[:1]):
            dx,dy=b[0]-a[0],b[1]-a[1];u=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
            distance=min(distance,math.hypot(x-a[0]-u*dx,y-a[1]-u*dy))
        u=min(1,distance/(min(max(xs)-min(xs),max(ys)-min(ys))*.08));edge=u*u*(3-2*u)
        best=max(best,height*max(0,1-r2)**2*edge)
    return best


def build_side(ctx,p):
    from corrections_v11 import side_entry_segment,tile_panels
    from podium_v9 import _add,_meta
    from crown_pattern_v8 import cut_pane
    e=p['side_v12'];old=p['entrance_v11'];lo,hi=old['t_span'];n=old['samples']
    points=[side_entry_segment(p,lo+(hi-lo)*i/n)[0] for i in range(n+1)];lengths=[0.]
    for a,b in zip(points,points[1:]):lengths.append(lengths[-1]+math.dist(a[:2],b[:2]))
    stone=[];glass=[];reveals=[];deck=[];rail=[];frames=[]
    opening={'s_min':e['inset_fraction'][0],'s_max':e['inset_fraction'][1],'z_min_m':0,'z_max_m':e['inset_top_candidate_m']}
    for i,(a,b) in enumerate(zip(points,points[1:])):
        s0,s1=lengths[i]/lengths[-1],lengths[i+1]/lengths[-1];z=e['balcony_z_candidate_m']
        def xyz(q,depth=0):
            u=(q[0]-s0)/(s1-s0);return (a[0]+(b[0]-a[0])*u+depth,a[1]+(b[1]-a[1])*u,q[1])
        stone.extend([[xyz(q) for q in piece] for piece in cut_pane([(s0,0),(s1,0),(s1,z),(s0,z)],[opening])])
        left,right=max(s0,opening['s_min']),min(s1,opening['s_max'])
        if right>left:
            for k in range(math.ceil(opening['z_max_m']/p['PG_horizontal_pitch_candidate_m'])):
                lower=k*p['PG_horizontal_pitch_candidate_m'];upper=min(opening['z_max_m'],lower+p['PG_horizontal_pitch_candidate_m'])
                glass.append([xyz(q,e['inset_depth_candidate_m']) for q in [(left,lower),(right,lower),(right,upper),(left,upper)]])
                frames.append([xyz((left,lower),e['inset_depth_candidate_m']),xyz((right,lower),e['inset_depth_candidate_m'])])
            top=opening['z_max_m'];reveals.append([xyz((left,top)),xyz((right,top)),xyz((right,top),e['inset_depth_candidate_m']),xyz((left,top),e['inset_depth_candidate_m'])])
            for edge in (opening['s_min'],opening['s_max']):
                if s0<=edge<s1:reveals.append([xyz((edge,0)),xyz((edge,top)),xyz((edge,top),e['inset_depth_candidate_m']),xyz((edge,0),e['inset_depth_candidate_m'])])
        depth=e['balcony_depth_candidate_m'];deck.append([(a[0],a[1],z),(b[0],b[1],z),(b[0]+depth,b[1],z),(a[0]+depth,a[1],z)])
        rail.append([(a[0],a[1],z+.1),(b[0],b[1],z+.1),(b[0],b[1],z+e['guard_height_candidate_m']),(a[0],a[1],z+e['guard_height_candidate_m'])])
    meta=_meta(p,'podium_v12_open_balcony_candidate',source_ids=p['source_ids']+['USER_OBSERVATION_V12'],evidence_level='待确认',formula='Open upper balcony; lower independent stone blocks cut for a smaller recessed glass entry; original PR cut rim retained, no full-height glazed enclosure.',uncertainty=e['uncertainty'])
    for name,polys,mat,role in [('PODIUM_V12_LONG_SIDE_STONE_BLOCKS',tile_panels(p,stone),'podium_entry_white','podium_v12_stone_block_candidate'),('PODIUM_V12_INSET_ENTRANCE_GLASS',glass,'glass_detail','podium_v12_inset_entry_candidate'),('PODIUM_V12_ENTRY_STONE_REVEALS',reveals,'podium_entry_white','podium_v12_stone_return_candidate'),('PODIUM_V12_OPEN_BALCONY_FLOOR',deck,'core','podium_v12_open_balcony_candidate'),('PODIUM_V12_LOW_BALCONY_GUARD',rail,'glass_detail','podium_v12_low_balcony_guard_candidate')]:
        v=[];f=[];_add(polys,v,f);o=ctx.mesh(name,v,f,'66_PODIUM_DETAIL_CANDIDATE',mat,{**meta,'geometry_role':role})
        if mat!='glass_detail':mod=o.modifiers.new('CANDIDATE_THICKNESS','SOLIDIFY');mod.thickness=.225 if mat=='core' else .12;mod.offset=-1
    ctx.lines('PODIUM_V12_INSET_WINDOW_CABLES',frames,'66_PODIUM_DETAIL_CANDIDATE',p['PG_cable_radius_candidate_m'],'steel',meta)


def fine_canopy(ctx,geometry,p):
    from transition_v5 import outer_reference,control_profile_at
    from podium_v9 import _sample,_add,_meta
    _,refs=outer_reference(geometry,ctx.config);profile=control_profile_at(geometry,ctx.config,refs,0);old=p['south_rain_canopy'];e=p['canopy_v12'];a,b=old['profile_fraction_candidate'];n=len(profile);path=profile[round(a*n):round(b*n)+1]
    length=sum(math.dist(v,w) for v,w in zip(path,path[1:]));count=math.ceil(length/old['module_width_candidate_m']);glass=[];ribs=[];edges=[];clips=[];drains=[]
    def point(f,d):
        v=_sample(path,f);r=math.hypot(v[0],v[1]);return (v[0]*(1+d/r),v[1]*(1+d/r),old['z_candidate_m']+.02*d)
    for i in range(count):
        gap=e['joint_candidate_m']/length;f0=i/count+gap/2;f1=(i+1)/count-gap/2
        for j in range(e['radial_rows']):
            d0=j*old['width_candidate_m']/e['radial_rows']+e['joint_candidate_m']/2;d1=(j+1)*old['width_candidate_m']/e['radial_rows']-e['joint_candidate_m']/2
            glass.append([point(f,d) for f,d in ((f0,d0),(f1,d0),(f1,d1),(f0,d1))])
        f=i/count;v,w=point(f,0),point(f,old['width_candidate_m']);ribs.append([(x,y,z-old['glass_rib_clearance_candidate_m']) for x,y,z in (v,w)])
        for d in (0,old['width_candidate_m']/2,old['width_candidate_m']):
            q=point(f,d);clips.append([(q[0],q[1],q[2]-.07),(q[0],q[1],q[2]+.018)])
        if i%max(1,e['drain_panel_stride'])==0:drains.append([(v[0],v[1],v[2]-.08),(v[0],v[1],.15)])
    for d in (0,old['width_candidate_m']/2,old['width_candidate_m']):edges.append([point(i/count,d) for i in range(count+1)])
    meta=_meta(p,'podium_v12_canopy_detail_candidate',source_ids=p['source_ids']+['USER_OBSERVATION_V12'],evidence_level='待确认',formula='True glass pieces with finite joints/thickness; stainless radial ribs, perimeter edges, clamp proxies and gutter/downpipes. Metric detail candidates, not shop nodes.')
    v=[];f=[];_add(glass,v,f);o=ctx.mesh('PODIUM_V12_CANOPY_INDIVIDUAL_GLASS',v,f,'66_PODIUM_DETAIL_CANDIDATE','glass_detail',meta);mod=o.modifiers.new('GLASS_THICKNESS_CANDIDATE','SOLIDIFY');mod.thickness=e['glass_thickness_candidate_m'];mod.offset=-1
    ctx.lines('PODIUM_V12_CANOPY_STAINLESS_RIBS',ribs,'66_PODIUM_DETAIL_CANDIDATE',old['rib_radius_candidate_m'],'steel',meta)
    ctx.lines('PODIUM_V12_CANOPY_FRAME_AND_GUTTER',edges,'66_PODIUM_DETAIL_CANDIDATE',e['edge_radius_candidate_m'],'steel',meta)
    ctx.lines('PODIUM_V12_CANOPY_CLAMP_CANDIDATES',clips,'66_PODIUM_DETAIL_CANDIDATE',.018,'steel',meta)
    ctx.lines('PODIUM_V12_CANOPY_DRAIN_CANDIDATES',drains,'66_PODIUM_DETAIL_CANDIDATE',.025,'steel',meta)
    return len(glass)


def landscape_levels(ctx,p):
    import bmesh,json
    from site_v8 import xy,_surface
    from crown_v5 import _circle
    from podium_v9 import _add
    v=p['levels_v12'];meta={'source_ids':p['source_ids']+['USER_OBSERVATION_V12'],'evidence_level':'待确认','asbuilt_verified':False,'geometry_role':'site_v12_grade_candidate','formula':'Published p29 XY trace; image-topology mound fit and two candidate lowered public spaces; metric grades not surveyed.','uncertainty':v['uncertainty']}
    for obj in list(ctx.objects):
        if obj.name.startswith(('SITE_V8_GREEN_BAND_','SITE_V8_PARK_PATH_','SITE_V8_PARK_TREE','SITE_V8_TREE_TRUNK','SITE_V8_BENCH','SITE_V10_GREEN','SITE_V8_STREET_LAMP')):
            obj['source_ids']=json.dumps(list(dict.fromkeys(json.loads(obj['source_ids'])+['USER_OBSERVATION_V12'])))
            obj['height_rule_v12']='Candidate p29 green-band elliptical mounds with smooth zero boundary; shared ground function for path/plant/fixture; no surveyed heights.'
            obj['height_parameters_v12']=json.dumps(v)
        if obj.name.startswith(('SITE_V8_GREEN_BAND_','SITE_V8_PARK_PATH_')):
            bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.triangulate(bm,faces=list(bm.faces))
            for _ in range(12):
                edges=[e for e in bm.edges if e.calc_length()>v['terrain_mesh_step_candidate_m']]
                if not edges:break
                bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
            for vert in bm.verts:vert.co.z+=grade_at(p,vert.co.x,vert.co.y)
            bm.to_mesh(obj.data);bm.free();obj['grade_evidence_level']='待确认';obj['uncertainty']+=' Unsurveyed V12 height fit.'
        elif obj.type=='MESH' and obj.name=='SITE_V8_PARK_TREE_CROWN_PLACEHOLDERS':
            for i in range(0,len(obj.data.vertices),84):
                points=list(obj.data.vertices)[i:i+84];x=sum(q.co.x for q in points)/len(points);y=sum(q.co.y for q in points)/len(points);dz=grade_at(p,x,y)
                for q in points:q.co.z+=dz
        elif obj.type=='MESH' and obj.name.startswith('SITE_V8_BENCH_'):
            x=sum(q.co.x for q in obj.data.vertices)/len(obj.data.vertices);y=sum(q.co.y for q in obj.data.vertices)/len(obj.data.vertices)
            for q in obj.data.vertices:q.co.z+=grade_at(p,x,y)
        elif obj.type=='CURVE' and obj.name.startswith(('SITE_V10_GREEN_CURVE_CURB_','SITE_V8_PARCEL_SIDEWALK_CURB','SITE_V8_TREE_TRUNK','SITE_V8_STREET_LAMP')):
            for spline in obj.data.splines:
                fixed=grade_at(p,spline.points[0].co.x,spline.points[0].co.y) if 'TREE_TRUNK' in obj.name or 'LAMP' in obj.name else None
                for q in spline.points:q.co.z+=fixed if fixed is not None else grade_at(p,q.co.x,q.co.y)
    # Existing western recess gains retaining faces rather than a floating floor.
    west=[xy(p,q) for q in p['sunken_entrance_polygon_px']];walls=[]
    for a,b in zip(west,west[1:]+west[:1]):walls.append([(*a,-p['sunken_depth_candidate_m']),(*b,-p['sunken_depth_candidate_m']),(*b,0),(*a,0)])
    center=xy(p,p['water_garden_center_px']);depth=v['east_sunken_depth_candidate_m'];radius=v['east_sunken_radius_candidate_m'];ring=_circle(center,radius,96)
    for a,b in zip(ring,ring[1:]+ring[:1]):walls.append([(*a,-depth),(*b,-depth),(*b,0),(*a,0)])
    verts=[];faces=[];_add(walls,verts,faces);ctx.mesh('SITE_V12_TWO_SUNKEN_RETAINING_WALLS',verts,faces,'68_SUNKEN_PUBLIC_SPACE_CANDIDATE','podium_stone',meta)
    _surface(ctx,'SITE_V12_EAST_SUNKEN_WALK',ring,-depth+.12,'paving','68_SUNKEN_PUBLIC_SPACE_CANDIDATE',meta,[_circle(center,p['water_garden_radius_candidate_m'],64)])
    for obj in ctx.objects:
        if obj.name in {'SITE_V8_BAMBOO_WATER_GARDEN_CANDIDATE','SITE_V8_BAMBOO_ISLAND_CANDIDATE'}:
            for q in obj.data.vertices:q.co.z-=depth
        if obj.name=='SITE_V8_BAMBOO_STEMS_CANDIDATE':
            for spline in obj.data.splines:
                for q in spline.points:q.co.z-=depth
    steps=[];n=v['east_stair_steps_candidate'];inner=radius-v['east_stair_width_candidate_m'];outer=radius
    for i in range(n):
        a,b=[math.radians(v['east_stair_arc_candidate_deg'][0]+(v['east_stair_arc_candidate_deg'][1]-v['east_stair_arc_candidate_deg'][0])*j/n) for j in (i,i+1)];z=-depth*(i+1)/n
        steps.append([(center[0]+r*math.cos(t),center[1]+r*math.sin(t),z) for r,t in ((inner,a),(outer,a),(outer,b),(inner,b))])
    verts=[];faces=[];_add(steps,verts,faces);ctx.mesh('SITE_V12_EAST_DESCENDING_STAIR_CANDIDATE',verts,faces,'68_SUNKEN_PUBLIC_SPACE_CANDIDATE','core',meta)
