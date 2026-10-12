"""Image-supported podium topology and actual A-facade ring apertures.

All local metric controls are candidates. No floor slab aperture is inferred
from a facade slit. Original tower parent columns and band identities survive.
"""
import math


def ring_specs(config):
    p=config.get('transition_v5',{});q=p.get('horizontal_slits_v13',{})
    if not q.get('enabled'):return []
    half=q['clear_glass_height_candidate_m']/2
    if q.get('center_rule')=='each_transition_storey_mid_height':
        return [{'id':r['id']+f'_STOREY_{i+1:02d}_A_HORIZONTAL_SLIT',
                 'z_min_m':(a+b)/2-half,'z_max_m':(a+b)/2+half,
                 'transition_storey_range_m':[a,b],'evidence_level':'待确认'}
                for r in p['regions']
                for i,(a,b) in enumerate(((r['z_bottom_m'],r['z_middle_m']),(r['z_middle_m'],r['z_top_m'])))]
    return [{'id':r['id']+'_A_HORIZONTAL_SLIT','z_min_m':r['z_middle_m']-half,
             'z_max_m':r['z_middle_m']+half,'evidence_level':'待确认'} for r in p['regions']]


def outside_intervals(bottom,top,holes,padding=0):
    out=[(bottom,top)]
    for hole in holes:
        low,high=hole['z_min_m']-padding,hole['z_max_m']+padding;parts=[]
        for a,b in out:
            if b<=low or a>=high:parts.append((a,b));continue
            if a<low:parts.append((a,low))
            if b>high:parts.append((high,b))
        out=parts
    return [(a,b) for a,b in out if b-a>1e-8]


def glass_fragments(quad,holes):
    a,b=quad[:2]
    return [[(a[0],a[1],lo),(b[0],b[1],lo),(b[0],b[1],hi),(a[0],a[1],hi)]
            for lo,hi in outside_intervals(min(q[2] for q in quad),max(q[2] for q in quad),holes)]


def frame_fragments(a,b,holes,padding):
    if abs(a[2]-b[2])<1e-9:
        for h in holes:
            for z,sign in ((h['z_min_m'],-1),(h['z_max_m'],1)):
                if abs(a[2]-z)<1e-8:
                    return [(tuple((*a[:2],z+sign*padding)),tuple((*b[:2],z+sign*padding)))]
            if h['z_min_m']-padding<a[2]<h['z_max_m']+padding:return []
        return [(a,b)]
    intervals=outside_intervals(min(a[2],b[2]),max(a[2],b[2]),holes,padding)
    def at(z):
        f=(z-a[2])/(b[2]-a[2]);return tuple(a[k]+f*(b[k]-a[k]) for k in range(3))
    return [(at(lo),at(hi)) for lo,hi in intervals]


def slit_meta(config):
    rule=config.get('transition_v5',{}).get('horizontal_slits_v13',{}).get('center_rule')
    return {'horizontal_slits_v13':ring_specs(config),'source_ids':['B14_GEOM','G01','S13','Y19','USER_IMAGES_V13_STREET']+(['USER_STOREY_SLITS_V15'] if rule=='each_transition_storey_mid_height' else []),
            'facade_slit_width_evidence':'待确认','facade_slit_rule':('One A/V circumferential slit at midheight of EACH of the two candidate transition storeys; two rings per section, not one at their common floor. Parent chords and full slabs retained.' if rule=='each_transition_storey_mid_height' else 'Remove narrow A-only circumferential glass strip at candidate middle of two transition storeys; original parent chords retained; V corner follows same rule. Floors remain complete.')}


def side_height(p,t):
    from podium_v9 import sweep_point
    e=p['side_v13'];start,end=p['entrance_v11']['t_span'];s=(end-t)/(end-start)
    rim=sweep_point(p,t,p['entrance_v11']['roof_cut_u'])[2]
    shoulder=e['shoulder_fraction_candidate'];base=e['shoulder_start_z_candidate_m']
    return min(rim,base+(rim-base)*max(0,s)/shoulder)


def roof_quadlets(p,t0,t1,u0,u1):
    """Trim only the external long-side patch, keep the opposite roof intact."""
    from podium_v9 import sweep_point
    e=p['entrance_v11'];start,end=e['t_span'];shoulder=end-(end-start)*p['side_v13']['shoulder_fraction_candidate']
    ts=sorted({t0,t1,*[q for q in (start,shoulder,end) if t0<q<t1]});out=[]
    for a,b in zip(ts,ts[1:]):
        inside=start<(a+b)/2<end
        us=sorted({u0,u1,*([e['roof_cut_u']] if inside and u0<e['roof_cut_u']<u1 else [])})
        for c,d in zip(us,us[1:]):
            rows=[(t,*sweep_point(p,t,u)) for t,u in ((a,c),(b,c),(b,d),(a,d))]
            if inside and (c+d)/2>=e['roof_cut_u']:
                kept=[];aa=rows[-1];da=aa[3]-side_height(p,aa[0])
                for bb in rows:
                    db=bb[3]-side_height(p,bb[0])
                    if (da>1e-8)!=(db>1e-8):
                        f=da/(da-db);kept.append(tuple(aa[k]+f*(bb[k]-aa[k]) for k in range(4)))
                    if db>1e-8:kept.append(bb)
                    aa,da=bb,db
                rows=kept
            if len(rows)>2:out.append([q[1:] for q in rows])
    return out


def side_openings(p):
    e=p['side_v13'];left,right=e['inset_fraction']
    out=[{'id':'MAIN_ENTRY','s_min':left,'s_max':right,'z_min_m':0,'z_max_m':e['inset_top_candidate_m']}]
    left,right=e['slot_fraction'];half=e['slot_height_candidate_m']/2
    out += [{'id':f'SLOT_{i+1:02d}','s_min':left,'s_max':right,'z_min_m':z-half,'z_max_m':z+half}
            for i,z in enumerate(e['slot_centers_candidate_m'])]
    return out


def build_side(ctx,p):
    from podium_v9 import _add,_meta,sweep_point
    from corrections_v11 import tile_panels
    from crown_pattern_v8 import cut_pane
    e=p['side_v13'];start,end=p['entrance_v11']['t_span'];steps=e['samples'];holes=side_openings(p)
    white=[];glass=[];slots=[];returns=[];frames=[]
    points=[sweep_point(p,end-(end-start)*i/steps,p['entrance_v11']['roof_cut_u']) for i in range(steps+1)]
    # s starts at the closed glass arch end; opposite short end is the terrace.
    for i,(a,b) in enumerate(zip(points,points[1:])):
        lo,hi=i/steps,(i+1)/steps;ta,tb=end-(end-start)*lo,end-(end-start)*hi
        za,zb=side_height(p,ta),side_height(p,tb)
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);inside=(-dy/length,dx/length)
        def xyz(q,depth=0):
            f=(q[0]-lo)/(hi-lo);return (a[0]+dx*f+inside[0]*depth,a[1]+dy*f+inside[1]*depth,q[1])
        parent=[(lo,0),(hi,0),(hi,zb),(lo,za)]
        white += [[xyz(q) for q in poly] for poly in cut_pane(parent,holes)]
        for h in holes:
            left,right=max(lo,h['s_min']),min(hi,h['s_max']);bottom,top=h['z_min_m'],h['z_max_m']
            if right<=left or min(za,zb)<top:continue
            pitch=e['glass_module_height_candidate_m'];n=math.ceil((top-bottom)/pitch)
            target=glass if h['id']=='MAIN_ENTRY' else slots
            for row in range(n):
                z0=bottom+(top-bottom)*row/n;z1=bottom+(top-bottom)*(row+1)/n
                target.append([xyz(q,e['inset_depth_candidate_m']) for q in [(left,z0),(right,z0),(right,z1),(left,z1)]])
                frames.append([xyz((left,z0),e['inset_depth_candidate_m']),xyz((right,z0),e['inset_depth_candidate_m'])])
            for z in (bottom,top):
                if z>0:returns.append([xyz((left,z)),xyz((right,z)),xyz((right,z),e['inset_depth_candidate_m']),xyz((left,z),e['inset_depth_candidate_m'])])
            for side in (h['s_min'],h['s_max']):
                if lo<=side<hi:
                    returns.append([xyz((side,bottom)),xyz((side,top)),xyz((side,top),e['inset_depth_candidate_m']),xyz((side,bottom),e['inset_depth_candidate_m'])])
                    frames.append([xyz((side,bottom),e['inset_depth_candidate_m']),xyz((side,top),e['inset_depth_candidate_m'])])
            if h['id']=='MAIN_ENTRY':frames.append([xyz((left,bottom),e['inset_depth_candidate_m']),xyz((left,top),e['inset_depth_candidate_m'])])
    m=_meta(p,'podium_v13_street_side_closed_stone_candidate',source_ids=p['source_ids']+['USER_IMAGES_V13_STREET'],
            evidence_level='待确认',formula='External long side relocated to u0.72; street-photo left sloped stone shoulder, broad inset rectangular glass and3 narrow slot windows; physical stone joints. Not an open balcony on this side.',uncertainty=e['uncertainty'],
            side_orientation='s0=closed t1 arch; s1=open t0 garden',side_v13=e,opening_charts_v13=holes)
    for name,polys,mat,role in [('PODIUM_V13_STREET_STONE_FRAME_BLOCKS',tile_panels(p,white),'podium_entry_white','podium_v13_street_side_closed_stone_candidate'),
                              ('PODIUM_V13_RECESSED_LARGE_ENTRY_GLASS',glass,'glass_detail','podium_v13_recessed_entry_candidate'),
                              ('PODIUM_V13_THREE_STONE_SLOT_WINDOWS',slots,'glass_detail','podium_v13_slot_windows_candidate'),
                              ('PODIUM_V13_STONE_WINDOW_REVEALS',returns,'podium_entry_white','podium_v13_window_reveal_candidate')]:
        v=[];f=[];_add(polys,v,f);obj=ctx.mesh(name,v,f,'66_PODIUM_DETAIL_CANDIDATE',mat,{**m,'geometry_role':role})
        mod=obj.modifiers.new('CANDIDATE_THICKNESS','SOLIDIFY');mod.thickness=e['stone_thickness_candidate_m'] if mat=='podium_entry_white' else e['glass_thickness_candidate_m'];mod.offset=-1
    ctx.lines('PODIUM_V13_RECESSED_ENTRY_FINE_GRID',frames,'66_PODIUM_DETAIL_CANDIDATE',p['PG_cable_radius_candidate_m'],'steel',m)


def build_open_end(ctx,p,poly):
    if p.get('raised_end_v14',{}).get('enabled'):
        from raised_end_v14 import build
        return build(ctx,p,poly)
    from podium_v9 import _clip_height,_add,_meta
    from corrections_v11 import tile_panels
    e=p['open_end_v13'];z=e['terrace_z_candidate_m'];fascia=e['fascia_height_candidate_m'];glass=[];stone=[];rails=[]
    # Lower enclosure remains; only the upper garden opening is unglazed.
    pitch=p['PG_horizontal_pitch_candidate_m']
    for i in range(math.ceil((z-fascia)/pitch)):
        lo=i*pitch;hi=min(z-fascia,(i+1)*pitch);cut=_clip_height(poly,lo,True)
        if cut:cut=_clip_height(cut,hi,False)
        if len(cut)>2:glass.append(cut)
    cut=_clip_height(poly,z-fascia,True)
    if cut:cut=_clip_height(cut,z,False)
    if len(cut)>2:stone.append(cut)
    # Intersections with PR define the open-end horizontal guard boundary.
    hits=[]
    for a,b in zip(poly,poly[1:]):
        if (a[2]-z)*(b[2]-z)<0:
            f=(z-a[2])/(b[2]-a[2]);hits.append(tuple(a[k]+f*(b[k]-a[k]) for k in range(3)))
    if len(hits)==2:
        a,b=hits;rails.append([(a[0],a[1],z+e['guard_height_candidate_m']),(b[0],b[1],z+e['guard_height_candidate_m'])])
        n=math.ceil(math.dist(a,b)/e['guard_post_spacing_candidate_m'])
        for i in range(n+1):
            x,y=[a[k]+(b[k]-a[k])*i/n for k in (0,1)];rails.append([(x,y,z),(x,y,z+e['guard_height_candidate_m'])])
    m=_meta(p,'podium_v13_open_garden_end_candidate',source_ids=p['source_ids']+['USER_IMAGES_V13_RENDER','USER_IMAGES_V13_STREET'],
            evidence_level='待确认',formula='t0 garden end open above22m candidate; low parapet/rail and lower enclosed fascia/glass. t1 alone retains the tall closed glass arch. Gensler actual aerial takes priority over design-render shape.',uncertainty=e['uncertainty'],open_end_v13=e)
    for name,polys,mat in [('PODIUM_V13_OPEN_END_LOWER_GLAZING',glass,'glass_detail'),('PODIUM_V13_OPEN_END_STONE_FASCIA',tile_panels(p,stone),'podium_entry_white')]:
        v=[];f=[];_add(polys,v,f);ctx.mesh(name,v,f,'66_PODIUM_DETAIL_CANDIDATE',mat,m)
    ctx.lines('PODIUM_V13_OPEN_END_LOW_GUARD',rails,'66_PODIUM_DETAIL_CANDIDATE',e['guard_radius_candidate_m'],'steel',m)


def audit_scene(objects,config):
    """Read actual saved meshes; check the apertures rather than input flags."""
    holes=ring_specs(config);rows=[]
    glass=[o for o in objects if o.type=='MESH' and o.get('horizontal_slits_v13') and 'FRAME' not in o.name and 'CLOSURE' not in o.name]
    for h in holes:
        bad=[];lower=upper=0
        for obj in glass:
            for face in obj.data.polygons:
                zs=[obj.data.vertices[i].co.z for i in face.vertices];lo,hi=min(zs),max(zs)
                if hi>h['z_min_m']+1e-4 and lo<h['z_max_m']-1e-4:bad.append([obj.name,face.index])
                lower+=abs(hi-h['z_min_m'])<1e-4;upper+=abs(lo-h['z_max_m'])<1e-4
        crossed=[]
        for obj in objects:
            if not obj.get('horizontal_slits_v13') or not ('FRAME' in obj.name or 'CLOSURE' in obj.name):continue
            if obj.type=='MESH':
                for face in obj.data.polygons:
                    zs=[obj.data.vertices[i].co.z for i in face.vertices]
                    if max(zs)>h['z_min_m']+1e-4 and min(zs)<h['z_max_m']-1e-4:crossed.append([obj.name,face.index])
            elif obj.type=='CURVE':
                radius=obj.data.bevel_depth
                for index,spline in enumerate(obj.data.splines):
                    zs=[pt.co.z for pt in spline.points]
                    if zs and max(zs)+radius>h['z_min_m']+1e-4 and min(zs)-radius<h['z_max_m']-1e-4:crossed.append([obj.name,index])
        rows.append({'id':h['id'],'z_range_m':[h['z_min_m'],h['z_max_m']],'transition_storey_range_m':h.get('transition_storey_range_m'),'crossing_glass_faces':bad[:12],
                     'crossing_display_frame_or_seal_elements':crossed[:12],
                     'lower_boundary_panels':lower,'upper_boundary_panels':upper,'passed':not bad and not crossed and lower>=130 and upper>=130})
    return {'ring_apertures':rows,'old_slab_notches':sum(bool(o.get('interlayer_notch_v11')) for o in objects),
            'restored_full_transition_slabs':sum(bool(o.get('full_outer_transition_plate')) for o in objects),
            'slit_scope':'Outer A including V only; not slab holes; exact height and width unconfirmed.'}
