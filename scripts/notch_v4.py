"""Closed reentrant V facade; published95deg angle, derived raster-fit lips.

The previous conservative K2 omission was an evidence placeholder, not a void.
Installed panels, crown clipping and height mapping remain candidate geometry.
"""
import math
from assembly_v3 import profile_at, _quads, meta


def notch_controls(geometry,cfg,p):
    grid=geometry.standard_grid(cfg,cfg['curtain']['half_panel_count'])
    lo,hi=p['lip_grid_indices'];a,b=grid[lo]['xy'],grid[hi]['xy']
    mid=tuple((x+y)/2 for x,y in zip(a,b));width=math.dist(a,b)
    depth=width/(2*math.tan(math.radians(p['interior_angle_deg']/2)))
    r=math.hypot(*mid);tip=tuple(v*(1-depth/r) for v in mid)
    return grid,a,tip,b,width,depth


def recess_points(geometry,cfg,points,p):
    """Replace only the concave corner. Mother shoulder arcs stay unchanged."""
    _,a,tip,b,_,_=notch_controls(geometry,cfg,p)
    angles=[math.atan2(v[1],v[0]) for v in (a,tip,b)]
    def radial_hit(angle,start,end):
        dx,dy=math.cos(angle),math.sin(angle);ex,ey=end[0]-start[0],end[1]-start[1]
        den=dx*ey-dy*ex
        if abs(den)<1e-12:return None
        radius=(start[0]*ey-start[1]*ex)/den
        return (radius*dx,radius*dy)
    result=[]
    for x,y in points:
        angle=math.atan2(y,x)
        if angles[0]-1e-9<=angle<=angles[2]+1e-9:
            point=radial_hit(angle,a,tip) if angle<=angles[1] else radial_hit(angle,tip,b)
            result.append(point)
        else:result.append((x,y))
    return result


def build_notch(ctx,geometry,completion,p):
    from crown_completion import trim_height,open_profile_stations,_clipped_vertical_chord
    from transition_v5 import band_schedule,step_faces,control_profile_at
    cfg=ctx.config;grid,a,tip,b,width,depth=notch_controls(geometry,cfg,p)
    xy=recess_points(geometry,cfg,[v['xy'] for v in grid],p)
    edges=[(i,(i+1)%len(grid)) for i,v in enumerate(grid) if v['excluded_by_notch_uncertainty']]
    quads=[];ordinary_quads=[];transition_quads=[];frames=[];closures=[];coverage=[]
    info=meta('closed_reentrant_V_facade_candidate',['G01','B14_GEOM'],
              'G01 Fig3 raster calibrated by WP1–WP2=47.665m; lip stations mapped to grid20/26; two planar V legs intersect at published95deg. Conditional q(z),theta(z) transform.',
              'Source plan is a design schematic, not final CAD. Lip fitting~±0.6m candidate; image line reading±4px~0.23m; systematic/version/height-dependent IR error unbounded. V panel grid and crown apex clipping unconfirmed.',
              source_locator='G01 p2 Fig3; B14_GEOM p15 Fig2.2',
              reference_notch_width_m=width,reference_notch_depth_m=depth,
              interior_angle_deg=p['interior_angle_deg'],topology_is_closed_reentrant_facade=True,
              real_panel_schedule=False)
    def band(bottom,top,previous_top=None,is_transition=False):
        row=profile_at(geometry,cfg,xy,top)
        for i,j in edges:
            v,w=row[i],row[j]
            q=[(v[0],v[1],bottom),(w[0],w[1],bottom),w,v]
            quads.append(q)
            (transition_quads if is_transition else ordinary_quads).append(q)
            frames.extend(([q[0],q[3]],[q[3],q[2]]))
        if previous_top is not None:
            old=profile_at(geometry,cfg,xy,previous_top)
            for i,j in edges:closures.extend(step_faces((old[i],old[j]),(row[i],row[j]),bottom))
        coverage.append([bottom,top])
    pitch=cfg['curtain']['nominal_band_pitch_m'];last=None
    for entry in band_schedule(cfg):
        bottom,top=entry['z_bottom_m'],entry['z_top_m']
        band(bottom,top,last,bool(entry['transition_id']));last=top
    glass=_quads(ctx,'CWA_V_REENTRANT_CLOSED_BANDS_DERIVED',ordinary_quads,'88_V_REENTRANT_FACADE','glass',info)
    if transition_quads:
        _quads(ctx,'CWA_V_REENTRANT_MEP_REFUGE_GLASS_VARIANT_CANDIDATE',transition_quads,
               '80_CURTAIN_A_TRANSITION_VARIANTS',cfg['transition_v5']['transition_glass_material'],
               {**info,'geometry_role':'transition_glass_variant_candidate','evidence_level':'待确认',
                'uncertainty':info['uncertainty']+'; equipment-zone glass material is display candidate; exact vent/spandrel/frit map unresolved.'})
    _quads(ctx,'CWA_V_REENTRANT_SEAM_CLOSURES_CANDIDATE',closures,'88_V_REENTRANT_FACADE','guide',
           {**info,'geometry_role':'horizontal_step_closure_proxy',
            'formula':'Same global A/V band schedule; intersecting horizontal chords split into simple wedges. Real joint section unknown.'})
    crown=completion['crown'];end_left=trim_height(1,crown);end_right=trim_height(0,crown)
    # Crown module now owns K2 shoulders. V crown owns ONLY actual lip20..26.
    # Rim mapping follows its shared high/low lips, and never duplicates shoulders.
    shoulderlo,shoulderhi=p['lip_grid_indices'];apex_index=(shoulderlo+shoulderhi)//2
    i0,i1=shoulderlo,shoulderhi
    crown_edges=[(i,i+1) for i in range(i0,i1)]
    heights={i:end_left+(min(end_left,end_right)-end_left)*(i-i0)/(apex_index-i0)
             if i<=apex_index else min(end_left,end_right)+(end_right-min(end_left,end_right))*(i-apex_index)/(i1-apex_index)
             for i in range(i0,i1+1)}
    heights[apex_index]=min(end_left,end_right)
    cfaces=[];cverts=[];crown_closures=[];z=542.;last=None
    while z<max(heights.values())-1e-8:
        top=min(z+pitch,max(heights.values()))
        for i,j in crown_edges:
            if z>=max(heights[i],heights[j])-1e-8:continue
            if crown.get('curtain_pattern_mode')=='shared_lower_grid':
                row=control_profile_at(geometry,cfg,[xy[i],xy[j]],top)
                face=_clipped_vertical_chord(row[0],row[1],z,top,heights[i],heights[j])
                if not face:continue
                k=len(cverts);cverts.extend(face);cfaces.append(tuple(range(k,k+len(face))))
                frames.extend(([face[k],face[(k+1)%len(face)]] for k in range(len(face))))
                if last is not None:
                    old=control_profile_at(geometry,cfg,[xy[i],xy[j]],last)
                    for q in step_faces(old,row,z):
                        # Step caps are frame/seal proxies, not extra glass panes.
                        crown_closures.append(q)
                continue
            # Evaluate corner at its actual clipped height; crown lips coincide
            # with crown perimeter control, unlike the old over-high chord XY.
            zi,zj=min(z,heights[i]),min(z,heights[j]);ti,tj=min(top,heights[i]),min(top,heights[j])
            pi=control_profile_at(geometry,cfg,[xy[i]],zi)[0]
            pj=control_profile_at(geometry,cfg,[xy[j]],zj)[0]
            qi=control_profile_at(geometry,cfg,[xy[i]],ti)[0]
            qj=control_profile_at(geometry,cfg,[xy[j]],tj)[0]
            face=[pi,pj,qj,qi]
            triangles=[[pi,pj,qj],[pi,qj,qi]]
            for triangle in triangles:
                if min(math.dist(a,b) for a,b in zip(triangle,triangle[1:]+triangle[:1]))<1e-8:continue
                k=len(cverts);cverts.extend(triangle);cfaces.append((k,k+1,k+2))
            frames.extend(([face[k],face[(k+1)%len(face)]] for k in range(len(face))))
        last=top;z=top
    ctx.mesh('CWA_V_CROWN_REENTRANT_CLOSED_TRIM_CANDIDATE',cverts,cfaces,'88_V_REENTRANT_FACADE','glass',
             {**info,'geometry_role':'closed_reentrant_V_crown_facade_candidate',
              'crown_lip_grid_indices':[i0,i1], 'crown_lip_elevations_m':[end_left,end_right],
              'crown_shoulders_owned_by':'crown_completion',
              'formula':'Shared lower parent chords extruded vertically and clipped by original crown lip heights; stepped seals retained.' if crown.get('curtain_pattern_mode')=='shared_lower_grid' else 'Actual clipped-height q(z),theta(z) corners; highlip→lower-apex→lowlip mapping is explicit candidate. Triangles avoid warped automatic quads.',
              'uncertainty':info['uncertainty']+'; exact V rim/apex height remains unconfirmed; triangular mesh is control surface, not a fabricated triangular glass panel pattern.'})
    ctx.lines('CWA_V_REENTRANT_FRAME_CANDIDATE',frames,'88_V_REENTRANT_FACADE',p['frame_radius_display_m'],'steel',info)
    if crown_closures:_quads(ctx,'CWA_V8_CROWN_PARENT_STEP_CLOSURES',crown_closures,'88_V_REENTRANT_FACADE','guide',{**info,'geometry_role':'crown_step_closure_candidate'})
    apex=tip;leftv=(a[0]-apex[0],a[1]-apex[1]);rightv=(b[0]-apex[0],b[1]-apex[1])
    angle=math.degrees(math.acos(sum(x*y for x,y in zip(leftv,rightv))/(math.hypot(*leftv)*math.hypot(*rightv))))
    # Add plan camera-independent diagnostic data, without asserting fabrication.
    return {'type':'closed V recess, not an empty corner','source_angle_deg':95.,'actual_reference_angle_deg':angle,
            'reference_lips_m':[a,b],'reference_apex_m':apex,'reference_width_m':width,'reference_depth_m':depth,
            'added_panels':len(quads)+len(cfaces),'standard_coverage_m':coverage,
            'checks':[{'name':'V_is_reentrant_and_angle_matches','passed':depth>0 and abs(angle-p['interior_angle_deg'])<.001,'actual':{'angle_deg':angle,'depth_m':depth}},
                      {'name':'V_filled_from_ground_through_crown','passed':len(quads)>1000 and coverage[0][0]==0 and coverage[-1][1]==542 and bool(cfaces),'actual':len(quads)+len(cfaces)}],
            'crown_lips_m':[end_left,end_right], 'crown_grid_edge_range':[i0,i1],
            'standard_V_band_schedule_matches_A':True,'transition_variant_panels':len(transition_quads)}
