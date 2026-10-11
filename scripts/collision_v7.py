"""Inspect actual generated crown surfaces and swept-member envelopes."""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def inspect(ctx):
    verts=[];faces=[]
    for obj in ctx.objects:
        if obj.type!='MESH' or obj.get('geometry_role') not in ('crown_candidate_panel','closed_reentrant_V_crown_facade_candidate'):continue
        offset=len(verts);verts.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in f.vertices) for f in obj.data.polygons)
    if not faces:return {'checks':[{'name':'v7_crown_glass_collision_target_exists','passed':False,'actual':0}]}
    tree=BVHTree.FromPolygons(verts,faces,all_triangles=False);rows=[];bad=[]
    for obj in ctx.objects:
        if obj.type!='CURVE' or not any(c.name=='75_CROWN_STEEL_CANDIDATE' for c in obj.users_collection):continue
        radius=obj.data.bevel_depth;minimum=math.inf;crossings=0;count=0
        for sp in obj.data.splines:
            pts=[obj.matrix_world@Vector(pt.co[:3]) for pt in sp.points]
            for a,b in zip(pts,pts[1:]):
                delta=b-a;length=delta.length
                if not length:continue
                hit=tree.ray_cast(a,delta/length,length)
                if hit[0] is not None:crossings+=1
                samples=max(2,math.ceil(length/.6))
                for j in range(samples+1):
                    pt=a+delta*j/samples;nearest=tree.find_nearest(pt)
                    if nearest[0] is not None:minimum=min(minimum,nearest[3]-radius)
                    count+=1
        rows.append({'object':obj.name,'axis_crossings':crossings,'minimum_sampled_envelope_clearance_m':minimum,'sample_count':count,'radius_m':radius})
        if crossings or minimum<-.002:bad.append(rows[-1])
    return {'checks':[{'name':'v7_crown_steel_does_not_cross_generated_glass','passed':bool(rows) and not bad,'actual':{'invalid':bad,'inspected_curve_objects':len(rows)},'meaning':'Ray intersections plus .6m axis sampling minus actual bevel radius; software surface clearance only, not installed-member verification'}],
            'member_rows':rows,'target_faces':len(faces),'asbuilt_verified':False}
