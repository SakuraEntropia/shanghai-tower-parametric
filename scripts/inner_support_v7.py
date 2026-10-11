"""B-wall lower assembly candidates; historic design topology, no shop dimensions."""
import math,json
from floors_v3 import ray_hole_radius


def i_section(p):
    w=p['beam_width_display_m']/2;h=p['beam_depth_display_m']/2
    f=p['flange_thickness_display_m'];v=p['web_thickness_display_m']/2
    return [(-w,-h),(w,-h),(w,-h+f),(v,-h+f),(v,h-f),(w,h-f),(w,h),(-w,h),(-w,h-f),(-v,h-f),(-v,-h+f),(-w,-h+f)]


def build(ctx,levels,p):
    section=i_section(p);n=len(section);verts=[];faces=[];sill=[];sf=[];clips=[];plates=0
    def segment(a,b,z):
        k=len(verts);dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);normal=(-dy/length,dx/length)
        verts.extend((pt[0]+u*normal[0],pt[1]+u*normal[1],z+v) for pt in (a,b) for u,v in section)
        faces.extend([tuple(k+i for i in reversed(range(n))),tuple(k+n+i for i in range(n))])
        faces.extend((k+i,k+(i+1)%n,k+(i+1)%n+n,k+i+n) for i in range(n))
    local={'source_ids':p['source_ids'],'source_locator':p['source_locator'],'geometry_role':'inner_floor_edge_Ibeam_candidate','evidence_level':'待确认','asbuilt_verified':False,'formula':'Ring I-beam plus radial I-joists below actual generated circular plate; core void preserved, separate from outer CWSS','uncertainty':p['uncertainty'],'used_parameters':p}
    for row in levels:
        if row['candidate_number']>=126 or row['z_m']<=0:continue
        plates+=1;r=row['radius_m']-p['sill_bracket_inset_display_m'];z=row['z_m']-row['thickness_m']-p['beam_depth_display_m']/2
        count=p['ring_samples'];points=[(r*math.cos(i*2*math.pi/count),r*math.sin(i*2*math.pi/count)) for i in range(count)]
        for a,b in zip(points,points[1:]+points[:1]):segment(a,b,z)
        for i in range(p['radial_joist_count_display']):
            angle=i*2*math.pi/p['radial_joist_count_display'];inner=ray_hole_radius(row['core_hole_vertices'],angle)
            segment((inner*math.cos(angle),inner*math.sin(angle)),(r*math.cos(angle),r*math.sin(angle)),z)
        # Backpan sits behind B glazing; floor fire seal and steel clip remain
        # separate components. These are conditional design layers, not a frit map.
        rb=row['radius_m']-p['shadowbox_depth_display_m']
        for i in range(count):
            a,b=i*2*math.pi/count,(i+1)*2*math.pi/count;k=len(sill)
            sill.extend((rb*math.cos(ph),rb*math.sin(ph),zz) for ph,zz in ((a,row['z_m']-.02),(b,row['z_m']-.02),(b,row['z_m']-p['shadowbox_height_display_m']),(a,row['z_m']-p['shadowbox_height_display_m'])))
            sf.append((k,k+1,k+2,k+3))
        for i in range(p['sill_bracket_count_display']):
            angle=i*2*math.pi/p['sill_bracket_count_display'];c,s=math.cos(angle),math.sin(angle)
            clips.append([(r*c,r*s,z+p['beam_depth_display_m']/2),((rb-.06)*c,(rb-.06)*s,row['z_m']-.06),((rb-.06)*c,(rb-.06)*s,row['z_m']+.08)])
    ctx.mesh('B_V7_FLOOR_EDGE_AND_RADIAL_I_BEAMS',verts,faces,'34_INNER_FLOOR_SUPPORT_CANDIDATE','steel',local)
    ctx.mesh('B_V7_FLOOR_EDGE_SHADOWBOX_FIRE_BACKPAN',sill,sf,'35_INNER_SILL_FIRE_BACKPAN_CANDIDATE','dark_backing',
             {**local,'geometry_role':'inner_sill_fire_backpan_candidate','formula':'G01 Fig38 fire/smoke seal behind shadow box; candidate .65m opaque backpan, no asserted final frit extent'})
    ctx.lines('B_V7_MULLION_BOTTOM_STEEL_CLIP_BRACKETS',clips,'35_INNER_SILL_FIRE_BACKPAN_CANDIDATE',.025,'steel',
              {**local,'geometry_role':'inner_mullion_sill_bracket_candidate','formula':'Open clip display proxy between perimeter beam and B frame; actual extrusion and bolts unavailable'})
    return {'supported_candidate_plates':plates,'radial_beams':plates*p['radial_joist_count_display'],'ring_beam_segments':plates*p['ring_samples'],'sill_clip_candidates':len(clips),'asbuilt_verified':False,'checks':[{'name':'inner_floor_lower_support_geometry_present','passed':plates>100 and len(faces)>1000,'actual':plates}]}
