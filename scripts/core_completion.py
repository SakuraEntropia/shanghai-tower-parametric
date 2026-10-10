"""Hollow evidence-derived core walls; unperforated reference, not as-built.

The low grid is measured from Su2013 Fig5. Thicknesses retain the explicit
2010 Table1 version; openings/steel are omitted and high templates are derived.
"""
import math


def wall_regions(candidate, zone):
    """Return rectangular wall footprints (xmin,ymin,xmax,ymax)."""
    t = candidate['outer_thickness_m'][zone-1]
    w = candidate['web_thickness_m'][zone-1]
    h = candidate['outer_width_m']/2
    ax = candidate['inner_axes_x_m']
    ay = candidate['inner_axes_y_m']
    boxes = []
    def vertical(x,y0,y1,thickness):
        boxes.append((x-thickness/2,y0,x+thickness/2,y1))
    def horizontal(y,x0,x1,thickness):
        boxes.append((x0,y-thickness/2,x1,y+thickness/2))
    if zone <= 6:
        end = h if zone <= 4 else candidate['partial_corner_side_end_m']
        for x in [-h+t/2,h-t/2]: vertical(x,-end,end,t)
        for y in [-h+t/2,h-t/2]: horizontal(y,-end,end,t)
        for x in ax: vertical(x,-h,h,w)
        for y in ay: horizontal(y,-h,h,w)
    elif zone <= 8:
        # Five cells. Arm perimeter uses flange thickness, central webs use web.
        for x in [-h+t/2,h-t/2]: vertical(x,ay[0]-t/2,ay[1]+t/2,t)
        for y in [-h+t/2,h-t/2]: horizontal(y,ax[0]-t/2,ax[1]+t/2,t)
        for x in ax:
            vertical(x,-h,ay[0],t); vertical(x,ay[0],ay[1],w); vertical(x,ay[1],h,t)
        for y in ay:
            horizontal(y,-h,ax[0],t); horizontal(y,ax[0],ax[1],w); horizontal(y,ax[1],h,t)
    else:
        # Source topmost three-cell rectangle; local Y direction remains assumed.
        for x in ax: vertical(x,-h,h,t)
        for y in [-h+t/2,h-t/2]: horizontal(y,ax[0]-t/2,ax[1]+t/2,t)
        for y in ay: horizontal(y,ax[0],ax[1],w)
    return boxes


def contains_wall(regions,x,y):
    return any(a <= x <= c and b <= y <= d for a,b,c,d in regions)


def union_prism(regions,z0,z1):
    """Extrude a rectilinear union with shared vertices and no internal side faces."""
    xs=sorted({round(v,9) for a,b,c,d in regions for v in (a,c)})
    ys=sorted({round(v,9) for a,b,c,d in regions for v in (b,d)})
    occupied={(i,j) for i in range(len(xs)-1) for j in range(len(ys)-1)
              if contains_wall(regions,(xs[i]+xs[i+1])/2,(ys[j]+ys[j+1])/2)}
    verts=[]; faces=[]; lookup={}
    def index(i,j,k):
        key=(i,j,k)
        if key not in lookup:
            lookup[key]=len(verts);verts.append((xs[i],ys[j],z1 if k else z0))
        return lookup[key]
    for i,j in sorted(occupied):
        b=[index(i,j,0),index(i+1,j,0),index(i+1,j+1,0),index(i,j+1,0)]
        t=[index(i,j,1),index(i+1,j,1),index(i+1,j+1,1),index(i,j+1,1)]
        faces.extend((tuple(reversed(b)),tuple(t)))
        if (i-1,j) not in occupied:faces.append((b[0],t[0],t[3],b[3]))
        if (i+1,j) not in occupied:faces.append((b[1],b[2],t[2],t[1]))
        if (i,j-1) not in occupied:faces.append((b[0],b[1],t[1],t[0]))
        if (i,j+1) not in occupied:faces.append((b[3],t[3],t[2],b[2]))
    return verts,faces


def build_core(ctx,candidate):
    # Keep previous evidence controls editable but suppress them in current views.
    for o in ctx.objects:
        if any(c.name in {'10_CORE_CONTROLS','11_CORE_PARTITION_INTERFACES','12_CORE_TOPOLOGY_UNRESOLVED'} for c in o.users_collection) or o.name=='CORE_EVIDENCE_LABEL':
            o.hide_render=True;o.hide_viewport=True
    objects=[];reports=[];checks=[]
    heights=candidate['height_boundaries_m']
    for zone in range(1,10):
        z0,z1=heights[zone-1:zone+1]
        regions=wall_regions(candidate,zone)
        verts,faces=union_prism(regions,z0,z1)
        meta={'source_ids':candidate['source_ids'],'evidence_level':'推导值',
              'source_locator':candidate['source_locator'],'geometry_role':'core_idealized_hollow_wall_reference',
              'formula':'Measured Su Fig5 grid + versioned Table1 thickness; union of rectangular wall strips',
              'uncertainty':candidate['uncertainty'], 'asbuilt_verified':False,'zone':zone,
              'source_version':candidate['source_version'],'openings_modeled':False,'reinforcement_modeled':False,
              'thickness_scope':candidate['zone9_thickness_scope'] if zone==9 else 'D10 2010 zone table, final edition unverified',
              'outer_wall_thickness_m':candidate['outer_thickness_m'][zone-1],
              'web_wall_thickness_m':candidate['web_thickness_m'][zone-1],
              'axis_measurement_error_m':candidate['source_measurement']['random_axis_error_m'],
              'systematic_error':'schematic scaling and high-zone layout/transition unbounded',
              'wall_offset_rule':'Outer envelope held at 30m; inward/outward construction shrink axes not verified',
              'high_corner_mapping':'partial wall ends ~8m; diagonal coupling beam is not an extruded RC wall' if zone in (5,6) else ''}
        obj=ctx.mesh(f'CORE_Z{zone:02d}_HOLLOW_WALLS_REFERENCE',verts,faces,'14_CORE_HOLLOW_DERIVED','core',meta)
        objects.append(obj)
        xs=[v.co.x for v in obj.data.vertices];ys=[v.co.y for v in obj.data.vertices]
        reports.append({'zone':zone,'height_m':[z0,z1],'outside_extent_m':[max(xs)-min(xs),max(ys)-min(ys)],'wall_regions':regions,'faces':len(faces),'grid_is_final':False})
        # Every base edge must belong to two faces: actual saved wall mesh is closed.
        edges={}
        for face in obj.data.polygons:
            ids=list(face.vertices)
            for a,b in zip(ids,ids[1:]+ids[:1]):
                key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1
        checks.append({'name':f'core_zone_{zone}_closed_wall_solids','passed':all(n==2 for n in edges.values()),'actual':{'edges':len(edges),'nonmanifold':sum(n!=2 for n in edges.values())},'scope':'Software wall solid topology; building doors/lintels omitted'})
    cell_x=[(-15+candidate['inner_axes_x_m'][0])/2,0,(15+candidate['inner_axes_x_m'][1])/2]
    cell_y=[(-15+candidate['inner_axes_y_m'][0])/2,0,(15+candidate['inner_axes_y_m'][1])/2]
    empty=[not contains_wall(wall_regions(candidate,1),x,y) for x in cell_x for y in cell_y]
    checks.append({'name':'core_nine_cells_are_voids','passed':all(empty),'actual':{'void_cell_centers':sum(empty)},'scope':'Lower nine-cell plan is hollow, not the old full control box; source openings unresolved'})
    checks.append({'name':'new_core_outer_width_30m','passed':math.isclose(reports[0]['outside_extent_m'][0],30,abs_tol=1e-5) and math.isclose(reports[0]['outside_extent_m'][1],30,abs_tol=1e-5),'actual':reports[0]['outside_extent_m'],'scope':'Published outer width, independent of measured internal wall positions'})
    ctx.empty('CORE_TOP_AND_TMD_CONNECTION_UNCONFIRMED',(0,0,heights[-1]),'14_CORE_HOLLOW_DERIVED',
              {'source_ids':candidate['source_ids'],'evidence_level':'待确认',
               'geometry_role':'core_top_tmd_connection_interface','formula':'Core top follows the selected NTUA section height candidate; no platform/node geometry',
               'uncertainty':'Core wall termination, TMD platform footprint and level crosswalk remain unconfirmed; candidate height is not surveyed','asbuilt_verified':False})
    return {'objects':[o.name for o in objects],'zones':reports,'checks':checks,'uncertainty':candidate['uncertainty'],'conflicts':candidate['conflicts']}
