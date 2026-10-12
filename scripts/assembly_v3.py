"""Physical assembly candidates. Design facts do not certify member coordinates.

All installation choices are editable in assembly.json and tagged on objects.
The external gravity system is mega columns / belts, not a concrete outer wall.
"""
import math


DEFAULTS = {
 'cwss': {'ring_pitch_m':4.5,'ring_OD_m':.356,'ring_wall_candidate_m':.025,
          'radial_OD_candidate_m':.273,'radial_wall_m':.013,
          'hanger_diameter_candidate_m':.08,'hanger_pair_separation_display_m':.35,
          'target_radial_spacing_m':9.0,'ring_glass_inset_candidate_m':.4,
          'inner_support_inset_candidate_m':.5,'ring_samples':144},
 'frame': {'pair_tangent_offset_m':4.7,'column_circle_inset_candidate_m':2.0,
           'mega_sections_m':[[3.7,5.3],[3.4,5.0],[3.,4.8],[2.8,4.6],
                              [2.6,4.4],[2.5,4.0],[2.3,3.3],[1.9,2.4]],
           'corner_sections_m':[[2.4,5.5],[2.2,5.0],[1.8,4.8],[1.5,4.8],[1.2,4.5]],
           'belt_height_candidate_m':9.,'belt_chord_radius_display_m':.30,
           'belt_web_radius_display_m':.20,'outrigger_radius_display_m':.30,
           'outrigger_zones':[2,4,5,6,7,8],'ordinary_column_count_display':24,
           'ordinary_column_radius_display_m':.25},
 'podium': {'early_design_height_m':38.,'early_design_floors':7,
            'footprint_half_x_candidate_m':98.,'footprint_half_y_candidate_m':78.,
            'footprint_exponent_candidate':3.,'samples':144,
            'slab_thickness_display_m':.225,'facade_module_width_display_m':3.,
            'facade_mullion_radius_display_m':.06},
 'closure': {'bottom_start_m':0.,'bottom_end_m':45.,'bottom_pitch_display_m':4.5,
             'frame_radius_display_m':.025,'upper_B_end_candidate_m':579.293,
             'upper_B_radius_candidate_m':23.25},
}


def resolved(assembly):
    return {key:{**values,**assembly.get(key,{})} for key,values in DEFAULTS.items()}


def meta(role,sources,formula,uncertainty,**extra):
    return {'source_ids':sources,'evidence_level':'待确认','approximation':True,
            'asbuilt_verified':False,'geometry_role':role,'formula':formula,
            'uncertainty':uncertainty,**extra}


def profile_at(geometry,cfg,points,z):
    """Below45 is an explicit extrapolation, never passed off as source curve."""
    v=cfg['versions'][cfg['selected_geometry_version']]
    t=(z-v['z0_m'])/(v['z1_m']-v['z0_m'])
    q=math.exp(math.log(v['remaining_ratio'])*t)
    angle=math.radians(cfg['orientation']['theta0_deg']+cfg['orientation']['direction']*v['twist_deg']*t)
    c,s=math.cos(angle),math.sin(angle)
    return [(q*(x*c-y*s),q*(x*s+y*c),z) for x,y in points]


def inset(point,d):
    x,y,z=point;r=math.hypot(x,y)
    return (x*(1-d/r),y*(1-d/r),z)


def _quads(ctx,name,quads,collection,material,m):
    # Also accepts the simple triangular wedges from repaired seam topology.
    vertices=[];faces=[]
    for face in quads:
        start=len(vertices);vertices.extend(face)
        faces.append(tuple(range(start,start+len(face))))
    return ctx.mesh(name,vertices,faces,collection,material,m)


def curtain_continuity(ctx,geometry,completion,p):
    cfg=ctx.config;pitch=cfg['curtain']['nominal_band_pitch_m']
    grid=geometry.standard_grid(cfg,cfg['curtain']['half_panel_count'])
    xy=[v['xy'] for v in grid]
    edges=[(i,(i+1)%len(xy)) for i,v in enumerate(grid) if not v['excluded_by_notch_uncertainty']]
    a_quads=[];closure=[];frames=[];intervals=[]
    m=meta('curtain_A_continuity_candidate',['B14_GEOM','G01','S13'],
           'Keep source standard4.5m bands; add separately tagged residual bands and zone seam closures.',
           'Residual facade details and bottom0–45m curve are unconfirmed. Bottom uses conditional extrapolation. K2 V geometry remains absent.')
    def fill(bottom,top):
        pts=profile_at(geometry,cfg,xy,top)
        for i,j in edges:
            a,b=pts[i],pts[j]
            quad=[(a[0],a[1],bottom),(b[0],b[1],bottom),b,a]
            a_quads.append(quad);frames.extend(([quad[0],quad[3]],[quad[3],quad[2]]))
        intervals.append([bottom,top]);return pts
    unified=ctx.component_results.get('CWA_unified_v5') if cfg.get('transition_v5',{}).get('enabled') else None
    z=p['closure']['bottom_start_m'];end=p['closure']['bottom_end_m'];bp=p['closure']['bottom_pitch_display_m']
    if unified:z=end
    while z<end-1e-8:
        top=min(end,z+bp);low=fill(z,top)
        if top<end:
            high=profile_at(geometry,cfg,xy,min(end,top+bp))
            for i,j in edges:closure.append([low[i],low[j],(high[j][0],high[j][1],top),(high[i][0],high[i][1],top)])
        z=top
    bounds=[] if unified else cfg['curtain']['standard_zone_reference_boundaries_m']
    for bottom,top in zip(bounds,bounds[1:]):
        count=int(math.floor((top-bottom+1e-8)/pitch));end_band=bottom+count*pitch
        if top-end_band>1e-6:
            previous=profile_at(geometry,cfg,xy,end_band);last=fill(end_band,top)
            for i,j in edges:closure.append([previous[i],previous[j],(last[j][0],last[j][1],end_band),(last[i][0],last[i][1],end_band)])
        if top<bounds[-1]:
            low=profile_at(geometry,cfg,xy,top);high=profile_at(geometry,cfg,xy,top+pitch)
            for i,j in edges:closure.append([low[i],low[j],(high[j][0],high[j][1],top),(high[i][0],high[i][1],top)])
    a=None
    if a_quads:
        a=_quads(ctx,'CWA_BOTTOM_AND_RESIDUAL_BANDS_CANDIDATE',a_quads,'86_CWA_CONTINUITY_CANDIDATE','glass',m)
        _quads(ctx,'CWA_ZONE_AND_BOTTOM_STEP_CLOSURES_CANDIDATE',closure,'86_CWA_CONTINUITY_CANDIDATE','steel',m)
        ctx.lines('CWA_CONTINUITY_FRAME_CANDIDATE',frames,'86_CWA_CONTINUITY_CANDIDATE',p['closure']['frame_radius_display_m'],'steel',m)
    b_quads=[];b_lines=[];b_intervals=[]
    zones=completion['inner']['zones']
    bp=completion['inner']['modelling']['nominal_band_height_m']
    for zone in zones:
        r=zone['radius_m'];bottom=max(0.,zone['z0_m']);top=zone['z1_m']
        existing_start=max(45.,bottom)
        ranges=[]
        if bottom<45:ranges.append((bottom,min(top,45.)))
        if top>existing_start:
            nominal_end=existing_start+math.floor((top-existing_start+1e-8)/bp)*bp
            if top-nominal_end>1e-6:ranges.append((nominal_end,top))
        for lo,hi in ranges:
            z=lo
            while z<hi-1e-8:
                z1=min(hi,z+bp);n=round(2*math.pi*r)
                for i in range(n):
                    a0,a1=2*math.pi*i/n,2*math.pi*(i+1)/n
                    q=[(r*math.cos(a0),r*math.sin(a0),z),(r*math.cos(a1),r*math.sin(a1),z),
                       (r*math.cos(a1),r*math.sin(a1),z1),(r*math.cos(a0),r*math.sin(a0),z1)]
                    b_quads.append(q);b_lines.extend(([q[0],q[3]],[q[3],q[2]]))
                b_intervals.append([z,z1,r]);z=z1
    # Z9 inner wall is an explicit constant-radius replacement interface candidate.
    r=p['closure']['upper_B_radius_candidate_m'];z=542.;end=p['closure']['upper_B_end_candidate_m'];n=round(2*math.pi*r)
    while z<end-1e-8:
        z1=min(end,z+bp)
        for i in range(n):
            a0,a1=2*math.pi*i/n,2*math.pi*(i+1)/n
            q=[(r*math.cos(a0),r*math.sin(a0),z),(r*math.cos(a1),r*math.sin(a1),z),
               (r*math.cos(a1),r*math.sin(a1),z1),(r*math.cos(a0),r*math.sin(a0),z1)]
            b_quads.append(q);b_lines.extend(([q[0],q[3]],[q[3],q[2]]))
        b_intervals.append([z,z1,r]);z=z1
    bm=meta('curtain_B_continuity_candidate',['D10','S13','B14_STRUCT'],
            'Complete residual / bottom circular bands, append constant radius Z9 candidate.',
            'B final joint details, Z9 profile and actual panel schedule unknown; never twists B with A.')
    _quads(ctx,'CWB_BOTTOM_RESIDUAL_AND_Z9_BANDS_CANDIDATE',b_quads,'87_CWB_CONTINUITY_CANDIDATE','glass_detail',bm)
    ctx.lines('CWB_CONTINUITY_FRAME_CANDIDATE',b_lines,'87_CWB_CONTINUITY_CANDIDATE',p['closure']['frame_radius_display_m'],'steel',bm)
    return {'A_added_panels':len(a_quads),'A_unified_v5_schedule':unified,
            'A_legacy_patch_suppressed':bool(unified),'B_added_panels':len(b_quads),
            'A_added_intervals_m':intervals,'B_added_intervals_m':b_intervals,
            'checks':[{'name':'curtain_residual_and_bottom_entities',
                      'passed':bool((a_quads or unified) and b_quads),
                      'actual':[len(a.data.polygons) if a else 0,len(b_quads)],
                      'scope':'V5 A uses shared primary schedule; no coincident secondary patch.'}]}


def frame_and_cwss(ctx,geometry,completion,p):
    f=p['frame'];cw=p['cwss'];zones=completion['inner']['zones']
    boundaries=[0.]+[z['z1_m'] for z in zones]
    radii=[z['radius_m'] for z in zones]
    m=meta('primary_mega_column_candidate',['D10','S13','B14_STRUCT'],
           'Eight mega columns in paired cardinal groups; D10 zone section table. Nonrotating column axes follow derived B radii.',
           'Section dimensions are published2010 design values; axis placement, local section orientation, splices and installation boundaries remain candidate.')
    def axes(r):
        t=f['pair_tangent_offset_m'];rr=r-f['column_circle_inset_candidate_m'];d=math.sqrt(rr*rr-t*t)
        return [(t,d),(-t,d),(d,t),(d,-t),(-t,-d),(t,-d),(-d,-t),(-d,t)]
    for index in range(8):
        verts=[];faces=[]
        for k,(r,z0,z1,section) in enumerate(zip(radii,boundaries,boundaries[1:],f['mega_sections_m'])):
            x,y=axes(r)[index];nr=radii[min(k+1,7)];x1,y1=axes(nr)[index]
            w,d=section
            # Major dimension tangential on N/S, radial convention unresolved.
            if index in (2,3,6,7):w,d=d,w
            q=len(verts)
            for xx,yy,zz in ((x,y,z0),(x1,y1,z1)):
                verts.extend([(xx-w/2,yy-d/2,zz),(xx+w/2,yy-d/2,zz),(xx+w/2,yy+d/2,zz),(xx-w/2,yy+d/2,zz)])
            faces.extend([(q+3,q+2,q+1,q),(q+4,q+5,q+6,q+7),(q,q+1,q+5,q+4),
                          (q+1,q+2,q+6,q+5),(q+2,q+3,q+7,q+6),(q+3,q,q+4,q+7)])
        ctx.mesh(f'MEGA_COLUMN_{index+1:02d}_D10_SECTION_CANDIDATE_AXIS',verts,faces,'30_INSTALLED_PRIMARY_FRAME_CANDIDATE','core',m)
    for index in range(4):
        a=math.radians(45+index*90);paths=[]
        for k in range(5):
            r0=radii[k]-2.;r1=radii[k+1]-2.
            paths.append([(r0*math.cos(a),r0*math.sin(a),boundaries[k]),(r1*math.cos(a),r1*math.sin(a),boundaries[k+1])])
        # Rectangular 2010 corner sections are solids; their azimuth is a candidate.
        for k,path in enumerate(paths):
            w,d=f['corner_sections_m'][k];v=[]
            for x,y,z in path:v.extend([(x-w/2,y-d/2,z),(x+w/2,y-d/2,z),(x+w/2,y+d/2,z),(x-w/2,y+d/2,z)])
            ctx.mesh(f'CORNER_COLUMN_{index+1:02d}_Z{k+1:02d}_CANDIDATE',v,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'30_INSTALLED_PRIMARY_FRAME_CANDIDATE','core',m)
    chords=[];webs=[];outs=[];ordinary=[]
    for k,z in enumerate(boundaries[1:]):
        points=axes(radii[min(k+1,7)]);h=f['belt_height_candidate_m']
        for i,(x,y) in enumerate(points):
            u,v=points[(i+1)%8]
            for zz in (z-h,z-h/2,z):chords.append([(x,y,zz),(u,v,zz)])
            webs.extend(([(x,y,z-h),(u,v,z)],[(x,y,z),(u,v,z-h)]))
            if k+1 in f['outrigger_zones']:
                rr=math.hypot(x,y);factor=15/max(abs(x),abs(y))
                c,d=x*factor,y*factor
                outs.extend(([(c,d,z-h),(x,y,z)],[(c,d,z),(x,y,z-h)],[(c,d,z),(x,y,z)]))
    for i in range(f['ordinary_column_count_display']):
        a=2*math.pi*i/f['ordinary_column_count_display']
        ordinary.append([((r-1)*math.cos(a),(r-1)*math.sin(a),z) for r,z in zip(radii+[radii[-1]],boundaries)])
    sm=meta('primary_belt_and_outrigger_candidate',['D10','B14_STRUCT'],
            'Eight belts, six source-design outrigger zones2/4/5/6/7/8; editable candidate two-storey depth9m.',
            'Actual truss/node dimensions and member sections missing; tube display proxies express source load paths.')
    for name,paths,rad in [('BELT_CHORDS',chords,f['belt_chord_radius_display_m']),('BELT_WEBS',webs,f['belt_web_radius_display_m']),
                           ('OUTRIGGER_TRUSSES',outs,f['outrigger_radius_display_m']),('ORDINARY_GRAVITY_COLUMNS',ordinary,f['ordinary_column_radius_display_m'])]:
        ctx.lines(name+'_CANDIDATE',paths,'31_INSTALLED_BELTS_OUTRIGGERS_CANDIDATE',rad,'steel',sm)
    # Installed CWSS ring, radial link and paired hanger axes, between the skins.
    ref=geometry.sample_profile(ctx.config,cw['ring_samples'])
    if 'notch_v4' in ctx.config:
        from notch_v4 import recess_points
        ref=recess_points(geometry,ctx.config,ref,ctx.config['notch_v4'])
    total=sum(x['length'] for x in geometry.profile_segments(ctx.config))
    rings=[];radials=[];hangers=[];support=[];tabs=[];records=[];cross_rods=[]
    for zone in zones[1:]:
        z0=max(45.,zone['z0_m']);z1=zone['z1_m'];r=zone['radius_m']
        step=cw['ring_pitch_m'];levels=[z0+i*step for i in range(math.ceil((z1-z0)/step))]+[z1]
        middle=(z0+z1)/2;scale=geometry.curve_state(middle,ctx.config)['scale']
        count=max(12,round(total*scale/cw['target_radial_spacing_m']))
        stations=geometry.sample_profile(ctx.config,count)
        if 'notch_v4' in ctx.config:
            stations=recess_points(geometry,ctx.config,stations,ctx.config['notch_v4'])
        for z in levels:
            ring=[inset(point,cw['ring_glass_inset_candidate_m']) for point in geometry.transform_profile(ref,z,ctx.config)]
            rings.append(ring+[ring[0]])
            if cw.get('cross_rods_enabled',False):
                for seg in geometry.profile_segments(ctx.config):
                    if not seg['id'].startswith('K'):continue
                    theta=math.radians(seg['start_deg'])+seg['length']/seg['radius']/2
                    target=(seg['center'][0]+seg['radius']*math.cos(theta),seg['center'][1]+seg['radius']*math.sin(theta))
                    index=min(range(len(ref)),key=lambda i:math.dist(ref[i],target))
                    delta=cw['cross_corner_index_half_span_candidate'];a,b=ring[(index-delta)%len(ring)],ring[(index+delta)%len(ring)]
                    inner=[]
                    for x,y,_ in (a,b):
                        rr=math.hypot(x,y);inner.append(((r-cw['inner_support_inset_candidate_m'])*x/rr,(r-cw['inner_support_inset_candidate_m'])*y/rr,z))
                    cross_rods.extend(([inner[0],b],[inner[1],a]))
            for point in geometry.transform_profile(stations,z,ctx.config):
                out=inset(point,cw['ring_glass_inset_candidate_m']);x,y,_=out;rr=math.hypot(x,y)
                start=((r-cw['inner_support_inset_candidate_m'])*x/rr,(r-cw['inner_support_inset_candidate_m'])*y/rr,z)
                radials.append([start,out])
        for station in stations:
            lower=inset(geometry.transform_profile([station],z0,ctx.config)[0],cw['ring_glass_inset_candidate_m'])
            upper=inset(geometry.transform_profile([station],z1,ctx.config)[0],cw['ring_glass_inset_candidate_m'])
            for sign in (-1,1):
                line=[]
                for x,y,z in (lower,upper):
                    rr=math.hypot(x,y);d=sign*cw['hanger_pair_separation_display_m']/2
                    line.append((x-d*y/rr,y+d*x/rr,z))
                hangers.append(line)
                for z in levels:
                    t=(z-z0)/(z1-z0)
                    target=tuple(a+t*(b-a) for a,b in zip(line[0],line[1]))
                    out=inset(geometry.transform_profile([station],z,ctx.config)[0],cw['ring_glass_inset_candidate_m'])
                    tabs.append([out,target])
            outer=inset(geometry.transform_profile([station],z1,ctx.config)[0],cw['ring_glass_inset_candidate_m'])
            x,y,_=outer;rr=math.hypot(x,y)
            support.append([((r-.5)*x/rr,(r-.5)*y/rr,z1-.225),outer])
        records.append({'zone':zone['zone'],'ring_elevations_m':levels,'radial_count_candidate':count,'hanger_pairs':count})
    cm=meta('installed_CWSS_candidate',['B14_CWSS','G01','B14_STRUCT'],
            'Continuous CHS ring axes at4.5m; radial stations ~9m spacing; straight paired candidate hangers and bridging tabs to ring levels. Ring center0.4m inward is phase-dependent candidate.',
            'Published member OD/range retained, but final station coordinates, actual hanger straightness, brackets, V closure and beam attachment nodes unconfirmed. Solid circular display envelope is not hollow wall detailing.',
            published_ring_OD_m=.356,source_ring_wall_range_m=[.022,.025],installation_verified=False)
    for name,paths,rad in [('RINGS',rings,cw['ring_OD_m']/2),('RADIAL_STRUTS',radials,cw['radial_OD_candidate_m']/2),
                          ('PAIRED_HANGERS',hangers,cw['hanger_diameter_candidate_m']/2),('TOP_SUPPORT_TRUSSES',support,.20),('RING_HANGER_LINKS',tabs,.04)]:
        ctx.lines('CWSS_INSTALLED_'+name+'_CANDIDATE',paths,'42_INSTALLED_CWSS_CANDIDATE',rad,'steel',cm)
    if cross_rods:
        ctx.lines('CWSS_V9_THREE_CORNER_PLAN_X_CROSS_RODS',cross_rods,'42_INSTALLED_CWSS_CANDIDATE',cw['cross_rod_reported_diameter_m']/2,'steel',
                  meta('installed_CWSS_corner_cross_rods_candidate',['B14_CWSS'],'TJAD Fig3.18:3 corner cross-rod pairs at each ring level, diameter60mm; crossed inner-edge to outer-ring nodes in horizontal planes.',
                       '2014 published system/diameter; corner node coordinates from candidate A/B geometry; no all-around vertical X grid.',published_diameter_m=.06,actual_member_count=len(cross_rods)))
    return {'mega_columns':8,'corner_columns':4,'belts':8,'outrigger_zones':f['outrigger_zones'],
            'CWSS_ring_count':len(rings),'CWSS_radial_members':len(radials),'CWSS_hanger_axes':len(hangers),'CWSS_cross_rods':len(cross_rods),'zone_registry':records,
            'checks':[{'name':'eight_mega_column_solids','passed':sum(o.name.startswith('MEGA_COLUMN_') for o in ctx.objects)==8,'actual':8},
                      {'name':'installed_CWSS_entities','passed':len(rings)>100 and len(radials)>1000 and len(hangers)>100,'actual':[len(rings),len(radials),len(hangers)]}]}


def podium(ctx,geometry,p):
    a=p['podium'];n=a['samples'];height=a['early_design_height_m'];floors=a['early_design_floors']
    ref=geometry.sample_profile(ctx.config,n)
    def outline(z):
        inner=profile_at(geometry,ctx.config,ref,z);outer=[]
        for x,y,_ in inner:
            ang=math.atan2(y,x);c,s=math.cos(ang),math.sin(ang);power=a['footprint_exponent_candidate']
            r=(abs(c/a['footprint_half_x_candidate_m'])**power+abs(s/a['footprint_half_y_candidate_m'])**power)**(-1/power)
            outer.append((r*c,r*s,z))
        return inner,outer
    m=meta('podium_retail_mass_and_floors_candidate',['D10'],
           'D10 PDFp2 early2010 scheme7floors38m; uniformly distribute7 candidate levels, adaptable superellipse footprint around extrapolated tower.',
           'Retail footprint, entrance, site coordinates and final floors have no original plan; footprint dimensions and equal levels are display choices, not measurements. This is explicitly a replacement-ready podium candidate.',
           source_version='D10 2010 design, not final shopping mall survey',footprint_verified=False)
    slabs=[];facade=[];frames=[]
    for f in range(floors+1):
        z=height*f/floors;inner,outer=outline(z);t=a['slab_thickness_display_m'];verts=inner+outer+[(x,y,z-t) for x,y,z in inner]+[(x,y,z-t) for x,y,z in outer];faces=[]
        for i in range(n):
            j=(i+1)%n;faces.extend([(i,n+i,n+j,j),(2*n+j,3*n+j,3*n+i,2*n+i),(n+i,3*n+i,3*n+j,n+j),(i,j,2*n+j,2*n+i)])
        obj=ctx.mesh(f'PODIUM_F{f:02d}_SLAB_UNKNOWN_FOOTPRINT',verts,faces,'60_PODIUM_RETAIL_CANDIDATE','core',m);slabs.append(obj.name)
        if f:
            lo=height*(f-1)/floors
            for i in range(n):
                j=(i+1)%n;x,y,_=outer[i];u,v,_=outer[j]
                facade.append([(x,y,lo),(u,v,lo),(u,v,z),(x,y,z)])
                frames.extend(([(x,y,lo),(x,y,z)],[(x,y,z),(u,v,z)]))
    _quads(ctx,'PODIUM_RETAIL_GLAZING_UNKNOWN_FOOTPRINT',facade,'60_PODIUM_RETAIL_CANDIDATE','glass_detail',m)
    ctx.lines('PODIUM_RETAIL_GRID_UNKNOWN_PATTERN',frames,'60_PODIUM_RETAIL_CANDIDATE',a['facade_mullion_radius_display_m'],'steel',m)
    ctx.box('BASEMENT_MAT_DISPLAY_NOT_FOUNDATION_DESIGN',(0,0,-1.5),(110,110,3),'61_GROUNDED_BASE_CANDIDATE','core',
            meta('grounded_base_candidate',['D10','S13'],'Candidate basement top0m, spans below source base−1m.',
                 'Mat dimensions/depth are display candidates; no foundation plan or survey.') )
    return {'slabs':slabs,'facade_panels':len(facade),'source_height_m':height,'source_floors':floors,'footprint_evidence':'待确认',
            'checks':[{'name':'podium实体_exists','passed':len(slabs)==floors+1 and bool(facade),'actual':len(slabs)},
                      {'name':'bottom_shell_reaches_ground','passed':abs(min(v[2] for q in facade for v in q))<.001,'actual':0.}]}


def build_assembly(ctx,geometry,completion,assembly):
    p=resolved(assembly)
    if 'podium_v9' in assembly:
        from podium_v9 import build_podium
        retail=build_podium(ctx,geometry,completion,assembly)
    elif 'podium_v4' in assembly:
        from podium_v4 import build_podium
        retail=build_podium(ctx,geometry,completion,assembly)
    else:retail=podium(ctx,geometry,p)
    result={'curtain_continuity':curtain_continuity(ctx,geometry,completion,p),
            'load_frame_and_CWSS':frame_and_cwss(ctx,geometry,completion,p),
            'podium':retail,'used_parameters':p,'asbuilt_verified':False}
    result['checks']=[entry for value in result.values() if isinstance(value,dict) for entry in value.get('checks',[])]
    return result
