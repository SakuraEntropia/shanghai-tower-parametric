"""Artist-reported C3/nominal dimensions; folded surfaces and tile layout fitted."""
import math


def ribbon_path(p, layer, side, samples=128):
    """Two tangent-continuous arcs. Never collapse lower nested limbs to zero."""
    segs=p['tmd_eye_bezier_segments_candidate'];path=[]
    scale=1-layer*p['tmd_eye_nested_scale_step_fit']
    for j in range(samples+1):
        start=0 if layer==0 else p.get('tmd_eye_inner_limb_trim_candidate_fraction',.12)+(layer-1)*p.get('tmd_eye_inner_limb_trim_step_candidate_fraction',.015)
        t=start+(1-start)*j/samples
        # The first segment occupies 23% of vertical extent; common tangent
        # at the join was fitted to the CIMA03 continuous curved backbone.
        k=0 if t<.23 else 1;u=t/.23 if k==0 else (t-.23)/.77
        weights=((1-u)**3,3*(1-u)**2*u,3*(1-u)*u*u,u**3)
        x,z=[sum(w*q[axis] for w,q in zip(weights,segs[k])) for axis in range(2)]
        path.append((side*x*p['tmd_eye_width_fit_m']*scale,
                     side*p['tmd_eye_ribbon_y_weave_fit_m']*(1-2*t)+layer*.024,
                     p['tmd_eye_height_fit_m']*(.5+(z-.5)*scale)))
    return path


def ribbon_mesh(path,width,depth,u_range=(0.,1.),top_ratio=.38,wall=None):
    v=[];f=[]
    for i,q in enumerate(path):
        a,b=path[max(0,i-1)],path[min(len(path)-1,i+1)]
        dx,dz=b[0]-a[0],b[2]-a[2];l=math.hypot(dx,dz)
        nx,nz=-dz/l,dx/l;u=u_range[0]+(u_range[1]-u_range[0])*i/(len(path)-1)
        w=width*(1-(1-top_ratio)*u)/2
        if wall:
            thickness=min(wall,w*.6,depth*.3)
            sections=((w,depth/2),(w-thickness,depth/2-thickness))
        else:sections=((w,depth/2),)
        for halfwidth,halfdepth in sections:
            for sign,dy in ((1,-halfdepth),(-1,-halfdepth),(-1,halfdepth),(1,halfdepth)):
                v.append((q[0]+sign*halfwidth*nx,q[1]+dy,q[2]+sign*halfwidth*nz))
        if i:
            stride=8 if wall else 4;b=stride*i
            f.extend((b-stride+j,b-stride+(j+1)%4,b+(j+1)%4,b+j) for j in range(4))
            if wall:f.extend((b-stride+4+(j+1)%4,b-stride+4+j,b+4+j,b+4+(j+1)%4) for j in range(4))
    if wall:
        b=8*(len(path)-1)
        for j in range(4):f.extend(((j,(j+1)%4,4+(j+1)%4,4+j),(b+j,b+4+j,b+4+(j+1)%4,b+(j+1)%4)))
    else:f.extend(((3,2,1,0),tuple(4*(len(path)-1)+i for i in range(4))))
    return v,f


def sculpture_buffers(p,with_transform=False):
    v=[];f=[];piece_ids=[];pieces=0
    for side_index in range(3):
        phi=math.radians(p['tmd_eye_azimuth_candidate_deg'])+side_index*2*math.pi/3;c,s=math.cos(phi),math.sin(phi)
        ribbon=0
        for k in range(p['tmd_eye_nested_blade_count_display']):
            for sign in (-1,1):
                full=ribbon_path(p,k,sign);n=len(full)-1
                count=18 if ribbon<3 else 17;ribbon+=1
                for tile in range(count):
                    a=(tile+p['tmd_eye_tile_joint_fraction_candidate']/2)/count
                    b=(tile+1-p['tmd_eye_tile_joint_fraction_candidate']/2)/count
                    path=[]
                    for j in range(7):
                        u=a+(b-a)*j/6;raw=u*n;idx=min(n-1,int(raw));t=raw-idx
                        path.append(tuple(full[idx][axis]+t*(full[idx+1][axis]-full[idx][axis]) for axis in range(3)))
                    vv,ff=ribbon_mesh(path,p['tmd_eye_blade_width_fit_m']*(1-.09*k),p['tmd_eye_jade_outer_depth_candidate_m'],(a,b),p['tmd_eye_upper_width_ratio_candidate'],p['tmd_eye_jade_wall_candidate_m'])
                    # Finish only the ends of each complete ribbon. These
                    # thin plates belong to its first/last jade candidate;
                    # they do not add to the reported519 logical tile count.
                    if tile in (0,count-1):
                        start=0 if tile==0 else 8*(len(path)-1)
                        before=len(vv);vv.extend((vv[start+i][0],vv[start+i][1],vv[start+i][2]+(-.003 if tile==0 else .003)) for i in range(4))
                        ff.append(tuple(before+i for i in range(4)))
                    base=len(v);v.extend((x*c-y*s,x*s+y*c,z) for x,y,z in vv);f.extend(tuple(base+i for i in q) for q in ff)
                    piece_ids.extend([pieces]*len(ff));pieces+=1
    # Publication does not define its width axis. Use max XY bounding dimension
    # as a documented implementation convention; keep 120-degree symmetry.
    lo=[min(q[i] for q in v) for i in range(3)];hi=[max(q[i] for q in v) for i in range(3)]
    scale=p['tmd_eye_width_fit_m']/max(hi[0]-lo[0],hi[1]-lo[1]);zscale=p['tmd_eye_height_fit_m']/(hi[2]-lo[2])
    result=([(x*scale,y*scale,(z-lo[2])*zscale) for x,y,z in v],f,piece_ids,pieces)
    return result+(tuple((scale,zscale,lo[2])),) if with_transform else result


def build_sculpture(ctx,p,meta,center):
    v,f,ids,count,transform=sculpture_buffers(p,True);bottom=p['tmd_hall_floor_owner_m']+p['tmd_eye_base_height_candidate_m']
    vv=[(x+center[0],y+center[1],z+bottom) for x,y,z in v]
    obj=ctx.mesh('TMD_V8_SHANGHAI_EYE_C3_519_JADE_TILE_CANDIDATES',vv,f,'78_TMD_ART_HALL_CANDIDATE','tmd_eye',
             {**meta,'geometry_role':'tmd_sculpture_threefold_jade_tile_candidate','reported_height_m':7.7,'reported_width_m':3.89,
              'reported_tile_count':519,'actual_candidate_tile_count':count,'symmetry_order':3,'reported_data_evidence':'已证实发布名义值',
              'formula':'C3 direct tangent-continuous Bezier arcs; lower wide/upper narrow;173 thin jade candidate tiles/face; normalize height/maxXY to artist nominal; no lower-layer zero-collapse.',
              'uncertainty':'519-piece total/C3 and nominal dimensions reported by artist; ribbon layers, folds, mounting and per-tile boundaries unconfirmed. Not an original fabrication model.'},
             face_attributes={'art_tile_id':ids})
    # An independent metal backbone follows the same continuous arc. Its
    # section and attachment thickness are replaceable candidates, not jade.
    skeleton=[];sf=[]
    # Re-use tile envelope normalization, including extrema of the broad feet.
    paths=[ribbon_path(p,k,side) for k in range(p['tmd_eye_nested_blade_count_display']) for side in (-1,1)]
    # The enclosing C3 jade geometry defines the metric art extents. Metal
    # paths are normalized from the same full tile sampling, then kept inside.
    sxy,sz,zmin=transform
    for face in range(3):
        phi=math.radians(p['tmd_eye_azimuth_candidate_deg'])+face*2*math.pi/3;c,s=math.cos(phi),math.sin(phi)
        for k,path in enumerate(paths):
            vv,ff=ribbon_mesh(path,p['tmd_eye_blade_width_fit_m']*p['tmd_eye_backbone_width_ratio_candidate']*(1-.09*(k//2)),p['tmd_eye_backbone_depth_candidate_m'])
            b=len(skeleton);skeleton.extend((center[0]+sxy*(x*c-y*s),center[1]+sxy*(x*s+y*c),bottom+(z-zmin)*sz) for x,y,z in vv)
            sf.extend(tuple(b+i for i in q) for q in ff)
    ctx.mesh('TMD_V9_CONTINUOUS_CURVED_METAL_BACKBONE',skeleton,sf,'78_TMD_ART_HALL_CANDIDATE','dark_backing',
             {**meta,'source_ids':list(dict.fromkeys(meta['source_ids']+['CIMA_RHINO_HALL_V9'])),
              'geometry_role':'tmd_art_internal_backbone_candidate','formula':'CIMA03 curved backbone topology; same direct arc family as thin jade pieces; section/mount coordinates candidate.'})
    r=p['tmd_eye_base_diameter_reported_m']/2;nv=96;nr=28;basev=[];basef=[]
    for j in range(nr+1):
        rr=r*j/nr;z=p['tmd_hall_floor_owner_m']+p['tmd_eye_base_height_candidate_m']+p['tmd_eye_base_wave_amplitude_candidate_m']*math.sin(rr*p['tmd_eye_base_wave_cycles_candidate']*2*math.pi/r)
        for i in range(nv):basev.append((center[0]+rr*math.cos(i*2*math.pi/nv),center[1]+rr*math.sin(i*2*math.pi/nv),z))
    for j in range(nr):
        for i in range(nv):
            a=j*nv+i;b=j*nv+(i+1)%nv;basef.append((a,b+nv,a+nv) if j==0 else (a,b,b+nv,a+nv))
    ctx.mesh('TMD_V8_9_1M_REPORTED_COPPER_RIPPLE_BASE',basev,basef,'78_TMD_ART_HALL_CANDIDATE','copper',
             {**meta,'geometry_role':'tmd_copper_art_base_candidate','reported_diameter_m':9.1,'formula':'Artist-reported diameter and copper ripple finish; wave amplitude, cycles and installation thickness candidates.'})
    return obj


def build_slot_rims(ctx,p,meta,roof_z,center):
    from crown_art_v7 import slot_polygon,canopy_point
    v=[];f=[]
    for deg in p['tmd_canopy_slot_azimuths_candidate_deg']:
        phi=math.radians(deg)%(2*math.pi);inner=slot_polygon(phi,p);outer=slot_polygon(phi,p,outer=True)
        for i in range(len(inner)):
            j=(i+1)%len(inner);k=len(v)
            v.extend(tuple(q[a]-(.08 if a==2 else 0) for a in range(3)) for uv in (inner[i],outer[i],outer[j],inner[j]) for q in [canopy_point(*uv,p,roof_z,center)])
            f.append((k,k+1,k+2,k+3))
    obj=ctx.mesh('TMD_V8_SOLID_WIDE_CAPSULE_OPENING_RIMS',v,f,'78_TMD_ART_HALL_CANDIDATE','canopy_gold',
             {**meta,'geometry_role':'tmd_canopy_solid_aperture_rim_candidate','formula':'Annular solid sheet between inner/expanded capsule outlines; slot centre remains void; thickness/width candidates.'})
    if hasattr(obj,'modifiers'):
        mod=obj.modifiers.new('SOLID_RIM_SECTION_CANDIDATE','SOLIDIFY');mod.thickness=.05;mod.offset=1


def build_hall_enclosure(ctx,p,meta):
    z0=p['tmd_hall_floor_owner_m'];h=p['tmd_canopy_low_offset_fit_m'];r=p['tmd_hall_radius_fit_m'];n=240;nz=20;v=[];f=[]
    for j in range(nz+1):
        t=j/nz;z=z0+h*t
        for i in range(n):
            phi=2*math.pi*i/n
            wrap=(.5+.5*math.cos(p['tmd_grg_lobes_candidate']*phi))**3
            rr=r-p['tmd_grg_inward_bulge_candidate_m']*wrap*math.sin(math.pi*t)**.8
            v.append((rr*math.cos(phi),rr*math.sin(phi),z))
    for j in range(nz):
        for i in range(n):a=j*n+i;b=j*n+(i+1)%n;f.append((a,b,b+n,a+n))
    obj=ctx.mesh('TMD_V8_SCULPTED_GRG_COLUMN_WRAPS_CANDIDATE',v,f,'78_TMD_ART_HALL_CANDIDATE','grg_gradient',
             {**meta,'source_ids':list(dict.fromkeys(meta['source_ids']+['ARTIST_EYE_V8'])),
              'geometry_role':'tmd_grg_sculpted_enclosure_candidate','formula':'Published GRG column wraps with black-to-gold finish; sculpted perimeter fits photos instead of flat full-height cylinder.',
              'uncertainty':'35m nominal room control reported; wrap count, radial bulge, hidden openings and GRG shop surface unresolved.'})
    return obj


def build_V_supports(ctx,p,meta,roof_z,center):
    from crown_art_v7 import canopy_point
    paths=[];count=p['tmd_V_support_count_candidate'];r=p['tmd_V_support_radius_candidate_m'];z=p['tmd_hall_floor_owner_m']
    angle=math.radians(p['tmd_V_support_branch_half_angle_candidate_deg'])
    for i in range(count):
        phi=math.radians(p['tmd_V_support_azimuth_candidate_deg'])+i*2*math.pi/count
        foot=(r*math.cos(phi),r*math.sin(phi),z)
        t=(r-p['deck_oculus_radius_fit_m'])/(p['tmd_hall_radius_fit_m']-p['deck_oculus_radius_fit_m'])
        for sign in (-1,1):paths.append([foot,canopy_point(phi+sign*angle,t,p,roof_z,center)])
    m={**meta,'source_ids':list(dict.fromkeys(meta['source_ids']+['CIMA_RHINO_HALL_V9','ARTIST_EYE_V8'])),
       'geometry_role':'tmd_hall_V_column_candidate','formula':'CIMA01/02 and owner photo diagonal forked supports: one floor foot/two canopy nodes; continuous steel cores with separate GRG wraps.',
       'uncertainty':'V support topology source-supported;12 positions, azimuth, GRG and steel sections candidates; no structural/fabrication verification.',
       'candidate_branch_count':len(paths),'candidate_support_count':count}
    ctx.lines('TMD_V9_HEAVY_V_COLUMN_STEEL_CORES',paths,'78_TMD_ART_HALL_CANDIDATE',p['tmd_V_support_steel_radius_candidate_m'],'steel',m)
    ctx.lines('TMD_V9_HEAVY_V_COLUMN_GRG_WRAPS',paths,'78_TMD_ART_HALL_CANDIDATE',p['tmd_V_support_skin_radius_candidate_m'],'grg_gradient',m)
    return paths
