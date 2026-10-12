"""2016 owner-photo topology fit; dimensions and full radial counts unconfirmed."""
import math


def ribbon_path(p, layer, side, samples=96):
    controls=p['tmd_eye_open_ribbon_controls_fit']
    pts=[controls[0]]+controls+[controls[-1]];path=[]
    scale=1-layer*p['tmd_eye_nested_scale_step_fit']
    for j in range(samples+1):
        t=j/samples;u=t*(len(controls)-1);k=min(len(controls)-2,int(u));f=u-k
        a,b,c,d=pts[k:k+4]
        q=[.5*((2*b[i])+(-a[i]+c[i])*f+(2*a[i]-5*b[i]+4*c[i]-d[i])*f*f+(-a[i]+3*b[i]-3*c[i]+d[i])*f*f*f) for i in range(2)]
        # Only outer limbs have long feet; inner ribbons retain blunt crossed ends.
        if layer and t<.18:q[0]*=t/.18
        x=side*q[0]*p['tmd_eye_width_fit_m']*scale
        z=p['tmd_eye_height_fit_m']*(.53+(q[1]-.53)*scale)
        y=side*p['tmd_eye_ribbon_y_weave_fit_m']*math.cos(math.pi*t)+layer*.025
        path.append((x,y,z))
    return path


def ribbon_mesh(path,width,depth,center,bottom,u_range=(0.,1.)):
    verts=[];faces=[]
    for i,v in enumerate(path):
        a=path[max(0,i-1)];b=path[min(len(path)-1,i+1)]
        dx,dz=b[0]-a[0],b[2]-a[2];l=math.hypot(dx,dz);nx,nz=-dz/l,dx/l
        u=u_range[0]+(u_range[1]-u_range[0])*i/(len(path)-1)
        taper=.48+.52*math.sin(math.pi*u)**.45;w=width*taper/2
        for sign,dy in ((1,-depth/2),(-1,-depth/2),(-1,depth/2),(1,depth/2)):
            verts.append((center[0]+v[0]+sign*w*nx,center[1]+v[1]+dy,bottom+v[2]+sign*w*nz))
        if i:
            k=4*i;faces.extend((k-4+j,k-4+(j+1)%4,k+(j+1)%4,k+j) for j in range(4))
    faces.extend(((3,2,1,0),tuple(4*(len(path)-1)+i for i in range(4))))
    return verts,faces


def slot_polygon(phi,p,count=32,outer=False):
    lo,hi=p['tmd_canopy_slot_radial_limits_candidate'];r=p['tmd_canopy_slot_end_radius_uv_candidate']
    w=math.radians(p['tmd_canopy_slot_half_angle_candidate_deg']);out=[]
    if outer:
        width=p.get('tmd_canopy_slot_solid_rim_width_candidate_m',.18)
        lo-=width/(p['tmd_hall_radius_fit_m']-p['deck_oculus_radius_fit_m']);hi+=width/(p['tmd_hall_radius_fit_m']-p['deck_oculus_radius_fit_m'])
        w+=width/((p['tmd_hall_radius_fit_m']+p['deck_oculus_radius_fit_m'])/2)
    for cy,start in ((lo+r,math.pi),(hi-r,0)):
        for i in range(count//2+1):
            angle=start+i*math.pi/(count//2)
            out.append((phi+w*math.cos(angle),cy+r*math.sin(angle)))
    return out


def canopy_point(phi,t,p,roof_z,center):
    r=p['deck_oculus_radius_fit_m']+(p['tmd_hall_radius_fit_m']-p['deck_oculus_radius_fit_m'])*t
    top=roof_z-p['deck_recess_depth_fit_m']-.08
    low=p['tmd_hall_floor_owner_m']+p['tmd_canopy_low_offset_fit_m']
    z=top-(top-low)*math.sin(math.pi*t/2)**.75
    return (center[0]*(1-t)+r*math.cos(phi),center[1]*(1-t)+r*math.sin(phi),z)


def canopy_polygons(p,lamella=False,with_ids=False):
    from crown_v5 import _cut_polygons
    n=int(p['tmd_canopy_rib_count_display']);nr=48;polys=[];ids=[]
    holes=[slot_polygon(math.radians(phi)% (2*math.pi),p,outer=lamella and p.get('version','').startswith('crown-v8')) for phi in p['tmd_canopy_slot_azimuths_candidate_deg']]
    # Cross-seam holes are duplicated in adjacent periodic UV charts.
    holes += [[(phi+shift,t) for phi,t in hole] for hole in list(holes) for shift in (-2*math.pi,2*math.pi)]
    width=2*math.pi/n*(p['tmd_canopy_lamella_fill_ratio_display'] if lamella else 1)
    twist=math.radians(p['tmd_canopy_twist_candidate_deg'])
    for i in range(n):
        phi=(i+.5)*2*math.pi/n
        for j in range(nr):
            t0,t1=j/nr,(j+1)/nr
            if lamella and p.get('version','').startswith('crown-v8') and i%2:
                t0=max(t0,p['tmd_canopy_short_strip_start_candidate']);
                if t0>=t1:continue
            a=phi+(twist*t0**1.4 if lamella else 0);b=phi+(twist*t1**1.4 if lamella else 0)
            w0=w1=width
            if lamella and p.get('tmd_canopy_constant_width_candidate_m'):
                radial=lambda t:p['deck_oculus_radius_fit_m']+(p['tmd_hall_radius_fit_m']-p['deck_oculus_radius_fit_m'])*t
                fill=p['tmd_canopy_lamella_fill_ratio_display'];start=p['tmd_canopy_short_strip_start_candidate']
                w0=min(p['tmd_canopy_constant_width_candidate_m']/radial(t0),2*math.pi/n*fill*(2 if t0<start else 1))
                w1=min(p['tmd_canopy_constant_width_candidate_m']/radial(t1),2*math.pi/n*fill*(2 if t1<start else 1))
            poly=[(a-w0/2,t0),(a+w0/2,t0),(b+w1/2,t1),(b-w1/2,t1)]
            cut=_cut_polygons([poly],holes);polys.extend(cut);ids.extend([i]*len(cut))
    return (polys,holes,ids) if with_ids else (polys,holes)


def build_art(ctx,p,meta,roof_z,center):
    col='78_TMD_ART_HALL_CANDIDATE'
    local={**meta,'source_ids':['TMD_CANOPY_PHOTO_V7','OWNER_TMD_WIND_V6','TMD_2025_REFRESH_V7'],
           'source_locator':'Owner2016-04-22 photographs; artist release2018 and original photos for v8; 2025 refurbishment separately documented',
           'evidence_level':'推导值','numeric_evidence_level':'待确认','asbuilt_verified':False,
           'uncertainty':'Uncalibrated 2016 photographs; shape topology fitted, metric geometry/full counts unbounded. No asserted 2025 shop geometry.'}
    if p.get('version','').startswith('crown-v8'):
        from crown_art_v8 import build_sculpture
        local['source_ids']=local['source_ids']+['ARTIST_EYE_V8','CIMA_RHINO_HALL_V9']
        build_sculpture(ctx,p,local,center)
    else:
        for k in range(int(p['tmd_eye_nested_blade_count_display'])):
            for side in (-1,1):
                path=ribbon_path(p,k,side)
                verts,faces=ribbon_mesh(path,p['tmd_eye_blade_width_fit_m']*(1-.09*k),p['tmd_eye_blade_depth_fit_m'],center,p['tmd_hall_floor_owner_m'])
                ctx.mesh(f'TMD_V7_OPEN_CROSSED_RIBBON_{k+1:02d}_{side:+d}',verts,faces,col,'tmd_eye',
                         {**local,'geometry_role':'tmd_sculpture_open_crossed_ribbon_candidate','formula':'Open Catmull-Rom broad blade; crossed flat cut tips, outer flared feet; independent paired depth weave','candidate_layer':k+1})
    fine=[]
    for deg in p['tmd_canopy_slot_azimuths_candidate_deg']:
        for j in range(p['tmd_fine_cables_per_slot_candidate']):
            phi=math.radians(deg)+(j-(p['tmd_fine_cables_per_slot_candidate']-1)/2)*.016
            r0=p['tmd_suspension_bottom_radius_fit_m'];r1=p['tmd_suspension_top_radius_fit_m']
            fine.append([(center[0]+r0*math.cos(phi),center[1]+r0*math.sin(phi),p['tmd_hall_floor_owner_m']),
                         (center[0]+r1*math.cos(phi),center[1]+r1*math.sin(phi),roof_z-p['deck_thickness_fit_m'])])
    ctx.lines('TMD_V7_FINE_SUSPENSION_GROUPS_THROUGH_RADIAL_SLOTS',fine,col,p['tmd_fine_cable_radius_candidate_m'],'steel',
              {**local,'geometry_role':'tmd_canopy_slot_suspension_candidate','formula':'Photo-visible parallel fine suspension members in slots; grouping/diameter and endpoints are candidates'})
    reports={}
    for is_lamella,name,material,depth in ((False,'DARK_BACKING_WITH_RADIAL_CAPSULE_HOLES','dark_backing',p['tmd_canopy_backing_depth_display_m']),
          (True,'RADIAL_FLAT_LAMELLAE_CLIPPED_AT_CAPSULES','canopy_gold',p['tmd_canopy_lamella_depth_display_m'])):
        polys,holes,strip_ids=canopy_polygons(p,is_lamella,True);verts=[];faces=[]
        for poly in polys:
            k=len(verts);verts.extend((q[0],q[1],q[2]-.055 if is_lamella else q[2]) for phi,t in poly for q in [canopy_point(phi,t,p,roof_z,center)])
            faces.append(tuple(range(k,k+len(poly))))
        obj=ctx.mesh('TMD_V7_'+name,verts,faces,col,material,
                     {**local,'geometry_role':'tmd_canopy_lamella_candidate' if is_lamella else 'tmd_canopy_perforated_backing_candidate',
                      'formula':f"Curved bell UV chart; capsule subtraction on backing AND blades; phi(t)=phi0+{p['tmd_canopy_twist_candidate_deg']}deg*t^1.4; constant candidate metric strip width; interior-below outward-clockwise convention",'at_least_two_apertures_visible':True,'complete_aperture_count_verified':False,'canopy_uv_holes_candidate':holes[:6]},face_attributes={'canopy_strip_id':strip_ids})
        if hasattr(obj,'modifiers'):
            mod=obj.modifiers.new('THIN_SECTION_CANDIDATE','SOLIDIFY');mod.thickness=depth;mod.offset=-1 if not is_lamella else 1
        reports[name]=len(faces)
    holes=[slot_polygon(math.radians(phi)%(2*math.pi),p) for phi in p['tmd_canopy_slot_azimuths_candidate_deg']]
    if p.get('version','').startswith('crown-v8'):
        from crown_art_v8 import build_slot_rims
        build_slot_rims(ctx,p,local,roof_z,center)
    else:
        ctx.lines('TMD_V7_RADIAL_CAPSULE_OPENING_EDGE_RETURNS',[[canopy_point(phi,t,p,roof_z,center) for phi,t in h+h[:1]] for h in holes],col,.035,'canopy_gold',
                  {**local,'geometry_role':'tmd_canopy_aperture_edge_candidate','formula':'Source-visible elongated rounded opening perimeter; candidate all-around layout'})
    oculus=[canopy_point(i*2*math.pi/96,0,p,roof_z,center) for i in range(97)]
    ctx.lines('TMD_V7_OCULUS_INNER_FINISH_RING',[oculus],col,.07,'canopy_gold',local)
    if p.get('tmd_eye_geometry_mode')=='direct_bezier_v9':
        from crown_art_v8 import build_V_supports
        build_V_supports(ctx,p,local,roof_z,center)
    return {'open_ribbon_pairs_candidate':p['tmd_eye_nested_blade_count_display'],'radial_apertures_candidate':len(holes),'at_least_two_apertures_photo_visible':True,'mesh_face_counts':reports,'scalloped_three_lobed_canopy_retired':True,'closed_almond_rings_retired':True,'asbuilt_verified':False}
