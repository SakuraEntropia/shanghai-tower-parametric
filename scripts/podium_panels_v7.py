"""PR subdivision from reported contractor rules on a PHOTO-FIT mother surface.
No claim that the unresolved axis9 or closed west sections have been recovered.
"""
import math
from bisect import bisect_left


def point(p,u,v):
    from podium_v4 import roof_xy,roof_height
    return (*roof_xy(p,u,v),roof_height(p,u,v))


def cross_section(p,u,count=384):
    vs=[-.5+i/count for i in range(count+1)];pts=[point(p,u,v) for v in vs];lengths=[0.]
    for a,b in zip(pts,pts[1:]):lengths.append(lengths[-1]+math.dist(a,b))
    return vs,lengths


def parameter_at(vs,lengths,fraction):
    target=fraction*lengths[-1];i=max(1,min(len(lengths)-1,bisect_left(lengths,target)))
    t=(target-lengths[i-1])/(lengths[i]-lengths[i-1])
    return vs[i-1]+t*(vs[i]-vs[i-1])


def planarize(pts,gap):
    center=tuple(sum(q[i] for q in pts)/len(pts) for i in range(3))
    a=[pts[1][i]-pts[0][i] for i in range(3)];b=[pts[-1][i]-pts[0][i] for i in range(3)]
    n=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]);length=math.sqrt(sum(v*v for v in n))
    if length<1e-10:return [],(0,0,1),0
    n=tuple(v/length for v in n);distances=[sum((q[i]-center[i])*n[i] for i in range(3)) for q in pts]
    result=[]
    for q,d in zip(pts,distances):
        flat=tuple(q[i]-d*n[i] for i in range(3));l=math.dist(flat,center);f=max(0,1-gap/2/max(l,1e-8))
        result.append(tuple(center[i]+(flat[i]-center[i])*f for i in range(3)))
    return result,n,max(abs(v) for v in distances)


def generate(p):
    from crown_v5 import _cut_polygons
    rules=p['pr_panel_rules'];cols=math.ceil(p['width_m']/rules['reported_length_m']);regions={'EAST':[],'WEST':[]};errors=[]
    hole=[(-p['roof_side_inner_u_left'],-.5),(p['roof_side_inner_u_right'],-.5),(p['roof_side_inner_u_right'],p['roof_back_v_min']),(-p['roof_side_inner_u_left'],p['roof_back_v_min'])]
    for i in range(cols):
        u0=-.5+i/cols;u1=-.5+(i+1)/cols;um=(u0+u1)/2
        side='EAST' if um>=0 else 'WEST';target=.3 if side=='EAST' else .2875
        v0,l0=cross_section(p,u0);v1,l1=cross_section(p,u1)
        rows=max(1,round((l0[-1]+l1[-1])/2/target))
        for j in range(rows):
            a,b=parameter_at(v0,l0,j/rows),parameter_at(v0,l0,(j+1)/rows)
            c,d=parameter_at(v1,l1,j/rows),parameter_at(v1,l1,(j+1)/rows)
            polys=_cut_polygons([[(u0,a),(u1,c),(u1,d),(u0,b)]],[hole])
            # Short western tip ends at the terrace, as visible in base aerial.
            if um<0:
                polys=[poly for poly in polys if sum(v for u,v in poly)/len(poly)>=p['left_fold_front_v_candidate']]
            for poly in polys:
                coords=[point(p,u,v) for u,v in poly]
                flat,n,e=planarize(coords,rules['reported_standard_joint_m'])
                if flat:regions[side].append((flat,n));errors.append(e)
    return regions,{'panels':sum(len(v) for v in regions.values()),'max_mother_surface_to_flat_panel_error_m':max(errors,default=0),
                    'reported_nominal_length_m':1.8,'reported_east_width_m':.3,'axis9_and_west_closed_sections_verified':False}


def build(ctx,p,meta):
    regions,report=generate(p);layers=p['pr_panel_rules']['reported_laminate_layers_m'];offset=0
    for side,panels in regions.items():
        offset=0
        for k,depth in enumerate(layers):
            verts=[];faces=[]
            for coords,n in panels:
                base=len(verts);verts.extend(tuple(q[i]-n[i]*offset for i in range(3)) for q in coords);faces.append(tuple(range(base,base+len(coords))))
            obj=ctx.mesh(f'PODIUM_V7_PR_{side}_LAYER_{k+1:02d}_GOLD_TEXTURED_LAMINATE',verts,faces,'65_PODIUM_WARM_ROOF_DERIVED','pr_gold_glass',
                         {**meta,'source_ids':['PODIUM_LINGYUN_BIM_V7','PODIUM_GENS_V4','PODIUM_GENS_GROUND_V6'],
                          'source_locator':'Contractor article §3.1.1 Fig6/12–19; reported rule, original publication/axis9/unified revisions unavailable',
                          'geometry_role':'podium_PR_gold_textured_glass_candidate','evidence_level':'待确认','reported_layer_thickness_m':depth,
                          'formula':'Cross-section arclength sampling of fitted mother; neighbour sections joined and flattened; physical gap and separate8/1.52/8mm layers',
                          'axis9_mapping_verified':False,'closed_west_curve_verified':False,'surface_fit_report':report})
            if hasattr(obj,'modifiers'):
                mod=obj.modifiers.new('LAMINATED_LAYER_REPORTED_DIMENSION_PENDING_ORIGINAL','SOLIDIFY');mod.thickness=depth;mod.offset=-1
            offset+=depth
    # The coarse source-fit mother intersects some flattened high-curvature
    # panels. Place the waterproof backing behind the actual flat panels,
    # preserving physical joints rather than exposing a crossing mother mesh.
    verts=[];faces=[]
    for panels in regions.values():
        for coords,n in panels:
            k=len(verts);verts.extend(tuple(q[i]-n[i]*.06 for i in range(3)) for q in coords);faces.append(tuple(range(k,k+len(coords))))
    obj=ctx.mesh('PODIUM_V7_PANEL_ALIGNED_WATERPROOF_BACKING',verts,faces,'65_PODIUM_WARM_ROOF_DERIVED','dark_backing',
                 {**meta,'source_ids':['PODIUM_LINGYUN_BIM_V7'],'geometry_role':'podium_PR_waterproof_backing_candidate',
                  'evidence_level':'待确认','formula':'Backpan60mm behind each fitted planar laminate; source roof standing-seam AlMgMn / wall-soffit black PVDF Al; depth and joins unresolved',
                  'continuous_waterproof_nodes_verified':False})
    if hasattr(obj,'modifiers'):
        mod=obj.modifiers.new('BACKING_SECTION_CANDIDATE','SOLIDIFY');mod.thickness=.006;mod.offset=-1
    return report
