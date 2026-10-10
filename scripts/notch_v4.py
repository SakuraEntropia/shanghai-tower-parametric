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
    cfg=ctx.config;grid,a,tip,b,width,depth=notch_controls(geometry,cfg,p)
    xy=recess_points(geometry,cfg,[v['xy'] for v in grid],p)
    edges=[(i,(i+1)%len(grid)) for i,v in enumerate(grid) if v['excluded_by_notch_uncertainty']]
    quads=[];frames=[];closures=[];coverage=[]
    info=meta('closed_reentrant_V_facade_candidate',['G01','B14_GEOM'],
              'G01 Fig3 raster calibrated by WP1–WP2=47.665m; lip stations mapped to grid20/26; two planar V legs intersect at published95deg. Conditional q(z),theta(z) transform.',
              'Source plan is a design schematic, not final CAD. Lip fitting~±0.6m candidate; image line reading±4px~0.23m; systematic/version/height-dependent IR error unbounded. V panel grid and crown apex clipping unconfirmed.',
              source_locator='G01 p2 Fig3; B14_GEOM p15 Fig2.2',
              reference_notch_width_m=width,reference_notch_depth_m=depth,
              interior_angle_deg=p['interior_angle_deg'],topology_is_closed_reentrant_facade=True,
              real_panel_schedule=False)
    def band(bottom,top,previous_top=None):
        row=profile_at(geometry,cfg,xy,top)
        for i,j in edges:
            v,w=row[i],row[j]
            q=[(v[0],v[1],bottom),(w[0],w[1],bottom),w,v]
            quads.append(q);frames.extend(([q[0],q[3]],[q[3],q[2]]))
        if previous_top is not None:
            old=profile_at(geometry,cfg,xy,previous_top)
            for i,j in edges:closures.append([(old[i][0],old[i][1],bottom),(old[j][0],old[j][1],bottom),(row[j][0],row[j][1],bottom),(row[i][0],row[i][1],bottom)])
        coverage.append([bottom,top])
    ranges=[(0.,45.)]+list(zip(cfg['curtain']['standard_zone_reference_boundaries_m'],cfg['curtain']['standard_zone_reference_boundaries_m'][1:]))
    pitch=cfg['curtain']['nominal_band_pitch_m'];last=None
    for lo,hi in ranges:
        z=lo
        while z<hi-1e-8:
            top=min(hi,z+pitch);band(z,top,last);last=top;z=top
    glass=_quads(ctx,'CWA_V_REENTRANT_CLOSED_BANDS_DERIVED',quads,'88_V_REENTRANT_FACADE','glass',info)
    _quads(ctx,'CWA_V_REENTRANT_SEAM_CLOSURES_CANDIDATE',closures,'88_V_REENTRANT_FACADE','steel',info)
    crown=completion['crown'];end_left=trim_height(1,crown);end_right=trim_height(0,crown)
    # Approximate crop over the replacement corner; no supposed measured 3D map.
    i0,i1=edges[0][0],edges[-1][1];left=(i1-i0)//2
    heights={i:end_left+(end_right-end_left)*(i-i0)/(i1-i0) for i in range(i0,i1+1)}
    shoulderlo,shoulderhi=p['lip_grid_indices'];apex_index=(shoulderlo+shoulderhi)//2
    heights[apex_index]=min(end_left,end_right)
    cfaces=[];cverts=[];z=542.;last=None
    while z<max(heights.values())-1e-8:
        top=min(z+pitch,max(heights.values()));row=profile_at(geometry,cfg,xy,top)
        for i,j in edges:
            face=_clipped_vertical_chord(row[i],row[j],z,top,heights[i],heights[j])
            if face:
                k=len(cverts);cverts.extend(face);cfaces.append(tuple(range(k,k+len(face))))
                frames.extend(([face[k],face[(k+1)%len(face)]] for k in range(len(face))))
        z=top
    ctx.mesh('CWA_V_CROWN_REENTRANT_CLOSED_TRIM_CANDIDATE',cverts,cfaces,'88_V_REENTRANT_FACADE','glass',info)
    ctx.lines('CWA_V_REENTRANT_FRAME_CANDIDATE',frames,'88_V_REENTRANT_FACADE',p['frame_radius_display_m'],'steel',info)
    apex=tip;leftv=(a[0]-apex[0],a[1]-apex[1]);rightv=(b[0]-apex[0],b[1]-apex[1])
    angle=math.degrees(math.acos(sum(x*y for x,y in zip(leftv,rightv))/(math.hypot(*leftv)*math.hypot(*rightv))))
    # Add plan camera-independent diagnostic data, without asserting fabrication.
    return {'type':'closed V recess, not an empty corner','source_angle_deg':95.,'actual_reference_angle_deg':angle,
            'reference_lips_m':[a,b],'reference_apex_m':apex,'reference_width_m':width,'reference_depth_m':depth,
            'added_panels':len(quads)+len(cfaces),'standard_coverage_m':coverage,
            'checks':[{'name':'V_is_reentrant_and_angle_matches','passed':depth>0 and abs(angle-p['interior_angle_deg'])<.001,'actual':{'angle_deg':angle,'depth_m':depth}},
                      {'name':'V_filled_from_ground_through_crown','passed':len(glass.data.polygons)>1000 and coverage[0][0]==0 and coverage[-1][1]==542 and bool(cfaces),'actual':len(quads)+len(cfaces)}]}
